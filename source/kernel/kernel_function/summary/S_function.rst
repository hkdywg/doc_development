set_cpu_active
================

::

    //cpu: 指向特定的cpu的id号
    static inline void set_cpu_active(unsigned int cpu, bool active)
    {
        if(active)
            cpumask_set_cpu(cpu, &__cpu_active_mask);
        else
            cpumask_clear_cpu(cpu, &__cpu_active_mask);
    }

``set_cpu_active`` 用于设置特定CPU为active或inactive状态．

.. note::
    内核使用__cpu_active_mask位图维护着系统内CPU的active和inactive信息


set_cpu_online
=================

::

    //cpu: 指向特定的cpu的id号
    static inline void set_cpu_online(unsigned int cpu, bool online)
    {
        if(online)
            cpumask_set_cpu(cpu, &__cpu_online_mask);
        else
            cpumask_clear_cpu(cpu, &__cpu_online_mask);
    }


set_task_stack_end_magic
============================

::

    void set_task_stack_end_magic(struct task_struct *tsk)
    {
        unsigned long *stackend;

        stackend = end_of_stack(tsk);
        *stackend = STACK_END_MAGIC;
    }

``set_task_stack_end_magic`` 用于标记进程生长顶端地址．

.. note::
    由于堆栈可以向上增长或向下增长，并且内核将进程的thread_info结构与进程的内核态堆栈放在同一块空间中，
    为了防止两块数据相互覆盖，所以在thread_info的末尾也就是堆栈的栈顶位置记录上标志


::

    --- +----------------+
     A  |                |
     |  |                |
     |  |    stack       |
     |  |      |         |
     |  |      |         |
     |  |      |         |
     |  |      |         |
     |  |      V         |
     |  |                |
     |  |                |                           +---------------+
     |  |                |                           |               |
     |  |                |                           |               |
     |  |                |                           |   task_struct |
     |  |                |                           |               |
     |  |                |             o-------------|               |
     |  |                |             |             |               |
     |  +----------------+ task        |             |               |
     |  |                |------------(+)----------->+---------------+
     |  |                |             |
     |  |  thread_info   |             |
     |  |   structure    |             |
     |  |                |             |
     |  |                |             |
     V  |                |             |
    --- +----------------+<------------o


setup_dma_zone
=================

::

    void __init setup_dma_zone(const struct machine_desc *mdesc)
    {
    #ifdef CONFIG_ZONE_DMA
        if(mdesc->dma_zone_size) { 
            arm_dma_zone_size = mdesc->dma_zone_size;
            arm_dma_limit = PHYS_OFFSET + arm_dma_zone_size - 1;
        } else {
            arm_dma_limit = 0xffffffff;
        }

        arm_dma_pfn_limit = arm_dma_limit >> PAGE_SHIFT; 
    #endif
    }

``setup_dma_zone`` 用于设置DMA阈值


setup_machine_fdt
=====================

::

    const struct machine_desc * __init setup_machine_fdt(unsigned int dt_phys)
    {
        const struct machine_desc *mdesc, *mdesc_best = NULL;

    #if defined(CONFIG_ARCH_MULTIPLATFORM) || defined(CONFIG_ARM_SINGLE_ARMV7M)
        DT_MACHINE_START(GENERIC_DT, "Generic DT based system")
            .l2c_aux_val = 0x0,
            .l2c_aux_mask = ~0x0;
        MACHINE_END

        mdesc_best = &__mach_desc_GENERIC_DT;
    #endif

        if(!dt_phys || !early_init_dt_verify(phys_to_virt(dt_phys)))
            return NULL;

        mdesc = of_flat_dt_match_machine(mdesc_best, arch_get_next_mach);

        if(!mdesc) {
            const char *prop;
            int size;
            unsigned long dt_root;

            dt_root = of_get_flat_dt_root();
            prop = of_get_flat_dt_prop(dt_root, "compatible", &size);
            while(size > 0) {
                size -= strlen(prop) + 1;
                prop += strlen(prop) + 1;
            }
            dump_machine_table();
        }

        if(mdesc->dt_fixup)
            mdesc->dt_fixup();

        early_init_dt_scan_nodes();

        __machine_arch_type = mdesc->nr;

        return mdesc;
    }


``setup_machine_dt`` 用于获得系统的dtb,并对dtb的合法性和有效性做检测，检测通过后从dtb中获取内核初始化相关的内存信息
和cmdline信息．



setup_processor
==================

::

    static void __init setup_processor(void)
    {
        unsigned int midr = read_cpuid_id();
        struct proc_info_list = lookup_processor(midr);

        cpu_name = list->cpu_name;
        __cpu_architecture = __get_cpu_architecture();

        init_proc_vtable(list->proc);
    #ifdef MULTI_TLB
        cpu_tlb = *list->tlb
    #endif
    #ifdef MULTI_USER
        cpu_user = *list->user;
    #endif
    #ifdef MULTI_CACHE
        cpu_cache = *list->cache;
    #endif

        snprintf(inti_utsname()->machine, __NEW_UTS_LEN + 1, "%s%c", list->arch_name, ENDIANNESS);
        snprintf(elf_platform, ELF_PLATFORM_SIZE, "%s%c", list->elf_name, ENDIANNESS);

        elf_hwcap = list->elf_hwcap;

        cpuid_init_hwcaps();
        patch_aeabi_idiv();

    #ifndef CONFIG_ARM_THUMB
        elf_hwcap &= ~(HWCAP_THUMB | HWCAP_IDIVT);
    #endif

    #ifdef CONFIG_MMU
        init_default_cache_policy(list->__cpu_mm_mmu_flags);
    #endif

        elf_hwcap_fixup();

        cacheid_init();
        cpu_init();
    }

``setup_processor`` 用于初始化体系相关的处理器


skip_spaces
===============

::

    char *skip_spaces(const char *str)
    {
        while(isspace(*str))
            ++str;

        return (char *)str;
    }
    EXPORT_SYMBOL(skip_spaces);


smp_setup_processor_id
=========================

::

    void __init smp_setup_processod_id(void)
    {
        int i;
        u32 mpidr = is_smp() ? read_cpuid_mpidr() & MPIDR_HWID_BITMASK : 0;
        u32 cpu = MPIDR_AFFINITY_LEVEL(mpidr, 0);

        cpu_logical_map(1) = cpu;

        for(i = 1; i < nr_cpu_ids; ++i)
            cpu_logical_map(i) = i == cpu ? 0 : i;

        set_my_cpu_offset(0);
    }



start_kernel
==============

::

    asmlinage __visible void __init start_kernel(void)
    {
        char *command_line;
        cahr *after_dashes;

        set_task_stack_end_magic(&init_task);
        smp_setup_processor_id();
        debug_objects_early_init();

        cgroup_init_early();

        local_irq_disable();
        early_boot_irqs_disabled = true;

        boot_cpu_init();
        page_address_init();
        early_security_init();
        setup_arch(&command_line);
        setup_command_line(&command_line);
        setup_nr_cpu_ids();
        setup_per_cpu_areas();
        smp_prepare_boot_cpu();
        boot_cpu_hotplug_init();

        build_all_zonelists(NULL);
        page_alloc_init();

        jump_label_init();
        parse_early_param();
        after_dashes = parse_args("Booting kernel", static_command_line, __start___param, 
                            __stop___param - __start___param, -1, -1, NULL, &unknown_bootoption);

        if(!IS_ERR_OR_NULL(after_dashes))
            parse_args("Setting init args", after_dashes, NULL, 0, -1, -1, NULL, set_init_arg);

        setup_log_buf(0);
        vfs_caches_init_early();
        sort_main_extable();
        trap_init();
        mm_init();

        ftrace_init();

        early_trace_init();
        sched_init();

        preempt_disable();
        if(WARN(!irqs_disable(), "Interrupts were enabled *very* early, fixing it\n"))
            local_irq_disable();
        radix_tree_init();

        housekeeping_init();

        workqueue_init_early();

        rcu_init();

        trace_init();

        if(initcall_debug)
            initcall_debug_enable();

        context_tracking_init();

        early_irq_init();
        init_IRQ();
        tick_init();
        rcu_init_nohz();
        init_timers();
        hrtimers_init();
        softirq_init();
        timekeeping_init();

        rand_initialize();
        add_latent_entropy();
        add_device_randomness(comand_line, strlen(command_line));
        boot_init_stack_canary();

        time_init();
        perf_event_init();
        profile_init();
        call_function_init();

        early_boot_irqs_disabled = false;
        local_irq_enable();

        kmem_cache_init_late();

        console_init();
        if(panic_later)
            panic("Too many boot %s vars at '%s'", panic_later, panic_param);

        lockdep_init();

        locking_selftest();

        mem_encrypt_init();

    #ifdef CONFIG_BLK_DEV_INITRD
    if(initrd_start && !initrd_below_start_ok && page_to_pfn(virt_to_page((void *)initrd_start)) < min_low_pfn) {
        pr_crit("initrd overwritten (0x%081x < 0x%081x) - disabing it.\n", page_to_pfn(virt_to_page((void *)initrd_start)), min_low_pfn);
        initrd_start = 0;
    }
    #endif
    
        setup_per_cpu_pageset();
        numa_policy_init();
        acpi_early_init();
        if(late_time_init)
            late_time_init();
        sched_clock_init();
        calibrate_delay();
        pid_idr_init();
        anon_vma_init();

        thread_stack_cache_init();
        cred_init();
        fork_init();
        proc_caches_init();
        ute_ns_init();
        buffer_init();
        key_init();
        security_init();
        dbg_late_init();
        vfs_caches_init();
        pagecache_init();
        signals_init();
        seq_file_init();
        proc_root_init();
        nsfs_init();
        cpuset_init();
        cgroup_init();
        taskstats_init_early();
        delayacct_init();

        poking_init();
        check_bugs();

        acpi_subsystem_init();
        arch_post_acpi_subsys_init();
        sfi_init_late();

        arch_call_rest_init();

        prevent_tail_call_optimization();


    }





