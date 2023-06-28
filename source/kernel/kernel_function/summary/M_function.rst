__map_init_section
=====================

::

    static void __init __map_init_section(pmd_t *pmd, unsigned long addr,
                unsigned long end, phys_addr_t phys, const struct mem_type *type, bool ng)
    { 
        pmd_t *p = pmd;
    #ifndef CONFIG_ARM_LPAE
        if(addr & SECTION_SIZE)
            pmd++;
    #endif
        do {
            *pmd = __pmd(phys | type->prot_sect | (ng ? PMD_SECT_nG : 0));
            phys += SECTION_SIZE;
        } while(pmd++, addr += SECTION_SIZE, addr != end);

        flush_pmd_entry(p);
    }


``__map_init_section`` 用于建立一个section一级页表


map_lowmem
=============

::

    static void __init map_lowmem(void)
    {
        struct memblock_region *reg;
        //计算内核镜像的起始物理地址和终止物理地址
        phys_addr_t kernel_x_start = round_down(__pa(KERNEL_START), SECTION_SIZE);
        phys_addr_t kernel_x_end = round_up(__pa(__init_end), SECTION_SIZE);

        //遍历系统中所有的可用物理内存
        for_each_memblock(memory, reg) {
            phys_addr_t start = reg->base;
            phys_addr_t end = start + reg->size;
            struct map_desc map;

            //判断这段物理内存块是否建立页表
            if(memblock_is_nomap(reg))
                continue;

            //如果物理内存的终止地址大于低端物理内存，则end设置为arm_lowmem_limit
            if(end > arm_lowmem_limit)
                end = arm_lowmem_limit;
            if(start >= end)
                break;

            if(end < kernel_x_start) {
                map.pfn = __phys_to_pfn(start);
                map.virtual = __phys_to_pfn(start);
                map.length = end - start;
                map.type = MT_MEMORY_RWX;
                create_mapping(&map);
            } else if(start >= kernel_x_end) {
                map.pfn = __phys_to_pfn(start);
                map.virtual = __phys_to_pfn(start);
                map.length = end - start;
                map.type =  MT_MEMORY_RW;
                create_mapping(&map);
            } else {
                if(start < kernel_x_start) {
                    map.pfn = __phys_to_pfn(start);
                    map.virtual = __phys_to_virt(start);
                    map.length = kernel_x_start - start;
                    map.type = MT_MEMORY_RW;

                    create_mapping(&map);
                }

                map.pfn = __phys_to_pfn(kernel_x_start);
                map.virtual = __phys_to_virt(kernel_x_start);
                map.length = end - kernel_x_end;
                map.type = MT_MEMORY_RW;

                create_mapping(&map);
            }

        }
    }

``map_lowmem`` 用于映射低端物理内存，低端物理内存的起始地址为DRM，低端物理内存的结束地址是arm_lowmem_limit.


memblock_add
===============

::

    int __init_memblock memblock_add(phys_addr_t base, phys_addr_t size)
    {
        phys_addr_t end = base + size - 1;

        return memblock_add_range(&memblock.memory, base, size, MAX_NUMNODES, 0);
    }

``memblock_add`` 用于将一块可用物理内存加入到memblock.memory内存区


memblock_add_range
=====================

::

    //type: 指向内存区
    //base: 需要加入的内存块的基地址
    //size: 需要加入内存块的长度
    //nid: NUMA节点
    //flags: 新加入内存块对应的flags
    int __init_memblock memblock_add_range(struct memblock_type *type, phys_addr_t base,
                    phys_addr_t size, int nid, enum memblock_flags flags)
    {
        bool insert = false;
        phys_addr_t obase = base;
        phys_addr_t end = base + memblock_cap_size(base, &size);
        int idx, nr_new;
        struct memblock_region *rgn;

        //如果size为0，则返回
        if(!size)
            return 0;

        //检查参数type->regions[0].size以此判断内存区是不是不包含其他内存区块
        //由于内存区内的所有内存区块都是按其首地址从低到高排列,如果第一个内存区块的长度为0
        //那么认为这个内存区可能为空，但不能确认
        if(type->regions[0].size == 0) {
            //继续检查内存区的cnt变量，这个变量统计内存区内存块的数量
            //如果内存区的cnt为1表示内存区内不包含内存块的数量
            //如果内存区的total_size不为零，那么内存区含有内存区块,内核报错
            WARN_ON(type->cnt != 1 || type->total_size);
            type->regions[0].base = base;
            type->regions[0].size = size;
            type->regions[0].flags = flags;
            memblock_set_region_node(&type->regions[0], nid);
            type->total_size = size;
            return 0;
        }

    repeat:
        base = obase;
        nr_new = 0;

        //遍历内存区内的所有内存区块
        for_earch_memblock_type(idx, type, rgn) {
            phys_addr_t rbase = rgn->base;
            phys_addr_t rend = rbase + rgn->size;

            if(rbase >= end)
                break;
            if(rend <= base)
                continue;

            if(rbase > base) {
                nr_new++;
                if(insert)
                    memblock_insert_region(type, idx++, base, rbase - base, nid, flags);
            }

            base = min(rend, end);
        }

        if(base < end) {
            nr_new++;
            if(insert)
                memblock_insert_region(type, idex, base, end - base, nid, flags);
        }

        if(!nr_new)
            return 0;

        if(!insert) {
            while(type->cnt + nr_new > type_max)
                if(memblock_double_array(type, obase, size) < 0)
                    return -ENOMEM;
            insert = true;
            goto repeat;
        } else {
            memblock_merge_regions(type);
            return 0;
        }
    }

``memblock_add_range`` 用于将一块物理内存插入到内存区里面，内存区可以是物理内存区，也可以是预留区

**遍历到的内存区块的起始地址大于或等于新内存区块的结束地址，新的内存区块位于遍历到内存区块的前端**

::

    1） rbase > end

     base                    end        rbase               rend
     +-----------------------+          +-------------------+
     |                       |          |                   |
     | New region            |          | Exist regions     |
     |                       |          |                   |
     +-----------------------+          +-------------------+

    2）rbase == endi

                             rbase                      rend
                            | <----------------------> |
     +----------------------+--------------------------+
     |                      |                          |
     | New region           | Exist regions            |
     |                      |                          |
     +----------------------+--------------------------+
     | <------------------> |
     base                   end

**遍历到的内存区块的终止地址小于或等于新内存区块的起始地址，新的内存区块位于遍历到内存区块的后面**

::

    1） base > rend
     rbase                rend         base                  end
     +--------------------+            +---------------------+
     |                    |            |                     |
     |   Exist regions    |            |      new region     |
     |                    |            |                     |
     +--------------------+            +---------------------+

    2) base == rend
                          base
     rbase                rend                     end
     +--------------------+------------------------+
     |                    |                        |
     |   Exist regions    |       new region       |
     |                    |                        |
     +--------------------+------------------------+


**其他情况,两个内存区块存在重叠部分**

::

                     rbase     Exist regions        rend
                     | <--------------------------> |
     +---------------+--------+---------------------+
     |               |        |                     |
     |               |        |                     |
     |               |        |                     |
     +---------------+--------+---------------------+
     | <--------------------> |
     base   New region        end


       * rbase                     rend
    | <---------------------> |
    +----------------+--------+----------------------+
    |                |        |                      |
    | Exist regions  |        |                      |
    |                |        |                      |
    +----------------+--------+----------------------+
                     | <---------------------------> |
                     base      new region            end



memblock_addrs_overlap
==========================

::

    static unsigned long __init_memblock memblock_addrs_overlap(phys_addr_t base1, phys_addr_t size1,
                                    phys_addr_t base2, phys_addr_t size2)
    { 
        return ((base1 < (base2 + size2)) && (base2 < (base1 + size1)));
    }

``memblock_addrs_overlap`` 用于确认两块内存区块是否存在重叠


memblock_alloc_base
======================

::

    phys_addr_t __init memblock_alloc_base(phys_addr_t size, phys_addr_t align, phys_addr_t max_addr)
    {
        phys_addr_t alloc;

        alloc = __memblock_alloc_base(size, align, max_addr);

        if(alloc == 0)
            panic("ERROR: Failed to allocate %pa bytes below %pa.\n", &size, &max_addr);

        return alloc;
    }

    phys_addr_t __init __memblock_alloc_base(phys_addr_t size, phys_addr_t align, phys_addr_t max_addr)
    {
        return memblock_alloc_base_nid(size, align, max_addr, NUMA_NO_NODE, MEMBLOCK_NONE);
    }


``memblock_alloc_base`` 用于获得指定长度的物理内存



memblock_alloc_base_nid
==========================

::

    phys_addr_t __init memblock_alloc_base_nid(phys_addr_t size, phys_addr_t align, phys_addr_t max_addr,
                                                int nid, enum memblock_flags flags)
    { 
        return memblock_alloc_range_nid(size, align, 0, max_addr, nid, flags);
    }


``memblock_alloc_base_nid`` 用于从指定NUMA节点上分配物理内存


memblock_alloc_internal
==========================

::

    static void * __init memblock_alloc_internal(phys_addr_t size, phys_addr_t  align,
            phys_addr_t min_addr, phys_addr_t max_addr, int nid)
    {
        phys_addr_t alloc;
        void *ptr;
        enum memblock_flags flags = choose_memblock_flags();

        if(WARN_ONCE(nid == MAX_NUMNODES, "Usage of MAX_NUMNODES is deprecated. Use NUMA_NO_NODE instead\n"))
            nid = NUMA_NO_NODE;

        //判断slab内存分配器是否启用
        //如果启用直接调用kzalloc_node分配内存,并返回
        if(WARN_ON_ONCE(slab_is_available()))
            return kzalloc_node(size, GFP_NOWAIT, nid);

        //如果align参数为0，那么打印堆栈信息，并将align设置为SMP_CACHE_BYTES
        if(!align) {
            dump_stack();
            align = SMP_CACHE_BYTES;
        }

        //如果max_addr大于MEMBLOCK内存分配器最大设置current_limit,则将其设置为MEMBLOCK最大限制
        if(max_addr > memblock.current_limit)
            max_addr = memblock.current_limit;

    again:
        //从MEMBLOCK分配器中获得指定物理内存
        alloc = memblock_find_in_range_node(size, align, min_addr, max_addr, nid, flags);

        //分配成功后，将其加入到预留区
        if(alloc && !memblock_reserve(alloc, size))
            goto done;

        //如果nid不是NUMA_NO_NODE，那么重新从NUMA_NO_NODE中分配内存，并将该区域加入到系统预留区
        if(nid != NUMA_NO_NODE) { 
            alloc memblock_find_in_range_node(size, align, min_addr, max_addr, NUMA_NO_NODE, flags);

            if(alloc && !memblock_reserve(alloc, size))
                goto done;
        }

        if(min_addr) {
            min_addr = 0;
            goto again;
        }

        if(flags & MEMBLOCK_MIRROR) {
            flags &= ~MMEBLOCK_MIRROR;
            goto again;
        }

        return NULL;

    done:
        //如果内存分配成功，那么函数调用phys_to_virt获得物理地址对应的虚拟地址
        ptr = phys_to_virt(alloc);
        if(max_addr != MEMBLOCK_ALLOC_KASAN)
            kmemleak_alloc(ptr, size, 0, 0);

        return ptr;
    }

    static inline void *phys_to_virt(phys_addr_t x)
    {
        return (void *)__phys_to_virt(x);
    }

``membock_alloc_internal`` 用于从MEMBLOCK内存分配器中获得指定大小的物理内存


memblock_alloc_node_nopanic
=============================

::
    
    void * __init memblock_alloc_try_nid_nopanic(phys_addr_t size, phys_addr_t align,
                    phys_addr_t min_addr, phys_addr_t max_addr, int nid)
    { 
        void *ptr;
        
        ptr = memblock_alloc_internal(size, align, min_addr, max_addr, nid);

        if(ptr)
            memset(ptr, 0, size);

        return ptr;
    }

    static inline void * __init memblock_alloc_node_nopanic(phys_addr_t size, int nid)
    {
        return memblock_alloc_try_nid_nopanic(size, SMP_CACHE_BYTES, MEMBLOCK_LOW_LIMIT, MEMBLOCK_ALLOC_ACCESSIBLE, nid);
    }

``memblock_alloc_node_nopanic`` 用于从指定的NUMA中分配物理内存



memblock_alloc_range
======================

::

    phys_addr_t __init memblock_alloc_range(phys_addr_t size, phys_addr_t align,
            phys_addr_t start, phys_addr_t end, enum memblock_flags  flags)
    {
        return memblock_alloc_range_nid(size, align, start, end, NUMA_NO_NODE, flags);
    }


``memblock_alloc_range`` 用于从MEMBLOCK可用物理内存指定范围内分配物理内存．



memblock_alloc_range_nid
==========================

::

    static phys_addr_t __init memblock_alloc_range_nid(phys_addr_t size, phys_addr_t align,
                phys_addr_t start, phys_addr_t end, int nid, enum memblock_flags flags)
    {
        phy_addr_t found;

        if(!align) {
            dump_stack();
            align = SMP_CACHE_BYTES;
        }

        found = memblock_find_in_range_node(size, align, start, end, nid, flags);

        if(found && !memblock_reserve(found, size)) {
            kmemleak_alloc_phy(found, size, 0, 0);
            return found;
        }

        return 0;
    }

``memblock_alloc_range_nid`` 用于从指定NUMA上分配物理内存


memblock_allow_resize
=======================

::

    void __init memblock_allow_reize(void)
    {
        memblock_can_resize = 1;
    }

``memblock_allow_resize`` 用于设置MEMBLOCK内存分配器的memblock_can_resize变量


memblock_bottom_up
====================

::

    static inline bool memblock_bottom_up(void)
    {
        return memblock.bottom_up;
    }

``memblock_bottom_up`` 用于获得当前MEMBLOCK分配的方向，如果为true那么MEMBLOCK从低地址向高地址分配，反之则高地址向低地址分配


memblock_cap_size
====================

::

    static inline phys_addr_t memblock_cap_size(phys_addr_t base,  phys_addr_t *size)
    {
        return *size =  min(*size, PHYS_ADDR_MAX - base);
    }

``memblock_cap_size`` 用于获得一个有效的长度值，函数确保size不会超出系统支持的物理内存



memblock_double_array
=======================

::

    //type: 需要扩编的memblock_type
    //new_area_start: 新物理内存区的起始物理地址
    //new_area_size: 新物理内存区的长度
    static int __init_memblock memblock_double_array(struct memblock_type *type,
            phys_addr_t new_area_start, phys_addr_t new_area_size)
    {
        struct memblock_region *new_array, *old_array;
        phys_addr_t old_alloc_size, new_alloc_size;
        phys_addr_t old_size, new_size, addr, new_end;
        //获取当前slab内存分配器是否可用
        int use_slab = slab_is_available();
        int *in_slab;

        if(!memblock_can_resize)
            return -1;
        //计算原先memblock_type支持的最大物理内存数
        old_size = type->max * sizeof(struct memblock_region);
        new_size = old_size << 1;

        //进行页对齐
        old_alloc_size = PAGE_ALIGN(old_size);
        new_alloc_size = PAGE_ALIGN(new_size);
        //如果type对应的类型是可用物理内存区，那么读取memblock_memory_in_slab的值到in_slab中
        if(type == &memblock.memory)
            in_slab = &memblock_memory_in_slab;
        else
            in_slab = &memblock_reserved_in_slab;

        //如果此时slab内存分配器已经可以使用，使用kmalloc分配内存
        if(use_slab) {
            new_array = kmalloc(new_size, GFP_KERNEL);
            addr = new_array ? __pa(new_array) : 0;
        } else {
            if(type != &memblock.reserved)
                new_area_start = new_area_size = 0;
            //查找一块空闲的物理内存
            addr = memblock_find_in_range(new_area_start + new_area_size, 
                        memblock.current_limit, new_alloc_size, PAGE_SIZE);

            //如果没有找到，那么函数从0地址重新查找物理内存
            if(!addr && new_area_size)
                addr = mmeblock_find_in_range(0, min(new_area_start, memblock.current_limit),
                                new_alloc_size, PAGE_SIZE);

            new_array = addr ? __va(addr) : NULL;
        }

        if(!addr) {
            pr_err("memblock: Failed to double %s array from %ld to %ld enties!\n", 
                    type->name, type->max, type->max * 2);
            return -1;
        }

        new_end = addr + new_size - 1;

        //将原始regions信息拷贝到新分配的物理内存上，然后清零new_array+type->max之后的物理内存
        memcpy(new_array, type->regions, old_size);
        memset(new_array + type->max, 0, old_size);
        old_array = type->regions;
        type->regions = new_array;
        type->max <<= 1;

        if(*in_slab)
            kfree(old_array);
        else if(old_array != memblock_memory_init_regions &&
                old_array != memblock_reserved_init_regions)
            memblock_free(__pa(old_array), old_alloc_size);

        if(!use_slab)
            BUG_ON(memblock_reserve(addr, new_alloc_size));

        *in_slab = use_slab;

        return 0;
    }

``memblock_double_array`` 将memblock_type支持的regions数扩大两倍


memblock_end_of_DRAM
=======================

::

    phys_addr_t __init_memblock memblock_end_of_DRAM(void)
    {
        int idx = memblock.memory.cnt - 1;

        return (memblock.memory.regions[idx].base + memblock.memory.regions[idx].size);
    }

``memblock_end_of_DRAM`` 用于获得MEMBLOCK内存分配器memory区域的最大物理地址．


memblock_find_in_range
========================

::

    phys_addr_t __init_memblock memblock_find_in_range(phys_addr_t start, phys_addr_t end,
                            phys_addr_t size, phys_addr_t align)
    {
        phys_addr_t ret;
        enum memblock_flags flags = choose_memblock_flags();

    again:
        ret = memblock_find_in_range_node(size, align, start, end, NUMA_NO_NODE, flags);

        if(!ret && (flags & MEMBLOCK_MIRROR)) {
            flags &= ~MEMBLOCK_MIRROR;
            goto again;
        }

        return ret;
    }

``memblock_find_in_range`` 在指定区间内查找一块可用的物理内存



memblock_find_in_range_node
=============================

::

    //size: 需要查找内存的大小
    //align: 对齐方式
    //start: 需要查找内存区域的起始地址
    //end: 需要查找内存区域的终止地址
    //nid: 代表NUMA节点信息
    //flags: 代表内存区的标志
    phys_addr_t __init_memblock memblock_find_in_range_node(phys_addr_t size, phys_addr_t align,
                        phys_addr_t start, phys_addr_t end, int nid, enum memblock_flags flags)
    {
        phys_addr_t kernel_end, ret;

        //对end参数进行检测
        if(end == MEMBLOCK_ALLOC_ACCESSIBLE || end == MEMBLOCK_ALLOC_KASAN)
            end = memblock.current_current_limit;

        //对start和end进行处理
        start = max_t(phys_addr_t, start, PAGE_SIZE);
        end = max(start, end);
        //获得kernel镜像的终止物理地址
        kernel_end = __pa_symbol(_end);

        //如果MEMBLOCK支持从低向上分配以及查找的终止地址大于内核的终止物理地址
        if(memblock_bottom_up() && end > kernel_end) {
            phys_addr_t bottom_up_start;

            bottom_up_start = max(start, kernel_end);

            ret = __memblock_find_range_bottom_up(bottom_up_start, end, size, align, nid, flags);

            if(ret)
                return ret;

            WARN_ONCE(IS_ENABLED(CONFIG_MEMORY_HOTREMOVE),
                    "memblock: bottom-up allocaton failed, memory hotremove may be affected\n");
        }

        return __memblock_find_range_top_down(start, end, size, align, nid, flags);
    }

``memblock_find_in_range_node`` 在指定的节点区间内查找一块可用的物理内存




__memblock_find_range_bottom_up
=================================

::

    static phys_addr_t __init_memblock __memblock_find_range_bottom_up(phys_addr_t start, phys_addr_t end,
        phys_addr_t size, phys_addr_t align, int nid, enum memblock_flags flags)
    {
        phys_addr_t this_start, this_end, cand;
        u64 i;

        //遍历所有可用的物理内存region
        for_each_free_mem_range(i, nid, flags, &this_start, &this_end, NULL) {
            //使用clamp找到符合要求的范围
            this_start = clamp(this_start, start, end);
            this_end = clamp(this_end, start, end);

            //对this_start进行对齐
            cand = round_up(this_start, align);
            if(cand < this_end && this_end - cand >= size)
                return cand;
        }

        return 0;
    }


``__memblock_find_range_bottom_up`` 用于从MEMBLOCK的底部开始，查找一块可用的物理内存region.



__memblock_find_range_top_down
===============================

::

    static phys_addr_t __init_memblock __memblock_find_range_top_down(phys_addr_t start, phys_addr_t end,
            phys_addr_t size, phys_addr_t align, int nid, enum memblock_flags flags)
    {
        phys_addr_t this_start, this_end, cand;
        u64 i;

        //倒序遍历所有的空闲物理区块
        for_each_free_mem_range_reverse(i, nid, flags, &this_start, &this_end, NULL) {
            //找到符合要求的起始物理地址和终止物理地址
            this_start = clamp(this_start, start, end);
            this_end = clamp(this_end, start, end);

            if(this_end < size)
                continue;

            cand = round_down(this_end - size, align);
            if(cand >= this_start)
                return cand;
        }
        
        return 0;
    }

``__memblock_find_rage_top_down`` 作用是从顶端往低端，查找满足需求的空闲物理块





memblock_free
=================

::

    int __init_memblock memblock_free(phys_addr_t base, phys_addr_t size)
    {
        phys_addr_t end = base + size - 1;

        kmemleak_free_part_phys(base, size);

        return memblock_remove_range(&memblock.reserved, base, size);
    }

``memblock_free`` 作用是释放物理内存区块


memblock_insert_region
==========================

::

    static void __init_memblock memblock_insert_region(struct memblock_type *type,
            int idx, phys_addr_t base, phys_addr_t size, int nid, enum memblock_flags flags)
    {
        struct memblock_region *rgn == &type->regions[idx];

        BUG_ON(type->cnt >= type->max);

        memmove(rgn + 1, rgn, (type->cnt - idx) * sizeof(*rgn));
        rgn->base = base;
        rgn->size = size;
        rgn->flags = flags;
        memblock_set_region_node(rgn, nid);
        type->cnt++;
        type->total_size += size;
    }


``memblock_insert_region`` 用于将一个新的memblock_region插入到MEMBLOCK指定类型里．


memblock_is_hotpluggable
=========================

::

    static inline bool memblock_is_hotpluggable(struct memblock_region *m)
    {
        return m->flags & MEMBLOCK_HOTPLUG;
    }


``memblock_is_hotpluggable`` 判断当前region是否具有热插拔属性．


memblock_is_mirror
=====================

::

    static inline bool memblock_is_mirror(struct memblock_region *m)
    {
        return m->flags & MEMBLOCK_MIRROR;
    }

``memblock_is_mirror`` 用于判断当前regions是否是MIRROR


memblock_is_nomap
=====================

::

    static inline bool memblock_is_nomap(struct memblock_region *m)
    {
        return m->flags & MEMBLOCK_NOMAP;
    }


``memblock_is_nomap`` 判断当前region是否不需要映射页表


memblock_is_region_memory
=============================

::

    bool __init_memblock memblock_is_region_memory(phys_addr_t base, phys_ddr_t size)
    {
        //查找base参数在memory regions的索引
        int idx = memblock_search(&memblock.memory, base);
        phys_addr_t end = base + memblock_cap_size(base, &size);

        if(idx == -1)
            return false;

        return (memblock.memory.regions[idx].base + memblock.memory.regions[idx].size) >= end;
    }

    static int __init_memblock memblock_search(struct memblock_type *type, phys_addr_t addr)
    {
        unsigned int left = 0, right = type->cnt;

        do {
            unsigned int mid = (right + left) / 2;

            if(addr < type->regions[mid].base)
                right = mid;
            else if(addr >= (type->regions[mid].base + type->regions[mid].size))
                lef = mid + 1;
            else 
                return mid;
        } while(left < right);

        return -1;
    }

``memblock_is_region_memory`` 用于确认内存区块是否在MEMBLOCK内存分配器memory regions里



memblock_is_region_reserved
===============================

::

    bool __init_memblock memblock_is_region_reserved(phys_addr_t base, phys_addr_t size)
    {
        //得到查找区域的安全长度
        memblock_cap_size(base, &size);
        return memblock_overlaps_region(&memblock.reserved, base, size);
    }

``memblock_is_region_reserved`` 检查参数对应的内存区块是否在MEMBLOCK内存分配器的预留区内


memblock_isolate_range
=========================

::

    //type: 指向特定的memblock_type
    //base: 孤立物理内存块的起始物理地址
    //size: 孤立物理内存块的长度
    static int __init_memblock memblock_isolate_range(struct memblock_type *type, phys_addr_t base,
                phys_addr_t size, int *start_rgn, int *end_rgn)
    {
        //计算孤立物理块的终止物理地址
        phys_addr_t end = base + memblock_cap_size(base, &size);
        int idx;
        struct memblock_region *rgn;

        *start_rgn = *end_rgn = 0;

        if(!size)
            return 0;

        while(type->cnt + 2 > type->max)
            if(memblock_double_array(type, base, size) < 0)
                return -ENOMEM;

        //遍历type对应的所有物理内存region
        for_each_memblock_type(idx, type, rgn) {
            phys_addr_t rbase = rgn->base;
            phys_addr_t rend = rbase + rgn->size;

            //找到符合要求的region
            if(rbase >= end)
                break;
            if(rend <= base)
                continue;

            //如果rbase小于base那么需要孤立的内存区块可能可遍历到的region存在重叠的情况
            //首先将重叠的部分从原先的region中移除，并将剩余的region插入到memblock_type的regions里
            if(rbase < base) {
                rgn->base = base;
                rgn->size -= base - rbase;
                type->total_size -= base - rbase;
                memblock_insert_region(type, idx, rbase, base - rbase, 
                        memblock_get_region_node(rgn), rgn->flags);
            } else if(rend > end) {
                rgn->base = end;
                rgn->size -= end - rbase;
                type->total_size = end - rbase;
                memblock_insert_region(type, idx--, rbase, end - rbase,
                    memblock_get_region_node(rgn), rgn->flags);
            } else {
                if(!*end_rgn)
                    *start_rgn = idx;
                *end_rgn = idx + 1;
            }
        }
        return 0;
    }

``memblock_isolate_range`` 用于将指定范围的物理内存从内存区块孤立出来



memblock_merge_regions
=========================

::

    static void __init_memblock memblock_merge_regions(struct memblock_type *type)
    {
        int i = 0;

        //遍历所有region
        while(i < type->cnt - 1) 
        {
            struct memblock_region *this = &type->regions[i];
            struct memblock_region *next = &type->regions[i + 1];

            if(this->base + this->size != next->base ||
                memblock_get_region_node(this) != memblock_get_region_node(next) ||
                this->flags != next->flags){
                BUG_ON(this->base + this->size > next->base);
                i++;
                continue;
            }

            //如果两个region正好相连，并且flags和numa都相同，则将两个region合并成一个region
            this->size += next->size;
            memmove(next, next + 1, (type->cnt - (i + 2)) * sizeof(*next));
            //type的cnt减一，进入下一次循环
            type->cnt--;
        }
    }


``memblock_merge_regions`` 用于合并特定memblock_type内的regions


memblock_overlaps_region
============================

::

    bool __init_memblock memblock_overlaps_region(struct memblock_type *type,
                            phys_addr_t base, phys_addr_t size)
    {
        unsigned long i;
        for(i = 0; i < type->cnt; i++)
            if(memblock_addrs_overlap(base, size, type->regions[i].base, type->regions[i].size))
                break;

        return i < type->cnt;
    }

``memblock_overlaps_region`` 用于判断内存区块在MEMBLOCK内存分配器指定type的regions内是否存在重叠部分


memblock_phys_alloc
======================

::

    phys_addr_t __init memblock_phys_alloc(phys_addr_t size, phys_addr_t align)
    {
        return memblock_alloc_base(size, align, MEMBLOCK_ALLOC_ACCESSIBLE);
    }

    phys_addr_t __init memblock_alloc_base(phys_addr_t size, phys_addr_t align, phys_addr_t max_addr)
    {
        phys_addr_t alloc;

        alloc = __memblock_alloc_base(size, align, max_addr);

        if(alloc == 0)
            panic("ERROR: Failed to allocate %pa bytes below %pa.\n");

        return alloc;
    }

    phys_addr_t __init __memblock_alloc_base(phys_addr_t size, phys_addr_t align, phys_addr_t max_addr)
    {
        return memblock_alloc_base_nid(size, align, max_addr, NUMA_NO_NODE, MEMBLOCK_NONE);
    }


``memblock_phys_alloc`` 用于获得指定长度的物理内存


memblock_resion_memory_base_pfn
======================================

::

    static inline unsigned long memblock_region_memory_base_pfn(const struct memblock_region *reg)
    {
        return PFN_UP(reg->base);
    }


``memblock_region_memory_base_pfn`` 用于获得memblock_region起始物理地址对应的页帧


memblock_region_memory_end_pfn
=================================

::

    static inline unsigned long memblock_region_memory_end_pfn(const struct memblock_region *reg)
    {
        return PFN_DOWN(reg->base + reg->size);
    }


``memblock_region_memory_end_pfn`` 用于获得memblock_region终止物理地址对应的页帧号 


memblock_remove_range
========================

::

    static int __init_memblock memblock_remove_range(struct memblock_type *type,
                    phys_addr_t base, phys_addr_t size)
    {
        int start_rgn, end_rgn;
        int i, ret;

        ret = memblock_isolate_range(type, base, size, &start_rgn, &end_rgn);
        if(ret)
            return ret;

        for(i = end_rgn - 1; i >= start_rgn; i--)
            memblock_remove_region(type, i);

        return 0;
    }


``memblock_remove_range`` 从指定的memblock_type中移除一定范围的内存区块


memblock_remove
====================

::

    int __init_memblock memblock_remove(phys_addr_t base, phys_addr_t size)
    {
        phys_addr_t end = base + size - 1;

        return memblock_remove_range(&memblock.memory, base, size);
    }




memblock_remove_region
=========================

::

    static void __init_memblock memblock_remove_region(struct memblock_type *type, unsigned long r)
    {
        type->total_size -= type->regions[r].size;
        memmove(&type->regions[r], &type->regions[r + 1],
            (type->cnt - (r + 1)) * sizeof(type->regions[r]));
        type->cnt--;

        if(type->cnt == 0)
        {
            WARN_ON(type->total_size != 0);
            type->cnt = 1;
            type->regions[0].base = 0;
            type->regions[0].size = 0;
            type->regions[0].flags = 0;
            memblock_set_region_node(&type->regions[0], MAX_NUMNODES);
        }
    }

``memblock_remove_region`` 用于从memblock_type region中移除指定的region


memblock_reserve
=====================

:: 

    int __init_memblock memblock_reserve(phys_addr_t base, phys_addr_t size)
    {
        phys_addr_t end = base + size - 1;

        return memblock_add_range(&memblock.reserved, base, size, MAX_NUMNODES, 0);
    }

``memblock_reserve`` 将内存区块加入到MEMBLOCK的保留区


memblock_search
=================

::

    static int __init_memblock memblock_search(struct memblock_type *type, phys_addr_t addr)
    {
        unsigned int left = 0, right = type->cnt;

        do {
            unsigned int mid = (right + left) / 2;

            if(addr < type->regions[mid].base)
                right = mid;
            else if(addr >= (type->regions[mid].base + type->regions[mid].size))
                left = mid + 1;
            else
                return mid;
        } while(left < right);

        return -1;
    }


memblock_start_of_DRAM
==========================

::

    phys_addr_t __init_memblock memblock_start_of_DRAM(void)
    {
        return memblock.memory.regions[0].base;
    }




movable_node_is_enabled
==========================

::

    static inline bool movable_node_is_enabled(void)
    {
        return movable_node_enabled;
    }








