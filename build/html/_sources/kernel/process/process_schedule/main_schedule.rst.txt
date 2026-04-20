linux进程调度器之主调度器
=========================

内核提供了两个调度器主调度器和周期性调度器,两者合在一起就组成了核心调度器(core scheduler)也叫通用调度器(generic scheduler)

在内核的许多地方，如果要将cpu分配给与当前活动进程不同的另一个进程，都会直接调用主调度器函数schedule. 该函数完成以下工作

schedule函数
------------

::

    asmlinkage __visible void __sched schedule(void)
    {
        struct task_struct *tsk = current;  //获取当前进程

        sched_submit_work(tsk); //避免死锁
        do {
            preempt_disable();  //关闭内核抢占
            __schedule(false);  //完成调度
            sched_preempt_enable_no_resched();  //开启内核抢占
        } while (need_resched());   //如果该进程被其他进程设置了TIF_NEED_RESCHED标志,则函数重新执行调度
        sched_update_worker(tsk);
    }
    EXPORT_SYMBOL(schedule);

.. note::
    #define __sched		__attribute__((__section__(".sched.text")))
    attribute((_section("...")))是gcc的编译属性，其目的在于将相关函数的代码编译之后,放到目标文件的特定段内

::

    static inline void sched_submit_work(struct task_struct *tsk)
    {
        if (!tsk->state) //检测tsk->state是否为0(runnable)，若为运行态时则返回
            return;

        /*
         * If a worker went to sleep, notify and ask workqueue whether
         * it wants to wake up a task to maintain concurrency.
         * As this function is called inside the schedule() context,
         * we disable preemption to avoid it calling schedule() again
         * in the possible wakeup of a kworker.
         */
        if (tsk->flags & PF_WQ_WORKER) {
            preempt_disable();
            wq_worker_sleeping(tsk);
            preempt_enable_no_resched();
        }

        if (tsk_is_pi_blocked(tsk)) //检测tsk的死锁检测器是否为空
            return;

        /*
         * If we are going to sleep and we have plugged IO queued,
         * make sure to submit it to avoid deadlocks.
         */
        if (blk_needs_flush_plug(tsk))  //检测是否刷新plug队列，用来避免死锁
            blk_schedule_flush_plug(tsk);
    }

- 内核抢占

linux除了内核态还有用户态,用户程序的上下文属于用户态,系统调用和中断处理例程上下文属于内核态.如果一个进程在用户态时被其他进程抢占了则发生了用户态抢占,
而如果此时进程进入了内核态，则内核态进程执行，如果此时发生了抢占,我们就说发生了内核抢占

抢占内核的主要特点是：一个在内核态运行的进程,当且仅当在执行内核函数期间被另外一个进程取代.

内核为了支撑内核抢占，提供了很多机制和结构，必要时候开关内核抢占也是必须的,这些函数定义在include/linux/preempt.h

::

    #define preempt_disable() \
    do { \
        preempt_count_inc(); \
        barrier(); \
    } while (0)

    #define sched_preempt_enable_no_resched() \
    do { \
        barrier(); \
        preempt_count_dec(); \
    } while (0)

    #define preempt_enable_no_resched() sched_preempt_enable_no_resched()


__schedule开始进程调度
-----------------------

__schedule完成了真正的调度工作,其定义在 kernel/sched/core.c

::

    static void __sched notrace __schedule(bool preempt)
    {
        struct task_struct *prev, *next;
        unsigned long *switch_count;
        struct rq_flags rf;
        struct rq *rq;
        int cpu;

        //找到当前cpu上的就绪队列rq，并将正在运行的进程curr保存到prev中
        cpu = smp_processor_id();
        rq = cpu_rq(cpu);
        prev = rq->curr;

        //如果禁止内核抢占,而又调用了cond_resched就会出错，这里就是来捕获该错误的
        schedule_debug(prev, preempt);

        if (sched_feat(HRTICK))
            hrtick_clear(rq);

        local_irq_disable(); //关闭本地中断
        rcu_note_context_switch(preempt);   //更新全局状态，标识当前CPU发生上下文切换

        /*
         * Make sure that signal_pending_state()->signal_pending() below
         * can't be reordered with __set_current_state(TASK_INTERRUPTIBLE)
         * done by the caller to avoid the race with signal_wake_up().
         *
         * The membarrier system call requires a full memory barrier
         * after coming from user-space, before storing to rq->curr.
         */
        rq_lock(rq, &rf);
        smp_mb__after_spinlock();

        /* Promote REQ to ACT */
        rq->clock_update_flags <<= 1;
        update_rq_clock(rq);

        switch_count = &prev->nivcsw;   //切换次数记录
        //scheduler检查prev的状态state和内核抢占标识,如果prev是不可运行的,并且内核在内核态没有被抢占
        if (!preempt && prev->state) {
            //如果当前进程有非阻塞等待信号,并且它的状态是TASK_INTERRUPTIBLE,则将进程状态设置为TASK_RUNNING
            if (signal_pending_state(prev->state, prev)) {
                prev->state = TASK_RUNNING;
            } else {
                deactivate_task(rq, prev, DEQUEUE_SLEEP | DEQUEUE_NOCLOCK); //将当前进程从runqueue中删除

                if (prev->in_iowait) {
                    atomic_inc(&rq->nr_iowait);
                    delayacct_blkio_start();
                }
            }
            switch_count = &prev->nvcsw; //获取切换次数
        }

        next = pick_next_task(rq, prev, &rf);   //选出优先级最高的任务
        clear_tsk_need_resched(prev);           //清楚prev的TIF_NEED_RESCHED标志
        clear_preempt_need_resched();           //清除内核抢占标识

        if (likely(prev != next)) { //如果next和prev不是同一个进程
            rq->nr_switches++;  //队列切换次数更新
            /*
             * RCU users of rcu_dereference(rq->curr) may not see
             * changes to task_struct made by pick_next_task().
             */
            RCU_INIT_POINTER(rq->curr, next);   //将next标记为队列的curr进程
            /*
             * The membarrier system call requires each architecture
             * to have a full memory barrier after updating
             * rq->curr, before returning to user-space.
             *
             * Here are the schemes providing that barrier on the
             * various architectures:
             * - mm ? switch_mm() : mmdrop() for x86, s390, sparc, PowerPC.
             *   switch_mm() rely on membarrier_arch_switch_mm() on PowerPC.
             * - finish_lock_switch() for weakly-ordered
             *   architectures where spin_unlock is a full barrier,
             * - switch_to() for arm64 (weakly-ordered, spin_unlock
             *   is a RELEASE barrier),
             */
            ++*switch_count;    //进程上下文切换次数加一

            trace_sched_switch(preempt, prev, next);    //

            /* Also unlocks the rq: */
            rq = context_switch(rq, prev, next, &rf);   //进程之间上下文切换
        } else {
            rq->clock_update_flags &= ~(RQCF_ACT_SKIP|RQCF_REQ_SKIP);
            rq_unlock_irq(rq, &rf);
        }

        balance_callback(rq);
    }

pick_next_task选择抢占的进程
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

内核从cpu的就绪队列中选择一个最合适的进程来抢占CPU

::

    next = pick_next_task(rq);

pick_next_task函数会按照优先级遍历所有调度器类的pick_next_task函数，去查找最优的那个进程,当然大多数情况下，系统中全是CFS调度的非实时进程，因而linux内核也有一些优化的策略.其执行流程如下

1) 如果当前CPU上所有的进程都是cfs调度的普通非实时进程,则直接用cfs调度，如果无程序调度则调度idle进程

2) 否则从优先级最高的调度器类开始遍历

::

    /*
     * Pick up the highest-prio task:
     */
    static inline struct task_struct *
    pick_next_task(struct rq *rq, struct task_struct *prev, struct rq_flags *rf)
    {
        const struct sched_class *class;
        struct task_struct *p;

        /*
         * Optimization: we know that if all tasks are in the fair class we can
         * call that function directly, but only if the @prev task wasn't of a
         * higher scheduling class, because otherwise those loose the
         * opportunity to pull in more work from other CPUs.
         */
         //如果当前所有进程都被cfs调度，没有实时进程
        if (likely((prev->sched_class == &idle_sched_class ||
                prev->sched_class == &fair_sched_class) &&
               rq->nr_running == rq->cfs.h_nr_running)) {       //当前cpu上的就绪队列中进程数与cfs_rq的进程数相等，则说明当前cpu上所有进程都是cfs调度的普通非实时进程
            //调用cfs的选择函数pick_next_task找到最优的那个进程
            p = fair_sched_class.pick_next_task(rq, prev, rf);
            if (unlikely(p == RETRY_TASK))
                goto restart;

            /* Assumes fair_sched_class->next == idle_sched_class */
            if (unlikely(!p))   //如果没有进程可被调度,则调度idle进程
                p = idle_sched_class.pick_next_task(rq, prev, rf);

            return p;
        }

    restart:
    #ifdef CONFIG_SMP
        /*
         * We must do the balancing pass before put_next_task(), such
         * that when we release the rq->lock the task is in the same
         * state as before we took rq->lock.
         *
         * We can terminate the balance pass as soon as we know there is
         * a runnable task of @class priority or higher.
         */
        for_class_range(class, prev->sched_class, &idle_sched_class) {
            if (class->balance(rq, prev, rf))
                break;
        }
    #endif

        put_prev_task(rq, prev);
        //进程中所有的调度器类，通过next域链接在一起的,调度的顺序为stop->dl->rt->fair->idle
        for_each_class(class) {
            p = class->pick_next_task(rq, NULL, NULL);
            if (p)
                return p;
        }

        /* The idle class should always have a runnable task: */
        BUG();
    }

加快经常性事件，是程序开发中一个优化的准则，linux系统中最普遍的进程就是非实时进程，其调度器必然是cfs

likely是gcc内建的一个编译选项，它其实就是告诉编译器表达式很大的情况下为真,编译器可以对此做出优化

::

    
    # ifndef likely
    #  define likely(x)	(__builtin_expect(!!(x), 1))
    # endif
    # ifndef unlikely
    #  define unlikely(x)	(__builtin_expect(!!(x), 0))
    # endif



context_switch进程上下文切换
------------------------------

进程上下文切换
^^^^^^^^^^^^^^^

上下文切换(有时候也称作进程切换或者任务切换)是指CPU从一个进程或线程切换到另一个进程或线程

上下文切换可以认为是内核在CPU上对进程进行以下活动

1) 挂起一个进程，将这个进程在cpu中的状态(上下文)存储在内存中的某处

2) 在内存中检索出下一个进程的上下文并将其在CPU的寄存器中恢复

3) 跳转到程序计数器所指向的位置(即跳转到进程中断时的代码行)，以恢复该进程

因此上下文是指某一时间点CPU寄存器核程序计数器的内容，广义上还包括内存中进程的虚拟地址映射信息

上下文只能发生在内核态中，上下文切换通常是计算密集型的,也就是说他需要相当可观的处理器时间，在每秒几十上百次的切换中，会消耗大量的CPU时间

context_switch流程
^^^^^^^^^^^^^^^^^^^

 ``context_switch`` 函数完成了进程上下文的切换,其定义在 kernel/sched/core.c中


::

    /*
     * context_switch - switch to the new MM and the new thread's register state.
     */
    static __always_inline struct rq *
    context_switch(struct rq *rq, struct task_struct *prev,
               struct task_struct *next, struct rq_flags *rf)
    {
        prepare_task_switch(rq, prev, next);

        /*
         * For paravirt, this is coupled with an exit in switch_to to
         * combine the page table reload and the switch backend into
         * one hypercall.
         */
        arch_start_context_switch(prev);

        /*
         * kernel -> kernel   lazy + transfer active
         *   user -> kernel   lazy + mmgrab() active
         *
         * kernel ->   user   switch + mmdrop() active
         *   user ->   user   switch
         */
        if (!next->mm) {                                // to kernel
            enter_lazy_tlb(prev->active_mm, next);

            next->active_mm = prev->active_mm;
            if (prev->mm)                           // from user
                mmgrab(prev->active_mm);
            else
                prev->active_mm = NULL;
        } else {                                        // to user
            membarrier_switch_mm(rq, prev->active_mm, next->mm);
            /*
             * sys_membarrier() requires an smp_mb() between setting
             * rq->curr / membarrier_switch_mm() and returning to userspace.
             *
             * The below provides this either through switch_mm(), or in
             * case 'prev->active_mm == next->mm' through
             * finish_task_switch()'s mmdrop().
             */
            switch_mm_irqs_off(prev->active_mm, next->mm, next);

            if (!prev->mm) {                        // from kernel
                /* will mmdrop() in finish_task_switch(). */
                rq->prev_mm = prev->active_mm;
                prev->active_mm = NULL;
            }
        }

        rq->clock_update_flags &= ~(RQCF_ACT_SKIP|RQCF_REQ_SKIP);

        prepare_lock_switch(rq, next, rf);

        /* Here we just switch the register state and the stack. */
        switch_to(prev, next, prev);
        barrier();

        return finish_task_switch(prev);
    }


