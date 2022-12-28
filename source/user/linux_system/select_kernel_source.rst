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
