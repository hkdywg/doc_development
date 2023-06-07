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

::

    int __init cma_declare_contiguous(phys_addr_t base, phys_addr_t size, phys_addr_t limit,
        phys_addr_t al)



cma_early_percent_memory
=========================




cma_for_each_area
====================



cma_get_base
===============




cma_get_name
==============




cma_get_size
===============




cma_init_reserved_areas
=========================






cma_init_reserved_mem
=========================





cma_release
==============



__cpu_active_mask
===================



__cpu_architecture
=====================





cpu_architecture
===================







cpu_has_aliasing_icache
==========================





cpu_init
===========








cpu_logical_map
===================





cpu_max_bits_warn
====================




__cpu_online_mask
====================





__cpu_possible_mask
=====================



__cpu_present_mask
=====================




cpu_proc_init
===============






CPU_TO_FDT32
===============






cpuid_feature_extract
=======================




cpuid_feature_extract_field
=============================




cpuid_init_hwcaps
=====================





cpumask_bits
===============




cpumask_check
=================



cpumsk_clear_cpu
===================





cpumask_set_cpu
=================





create_mapping
==================




__create_mapping
===================




current_stack_pointer
=======================







current_thread_info
======================


































