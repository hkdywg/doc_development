cacheid_init
================

::

    unsigned int cacheid __read_mostly;

    static void __init cachid_init(void)
    {
        unsigned int arch = cpu_architecture();

        if(arch >= CPU_ARCH_ARMv6) {
            //读取ARM体系的CTR(cache type register)寄存器，以此读取体系CACHE的类型信息
            unsigned int cachetype = read_cpuid_cachetype();

            if((arch == CPU_ARCH_ARMv7M) && !(cachetype & 0xf000f)) {
                cacheid = 0;
            } else if((cachetype & (7 << 29)) == 4 << 29) {
                arch = CPU_ARCH_ARMv7;
                cacheid = CACHEID_VIPT_NONALIASING;
                switch (cachetype & (3 << 14)) {
                    case (1 << 14):
                        cacheid |= CACHEID_ASID_TAGGED;
                        break;
                    case (3 << 14):
                        cacheid |= CACHEID_PIPT;
                        break;
                }
            } else {
                arch = CPU_ARCH_ARMv6;
                if(cachetype & (1 << 23))
                    cacheid = CACHEID_VIPT_ALIASING;
                else
                    cacheid = CACHEID_VIPT_NONALIASING;
            }
            if(cpu_has_alising_icache(arch))
                cacheid |= CACHEID_VIPT_I_ALIASING;
        }
        else
            cacheid = CACHEID_VIVT;
    }

``cacheid_init`` 用于初始化系统CACHE信息，内核使用全局变量cacheid维护cache相关的信息．


cache_is_vipt
===============

::

    #define cache_is_vipt() cacheid_is(CACHEID_VIPT)

此函数用于判断CACHE是否属于VIPT类型．Virtual Index, Physical Tag


cache_is_vipt_aliasing
========================

::

    #define cache_is_vipt_aliasing() cacheid_is(CACHEID_VIPT_ALIASING)


此函数用于判断CACHE是否属于VIPT别名


cache_is_vipt_nonaliasing
===========================

::

    #define cache_is_vipt_nonaliasing() cacheid_is(CACHEID_VIPT_NONALIASING)


此函数用于判断CACHE是否属于VIPT非别名

cache_is_vivt_asid_tagged
===============================

::

    #define cache_is_vivt_asid_tagged() cacheid_is(CACHEID_ASID_TAGGED)



cahceid
============

::
    
    unsigned int cacheid __read_mostly;



cachepolicy
=============

::

    static unsigned int cachepolicy __initdata = CPOLICY_WRITEBACK;


``cachepolicy`` 全局变量用于指定当前系统所使用的cache policy在cache_policies[]数组中的索引



calc_memmap_size
==================

::

    static unsigned long __init cacl_memmap_size(unsigned long spanned_pages,
                unsigned long present_pages)
    {
        unsigned long pages = spanned_pages;

        if(spanned_pages > present_pages + (present_pages >> 4)
            && IS_ENABLED(CONFIG_SPARSMEM))
            pages = present_pages;

        return PAGE_ALIGN(pages + sizeof(struct page)) >> PAGE_SHIFT;
    }


``cacl_memmap_size`` 用于计算当前节点用于维护spanned物理页帧的struct page占用的页的数量




calculatode_totalpage
=======================

::

    static void __init calculate_node_totalpages(struct pglist_data *pgdat,
            unsigned long node_start_pfn, unsigned long node_end_pfn,
            unsigned long *zone_size, unsigned long *zholes_size)
    {
        unsigned long realtotalpages = 0, totalpages = 0;
        enum zone_type i;

        for(i = 0; i < MAX_NR_ZONES; i++) {
            //遍历每一个ZONE
            struct zone *zone = pgdat->node_zones + i;
            unsigned long zone_start_pfn, zone_end_pfn;
            unsigned long size, real_size;

            //计算该ZONE横跨了多少个物理页帧
            size = zone_spanned_pages_in_node(pgdat->node_id, i, node_start_pfn,
                        &zone_start_pfn, &zone_end_pfn, zones_size);
            //
            real_size = size - zone_absent_pages_in_node(pgdat->node_id, i, node_start_pfn, 
                                node_end_pfn, zholes_size);

            if(size)
                zone->zone_start_pfn = zone_start_pfn;
            else
                zone->zone_start_pfn = 0;

            zone->spanned_pages = size;
            zone->present_pages = real_size;

            totalpages += size;
            realtotalpages += real_size;
        }

        pgdat->node_spanned_pages = totalpages;
        pgdat->node_present_pages = realtotalpages;
    }

``calculate_node_totalpages`` 用于计算系统占用的物理页帧和实际物理页帧的数量，所谓占用物理页帧指的是多块物理内存中间存在hole，但这些
hole是不可用的物理页帧，因此系统占用的物理页帧就是hole加上实际物理页帧数量．

.. note::
    内存块之间存在hole，因此spanned pages指的就是第一块物理内存到最后一块物理内存块横跨了多少物理页帧，而real pages指的就是实际物理内存块占用了多少物理页帧




check_block_
=================

::

    static int check_block_(uint32_t hdrsize, uint32_t totalsize, uint32_t base, uint32_t size)
    {
        //检查base是否在hdrsize和totalsize之间
        if(!check_off_(hdrsize, totalsize, base))
            return 0;
        //检查base+size是否溢出
        if((base + size) < size)
            return 0;
        //检查base+size的和是否在hdrsize和totalsize之间
        if(!check_off_(hdrsize, totalsize, base + size))
            return 0;
        return 1;
    }



check_off_
================

::

    static int check_off_(uint32_t hdrsize, uint32_t totalsize, uint32_t off)
    {
        //检查off是否在hdrsize和totalsize之间
        return (off >= hdrsize) && (off <= totalsize);
    }



choose_memblock_flags
=======================

::

    enum memblock_flags __init_memblock choose_memblock_flags(void)
    {
        return system_has_some_miiror ? MEMBLOCK_MIRROR : MEMBLOCK_NONE;
    }

``choose_memblock_flags`` 用于获得MEMBLOCK内存区间的FLAGS.



clamp
======

::

    #define clamp(val, lo, hi) min(typeof(val)max(val, lo), hi)

``clamp`` 用于从val和lo中找到一个最大的值，再将该值与hi中找到最小的值


cma_activate_area
===================

::

    static int __init cam_activate_area(struct cma *cma)
    {
        //存储cma的bitmap需要使用的字节数
        int bitmap_size = BITS_TO_LONGS(cma_bitmap_maxno(cma) * sizeof(long));
        //存储cma区域的起始物理页帧
        unsigned long base_pfn = cma->base_pfn, pfn = base_pfn;
        //表示cma区域占用的pageblock数量
        unsigned i = cma->count >> pageblock_order;
        struct zone *zone;

        //分配一定长度的内存用于存储CMA区域的bitmap
        cma->bitmap = kzalloc(bitmap_size, GFP_KERNEL);

        if(!cma->bitmap)
            return -ENOMEM;

        WARN_ON_ONCE(!pfn_valid(pfn));
        zone = page_zone(pfn_to_page(pfn));

        do {
            unsigned j;

            base_pfn = pfn;
            for(j = pageblock_nr_pages; j; --j, pfn++) {
                //检查cma区域的每个pageblock所有页是否有效
                if(page_zone(pfn_to_page(pfn)) != zone)
                    goto not_in_zone;
            }
            //将pageblock所有的物理页的RESERVED标志清除，然后将这些页都返回给buddy系统使用
            init_cma_reserved_pageblock(pfn_to_page(base_pfn));
        } while(--i);

        //初始化cma区域使用的互斥锁
        mutex_init(&cma->lock);

        return 0;

        not_in_zone:
            kfree(cma->bitmap);
            cma->count = 0;
            return -EINVAL;
    }


``cma_activate_area`` 将CMA区域内的预留页全部释放添加到Buddy管理器内，然后激活CMA区域供系统使用


cma_alloc
=============

::

    struct page *cma_alloc(struct cma *cma, size_t count, unsigned int align, bool no_warn)
    {
        unsigned long mask, offset;
        unsigned long pfn = -1;
        unsigned long start = 0;
        unsigned long bitmap_maxno, bitmap_no, bitmap_count;
        size_t i;
        struct page *page = NULL;
        int ret = -ENOMEM;

        //检查cma和cma->count的有效性
        if(!cma || !cma->count)
            return NULL;

        if(!count)
            return NULL;

        //获得一个用于分配的掩码
        mask = cma_bitmap_aligned_mask(cma, align);
        //获得符合对齐要求的CMA起始页帧
        offset = cma_bitmap_aligned_offset(cma, align);
        bitmap_maxno = cma_bitmap_maxno(cma);
        //获取参数count在CMA bitmap中对应的bit数量
        bitmap_count = cma_bitmap_pages_to_bits(cma, count);

        //如果需要分配的bit总数大于CMA区域bitmap支持的最大bit数,则直接返回
        if(bitmap_count > bitmap_maxno)
            return NULL;

        for(;;) {
            //上互斥锁，以让分配是独占的
            mutex_lock(&cma->lock);
            //从start到bitmap_maxno区间中，在CMA的bitmap中找到第一块长度为bitmap_count的连续物理内存区块
            bitmap_no = bitmap_find_next_zero_area_off(cma->bitmap,
                bitmap_maxno, start, bitmap_count, mask, offset);

            //如果bitmap_no大于等于bitmap_maxno那么表示没有找到
            if(bitmap_no >= bitmap_maxno) {
                muxtex_unlock(&cma->lock);
                break;
            }
            //将bitmap中对应的bit位置位
            bitmap_set(cma->bitmap, bitmap_no, bitmap_count);

            mutex_unlock(&cma->lock);
            //通过bitmap_no计算出对应的起始页帧号
            pfn = cma->base_pfn + (bitmap_no << cma->order_per_bit);
            mutex_lock(&cma_mutex);
            //从buddy系统中分配从pfn到pnf+count的所有物理页，迁移类型为MIGRATE_CMA
            ret = allock_contig_range(pfn, pfn + count, MIGRATE_CMA, 
                GFP_KERNEL | (no_warn ? __GFP_NOWARN : 0));

            mutex_unlock(&cma_mutex);
            if(ret == 0) {
                page = pfn_to_page(pfn);
                break;
            }
            //清除之前置位的bit
            cma_clear_bitmap(cma, pfn, count);
            if(ret != -EBUSY)
                break;

            start = bitmap_no + mask + 1;
        }
        trace_cma_alloc(pfn, page, count, align);

        if(page) {
            for(i = 0; i < count; i++)
                page_kasan_tag_reset(page + i);
        }

        if(ret && !no_warn)
            page_debug_show_areas(cma);

        return page;
    }


``cma_alloc`` 从CMA区域内分配指定长度的连续物理内存




cma_bitmap_aligned_mask
========================

::

    static unsigned long cma_bitmap_aligned_mask(const struct cma *cma,
                                        unsigned int align_order)
    {
        //判断align_order是否小于该CMA区域order_per_bit
        if(align_order <= cma->order_per_bit)
            return 0;

        return (1UL << (align_order - cma->oder_per_bit)) - 1; 
    }

``cma_bitmap_aligned_mask`` 用于获得指定页块的掩码



cma_bitmap_cligned_offset
==========================

::

    static unsigned long cma_bitmap_aligned_offset(const struct cma *cma,
                                    unsigned int align_order)
    {
        return (cma->base_pfn & ((1UL << align_order) - 1)) >> cma->order_per_bit;
    }


``cma_bitmap_aligned_offset`` 用于获得该CMA区域的起始页帧按一定的对齐方式在bitmap中的位置


cma_bitmap_maxno
==================

::

    static inline unsigned long cma_bitmap_maxno(struct cma *cma)
    {
        //struct cma中count成员用于存储cma区域包含的page数量
        //order_per_bit成员用于表示bitmap中一个bit包含的page数量
        return cma->count >> cma->order_per_bit;
    }

``cma_bitmap_maxno`` 用于获得该CMA区域bitmap总共含有的bit数



cma_bitmap_pages_to_bits
==========================

::

    static unsigned long cma_bitmap_pages_to_bits(const struct cma *cma, unsigned long pages)
    {
        return ALIGN(pages, 1UL << cma->order_per_bit) >> cma->order_per_bit;
    }

用于获得一定page数占用bit数量


cma_clear_bitmap
==================

::

    //pfn: 指向即将清除bit的起始页帧
    //count:表示要清除页帧数量
    static void cma_clear_bitmap(struct cma *cma, unsigned long pfn, unsigned int count)
    {
        unsigned long bitmap_no, bitmap_count;

        //计算pfn相对cma起始页帧的偏移
        bitmap_no = (pfn - cma->base_pfn) >> cma->order_per_bit;
        //计算要删除page数量占用的bit数
        bitmap_count = cma_bitmap_pages_to_bits(cma, count);

        mutex_lock(&cma->lock);
        bitmap_clear(cma->bitmap, bitmap_no, bitmap_count);
        mutex_unlock(&cma->lock);
    }

``cma_clear_bitmap`` 用于清除CMA区域bitmap中一定长度的bit


cma_declare_contiguous
=========================



cma_early_percent_memory
=========================

::

    #ifdef CONFIG_CMA_SIZE_PERCENTAGE
    static phys_addr_t __init __maybe_unused cma_early_percent_memory(void)
    {
        struct memblock_region *reg;
        unsigned long total_pages = 0;

        //遍历MEMBLOCK内存分配器中所有可用的物理内存
        for_each_memblock(memory, reg)
            //统计总共可用的物理内存数
            total_pages += memblock_region_memory_end_pfn(reg) - 
                memblock_region_memory_base_pfn(reg);
        return (total_pages * CONFIG_CMA_SIZE_PERCENTAGE / 100) << PAGE_SHIFT;
    }
    #else
    static inline __maybe_unused phys_addr_t cma_early_percent_memory(void)
    {
        return 0;
    }
    #endif

``cma_early_percent_memory`` 用于按内核配置获得一定百分比的物理内存数


cma_for_each_area
====================

::

    int cma_for_each_area(int (*it)(struct cma *cma, void *data), void *data)
    {
        int i;

        for(i = 0; i < cma_area_count; i++) {
            int ret = it(&cma_areas[i], data);

            if(ret)
                return ret;
        }

        return 0;
    }

``cma_for_each_area`` 用于遍历所有的CMA区域，并在每个区域内处理指定的任务．参数it是一个回调函数，data是传入的参数



cma_get_base
===============

::

    phys_addr_t cma_get_base(const struct cma *cma)
    {
        return PFN_PHYS(cma->base_pfn);
    }

``cma_get_base`` 用于获得CMA区域的起始物理地址


cma_get_name
==============

::

    const char *cma_get_name(const struct cma *cma)
    {
        return cma->name ? cma->name : "(undefined)";
    }

``cma_get_name`` 用于获得CMA区域的名字



cma_get_size
===============


::

    unsigned long cma_get_size(const struct cma *cma)
    {
        return cma->count << PAGE_SHIFT;
    }

``cma_get_size`` 用于获得CMA区域的长度



cma_init_reserved_areas
=========================

::

    static int __init cma_init_reserved_areas(void)
    {
        int  i;
        for(i = 0; i < cma_area_count; i++) {
            //激活cma区域
            int ret = cma_activate_area(&cma_areas[i]);

            if(ret)
                return ret;
        }

        return 0;
    }


``cma_init_reserved_areas`` 用于激活系统所有的CMA区域，当前系统总共包含cma_area_count个CMA区域


cma_init_reserved_mem
=========================

::

    //base: 指向系统预留区的起始地址
    //size: 指向预留区的长度
    //order_per_bit: 指明CMA中一个bitmap代表page的数量
    //name: cma区域名字
    //cma: 指向一个cma区域
    int __init cma_init_reserved_mem(phys_addr_t base, phys_addr_t size, unsigned int order_per_bit,
                                        const char *name, struct cma **res_cma)
    {
        struct cma *cma;
        phys_addr_t alignment;

        //检查当前cma区域数量是否已经超过系统支持最大cma区域数
        if(cma_area_count == ARRAY_SIZE(cma_areas))
            return -ENOSPC;

        //判断此区域是否已经在MEMBLOCK分配器中了
        if(!size || !memblock_is_region_reserved(base, size))
            return -EINVAL;

        //算出最大对齐占用的page数量
        alignment = PAGE_SIZE << max_t(unsigned long, MAX_OEDER - 1, pageblock_order);

        //
        if(!IS_ALIGNED(alignment >> PAGE_SHIFT, 1 << order_per_bit))
            return -EINVAL;

        if(ALIGN(base, alignment) != bae || ALIGN(size, alignment) != size)
            return -EINVAL;
        //取出当前可用的struct cma
        cma = &cma_areas[cma_area_count];
        //设置cma名字
        if(name) 
            cma->name = name;
        else
            cma->name = kasprintf(GFP_KERNEL, "cam%d\n", cma_area_count);
            if(!cma->name)
                return -NOMEM;
        //设置cma区域的起始物理页帧号
        cma->base_pfn = PFN_DOWN(base);
        cma->count = size >> PAGE_SHIFT;
        cma->order_per_bit = order_per_bit;
        *res_cma = cma;
        cma_area_count++;
        totalcma_pages += (size / PAGE_SIZE);

        return  0;
    }

``cma_init_reserved_mem`` 作用是将一块系统预留区加入到CMA区域内


cma_release
==============

::

    //cma: 指向一块cma区域
    //pages: 指向要释放物理内存区块的起始物理页
    //count: 指明要释放的物理页的数量
    bool cma_release(struct cma *cma, const struct page *pages, unsigned int count)
    {
        unsigned long pfn;

        //判断cma和pages参数的有效性
        if(!cma || !pages)
            return false;

        //将pages转换成页帧号
        pfn = page_to_pfn(pages);
        //判断页帧号是否在cma区域内
        if(pfn < cma->base_pfn || pfn >= cma->base_pfn + cma->count)
            return false;

        VM_BUG_ON(pfn + count > cma->base_pfn + cma->count);

        //将所有页帧返回给buddy系统
        free_contig_range(pfn, count);
        cma_clear_bitmap(cma, pfn, count);
        trace_cma_relase(pfn, pages, count);
    }

``cma_release`` 用于释放一块连续物理内存区块



__cpu_active_mask
===================

::

    typedef struct cpumask { DECLARE_BITMAP(bits, NR_CPUS); } cpumask_t;

    struct cpumask __cpu_active_mask __read_mostly;
    EXPORT_SYMBOL(__cpu_active_mask);


``__cpu_active_mask`` 用于维护系统中所有CPU的active和inactive信息,其实现是一个bitmap，每个bit对应一个CPU



cpu_has_aliasing_icache
==========================

::

    static int cpu_has_aliasing_icache(unsigned int arch)
    {
        int aliasing_icache;
        unsigned int id_reg, num_sets, line_size;

        //判断ICACHE是否属于PIPT类型，如果是PIPT类型则不需要对齐，直接返回
        if(icache_is_pipt())
            return 0;

        switch(arch) {
            case CPU_ARCH_ARMv7:
                //设置CSSELR寄存器，选中level1的ICACHE
                set_csselr(CSSELR_ICACHE | CSSELR_L1);
                //执行一次内存屏障
                isb();
                //读取level1 ICACHE的cache sets和cache line信息
                id_reg = read_ccsidr();
                line_size = 4 << ((id_reg & 0x7) + 2);
                num_sets = ((id_reg >> 13) & 0x7fff) + 1;
                aliasing_icache = (line_size * num_sets) > PAGE_SIZE;
                break;
            case CPU_ARCH_ARMv6:
                aliasing_icache = read_cpuid_cachetype() & (1 << 11);
                break;
            default:
                aliasing_icache = 0;
        }

        return aliasing_icache;
    }

``cpu_has_aliasing_icache`` 用于判断ICACHE是否按页对齐





cpu_init
===========

::

   void notrace cpu_init(void) 
   {
    #ifndef CONFIG_CPU_V7M
        //获取当前使用的cpu号
        unsigned int cpu = smp_processor_id();
        //获取但前cpu对应的全局堆栈
        struct stack *stk = &stacks[cpu];

        if(cpu >= NR_CPUS) {
            pr_crit("CPU%u: bad primary CPU number\n", cpu);
            BUG();
        }
        //将当前CPU在per_cpu_offset中的值写入到TPIDRPRW寄存器里
        set_my_cpu_offset(per_cpu_offset(cpu));
        //调用系统相关的proc_init函数
        cpu_proc_init();
    #ifdef CONFIG_THUMB2_KERNEL
    #define PLC "r"
    #else
    #define PLC "I"
    #endif
        //内嵌汇编,修改CPSR寄存器
        __asm__ (
        "msr cpsr_c, %1\n\t"
        "add r14, %0, %2\n\t"
        "mov sp, r14\n\t"
        "msr cpsr_c, %3\n\t"
        "add r14, %0. %4\n\t"
        "mov sp, r14\n\t"
        "msr cpsr_c, %7\n\t"
        "add r14, %0, %8\n\t"
        "mov sp, r14\n\t"
        "msr cpsr_c, %9"
        :
        : "r" (stk),
        PLC (PSR_F_BIT | PSR_I_BIT | IRQ_MODE),
        "I" (offsetof(struct stack, irq[0])),
        PLC (PSR_F_BIT | PSR_I_BIT | ABT_MODE),
        "I" (offsetof(struct stack, abt[0])),
        PLC (PSR_F_BIT | PSR_I_BIT | UND_MODE),
        "I" (offsetof(struct stack, und[0])),
        PLC (PSR_F_BIT | PSR_I_BIT | FIQ_MODE),
        "I" (offsetof(struct stack, fiq[0])),
        PLC (PSR_F_BIT | PSR_I_BIT | SVC_MODE)
        : "r14");
    #endif
   }

``cpu_init`` 用于初始化一个CPU,并设置了per-cpu的堆栈


.. note::
    linux使用stacks[]维护全局堆栈



cpu_logical_map
===================

::

    extern u32 __cpu_logical_map[];
    #define cpu_logical_map(cpu) __cpu_logical_map[cpu]

    //arm中对应的为
    u32 __cpu_logical_map[NR_CPUS] = { [0 ... NR_CPUS-1] = MPIDR_INVALID };


``cpu_logical_map`` 用于获得cpu对应的逻辑cpu号



cpu_max_bits_warn
====================

::

    static inline void cpu_max_bits_warn(unsigned int cpu, unsigned int bits)
    {
    #ifdef CONFIG_DEBUG_PER_CPU_MAPS
        WARN_ON_ONCE(cp >= bits);
    #endif
    }

``cpu_max_bits_warn`` 用于检查cpu号是否已经超过最大cpu号，如果超过，内核则报错


cpu_proc_init
===============

::

    #define PROC_VTABLE(f) processor.f
    #define cpu_proc_init   PROC_VTABLE(__proc_init)

    ENTRY(cpu_v7_proc_init)
        ret lr
    ENDPROC(cpu_v7_proc_init)



CPU_TO_FDT32
===============

::

    #define CPU_TO_FDT32(x) ((EXTRAC_BYTE(x, 0) << 24) | (EXTRAC_BYTE(x, 1) << 16)) |
                                (EXTRAC_BYTE(x, 2) << 8) | (EXTRAC_BYTE(x, 3)))


``CPU_TO_FDT32`` 用于将数据的大小端模式进行翻转


cpuid_init_hwcaps
=====================

::

    static void __init cpuid_init_hwcaps(void)
    {
        int block;
        u32 isar5;

        if(cpu_architecture() < CPU_ARCH_ARMv7)
            return;

        block = cpuid_feature_extract(CPUID_EXT_ISAR0, 24);
        if(block >= 2)
            elf_hwcap |= HWCAP_IDIVA;
        if(block >= 1)
            elf_hwcap |= HECAP_IDIVT;

        block = cpuid_feature_extract(CPUID_EXT_MMFR0, 0);
        if(block >= 5)
            elf_hwcap |= HWCAP_LPAE;

        isar5 = read_cpuid_ext(CPUID_EXT_ISAR5);

        block = cpuid_feature_extract_field(isar5, 4);
        if (block >= 2)
                elf_hwcap2 |= HWCAP2_PMULL;
        if (block >= 1)
                elf_hwcap2 |= HWCAP2_AES;

        block = cpuid_feature_extract_field(isar5, 8);
        if (block >= 1)
                elf_hwcap2 |= HWCAP2_SHA1;

        block = cpuid_feature_extract_field(isar5, 12);
        if (block >= 1)
                elf_hwcap2 |= HWCAP2_SHA2;

        block = cpuid_feature_extract_field(isar5, 16);
        if (block >= 1)
                elf_hwcap2 |= HWCAP2_CRC32;
    }


``cpuid_init_hwcaps`` 用于获得系统指定的硬件支持信息


create_mapping
==================




__create_mapping
===================

::

    //mm: 指向进程的mm_struct结构
    //map_desc: 指向映射关系
    //alloc: 指向分配函数
    static void __init __create_mapping(struct mm_struct *mm, struct map_desc *md,
                void *(*alloc)(unsigned long sz), bool ng)
    {
        unsigned long addr, length, end;
        phys_addr_t phys;
        const struct mem_types *type;
        pgd_t *pgd;

        //获取内存类型
        type = &mem_types[md->type];

        #ifndef CONFIG_ARM_LPAE
        if(md->pfn >= 0x1000000)
            create_36bit_mapping(mm, md, type, ng);
            return;
        #endif

        //从映射关系结构中获得虚拟地址
        addr = md->virtual & PAGE_MASK;
        //获得物理地址
        phys = __pfn_to_phys(md->pfn);
        length = PAGE_ALIGN(md->length + (md->virtual & ~PAGE_MASK));

        if(type->prot_l1 == 0 && ((addr | phys | length) & ~SECTION_MASK))
            return;

        //获得虚拟地址addr对应的PGD入口
        pgd = pgd_offset(mm, addr);
        //计算终止的虚拟地址
        end = addr + length;

        do {
            //获得下一个pgd入口对应的虚拟地址
            unsigned long next = pgd_addr_end(addr, end);
            //分配获得初始化一个pud入口地址
            alloc_init_pud(pgd, addr, next, phys, type, alloc, ng);

            phys += next - addr;
            addr = next;
        } while(pgd++, addr != end);
    }


``__create_mapping`` 作用就是建立页表




current_stack_pointer
=======================

::

    register unsigned long current_stack_pointer asm("sp");


``current_stack_pointer`` 用于读取当前堆栈的值



current_thread_info
======================

::

    static inline struct thread_info *current_thread_info(void)
    {
        return (struct thread_inf *) (current_stack_pointer & ~(THREAD_SIZE - 1));

    }

``current_thread_info`` 用于获得当前进程的thread_info结构．在linux内核中，进程将thread_info与进程的内核态堆栈捆绑在同一块
区域内，区域的大小为THREAD_SIZE．通过一定的算法，只要知道进程内核态堆栈的地址，也就可以推断出thread_info的地址．

































