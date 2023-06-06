add_static_vm_early
========================

::

    void __init add_static_vm_early(struct static_vm *svm)
    {
        struct static_vm *curr_svm;
        struct vm_struct *vm;
        void *vaddr;

        vm = &svm->vm;
        vm_area_add_early(vm);
        vaddr = vm->addr;

        list_for_each_entry(curr_svm, &static_vmlist, list) {
            vm = &curr_svm->vm;
            if(vm->addr > vaddr)
                break;
        }
        list_add_tail(&svm->list, &curr_svm->list);
    }


``add_static_vm_early`` 函数用于内核启动早期，将一个static_vm加入到内核维护的vmlist和static_vmlist里．函数首先获得参数svm对应的vm,并通过函数
vm_area_add_early函数将该vm加入到系统早期的vmlist里．函数接着使用list_for_each_entry函数遍历系统的static_vmlist链表，直到链表中找到一个成员的
地址大于svm对应的地址，然后调用list_add_tail函数添加到链表的当前位置



adjust_lowmem_bounds
=====================

::

    void __init adjust_lowmem_bounds(void)
    {
        phys_addr_t memblock_limit = 0;
        u64 vmalloc_limit;
        struct memblock_region *reg;
        phys_addr_t lowmem_limit = 0;

        vmaloc_limit = (u64)(uintptr_t)vmalloc_min - PAGE_OFFSET + PHYS_OFFSET;

        //遍历MEMBLOCK内存分配器的memory可用物理内存区域内的所有regions
        for_each_memblock(memory, reg) {
            //每遍历一块内存区，获取该内存区的起始和终止地址
            phys_addr_t block_start = reg->base;
            phys_addr_t block_end = reg->base + reg->size;

            //如果该内存区的地址小于vmalloc_limit
            if(reg->base < vmalloc_limit) {
                if(block_end > lowmem_limit) 
                    lowmem_limit = min_t(u64, vmalloc_limit, block_end);

                    //进行内存对齐
                    if(!memblock_limit) {
                        if(!IS_ALIGNED(block_start, PMG_SIZE))
                            memblock_limit = block_start;
                        else if(!IS_ALIGNED(block_end, PMD_SIZE))
                            memblock_limit = lowmem_limit;
                    }
            }
        }
        arm_lowmem_limit = lowmem_limit;
        high_memory = __va(arm_lowmem_limit - 1) + 1;

        if(!memblock_limit)
            memblock_limit = arm_lowmem_limit;

        memblock_limit = round_down(memblock_limit, PMD_SIZE);

        if(!IS_ENABLED(CONFIG_HIGHMEM) || cache_is_vipt_aliasing()) {
            if(memblock_end_of_DRAM() > arm_lowmem_limit) {
                phys_addr_t end = memblock_end_of_DRAM();

                pr_notice("Ignoring RAM at %pa-%pa\n", &memblock_limit, &end);
                pr_notice("Consider using a HIGHMEM enabled kernel.\n");

                memblock_remove(memblock_limit, end - memblock_limit);
            }
        }

        memblock_set_current_limit(memblock_limit);
    }


``adjust_lowmem_bounds`` 用于调整获得低端物理内存的边界，该函数主要在内存初始化阶段调用，用于确定可用的低端内存范围．

在linux内核中，物理内存被分为两个区域: ``低端内存`` 和 ``高端内存`` .低端内存是位于物理地址较低的区域，通常包含操作系统内核和常用的数据结构，
例如页表，任务状态段等．高端内存则是位于物理地址较高的区域，用于存储用户进程的堆栈，缓冲区等

::

    vmaloc_limit = (u64)(uintptr_t)vmalloc_min - PAGE_OFFSET + PHYS_OFFSET;


vmaloc_limit用于存储vmalloc内存区的极值，lowmem_limit用于存储低端物理内存的限值

.. note::
    - vmalloc_min: VMALLOC内存区的最低地址

    - PAGE_OFFSET: 内核虚拟地址的起始地址

    - PHYS_OFFSET: DRAM在地址总线行的偏移，即DRAM的物理地址


alloc_init_pmd
==================

::

    static void __init alloc_init_pwd(pud_t *pud, unsigned long addr, unsigned long end,
                        phys_addr_t phys, cosnt struct mem_type *type,
                        void *(alloc)(unsigned long sz), bool ng)
    {
        pmd_t *pmd = pmd_offset(pud, addr);
        unsigned long next;

        do {
            //获取addr对应的下一个PMD入口
            next = pmd_addr_end(addr, end);

            if(type->port_sect &&
                ((addr | next | phys) & ~SECTION_MASK) == 0)
                //初始化PMD入口项
                __map_init_section(pmd, addr, next, phys, type, ng);
            else
                //反之则分配一个pte页并初始化PMD入口项
                alloc_init_pte(pmd, addr, next, __phys_to_pfn(phys), type, alloc, ng);
    
            //增加phys和pmd的值
            phys += next - addr;

        } while(pmd++, addr = next, addr != end);
    }


``alloc_init_pmd`` 用于分配或初始化一个页表中间级页表(PMD)入口

- pud: 指向PUD入口

- addr: 虚拟地址

- end: 结束虚拟地址

- phys: 指向物理地址

- type: 指向内存类型

- alloc: 指向分配函数




alloc_init_pud
===================


::

    static void __init alloc_init_pud(pgd_t *pgd, unsigned long addr,
        unsigned long end, phys_addr_t phys, const struct mem_type,
        void *(*alloc)(unsigned long sz), bool ng)
    {
        pud_t *pud = pud_offset(pgd, addr);

        do {
            next = pud_addr_end(addr, end);
            alloc_init_pmd(pud, addr, next, phys, type, alloc, ng);
            phys += next - addr;
        } while(pud++, addr = next, addr != end);
    }


``alloc_init_pud`` 用于分配并初始化一个页表顶级页表(PUD)的条目

.. note::

    页表是用于虚拟地址到物理地址的映射的数据结构．
    页表层次结构包含多个级别，其中最顶级的页表是页表顶级页表(PUD)


- PGD(Page Global Directory): 是页表的最顶层目录，用于建立虚拟地址到物理地址的映射关系．每个PGD条目对应一个PGD表，其中包含多个PUD条目

- PUD(Page Upper Directory): 是页表的第二级目录，用于映射较大范围的虚拟地址空间，每个PUD条目对应一个PUD表，其中包含多个PMD条目

- PMD(Page Middle Directory): 是页表的第三级目录，用于映射较中等范围的虚拟地址空间，每个PMD条目对应一个PMD表，其中包含多个页表项

- PT(Page Table): 是页表的最底层目录，用于映射较小范围的虚拟地址空间，每个PT条目对应一个物理页面，用于存储页表项

::

                +---------------------------------------+
                |                PGD                    |
                |                                       |
                |          +------------------------+   |
                |          |          PUD           |   |
                |          |                        |   |
                |          |   +----------------+   |   |
                |          |   |      PMD       |   |   |
                |          |   |                |   |   |
                |          |   |   +--------+   |   |   |
                |          |   |   |   PT   |   |   |   |
                |          |   |   +--------+   |   |   |
                |          |   |                |   |   |
                |          |   +----------------+   |   |
                |          |                        |   |
                |          +------------------------+   |
                |                                       |
                +---------------------------------------+


alloc_node_mem_map
=====================

::
    
    static void __ref alloc_node_mem_map(struct pglist_data *pgdat)
    {
        unsigned long __maybe_unused start = 0;
        unsigned long __maybe_unused offset = 0;

        //判断pgdat对应的节点是否包含物理页帧
        if(!pgdat->node_spanned_pages)
            return;

        //进行MAX_ORDER_NR_PAGES对齐
        start = pgdat->node_start_pfn & ~ (MAX_ORDER_NR_PAGES - 1);
        offset = pgdate->node_start_pfn - start;

        if(!pgdat->node_mem_map) {
            unsigned long size, end;
            struct page *map;

            end = pgdat_end_pfn(pgdat);
            end = ALIGN(end, MAX_ORDER_NR_PAGES);
            size = (end - start) * sizeof(struct page);
            map = memblock_alloc_node_nopanic(size, pgdat->node_id);
            pgdat->node_mem_map = map + offset;
        }
        #ifndef CONFIG_NEED_MULTIPLE_NODES
        if(pgdat == NODE_DATA(0)) {
            mem_map = NODE_DATA(0)->node_mem_map;
        #if defined(CONFIG_HAVE_MEMBLOCK_NODE_MAPE) || defined(CONFIG_FLATMEM)
            if(papge_to_pfn(mem_map) != pgdat->node_start_pfn)
                mem_map -= offset;
        #endif
        }
        #endif
    }

``alloc_nod_mem_map`` 用于创建全局struct page数组mem_map,并将mem_map与节点0的物理页帧进行映射



ARRAY_SIZE
=============


::

    #define ARRAY_SIZE(arr) (sizeof(arr) / sizeof((arr)[0]) + __must_be_array(arr))


用于计算数组中成员的个数


arch_get_next_mach
======================

::

    static const void * __init arch_get_next_mach(const char *const **match)
    {
        static const struct machine_desc *mdesc = __arch_info_begin;
        const struct machine_desc *m = mdesc;

        if(m >= __arch_info_end)
            return NULL;

        mdesc++;
        *match = m->dt_compat;
        return m;
    }


``arch_get_next_mach`` 用于获得下一个machine_desc结构的device tree compatible strings地址．




arch_local_irq_disable
===========================

::

    static inline void arch_local_irq_disable(void)
    {
        asm_volatile(
            "   cpsid i @ arch_local_irq_disable"
            :
            :
            : "memory", "cc");
    }

在ARMV7版本中通过arch_local_irq_disable函数实现禁止本地中断，CPSID指令与I参数用该与将CPSR寄存器中的interrupt标志位清零，以此禁止本地中断




arm_adjust_dma_zone
======================

::

    static void __init arm_adjust_dma_zone(unsigned long *size, unsigned long *hole,
                unsigned long dma_size)
    {
        if(size[0] <= dma_size)
            return;

        size[ZONE_NORMAL] = size[0] - dma_size;
        size[ZONE_DMA] = dma_size;
        hole[ZONE_NORMAL] = hole[0];
        holo[ZONE_DMA] = 0;
    }

``arm_adjust_dma_zone`` 用于调整DMA_ZONE和NORMAL_ZONE统计数组

- size: 指向可用物理页帧数组

- hole: 指向碎片物理页帧数组

- dma_size: 指向DMA_ZONE占用的物理页帧


arm_initrd_init
=================

::

    static void __init arm_initrd_init(void)
    {
    #ifdef CONFIG_BLK_DEV_INITRD
        phys_addr_t start;
        unsigned long size;

        initrd_start = initrd_end = 0;

        if(!phys_initrd_size)
            return;

        //对start和size进行PAGE_SIZE对齐操作
        start = round_down(phys_initrd_start, PAGE_SIZE);
        size = phys_initrd_size + (phys_initrd_start - start);
        size = round_up(size, PAGE_SIZE);
        
        //判断start和size对应的内存区域是否在MEMBLOCK的reserved和memory区域内
        if(!memblock_is_region_memory(start, size)) 
            return;

        if(memblock_is_region_reserved(start, size))
            return;

        //通过检查后，将start和size对应的区域加入到MEMBLOCK的预留区域内
        memblock_reserve(start, size);

        //并将phys_initd_start对应的虚拟地址赋值给initd_start
        initrd_start = __phys_to_virt(phys_initrd_start);
        initrd_end = initrd_start + phys_initrd_size;

    #endif
    }



``arm_initrd_init`` 将initrd所占用的物理内存加入到memblock内存分配器的预留区内

.. note::
    系统启动过程中，uboot将initrd占用的物理地址信息存储在dtb的chosen节点内，在early_init_dt_check_for_initrd函数中，
    从dtb中解析出inird的物理信息存储在phy_initrd_start和phys_initrd_size两个全局变量里


arm_pte_alloc
===============

::

    static pte_t * __init arm_pte_alloc(pmd_t *pmd, unsigned long addr,
                unsigned long prot, void *(*alloc)(unsigned long sz))
    {
        //判断pmd是否为空
        if(pmd_none(*pmd)) { 
            //使用alloc函数进行内存分配，长度为PTE_HWTABLE_OFF + PTE_HWTABLE_SIZE
            pte_t *pte = alloc(PTE_HWTABLE_OFF + PTE_HWTABLE_SIZE);
            //将PTE填充到PMD入口项里
            __pmd_populate(pmd, __pa(pte), prot);
        }

        //检测pmd入口项的有效性
        BUG_ON(pmd_bad(*pmd));
        //返回addr虚拟地址对应的pte入口
        return pte_offset_kernel(pmd, addr);
    }


``arm_pte_alloc`` 用于分配并安装一个新的PTE页表

- pmd: 指向PMD入口

- addr: 指向虚拟地址

- prot: 指向页表属性

- alloc: 执行内存分配函数



arm_memblock_init
====================


::

    void __init arm_memblock_init(const struct machine_desc *mdesc)
    {
        //将内核镜像所在的物理块加入到保留区
        memblock_reserved(__pa(KERNEL_START), KERNEL_END - KERNEL_START);

        //将INITRD所占用的物理内存区加入到保留区
        arm_initrd_init();

        //将内核全局页目录所在的物理地址加入到保留区内
        arm_mm_memblock_reserve();

        //将dtb memory reserved mapping中指定的区域加入到保留区
        if(mdesc->reserve)
            mdesc->reserve();

        early_init_fdt_reserve_self();
        early_init_fdt_scan_reserved_mem();

        dma_contiguous_reserve(arm_dma_limit);

        arm_memblock_steal_permitted = false;
        memblock_dump_all();
    }

``arm_memblock_init`` 用于将系统需要预留的内存加入到MEMBLOCK内存分配器的预留区域中



arm_mm_memblock_reserve
==========================


::

    void __init arm_mm_memblock_reserve(void)
    {
        memblock_reserve(__pa(swapper_pg_dir), SWAPPER_PG_DIR_SIZE);

        #ifdef CONFIG_SA1111
        memblock_reserve(PHYS_OFFSET, __pa(swapper_pg_dir) - PHYS_OFFSET);
        #endif
    }













