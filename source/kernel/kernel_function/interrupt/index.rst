Linux内核API之中断机制
=========================

__tasklet_hi_schedule
-----------------------

``__tasklet_hi_schedule`` 函数功能描述：其主要作用是将参数t代表的软中断的描述符添加到向量tasklet_hi_vec的尾部，等待获得CPU资源，
被调度执行．tasklet_hi_vec代表高优先级的软中断描述符链表．通过此函数添加的软中断具有较高的优先级，会先被调度执行．

::

    #include <linux/interrupt.h>
    
    //源码位置kernel/softirp.c
    void __tasklet_hi_schedule(struct tasklet_struct *t)

函数输入参数是struct tasklet_struct结构体类型的指针，保存软中断的描述符信息，其定义见文件include/linux/interrupt.h

::

    struct tasklet_struct
    {
        struct tasklet_struct *next;
        unsigned long state;
        atomic_t count;
        void (*func)(unsigned long);
        unsigned long data;
    }


- next: 指向链表的下一个元素

- state: 定义来当前软中断的状态，内核中只使用了bit1和bit0两个状态位．bit1表示当前tasklet正在执行，它仅对SMP系统有意义．bit0=1表示当前tasklet已经被调度，
  等待获得CPU资源执行

::

    enum
    {
        TASKLET_STATE_SCHED,    /*软中断被调度，但未执行*/
        TASKLET_STATE_RUN       /*软中断正在执行*/
    }

- count: 原子计数值，代表当前tasklet的引用计数值，只有当count等于0时，tasklet对应的中断处理函数才能被执行

- func: 函数指针，代表中断的处理函数

- data: 中断处理函数执行时的参数，即字段func执行时的参数


**测试代码**

::

    #include <linux/interrupt.h>
    #include <linux/module.h>
    #include <linux/init.h>

    static unsigned long data = 0x00;
    static struct tasklet_struct tasklet, tasklet_1;

    static void irq_tasklet_action(unsigned long data)
    {
        printk("in irq_tasklet_action the state of tasklet is : %ld\n", (&tasklet)->state);
        printk("tasklet running.\n");
        return;
    }

    static void irq_tasklet_action1(unsigned long data)
    {
        printk("in irq_tasklet_action1 the state of tasklet is : %ld\n", (&tasklet1)->state);
        printk("tasklet1 running.\n");
        return;
    }

    static int __init　__tasklet_hi_schedule_init(void)
    {
        tasklet_init(&tasklet, irq_tasklet_action, data);
        tasklet_init(&tasklet1, irq_tasklet_action1, data);

        printk("in irq_tasklet_action the state of tasklet is : %ld\n", (&tasklet)->state);
        printk("in irq_tasklet_action1 the state of tasklet is : %ld\n", (&tasklet1)->state);

        tasklet_schedule(&tasklet); //将中断送入普通中断队列
        if(!test_and_set_bit(TASKLET_STATE_SCHED, &tasklet1.state))
            __tasklet_hi_schedule(&tasklet1);   //将中断送入高优先级队列

        tasklet_kill(&tasklet);
        tasklet_kill(&tasklet1);
        
        return 0;
    }

    static void __exit __tasklet_hi_schedule_exit(void)
    {
        return;
    }


disable_irq
----------------

``disable_irq`` :此函数在实现过程中先后调用了 ``disable_irq_nosync`` 完成增加中断所处的深度和改变中断的状态,然后调用 ``synchronize_irq`` 使处理器处于
检测中断号所对应的中断状态

::

    #include <linux/interrupt.h>
    //源码位置kernel/irq/manage.c
    void disable_irq(unsigned int irq);
    void disable_irq_nosync(unsigned int irq);
    void enable_irq(unsigned int irq);


**测试代码**

::

    #include <linux/interrupt.h>
    #include <linux/module.h>

    static int ieq = 3;

    static irqreturn_t irq_handler(int data, void *dev_id)
    {
        printk("the data is: %d\n", data);
        
        return IRQ_NONE;
    }

    static int __init disable_irq_nosync_init(void)
    {
        int ret;
        ret = request_irq(irq, irq_handler, IRQF_DISABLE, "A_New_Device", NULL);    //申请一个新的中断
        disable_irq_nosync(irq);    //使中断的深度增加1
        enable_irq(irq);    //使中断的深度减少1,同时触发中断处理函数执行

        printk("the result of rquest_irq is : %d\n", result);

        return 0;
    }

    static void __exit disable_irq_nosync_exit(void)
    {
        free_irq(irq, NULL);
        return;
    }

    module_init(disable_irq_nosync_init);
    module_exit(disable_irq_nosync_exit);


irq_set_chip
---------------

``irq_set_chip`` :此函数是为irq_desc数组中对应下标为irq的元素设定irq_chip的值，如果传入的参数为NULL,则使用系统定义好的no_irq_chip为它赋值．


::

    #include <linux/irq.h>
    //代码位置kernel/irq/chip.c
    int irq_set_chip(unsigned int irq, struct irq_chip *chip)

参数chip是一个struct irq_chip型的结构体变量，是对应的硬件中断的描述符的irq_chip字段的值，定义见include/linux/irq.h中

::

    struct irq_chip {
        const char *name;
        unsigned int (*irq_startup)(struct irq_data *data);
        void (*irq_shutdown)(struct irq_data *data);
        void (*irq_enable)(struct irq_data *data);
        void (*irq_disable)(struct irq_data *data);

        void (*irq_ack)(struct irq_data *data);
        void (*irq_mask)(struct irq_data *data);
        void (*irq_mask_ack)(struct irq_data *data);
        void (*irq_unmask)(struct irq_data *data);
        void (*irq_eoi)(struct irq_data *data);

        void (*irq_set_affinity)(struct irq_data *data, const struct cpumask *dest, bool force);
        void (*irq_retrigger)(struct irq_data *data);
        void (*irq_set_type)(struct irq_data *data, unsigned int flow_type);
        void (*irq_set_wake)(struct irq_data *data, unsigned int on);
        void (*irq_bus_lock)(struct irq_data *data);
        void (*irq_bus_sync_unlock)(struct irq_data *data);

        void (*irq_cpu_online)(struct irq_data *data);
        void (*irq_cpu_offline)(struct irq_data *data);


        void (*irq_suspend)(struct irq_data *data);
        void (*irq_resume)(struct irq_data *data);
        void (*irq_pm_shutdown)(struct irq_data *data);


        void (*irq_calc_mask)(struct irq_data *data);

        void (*irq_print_chip)(struct irq_data *data, struct seq_file *p);
        void (*irq_request_resources)(struct irq_data *data);
        void (*irq_release_resources)(struct irq_data *data);


        void (*irq_compose_msi_msg)(struct irq_data *data, struct msi_msg *msg);
        void (*irq_write_msi_msg)(struct irq_data *data, struct msi_msg *msg);

        ungsigned long flags;
    };

如果传入的参数chip为NULL，则系统用no_irq_chip进行初始化，no_irq_chip的定义见kernel/irq/dummychip.c

::

    struct irq_chip no_irq_chip = { 
        .name = "none",
        .irq_startup = noop_ret,
        .irq_shutdown = noop,
        .irq_enable = noop,
        .irq_disable = noop,
        .irq_ack = ack_bad,
    };

**测试代码**

::

    #include <linux/irq.h>
    #include <linux/interrupt.h>
    #include <linux/module.h>

    static int irq = 4;

    static irqreturn_t irq_handler(int irq, void *dev_id)
    {
        printk("the irq is : %d\n", irq);

        return IRQ_WAKE_THREAD;
    }

    static irqreturn_t irq_thread_fn(int irq, void *dev_id)
    {
        printk("the irq is : %d\n", irq);
        return IRQ_HANDLED;
    }

    static int __init irq_set_chip_init(void)
    {
        request_threaded_irq(irq, irq_handler, irq_thread_fn, IRQF_DISABLED, "A_New_Device", NULL);
        irq_set_chip(irq, NULL);

        return 0;
    }

    static void __exit irq_set_chip_exit(void)
    {
        free_irq(irq, NULL);
        return;
    }

    module_init(irq_set_chip_init);
    module_exit(irq_set_chip_exit);


irq_set_chip_data
---------------------

::

    #include <linux/irq.h>
    //源码位置kernel/irq/chip.c
    int irq_set_chip_data(unsigned int irq, void *data)


- irq: 设备对应的中断号，对应数组irq_desc中元素的下标

- data: 为irq_desc数组中元素的chip字段中的函数体哦嗯一个私有的数据区，以实现chip字段中函数的共享执行

::

    #include <linux/irq.h>
    //源码位置kernel/irq/chip.c
    int irq_set_irq_type(unsigned int irq, unsigned int type)

=================================== ====================================================================
 中断触发类型　                             描述
----------------------------------- --------------------------------------------------------------------
 IRQ_TYPE_NOE                         系统默认，没有明确指明类型的触发模式
 IRQ_TYPE_EDGE_RISING               　上升沿触发
 IRQ_TYPE_EDGE_FAILLING               下降沿触发
 IRQ_TYPE_EDGE_BOTH                   上升沿或下降沿触发
 IRQ_TYPE_LEVEL_HIGH                　高电平触发
 IRQ_TYPE_LEVEL_LOW                 　低电平触发
 IRQ_TYPE_SENSE_MASK                  以上任何一种方式触发
 IRQ_TYPE_DEFAULT                     IRQ_TYPPE_SENSE_MASK以上任何一种方式
=================================== ====================================================================

**测试代码**

::

    #include <linux/irq.h>
    #include <linux/interrupt.h>
    #include <linux/module.h>

    static int irq = 10;

    static irqreturn_t irq_handler(int irq, void *dev_id)
    {
        printk("the irq is : %d\n", irq);

        return IRQ_WAKE_THREAD;
    }

    static irqreturn_t irq_thread_fn(int irq, void *dev_id)
    {
        printk("the irq is : %d\n", irq);

        return IRQ_HANDLED;
    }

    struct chip_data
    {
        int num;
        char *name;
        int flags;
    };

    static int __init irq_set_chip_data_init(void)
    {
        struct chip_data data;
    
        request_threaded_irq(irq, irq_handler, irq_thread_fn, IRQF_DISABLED, "A_New_Device", NULL);
        irq_set_irq_type(irq, IRQ_TYPE_EDGE_BOTH);
        irq_set_chip(irq, NULL);
        irq_set_chip_data(irq, &data);

        return 0;
    }

    static void __exit irq_set_chip_data_exit(void)
    {
        free(irq, NULL);

        return;
    }

    module_init(irq_set_chip_data_init);
    module_exit(irq_set_chip_data_exit);


irq_set_irq_wake
-----------------

``irq_set_irq_wake`` ：此函数用于改变中断的状态及中断的唤醒深度，其对中断状态及中断唤醒深度的影响根据参数on不同会有不同的结果．
如果on为0,函数使中断处于睡眠状态，不能被唤醒，减少中断唤醒深度wake_depth的值，如果on的值为非0,函数将中断从睡眠状态唤醒，使中断处于唤醒状态，
增加其唤醒深度wake_depth的值


::

    #include <linux/interrupt.h>
    //源码位置kernel/irq/manage.c
    int irq_set_irq_wake(unsigned int irq, unsigned int on)


**测试代码**

::

    #include <linux/module.h>
    #include <linux/interrupt.h>

    static int irq = 3;
    static irqreturn_t irq_handler(int data, void *data_id)
    {
        printk("the data is : %d\n", data);

        return IRQ_NONE;
    }

    static int __init irq_set_irq_wake_init(void)
    {
        request_irq(irq, irq_handler, IRQF_DISABLED, "A_New_Device", NULL);

        irq_set_irq_wake(irq, 0);   //使中断处于睡眠状态，减少唤醒深度
        irq_set_irq_wake(irq, 1);   //使中断处于唤醒状态，增加唤醒深度

        return 0;
    }

    static void __exit irq_set_irq_wake_exit(void)
    {
        free_irq(irq, NULL);
        return;
    }

    module_init(irq_set_irq_wake_init);
    module_exit(irq_set_irq_wake_exit);


tasklet_init
---------------

``tasklet_init`` : 用于初始化一个struct tasklet_struct结构体类型的变量，将其state字段及其count字段的值清零，并完成func及data的赋值

::

    #include <linux/interrupt.h>
    //内核源码kernel/softirq.c
    void tasklet_init(struct tasklet_struct *t, void (*func)(unsigned long), unsigned long data)

``tasklet_enable`` :用于减少结构体tasklet_struct中字段count的值，当此字段的值等于0时，相应的软中断被重新使能，对应的中断处理函数能够
被CPU调度执行，处理相应的中断

::

    #include <linux/interrupt.h>
    //内核源码include/linux/interrupt.h
    static inline void tasklet_enable(struct tasklet_struct *t)
    {
        smp_mb_befor_atomic();
        atomic_dec(&t->count);
    }


``tasklet_disable`` :用于增加软中断描述符中count字段的值，使软中断处于睡眠状态，不能响应对应的中断

::

    #include <linux/interrupt.h>
    //内核源码include/linux/interrupt.h
    static inline void tasklet_disable(struct tasklet_struct *t)
    {
        tasklet_disable_nosync(t);
        tasklet_unlock_wait(t);
        smp_mb();
    }

    static inline void tasklet_disable_nosync(struct tasklet_struct *t)
    {
        atomic_inc(&t->count);
        smp_mb_after_atomic_inc();
    }


``tasklet_kill`` :用于阻塞当前线程，等待中断处理函数的执行完毕．此函数通过循环检测中断字段state的值，判断中断处理函数的执行情况，
当中断处理函数执行完毕之后，循环结束，然后将字段state清零


::

    #include <linux/interrupt.h>
    //内核源码kernel/softirq.c
    void tasklet_kill(struct tasklet_struct *t)


``tasklet_trylock`` :返回0表示此中断不可在此CPU上调度

::

    #include <linux/interrupt.h>
    //内核源码include/linux/interrupt.h
    static inline int tasklet_trylock(struct tasklet_struct *t)
    {
        return !test_and_set_bit(TASKLET_STATE_RUN, &(t)->state);
    }


**测试代码**

::

    #include <linux/interrupt.h>
    #include <linux/module.h>
    #include <linux/init.h>

    static unsigned long data = 10;
    static struct tasklet_struct tasklet;

    static void irq_tasklet_action(unsigned long data)
    {
        printk("the data value of tasklet is : %ld\n", (&tasklet)->data);
        return;
    }

    static int __init tasklet_init_init(void)
    {
        if(tasklet.func == NULL) {
            printk("the tasklet has not been initialized!\n");
        }

        tasklet_init(&tasklet, irq_tasklet_action, data);   //初始化一个struct tasklet_struct变量
        printk("the data value of the tasklet is : %ld\n", tasklet.data);

        if(tasklet.func == NULL) {
            printk("the tasklet has not been initialized!\n");
        } else {
            printk("the tasklet has been initialized!\n");
        }

        tasklet_schedule(&tasklet); //把软中断放入调度队列，等待调度执行
        printk("the count value of the tasklet befor tasklet_disable is : %d\n", tasklet.count);
        tasklet_disable(&tasklet); //调用tasklet_disable使tasklet对应的处理函数不能执行
        if(atomic_read(&(tasklet.count)) != 0)  //测试当前count值
            printk("tasklet is disabled.\n");
        printk("the count value of the tasklet after tasklet_disable is : %d\n", tasklet.count);

        tasklet_enable(&tasklet);   //使能tasklet
        if(atomic_read(&(tasklet.count)) == 0)
            printk("tasklet is enabled.\n");

        tasklet_kill(&tasklet); //等待tasklet被调度执行完毕

        return 0;
    }

    static void __exit tasklet_init_exit(void)
    {
        return;
    }

    module_init(tasklet_init_init);
    module_exit(tasklet_init_exit);


request_irq
-------------

``request_irq`` :动态申请注册一个中断

:: 

    #include <linux/interrupt.h>
    //内核源码include/linux/interrupt.h
    static inline int __must_check request_irq(unsigned int irq, irq_handler_t handler,
                unsigned long flags, const char *name, void *dev)
    {
        return request_thread_irq(irq, handler, NULL, flags, name, dev);
    }

    int __must_check request_threaded_irq(unsigned int irq, irq_handler_t handler, irq_handler_t thrad_fn,
        unsigned long flags, const char *name, void *dev);

- irq: 为对应的中断号，系统已用的是0~31,其中IRQ9, IRQ10, IRQ15系统保留，32~16640用于用户定义的中断

- handler: 是对应的中断处理函数，返回值类型是irq_handler_t

::
    
    enum irqreturn {
        IRQ_NONE = (0 << 0),    //中断不是此设备发出
        IRQ_HANDLED = (1 << 0), //中断被此设备处理
        IRQ_WAKE_THREAD = (1 << 1), //中断处理函数需要唤醒中断处理线程


- thread_fn: 对应的中断线程处理函数，如果中断处理函数的返回值是IRQ_WAKE_THREAD,则此时的中断线程处理函数将被调用，此函数是对中断处理函数的补充

- flags: 用来标识中断的类型

::

    #define IRQF_DISABLED           0x00000020  //中断失能
    #define IRQF_SHARED             0x00000080  //设备共享
    #define IRQF_PROBE_SHARED       0x00000100  //错序共享中断
    #define __IRQF_TIMER            0x00000200  //时钟中断
    #define IRQF_PERCPU             0x00000400  //CPU中断
    #define IRQF_NOBALANCING        0x00000800  //中断平衡使能
    #define IRQF_IRQPOLL            0x00001000  //中断轮循检测，用于设备共享的中断
    #define IRQF_ONESHOT            0x00002000  //将中断保持不可用状态，直到中断处理函数结束
    #define IRQF_NO_SUSPEND         0x00004000  //挂起期间不让中断保持不可用状态

    #define IRQF_FORCE_RESUME       0x00008000  //
    #define IRQF_NO_THREAD          0x00010000  //不可中断线程状态
    #define IRQF_EARLY_RESUME       0x00020000  //提起恢复IRQ而不是在设备恢复期间

    #define IRQF_TIMER              (__IRQF_TIMER | IRQF_NO_SUSPEND | IRQF_NO_THREAD)


``remove_irq`` :此函数用于卸载IRQ链表中的与输入参数对应的irqaction描述符

::

    #include <linux/irq.h>
    //内核源码kernel/irq/manage.c
    void remove_irq(unsigned int irq, struct irqcation *act);


- irq: 中断号

- act: 参数act是与系统对应的一个irqaction标识符


::

    struct irqaction {
        irq_hander_t handler;   //中断处理函数
        void *dev_id;           //设备标识符，用于设别设备
        void __percpu *percpu_dev_id;   //设备标识符，用于识别设备
        struct irqaction *next;         //指向中断向量链表中的下一个中断标识符
        irq_handkler_t thread_fn;       //中断线程处理函数
        struct task_struct *thread;     //任务描述符,指向与此中断线程对应的线程
        unsigned int irq;               //中断号
        unsigned int flags;             //中断类型
        unsigned long thread_flags;     //线程标识
        unsigned long thread_mask;      //CPU掩码，表示此中断所在的CPU编号
        const char *name;               //中断标识符对应的设备名
        struct proc_dir_entry *dir;     //目录入口指针，指向在文件夹/proc/irq中与此中断标识符对应的中断号相应的文件夹
    } ___cacheline_internodealinged_in_smp;
        











































