软中断
===========


软中断概述
-----------

中断处理可以分为上半部和下半部，上半部是指中断处理程序，下半部则是指虽然与中断相关但是可以延后执行的任务。这两者的区别是上半部不能被相同类型的中断打断，对时间比较敏感，
而下半部则可以被中断

下半部主要由软中断、tasklet和工作队列机制构成。

软中断特性包括

1. 产生后并不是马上可以运行，必须要等待内核的调度才能执行，软中断不能被自己打断(即单个CPU上软中断不能嵌套执行)，只能被硬件中断打断(上半部)
2. 可以并发运行在多个cpu上(即使同一类型的也可以)，所以软中断必须设计为可重入的函数(允许多个CPU同时操作)，因此也需要使用自旋锁来保其数据结构

软中断类型
^^^^^^^^^^^^^^

系统静态定义了若干软中断类型，内核开发者不希望用户再扩充新的软中断类型，如有需要，建议使用tasklet机制。每一种软中断都是用索引来表示一种相对的优先级，
索引号越小软中断优先级越高，并在一轮软中断处理中得到优先执行

已经定义号的软中断类型如下:

::

	//include/linux/interrupt.h
	enum
	{
			HI_SOFTIRQ=0,   //用于高优先级的tasklet
			TIMER_SOFTIRQ,  //用于定时器的下半部
			NET_TX_SOFTIRQ, //用于网络层的发包
			NET_RX_SOFTIRQ, //用于网络层的收包
			BLOCK_SOFTIRQ,  //用于块设备
			IRQ_POLL_SOFTIRQ,
			TASKLET_SOFTIRQ,    //用于低优先级的tasklet
			SCHED_SOFTIRQ,
			HRTIMER_SOFTIRQ,
			RCU_SOFTIRQ,    /* Preferable RCU should always be the last softirq */

			NR_SOFTIRQS
	};

软中断数据结构
^^^^^^^^^^^^^^^

- struct softirq_action

::

	/* softirq mask and active fields moved to irq_cpustat_t in
	 * asm/hardirq.h to get better cache usage.  KAO
	 */
	struct softirq_action
	{
			void    (*action)(struct softirq_action *); 
	};

用于描述软中断所要执行的回调

::

	static struct softirq_action softirq_vec[NR_SOFTIRQS] __cacheline_aligned_in_smp;

软中断描述符数组softirq_vec[]，类似于硬件中断描述符数据结构irq_desc[],每个软中断类型对应一个描述符，其中软中断的索引就是该数组的索引。
__cacheline_aligned_in_smp用于将softirq_vec数据结构和L1缓存行对齐

- irq_cpustat_t

::

	//include/asm-genegic/hardirq.h
	typedef struct {
		unsigned int __softirq_pending;
	} ____cacheline_aligned irq_cpustat_t;
	

描述软中断状态信息，可以理解为软中断状态寄存器，其成员__softirq_pending的每个bit表示一个软中断类型的状态，置0表示此类型软中断没有触发，置1表示已经触发，需要执行
对应的软中断处理函数

::

	#ifndef __ARCH_IRQ_STAT
	DEFINE_PER_CPU_ALIGNED(irq_cpustat_t, irq_stat);
	EXPORT_PER_CPU_SYMBOL(irq_stat);
	#endif

每个CPU由一个软中断状态信息变量irq_sta(即__softirq_pending), __softirq_pending的每一个bit代表CPU的一个软中断类型


注册软中断
-------------

::
	
	//kernel/softirq.c
	void open_softirq(int nr, void (*action)(struct softirq_action *))
	{
		softirq_vec[nr].action = action;
	}


即注册对应类型的处理函数到全局数组softirq_vec中，例如网络发包对应类型为NET_TX_SOFTIRQ的处理函数net_tx_action

softirq_vec[]是一个多CPU共享的数组，软中断的初始化通常是在系统启动时init函数中完成(如:subsys_initcall(blk_softirq_init)),系统启动时是串行执行的，因此
没有额外的保护机制


触发软中断
-----------

raise_softirq和raise_softirq_irqoff是触发软中断的两个主要接口，注意触发软中断只是将per cpu的irq_stat.__softirq_pending的相应Bit位置位，中断处理退出函数irq_exit
执行软中断才会真正的执行软中断对应的回调action

- raise_softirq

::

	void raise_softirq(unsigned int nr)
    |  //关闭本地中断，实际屏蔽本地CPU的PSTATE的irq bit
    |--local_irq_save(flags);
    |--raise_softirq_irqoff(nr);
    |      |--__raise_softirq_irqoff(nr);
    |      |      |--trace_softirq_raise();
    |      |      |  //实际是置位本地cpu的irq_stat.__softirq_pending的第nr bit
    |      |      |--or_softirq_pending(1UL << nr);
    |      |  //如果不在中断上下文，wakeup_softirqd唤醒本cpu的ksoftirqd线程执行软中断处理函数
    |      |--if (!in_interrupt()) 
    |             |--wakeup_softirqd();
    |--local_irq_restore(flags);


- raise_softirq_irqoff

与raise_softirq的区别是不会主动关闭本地中断

执行中断
------------

::

    handle_domain_irq(struct irq_domain *domain,unsigned int hwirq, struct pt_regs *regs)
    |--__handle_domain_irq(domain, hwirq, true, regs);
           |--unsigned int irq = hwirq;
           |--irq_enter();
           |  //以硬中断号为索引软中断号返回给irq
           |--irq = irq_find_mapping(domain, hwirq);
           |--generic_handle_irq(irq);
           |--irq_exit();


在上述中断处理中，中断处理完成后会调用irq_exit退出中断，在irq_exit中会检查并执行软中断的处理函数，这里要注意软中断处理函数的执行时机，包含三部分

1. 中断返回，在中断上下文，irq_exit会执行各个CPU的__softirq_pending中置位的软中断，运行在中断上下文
2. 如果软中断太多，或耗时太久将会唤醒本地CPU的ksoftirqd线程来执行软中断，运行在进程上下文
3. local_bh_enable中会调用do_softirq执行软中断处理，运行在进程上下文

中断返回
^^^^^^^^^^

::

    //kernel/softirq.c
    /*
     * Exit an interrupt context. Process softirqs if needed and possible:
     */
    void irq_exit(void)
    {
    #ifndef __ARCH_IRQ_EXIT_IRQS_DISABLED
        local_irq_disable();
    #else
        lockdep_assert_irqs_disabled();
    #endif
        account_irq_exit_time(current);
        preempt_count_sub(HARDIRQ_OFFSET);
        if (!in_interrupt() && local_softirq_pending())
            invoke_softirq();

        tick_irq_exit();
        rcu_irq_exit();
        trace_hardirq_exit(); /* must be last! */
    }


::

    static inline void invoke_softirq(void)
    {
            //如果当前有软中断线程正在执行软中断处理，则退出保证软中断执行的串行化
            if (ksoftirqd_running(local_softirq_pending()))
                    return;
            if (!force_irqthreads) {
    #ifdef CONFIG_HAVE_IRQ_EXIT_ON_IRQ_STACK
                    /*
                     * We can safely execute softirq on the current stack if
                     * it is the irq stack, because it should be near empty
                     * at this stage.
                     */
                    __do_softirq();
    #else
                    /*
                     * Otherwise, irq_exit() is called on the task stack that can
                     * be potentially deep already. So call softirq in its own stack
                     * to prevent from any overrun.
                     */
                    //使用被中断进程的内核栈执行
                    do_softirq_own_stack();
    #endif
            } else {
                    wakeup_softirqd();
            }
    }              

::

    do_softirq_own_stack(void)
    |--__do_softirq(void)
            |  //初始化软中断处理的最长时间，如果超过这个时间将唤醒软中断线程进行处理
            |--unsigned long end = jiffies + MAX_SOFTIRQ_TIME;
            |  //初始化软中断处理允许的最大次数
            |--int max_restart = MAX_SOFTIRQ_RESTART;
            |--current->flags &= ~PF_MEMALLOC;
            |  //获取pending的软中断
            |--pending = local_softirq_pending();
            |--account_irq_enter_time(current);
            |  //禁用软中断
            |--__local_bh_disable_ip(_RET_IP_, SOFTIRQ_OFFSET);
            |--in_hardirq = lockdep_softirq_start();
        restart:                      
            |  //Reset the pending bitmask before enabling irqs
            |--set_softirq_pending(0);
            |  //使能cpu中断，实际是清空PSTATE的I位
            |--local_irq_enable();
            |  //softirq_vec为软中断描述符数组，保存了每个软中断的action
            |--h = softirq_vec;
            |--while ((softirq_bit = ffs(pending))
            |       |  //从softirq_vec数组拿到pending的软中断描述符（里面保存了action）
            |       |--h += softirq_bit - 1;
            |       |  //执行软中断处理函数
            |       |--h->action(h);
            |       |--h++;
            |       |--pending >>= softirq_bit//从低位到高位，每处理完一个软中断，需右移
            |--local_irq_disable();
            |--pending = local_softirq_pending();
            |--if (pending)
            |       //如果没有超过软中断处理的最后时间点或没有超过允许的最大次数，可以继续在软中断上下文处理
            |       if (time_before(jiffies, end) && !need_resched() && --max_restart)
            |           goto restart;
            |       //唤醒软中断线程进行处理
            |       wakeup_softirqd();
            |  //重新使能软中断
            |--__local_bh_enable(SOFTIRQ_OFFSET);


ksoftirqd
^^^^^^^^^^^

::

    <kernel/softirq.c>
    static struct smp_hotplug_thread softirq_threads = {
            .store                  = &ksoftirqd,
            .thread_should_run      = ksoftirqd_should_run,
            .thread_fn              = run_ksoftirqd,
            .thread_comm            = "ksoftirqd/%u",
    };

    static __init int spawn_ksoftirqd(void)
    {
            cpuhp_setup_state_nocalls(CPUHP_SOFTIRQ_DEAD, "softirq:dead", NULL,
                                      takeover_tasklets);
            BUG_ON(smpboot_register_percpu_thread(&softirq_threads));

            return 0;
    }
    early_initcall(spawn_ksoftirqd);

ksoftirqd内核线程是在start_kernel初始化时通过spawn_ksoftirqd创建的per cpu线程，通过ps或者top命令可以看到。其中的线程处理函数位run_ksoftirqd

::

    static void run_ksoftirqd(unsigned int cpu)
    {
            local_irq_disable();
            if (local_softirq_pending()) {
                    /*
                     * We can safely run softirq on inline stack, as we are not deep
                     * in the task stack here.
                     */
                    __do_softirq();
                    local_irq_enable();
                    cond_resched();
                    return;
            }
            local_irq_enable();
    }

这里我们看到ksoftirqd线程在执行时是关闭了本地cpu中断的，再一次验证了软中断执行的串行化。这里与invoke_softirq的区别是，invoke_softirq运行再中断上下文，而ksoftirqd运行在进程上下文




























































