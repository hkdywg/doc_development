linux进程调度器的设计
======================

调度器使用一系列数据结构来排序和管理系统中的进程,调度器的工作方式和这些数据紧密相关

task_struct中调度相关成员
-------------------------

::

    struct task_struct
    {
        ......
        int on_rq;          //表示是否在运行队列

        /*  进程优先级
            * prio: 动态优先级,范围为100~139,与静态优先级和补偿(bonus)有关
            * static_prio: 静态优先级, static_prio = 100 + nice + 20 (nice值为-20~19所以static_prio值为100-139)
            * normal_prio: 没有受优先级继承影响的常规优先级,具体见normal_prio函数,跟属于什么类型的进程有关
        */
        int prio, static_prio, normal_prio;

        unsigned int rt_priority;   //实时进程优先级

        const struct sched_class *sched_class;          //调度类,调度处理函数类

        struct sched_entity se; //调度实体(红黑树的一个结点)

        struct sched_rt_entity rt;
        struct sched_dl_entity dl;

        #ifdef CONFIG_CGROUP_SCHED
            struct task_group *sched_task_group;    //指向所在进程组
        #endif
    }

优先级
^^^^^^^

static_prio: 用于保存静态优先级，是进程启动时分配的优先级，可以通过nice或者sched_setcheduler系统调用来修改,否则在进程运行期间会一直保持恒定

prio:   保存进程的动态优先级

normal_prio:    表示基于进程的静态优先级和调度策略计算出的优先级,因此即使普通进程和实时进程具有相同的静态优先级，其普通优先级也是不同的,进程fork时,子进程会继承父进程的普通优先级

rt_priority:    用于保存实时优先级


0-99    实时进程
100-139 非实时进程

调度策略
^^^^^^^^

::

    /*
     * Scheduling policies
     */
    #define SCHED_NORMAL		0
    #define SCHED_FIFO		1
    #define SCHED_RR		2
    #define SCHED_BATCH		3   //用于非交互的处理器消耗型进程
    /* SCHED_ISO: reserved but not implemented yet */
    #define SCHED_IDLE		5
    #define SCHED_DEADLINE		6


SCHED_BATCH用于非交互，CPU使用密集型的批处理进程，调度决策对此类进程给与"冷处理"。他们绝不会抢占CF调度器处理另一个进程,因此不会干扰交互式进程.如果打算使用nice值降低
进程的静态优先级,同时又不希望该进程影响系统的交互性,此时最适合使用该调度类

.. note::
    注意
    尽管名称是SCHED_IDLE但是SCHED_IDLE不负责调度空闲进程,空闲进程由内核提供单独的机制来处理

调度类
^^^^^^

sched_class结构体表示调度类,类提供了通用调度器和各个调度器之间的关联,调度器类和特定数据结构中汇集的几个函数指针表示，全局调度器请求的各个操作都可以用一个指针表示，
这使得无需了解调度类内部工作原理即可创建通用调度器,定义在kernel/sched/sched.h

::

    struct sched_class {
        //系统中多个调度类,按照其调度的优先级排成一个链表，指向下一优先级的调度类
        //调度类优先级顺序:stop_sched_class > dl_sched_class > rt_sched_class > fair_sched_class > idle_sched_class
        const struct sched_class *next;

    #ifdef CONFIG_UCLAMP_TASK
        int uclamp_enabled;
    #endif
    
        //将进程加入到运行队列中,即将调度实体(进程)放入红黑树中,并对nr_running变量加一
        void (*enqueue_task) (struct rq *rq, struct task_struct *p, int flags);
        //从运行队列中删除进程，并对nr_running变量减一
        void (*dequeue_task) (struct rq *rq, struct task_struct *p, int flags);
        //放弃CPU在compat_yield sysctl关闭的情况下，该函数实际上执行先出队后入队,在这种情况下，它将调度实体放在红黑树的最右端
        void (*yield_task)   (struct rq *rq);
        bool (*yield_to_task)(struct rq *rq, struct task_struct *p, bool preempt);
        //检查当前进程是否可被新进程抢占,在实际抢占正在运行的任务之前,CFS调度程序模块将执行公平性测试
        void (*check_preempt_curr)(struct rq *rq, struct task_struct *p, int flags);

        /*
         * Both @prev and @rf are optional and may be NULL, in which case the
         * caller must already have invoked put_prev_task(rq, prev, rf).
         *
         * Otherwise it is the responsibility of the pick_next_task() to call
         * put_prev_task() on the @prev task or something equivalent, IFF it
         * returns a next task.
         *
         * In that case (@rf != NULL) it may return RETRY_TASK when it finds a
         * higher prio class has runnable tasks.
         */
         //选择下一个应该要运行的进程运行
        struct task_struct * (*pick_next_task)(struct rq *rq,
                               struct task_struct *prev,
                               struct rq_flags *rf);
        //将进程放回运行队列
        void (*put_prev_task)(struct rq *rq, struct task_struct *p);
        void (*set_next_task)(struct rq *rq, struct task_struct *p, bool first);

    #ifdef CONFIG_SMP
        int (*balance)(struct rq *rq, struct task_struct *prev, struct rq_flags *rf);
        //为进程选择一个合适的CPU
        int  (*select_task_rq)(struct task_struct *p, int task_cpu, int sd_flag, int flags);
        //迁移任务到另外一个CPU
        void (*migrate_task_rq)(struct task_struct *p, int new_cpu);

        //用于进程唤醒
        void (*task_woken)(struct rq *this_rq, struct task_struct *task);

        //修改进程的CPU亲和力
        void (*set_cpus_allowed)(struct task_struct *p,
                     const struct cpumask *newmask);

        //启动运行队列
        void (*rq_online)(struct rq *rq);
        //禁止运行队列
        void (*rq_offline)(struct rq *rq);
    #endif

        /在每次激活周期调度器时,由周期性调度器使用,该函数通常调用自time tick函数,它可能引起进程切换
        void (*task_tick)(struct rq *rq, struct task_struct *p, int queued);
        //在进程创建时调用,不同调度策略的进程初始化不一样
        void (*task_fork)(struct task_struct *p);
        //进程退出时调用
        void (*task_dead)(struct task_struct *p);

        /*
         * The switched_from() call is allowed to drop rq->lock, therefore we
         * cannot assume the switched_from/switched_to pair is serliazed by
         * rq->lock. They are however serialized by p->pi_lock.
         */
         //用于进程切换
        void (*switched_from)(struct rq *this_rq, struct task_struct *task);
        void (*switched_to)  (struct rq *this_rq, struct task_struct *task);
        //改变优先级
        void (*prio_changed) (struct rq *this_rq, struct task_struct *task,
                      int oldprio);

        unsigned int (*get_rr_interval)(struct rq *rq,
                        struct task_struct *task);

        void (*update_curr)(struct rq *rq);

    #define TASK_SET_GROUP		0
    #define TASK_MOVE_GROUP		1

    #ifdef CONFIG_FAIR_GROUP_SCHED
        void (*task_change_group)(struct task_struct *p, int type);
    #endif
    };

对于每个调度器类，都必须提供struct sched_class的一个实例,目前内核中由实现以下五种

::

    //优先级最高的线程，会中断其他线程，且不会被其他任务打断
    //1.发生在cpu_stop_cpu_callback进行cpu之间任务migration 2.HOTPLUG_CPU的情况下关闭任务
    extern const struct sched_class stop_sched_class;
    //
    extern const struct sched_class dl_sched_class;
    //实时任务
    extern const struct sched_class rt_sched_class;
    //CFS(公平调度器),作用于一般常规线程
    extern const struct sched_class fair_sched_class;
    //每个CPU的第一个pid=0线程：swapper,是一个静态线程,调度类属于idle_sched_class
    extern const struct sched_class idle_sched_class;


SCHED_NORMAL, SCHED_BATCH, SCHED_IDLE被映射到fail_sched_class

SCHED_RR和SCHED_FIFO则与rt_schedule_class相关联

就绪队列
^^^^^^^^

就绪队列是核心调度器用于管理活动进程的主要数据结构

每个CPU都有自身的就绪队列,各个活动进程只出现在一个就绪队列中，在多个CPU上同时运行一个进程是不可能的.就绪队列是全局调度器许多操作的起点，但是进程并不是就绪队列直接管理的
调度管理是各个调度器的职责,因此在各个就绪队列中潜入了特定调度类的子就绪队列(cfs的顶级调度就绪队列 struct cfs_rq, 实时调度类的就绪队列 struct rt_rq和deadline调度类的就绪队列
struct dl_rq)

在调度时，调度器首先会西安去实时进程队列找是否由实时进程需要运行,如果没有才回去CFS运行队列去找是否由需要运行的,这就是为什么实时进程比普通进程优先级高.不仅仅体现在prio优先级上,还
体现在调度器设计上


就绪队列用struct rq来表示,其定义在kernel/sched/sched.h

::

    /* * This is the main, per-CPU runqueue data structure.
     *
     * Locking rule: those places that want to lock multiple runqueues
     * (such as the load balancing or the thread migration code), lock
     * acquire operations must be ordered by ascending &runqueue.
     */
     //每个处理器都会配备一个rq
    struct rq {
        /* runqueue lock: */
        raw_spinlock_t		lock;

        /*
         * nr_running and cpu_load should be in the same cacheline because
         * remote CPUs use both these fields when doing load calculation.
         */
         //用来记录目前处理器rq中执行task的数量
        unsigned int		nr_running;
    #ifdef CONFIG_NUMA_BALANCING
        unsigned int		nr_numa_running;
        unsigned int		nr_preferred_running;
        unsigned int		numa_migrate_on;
    #endif
    #ifdef CONFIG_NO_HZ_COMMON
    #ifdef CONFIG_SMP
        unsigned long		last_load_update_tick;
        unsigned long		last_blocked_load_update_tick;
        unsigned int		has_blocked_load;
    #endif /* CONFIG_SMP */
        unsigned int		nohz_tick_stopped;
        atomic_t nohz_flags;
    #endif /* CONFIG_NO_HZ_COMMON */
        //在每次scheduler tick中呼叫update_cpu_load时，这个值会增加一,用来更新cpu load更新的次数
        unsigned long		nr_load_updates;
        //用来累加处理器进行context switch的次数,会在调用schedule时进行累加，并可以通过函数nr_context_switches统计目前所有处理器总共的
        //context switch次数,或者可以通过/proc/stat中得知目前整个系统触发context switch的次数
        u64			nr_switches;

    #ifdef CONFIG_UCLAMP_TASK
        /* Utilization clamp values based on CPU's RUNNABLE tasks */
        struct uclamp_rq	uclamp[UCLAMP_CNT] ____cacheline_aligned;
        unsigned int		uclamp_flags;
    #define UCLAMP_FLAG_IDLE 0x01
    #endif

        struct cfs_rq		cfs;    //为cfs fair scheduling class的rq就绪队列
        struct rt_rq		rt;     //为real-time scheduling class的rq就绪队列
        struct dl_rq		dl;     //为dead-line scheduling class的rq就绪队列

    #ifdef CONFIG_FAIR_GROUP_SCHED
        /* list of leaf cfs_rq on this CPU: */
        //在有设置fair group scheduling的环境下,会基于原本cfs rq中包含有若干task的group所成的集合，也就是说当有一个group就会有自己的cfs rq用来排成自己所属的tasks
        //而属于这group的tasks所使用到的处理器时间就会以这group总共所分的时间为上限
        //基于cgoup的fair group scheduling架构,可以创造出有阶层性的task组织,根据不同的task的功能群组化再配置给该群组对应的处理器资源,
        struct list_head	leaf_cfs_rq_list;
        struct list_head	*tmp_alone_branch;
    #endif /* CONFIG_FAIR_GROUP_SCHED */

        /*
         * This is part of a global counter where only the total sum
         * over all CPUs matters. A task can increase this counter on
         * one CPU and if it got migrated afterwards it may decrease
         * it on another CPU. Always updated under the runqueue lock:
         */
         //一般来说,linux kernel的task状态可以为TASK_RUNNING  TASK_INTERRUPTIBLE(sleep) TASK_UNINTERRUPTIBLE(deactivate task)   TASK_STOPPED
         //通过这个变量会统计目前rq中有多少个task属于TASK_UNINTERRUPTIBLE状态，当调用active_tas时，会把nr_uninterruptible的值减一
        unsigned long		nr_uninterruptible;

        struct task_struct	*curr;      //指向目前处理器正在执行的task
        struct task_struct	*idle;      //指向属于idle-task scheduling class的idle task
        struct task_struct	*stop;      //指向目前最高等级属于stop-task scheduling class的task
        unsigned long		next_balance;   //基于处理器的jiffies的值,用以记录下次进行处理器的balancing的时间点
        struct mm_struct	*prev_mm;   //用以存储context-switch发生时,前一个task的memory management结构并可用在函数finish_task_switch透过函数mmdrop释放前一个task的结构体资源

        unsigned int		clock_update_flags;
        u64			clock;      //用以记录目前rq的clock值,基本上该值会等于sched_clock_cpu(cpu_of(rq))的返回值,并会在每次调用scheduler_tick时通过函数update_rq_clock更新目前rq clock值
                            
        /* Ensure that all clocks are in the same cache line */
        u64			clock_task ____cacheline_aligned;
        u64			clock_pelt;
        unsigned long		lost_idle_time;
        //用以记录目前rq中有多少个task处于等待i/o的sleep状态,在实际的使用上，例如当driver接受来自task的调用,但处于等待i/o回复的阶段时,为了充分利用处理器的执行资源，这时就可以在driver中
          调用io_schedule，此时就会把目前rq中的nr_iowait加一并把目前task的io_wait设置为1,然后触发scheduling让其他task有机会可以得到处理器执行时间
        atomic_t		nr_iowait;

    #ifdef CONFIG_MEMBARRIER
        int membarrier_state;
    #endif

    #ifdef CONFIG_SMP
    //root domain是基于多核心架构下的机制,会由rq结构记住目前采用的root domain,其中包括了目前的cpu mask(包括span, online rt overload),reference count 和 cpupri
        struct root_domain		*rd;
        struct sched_domain __rcu	*sd;

        unsigned long		cpu_capacity;
        unsigned long		cpu_capacity_orig;

        struct callback_head	*balance_callback;

        unsigned char		idle_balance;

        unsigned long		misfit_task_load;

        //当rq中此值为1,表示rq正在进行,
        /* For active balancing */
        int			active_balance;
        int			push_cpu;
        struct cpu_stop_work	active_balance_work;

        /* CPU of this runqueue: */
        int			cpu;    //用来记录rq的处理器ID
        int			online; //为1表示目前此rq有在对应的处理器上并执行

        struct list_head cfs_tasks;

        struct sched_avg	avg_rt; //这个值用来统计real-time task执行时间的均值,dleta_exec = rq->clock_task - curr->se.exec_start.在通过函数sched_rt_avg_update把这个
                                    //delta值跟rq中的avg_rt值取平均值,以运行周期来看,这个值可反应目前系统中real-time task平均分配到的执行时间
        struct sched_avg	avg_dl;
    #ifdef CONFIG_HAVE_SCHED_AVG_IRQ
        struct sched_avg	avg_irq;
    #endif
        u64			idle_stamp;     //这个值主要在sched_avg_update更新
        u64			avg_idle;       

        /* This is used to determine avg_idle's max value */
        u64			max_idle_balance_cost;
    #endif

    #ifdef CONFIG_IRQ_TIME_ACCOUNTING
        u64			prev_irq_time;
    #endif
    #ifdef CONFIG_PARAVIRT
        u64			prev_steal_time;
    #endif
    #ifdef CONFIG_PARAVIRT_TIME_ACCOUNTING
        u64			prev_steal_time_rq;
    #endif

        /* calc_load related fields */
        unsigned long		calc_load_update;   //用来记录下一次计算cpu load的时间
        long			calc_load_active;

    #ifdef CONFIG_SCHED_HRTICK
    #ifdef CONFIG_SMP
        int			hrtick_csd_pending;
        call_single_data_t	hrtick_csd;
    #endif
        struct hrtimer		hrtick_timer;
    #endif

    #ifdef CONFIG_SCHEDSTATS
        /* latency stats */
        struct sched_info	rq_sched_info;
        unsigned long long	rq_cpu_time;
        /* could above be rq->cfs_rq.exec_clock + rq->rt_rq.rt_runtime ? */

        /* sys_sched_yield() stats */
        unsigned int		yld_count;

        /* schedule() stats */
        unsigned int		sched_count;        //统计触发scheduling的次数
        unsigned int		sched_goidle;       //统计进入idle task的次数

        /* try_to_wake_up() stats */
        unsigned int		ttwu_count;     //统计wake up task次数
        unsigned int		ttwu_local;     //统计wake wp同一个处理器task的次数
    #endif

    #ifdef CONFIG_SMP
        struct llist_head	wake_list;
    #endif

    #ifdef CONFIG_CPU_IDLE
        /* Must be inspected within a rcu lock section */
        struct cpuidle_state	*idle_state;
    #endif
    };


内核中也提供了一些宏,用来获取cpu上的就绪队列的信息

::

    #define cpu_rq(cpu)		(&per_cpu(runqueues, (cpu)))
    #define this_rq()		this_cpu_ptr(&runqueues)
    #define task_rq(p)		cpu_rq(task_cpu(p))
    #define cpu_curr(cpu)		(cpu_rq(cpu)->curr)
    #define raw_rq()		raw_cpu_ptr(&runqueues)


- CFS公平调度器的就绪队列

在系统中至少有一个CFS运行队列,其就是根cfs运行队列，而其他的进程组和进程都包含在此运行队列中，不同的进程组又有他自己的cfs运行队列，其运行队列包含的是此进程组中的所有进程.
当调度器从根cfs运行队列中选择一个进程组进行调度时,进程组会从自己的cfs运行队列中选择一个调度实体进程调度(这个调度实体可能为进程也可能是一个子进程组),就这样一直深入,知道最后
选出一个进程运行位置

::

    /* CFS-related fields in a runqueue */
    //CFS调度的运行队列，每个cpu的rq会包含一个cfs_rq,而每个组调度的sched_entity也会有自己的一个cfs_rq队列
    struct cfs_rq {
        struct load_weight	load;   //cfs运行队列中所有进程的总负载
        unsigned long		runnable_weight;
        unsigned int		nr_running; //调度的实体数量
        unsigned int		h_nr_running;      /* SCHED_{NORMAL,BATCH,IDLE} */  //只对进程组有效
        unsigned int		idle_h_nr_running; /* SCHED_IDLE */

        u64			exec_clock;
        u64			min_vruntime;   //当前cfs队列上最小运行时间,单调递增,两种情况下会更新该值1.更新当前运行任务的累计运行时间2.当任务从队列删除,如任务睡眠或者退出,
                                    //这时候查看剩下的任务的vruntime是否大于min_vruntime如果是则更新该值
    #ifndef CONFIG_64BIT
        u64			min_vruntime_copy;
    #endif

        struct rb_root_cached	tasks_timeline;         //该红黑树的root

        /*
         * 'curr' points to currently running entity on this cfs_rq.
         * It is set to NULL otherwise (i.e when none are currently running).
         */
        struct sched_entity	*curr;
        struct sched_entity	*next;
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


- 实时进程就绪队列rt_rq

::


    /* Real-Time classes' related field in a runqueue: */
    struct rt_rq {
        struct rt_prio_array	active;
        unsigned int		rt_nr_running;
        unsigned int		rr_nr_running;
    #if defined CONFIG_SMP || defined CONFIG_RT_GROUP_SCHED
        struct {
            int		curr; /* highest queued rt task prio */
    #ifdef CONFIG_SMP
            int		next; /* next highest */
    #endif
        } highest_prio;
    #endif
    #ifdef CONFIG_SMP
        unsigned long		rt_nr_migratory;
        unsigned long		rt_nr_total;
        int			overloaded;
        struct plist_head	pushable_tasks;

    #endif /* CONFIG_SMP */
        int			rt_queued;

        int			rt_throttled;
        u64			rt_time;
        u64			rt_runtime;
        /* Nests inside the rq lock: */
        raw_spinlock_t		rt_runtime_lock;

    #ifdef CONFIG_RT_GROUP_SCHED
        unsigned long		rt_nr_boosted;

        struct rq		*rq;
        struct task_group	*tg;
    #endif
    };

- deadline就绪队列dl_rq

::


    /* Deadline class' related fields in a runqueue */
    struct dl_rq {
        /* runqueue is an rbtree, ordered by deadline */
        struct rb_root_cached	root;

        unsigned long		dl_nr_running;

    #ifdef CONFIG_SMP
        /*
         * Deadline values of the currently executing and the
         * earliest ready task on this rq. Caching these facilitates
         * the decision whether or not a ready but not running task
         * should migrate somewhere else.
         */
        struct {
            u64		curr;
            u64		next;
        } earliest_dl;

        unsigned long		dl_nr_migratory;
        int			overloaded;

        /*
         * Tasks on this rq that can be pushed away. They are kept in
         * an rb-tree, ordered by tasks' deadlines, with caching
         * of the leftmost (earliest deadline) element.
         */
        struct rb_root_cached	pushable_dl_tasks_root;
    #else
        struct dl_bw		dl_bw;
    #endif
        /*
         * "Active utilization" for this runqueue: increased when a
         * task wakes up (becomes TASK_RUNNING) and decreased when a
         * task blocks
         */
        u64			running_bw;

        /*
         * Utilization of the tasks "assigned" to this runqueue (including
         * the tasks that are in runqueue and the tasks that executed on this
         * CPU and blocked). Increased when a task moves to this runqueue, and
         * decreased when the task moves away (migrates, changes scheduling
         * policy, or terminates).
         * This is needed to compute the "inactive utilization" for the
         * runqueue (inactive utilization = this_bw - running_bw).
         */
        u64			this_bw;
        u64			extra_bw;

        /*
         * Inverse of the fraction of CPU utilization that can be reclaimed
         * by the GRUB algorithm.
         */
        u64			bw_ratio;
    };


调度实体
^^^^^^^^

调度器不限于调度进程,还可以调度更大的实体，比如实现组调度.

::

    //一个调度实体(红黑树的一个结点)，其包含一组或一个指定进程,包含一个自己的运行队列,一个父指针，一个指向需要调度的运行队列
    struct sched_entity {
        /* For load-balancing: */
        struct load_weight		load;       //权重,在数组prio_to_weight包含优先级转权重的数值
        unsigned long			runnable_weight;
        struct rb_node			run_node;   //实体在红黑树对应的结点信息
        struct list_head		group_node; //实体所在的进程组
        unsigned int			on_rq;      //实体是否处于红黑树运行队列中

        u64				exec_start;         //开始运行时间
        u64				sum_exec_runtime;   //累计运行时间
        u64				vruntime;           //虚拟运行时间，在时间中断或者任务状态发生改变时会更新,其会不停的增长，增长速度与load权重成反比,load越高增长速度越慢
                                            //就越可能处于红黑树最左边被调度,每次时钟中断都会修改其值
        u64				prev_sum_exec_runtime;  //进程在切换进CPU时的sum_exec_runtime值

        u64				nr_migrations;  //此调度实体中进程移到其他CPU组的数量

        struct sched_statistics		statistics;

    #ifdef CONFIG_FAIR_GROUP_SCHED
        int				depth;  //代表进程组的深度,每个进程组都比其parent调度组深度大1
        struct sched_entity		*parent;    //父调度实体指针
        /* rq on which this entity is (to be) queued: */
        struct cfs_rq			*cfs_rq;    //实体所处的红黑树运行队列
        /* rq "owned" by this entity/group: */
        struct cfs_rq			*my_q;  //NULL表示是一个进程,非NULL则表明是一个调度组
    #endif

    #ifdef CONFIG_SMP
        /*
         * Per entity load average tracking.
         *
         * Put into separate cache line so it does not
         * collide with read-mostly values above.
         */
        struct sched_avg		avg;
    #endif
    };

- 实时进程调度实体sched_rt_entity

::

    struct sched_rt_entity {
        struct list_head		run_list;
        unsigned long			timeout;
        unsigned long			watchdog_stamp;
        unsigned int			time_slice;
        unsigned short			on_rq;
        unsigned short			on_list;

        struct sched_rt_entity		*back;
    #ifdef CONFIG_RT_GROUP_SCHED
        struct sched_rt_entity		*parent;
        /* rq on which this entity is (to be) queued: */
        struct rt_rq			*rt_rq;
        /* rq "owned" by this entity/group: */
        struct rt_rq			*my_q;
    #endif
    } __randomize_layout;

- edf调度实体sched_dl_entity

::

    struct sched_dl_entity {
        struct rb_node			rb_node;

        /*
         * Original scheduling parameters. Copied here from sched_attr
         * during sched_setattr(), they will remain the same until
         * the next sched_setattr().
         */
        u64				dl_runtime;	/* Maximum runtime for each instance	*/
        u64				dl_deadline;	/* Relative deadline of each instance	*/
        u64				dl_period;	/* Separation of two instances (period) */
        u64				dl_bw;		/* dl_runtime / dl_period		*/
        u64				dl_density;	/* dl_runtime / dl_deadline		*/

        /*
         * Actual scheduling parameters. Initialized with the values above,
         * they are continuously updated during task execution. Note that
         * the remaining runtime could be < 0 in case we are in overrun.
         */
        s64				runtime;	/* Remaining runtime for this instance	*/
        u64				deadline;	/* Absolute deadline for this instance	*/
        unsigned int			flags;		/* Specifying the scheduler behaviour	*/

        /*
         * Some bool flags:
         *
         * @dl_throttled tells if we exhausted the runtime. If so, the
         * task has to wait for a replenishment to be performed at the
         * next firing of dl_timer.
         *
         * @dl_boosted tells if we are boosted due to DI. If so we are
         * outside bandwidth enforcement mechanism (but only until we
         * exit the critical section);
         *
         * @dl_yielded tells if task gave up the CPU before consuming
         * all its available runtime during the last job.
         *
         * @dl_non_contending tells if the task is inactive while still
         * contributing to the active utilization. In other words, it
         * indicates if the inactive timer has been armed and its handler
         * has not been executed yet. This flag is useful to avoid race
         * conditions between the inactive timer handler and the wakeup
         * code.
         *
         * @dl_overrun tells if the task asked to be informed about runtime
         * overruns.
         */
        unsigned int			dl_throttled      : 1;
        unsigned int			dl_boosted        : 1;
        unsigned int			dl_yielded        : 1;
        unsigned int			dl_non_contending : 1;
        unsigned int			dl_overrun	  : 1;

        /*
         * Bandwidth enforcement timer. Each -deadline task has its
         * own bandwidth to be enforced, thus we need one timer per task.
         */
        struct hrtimer			dl_timer;

        /*
         * Inactive timer, responsible for decreasing the active utilization
         * at the "0-lag time". When a -deadline task blocks, it contributes
         * to GRUB's active utilization until the "0-lag time", hence a
         * timer is needed to decrease the active utilization at the correct
         * time.
         */
        struct hrtimer inactive_timer;
    };

组调度(struct task_group)
^^^^^^^^^^^^^^^^^^^^^^^^^^^


linux是一个多用户系统，如果有两个进程分别属于两个用户，而进程的优先级不同，会导致两个用户所占用的CPU时间不同,这显然是不公平的(如果优先级差距过大,低优先级进程所属用户使用CPU时间就很小),所以内核
引入组调度。如果基于用户分组,即使进程优先级不同,这两个用户使用的CPU时间都为50%

如果task_group中的运行时间还没有使用完，而当前进程运行时间使用完后,会调度task_group中下一个被调度进程,相反,如果task_group的运行时间使用结束,则调用上一层的下一个被调度进程.需要注意的是,一个组
调度中可能有一部分是实时进程，一部分是普通进程,这也导致这种组要能够满足既能在实时调度中进行调度又可以在CFS调度中被调度

linux可以用两种方式进行进程的分组

1)  用户ID:按照进程的USER ID进行分组,在对应的/sys/kernel/uid目录下会生成一个cpu.share的文件,可以通过配置该文件来配置用户所占CPU的时间比例

2)  cgroup(control group):生成组用于限制其所有进程，比如我生成一个组(生成后此组为空,里面没有进程),设置其CPU使用率为10%并把一个进程丢进这个组中，那么这个进程最多只能使用CPU的10%,如果将多个进程丢进这个
组,则这个组中的所有进程平分这10%


::

    /* Task group related information */
    struct task_group {
        struct cgroup_subsys_state css;

    #ifdef CONFIG_FAIR_GROUP_SCHED
        /* schedulable entities of this group on each CPU */
        struct sched_entity	**se;
        /* runqueue "owned" by this group on each CPU */
        struct cfs_rq		**cfs_rq;
        unsigned long		shares;

    #ifdef	CONFIG_SMP
        /*
         * load_avg can be heavily contended at clock tick time, so put
         * it in its own cacheline separated from the fields above which
         * will also be accessed at each tick.
         */
        atomic_long_t		load_avg ____cacheline_aligned;
    #endif
    #endif

    #ifdef CONFIG_RT_GROUP_SCHED
        struct sched_rt_entity	**rt_se;
        struct rt_rq		**rt_rq;

        struct rt_bandwidth	rt_bandwidth;
    #endif

        struct rcu_head		rcu;
        struct list_head	list;

        struct task_group	*parent;
        struct list_head	siblings;
        struct list_head	children;

    #ifdef CONFIG_SCHED_AUTOGROUP
        struct autogroup	*autogroup;
    #endif

        struct cfs_bandwidth	cfs_bandwidth;

    #ifdef CONFIG_UCLAMP_TASK_GROUP
        /* The two decimal precision [%] value requested from user-space */
        unsigned int		uclamp_pct[UCLAMP_CNT];
        /* Clamp values requested for a task group */
        struct uclamp_se	uclamp_req[UCLAMP_CNT];
        /* Effective clamp values used for a task group */
        struct uclamp_se	uclamp[UCLAMP_CNT];
    #endif

    };



