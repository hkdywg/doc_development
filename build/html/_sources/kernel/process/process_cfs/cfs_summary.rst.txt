CFS调度器概述
================

cfs调度器类fair_sched_class
------------------------------


CFS完全公平调度器的调度类叫 ``fair_sched_class`` ,其定义在kernel/sched/fair.c中,它是我们熟知的struct sched_class调度器类型

::


    /*
     * All the scheduling class methods:
     */
    const struct sched_class fair_sched_class = {
        .next			= &idle_sched_class,    //下个优先级的调度类,所有的调度类通过next链接在一个链表中
        .enqueue_task		= enqueue_task_fair,    //向就绪队列中添加一个进程,它将调度实体(进程)放入红黑树中,并对nr_running变量加1
        .dequeue_task		= dequeue_task_fair,    //将一个进程从就绪队列中删除
        .yield_task		= yield_task_fair,          //在进程想要资源放弃对处理器的控制权时,可使用sched_yield系统调用
        .yield_to_task		= yield_to_task_fair,

        .check_preempt_curr	= check_preempt_wakeup, //该函数将检查当前运行的任务是否被抢占,在实际抢占正在运行的任务之前,cfs调度器将执行公平性测试,这将驱动唤醒式抢占

        .pick_next_task		= pick_next_task_fair,  //选择接下来要运行的最合适的进程
        .put_prev_task		= put_prev_task_fair,   //用另外一个进程替代当前运行的进程
        .set_next_task          = set_next_task_fair,   //当任务修改其调度类或修改其任务组时,将调用这个函数

    #ifdef CONFIG_SMP
        .balance		= balance_fair,
        .select_task_rq		= select_task_rq_fair,
        .migrate_task_rq	= migrate_task_rq_fair,

        .rq_online		= rq_online_fair,
        .rq_offline		= rq_offline_fair,

        .task_dead		= task_dead_fair,
        .set_cpus_allowed	= set_cpus_allowed_common,
    #endif

        .task_tick		= task_tick_fair,   //在每次激活周期调度器时,由周期性调度器调用,该函数通常调用自time tick函数,它可能引起进程切换,这将驱动运行时抢占
        .task_fork		= task_fork_fair,   //内核调度程序为调度模块提供了管理新任务启动的机会，用于建立fork系统调用和调度器之间的关联,每次新进程建立后，则用new_task通知调度器,cfs使用
                                            //它进行组调度，而用于实时任务的调度模块则不会使用这个函数

        .prio_changed		= prio_changed_fair,
        .switched_from		= switched_from_fair,
        .switched_to		= switched_to_fair,

        .get_rr_interval	= get_rr_interval_fair,

        .update_curr		= update_curr_fair,

    #ifdef CONFIG_FAIR_GROUP_SCHED
        .task_change_group	= task_change_group_fair,
    #endif

    #ifdef CONFIG_UCLAMP_TASK
        .uclamp_enabled		= 1,
    #endif
    };


cfs就绪队列
------------


就绪队列时全局调度器许多操作的起点，但是进程并不是由就绪队列直接管理的,调度管理是各个调度器的职责，因此在各个就绪队列中潜入了特定调度类的子就绪队列(
cfs的顶级调度队列struct cfs_rq,实时调度类的就绪队列struct rt_rq和deadline调度类的就绪队列struct dl_rq)

::

    //cfs调度的运行队列，每个CPU的rq会包含一个cfs_rq，而每个组调度的sched_entity也会有自己的一个cfs_rq队列
    /* CFS-related fields in a runqueue */
    struct cfs_rq {
        struct load_weight	load;   //cfs运行
        unsigned long		runnable_weight;//cfs运行队列中所有进程的总负载
        unsigned int		nr_running; //cfs_rq中调度实体的数量
        unsigned int		h_nr_running;      /* SCHED_{NORMAL,BATCH,IDLE} */  //只对进程组有效
        unsigned int		idle_h_nr_running; /* SCHED_IDLE */

        u64			exec_clock;
        //当前cfs队列上最小运行时间，单调递增
        //两种情况下更新该值
        //1.更新当前运行任务的累计运行时间时
        //2.当任务从队列删除去,如任务睡眠或者退出,这时候会查看剩下的任务的vruntime是否大于min_vruntime，如果是则更新该值
        u64			min_vruntime;
    #ifndef CONFIG_64BIT
        u64			min_vruntime_copy;
    #endif

        struct rb_root_cached	tasks_timeline;     //该红黑树的root

        /*
         * 'curr' points to currently running entity on this cfs_rq.
         * It is set to NULL otherwise (i.e when none are currently running).
         */
        struct sched_entity	*curr;  //当前正在运行的sched_entity(对于组虽然他不会在cpu上运行,但是当它的下层有一个task在cpu上运行,那么它所在的cfs_rq就把它当作是该cfs_rq上当前正在运行的sched_entity)
        struct sched_entity	*next;  //表示有些进程急需运行,即使不遵从cfs调度也必须运行它，调度时会检查是否next需要调度,有就调度next
        struct sched_entity	*last;
        struct sched_entity	*skip;

    #ifdef	CONFIG_SCHED_DEBUG
        unsigned int		nr_spread_over;
    #endif

    #ifdef CONFIG_SMP
        /*
         * CFS load tracking
         */
        struct sched_avg	avg;
    #ifndef CONFIG_64BIT
        u64			load_last_update_time_copy;
    #endif
        struct {
            raw_spinlock_t	lock ____cacheline_aligned;
            int		nr;
            unsigned long	load_avg;
            unsigned long	util_avg;
            unsigned long	runnable_sum;
        } removed;

    #ifdef CONFIG_FAIR_GROUP_SCHED
        unsigned long		tg_load_avg_contrib;
        long			propagate;
        long			prop_runnable_sum;

        /*
         *   h_load = weight * f(tg)
         *
         * Where f(tg) is the recursive weight fraction assigned to
         * this group.
         */
        unsigned long		h_load;
        u64			last_h_load_update;
        struct sched_entity	*h_load_next;
    #endif /* CONFIG_FAIR_GROUP_SCHED */
    #endif /* CONFIG_SMP */

    #ifdef CONFIG_FAIR_GROUP_SCHED
        struct rq		*rq;	/* CPU runqueue to which this cfs_rq is attached */

        /*
         * leaf cfs_rqs are those that hold tasks (lowest schedulable entity in
         * a hierarchy). Non-leaf lrqs hold other higher schedulable entities
         * (like users, containers etc.)
         *
         * leaf_cfs_rq_list ties together list of leaf cfs_rq's in a CPU.
         * This list is used during load balance.
         */
        int			on_list;
        struct list_head	leaf_cfs_rq_list;
        struct task_group	*tg;	/* group that "owns" this runqueue */

    #ifdef CONFIG_CFS_BANDWIDTH
        int			runtime_enabled;
        s64			runtime_remaining;

        u64			throttled_clock;
        u64			throttled_clock_task;
        u64			throttled_clock_task_time;
        int			throttled;
        int			throttle_count;
        struct list_head	throttled_list;
    #endif /* CONFIG_CFS_BANDWIDTH */
    #endif /* CONFIG_FAIR_GROUP_SCHED */
    };
