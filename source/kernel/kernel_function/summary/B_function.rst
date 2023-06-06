boot_cpu_init
===============

::

    void __init boot_cpu_init(void)
    {
        //获得boot cpu的ID
        int cpu = smp_processor_id();

        //将其在系统维护的多个位图中置位，其中包括online, active, present, possible
        set_cpu_online(cpu, true);
        set_cpu_active(cpu, true);
        set_cpu_present(cpu, true);
        set_cpu_possible(cpu, true);

        #ifdef CONFIG_SMP
        __boot_cpu_id = cpu;
        #endif
    }


``boot_cpu_init`` 用于初始化Boot CPU



build_mem_type_table
=======================


::

    static void __init build_mem_type_table(void)
    {
        struct cachepolicy *cp;
        unsigned int cr = get_cr();
        pteval_t user_pgprot, kern_pgprot, vecs_pgprot;
        pteval_t hyp_device_pgprot, s2_pgprot, s2_device_pgprot;
        int cpu_arch = cpu_architecture();
        int i;

        if(is_smp()) {
            if(cachepolicy != CPOLICY_WRITEALLOC)
                cachepolicy = CPOLICY_WRITEALLOC;
            if(!(initial_pmd_value & PMD_SECT_S))
                initial_pmd_value |= PMD_SECT_S;
        }

        if(cpu_is_xsc3() || (cpu_arch >= CPU_ARCH_ARMv6 && (cr & CR_XP))) {
            if(!cpu_is_xsc3()) {
                //对各个成员的prot_sect标志增加PMD_SECT_XN支持
                //XN为Execute-Never,即指明处理器能否在该区域上执行程序
                mem_types[MT_DEVICE].prot_sect |= PMD_SECT_XN;
                mem_types[MT_DEVICE_NONSHARED].pro_sect |= PMD_SECT_XN;
                mem_types[MT_DEVICE_CACHED].pro_sect |= PMD_SECT_XN;
                mem_types[MT_DEVICE_WC].pro_sect |= PMD_SECT_XN;

                mem_types[MT_MEMORY_RW].prot_sect |= PMD_SECT_XN;
            }

            if(cpu_arch >= CPU_ARCH_ARMv7 && (cr & CR_TRE)) {
                mem_types[MT_DEVICE].prot_sect |= PMD_SECT_TEX(1);
                mem_types[MT_DEVICE_NONSHARED].prot_sect |= PMD_SECT_TE(1);
                mem_types[MT_DEVICE_WC].prot_sect |= PMD_SECT_BUFFERABLE;
            }
        }

        cp = &cache_policies(cachepolicy);
        vecs_pgprot = kern_pgprot = user_pgprot = cp->pte;
        s2_pgprot = cp->pte_s2;
        hyp_device_pgprot = mem_types[MT_DEVICE].prot_pte;
        s2_device_pgprot = mem_types[MT_DEVICE].prot_pte_s2;
    }


.. note::
    TRE位用于SCTLR寄存器的bit28, 用于页表TEX remap使能．如果该位置位，那么在页表中，TEX[2:1]被分配给操作系统管理，而TEX[0],
    C, B位以及MMU remap寄存器用于描述内存区的属性．反之如果该位清零，那么页表中，TEX[2:0]和C, B位一起用于描述内存区域的属性



.. warning::
    此函数待完善.........





