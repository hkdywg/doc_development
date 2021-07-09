linux唤醒抢占
==============

当在try_to_wake_up和wake_up_process和wanke_up_new_task中唤醒进程时，内核使用全局check_preemp_curr查看是否进程可以抢占当前进程。每个调度器
都会实现check_preempt_cuur, 在全局的check_preempt_cuur会调用进程所调度器类check_preempt_curr进行抢占检查

linux进程的睡眠
----------------

在linux中，仅等待CPU时间的进程称为就绪进程，他们被放置在一个运行队列，一个就绪进程的状态标志为TASK_RUNNING. 一旦一个运行中的进程时间片用完,
linux内核的调度器会剥夺这个进程对CPU的控制权,并且从运行队列中选择一个合适的进程投入运行.当然一个进程也可以主动释放CPU的使用权,schedule()是
一个调度函数它可以被一个进程主动调用,从而调度其他进程占用CPU

linux中进程睡眠状态有两种

1) 一种是可中断的睡眠状态，其状态标志位TASK_INTERRUPTIBLE. 可中断的睡眠状态的进程会睡眠直到某个条件变为真，比如产生一个硬件中断，释放进程正在等待的资源可以唤醒进程的条件

2) 另一种是不可中断的睡眠状态,其状态标志位TASK_UNINTERRUPTIBLE。与不可中断的睡眠状态区别在于它不响应信号的唤醒

进程一般都是调用schedule的方法进入睡眠状态的，下面的代码演示了如何让正在运行的进程进入睡眠状态

::

    sleeping_task = current;
    set_curreent_state(TASK_INTERRUPTIBLE);
    schedule();
    func1();
    ....


linux进程的唤醒
----------------

- wake_up_process

::

    int wake_up_process(struct task_struct *p)
    {
        return try_to_wake_up(p, TASK_NORMAL, 0);
    }

在调用了wake_up_process以后，这个睡眠进程的状态会被设置为TASK_RUNNING,而且调度器会把它加入到运行队列中去,当然，这个进程只有在下次被调度器调度到的时候才能真正投入运行

- try_to_wake_up

::

    static int
    try_to_wake_up(struct task_struct *p, unsigned int state, int wake_flags)
    {
        unsigned long flags;
        int cpu, success = 0;

        preempt_disable();
        if (p == current) {
            /*
             * We're waking current, this means 'p->on_rq' and 'task_cpu(p)
             * == smp_processor_id()'. Together this means we can special
             * case the whole 'p->on_rq && ttwu_remote()' case below
             * without taking any locks.
             *
             * In particular:
             *  - we rely on Program-Order guarantees for all the ordering,
             *  - we're serialized against set_special_state() by virtue of
             *    it disabling IRQs (this allows not taking ->pi_lock).
             */
            if (!(p->state & state))
                goto out;

            success = 1;
            cpu = task_cpu(p);
            trace_sched_waking(p);
            p->state = TASK_RUNNING;
            trace_sched_wakeup(p);
            goto out;
        }

        /*
         * If we are going to wake up a thread waiting for CONDITION we
         * need to ensure that CONDITION=1 done by the caller can not be
         * reordered with p->state check below. This pairs with mb() in
         * set_current_state() the waiting thread does.
         */
        raw_spin_lock_irqsave(&p->pi_lock, flags);
        smp_mb__after_spinlock();
        if (!(p->state & state))
            goto unlock;

        trace_sched_waking(p);

        /* We're going to change ->state: */
        success = 1;
        cpu = task_cpu(p);

        /*
         * Ensure we load p->on_rq _after_ p->state, otherwise it would
         * be possible to, falsely, observe p->on_rq == 0 and get stuck
         * in smp_cond_load_acquire() below.
         *
         * sched_ttwu_pending()			try_to_wake_up()
         *   STORE p->on_rq = 1			  LOAD p->state
         *   UNLOCK rq->lock
         *
         * __schedule() (switch to task 'p')
         *   LOCK rq->lock			  smp_rmb();
         *   smp_mb__after_spinlock();
         *   UNLOCK rq->lock
         *
         * [task p]
         *   STORE p->state = UNINTERRUPTIBLE	  LOAD p->on_rq
         *
         * Pairs with the LOCK+smp_mb__after_spinlock() on rq->lock in
         * __schedule().  See the comment for smp_mb__after_spinlock().
         */
        smp_rmb();
        if (p->on_rq && ttwu_remote(p, wake_flags))
            goto unlock;

    #ifdef CONFIG_SMP
        /*
         * Ensure we load p->on_cpu _after_ p->on_rq, otherwise it would be
         * possible to, falsely, observe p->on_cpu == 0.
         *
         * One must be running (->on_cpu == 1) in order to remove oneself
         * from the runqueue.
         *
         * __schedule() (switch to task 'p')	try_to_wake_up()
         *   STORE p->on_cpu = 1		  LOAD p->on_rq
         *   UNLOCK rq->lock
         *
         * __schedule() (put 'p' to sleep)
         *   LOCK rq->lock			  smp_rmb();
         *   smp_mb__after_spinlock();
         *   STORE p->on_rq = 0			  LOAD p->on_cpu
         *
         * Pairs with the LOCK+smp_mb__after_spinlock() on rq->lock in
         * __schedule().  See the comment for smp_mb__after_spinlock().
         */
        smp_rmb();

        /*
         * If the owning (remote) CPU is still in the middle of schedule() with
         * this task as prev, wait until its done referencing the task.
         *
         * Pairs with the smp_store_release() in finish_task().
         *
         * This ensures that tasks getting woken will be fully ordered against
         * their previous state and preserve Program Order.
         */
        smp_cond_load_acquire(&p->on_cpu, !VAL);

        p->sched_contributes_to_load = !!task_contributes_to_load(p);
        p->state = TASK_WAKING;

        if (p->in_iowait) {
            delayacct_blkio_end(p);
            atomic_dec(&task_rq(p)->nr_iowait);
        }

        cpu = select_task_rq(p, p->wake_cpu, SD_BALANCE_WAKE, wake_flags);
        if (task_cpu(p) != cpu) {
            wake_flags |= WF_MIGRATED;
            psi_ttwu_dequeue(p);
            set_task_cpu(p, cpu);
        }

    #else /* CONFIG_SMP */

        if (p->in_iowait) {
            delayacct_blkio_end(p);
            atomic_dec(&task_rq(p)->nr_iowait);
        }

    #endif /* CONFIG_SMP */

        ttwu_queue(p, cpu, wake_flags);
    unlock:
        raw_spin_unlock_irqrestore(&p->pi_lock, flags);
    out:
        if (success)
            ttwu_stat(p, cpu, wake_flags);
        preempt_enable();

        return success;
    }

- wake_up_new_task

之前进入睡眠状态的可以通过try_to_wake_up和wake_up_process完成唤醒,而我们fork新创建的进程在完成自己的创建工作后,可以通过wake_up_new_task完成唤醒工作.

- check_preempt_cuur

wake_up_new_task中唤醒进程时,内核使用全局check_preempt_cuur检查是否进程可以抢占当前运行的进程

::

    void check_preempt_curr(struct rq *rq, struct task_struct *p, int flags)
    {
        const struct sched_class *class;

        if (p->sched_class == rq->curr->sched_class) {
            rq->curr->sched_class->check_preempt_curr(rq, p, flags);
        } else {
            for_each_class(class) {
                if (class == rq->curr->sched_class)
                    break;
                if (class == p->sched_class) {
                    resched_curr(rq);
                    break;
                }
            }
        }

        /*
         * A queue event has occurred, and we're going to schedule.  In
         * this case, we can save a useless back to back clock update.
         */
        if (task_on_rq_queued(rq->curr) && test_tsk_need_resched(rq->curr))
            rq_clock_skip_update(rq);
    }
