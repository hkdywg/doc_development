early_alloc
===============

::

    static void __init *early_alloc(unsigned long sz)
    {
        return early_alloc_aligned(sz, sz);
    }


``early_alloc`` 用于早期分配指定长度的物理内存．参数sz指向需求物理内存的长度


early_alloc_aligned
=======================

::

    static void __init *early_alloc_aligned(unsigned long sz, unsigned long align)
    {
        void *ptr = __va(memblock_phys_alloc(sz, align));
        memset(ptr, 0, sz);
        return ptr;
    }


``early_alloc_aligned`` 用于早期分配指定长度的物理内存，参数sz指向需求物理内存的长度，align指向对齐方式


early_cma
============

::

    static int __init early_cma(char *p)
    {
        if(!p)
            return -EINVAL;

        //解析cmdline的长度
        size_cmdline = memparse(p, &p);
        //判断字符串中是否含有"@"字符
        if(*p != '@')
            return 0;
        base_cmdline = memparse(p + 1, &p);
        if(*p != '-') {
            limit_cmdline = base_cmdline + size_cmdline;
            return 0;
        }
        limit_cmdline = memparse(p + 1, &p);
            
        return 0;
    }
    early_param("cma", early_cma);


``early_cma`` 用于从CMDLINE中解析"cma="参数，cma参数支持的格式如下

::

    cma=nn[MG]@[start][MG][-end[MG]]

    例如:

    "cma=20M@0x68000000-0x70000000"


上面的例子就是CMA的大小为20M,这20M物理内存必须在0x68000000-0x70000000范围内查找．


early_fixmap_shutdown
=======================

::

    static void __init early_fixmap_shutdown(void)
    {
        int i;
        //获得__end_Of_permanent_fixed_addresses对应的虚拟地址
        unsigned long va = fix_to_virt(__end_of_permanent_fixed_addresses - 1);

        pte_offset_fixmap = pte_offset_late_fixmap;
        //清除虚拟地址对应的PMD入口
        pmd_clear(fixmap_pmd(va));
        //刷新tbl
        local_flush_tlb_kernel_page(va);

        for(i = 0; i < __end_of_permanent_fixed_addresses; i++) {
            pte_t *pte;
            struct map_desc map;

            //获得FIXMAP区域内的虚拟地址
            map.virtual = fix_to_virt(i);
            //获得虚拟地址对应的PTE入口
            pte = pte_offset_early_fixmap(pmd_off_k(map.virtual), map.virtual);

            //如果PTE为空或者PTE表项不包含L_PTE_MT_DEV_SHARD，那么不为其建立页表，结束本次循环
            if(pte_none(*pte) || (pte_val(*pte) & L_PTE_MT_MASK) != L_PTE_MT_DEV_SHARED)
                continue;

            //
            map.pfn = pte_pfn(*pte);
            map.type = MT_DEVICE;
            map.length = PAGE_SIZE;

            //建立页表
            create_mapping(&map);
        }
    }


``early_fixmap_shutdown`` 作用是为FIXMAP区域建立页表



early_ioremap_init
====================

::

    void __init early_ioremap_init(void)
    {
        early_ioremap_setup();
    }


``early_ioremap_init`` 用于初始化早期的I/O使用的虚拟地址


early_ioremap_setup
=====================

::

    void __init early_ioremap_setup(void)
    {
        int  i;

        for(i = 0; i < FIX_BTMAPS_SLOTS; i++)
            if(WARN_ON(prev_map[i]))
                break;

        for(i = 0; i < FIX_BTMAPS_SLOTS; i++)
            //将所有SLOT对应的虚拟地址存储在slot_virt数组中
            slot_virt[i] = __fix_to_virt(FIX_BTMAP_BEGIN - NR_FIX_BTMAPS * i);
    }

``early_ioremap_setup`` 设置早期I/O映射的虚拟地址,函数在FIXMAP内存区域分配了一块虚拟地址给早期的I/O使用,
一个包含FIX_BTMAPS_SLOTS个slot，每个slot包含了NR_FIX_BTMAPS


early_init_dt_add_memory_arch
=================================

::

    //base: 物理内存的基地址
    //size: 物理内存的长度
    void __init __weak early_init_dt_add_memory_arch(u64 base, u64 size)
    {
        const u64 phys_offset = MIN_MEMBLOCK_ADDR;

        //将基地址和长度与MEMBLOCK管理的最大和最小物理内存信息做检测
        if(size < PAGE_SIZE - (base & ~PAGE_MASK)) {
           return; 
        }

        if(!PAGE_ALIGNED(base)) {
            size -= PAGE_SIZE - (base & ~PAGE_MASK);
            base = PAGE_ALIGN(base);
        }
        size &= PAGE_MASK;

        if(base > MAX_MEMBLOCK_ADDR)
            return;

        if(base + size - 1 > MAX_MEMBLOCK_ADDR)
            size = MAX_MEMBLOCK_ADDR - base + 1;

        if(base + size < phys_offset)
            return;

        if(base < phys_offset) { 
            size -= phys_offset - base;
            base = phys_offset;
        }
        //将物理内存信息更新到MEMBLOCK内存管理器里
        memblock_add(base, size);
    }


``early_init_dt_add_memory_arch`` 用于从DTB中获得内存的基地址和长度之后，进行对齐和检测操作，并将基地址对应
长度的物理内存信息添加到MEMBLOCK内存管理器里


early_init_dt_alloc_reserved_memory_arch
============================================

::

    //size: 分配大小
    //align: 对齐方式
    //start: 可以分配的起始地址
    //end: 可以分配的终止地址
    //nomap: 指明是否为预留区内存建立页表
    //res_base: 用于分配物理内存的起始地址
    int __init __weak early_init_dt_alloc_reserved_memory_arch(phys_addr_t size,
        phys_addr_t align, phys_addr_t start, phys_addr_t end, bool nomap, phys_addr_t *res_base)
    {
        phys_addr_t base;

        //判断end和align是否符合要求，并处理
        end = !end ? MEMBLOCK_ALLOC_ANYWHERE : end;
        align  = !align ? SMP_CACHE_BYTES : align;
        //从指定的物理内存中分配所需要大小的物理内存
        base = __memblock_alloc_base(size, align, end);
        if(!base)
            return -ENOMEM;

        //如果分配的地址小于指定的起始地址，则释放申请的内存并退出
        if(base < start) {
            memblock_free(base, size);
            return -ENOMEM;
        }

        //将申请的物理内存地址写入res_base中
        *res_base = base;
        //如果不需要对新分配的物理内存建立页表
        if(nomap)
            return memblock_remove(base, size);

        return 0;

    }


``early_init_dt_alloc_reserved_memory_arch`` 用于为DTS中"reseved-memory"节点中的特定预留区分配物理内存，该类预留区不包含"reg"属性，
只包含"size"属性，因此需要对这里预留区分配物理内存




early_init_dt_check_for_initrd
==================================

::

    //node: 代表chosen节点在dtb区域内的偏移
    static void __init early_init_dt_check_for_initrd(unsigned long node)
    {
        u64 start, end;
        int len;
        const __be32 *prop;

        //获得linux,initrd-start属性值
        prop = of_get_flat_dt_prop(node, "linux,initrd-start", &len);
        if(!prop)
            return;
        start =  of_read_number(prop, len/4);

        //获得linux,initrd-end属性值
        prop = of_get_flat_dt_prop(node, "linux,initrd-end", &len);
        if(!prop)
            return;
        end = of_read_number(prop, len/4);

        //将inird的地址写入全局变量initrd_start, initrd_end中
        __early_init_dt_declare_initrd(start, end);
        phys_initrd_start = start;
        phys_initrd_size = end - start;
    }

``early_init_dt_check_for_initrd`` 用于从DTB中读出INITRD信息，并设置INITRD相关的全局变量





__early_init_dt_declare_initrd
===================================

::

    static void __early_init_dt_declare_initd(unsigned long start, unsigned long end)
    {
        if(!IS_ENABLED(CONFIG_ARM64)) {
            initrd_start = (unsigned long)__va(start);
            initrd_end = (unsigned long)__va(end);
            initrd_below_start_ok = 1;
        }
    }


``__early_init_dt_declare_initrd`` 用于在系统启动早期，设置INITRD的范围．

 
early_init_dt_reserve_memory_arch
====================================

::

    //base: 指向DTB占用物理内存区的起始地址
    //size: 大小
    //nomap: 是否给DTB占用的物理内存建立页表
    int __init __weak early_init_dt_reserve_memory_arch(phys_addr_t base,
                    phys_addr_t size, bool nomap)
    {
        if(nomap)
            return memblock_remove(base, size);
        return memblock_reserve(base, size);
    }

``early_init_dt_reserve_memory_arch`` 根据不同的条件，将DTB占用的物理内存加入到MEMBLOCK的指定区域


early_init_dt_scan_chosen
===========================

::

    //node: dtb中chosen节点在dtb devicetree structure区域内的偏移
    //uname: chosen节点的节点名字
    //depth: chosen字节点的前套数
    //data: 指向cmdline
    int __init early_init_dt_scan_chosen(unsigned long node, const char *name,
                                    int depth, void *data)
    { 
        int l;
        const char *p;

        //检查depth及data有效性
        //检查节点名字是否为chosen或chosen@0
        if(depth != 1 || !data || (strcmp(uname, "chosen") != 0 && strcmp(uname, "chosen@0") != 0))
            return 0;

        //从dtb的chosen节点中读取并设置initrd相关的数据
        early_init_dt_check_for_initrd(node);

        //读取bootargs属性值，如果存在则拷贝到data
        p = of_get_flat_dt_prop(node, "bootargs", &l);
        if(p != NULL && l > 0)
            strlcpy(data, p, min((int)l, COMMAND_LINE_SIZE));

    #ifdef   CONFIG_CMDLINE
    #if defined(CONFIG_CMDLINE_EXTEND)
        //如果存在CONFIG_CMDLINE_EXTEND宏，则将其中的cmdline拼接到data后
        strlcat(data, " ", COMMAND_LINE_SIZE);
        strlcat(data, CONFIG_CMDLINE, COMMAND_LINE_SIZE);
    #if defined(CONFIG_CMDLINE_FORCE)
        strlcpy(CONFIG_CMDLINE, COMMAND_LINE_SIZE);
    #else
        if(!((char *)data)[0])
            strlcpy(data, CONFIG_CMDLINE, COMMAND_LINE_SIZE);
    #endif
    #endif

        return 1;
    }

``early_init_dt_scan_chosen`` 用于从DTB的chosen节点中读取bootargs参数并与内核提供的CMDLINE,最终合成系统启动时需要的cmdline.


early_init_dt_scan_memory
=============================

::

    //node: 指向节点的偏移
    //uname: 节点名字
    //depth: 节点深度
    //data: 私有数据
    int __init early_init_dt_scan_memory(unsigned long node, const char *uname,
                                    int depth, void *data)
    {
        //获得当前节点的device_type属性值
        const char *type = of_get_flat_dt_prop(node, "device_type", NULL);
        cosnt __be32 *reg, *endp;
        int l;
        bool hotpluggable;
        //如果属性值不存在或不是memory则直接返回
        if(type == NULL || strcmp(type, "memory") != 0)
            return 0;
        //读取linux,usable-memory属性值，如果不存在则读取reg属性值
        reg = of_get_flat_dt_prop(node, "linux,usable-memory", &l);
        if(reg == NULL)
            reg = of_get_flat_dt_prop(node, "reg", &l);
        if(reg == NULL)
            return 0;
        
        //
        endp = reg + (1 / sizeof(__be32));
        hotpluggable = of_get_flat_dt_prop(node, "hotpluggable", NULL);

        while((endp - reg) >= (dt_root_addr_cells + dt_root_size_cells)) {
            u64 base, size;

            base = dt_mem_next_cell(dt_root_addr_cells, &reg);
            size = dt_mem_next_cell(dt_root_size_cells, &reg);

            if(size == 0)
                continue;

            early_init_dt_add_memory_arch(base, size);

            //如果系统不支持热拔插的内存条则结束本次循环
            if(!hotpluggable)
                continue;

        }
        return 0;
    }


``early_init_dt_scan_memory`` 用于获得DTB memory节点的信息，即物理内存的信息，并将物理内存的信息更新到MEMBLOCK内存分配器中．




early_init_dt_sacn_nodes
===========================

::

    void __init early_init_dt_scan_nodes(void)
    {
        int rc = 0;

        //获得cmdline信息
        rc = of_scan_flat_dt(early_init_dt_scan_chosen, boot_command_line);

        //获得根节点的address-cells和size-cells信息
        of_scan_flat_dt(early_init_dt_scan_root, NULL);

        //获得内存信息
        of_scan_flat_dt(early_init_dt_scan_memory, NULL);
    }

``early_init_dt_scan_nodes`` 用于从DTB获得cmdline信息，以及物理内存信息．


early_init_dt_scan_root
=========================

::

    int __init early_init_dt_scan_root(unsigned long node, const char *uname, int depth, void *data)
    {
        const __be32 *prop;

        //根节点的depth为0，如果非0值直接返回
        if(depth != 0)
            return 0;

        dt_root_size_cells = OF_ROOT_NODE_SIZE_CELLS_DEFAULT;
        dt_root_addr_cells = OF_ROOT_NODE_ADDR_CELLS_DEFAULT;

        prop = of_get_flat_dt_prop(node, "#size-cells", NULL);
        if(prop)
            dt_root_size_cells = be32_to_cpup(prop);

        prop = of_get_flat_dt_prop(node, "#address-cells", NULL);
        if(prop)
            dt_root_addr_cells = be32_to_cpup(prop);

        return 1;
    }

``early_init_dt_scan_root`` 用于获得根节点#size_cells用于#address-cells对应的属性值



early_init_dt_verify
========================

::

    //params: dtb所在的虚拟地址
    bool __init early_init_dt_verify(void *params)
    {
        if(!params)
            return false;

        //检查dtb header的有效性
        if(fdt_check_header(params))
            return false;

        //将params参数赋值给initial_boot_params,生成dtb的crc
        of_fdt_crc32 = crc32_be(~0, initial_boot_params, fdt_totalsize(initial_boot_params));

        return true;
    }

``early_init_dt_verify`` 用于检查dtb的有效性




early_init_fdt_reserve_self
==============================

::

    void __init early_init_fdt_reserve_self(void)
    {
        if(!initial_boot_params)
            return;

        early_init_dt_reserve_memory_arch(__pa(initial_boot_params), fdt_totalsize(initial_boot_params), 0);
    }


``early_init_fdt_reserve_self`` 将dtb将入到MEMBLOCK的预留区内．initial_boot_params指向dtb所在的虚拟地址



early_init_fdt_scan_reserved_mem
===================================

::

    void __init early_init_fdt_scan_reserved_mem(void)
    {
        int n;
        u64 base, size;

        //判断initial_boot_params有效性
        if(!initial_boot_params)
            return;

        //遍历memory reserved mapping区域内的所有预留区
        fo(n = 0; ; n++)
        {
            //获取区域内的起始地址和长度
            fdt_get_mem_rsv(initial_boot_params, n, &base, &size);
            if(!size)
                break;

            //加入到MEMBLOCK分配器的预留区内
            early_init_dt_reserve_memory_arch(base, size, 0);
        }

        //将dts的reserved-memory节点中子节点对应的预留区加入到系统的reserved_mem数组
        of_scan_flat_dt(__fdt_scan_reserved_mem, NULL);
        fdt_init_reserved_mem();
    }

``early_init_fdt_scan_reserved_mem`` 用于将dtb中memory reserved mapping区域内的预留区加入到MEMBLOCK内存分配器的预留区．
并将dts reserved-memory节点的子节点加入到系统预留区，并初始化节点



early_mm_init
================

::

    //mdesc: machine_desc结构
    void __init early_mm_init(const struct machine_desc *mdesc)
    {
        //根据体系设置PTE和PMD在mem_types[]数组中的标志
        build_mem_type_table();
        //初始化早期的页表
        early_paging_init(mdesc);
    }

``early_mm_init`` 用于初始化简单的页表项PTE和PMD．


early_pte_alloc
=================

::

    //pmd: PMD入口
    //addr: 虚拟地址
    //prot: 页表标志
    static pte_t * __init early_pte_alloc(pmd_t *pmd, unsigned long addr, unsigned long prot)
    {
        return arm_pte_alloc(pmd, addr, prot, early_alloc);
    }


``early_pte_alloc`` 用于内核启动早期，分配并初始化一个PTE页表



early_trap_init
=====================

::

    //vectors_base: 新异常向量表所在的虚拟地址
    void __init early_trap_init(void *vectors_base)
    {
    #ifndef CONFIG_CPU_V7M
        unsigned long vectors = (unsigned long)vectors_base;
        extern char __stubs_start[], __stubs_end[];
        extern char __vectors_start, __vectors_end[];
        unsigned i;

        vectors_page = vectors_base;

        for(i = 0; i < PAGE_SIZE / sizeof(u32); i++)
            ((u32 *)vectors_base)[i] = 0xe7fddef1;

        memcpy((void *)vectors, __vectors_start, __vectors_end - __vectors_start);
        memcpy((void *)vectors + 0x1000, __stubs_start, __stubs_end - __stubs_start);

        kuser_init(vectors_base);

        flush_icache_range(vectors, vectors + PAGE_SIZE * 2);

    #else

    #endif
    }

``early_trap_init`` 用于早期异常向量表的建立．



elf_hwcap_fixup
==================

::

    static void __init elf_hwcap_fixup(void)
    {
        unsigned id = read_cpuid_id();

        if(read_cpuid_part() == ARM_CPU_PART_ARM1136 && ((id >> 20) & 3) == 0) {
            elf_hwcap &= ~HWCAP_TLS;
            return;
        }

        if((id & 0x000f0000) != 0x000f0000)
            return;

        if(cpuid_feature_extract(CPUID_EXT_ISAR3, 12) > 1 || 
            (cpuid_feature_extract(CPUID_EXT_ISAR3, 12) == 1 &&
            cpuid_feature_extract(CPUID_EXT_ISAR4, 20) >= 3))
                elf_hwcap &= ~HWCAP_SWP;
    }

``elf_hwcap_fixup`` 用于修改正ARM硬件支持的信息．



end_of_stack
==============

::

    static inline unsigned long *end_of_stack(struct task_struct *p)
    {
    #ifdef CONFIG_STACK_GROWSUP
        return (unsigned long *)((unsigned long)task_thread_info(p) + THREAD_SIZE) - 1;
    #else
        return (unsigned long *)(task_thread_info(p) + 1);
    #endif
    }

``end_of_stack`` 用于获得进程堆栈栈顶的地址






