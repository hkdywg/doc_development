源码解读select/poll/epoll内核机制
=====================================

相关的内核文件

::

    kernel/fs/select.c
    kernel/include/linux/poll.h 
    kernel/include/linux/fs.h
    kernel/include/linux/sched.h
    kernel/include/linux/wait.h
    kernel/kernel/sched/wait.c
    kernel/kernel/sched/core.c


select源码
----------------


select最终是通过底层驱动对应设备文件的poll函数来查询是否有可用资源(可读或者可写),如果没有则睡眠

::

    #include <sys/select.h>

    #define FD_SETSIZE  1024
    #define NFDBITS     (8 * sizeof(unsigned long))
    #define __FDSET_LONGS (FD_SETSIZE/NFDBITS)

    typedef struct {
        unsigned long fds_bits[__FDSET_LONGS];
    } fd_set;


fd_set是个文件描述符fd的集合，每个进程可打开的文件描述符默认值为1024, fd_set采用bitmap算法

- select系统调用对应的方法是 ``sys_select`` ,具体代码如下

::

     SYSCALL_DEFINE5(select, int, n, fd_set __user *, inp, fd_set __user *, outp,
             fd_set __user *, exp, struct timeval __user *, tvp)
     {
         return kern_select(n, inp, outp, exp, tvp);
     }

     static int kern_select(int n, fd_set __user *inp, fd_set __user *outp,
                    fd_set __user *exp, struct timeval __user *tvp)
     {
         struct timespec64 end_time, *to = NULL;
         struct timeval tv;
         int ret;
     
         //设置超时阈值
         if (tvp) { 
             if (copy_from_user(&tv, tvp, sizeof(tv)))
                 return -EFAULT;
     
             to = &end_time;
             if (poll_select_set_timeout(to,
                     tv.tv_sec + (tv.tv_usec / USEC_PER_SEC),
                     (tv.tv_usec % USEC_PER_SEC) * NSEC_PER_USEC))
                 return -EINVAL;
         }
     
         ret = core_sys_select(n, inp, outp, exp, to);
         return poll_select_finish(&end_time, tvp, PT_TIMEVAL, ret);
     }
     

**core_sys_select**

::

    int core_sys_select(int n, fd_set __user *inp, fd_set __user *outp,
                   fd_set __user *exp, struct timespec64 *end_time)
    {
        fd_set_bits fds;
        void *bits;
        int ret, max_fds;
        size_t size, alloc_size;
        struct fdtable *fdt;
        //分配大小为256的数组
        /* Allocate small arguments on the stack to save memory and be faster */
        long stack_fds[SELECT_STACK_ALLOC/sizeof(long)];
    

        ret = -EINVAL;
        if (n < 0)
            goto out_nofds;

        /* max_fds can increase, so grab it once to avoid race */
        rcu_read_lock();
        fdt = files_fdtable(current->files);
        max_fds = fdt->max_fds;
        rcu_read_unlock();
        if (n > max_fds)
            n = max_fds;    //select可监控个数小于等于进程可打开的文件描述符上限

        /*
         * We need 6 bitmaps (in/out/ex for both incoming and outgoing),
         * since we used fdset we need to allocate memory in units of
         * long-words. 
         */
         //根据n来计算需要多少个字节，展开为size=4*(n+32-1)/32
        size = FDS_BYTES(n);
        bits = stack_fds;
        if (size > sizeof(stack_fds) / 6) {
            /* Not enough space in on-stack array; must use kmalloc */
            ret = -ENOMEM;
            if (size > (SIZE_MAX / 6))
                goto out_nofds;

            alloc_size = 6 * size;
            bits = kvmalloc(alloc_size, GFP_KERNEL);
            if (!bits)
                goto out_nofds;
        }
        fds.in      = bits;
        fds.out     = bits +   size;
        fds.ex      = bits + 2*size;
        fds.res_in  = bits + 3*size;
        fds.res_out = bits + 4*size;
        fds.res_ex  = bits + 5*size;

        //将用户空间的inp, outp, exp拷贝到内核空间fds的in out ex
        if ((ret = get_fd_set(n, inp, fds.in)) ||
            (ret = get_fd_set(n, outp, fds.out)) ||
            (ret = get_fd_set(n, exp, fds.ex)))
            goto out;

        //将fds的res_in res_out res_exp内容清零
        zero_fd_set(n, fds.res_in);
        zero_fd_set(n, fds.res_out);
        zero_fd_set(n, fds.res_ex);

        ret = do_select(n, &fds, end_time); //核心方法

        if (ret < 0)
            goto out;
        if (!ret) {
            ret = -ERESTARTNOHAND;
            if (signal_pending(current))
                goto out;
            ret = 0;
        }

        //将fds的res_in res_out res_ex结果拷贝到用户空间inp, outp, exp
        if (set_fd_set(n, inp, fds.res_in) ||
            set_fd_set(n, outp, fds.res_out) ||
            set_fd_set(n, exp, fds.res_ex))
            ret = -EFAULT;

    out:
        if (bits != stack_fds)
            kvfree(bits);
    out_nofds:
        return ret;
    }

**fdset相关操作方法**

::

    //记录可读，可写，异常的输入和输出结果信息
    typedef struct {
        unsigned long *in, *out, *ex;
        unsigned long *res_in, *res_out, *res_ex;
    };

    //将用户空间的ufdset拷贝到内核空间fdset
    static inline int get_fd_set(unsigned long nr, void __user *ufdset, unsigned long *fdset)
    {
        nr = FDS_BYTES(nr);
        if(ufdset) 
            return copy_from_user(fdset, ufdset, nr) ? -EFAULT : 0;
        memset(fdset, 0, nr);
        return 0;
    }

    static intline unsigned long __must_check
    set_fd_set(unsigned long nr, void __user *ufdset, unsigned long *fdset)
    {
        if(ufdset)
            return __copy_to_user(ufdset, fdset, FDS_BYTES(nr));
        return 0;
    }

    static inline void zero_fd_set(unsigned long nr, unsigned long *fdset)
    {
        memset(fdset, 0, FDS_BYTES(nr));
    }


**do_select核心**

::

    static int do_select(int n, fd_set_bits *fds, struct timespec64 *end_time)
    {
        ktime_t expire, *to = NULL;
        struct poll_wqueues table;
        poll_table *wait;
        int retval, i, timed_out = 0;
        u64 slack = 0;
        __poll_t busy_flag = net_busy_loop_on() ? POLL_BUSY_LOOP : 0;
        unsigned long busy_start = 0;

        rcu_read_lock();
        retval = max_select_fd(n, fds);
        rcu_read_unlock();

        if (retval < 0)
            return retval;
        n = retval;

        poll_initwait(&table);  //初始化等待队列
        wait = &table.pt;
        if (end_time && !end_time->tv_sec && !end_time->tv_nsec) {
            wait->_qproc = NULL;
            timed_out = 1;
        }

        if (end_time && !timed_out)
            slack = select_estimate_accuracy(end_time);

        retval = 0;
        for (;;) {
            unsigned long *rinp, *routp, *rexp, *inp, *outp, *exp;
            bool can_busy_loop = false;

            inp = fds->in; outp = fds->out; exp = fds->ex;
            rinp = fds->res_in; routp = fds->res_out; rexp = fds->res_ex;

            for (i = 0; i < n; ++rinp, ++routp, ++rexp) {
                unsigned long in, out, ex, all_bits, bit = 1, j;
                unsigned long res_in = 0, res_out = 0, res_ex = 0;
                __poll_t mask;

                in = *inp++; out = *outp++; ex = *exp++;
                all_bits = in | out | ex;
                if (all_bits == 0) {
                    i += BITS_PER_LONG; //以32bit步长遍历位图，直到在该区间存在目标fd
                    continue;
                }

                for (j = 0; j < BITS_PER_LONG; ++j, ++i, bit <<= 1) {
                    struct fd f;
                    if (i >= n)
                        break;
                    if (!(bit & all_bits))
                        continue;
                    f = fdget(i);   //找到目标fd
                    if (f.file) {
                        wait_key_set(wait, in, out, bit,
                                 busy_flag);
                        mask = vfs_poll(f.file, wait);  //执行文件系统的poll函数，检测IO事件

                        fdput(f);
                        //写入对应的in/out/ex结果
                        if ((mask & POLLIN_SET) && (in & bit)) {
                            res_in |= bit;
                            retval++;
                            wait->_qproc = NULL;
                        }
                        if ((mask & POLLOUT_SET) && (out & bit)) {
                            res_out |= bit;
                            retval++;
                            wait->_qproc = NULL;
                        }
                        if ((mask & POLLEX_SET) && (ex & bit)) {
                            res_ex |= bit;
                            retval++;
                            wait->_qproc = NULL;
                        }
                        //当返回值不为零，则停止循环轮循
                        /* got something, stop busy polling */
                        if (retval) {
                            can_busy_loop = false;
                            busy_flag = 0;

                        /*
                         * only remember a returned
                         * POLL_BUSY_LOOP if we asked for it
                         */
                        } else if (busy_flag & mask)
                            can_busy_loop = true;

                    }
                }
                //本轮循环遍历完成，则更新fd事件的结果
                if (res_in)
                    *rinp = res_in;
                if (res_out)
                    *routp = res_out;
                if (res_ex)
                    *rexp = res_ex;
                cond_resched(); //让出cpu给其他进程运行
            }
            wait->_qproc = NULL;
            //当有文件描述符就绪或超时或有待处理的信号，则退出循环
            if (retval || timed_out || signal_pending(current))
                break;
            if (table.error) {
                retval = table.error;
                break;
            }

            /* only if found POLL_BUSY_LOOP sockets && not out of time */
            if (can_busy_loop && !need_resched()) {
                if (!busy_start) {
                    busy_start = busy_loop_current_time();
                    continue;
                }
                if (!busy_loop_timeout(busy_start))
                    continue;
            }
            busy_flag = 0;

            /*
             * If this is the first loop and we have a timeout
             * given, then we convert to ktime_t and set the to
             * pointer to the expiry value.
             */
            if (end_time && !to) {
                expire = timespec64_to_ktime(*end_time);
                to = &expire;
            }

            if (!poll_schedule_timeout(&table, TASK_INTERRUPTIBLE,
                           to, slack))
                timed_out = 1;
        }

        poll_freewait(&table);  //释放poll等待队列

        return retval;
    }


do_select最核心的还是调用文件系统 ``vfs_poll`` 函数来检测IO事件

- 当存在被监听的fd触发目标事件则将其fd记录下来，退出循环体，返回用户空间

- 当没有找到目标事件，如果已超时或者有待处理的信号，也会退出循环体，返回用户空间

- 当以上两种情况都不满足，则会让进程进入休眠状态，以等待fd或者超时定时器来唤醒自己


poll源码
------------

poll函数对应的系统调用是 ``sys_poll``

::
    
    SYSCALL_DEFINE3(poll, struct pollfd __user *, ufds, unsigned int, nfds,
            int, timeout_msecs)
    {
        struct timespec64 end_time, *to = NULL;
        int ret;

        //设置超时
        if (timeout_msecs >= 0) {
            to = &end_time;
            poll_select_set_timeout(to, timeout_msecs / MSEC_PER_SEC,
                NSEC_PER_MSEC * (timeout_msecs % MSEC_PER_SEC));
        }

        ret = do_sys_poll(ufds, nfds, to);

        if (ret == -ERESTARTNOHAND) {
            struct restart_block *restart_block;

            restart_block = &current->restart_block;
            restart_block->fn = do_restart_poll;
            restart_block->poll.ufds = ufds;
            restart_block->poll.nfds = nfds;

            if (timeout_msecs >= 0) {
                restart_block->poll.tv_sec = end_time.tv_sec;
                restart_block->poll.tv_nsec = end_time.tv_nsec;
                restart_block->poll.has_timeout = 1;
            } else
                restart_block->poll.has_timeout = 0;

            ret = -ERESTART_RESTARTBLOCK;
        }
        return ret;
    }


**do_sys_poll**

::

    static int do_sys_poll(struct pollfd __user *ufds, unsigned int nfds,
            struct timespec64 *end_time)
    {
        struct poll_wqueues table;
        int err = -EFAULT, fdcount, len;
        /* Allocate small arguments on the stack to save memory and be
           faster - use long to make sure the buffer is aligned properly
           on 64 bit archs to avoid unaligned access */
        long stack_pps[POLL_STACK_ALLOC/sizeof(long)];
        struct poll_list *const head = (struct poll_list *)stack_pps;
        struct poll_list *walk = head;
        unsigned long todo = nfds;

        if (nfds > rlimit(RLIMIT_NOFILE))   //上限默认是1024
            return -EINVAL;

        len = min_t(unsigned int, nfds, N_STACK_PPS);
        for (;;) {
            walk->next = NULL;
            walk->len = len;
            if (!len)
                break;

            //拷贝用户空间pollfd到内核空间
            if (copy_from_user(walk->entries, ufds + nfds-todo,
                        sizeof(struct pollfd) * walk->len))
                goto out_fds;

            todo -= walk->len;
            if (!todo)
                break;

            len = min(todo, POLLFD_PER_PAGE);
            walk = walk->next = kmalloc(struct_size(walk, entries, len),
                            GFP_KERNEL);
            if (!walk) {
                err = -ENOMEM;
                goto out_fds;
            }
        }

        poll_initwait(&table);
        fdcount = do_poll(head, &table, end_time);
        poll_freewait(&table);

        for (walk = head; walk; walk = walk->next) {
            struct pollfd *fds = walk->entries;
            int j;

            for (j = 0; j < walk->len; j++, ufds++)
                if (__put_user(fds[j].revents, &ufds->revents))
                    goto out_fds;
        }

        err = fdcount;
    out_fds:
        walk = head->next;
        while (walk) {
            struct poll_list *pos = walk;
            walk = walk->next;
            kfree(pos);
        }

        return err;
    }

进程可打开文件的上限可通过命令ulimit -n获取，默认为1024


**do_poll**

::
    
    static int do_poll(struct poll_list *list, struct poll_wqueues *wait,
               struct timespec64 *end_time)
    {
        poll_table* pt = &wait->pt;
        ktime_t expire, *to = NULL;
        int timed_out = 0, count = 0;
        u64 slack = 0;
        __poll_t busy_flag = net_busy_loop_on() ? POLL_BUSY_LOOP : 0;
        unsigned long busy_start = 0;

        /* Optimise the no-wait case */
        if (end_time && !end_time->tv_sec && !end_time->tv_nsec) {
            pt->_qproc = NULL;
            timed_out = 1;
        }

        if (end_time && !timed_out)
            slack = select_estimate_accuracy(end_time);

        for (;;) {
            struct poll_list *walk;
            bool can_busy_loop = false;

            for (walk = list; walk != NULL; walk = walk->next) {
                struct pollfd * pfd, * pfd_end;

                pfd = walk->entries;
                pfd_end = pfd + walk->len;
                for (; pfd != pfd_end; pfd++) {
                    /*
                     * Fish for events. If we found one, record it
                     * and kill poll_table->_qproc, so we don't
                     * needlessly register any other waiters after
                     * this. They'll get immediately deregistered
                     * when we break out and return.
                     */
                    if (do_pollfd(pfd, pt, &can_busy_loop,
                              busy_flag)) {
                        count++;
                        pt->_qproc = NULL;
                        /* found something, stop busy polling */
                        busy_flag = 0;
                        can_busy_loop = false;
                    }
                }
            }
            /*
             * All waiters have already been registered, so don't provide
             * a poll_table->_qproc to them on the next loop iteration.
             */
            pt->_qproc = NULL;
            if (!count) {
                count = wait->error;
                if (signal_pending(current))    //有待处理信号，则跳出循环
                    count = -ERESTARTNOHAND;
            }
            if (count || timed_out)     //监听事件触发，或者超时，跳出循环
                break;

            /* only if found POLL_BUSY_LOOP sockets && not out of time */
            if (can_busy_loop && !need_resched()) {
                if (!busy_start) {
                    busy_start = busy_loop_current_time();
                    continue;
                }
                if (!busy_loop_timeout(busy_start))
                    continue;
            }
            busy_flag = 0;

            /*
             * If this is the first loop and we have a timeout
             * given, then we convert to ktime_t and set the to
             * pointer to the expiry value.
             */
            if (end_time && !to) {
                expire = timespec64_to_ktime(*end_time);
                to = &expire;
            }

            if (!poll_schedule_timeout(wait, TASK_INTERRUPTIBLE, to, slack))
                timed_out = 1;
        }
        return count;
    }



**do_pollfd**

::

    static inline __poll_t do_pollfd(struct pollfd *pollfd, poll_table *pwait,
                         bool *can_busy_poll,
                         __poll_t busy_flag)
    {
        int fd = pollfd->fd;
        __poll_t mask = 0, filter;
        struct fd f;

        if (fd < 0)
            goto out;
        mask = EPOLLNVAL;
        f = fdget(fd);
        if (!f.file)
            goto out;

        /* userland u16 ->events contains POLL... bitmap */
        filter = demangle_poll(pollfd->events) | EPOLLERR | EPOLLHUP;
        pwait->_key = filter | busy_flag;
        mask = vfs_poll(f.file, pwait);     //调用文件系统的poll函数
        if (mask & busy_flag)
            *can_busy_poll = true;
        mask &= filter;		/* Mask out unneeded events. */
        fdput(f);

    out:
        /* ... and so does ->revents */
        pollfd->revents = mangle_poll(mask);    //设置revents
        return mask;
    }


.. note::
    select和poll机制的原理非常接近，主要是一些数据结构的不同，最终到驱动层都会执行f_op->poll函数，执行__pollwait()把自己挂入到
    等待队列，一旦有事件发生时便会唤醒等待队列上的进程．这一切都是基于底层文件系统作为基石来完成IO多路复用的事件监听功能


epoll源码
-----------

select和poll作为IO多路复用的机制有如下缺点

- 通过select单个进程能够监控的文件描述符不得超过进程可打开的文件个数上限，默认为1024,即使强行修改这个上限，还会遇到性能问题

- select轮循效率随着监控个数的增加而性能变差

- select从内核返回到用户空间的是整个文件描述符数组，应用程序还需要再遍历整个数组才知道哪些文件描述符出发了相应事件


**epoll_create**

::

    SYSCALL_DEFINE1(epoll_create, int, size)
    {
        if (size <= 0)
            return -EINVAL;

        return do_epoll_create(0);
    }

    /*
     * Open an eventpoll file descriptor.
     */
    static int do_epoll_create(int flags)
    {
        int error, fd;
        struct eventpoll *ep = NULL;
        struct file *file;

        /* Check the EPOLL_* constant for consistency.  */
        BUILD_BUG_ON(EPOLL_CLOEXEC != O_CLOEXEC);

        if (flags & ~EPOLL_CLOEXEC)
            return -EINVAL;
        /*
         * Create the internal data structure ("struct eventpoll").
         */
        //创建内部数据结构eventpoll
        error = ep_alloc(&ep);
        if (error < 0)
            return error;
        /*
         * Creates all the items needed to setup an eventpoll file. That is,
         * a file structure and a free file descriptor.
         */
        //查询未使用的fd
        fd = get_unused_fd_flags(O_RDWR | (flags & O_CLOEXEC));
        if (fd < 0) {
            error = fd;
            goto out_free_ep;
        }
        //创建file实例，以及匿名inode节点和dentry等数据结构
        file = anon_inode_getfile("[eventpoll]", &eventpoll_fops, ep,
                     O_RDWR | (flags & O_CLOEXEC));
        if (IS_ERR(file)) {
            error = PTR_ERR(file);
            goto out_free_fd;
        }
        ep->file = file;
        fd_install(fd, file);   //建立fd和file的关联关系
        return fd;

    out_free_fd:
        put_unused_fd(fd);
    out_free_ep:
        ep_free(ep);
        return error;
    }


**epoll_ctl**

::

    SYSCALL_DEFINE4(epoll_ctl, int, epfd, int, op, int, fd,
            struct epoll_event __user *, event)
    {
        int error;
        int full_check = 0;
        struct fd f, tf;
        struct eventpoll *ep;
        struct epitem *epi;
        struct epoll_event epds;
        struct eventpoll *tep = NULL;

        //将用户空间的epoll_event拷贝到内核
        error = -EFAULT;
        if (ep_op_has_event(op) &&
            copy_from_user(&epds, event, sizeof(struct epoll_event)))
            goto error_return;

        error = -EBADF;
        f = fdget(epfd);    //epfd对应的file文件
        if (!f.file)
            goto error_return;

        /* Get the "struct file *" for the target file */
        tf = fdget(fd);     //fd对应的file文件
        if (!tf.file)
            goto error_fput;

        /* The target file descriptor must support poll */
        error = -EPERM;
        if (!file_can_poll(tf.file))    //目标文件描述符必须支持poll
            goto error_tgt_fput;

        /* Check if EPOLLWAKEUP is allowed */
        if (ep_op_has_event(op))        //检查是否支持EPOLLWAKEUP
            ep_take_care_of_epollwakeup(&epds);

        /*
         * We have to check that the file structure underneath the file descriptor
         * the user passed to us _is_ an eventpoll file. And also we do not permit
         * adding an epoll file descriptor inside itself.
         */
        error = -EINVAL;
        if (f.file == tf.file || !is_file_epoll(f.file))
            goto error_tgt_fput;

        /*
         * epoll adds to the wakeup queue at EPOLL_CTL_ADD time only,
         * so EPOLLEXCLUSIVE is not allowed for a EPOLL_CTL_MOD operation.
         * Also, we do not currently supported nested exclusive wakeups.
         */
        if (ep_op_has_event(op) && (epds.events & EPOLLEXCLUSIVE)) {
            if (op == EPOLL_CTL_MOD)
                goto error_tgt_fput;
            if (op == EPOLL_CTL_ADD && (is_file_epoll(tf.file) ||
                    (epds.events & ~EPOLLEXCLUSIVE_OK_BITS)))
                goto error_tgt_fput;
        }

        /*
         * At this point it is safe to assume that the "private_data" contains
         * our own data structure.
         */
        ep = f.file->private_data;  //取出epoll_create过程创建的ep

        /*
         * When we insert an epoll file descriptor, inside another epoll file
         * descriptor, there is the change of creating closed loops, which are
         * better be handled here, than in more critical paths. While we are
         * checking for loops we also determine the list of files reachable
         * and hang them on the tfile_check_list, so we can check that we
         * haven't created too many possible wakeup paths.
         *
         * We do not need to take the global 'epumutex' on EPOLL_CTL_ADD when
         * the epoll file descriptor is attaching directly to a wakeup source,
         * unless the epoll file descriptor is nested. The purpose of taking the
         * 'epmutex' on add is to prevent complex toplogies such as loops and
         * deep wakeup paths from forming in parallel through multiple
         * EPOLL_CTL_ADD operations.
         */
        mutex_lock_nested(&ep->mtx, 0);
        if (op == EPOLL_CTL_ADD) {
            if (!list_empty(&f.file->f_ep_links) ||
                    ep->gen == loop_check_gen ||
                            is_file_epoll(tf.file)) {
                full_check = 1;
                mutex_unlock(&ep->mtx);
                mutex_lock(&epmutex);
                if (is_file_epoll(tf.file)) {
                    error = -ELOOP;
                    if (ep_loop_check(ep, tf.file) != 0)
                        goto error_tgt_fput;
                } else {
                    get_file(tf.file);
                    list_add(&tf.file->f_tfile_llink,
                                &tfile_check_list);
                }
                mutex_lock_nested(&ep->mtx, 0);
                if (is_file_epoll(tf.file)) {
                    tep = tf.file->private_data;
                    mutex_lock_nested(&tep->mtx, 1);
                }
            }
        }

        /*
         * Try to lookup the file inside our RB tree, Since we grabbed "mtx"
         * above, we can be sure to be able to use the item looked up by
         * ep_find() till we release the mutex.
         */
        epi = ep_find(ep, tf.file, fd); //ep红黑树中查找该fd

        error = -EINVAL;
        switch (op) {
        case EPOLL_CTL_ADD:
            if (!epi) {
                epds.events |= EPOLLERR | EPOLLHUP;
                error = ep_insert(ep, &epds, tf.file, fd, full_check);  //增加
            } else
                error = -EEXIST;
            break;
        case EPOLL_CTL_DEL:
            if (epi)
                error = ep_remove(ep, epi); //删除
            else
                error = -ENOENT;
            break;
        case EPOLL_CTL_MOD:
            if (epi) {
                if (!(epi->event.events & EPOLLEXCLUSIVE)) {
                    epds.events |= EPOLLERR | EPOLLHUP;
                    error = ep_modify(ep, epi, &epds);  //修改
                }
            } else
                error = -ENOENT;
            break;
        }
        if (tep != NULL)
            mutex_unlock(&tep->mtx);
        mutex_unlock(&ep->mtx);

    error_tgt_fput:
        if (full_check) {
            clear_tfile_check_list();
            loop_check_gen++;
            mutex_unlock(&epmutex);
        }

        fdput(tf);
    error_fput:
        fdput(f);
    error_return:

        return error;
    }

**ep_insert**

::

    static int ep_insert(struct eventpoll *ep, const struct epoll_event *event,
                 struct file *tfile, int fd, int full_check)
    {
        int error, pwake = 0;
        __poll_t revents;
        long user_watches;
        struct epitem *epi;
        struct ep_pqueue epq;

        lockdep_assert_irqs_enabled();

        user_watches = atomic_long_read(&ep->user->epoll_watches);
        if (unlikely(user_watches >= max_user_watches))
            return -ENOSPC;
        if (!(epi = kmem_cache_alloc(epi_cache, GFP_KERNEL)))
            return -ENOMEM;

        //构造并填充epi结构体
        /* Item initialization follow here ... */
        INIT_LIST_HEAD(&epi->rdllink);
        INIT_LIST_HEAD(&epi->fllink);
        INIT_LIST_HEAD(&epi->pwqlist);
        epi->ep = ep;
        ep_set_ffd(&epi->ffd, tfile, fd);
        epi->event = *event;
        epi->nwait = 0;
        epi->next = EP_UNACTIVE_PTR;
        if (epi->event.events & EPOLLWAKEUP) {
            error = ep_create_wakeup_source(epi);
            if (error)
                goto error_create_wakeup_source;
        } else {
            RCU_INIT_POINTER(epi->ws, NULL);
        }

        /* Add the current item to the list of active epoll hook for this file */
        spin_lock(&tfile->f_lock);
        list_add_tail_rcu(&epi->fllink, &tfile->f_ep_links);
        spin_unlock(&tfile->f_lock);

        /*
         * Add the current item to the RB tree. All RB tree operations are
         * protected by "mtx", and ep_insert() is called with "mtx" held.
         */
        ep_rbtree_insert(ep, epi);  //将当前epi添加到RB树

        /* now check if we've created too many backpaths */
        error = -EINVAL;
        if (full_check && reverse_path_check())
            goto error_remove_epi;

        /* Initialize the poll table using the queue callback */
        epq.epi = epi;
        init_poll_funcptr(&epq.pt, ep_ptable_queue_proc);   //设置轮循回调函数

        /*
         * Attach the item to the poll hooks and get current event bits.
         * We can safely use the file* here because its usage count has
         * been increased by the caller of this function. Note that after
         * this operation completes, the poll callback can start hitting
         * the new item.
         */
        revents = ep_item_poll(epi, &epq.pt, 1);    //执行poll方法

        /*
         * We have to check if something went wrong during the poll wait queue
         * install process. Namely an allocation for a wait queue failed due
         * high memory pressure.
         */
        error = -ENOMEM;
        if (epi->nwait < 0)
            goto error_unregister;

        /* We have to drop the new item inside our item list to keep track of it */
        write_lock_irq(&ep->lock);

        /* record NAPI ID of new item if present */
        ep_set_busy_poll_napi_id(epi);

        /* If the file is already "ready" we drop it inside the ready list */
        //事件就绪并且epi的就绪队列有数据
        if (revents && !ep_is_linked(epi)) {
            list_add_tail(&epi->rdllink, &ep->rdllist);
            ep_pm_stay_awake(epi);

            //唤醒正在等待文件，调用epoll_wait进程
            /* Notify waiting tasks that events are available */
            if (waitqueue_active(&ep->wq))
                wake_up(&ep->wq);
            if (waitqueue_active(&ep->poll_wait))
                pwake++;
        }

        write_unlock_irq(&ep->lock);

        atomic_long_inc(&ep->user->epoll_watches);

        /* We have to call this outside the lock */
        if (pwake)
            ep_poll_safewake(&ep->poll_wait);   //唤醒等待eventpoll文件就绪的进程

        return 0;

    error_unregister:
        ep_unregister_pollwait(ep, epi);
    error_remove_epi:
        spin_lock(&tfile->f_lock);
        list_del_rcu(&epi->fllink);
        spin_unlock(&tfile->f_lock);

        rb_erase_cached(&epi->rbn, &ep->rbr);

        /*
         * We need to do this because an event could have been arrived on some
         * allocated wait queue. Note that we don't care about the ep->ovflist
         * list, since that is used/cleaned only inside a section bound by "mtx".
         * And ep_insert() is called with "mtx" held.
         */
        write_lock_irq(&ep->lock);
        if (ep_is_linked(epi))
            list_del_init(&epi->rdllink);
        write_unlock_irq(&ep->lock);

        wakeup_source_unregister(ep_wakeup_source(epi));

    error_create_wakeup_source:
        kmem_cache_free(epi_cache, epi);

        return error;
    }


**ep_item_poll**

::

    static inline unsigned int ep_item_poll(struct epitem *epi, poll_table *pt)
    {
        pt->_key = epi->event.events;
        //调用文件系统的poll核心方法
        return epi->ffd.file->f_op->poll(epi->ffd.file, pt) & epi->event.events;
    }

**ep_wait**

::

    SYSCALL_DEFINE4(epoll_wait, int, epfd, struct epoll_event __user *, events,
            int, maxevents, int, timeout)
    {
        return do_epoll_wait(epfd, events, maxevents, timeout);
    }

    static int do_epoll_wait(int epfd, struct epoll_event __user *events,
                 int maxevents, int timeout)
    {
        int error;
        struct fd f;
        struct eventpoll *ep;

        /* The maximum number of event must be greater than zero */
        if (maxevents <= 0 || maxevents > EP_MAX_EVENTS)
            return -EINVAL;

        //检查用户空间传递的内存是否可写
        /* Verify that the area passed by the user is writeable */
        if (!access_ok(events, maxevents * sizeof(struct epoll_event)))
            return -EFAULT;

        /* Get the "struct file *" for the eventpoll file */
        f = fdget(epfd);    //获取eventpoll文件
        if (!f.file)
            return -EBADF;

        /*
         * We have to check that the file structure underneath the fd
         * the user passed to us _is_ an eventpoll file.
         */
        error = -EINVAL;
        if (!is_file_epoll(f.file))
            goto error_fput;

        /*
         * At this point it is safe to assume that the "private_data" contains
         * our own data structure.
         */
        ep = f.file->private_data;  //获取epoll_create创建的ep

        /* Time to fish for events ... */
        error = ep_poll(ep, events, maxevents, timeout);

    error_fput:
        fdput(f);
        return error;
    }


**ep_poll**

::

    static int ep_poll(struct eventpoll *ep, struct epoll_event __user *events,
               int maxevents, long timeout)
    {
        int res = 0, eavail, timed_out = 0;
        u64 slack = 0;
        wait_queue_entry_t wait;
        ktime_t expires, *to = NULL;

        lockdep_assert_irqs_enabled();

        if (timeout > 0) {  //超时设置
            struct timespec64 end_time = ep_set_mstimeout(timeout);

            slack = select_estimate_accuracy(&end_time);
            to = &expires;
            *to = timespec64_to_ktime(end_time);
        } else if (timeout == 0) {
            /*
             * Avoid the unnecessary trip to the wait queue loop, if the
             * caller specified a non blocking operation. We still need
             * lock because we could race and not see an epi being added
             * to the ready list while in irq callback. Thus incorrectly
             * returning 0 back to userspace.
             */
            timed_out = 1;
            //timeout等于0为非阻塞操作，此处避免不必要的等待队列循环
            write_lock_irq(&ep->lock);
            eavail = ep_events_available(ep);
            write_unlock_irq(&ep->lock);

            goto send_events;
        }

    fetch_events:

        //没有事件就绪则进入睡眠状态，当事件就绪后可通过ep_poll_callback来唤醒
        if (!ep_events_available(ep))
            ep_busy_loop(ep, timed_out);

        eavail = ep_events_available(ep);
        if (eavail)
            goto send_events;

        /*
         * Busy poll timed out.  Drop NAPI ID for now, we can add
         * it back in when we have moved a socket with a valid NAPI
         * ID onto the ready list.
         */
        ep_reset_busy_poll_napi_id(ep);

        do {
            /*
             * Internally init_wait() uses autoremove_wake_function(),
             * thus wait entry is removed from the wait queue on each
             * wakeup. Why it is important? In case of several waiters
             * each new wakeup will hit the next waiter, giving it the
             * chance to harvest new event. Otherwise wakeup can be
             * lost. This is also good performance-wise, because on
             * normal wakeup path no need to call __remove_wait_queue()
             * explicitly, thus ep->lock is not taken, which halts the
             * event delivery.
             */
            init_wait(&wait);
            write_lock_irq(&ep->lock);
            //将当前进程加入到eventpoll等待队列，等待文件就绪，超时，或者中断信号
            __add_wait_queue_exclusive(&ep->wq, &wait);
            write_unlock_irq(&ep->lock);

            /*
             * We don't want to sleep if the ep_poll_callback() sends us
             * a wakeup in between. That's why we set the task state
             * to TASK_INTERRUPTIBLE before doing the checks.
             */
            set_current_state(TASK_INTERRUPTIBLE);
            /*
             * Always short-circuit for fatal signals to allow
             * threads to make a timely exit without the chance of
             * finding more events available and fetching
             * repeatedly.
             */
            if (fatal_signal_pending(current)) {
                res = -EINTR;
                break;
            }

            //有事件就绪则跳出循环
            eavail = ep_events_available(ep);
            if (eavail)
                break;
            //有等待处理的信号跳出循环
            if (signal_pending(current)) {
                res = -EINTR;
                break;
            }
            //主动让出CPU,从这里开始进入睡眠状态 
            if (!schedule_hrtimeout_range(to, slack, HRTIMER_MODE_ABS)) {
                timed_out = 1;
                break;
            }

            /* We were woken up, thus go and try to harvest some events */
            eavail = 1;

        } while (0);

        __set_current_state(TASK_RUNNING);

        if (!list_empty_careful(&wait.entry)) {
            write_lock_irq(&ep->lock);
            __remove_wait_queue(&ep->wq, &wait);
            write_unlock_irq(&ep->lock);
        }

    send_events:
        /*
         * Try to transfer events to user space. In case we get 0 events and
         * there's still timeout left over, we go trying again in search of
         * more luck.
         */
        if (!res && eavail &&
            !(res = ep_send_events(ep, events, maxevents)) && !timed_out)
            goto fetch_events;

        return res;
    }


.. note::
    - epoll_create(): 创建并初始化eventpoll结构体ep,并将ep放入file->private，并返回fd
    - epoll_ctl(): 以插入epi为例(进入ep_insert)
      - init_poll_funcptr(): 将ep_pquenue->pt的成员变量_qproc设置为ep_ptable_queue_proc函数，用于poll_wait()的回调函数
      - ep_item_poll(): 执行上面设置的回调函数ep_table_queue_proc
      - ep_ptable_queue_proc(): 设置pwq->wait的成员变量func唤醒函数为ep_poll_callback,这是用于就绪事件触发时，唤醒该进程所用的回调函数，再将ep_poll_callback放入等待队列头whead
    - ep_wait(): 主要工作是执行ep_poll()方法
      - wait->func的唤醒函数为default_wake_function(),并将等待队列项加入ep->wq
      - schedule_hrtimeout_range(): 让出cpu,进入睡眠状态



.. note::
    epoll比select更高效的一点是: epoll监控的每一个文件fd就绪事件触发，导致相应的fd上的回调函数ep_poll_callback()被调用



