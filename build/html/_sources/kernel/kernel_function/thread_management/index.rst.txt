Linux内核API之进程管理
========================

数据结构
------------

::

    enum pid_type
    {
        PIDTYPE_PID,    //进程的进程号
        PIDTYPE_PGID,   //进程组领头进程的进程号
        PIDTYPE_SID,    //会话领头进程的进程号
        PIDTYPE_MAX
    };


::

    struct pid_namespace 
    {
        struct kref kref;   //引用计数器，进程每引用一次加1
        struct pidmap pidmap[PIDMAP_ENTRIES];   //记录当前系统的PID使用情况
        struct rcu_head rcu;
        int last_pid;   //记录上一次分配给进程的PID值
        unsigned int nr_hashed;
        struct task_struct *child_reaper;   //保存指向该进程的task_struct值
        struct kmem_cache *pid_cachep;      //指向该进程的cache中分配的空间
        unsigned int level;                 //表示当前命名空间在命名空间层次结构中的深度
        struct pid_namespace *parent;       //指向父命名空间的指针
        #ifdef CONFIG_RPOC_FS
        struct vfsmount *proc_self;
        struct dentry *proc_self;
        struct dentry *proc_thread_self;
        #endif
        #ifdef CONFIG_BSD_PROCESS_ACCT
        struct bsd_acct_struct *bacct;
        #endif
        struct user_namespace *user_ns;
        struct work_struct proc_work;
        kgid_t pid_gid;
        int hide_pid;
        int reboot;
        struct ns_common ns;
    };


::

    struct pid 
    {
        atomic_t count; //使用此进程的任务数量
        unsigned int level; 
        struct hlist_head tasks[PIDTYPE_MAX];
        struct upid numbers[1];
    };


::

    struct mm_struct
    {
        struct vm_area_struct *mmap;    //指向线性区对象的链表头
        struct rb_root mm_rb;
        u32 vmacache_seqnum;    //每一个进程的vmacache大小
        #ifdef CONFIG_MMU
        //在进程地址空间中搜索有效线性地址区间的方法
        unsigned long (*get_unmapped_area)(struct file *filp, unsigned long addr, unsigned long len,
                                unsigned long pgoff, unsigned long flags);
        #endif
        unsigned long mmap_base;    //标识第一个分配的匿名线性区或文件内存映射的线性地址
        unsigned long mmap_legacy_base; //mmap区域自下而上的分配区
        unsigned long task_size;    //在vm空间任务大小
        unsigned long highest_vm_end;   //最大vma的结束地址
        pgd_t *pgd; //指向页全局目录
        atomic_t mm_users;  //次使用计数器
        atomic_t mm_count;  //主使用计数器
        atomic_long_t nr_ptes;  //页表所在的页地址
        int map_count;  //线性区vma的个数
        spinlock_t page_table_lock; //线性区的自旋锁
        struct rw_semaphore mmap_sem;   //线性区的读写信号量
        struct list_head mmlist;    //指向内存描述符链表中的相邻元素
        unsigned long hiwater_rss;
        unsigned long hiwater_vm;

        /*total_vm指进程地址空间的大小(页数)，locked_vm指锁住而不能换出的页的个数
        shared_vm值共享文件内存映射中的页数，exec_vm指可执行内存映射中的页数*/
        unsigned long total_vm, locked_vm, pinned_vm, shared_vm, exec_vm;

        //stack_vm指用户堆栈中的页数
        unsigned long stack_vm, def_flags;

        //start_code指可执行代码的起始地址，end_code指可执行代码的最后地址，
        //start_data指已初始化数据的地址，end_data指已初始化数据的最后地址
        unsigned long start_code, end_code, start_data, end_data;

        //start_brk指堆的起始地址，brk指堆的当前最后地址，start_stack指用于堆栈的起始地址
        unsigned long start_brk, brk, start_stack;

        //命令行参数起止地址，环境变量的起止地址
        unsigned long arg_start, arg_end, env_start, env_end;
        unsigned long saved_auxv[AT_VECTOR_SIZE];   //开始执行ELF程序时使用
        struct mm_rss_stat rss_stat;
        struct linux_binfmt *binfmt;
        cpumask_var_t cpu_vm_mask_var;
        mm_context_t context;   //mm上下文
        unsigned long flags;    
        struct core_state *core_state;
        #ifdef CONFIG_AIO
        spinlock_t ioctx_lock;
        struct kioctx_tabl __rcu *ioctx_table;
        #endif
        #ifdef CONFIG_MEMCG
        struct task_struct __rcu *owner;
        #endif
        struct file *exe_file;
        #ifdef CONFIG_MMU_NOTIFIER
        struct mmu_notifier_mm *mmu_notifier_mm;
        #endif
    }



函数接口
----------

- __task_pid_nr_ns

此函数用于获取进程的进程号，此进程应满足如下约束条件

1. 如果参数type不等于PIDTYPE_PID,则参数task用其所属任务组中的第一个任务赋值，否则保持task不变
2. 此进程是参数task任务描述符中的进程
3. 保证进程进程描述符pid_namespace和参数ns相同

::

    #include <linux/sched.h>
    /*
     * task: 保存任务的基本信息
     * type: pid类型
     * ns: 对进程命名空间信息的描述
     * return: 返回符合条件的进程的进程号
    */
    pid_t __task_pid_nr_ns(struct task_struct *task, enum pid_type type, 
                            struct pid_namespace *ns)


测试代码

::

    static int __init __task_pid_nr_ns_init(void)
    {
        //获取当前进程的进程描述符
        struct pid *kpid = find_get_pid(current->pid);

        //获取进程所属任务的任务描述符
        struct task_struct *task = pid_task(kpid, PIDTYPE_PID);

        //获取任务对应进程的进程描述符
        pid_t ret = __task_pid_nr_ns(task, PIDTYPE_PID, kpid->numbers[kpid->level].ns);

        printk("the pid of find_get_pid is : %d\n", kpid->numbers[kpid->level].nr);
        printk("the result of the __task_pid_nr_ns is : %d\n", ret);
    }


- find_get_pid

该函数根据提供的进程号获取对应的进程描述符，并使进程描述符中的字段count的值加1，即此进程的用户数加1

::

    #include <linux/pid.h>
    /*
     * nr: 进程对应的进程号
     * return: 返回与提供的进程号对应的进程描述符  
    */
    struct pid *find_get_pid(int nr)


- find_pid_ns

该函数获取进程的进程描述符，此进程应满足如下约束条件

1. 进程的进程号和参数nr相同

2. 保证进程描述符的pid_namespace和参数ns相同

::

    #include <linux/pid.h>

    /*
     * nr: 进程描述符对应的进程号
     * ns: 进程命名空间信息描述
     * return: 保存符合条件的进程描述符信息
    */
    struct pid *find_pid_ns(int nr, struct pid_namespace *ns)

测试代码

::

    static int __init find_pid_ns_init(void)
    {
        //获取当前进程的描述符
        struct pid *kpid = find_get_pid(current->pid);
        //获取进程的描述符
        struct pid *fpid = find_pid_ns(kpid->numbers[kpid->level].nr, 
                                       kpid->numbers[kpid->level].ns);

        printk("the find_pid_ns result's count is: %d\n", fpid->count);
        printk("the find_pid_ns result's level is: %d\n", fpid->level);
        printk("the find_pid_ns result's pid is: %d\n", fpid->numbers[fpid->level].nr);
        printk("the pid of current thread is: %d\n", current->pid);
    }


- find_vpid

此函数根据提供的局部进程号获取对应的进程描述符


::

    #include <linux/pid.h>
    /*
     * nr: 进程对应的局部进程号，一般与进程号相同
     * return: 返回进程描述符信息
    */
    struct pid *find_vpid(int nr)


- get_task_mm

此函数根据提供的任务描述符信息，获取其对应的内存信息

::

    #include <linux/sched.h>
    /*
     *  task:　进程的任务描述符信息
     *  return: 返回任务描述符对应的内存信息
    */
    struct mm_struct *get_task_mm(struct task_struct *task)


测试代码


::

    static int __init get_task_mm_init(void)
    {
        //获取当前进程的描述符信息　
        struct pid *kpid = find_get_pid(current->pid);  
        //获取进程任务描述符信息
        struct task_struct *task = pid_task(kpid, PIDTYPE_PID);
        //获取任务的内存描述符
        struct mm_struct *mm_task = get_task_mm(task);

        printk("the mm_users of the mm_struct is: %d\n", mm_task->mm_users);
        printk("the mm_count of the mm_struct is: %d\n", mm_task->mm_count);
        printk("the tgid of the mm_struct is: %d\n", mm_task->owner->tgid);
    }

- ns_of_pid

此函数用于获取进程的命名空间信息


::

    #include <linux/pid.h>
    /*
     * pid: 进程描述符
     * return: 返回进程命名空间信息
    */
    static inline struct pid_namespace *ns_of_pid(struct pid *pid)


- pid_task

此函数用于获取任务的任务描述符信息，此任务在进程pid的使用链表中，并且搜索的链表的起始元素的下标为参数type的值

::

    #include <linux/pid.h>
    /*
     * pid: 进程描述符
     * pid_type: pid类型 
     * return: 返回任务描述
    */
    struct task_struct *pid_task(struct pid *pid, enum pid_type)




