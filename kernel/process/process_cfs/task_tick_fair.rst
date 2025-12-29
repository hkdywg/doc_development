task_tick_fair周期性调度器
==========================

主调度器schedule在选择最优的进程抢占处理器的时候，通过__schedule调用全局的pick_next_task函数,在全局的pick_next_task函数中，按照stop > dl > rt > cfs > idle的顺序依次
从各个调度器类中pick_next函数，从而选择一个最优的进程

周期性调度器的工作由scheduler_tick函数完成(定义在kernel/sched/core.c)在scheduler_tick中周期性调度器通过调用curr进程所属调度器类sched_class的task_tick函数完成周期性调度的工作

CFS的周期性调度
----------------

task_tick_fair与周期性调度
^^^^^^^^^^^^^^^^^^^^^^^^^^

CFS完全公平调度器类通过task_tick_fair函数完成周期性调度的工作

::

    static void task_tick_fair(struct rq *rq, struct task_struct *curr, int queued)
    {
        struct cfs_rq *cfs_rq;
        struct sched_entity *se = &curr->se;    /获取当前进程curr所在的调度实体

        for_each_sched_entity(se) {     //在不支持组调度的条件下只循环一次，在组调度的条件下调度实体存在层次关系,更新子调度实体时必须更新父调度实体
            cfs_rq = cfs_rq_of(se);     //获取当前运行进程所在的cfs就绪队列
            entity_tick(cfs_rq, se, queued);    //完成周期性调度
        }

        if (static_branch_unlikely(&sched_numa_balancing))
            task_tick_numa(rq, curr);

        update_misfit_status(curr, rq);
        update_overutilized_status(task_rq(curr));
    }

entity_tick函数
^^^^^^^^^^^^^^^^^^

::

    static void
    entity_tick(struct cfs_rq *cfs_rq, struct sched_entity *curr, int queued)
    {
        /*
         * Update run-time statistics of the 'current'.
         */
        update_curr(cfs_rq);    //更新统计量

        /*
         * Ensure that runnable average is periodically updated.
         */
        update_load_avg(cfs_rq, curr, UPDATE_TG);   //更新load
        update_cfs_group(curr);

    #ifdef CONFIG_SCHED_HRTICK
        /*
         * queued ticks are scheduled to match the slice, so don't bother
         * validating it and just reschedule.
         */
        if (queued) {
            resched_curr(rq_of(cfs_rq));
            return;
        }
        /*
         * don't let the period tick interfere with the hrtick preemption
         */
        if (!sched_feat(DOUBLE_TICK) &&
                hrtimer_active(&rq_of(cfs_rq)->hrtick_timer))
            return;
    #endif

        if (cfs_rq->nr_running > 1)     //如果进程的数目不少于两个,则由check_preempt_tick作出决策
            check_preempt_tick(cfs_rq, curr);
    }

check_preempt_tick函数
^^^^^^^^^^^^^^^^^^^^^^

check_preempt_tick函数的目的在于，判断是否需要抢占当前进程,确保没有哪个进程能够比延迟周期中确定的份额运行的更长,该份额对应的实际运行时间长度在sched_clice中计算。
进程在CPU上实际运行的时间由sum_exec_runtime - prev_sum_exec_runtime给出

因此抢占决策很容易做出决定，如果检查发现当前进程运行需要被抢占,那么通过resched_task发出重调度请求，这会在task_struct中设置TIF_NEED_RESCHED标志，核心调度器会在下一个适当的时机发起重调度

其实需要抢占的条件有下面两种可能性

- curr进程实际运行时间比期望的运行时间长,此时说明curr已经运行了足够长的时间

- curr进程与红黑树中最左进程Left虚拟运行时间各差值大于curr的期望运行时间

::

    static void
    check_preempt_tick(struct cfs_rq *cfs_rq, struct sched_entity *curr)
    {
        unsigned long ideal_runtime, delta_exec;
        struct sched_entity *se;
        s64 delta;

        ideal_runtime = sched_slice(cfs_rq, curr);  //计算curr的理论上的运行时间
        delta_exec = curr->sum_exec_runtime - curr->prev_sum_exec_runtime;      //计算curr的实际运行时间
        if (delta_exec > ideal_runtime) {       //如果实际运行时间比理论上运行时间要长,说明curr进程已经运行了足够长的时间,应该调度新的进程抢占CPU了
            resched_curr(rq_of(cfs_rq));
            /*
             * The current task ran long enough, ensure it doesn't get
             * re-elected due to buddy favours.
             */
            clear_buddies(cfs_rq, curr);
            return;
        }

        /*
         * Ensure that a task that missed wakeup preemption by a
         * narrow margin doesn't have to wait for a full slice.
         * This also mitigates buddy induced latencies under load.
         */
        if (delta_exec < sysctl_sched_min_granularity)
            return;

        se = __pick_first_entity(cfs_rq);
        delta = curr->vruntime - se->vruntime;  //计算红黑树最左端节点与curr进程的虚拟运行时间差值

        if (delta < 0)
            return;

        if (delta > ideal_runtime)
            resched_curr(rq_of(cfs_rq));    //设置重调度表示TIF_NEDD_RESCHED
    }


周期性调度器不显式的进行调度,而是采用延迟调度的策,如果发现需要抢占,周期性调度器就设置进程的重调度标识TIF_NEED_RESCHED然后由主调度器完成调度工作

.. note::
    TIF_NEED_RESCHED标识表明进程需要被调度，TIF前缀表明这是一个存储在进程thread_info中flag字段的一个标识信息.在内核的关键位置，会检查当前进程是否设置了重调度标志TIF_NEED_RESCHE


