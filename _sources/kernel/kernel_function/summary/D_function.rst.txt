dev_get_cma_area
==================

::

    static inline struct cma *dev_get_cma_area(struct device *dev)
    {
        if(dev && dev->cma_area)
            return dev->cma_area;

        return dma_contiguous_default_area;
    }
    
``dev_get_cma_area`` 用于获得设备对应的cma信息，如果设备没有配置cma信息，则使用默认的CMA区域dma_contiguous_default_area


dev_set_cma_area
==================

::

    static inline void dev_set_cma_area(struct device *dev, struct cma *cma)
    {
        if(dev)
            dev->cma_area = cma;
    }


devicemaps_init
=================


::

    static void __init devicemaps_init(const struct machine_desc *mdesc)
    {
        struct map_desc map;
        unsigned long addr;
        void *vectors;

        //首先为新的异常向量表分配内存空间
        vectors = early_alloc(PAGE_SIZE * 2);

        //将系统的异常向量表和特定的函数拷贝到新的异常向量表所在的空间
        early_trap_init(vectors);

        //将VMALLOC_START和FIXMAP之间的虚拟地址的PMD入口清零
        for(addr = VMALLOC_START; addr < (FIXADDR_TOP & PMD_MASK); addr += PMD_SIZE)
            pmd_clear(pmd_off_k(addr));

        //如果系统定义了以下几个宏，则为这几个IO或设备建立页表
    #ifdef CONFIG_XIP_KERNEL
        map.pfn = __phys_to_pfn(CONFIG_XIP_PHYS_ADDR & SECTION_MASK);
        map.virtual = MODULES_VADDR;
        map.length = ((unsigned long)_exiprom - map.virtual + ~SECTION_MASK) & SECTION_MASK;
        map.type = MT_ROM;
        create_mapping(&map);
    #endif

    #ifdef FLUSH_BASE
        map.pfn = __phys_to_pfn(FLUSH_BASE_PHYS);
        map.virtual = FLUSH_BASE;
        map.length = SZ_1M;
        map.type = MT_CACHECLEAN;
        create_mapping(&map);
    #endif

    #ifdef FLUSH_BASE_MINICACHE
        map.pfn = __phys_to_pfn(FLUSH_BASE_PHYS + SZ_1M);
        map.virtual = FLUSH_BASE_MINICACHE;
        map.length = SZ_1M;
        map.type = MT_CACHECLEAN;
        create_mapping(&map);
    #endif

        //为新的异常向量表建立页表
        map.pfn = __phys_to_pfn(virt_to_phys(vectors));
        //设置页表的虚拟地址
        map.virtual = 0xffff0000;
        map.length = PAGE_SIZE;
    #ifdef CONFIG_KUSER_HELPERS
        map.type = MT_HIGH_VECTORS;
    #else
        map.type = MT_LOW_VECTORS;
    #endif
        //建立页表
        create_mapping(&map);

        //判断异常向量表是否在高地址，如果不在高地址，则为低端的异常向量表建立映射
        if(!vectors_high()) {
            map.virtual = 0;
            map.length = PAGE_SIZE * 2;
            map.type = MT_LOW_VECTORS;
            create_mapping(&map);
        }

        //建立一个只读的页表
        map.pnf += 1;
        map.virtual = 0xffff0000 + PAGE_SIZE;
        map.length = PAGE_SIZE;
        map.type = MT_LOW_VECTORS;
        create_mapping(&map);

        //如果包含了体系相关的IO映射，则调用对应的映射函数
        if(mdesc->map_io)
            mdesc->map_io();
        else
            debug_ll_io_init();

        //IO或设备建立的映射中PMD只使用了其中一个入口，将另外一个空的PMD入口填充
        fill_pmd_pages();

        //为PCI设备建立映射
        pci_reserve_io();

        //刷新TLB和cache
        local_flush_tlb_all();
        flush_cache_all();

        //使能同步ABORT异常处理
        early_abt_enable();
    }


``devicemaps_init`` 用于IO设备建立映射




dma_alloc_from_contiguous
===========================

::

    struct page *dma_alloc_from_contiguous(struct device *dev, size_t count,
                                    unsigned int align, bool no_warn)
    {
        if(align > CONFIG_CMA_ALIGNMENT)
            align = CONFIG_CMA_ALIGNMENT;

        return cma_alloc(dev_get_cma_area(dev), count, align, no_warn);
    }

``dma_alloc_from_contiguous`` 用于从系统中分配指定长度的连续物理内存




dma_contiguous_early_fixup
============================

::
    
    void __init dma_contiguous_early_fixup(phys_addr_t base, unsigned long size)
    {
        dma_mmu_remap[dma_mmu_remap_num].base = base;
        dma_mmu_remap[dma_mmu_remap_num].size = size;
        dma_mmu_remap_num++;
    }

``dma_contiguous_early_fixup`` 将一个区域加入到系统DMA映射数组dma_mmu_remap中



dma_contiguous_remap
======================

::

    void __init dma_contiguous_remap(void)
    {
        int i;
        //遍历dma_mmu_remap成员
        for(i = 0; i < dma_mmu_remap_num; i++) {
            phys_addr_t start = dma_mmu_remap[i].base;
            phys_addr_t end = start + dma_mmu_remap[i].size;
            struct map_desc map;
            unsigned long addr;

            //检查物理地址是否超出低端物理地址的范围
            if(end > arm_lowmem_limit)
                end = arm_lowmem_limit;
            if(start >= end)
                continue;

            map.pfn = __phys_to_pfn(start);
            map.virtual = __phys_to_pfn(start);
            map.length = end - start;
            map.type = MT_MEMORY_DMA_READY;

            for(addr = __phys_to_virt(start); addr < __phys_to_virt(end); addr += PMD_SIZE)
                pmd_clear(pmd_off_k(addr));

            flush_tlb_kernel_range(__phys_to_virt(start), __phys_to_virt(end));

            iotable_init(&map, 1);
        }
    }

``dma_contiguous_remap`` 将连续物理内存CMA重新建立页表




dma_contiguous_reserve
============================

::

    //limit: 最大可用的物理地址
    void __init dma_contiguous_reserve(phys_addr_t limit)
    {
        phys_addr_t selected_size = 0;
        phys_addr_t selected_base = 0;
        phys_addr_t selected_limit = limit;
        bool fixed = false;

        //如果size_cmdline不为-1,则根据cmdline中包含的内容构建
        if(size_cmdline != -1)  {
            selected_size = size_cmdline;
            selected_base = base_cmdline;
            selected_limit = min_not_zero(limit_cmdline, limit);
            if(base_cmdline + size_cmdline == limit_cmdline)
                fixed = true;
        } else {
        #ifdef CONFIG_CMA_SIZE_SEL_MBYTES
            selected_size = size_bytes;
        #elif defined(CONFIG_CMA_SIZE_SEL_PERCENTAGE)
            selected_size = cma_early_percent_memory();
        #elif defined(CONFIG_CMA_SIZE_SEL_MIN)
            selected_size = min(size_bytes, cma_early_percent_memory());
        #elif defined(CONFIG_CMA_SIZE_SEL_MAX)
            selected_size = max(size_bytes, cma_early_percent_memory());
        #endif
        }
        if(selected_size &&&&& !dma_contiguous_default_area) {
            dma_contiguous_reserve_area(selected_size, selected_base, selected_limit,
                                &dma_contiguous_default_area, fixed);
        }

    }

``dma_contiguous_reserve`` 将一块物理内存区预留做连续物理内存使用．


dma_contiguous_set_default
=============================

::

    static inline void dma_contiguous_set_default(struct cma *cma)
    {
        dma_contiguous_default_area = cma;
    }




dma_release_from_contiguous
==============================

::

    bool dma_release_from_contiguous(struct device *dev, struct page *pages, int count)
    {
        return cma_release(dev_get_cma_area(dev), pages, count);
    }

``dma_release_from_contiguous`` 用于释放一段连续物理内存到CMA



do_early_param
===================

::

    //param: 指向参数名字
    //val: 指向参数的值
    //unused: 表示是否使用过
    static int __init do_early_param(char *param, char *val,
                                const char *unused, void *arg)
    {
        const struct obs_kernel_param *p;

        for(p = __set_start; p < __setup_end; p++) {
            if((p->early && parameq(param, p->str)) || (strcmp(param, "console") == 0 &&
            strcmp(p->str, "earlycon") == 0)) {
                if(p->setup_func(val) != 0)
                    pr_warn("Malformed early option '%s'\n", param);
            }
        }

        return 0;
    }

``do_early_param`` 用于从cmdline中设置内核早期启动需要的参数．cmdline对应的参数在内核源码中可以通过__setup()函数进行设置，
函数会将设置的参数加入到".init.setup" section中，并且__setup_start指向该section开始的位置，__setup_end指向该section结束的
位置



dt_mem_next_cell
===================

::

    u64 __init dt_mem_next_cell(int s, const __be32 **cellp)
    {
        const __be32 *p = *cellp;

        *cellp = p + s;
        return of_read_number(p, s);
    }

``dt_mem_next_cell`` 从DTB memory节点中读取reg属性的值




dump_stack_set_arch_desc
===========================

::

    void __init dump_stack_set_arch_desc(const char *fmt, ...)
    {
        va_list args;

        va_start(args, fmt);
        vsnprintf(dump_stack_arch_desc_str, sizeof(dump_stack_arch_desc_str), fmt, args);
        va_end(args);
    }


``dump_stack_set_arch_desc`` 用于将体系名字信息写入全局变量dump_stack_arch_desc_str里























