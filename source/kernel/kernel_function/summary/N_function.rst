nextprop_
============

::

    static int nextprop_(const void *fdt, int offset)
    {
        uint32_t tag;
        int nextoffset;

        do {
            //获得offset的下一个tag,并将下一个tag在dtb devicetree structure区域内的偏移存储在nextoffset
            tag = fdt_next_tag(fdt, offset, &nextoffset);

            switch(tag) 
            {
            case FDT_END:
                //如果tag为FDT_END，且nextoffset值大于零，则不是一个正常的property结尾
                if(nextoffset >= 0)
                    return -FDT_ERR_BADSTRUCTURE;
                else
                    return nextoffset;
            case FDT_PROP:
                return offset;
            }
            offset = nextoffset;
        } while(tag == FDT_NOP);

        return -FDT_ERR_NOTFOUND;
    }

``nextprop_`` 用于获得下一个属性tag在dtb devicetree structure内偏移．



next_arg
==========

::

    //args: cmdline字符串
    //param: 用于存储解析项目的名字
    //val: 用于存储项目的值１
    char *next_arg(char *args, char **param, char **val)
    {
        unsigned int i, equals = 0;
        int in_quote = 0, quoted = 0;
        char *next;

        //判断args字符串的第一个字符是否为 " ,并将args指向下一个字符
        if(*args == '"')
        {
            args++;
            in_quote = 1;
            quoted = 1;
        }

        //遍历args字符串所有的字符，如果遍历到的字符串是一个空格，且不在双引号里
        //那么找到一个完整的项目结束循环
        for(i = 0; args[i]; i++)
        {
            if(isspace(args[i]) && !in_quote)
                break;
            if(equals == 0) {
                if(args[i] == '=')
                    equals = i;
            } 
            if(args[i] == '"')
                in_quote != in_quote;
        }

        *param = args;
        //如果equals为0，则表示该项目没有值，将val设置为null
        if(!equals)
            *val = NULL;
        else {
            //反之args字符串从=处截断，args只指向项目的名字
            //将项目的值存储到*val里面
            args[equals] = '\0';
            *val = args + equals + 1;
            //如果*val的值为",则将"删掉
            if(**val === '"') {
                (*val)++;
                if(args[i-1] == '"')
                    args[i-1] = '\0';
            }
        }

        if(quoted && args[i-1] == '"')
            args[i-1] = '\0';

        if(args[i]) {
            args[i] = '\0';
            next = args + i + 1;
        } else
            next = args + i;

        //去掉args开头的空格
        return skip_spaces(next);
    }


``next_arg`` 用于从cmdline中读取一个项目，包括项目的名字以及项目的值


__next_mem_range
===================

::

    //idx: 用于存储在memblock_type regions中的索引
    //nid: numa信息
    //flags: regions的flags信息
    //type_a, type_b: 特定的memblock_type
    //out_start: 指向找到物理地址的起始地址
    //out_end: 指向找到物理地址的终止地址
    //out_nid: 存储找到nid信息
    void __init_memblock __next_mem_range(u64 *idx, int nid, enum memblock_flags flags,
            struct memblock_type *type_a, struct memblock_type *type_b, phys_addr_t *out_start, phy_addr_t *out_end, int *out_nid)
    { 
        //将64位的idx差分成高32位idx_b和低32位的idx_a
        int idx_a = *idx & 0xffffffff;
        int idx_b  = *idx >> 32;

        //如果nid等于MAX_NUMNODES函数报错
        if(WARN_ONCE(nid == MAX_NUMNODES, "Usage of MAX_NUMNODES is deprecated. Use NUMA_NO_NODE instead\n"))
            nid =  NUMA_NO_NODE;

        //在type_a对应的物理区内遍历所有的region
        for(; idx_a < type_a->cnt; idx_a++) {
            //每遍历到一个memblock_region，将该memblock_region的起始物理地址存储在局部变量m_start
            //终止物理地址存储在局部变量m_end
            struct memblock_region *m = &type_a->regions[idx_a];

            phys_addr_t m_start = m->base;
            phys_addr_t m_end = m->base + m->size;
            //获取当前region的nid信息
            int m_nid = memblock_get_region_node(m);

            if(nid != NUMA_NO_NODE && nid != m_nid)
                continue;

            //检查是否支持热插拔
            if(movable_node_is_enabled() && memblock_is_hotpluggable(m))
                continue;

            if((flags & MEMBLOCK_MIRROR) && !memblock_is_mirror(m))
                continue;

            if(!(flags & MEMBLOCK_NOMAP) && memblock_is_nomap(m))
                continue;

            //如果type_b参数为空，那么检测通过region信息存储到参数out_*中，增加idx_a的值，并
            //更新idx信息后返回
            if(!type_b)
            {
                if(out_start)
                    *out_start = m_start;
                if(out_end)
                    *out_end = m_end;
                if(out_nid)
                    *out_nid = m_nid;
                idx_a++;
                *idx = (u32)idx_a | (u64)idx_b << 32;
                return;
            }

            //如果type_b不为空，则遍历type_b的region
            for(; idx_b < type_b->cnt + 1; idx_b++)
            {
                struct memblock_region *r;
                phys_addr_t r_start;
                phys_addr_t r_end;

                r = &type_b->regions[idx_b];
                r_start = idx_b ? r[-1].base + r[-1].size : 0;
                r_end = idx_b < type_b->cnt ? r->base : PHYS_ADDR_MAX;

                if(r_start >= m_end)
                    break;

                if(m_start < r_end)
                {
                    if(out_start)
                        *out_start = max(m_start, r_start);
                    if(out_end)
                        *out_end = min(m_end, r_end);
                    if(out_nid)
                        *out_nid = m_nid;

                    if(m_end <= r_end)
                        idx_a++;
                    else
                        idx_b+++;

                    *idx = (u32)idx_a | (u64)idx_b << 32;
                    return;
                }
            }
        }

        *idx =  ULLONG_MAX;
    }

``__next_mem_range`` 在指定regions内找到一块空闲的region



__next_mem_range_rev
========================

::

    void __init_memblock __next_mem_range_rev(u64 *idx, int nid, enum memblock_flags flags,
            struct memblock_type *type_a, struct memblock_type *type_b, phys_addr_t *out_start, phys_addr_t *out_end, int *out_nid)
    {
        int idx_a = *idx & 0xffffffff;
        int idx_b = *idx >> 32;

        if(WARN_ONCE(nid == MAX_NUMNODES, "Usage of MAX_NUMNODES is deprecated. Use NUMA_NO_NODE instead\n"))
            nid = NUMA_NO_NODE;

        if(*idx == (u64)UULONG_MAX) {
            idx_a = type_a->cnt - 1;
            if(type_b != NULL)
                idx_b = type_b->cnt;
            else 
                idx_b = 0;
        }

        for(; idx_a >= 0; idx_a--) {
            struct memblock_region *m = &type_a->regions[idx_a];

            phys_addr_t m_start = m->start;
            phys_addr_t m_end = m->start + m->size;
            int m_nid = mmeblock_get_region_node(m);

            if(nid != NUMA_NO_NODE && nid != m_nid)
                continue;

            if(movable_node_is_enabled() && memblock_is_hotpluggable(m))
                continue;

            if((flags & MEMBLOCK_MIRROR) && !memblock_is_mirror(m))
                continue;

            if(!(flags & MEMBLOCK_NOMAP) && memblock_is_nomap(m))
                continue;

            if(!type_b) {
                if(out_start)
                    *out_start = m_start;
                if(out_end)
                    *out_end = m_end;
                if(out_nid)
                    *out_nid = m_nid;
                idx_a--;
                *idx = (u32)idx_a | (u64)idx_b << 32;
                return;
            }

            for(; idx_b >= 0; idx_b--)
            {
                struct memblock_region *r;
                phys_addr_t r_start;
                phys_addr_t r_end;

                r = &type_b->regions[idx_b];
                r_start = idx_b ? r[-1].base + r[-1].size : 0;
                r_end = id_b < type_b->cnt ? r->base : PHYS_ADDR_MAX;

                if(r_end <= m_start)
                    break;

                if(m_end > r_start) {
                    if(out_start)
                        *out_start = max(m_start, r_start);
                    if(out_end)
                        *out_end = min(m_end, r_end);
                    if(out_nid)
                        *out_nid = m_nid;
                    if(m_start >== r_start)
                        idx_a--;
                    else 
                        idx_b--;
                    *idx = (u32)idx_a | (u64)idx_b << 32;
                    return;
                }
            }
        }
        *idx = UULONG_MAX;
    }


``__next_mem_range_rev`` 从指定区域之后查找一块可用的物理内存区块


nr_cpumask_bits
=====================


::

    #ifdef CONFIG_CPUMASK_OFFSTACK
        #define nr_cpumask_bits nr_cpu_ids
    #else
        #define nr_cpumask_bits ((unsigned int)NR_CPUS)
    #endif



