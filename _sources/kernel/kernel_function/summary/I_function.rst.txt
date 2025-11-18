icache_is_pipt
================

::

    #define icache_is_pipt() cacheid_is(CACHEID_PIPT)

``icache_is_pipt`` 判断L1指令CACHE是否是PIPT(Physical index, Physical tag)


icache_is_vipt_aliasing
==========================

::

    #define icache_is_vipt_aliasing() cacheid_is(CACHEID_VIPT_I_ALIASING)


``icache_is_vipt_aliasing`` 用于判断ICACHE是否属于VIPT aliasing


icache_is_vivt_asid_tagged
============================

::

    #define icache_is_vivt_asid_tagged() cacheid_is(CACHEID_ASID_TAGGED)


``icache_id_vivt_asid_tagged`` 用于判断ICACHE是否属于VIVT ASID tags


iotable_init
=================

::

    void __init iotable_init(struct map_desc *io_desc, int nr)
    {
        struct map_desc *md;
        struct vm_struct *vm;
        struct static_vm *svm;

        if(!nr)
            return;

        //给static_vm分配内存
        svm = early_alloc_aligned(sizeof(*svm) * nr, __alignof__(*svm));

        //给参数io_desc映射结构建立指定的页表
        for(md = io_desc; nr; md++, nr--)
        {
            //执行真正的页表建立
            create_mapping(md);

            //更新svm的vm结构
            vm = &svm->vm;
            vm->addr = (void *)(md->virtual && PAGE_MASK);
            vm->size = PAGE_ALIGN(md->length + (md->virtual & ~PAGE_MASK));
            vm->phys_addr = __pfn_to_phys(md->pfn);
            vm->flags = VM_IOREMAP | VM_ARM_STATIC_MAPPING;
            vm->flags |= VM_ARM_MTYPE(md->type);
            vm->caller = iotable_init;
            add_static_vm_early(svm++);
        }
    }

``iotable_init`` 用于建立体系IO映射表



init_default_cache_policy
===========================

::

    void __init init_default_cache_policy(unsigned long pmd)
    {
        int i;

        initial_pmd_value = pmd;

        pmd &= PMD_SECT_CACHE_MASK;

        for(i = 0; i < ARRAY_SIZE(cache_policies); i++)
        {
            if(cache_policies[i].pmd == pmd) {
                cachepolicy = i;
                break;
            }
        }

        if(i == ARRAY_SIZE(cache_policies))
            pr_err("ERROR: could not find cache policy\n");
    }

``init_default_cache_policy`` 用于初始化系统cachepolicy信息．内核通过cache_policies[]数组提供了多种cache策略



init_utsname
================

::

    static inline struct new_utsname *init_utsname(void)
    {
        return &init_uts_ns.name;
    }

``init_utsname`` 用于初始化全局变量init_uts_ns的name成员．init_uts_ns属于struct uts_namespace，其结构用于维护系统名称，版本号，机器名称



initial_pmd_value
=======================

::

    static unsigned long initial_pmd_value __initdata = 0;


isspace
===========

::

    #define isspace(c) ((__ismask(c)&(_S)) != 0)

``isspace`` 判断字符c是否是一个空格


is_highmem_idx
=================

::

    static inline int is_highmem_idx(enum zone_type idx)
    {
    #ifdef CONFIG_HIGHMEM
        return (idx == ZONE_HIGHMEM || (idx == ZONE_MOVABLE && zone_movable_is_highmem()));
    #else
        return 0;
    #endif
    }


``is_highmem_idx`` 用于判断idx是否指向高端内存


is_smp
=========

::

    static inline bool is_smp(void)
    {
    #ifndef CONFIG_SMP
        return false;
    #elif defined(CONFIG_SMP_ON_UP)
        extern unsigned int smp_on_up;
        return !!smp_on_up;
    #else
        return true;
    #endif
    }

``is_smp`` 用于判断CPU是否支持smp





