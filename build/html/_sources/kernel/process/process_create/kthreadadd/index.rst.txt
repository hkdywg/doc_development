kthreadd
========

内核初始化 ``rest_init`` 函数中，由进程0创建了两个process

- init进程(pid = 1, ppid = 0)

- kthreadd(pid = 2, ppid = 0)

所有其他内核线程的ppid都是2,也就是说他们都是由kthreadd创建的

2号进程的创建
-------------

::

	pid = kernel_thread(kthreadd, NULL, CLONE_FS | CLONE_FILES);
	rcu_read_lock();
	kthreadd_task = find_task_by_pid_ns(pid, &init_pid_ns);
	rcu_read_unlock();

	/*
	 * Enable might_sleep() and smp_processor_id() checks.
	 * They cannot be enabled earlier because with CONFIG_PREEMPTION=y
	 * kernel_thread() would trigger might_sleep() splats. With
	 * CONFIG_PREEMPT_VOLUNTARY=y the init task might have scheduled
	 * already, but it's stuck on the kthreadd_done completion.
	 */
	system_state = SYSTEM_SCHEDULING;

	complete(&kthreadd_done);

2号进程的循环
-------------

::

    int kthreadd(void *unused)
    {
        struct task_struct *tsk = current;

        /* Setup a clean context for our children to inherit. */
        set_task_comm(tsk, "kthreadd");
        ignore_signals(tsk);
        set_cpus_allowed_ptr(tsk, cpu_all_mask);
        //允许kthread在任意cpuh上运行
        set_mems_allowed(node_states[N_MEMORY]);

        current->flags |= PF_NOFREEZE;
        cgroup_init_kthreadd();

        for (;;) {
        //首先将线程状态设置为TASK_INTERRUPTIBLE,如果当前没有要创建的线程则主动放弃CPU,此进程变为阻塞态
            set_current_state(TASK_INTERRUPTIBLE);
            if (list_empty(&kthread_create_list))
                schedule();
                //没有要创建的内核线程,什么也不做执行一次调度,让出CPU

            //运行到此处表示Kthreadd线程被唤醒,设置进程状态为TASK_RUNNING
            __set_current_state(TASK_RUNNING);

            spin_lock(&kthread_create_lock);
            while (!list_empty(&kthread_create_list)) {
                struct kthread_create_info *create;


                create = list_entry(kthread_create_list.next,
                            struct kthread_create_info, list);
                list_del_init(&create->list);
                //从链表中删除
                spin_unlock(&kthread_create_lock);

                create_kthread(create);
                //创建线程

                spin_lock(&kthread_create_lock);
            }
            spin_unlock(&kthread_create_lock);
        }

        return 0;
    }


在create_kthread()函数中,会调用kernel_thread来生成一个新的进程

::

    pid = kernel_thread(kthread, create, CLONE_FS | CLONE_FILES | SIGCHLD);

kernel_thread会调用 ``_do_fork`` 函数
::

    /*
     * Create a kernel thread.
     */
    pid_t kernel_thread(int (*fn)(void *), void *arg, unsigned long flags)
    {
        struct kernel_clone_args args = {
            .flags		= ((flags | CLONE_VM | CLONE_UNTRACED) & ~CSIGNAL),
            .exit_signal	= (flags & CSIGNAL),
            .stack		= (unsigned long)fn,
            .stack_size	= (unsigned long)arg,
        };

        return _do_fork(&args);
    }

新创建的内核线程kthread函数

::

    static int kthread(void *_create)
    {
        /* Copy data: it's on kthread's stack */
        struct kthread_create_info *create = _create;
        int (*threadfn)(void *data) = create->threadfn;
        //新线程创建完毕后执行的函数
        void *data = create->data;
        //新线程创建完毕后执行的参数
        struct completion *done;
        struct kthread *self;
        int ret;

        self = kzalloc(sizeof(*self), GFP_KERNEL);
        set_kthread_struct(self);

        /* If user was SIGKILLed, I release the structure. */
        done = xchg(&create->done, NULL);
        if (!done) {
            kfree(create);
            do_exit(-EINTR);
        }

        if (!self) {
            create->result = ERR_PTR(-ENOMEM);
            complete(done);
            do_exit(-ENOMEM);
        }

        self->data = data;
        init_completion(&self->exited);
        init_completion(&self->parked);
        current->vfork_done = &self->exited;

        /* OK, tell user we're spawned, wait for stop or wakeup */
        __set_current_state(TASK_UNINTERRUPTIBLE);
        create->result = current;
        //current表示当前新创建的thread的task_struct结构
        complete(done);
        schedule();
        //执行任务切换,让出CPU

        //执行到此处时说明内核调用了wake_up_process(p)唤醒了新创建的线程,线程被唤醒后会接着执行threadfn(data)
        ret = -EINTR;
        if (!test_bit(KTHREAD_SHOULD_STOP, &self->flags)) {
            cgroup_kthread_ready();
            __kthread_parkme(self);
            ret = threadfn(data);
        }
        do_exit(ret);
    }

- 总结

kthreadd进程由idle通过kernel_thread创建,并始终运行在内核空间,负责所有内核线程的调度和管理,他的任务就是管理和调度其他内核线程kernel_thread

我们在内核中通过kernel_create或者其他方式创建一个内核线程,然后kthreadd内核线程会被唤醒,来执行真正的内核线程创建工作，新的线程将执行kthread函数,完成创建工作.
创建完毕后让出CPU，因此新的内核线程不会立刻运行,需要手动wake up被唤醒后将执行自己的真正工作函数

1) 任何一个内核线程入口都是kthread()

2) 通过kthread_create()创建的内核线程不会立刻运行,需要手动wake up

3) 通过kthread_create()创建的内核线程有可能不会执行相应的线程函数threadfn而直接退出
