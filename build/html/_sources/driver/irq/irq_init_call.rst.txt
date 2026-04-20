linux中断初始化和基本调用流程
===============================

这里介绍的是按照ARM平台整理的，ARM64暂时未做整理

irq_usr
--------

正常情况下有两种情况会进入irq模式，一种是usr模式，另一种是svc模式


::

    __irq_usr:
        usr_entry   //保存中断上下文
        irq_handler //中断处理
        get_thread_info tsk //获取保存当前task的地址
        mov	why, #0
        b	ret_to_user_from_irq
     UNWIND(.fnend		)
    ENDPROC(__irq_usr)

    __irq_svc:
        svc_entry
        irq_handler

    #ifdef CONFIG_PREEMPT
        ldr	r8, [tsk, #TI_PREEMPT]		@ get preempt count
        ldr	r0, [tsk, #TI_FLAGS]		@ get flags
        teq	r8, #0				@ if preempt count != 0
        movne	r0, #0				@ force flags to 0
        tst	r0, #_TIF_NEED_RESCHED
        blne	svc_preempt
    #endif

        svc_exit r5, irq = 1			@ return from exception
     UNWIND(.fnend		)
    ENDPROC(__irq_svc)

- irq_handler


::

    /*
     * Interrupt handling.
     */
        .macro	irq_handler
    #ifdef CONFIG_GENERIC_IRQ_MULTI_HANDLER
        ldr	r1, =handle_arch_irq    //处理器相关中断处理函数地址
        mov	r0, sp                  //sp栈保存了中断上下文
        badr	lr, 9997f           //把9997标号的地址存入lr，因为irq_handler是一个宏，所以最终的irq_handler的下一条指令地址，即__irq_usr中
                                    //的get_thread_info tsk指令
        ldr	pc, [r1]                //跳转到irq中断处理函数
    #else
        arch_irq_handler_default
    #endif
    9997:
        .endm


irq_handler
------------

irq_handler的处理有两种配置，一种是配置了CONFIG_MULTI_IRQ_HANDLER,这种情况下linux kernel允许run time设定irq handler，如果我们是一个linux kernel image支持多个平台，这时
就需要配置这个选项。另一种是传统的linux做法，irq_handler实际上就是arch_irq_handler_default

第一种方式
^^^^^^^^^^^

第一种方式是直接跳转到handle_arch_irq的地址处执行，而这个地址就是C函数的地址，并且是可以动态设置的，由此就进入C代码阶段进行处理了

::

 
    void __init setup_arch(char **cmdline_p)
    {
        const struct machine_desc *mdesc;
         
        setup_processor();
        mdesc = setup_machine_fdt(__atags_pointer);
        if (!mdesc)
           mdesc = setup_machine_tags(__atags_pointer, __machine_arch_type);
        ......
        #ifdef CONFIG_MULTI_IRQ_HANDLER
            handle_arch_irq = mdesc->handle_irq;   /* 初始化阶段设置 */
        #endif
        ......
    }
     
     
     
    #ifdef CONFIG_MULTI_IRQ_HANDLER
    void __init set_handle_irq(void (*handle_irq)(struct pt_regs *))
    {
        if (handle_arch_irq)
                return;
                 
        handle_arch_irq = handle_irq;        /* 调用函数动态设置 */
                    
    }
    #endif

第二种方式
^^^^^^^^^^^^^

arch_irq_handler_default在arch/arm/include/asm/entry-macro-multi.S定义

::

    /*
     * Interrupt handling.  Preserves r7, r8, r9
     */
        .macro	arch_irq_handler_default
        get_irqnr_preamble r6, lr
    1:	get_irqnr_and_base r0, r2, r6, lr
        movne	r1, sp
        @
        @ routine called with r0 = irq number, r1 = struct pt_regs *
        @
        badrne	lr, 1b
        bne	asm_do_IRQ

    #ifdef CONFIG_SMP
        /*
         * XXX
         *
         * this macro assumes that irqstat (r2) and base (r6) are
         * preserved from get_irqnr_and_base above
         */
        ALT_SMP(test_for_ipi r0, r2, r6, lr)
        ALT_UP_B(9997f)
        movne	r1, sp
        badrne	lr, 1b
        bne	do_IPI
    #endif
    9997:
        .endm

        .macro	arch_irq_handler, symbol_name
        .align	5
        .global \symbol_name
    \symbol_name:
        mov	r8, lr
        arch_irq_handler_default
        ret	r8
        .endm

这种方法是通过asm_do_IRQ函数来进入到C代码中的

::
    
    //__handle_domain_irq在kernel/kernel/irq/irqdesc.c中实现
    int __handle_domain_irq(struct irq_domain *domain, unsigned int hwirq,
                bool lookup, struct pt_regs *regs)
    {
        struct pt_regs *old_regs = set_irq_regs(regs);
        unsigned int irq = hwirq;
        int ret = 0;

        irq_enter();

    #ifdef CONFIG_IRQ_DOMAIN
        if (lookup)
            irq = irq_find_mapping(domain, hwirq);
    #endif

        /*
         * Some hardware gives randomly wrong interrupts.  Rather
         * than crashing, do something sensible.
         */
        if (unlikely(!irq || irq >= nr_irqs)) {
            ack_bad_irq(irq);
            ret = -EINVAL;
        } else {
            generic_handle_irq(irq);    //由此进入通用的中断处理函数
        }

        irq_exit();
        set_irq_regs(old_regs);
        return ret;
    }
    /*
     * handle_IRQ handles all hardware IRQ's.  Decoded IRQs should
     * not come via this function.  Instead, they should provide their
     * own 'handler'.  Used by platform code implementing C-based 1st
     * level decoding.
     */
    void handle_IRQ(unsigned int irq, struct pt_regs *regs)
    {
        __handle_domain_irq(NULL, irq, false, regs);
    }

    /*
     * asm_do_IRQ is the interface to be used from assembly code.
     */
    asmlinkage void __exception_irq_entry
    asm_do_IRQ(unsigned int irq, struct pt_regs *regs)
    {
        handle_IRQ(irq, regs);
    }


这种方式是比较旧的一种操作，它处理的硬件中断号和IRQ number之间的关系非常简单，但是实际上ARM平台上的硬件中断系统已经越来越复杂了。
需要引入Interrupt controller级联，irq domain等概念

handle_arch_irq
-----------------

这里详细分析一下第一种中断处理方式

::

    start_kernel
    ...
        local_irq_disable
        ...
        setup_arch(&command_line)
            paging_init
                devicemaps_init
                    early_trap_init(vectors)    //设置异常向量表
            ...
            handle_arch_irq = mdesc->handle_irq     //默认handle_irq还是空
        ...
        trap_init
        ...
        early_irq_init  //初始化irq_desc数组
        init_IRQ //芯片相关的中断初始化
        ...
        local_irq_enable

**初始化irq_desc数组空间一些通用的参数**

::

    struct irq_desc irq_desc[NR_IRQS] __cacheline_aligned_in_smp = {
        [0 ... NR_IRQS-1] = {
            .handle_irq	= handle_bad_irq,   //默认每个中断函数都是错误中断需要我们自己实现注册
            .depth		= 1,
            .lock		= __RAW_SPIN_LOCK_UNLOCKED(irq_desc->lock),
        }
    };

    int __init early_irq_init(void)
    {
        int count, i, node = first_online_node;
        struct irq_desc *desc;

        init_irq_default_affinity();

        printk(KERN_INFO "NR_IRQS: %d\n", NR_IRQS);

        desc = irq_desc;
        count = ARRAY_SIZE(irq_desc);

        for (i = 0; i < count; i++) {   //遍历整个lookup table,对每个entry进行初始化
            desc[i].kstat_irqs = alloc_percpu(unsigned int);    //分配per cpu的irq统计信息需要的内存
            alloc_masks(&desc[i], node);        //分配中断描述符中需要的cpu mask内存
            raw_spin_lock_init(&desc[i].lock);  //初始化spin lock
            lockdep_set_class(&desc[i].lock, &irq_desc_lock_class);
            mutex_init(&desc[i].request_mutex);   
            desc_set_defaults(i, &desc[i], node, NULL, NULL);   //设定default值
        }
        return arch_early_irq_init();   //调用arch相关d的初始化函数(arm体系中此函数为空)
    }



::

    void __init init_IRQ(void)
    {
        int ret;

        if (IS_ENABLED(CONFIG_OF) && !machine_desc->init_irq)
            irqchip_init();
        else
            machine_desc->init_irq();   //此处会调用平台相关的中断初始化函数

        if (IS_ENABLED(CONFIG_OF) && IS_ENABLED(CONFIG_CACHE_L2X0) &&
            (machine_desc->l2c_aux_mask || machine_desc->l2c_aux_val)) {
            if (!outer_cache.write_sec)
                outer_cache.write_sec = machine_desc->l2c_write_sec;
            ret = l2x0_of_init(machine_desc->l2c_aux_val,
                       machine_desc->l2c_aux_mask);
            if (ret && ret != -ENODEV)
                pr_err("L2C: failed to init: %d\n", ret);
        }

        uniphier_cache_init();
    }

关于machine_desc，这个是在启动阶段通过命令行或者设备树传过来的机器码找到对应的machin. 具体可见setup_arch函数中
