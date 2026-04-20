进程描述
========

进程是出于执行期的程序以及它所管理的资源(如打开的文件、挂起的信号、进程状态、地址空间等等)的总称。
注意，程序不是进程，实际上两个或者多个进程有可能执行同意程序，而且还可能共享地址空间等资源。

linux通过一个被称为进程描述符的 ``task_struct`` 结构体来管理进程，这个结构体包含了一个进程所需要的所有信息. 它定义在 ``include/linux/sched.h`` 文件中

进程状态
--------

::

    volatitle long state;   /* -1 unrunnable, 0 runnable, > 0 stopped */

state成员可能取值如下

::

    /*
     * Task state bitmask. NOTE! These bits are also
     * encoded in fs/proc/array.c: get_task_state().
     *
     * We have two separate sets of flags: task->state
     * is about runnability, while task->exit_state are
     * about the task exiting. Confusing, but this way
     * modifying one set can't modify the other one by
     * mistake.
     */

    /* Used in tsk->state: */
    #define TASK_RUNNING			0x0000
    #define TASK_INTERRUPTIBLE		0x0001
    #define TASK_UNINTERRUPTIBLE		0x0002
    #define __TASK_STOPPED			0x0004
    #define __TASK_TRACED			0x0008
    /* Used in tsk->exit_state: */
    #define EXIT_DEAD			0x0010
    #define EXIT_ZOMBIE			0x0020
    #define EXIT_TRACE			(EXIT_ZOMBIE | EXIT_DEAD)
    /* Used in tsk->state again: */
    #define TASK_PARKED			0x0040
    #define TASK_DEAD			0x0080
    #define TASK_WAKEKILL			0x0100
    #define TASK_WAKING			0x0200
    #define TASK_NOLOAD			0x0400
    #define TASK_NEW			0x0800
    #define TASK_STATE_MAX			0x1000


state域能够取5个互为排斥的值,系统中的每个进程都必然处于以上所列进程状态中的一中。


+-------------------------+-----------------------------------------------------------------------+
|                         |                                                                       |
|  state                  |                     描述                                              |
+=========================+=======================================================================+
|                         |  表示进程要么正在执行或者已经就绪，正在等待cpu时间片的调度            |
|                         |                                                                       |
| TASK_RUNNING            |                                                                       |
+-------------------------+-----------------------------------------------------------------------+
|                         |   进程因为等待一些条件而被挂起(阻塞)而处的状态，这些条件主要包括硬    |
|                         |   中断、资源、信号...，一旦等待的条件成立，进程就会从该状态迅速转换   |
| TASK_INTERRUPTIBLE      |   为TASK_RUNNING                                                      |
+-------------------------+-----------------------------------------------------------------------+
|                         |   意义与TASK_INTERRUPTIBLE类似,不同的是中断、信号不能唤醒它们，只能   |
|                         |   在它所等待的资源可用的时候，才会被唤醒。                            |
| TASK_UNINTERRUPTIBLE    |                                                                       |
+-------------------------+-----------------------------------------------------------------------+
|                         |   进程被停止执行，当进程收到SIGSTOP SIGTTIN SIGTSTP或者SIGTOU 信号    |
|  TASK_STOPPED           |   之后就会进入该状态                                                  |
|                         |                                                                       |
+-------------------------+-----------------------------------------------------------------------+
|                         |   进程被debugger等进程监视                                            |
|  TASK_TRACED            |                                                                       |
|                         |                                                                       |
+-------------------------+-----------------------------------------------------------------------+

- 2个中止状态

只有当进程终止的时候才会达到这两种状态

::

    int exit_state;
    int exit_code, exit_signal;

当进程被终止时,其父进程还没有使用wait()等系统调用来获取它的终止信息,此时进程称为僵尸进程    ``EXIT_ZOMBIE``

进程的最终状态 ``EXIT_DEAD``

- 睡眠状态

TASK_INTERRUPTBLTE 和 TASK_UNINTERRUPTBLTE 这两种状态都属于睡眠状态.

linux内核提供了两种方法将进程置为睡眠状态

1)  如果进程处于可中断模式的睡眠状态,那么可以通过显示的唤醒(wakeup_process())或需要处理的信号来唤醒它

2)  如果进程处于非可中断模式的睡眠状态，那么只能通过显示的唤醒呼叫将其唤醒,除非万不得已否则不建议将进程置为不可中断睡眠模式


内核中还有一种新的睡眠状态, ``TASK_KILLABLE``

它的运行原理与 TASK_UNINTERRUPTIBLE 类似，只不过可以响应致命信号

::

    /* Convenience macros for the sake of set_current_state: */
    #define TASK_KILLABLE			(TASK_WAKEKILL | TASK_UNINTERRUPTIBLE)
    #define TASK_STOPPED			(TASK_WAKEKILL | __TASK_STOPPED)
    #define TASK_TRACED			(TASK_WAKEKILL | __TASK_TRACED)

    #define TASK_IDLE			(TASK_UNINTERRUPTIBLE | TASK_NOLOAD)



进程描述符
----------

::

    pid_t pid;
    pid_t tgid;

unix系统通过pid来标识进程,linux把不同的pid与系统中每个进程或轻量级线程关联,一个线程所有线程与领头线程具有相同的pid，存入tgid字段，getpid()返回当前进程的tgid
而不是pid的值

::

    #define PID_MAX_DEFAULT (CONFIG_BASE_SMALL ? 0x1000 : 0x8000)
    #define PID_MAX_LIMIT (CONFIG_BASE_SMALL ? PAGE_SIZE * 8 : \
                            (sizeof(long) > 4 ? 4 * 1024 * 1024 : PID_MAX_DEFAULT))


进程内核栈
----------

:: 
    
    void *stack;

内核栈与线程描述符
^^^^^^^^^^^^^^^^^^

对于每个进程，linux内核把两个不同的数据结构紧凑的存放在一个单独为进程分配的内存区域中

1) 一个是内核态的进程堆栈

2)另一个是紧挨着进程描述符的小数据结构 ``thread_info`` ,叫做线程描述符

linux把 thread_info 和内核态的线程堆栈放在一起，这块区域通常是8192(占两个页框)，其实地址必须是8192的整数倍

内核太的进程访问处于内核数据段的栈,这个栈不同于用户态的进程所用的栈.用户态的进程所用的栈,是在进程线性地址空间中。而内核栈是当前进程从用户空间进入内核空间时，
特权级别发生变化需要切换堆栈，那么内空间中使用的就是这个内核栈


内核栈数据接哦古描述thread_info和thread_union
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

thread_info是体系结构相关的,结构的定义在thread_info.h中， arm64体系结构中位于arch/arm64/include/asm/thread_info.h

::

    /*
     * low level task data that entry.S needs immediate access to.
     */
    struct thread_info {
        unsigned long		flags;		/* low level flags */
        mm_segment_t		addr_limit;	/* address limit */
    #ifdef CONFIG_ARM64_SW_TTBR0_PAN
        u64			ttbr0;		/* saved TTBR0_EL1 */
    #endif
        union {
            u64		preempt_count;	/* 0 => preemptible, <0 => bug */
            struct {
    #ifdef CONFIG_CPU_BIG_ENDIAN
                u32	need_resched;
                u32	count;
    #else
                u32	count;
                u32	need_resched;
    #endif
            } preempt;
        };
    };

linux 内核中使用一个联合体来表示一个进程的线程描述符和内核栈

::

    union thread_union {
    #ifndef CONFIG_ARCH_TASK_STRUCT_ON_STACK
        struct task_struct task;
    #endif
    #ifndef CONFIG_THREAD_INFO_IN_TASK
        struct thread_info thread_info;
    #endif
        unsigned long stack[THREAD_SIZE/sizeof(long)];
    };

- 获取当前CPU上正在运行进程的thread_info

进程最常用的是进程描述符结构task_struct而不是thread_info结构的地址，为了获取当前CPU上运行进程的task_struct结构，内核提供了current宏,由于task_struct task 在thread_info的起始位置，该宏
本质上current_thread_info()->task 


::

    static __always_inline struct task_struct *get_current(void)
    {
        unsigned long sp_el0;

        asm ("mrs %0, sp_el0" : "=r" (sp_el0));

        return (struct task_struct *)sp_el0;
    }

    #define current get_current()
    
    #define current_thread_info() ((struct thread_info *)current)

- 分配和销毁thread_info

进程通过alloc_thread_info_node函数分配它的内核栈，通过free_thread_info函数释放所分配的内核栈

::

    static struct kmem_cache *thread_stack_cache;

    static unsigned long *alloc_thread_stack_node(struct task_struct *tsk,
                              int node)
    {
        unsigned long *stack;
        stack = kmem_cache_alloc_node(thread_stack_cache, THREADINFO_GFP, node);
        tsk->stack = stack;
        return stack;
    }

    static void free_thread_stack(struct task_struct *tsk)
    {
        kmem_cache_free(thread_stack_cache, tsk->stack);
    }

    void thread_stack_cache_init(void)
    {
        thread_stack_cache = kmem_cache_create_usercopy("thread_stack",
                        THREAD_SIZE, THREAD_SIZE, 0, 0,
                        THREAD_SIZE, NULL);
        BUG_ON(thread_stack_cache == NULL);
    }


进程标记
---------

::
    unsigned int flags; 

反应进程状态信息，但不是运行状态，用于内核识别进程当前状态，以备下一步操作

flags成员可能取值如下,这些以PF(processflag)开头

::

    /*
     * Per process flags
     */
    #define PF_IDLE			0x00000002	/* I am an IDLE thread */
    #define PF_EXITING		0x00000004	/* Getting shut down */
    #define PF_VCPU			0x00000010	/* I'm a virtual CPU */
    #define PF_WQ_WORKER		0x00000020	/* I'm a workqueue worker */
    #define PF_FORKNOEXEC		0x00000040	/* Forked but didn't exec */
    #define PF_MCE_PROCESS		0x00000080      /* Process policy on mce errors */
    #define PF_SUPERPRIV		0x00000100	/* Used super-user privileges */
    #define PF_DUMPCORE		0x00000200	/* Dumped core */
    #define PF_SIGNALED		0x00000400	/* Killed by a signal */
    #define PF_MEMALLOC		0x00000800	/* Allocating memory */
    #define PF_NPROC_EXCEEDED	0x00001000	/* set_user() noticed that RLIMIT_NPROC was exceeded */
    #define PF_USED_MATH		0x00002000	/* If unset the fpu must be initialized before use */
    #define PF_USED_ASYNC		0x00004000	/* Used async_schedule*(), used by module init */
    #define PF_NOFREEZE		0x00008000	/* This thread should not be frozen */
    #define PF_FROZEN		0x00010000	/* Frozen for system suspend */
    #define PF_KSWAPD		0x00020000	/* I am kswapd */
    #define PF_MEMALLOC_NOFS	0x00040000	/* All allocation requests will inherit GFP_NOFS */
    #define PF_MEMALLOC_NOIO	0x00080000	/* All allocation requests will inherit GFP_NOIO */
    #define PF_LESS_THROTTLE	0x00100000	/* Throttle me less: I clean memory */
    #define PF_KTHREAD		0x00200000	/* I am a kernel thread */
    #define PF_RANDOMIZE		0x00400000	/* Randomize virtual address space */
    #define PF_SWAPWRITE		0x00800000	/* Allowed to write to swap */
    #define PF_MEMSTALL		0x01000000	/* Stalled due to lack of memory */
    #define PF_UMH			0x02000000	/* I'm an Usermodehelper process */
    #define PF_NO_SETAFFINITY	0x04000000	/* Userland is not allowed to meddle with cpus_mask */
    #define PF_MCE_EARLY		0x08000000      /* Early kill for mce process policy */
    #define PF_MEMALLOC_NOCMA	0x10000000	/* All allocation request will have _GFP_MOVABLE cleared */
    #define PF_FREEZER_SKIP		0x40000000	/* Freezer should not count it as freezable */
    #define PF_SUSPEND_TASK		0x80000000      /* This thread called freeze_processes() and should not be frozen */

表示进程亲属关系的成员
----------------------

::
    
    
	/* Real parent process: */
	struct task_struct __rcu	*real_parent;

	/* Recipient of SIGCHLD, wait4() reports: */
	struct task_struct __rcu	*parent;

	/*
	 * Children/sibling form the list of natural children:
	 */
	struct list_head		children;
	struct list_head		sibling;
	struct task_struct		*group_leader;


linux 系统中所有进程之间都直接或者间接的存在关系

+-----------------+----------------------------------------------------------------------------------------------------+
|  字段           |                                       描述                                                         |
+=================+====================================================================================================+
|  real_patent    |   指向父进程,如果创建它的父进程不存在了则指向PID为1的init进程                                      |
+-----------------+----------------------------------------------------------------------------------------------------+
|  parent         |   指向父进程，当它终止时，必须向它的父进程发送信号,一般与real_parent相同                           |
+-----------------+----------------------------------------------------------------------------------------------------+
|  children       |   表示链表的头部，链表中的所有元素都是它的子进程                                                   |
+-----------------+----------------------------------------------------------------------------------------------------+
|  sibling        |   用于吧当前进程插入到兄弟链表中                                                                   |
+-----------------+----------------------------------------------------------------------------------------------------+
|  group_leader   |   指向其所在进程组的领头进程                                                                       |
+-----------------+----------------------------------------------------------------------------------------------------+


优先级
------

::

	int				prio;
	int				static_prio;
	int				normal_prio;
	unsigned int			rt_priority;


实时优先级的范围时0-MAX_RT_PRIO-1(即99)，而普通进程的静态优先级范围时MAX_RT_PRIO到MAX_PRIO-1(即100-139),
值越大优先级越低

+----------------+-----------------------------------------------------------------------------+
|   字段         |                          描述                                               |
+================+=============================================================================+
|   static_prio  |  用于保存静态优先级,可以通过nice系统调用来进行修改                          |
+----------------+-----------------------------------------------------------------------------+
|   prio         |  用于保存动态优先级                                                         |
+----------------+-----------------------------------------------------------------------------+
|   normal_pro   |  normal_prio的值取决于静态优先级和调度策略                                  |
+----------------+-----------------------------------------------------------------------------+
|   rt_priority  |  用于保存实时优先级                                                         |
+----------------+-----------------------------------------------------------------------------+

::

    /**
     * task_nice - return the nice value of a given task.
     * @p: the task in question.
     *
     * Return: The nice value [ -20 ... 0 ... 19 ].
     */
    static inline int task_nice(const struct task_struct *p)
    {
        return PRIO_TO_NICE((p)->static_prio);
    }


prio定义如下

::

    #define MAX_NICE    19
    #define MIN_NICE    -20
    #define NICE_WIDTH  (MAX_NICE - MIN_NICE + 1)

    #define MAX_USER_RT_PRIO    100
    #define MAX_RT_PRIO     MAX_USER_RT_PRIO
    #define DEFAULT_PRIO        (MAX_RT_PRIO + NICE_WIDTH / 2)


调度策略相关字段
----------------

::

	unsigned int			policy;
	cpumask_t			cpus_mask;

	const struct sched_class	*sched_class;
	struct sched_entity		se;
	struct sched_rt_entity		rt;
	struct sched_dl_entity		dl;

各字段定义如下

+--------------------+-----------------------------------------------------------------------+
| 字段               |                       描述                                            |
+====================+=======================================================================+
| polocy             | 调度策略                                                              |
+--------------------+-----------------------------------------------------------------------+
| sched_class        | 调度类                                                                |
+--------------------+-----------------------------------------------------------------------+
| se                 | 普通进程的调用实体,每个进程都有其中之一的实体                         |
+--------------------+-----------------------------------------------------------------------+
| rt                 | 实时进程的调度实体                                                    |
+--------------------+-----------------------------------------------------------------------+
| dl                 |                                                                       |
+--------------------+-----------------------------------------------------------------------+
| cpus_allowed       | 用于控制进程可以在那个CPU上运行                                       |
+--------------------+-----------------------------------------------------------------------+

policy表示调度策略,目前主要有以下5种

::

    /*
     * Scheduling policies
     */
    #define SCHED_NORMAL		0
    #define SCHED_FIFO		1
    #define SCHED_RR		2
    #define SCHED_BATCH		3
    /* SCHED_ISO: reserved but not implemented yet */
    #define SCHED_IDLE		5
    #define SCHED_DEADLINE		6

调度策略描述如下

+------------------+----------------------------------------------------------------------------------------------+---------+
| 字段             |                          描述                                                                | 调度器  |
+==================+==============================================================================================+=========+
| SCHED_NORMAL     | 用于普通进程,通过CFS调度器实现                                                               | cfs     |
|                  |                                                                                              |         |
+------------------+----------------------------------------------------------------------------------------------+---------+
| SCHED_BATCH      | SCHED_NORMAL普通进程的分化版本,采用分时策略,根据动态优先级,分配CPU运算资源.                  | cfs     |
|                  |                                                                                              |         |
+------------------+----------------------------------------------------------------------------------------------+---------+
| SCHED_IDLE       | 优先级最低，只有在系统空闲时才跑这类进程                                                     | cfs     |
|                  |                                                                                              |         |
+------------------+----------------------------------------------------------------------------------------------+---------+
| SCHED_FIFO       | 先入先出(实时调度策略),相同优先级的先到先服务，高优先级的可以抢占低优先级的任务              | rt      |
|                  |                                                                                              |         |
+------------------+----------------------------------------------------------------------------------------------+---------+
| SCHED_RR         | 轮流调度算法(实时调度策略),采用时间片，相同优先级的当用完时间片以后会被放到队列尾部,以保证   | rt      |
|                  | 公平性,高优先级的可以抢占低优先级的                                                          |         |
+------------------+----------------------------------------------------------------------------------------------+---------+
| SCHED_DEADLINE   | 新支持的实时进程调度策略,针对突发型计算,且对延迟和完成时间高度敏感的任务适用.                |         |
|                  |                                                                                              |         |
+------------------+----------------------------------------------------------------------------------------------+---------+


调度类
------

::

    extern const struct sched_class stop_sched_class;
    extern const struct sched_class dl_sched_class;
    extern const struct sched_class rt_sched_class;
    extern const struct sched_class fair_sched_class;
    extern const struct sched_class idle_sched_class;

    
进程地址空间
------------

::

	struct mm_struct		*mm;
	struct mm_struct		*active_mm;

	/* Per-thread vma caching: */
	struct vmacache			vmacache;


+-----------------------+-----------------------------------------------------------------------------------------------------+
| 字段                  |                                          描述                                                       |
+=======================+=====================================================================================================+
| mm                    | 进程所用于的用户地址空间描述符,内核线程mm为NULL                                                     |
+-----------------------+-----------------------------------------------------------------------------------------------------+
| active_mm             | 普通进程与mm的值相同,内核线程时被初始化为前一个运行进程的active_mm的值                              |
+-----------------------+-----------------------------------------------------------------------------------------------------+
| vmacache              |                                                                                                     |
+-----------------------+-----------------------------------------------------------------------------------------------------+

如果当前内核线程被调度之前运行的是另外一个内核线程的时候,那么mm和active_mm都是NULL

判断标志
--------

::

	int				exit_state;
	int				exit_code;
	int				exit_signal;
	/* The signal sent when the parent dies: */
	int				pdeath_signal;
	/* JOBCTL_*, siglock protected: */
	unsigned long			jobctl;

	/* Used for emulating ABI behavior of previous Linux versions: */
	unsigned int			personality;

	/* Scheduler bits, serialized by scheduler locks: */
	unsigned			sched_reset_on_fork:1;
	unsigned			sched_contributes_to_load:1;
	unsigned			sched_migrated:1;
	unsigned			sched_remote_wakeup:1;

	/* Force alignment to the next boundary: */
	unsigned			:0;

	/* Unserialized, strictly 'current' */

	/* Bit to tell LSMs we're in execve(): */
	unsigned			in_execve:1;
	unsigned			in_iowait:1;


各字段描述如下

+-----------------------+-----------------------------------------------------------------------------------------------------+
| 字段                  |                                          描述                                                       |
+=======================+=====================================================================================================+
| exit_code             | 用于设置进程的终止代号,要么是_exit()系统调用参数(正常终止)或者是内核提供的错误代号(异常终止)        |
+-----------------------+-----------------------------------------------------------------------------------------------------+
| exit_signal           | 只有当线程组的最后与i个成员终止时,才会产生一个信号,以通知线程组的领头进程的父进程                   |
+-----------------------+-----------------------------------------------------------------------------------------------------+
| pdeath_signal         | 用于判断父进程终止时发送信号                                                                        |
+-----------------------+-----------------------------------------------------------------------------------------------------+
| persionality          | 用于处理不通的ABI                                                                                   |
+-----------------------+-----------------------------------------------------------------------------------------------------+
| in_iowait             | 用于判断是否进行iowait计数                                                                          |
+-----------------------+-----------------------------------------------------------------------------------------------------+
| sched_reset_on_fork   | 用于判断是否恢复默认的优先级或者调度策略                                                            |
+-----------------------+-----------------------------------------------------------------------------------------------------+

时间
----

::

	u64				utime;
	u64				stime;
    u64				utimescaled;
    u64				stimescaled;
    u64				gtime;
    struct prev_cputime		prev_cputime;

	unsigned long			nvcsw;
	unsigned long			nivcsw;

	u64				start_time;

	u64				real_start_time;
 
         
+-----------------------+-----------------------------------------------------------------------------------------------------+
| 字段                  |                                          描述                                                       |
+=======================+=====================================================================================================+
| utime/stime           | 用于记录进程在用户态/内核态下所经过的节拍数字(定时器)                                               |
+-----------------------+-----------------------------------------------------------------------------------------------------+
| utimescaled           | 用于记录进程在用户态的运行时间,但以处理器的频率为刻度                                               |
+-----------------------+-----------------------------------------------------------------------------------------------------+
| gtime                 | 以节拍技术的虚拟机运行时间(guest time)                                                              |
+-----------------------+-----------------------------------------------------------------------------------------------------+
| vncsw/nivcsw          | 自愿和非自愿的上下文切换计数                                                                        |
+-----------------------+-----------------------------------------------------------------------------------------------------+
| start_time/real_s_t   | 进程创建时间,real_start_time包含了进程睡眠时间,常用于/proc/pid/stat                                 |
+-----------------------+-----------------------------------------------------------------------------------------------------+

信号处理
--------

::


	/* Signal handlers: */
	struct signal_struct		*signal;
	struct sighand_struct		*sighand;
	sigset_t			blocked;
	sigset_t			real_blocked;
	/* Restored if set_restore_sigmask() was used: */
	sigset_t			saved_sigmask;
	struct sigpending		pending;
	unsigned long			sas_ss_sp;
	size_t				sas_ss_size;
	unsigned int			sas_ss_flags;


+-----------------------+-----------------------------------------------------------------------------------------------------+
| 字段                  |                                          描述                                                       |
+=======================+=====================================================================================================+
| signal                | 指向进程的信号描述符                                                                                |
+-----------------------+-----------------------------------------------------------------------------------------------------+
| sighand               | 指向进程的信号处理程序描述符                                                                        |
+-----------------------+-----------------------------------------------------------------------------------------------------+
| blocked               | 表示被阻塞信号的掩码,real_blocked 表示临时掩码                                                      |
+-----------------------+-----------------------------------------------------------------------------------------------------+
| pending               | 存放私有挂起信号的数据结构                                                                          |
+-----------------------+-----------------------------------------------------------------------------------------------------+
| sas_ss_sp             | 是信号处理程序备用堆栈的地址,sas_ss_size表示堆栈的大小                                              |
+-----------------------+-----------------------------------------------------------------------------------------------------+

其他
----

::

    spinlock_t alloc_lock;      //用于保护资源分配或者释放的自旋锁
    atomic_t usage;     //进程描述符使用计数,被置为2时,表示进程描述符正在被使用而且其相应的进程处于活动状态
    struct sched_info sched_info;       //用于调度器统计进程的运行信息
    struct list_head tasks;     //用于构建进程链表
    int link_count, total_link_count;
    struct fs_struct *fs;   //fs用来表示进程与文件系统的联系,包括当前目录和根目录
    struct files_struct *files; //files表示进程打开的文件
    struct sysv_sem sysvsem;    //进程通信(SYSVIPC)
    struct thread_struct thread;        //处理器特有数据
    struct nsproxy *nsproxy;            //命名空间
    struct bio_list *bio_list;      //块设备链表
    struct io_context *io_context;      //I/O调度器所使用的信息


