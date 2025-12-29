poll机制
========

使用 ``man 2 poll`` 命令可查看poll的使用方法和作用。函数原型如下

::

    intt poll(struct pollfd *fds, nfds_t nfds, int timeout);

第一个结构体代表文件描述符，第二个参数代表文件的数量，第三个参数代表超时自动唤醒时间


* :download:`驱动程序实例<res/driver.c>` 

* :download:`应用程序实例<res/app.c>`


以下内容会涉及到等待队列的使用，可参考 kernel_note章节的kernel queue note


poll函数相关参数
-----------------


::

    struct pollfd {
        int fd;     /*该进程中打开文件的文件描述符*/
        short events;   /*表示要请求的事件类型*/
        short revents;  /*表示返回的事件类型*/
    };


    struct timspec {
        __kernel_time_t tv_sec; /*seconds,以s为单位的时间*/   
        long tv_nsec;   /*nanoseconds,以ns为单位的时间*/
    };


    typedef void (*poll_queue_proc)(struct file *, wait_queue_head_t *, struct poll_table_struct *);

    typedef struct poll_table_struct {
        poll_queue_proc _qroc;
        unsigned long _key;
    } poll_table;

    struct poll_list {
        struct poll_list *next;
        int len;
        struct pollfd entries[0];
    };

    struct poll_wqueues {
        poll_table pt;
        struct poll_table_page *table;
        struct task_struct *polling_task;
        int triggered;
        int error;
        int inline_index;
        struct poll_table_entry inline_entries[N_INLINE_POLL_ENTRIES];
    };

其中请求事件和返回事件可以是下面的几种

====================    ====================================
事件                    描述
--------------------    ------------------------------------
POLLIN                  有数据可读
POLLRDNORM              普通数据可读
POLLRDBAND              优先级数据可读
POLLPRI                 高优先级数据可读
POLLOUT                 数据可写
POLLWRNORM              普通数据可写
POLLWRBAND              优先级带数据可写
POLLERR                 发生错误
POLLHUP                 发生挂起
POLLNVAL                描述字不是一个打开的文件
====================    ====================================

.. note::
    后三个只能作为描述字的返回结果存放在revents中，而不能作为测试条件用于events中


sys_poll函数
--------------

::

    SYSCALL_DEFINE3(poll, struct pollfd __user *, ufds, unsigned int, nfds,
            int, timeout_msecs)
    {
        struct timespec64 end_time, *to = NULL;
        int ret;

        if (timeout_msecs >= 0) {   //超时时间换算，最终换算成以struct timespec结构方式计算的秒和纳秒形式
            to = &end_time;
            poll_select_set_timeout(to, timeout_msecs / MSEC_PER_SEC,
                NSEC_PER_MSEC * (timeout_msecs % MSEC_PER_SEC));
        }
        //执行真正的系统调用
        ret = do_sys_poll(ufds, nfds, to);
        //如果在poll期间有信号到来，回返回-ERESTARTNOHAND，这会导致重新调用
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


do_sys_poll
^^^^^^^^^^^^

::
   
    #define FRONTEND_STACK_ALLOC    256
    #define SELECT_STACK_ALLOC  FRONTEND_STACK_ALLOC
    #define POLL_STACK_ALLOC    FRONTEND_STACK_ALLOC
    #define WQUEUES_STACK_ALLOC (MAX_STACK_ALLOC - FRONTEND_STACK_ALLOC)
    #define N_INLINE_POLL_ENTRIES   (WQUEUES_STACK_ALLOC / sizeof(struct poll_table_entry))
    #define DEFAULT_POLLMASK (EPOLLIN | EPOLLOUT | EPOLLRDNORM | EPOLLWRNORM)

    static int do_sys_poll(struct pollfd __user *ufds, unsigned int nfds,
            struct timespec64 *end_time)
    {
        struct poll_wqueues table;  //局部变量分配poll_wqueues
        int err = -EFAULT, fdcount, len;
        /* Allocate small arguments on the stack to save memory and be
           faster - use long to make sure the buffer is aligned properly
           on 64 bit archs to avoid unaligned access */
        long stack_pps[POLL_STACK_ALLOC/sizeof(long)];  //用来存放用户空间传过来的数据
        struct poll_list *const head = (struct poll_list *)stack_pps;
        struct poll_list *walk = head;
        unsigned long todo = nfds;  //等待的事件数目

        if (nfds > rlimit(RLIMIT_NOFILE))   //检查监听的文件数量是否大于进行打开的文件数
            return -EINVAL;

        len = min_t(unsigned int, nfds, N_STACK_PPS);
        for (;;) {
            walk->next = NULL;
            walk->len = len;
            if (!len)
                break;
            //将用户空间的pollfd拷贝到可存放walk的entries空间中
            if (copy_from_user(walk->entries, ufds + nfds-todo,
                        sizeof(struct pollfd) * walk->len))
                goto out_fds;

            todo -= walk->len;
            if (!todo)
                break;
    /*检查一页(4K)和剩下没拷贝的那个小,返回较小者,如果一页也不够拷贝,下轮循环再申请一页
    POLLFD_PER_PAGE表示一页的内存能够存储多少个struct pollfd，可以计算一下，一页是4K，而  
    struct pollfd的内存占用8个字节，就是一页的内存可以将近存储512个pollfd描述符。如果
    在分配一页的内存之后，还不够nfds来用，没关系，循环不会退出的，会再分配一个页，并且所有分
    配的块都被struct poll_list链接起来，上面可以看到，这个结构有一个next域，就是专门做这个
    的。在这之后，就会形成一个以stack_pps存储空间为头，然后一页一页分配的内存为接点的链表，
    这个链表上就存储了poll调用时传入的所有的fd描述符*/

            len = min(todo, POLLFD_PER_PAGE);   
            //动态申请len长度，和64long长度的stack_pps组成一个单向链表
            walk = walk->next = kmalloc(struct_size(walk, entries, len),
                            GFP_KERNEL);
            if (!walk) {
                err = -ENOMEM;
                goto out_fds;
            }
        }
        //初始化等待队列项
        poll_initwait(&table);
        //执行驱动中的poll函数
        fdcount = do_poll(head, &table, end_time);
        //删除等待队列，释放动态申请的空间
        poll_freewait(&table);
        //把内核空间每个文件描述符的返回值，拷贝到用户空间数组中
        for (walk = head; walk; walk = walk->next) {
            struct pollfd *fds = walk->entries;
            int j;

            for (j = 0; j < walk->len; j++, ufds++)
                if (__put_user(fds[j].revents, &ufds->revents))
                    goto out_fds;
        }

        err = fdcount;
    out_fds:    //释放动态申请的内存
        walk = head->next;
        while (walk) {
            struct poll_list *pos = walk;
            walk = walk->next;
            kfree(pos);
        }

        return err;
    }


poll_initwait
""""""""""""""""

::

    //初始化等待队列
    void poll_initwait(struct poll_wqueues *pwq)
    {
        init_poll_funcptr(&pwq->pt, __pollwait);
        pwq->polling_task = current;
        pwq->triggered = 0;
        pwq->error = 0;
        pwq->table = NULL;
        pwq->inline_index = 0;
    }
    EXPORT_SYMBOL(poll_initwait);

    static inline void init_poll_funcptr(poll_table *pt, poll_queue_proc qproc)
    {
        pt->_qproc = qproc; //绑定poll_wait函数
        pt->_key   = ~(__poll_t)0; /* all events enabled */
    }

    //删除等待队列中的所有项，并释放动态申请的空间
    void poll_freewait(struct poll_wqueues *pwq)
    {
        struct poll_table_page * p = pwq->table;
        int i;
        for (i = 0; i < pwq->inline_index; i++)
            free_poll_entry(pwq->inline_entries + i);   //从等待队列中删除所有等待项
        while (p) {     //删除等待列表中所有动态申请的项
            struct poll_table_entry * entry;
            struct poll_table_page *old;

            entry = p->entry;
            do {
                entry--;
                free_poll_entry(entry);
            } while (entry > p->entries);
            old = p;
            p = p->next;
            free_page((unsigned long) old);
        }
    }
    EXPORT_SYMBOL(poll_freewait);


do_poll
""""""""""

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
            //执行每个list链表项中的每个pollfd项
            for (walk = list; walk != NULL; walk = walk->next) {
                struct pollfd * pfd, * pfd_end;

                pfd = walk->entries;    
                pfd_end = pfd + walk->len;
                //每个链表中的entries上可能会挂载多个struct pollfd
                for (; pfd != pfd_end; pfd++) {
                    /*
                     * Fish for events. If we found one, record it
                     * and kill poll_table->_qproc, so we don't
                     * needlessly register any other waiters after
                     * this. They'll get immediately deregistered
                     * when we break out and return.
                     */
                     //处理当前进程的一个fd的poll操作，返回非0值表示有事件发生(或者错误)
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
                if (signal_pending(current))
                    count = -ERESTARTNOHAND;
            }
            if (count || timed_out)
                break;

            /* only if found POLL_BUSY_LOOP sockets && not out of time */
            if (can_busy_loop && !need_resched()) {
                if (!busy_start) {
                    busy_start = busy_loop_current_time();  //如果有us级别的等待，不睡眠而是忙等(我们的调度是ms级别的)
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


do_pollfd
""""""""""

::

    static inline __poll_t do_pollfd(struct pollfd *pollfd, poll_table *pwait,
                         bool *can_busy_poll,
                         __poll_t busy_flag)
    {
        int fd = pollfd->fd;    //得到文件描述符
        __poll_t mask = 0, filter;
        struct fd f;

        if (fd < 0)
            goto out;
        mask = EPOLLNVAL;
        f = fdget(fd);  //通过文件描述符得到文件信息
        if (!f.file)
            goto out;

        /* userland u16 ->events contains POLL... bitmap */
        filter = demangle_poll(pollfd->events) | EPOLLERR | EPOLLHUP;   //错误和热插拔事件是必须要的
        pwait->_key = filter | busy_flag;
        mask = vfs_poll(f.file, pwait); //执行驱动中的poll函数
        if (mask & busy_flag)
            *can_busy_poll = true;
        mask &= filter;		/* Mask out unneeded events. */
        fdput(f);

    out:
        /* ... and so does ->revents */
        pollfd->revents = mangle_poll(mask);
        return mask;
    }

    static inline __poll_t vfs_poll(struct file *file, struct poll_table_struct *pt)
    {
        if (unlikely(!file->f_op->poll))
            return DEFAULT_POLLMASK;
        return file->f_op->poll(file, pt);
    }

驱动程序
---------

我们看一下驱动程序做了什么

::

    static unsigned int button_drv_poll(struct file *file, struct poll_table_struct *wait)
    {
        int mask = 0;

        //将进程挂载button_waitq队列上，不是在这里睡眠
        poll_wait(file, &button_wait_q, wait);
        if(ev_press)
        {
            msk = POLLIN | POLLRDNORM;
        }

        return mask;
    }

poll_wait函数

::

    static inline void poll_wait(struct file * filp, wait_queue_head_t * wait_address, poll_table *p)
    {
        if (p && p->_qproc && wait_address)        /* 检查等待队列头和file中的_qproc存在 */
            p->_qproc(filp, wait_address, p);      /* 执行该函数 */
    }

其中p->qproc是在初始化table的时候绑定的一个函数指针, poll_initwait(&table)函数将__pollwait绑定在_qproc上

::

    
    /*Add a new entry*/
    //__pollwait会把当前进程挂接到等待队列上，并不会睡眠该进程
    //一旦有I/O事件到来，等待队列将被唤醒，就会唤醒等待队列上的进程
    static void __pollwait(struct file *filp, wait_queue_head_t *wait_address,
                    poll_table *p)
    {
        struct poll_wqueues *pwq = container_of(p, struct poll_wqueues, pt);
        struct poll_table_entry *entry = poll_get_entry(pwq);
        if (!entry)
            return;
        entry->filp = get_file(filp);
        entry->wait_address = wait_address; //驱动程序中的等待队列头
        entry->key = p->_key;   //设置等待的事件
        init_waitqueue_func_entry(&entry->wait, pollwake);  //绑定函数唤醒函数
        entry->wait.private = pwq;
        add_wait_queue(wait_address, &entry->wait); //把等待项加入等待队列
    }


唤醒函数

::

    static int __pollwake(wait_queue_entry_t *wait, unsigned mode, int sync, void *key)
    {
        struct poll_wqueues *pwq = wait->private;
        DECLARE_WAITQUEUE(dummy_wait, pwq->polling_task);

        /*
         * Although this function is called under waitqueue lock, LOCK
         * doesn't imply write barrier and the users expect write
         * barrier semantics on wakeup functions.  The following
         * smp_wmb() is equivalent to smp_wmb() in try_to_wake_up()
         * and is paired with smp_store_mb() in poll_schedule_timeout.
         */
        smp_wmb();
        pwq->triggered = 1;

        /*
         * Perform the default wake up operation using a dummy
         * waitqueue.
         *
         * TODO: This is hacky but there currently is no interface to
         * pass in @sync.  @sync is scheduled to be removed and once
         * that happens, wake_up_process() can be used directly.
         */
        return default_wake_function(&dummy_wait, mode, sync, key);
    }

    static int pollwake(wait_queue_entry_t *wait, unsigned mode, int sync, void *key)
    {
        struct poll_table_entry *entry;

        entry = container_of(wait, struct poll_table_entry, wait);
        if (key && !(key_to_poll(key) & entry->key))
            return 0;
        return __pollwake(wait, mode, sync, key);
    }



