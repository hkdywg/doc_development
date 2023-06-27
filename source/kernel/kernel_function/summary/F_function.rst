FD_ALIGN
===========

::

    #define FDT_ALIGN(x, a) (((x) + (a) - 1) & ~((a) - 1))


``FDT_ALIGN`` 用于将x参数按照a对齐


fdt_boot_cpuid_phys
======================

::

    #define fdt_boot_cpuid_phys(fdt) (fdt_get_header(fdt, boot_cpuid_phys))


``fdt_boot_cpuid_phys`` 用于读取DTB header的boot_cpuid_phys信息


fdt_check_header
====================

::

    int fdt_check_header(const void *fdt)
    {
        size_t hdrsize;

        //检查dtb的magic是否有效
        if(fdt_magic(fdt) != FDT_MAGIC)
            return -FDT_ERR_BADMAGIC;

        //获取dtb header大小
        hdrsize = fdt_header_size(fdt);
        //判断dtb版本
        if((fdt_version(fdt) < FDT_FIRST_SUPPORTED_VERSION) || 
            (fdt_last_comp_version(fdt) > FDT_LAST_SUPPORTED_VERSION))
                return -FDT_ERR_BADVERSION;

        if(fdt_version(fdt) < fdt_last_comp_version(fdt))
            return -FDT_ERR_BADVERSION;
        //如果dtb长度比dtb header小，或者dtb 长度比INT_MAX大，则认为dtb无效
        if((fdt_totalsize(fdt) < hdrsize) || (fdt_totalsize(fdt) > INT_MAX))
            return -FDT_ERR_TRUNCATED;

        //检查dtb reserved区域是否在大于dtb header而小于dtb 二进制大小的区域内
        if(!check_off_(hdrsize, fdt_totalsize(fdt), fdt_off_mem_rsvmap(fdt)))
            return -FDT_ERR_TRUNCTED;

        //如果dtb版本小于17,如果此时devicetree struct的位置不再hdrsize和totalsize之间，则认定dtb无效
        if(fdt_version(fdt) < 17) {
            if(!check_off_(hdrsize, fdt_totalsize(fdt), fdt_off_dt_struct(fdt)))
                return -FDT_ERR_TRUNCTED;
        } else {
            if(!check_block_(hdrsize, fdt_totalsize(fdt), fdt_off_dt_struct(fdt), fdt_size_dt_struct(fdt)))
                return -FDT_ERR_TRUNCTED;
        }

        if(!check_block_(hdrsize, fdt_totalsize(fdt), fdt_off_dt_strings(fdt), fdt_size_dt_strings(fdt)))
            return -FDT_ERR_TRUNCTED;

        return 0;
    }


``fdt_check_header`` 用于检查DTB二进制文件是否有效



fdt_check_node_offset_
===========================

::

    int fdt_check_node_offset_(const void *fdt, int offset)
    {
        if((offset <  0) || (offset % FDT_TAGSIZE) || (fdt_next_tag(fdt, offset, &offset) != FDT_BEGIN_NODE))
            return -FDT_ERR_BADOFFSET;

        return offset;
    }


``fdt_check_node_offset_`` 用于判断offset对应的值是否为fdt device node




fdt_check_prop_offset_
==========================

::

    //fdt: 指向dtb
    //offset: property在dtb devicetree structure内偏移
    int fdt_check_prop_offset_(const void *fdt, int offset)
    {
        if((offset < 0) || (offset % FDT_TAGSIZE) || (fdt_next_tag(fdt, offset, &offset) != FDT_PROP))
            return -FDT_ERR_BADOFFSET;

        return offset;
    }

``fdt_check_prop_offset_`` 用于判断offset对应的tag是否为fdt property.




fdt_first_property_offset
============================

::

    int fdt_first_property_offset(const void *fdt, int nodeoffset)
    {
        int offset;

        if((offset = fdt_check_node_offset_(fdt, nodeoffset)) < 0)
            return offset;

        return nextprop_(fdt, offset);
    }

``fdt_first_property_offset`` 用于获得device node的第一个属性在dtb devicetree structure区域内的偏移




fdt_get_property_by_offset_
===============================

::

    static const struct fdt_property *fdt_get_property_by_offset_(const void *fdt, int offset, int *lenp)
    {
        int err;
        const struct fdt_property *prop;

        if((err = fdt_check_prop_offset_(fdt, offset)) < 0) {
            if(lenp)
                *lenp = err;
            return NULL;
        }

        prop = fdt_offset_ptr_(fdt, offset);

        if(lenp)
            *lenp = fdt32_ld(&prop->len);

        return prop;
    }

``fdt_get_property_by_offset_`` 通过属性在dtb devicetree structure区域内的偏移获取属性值的长度．



fdt_header_size_
====================

::

    #define FDT_V1_SIZE         (7*sizeof(fdt32_t))
    #define FDT_V2_SIZE         (FDT_V1_SIZE + sizeof(fdt32_t))
    #define FDT_V3_SIZE         (FDT_V2_SIZE + sizoef(fdt32_t))
    #define FDT_V16_SIZE        FDT_V3_SIZE
    #define FDT_V17_SIZE        (FDT_V16_SIZE + sizeof(fdt32_t))

    size_t fdt_header_size_(uint32_t version)
    {
        if(version <= 1)
            return FDT_V1_SIZE;
        else if(version <= 2)
            return FDT_V2_SIZE;
        else if(version <= 3)
            return FDT_V3_SIZE;
        else if(version <= 16)
            return FDT_V16_SIZE;
        else
            return FDT_V17_SIZE;
    }

``fdt_header_size_`` 用于获得dtb header结构的长度


fdt_header_size
==================

::

    static inline size_t fdt_header_size(const void *fdt)
    {
        return fdt_header_size_(fdt_version(fdt));
    }



fdt_init_reserved_mem
=============================

::

    void __init fdt_init_reserved_mem(void)
    {
        int i;

        //检查reserved_mem数组对应的预留区是否存在重叠部分
        __rmem_check_for_overlap();

        for(i = 0; i < reserved_mem_count; i++) {
            struct reserved_mem *rmem = &reserved_mem[i];
            unsigned long node = rmem->fdt_node;
            int len;
            const __be32 *prop;
            int err = 0;

            //获得节点的phandle或linux,phandle属性
            prop = of_get_flat_dt_prop(node, "phandle", &len);
            if(!prop)
                prop = of_get_flat_dt_prop(node, "linux,phandle", &len);
            if(prop)
                rmem->phanlde = of_read_number(prop, len/4);

            //为预留区分配内存
            if(rmem->size == 0)
                err = __reserved_mem_alloc_size(node, rmem->name, &rmem->base, &rmem->size);

            //初始化预留区
            if(err == 0)
                __reserved_mem_init_node(rmem);
        }
    }


``fdt_init_reserved_mem`` 用于为reserved_mem[]数组内的保留区分配内存并初始化预留区


fdt_get_header
========================

::

    #define fdt_get_header(fdt, field)  \
        (fdt32_ld(&((const struct fdt_header *)(fdt))->field))


``fdt_get_header`` 用于从dtb的header读取指定的信息．


fdt_get_mem_rsv
==================

::

    int fdt_get_mem_rsv(const void *fdt, int n, uint64_t *address, uint64_t *size)
    {
        const struct fdt_reserve_entry *re;

        FDT_RO_PROBE(fdt);
        re = fdt_mem_rsv(fdt, n);
        if(!re)
            return -FDT_ERR_BADOFFSET;

        *address = fdt64_ld(&re->address);
        *size = fdt64_ld(&re->size);

        return 0;
    }

``fdt_get_mem_rsv`` 用于获得dtb保留区中指定区域的地址和长度


fdt_get_name
================

::

    //fdt: 指向dtb
    //nodeoffset: device-node在dtb devicetree structure区域内的偏移
    //len: 用于存储名字的长度
    const char *fdt_get_name(const void *fdt, int nodeoffset, int *len)
    {
        //获取nodeoffset对应的指针
        const struct fdt_node_header *nh = fdt_offset_ptr_(fdt, nodeoffset);
        const char *nameptr;
        int err;

        //对fdt进行最小健全性检测，以及检查device-node的合法性
        if((err = fdt_ro_probe_(fdt)) != 0 || ((err = fdt_check_node_offset_(fdt, nodeoffset)) < 0))
            goto fail;

        //获取name
        nameptr = nh->name;

        //如果当前版本小于17
        if(fdt_version(fdt) < 0x10) {
            const char *leaf;
            leaf = strrchr(nameptr, '/');
            if(leaf == NULL) {
                err = -FDT_ERR_BADSTRUCTURE;
                goto fail;
            }
            nameptr = leaf + 1;
        }

        if(len)
            *len = strlen(strlen(nameptr));

        return nameptr;

    fail:
        if(len)
            *len = err;
        return NULL;
    }

``fdt_get_name`` 通过节点的偏移获得节点的名字.


fdt_get_property_namelen_
=============================

::

    //fdt: 指向dtb
    //offset: property在dtb devicetree structure中的偏移
    //name: 需要查找的property名字
    //namelen: 名字的长度
    //lenp: 用于存储property的偏移
    static const struct fdt_property *fdt_get_property_namelen_(const void *fdt, int offset, const char *name,
                                                            int namelen, int *lenp, int *poffset)
    {
        //获得offset参数开始之后的第一个property
        for(offset = fdt_first_property_offset(fdt, offset); (offset >= 0); (offset = fdt_next_property_offset(fdt, offset))) {
            const struct fdt_property *prop;

            if(!(prop = fdt_get_property_by_offset_(fdt, offset, lenp))) {
                offset = -FDT_ERR_INTERNAL;
                break;
            }

            //对比property属性名字是否和name参数一致
            if(fdt_string_eq_(fdt, fdt32_ld(&prop->nameoff), name, namelen)) {
                if(poffset)
                    *poffset = offset;
                return prop;
            }
        }
        if(lenp)
            *lenp = offset;

        return NULL;
    }

``fdt_get_property_namelen_`` 通过name参数获得dtb中的property


fdt_get_string
==================

::

    const char *fdt_get_string(const void *fdt, int stroffset, int *lenp)
    {
        //计算字符串在dtb内的偏移
        uint32_t absoffset = stroffset + fdt_off_dt_strings(fdt);
        size_t len;
        int err;
        const char *s, *n;

        //对dtb进行最小健全性检查
        err = fdt_ro_probe_(fdt);
        if(err != 0)
            goto fail;

        err = -FDT_ERR_BADOFFSET;
        //判断offset是否超过fdt的size
        If(absoffset >= fdt_totalsize(fdt))
            goto fail;
        len = fdt_totalsize(fdt) - absoffset;

        //获取dtb的magic并做不同的处理
        if(fdt_magic(fdt) == FDT_MAGIC) {
            if(stroffset < 0)
                goto fail;

            if(fdt_version(fdt) >= 17) {
                if(stroffset >= fdt_size_dt_strings(fdt))
                    goto fail;
                if((fdt_size_dt_strings(fdt) - stroffset) < len)
                    len = fdt_size_dt_strings(fdt) - stroffset;
            }
        } else if(fdt_magic(fdt) == FDT_SW_MAGIC) { 
            if((stroffset >= 0) || (stroffset < -fdt_size_dt_strings(fdt)))
                goto fail;
            if((-stroffset) < len)
                len = -stroffset;
        } else {
            err = -FDT_ERR_INTERNAL;
            goto fail;
        }

        s = (const char *)fdt + absoffset;
        n = memchr(s, '\', len);
        
        if(!n) {
            err = -FDT_ERR_TRUNCATED;
            goto fail;
        }

        if(lenp)
            *lenp = n - s;

        return s;
    }


``fdt_get_string`` 通过字符串在dtb devicetree strings区域内的偏移，获得对应的字符串



fdt_getprop
===============

::

    const void *fdt_getprop(const void *fdt, int nodeoffset, const char *name ,int *lenp)
    {
        return fdt_getprop_namelen(fdt, nodeoffset, name, strlen(name), lenp);
    }


``fdt_getprop`` 通过名字获得device-node中的属性值


fdt_getprop_namelen
======================

::

    const void *fdt_getprop_namelen(const void *fdt, int nodeoffset, const char *name, int namelen, int *lenp)
    {
        int poffset;
        const struct fdt_property *prop;

        prop = fdt_get_property_namelen_(fdt, nodeoffset, name, namelen, lenp, &poffset);
        if(!prop)
            return NULL;

        if(fdt_version(fdt) < 0x10 && (poffset + sizeof(*prop)) % 8 && fdt32_ld(&prop->len) >= 8)
            return prop->data + 4;

        return prop->data;
    }


``fdt_getprop_namelen`` 用于获得device-node内部属性的值




fdt_last_comp_version
========================

::

    #define fdt_last_comp_version(fdt)      (fdt_get_header(fdt, last_comp_version))


``fdt_last_comp_version`` 用于读取dtb header的last_comp_version信息


fdt_magic
==============

::

    #define fdt_magic(fdt) (fdt_get_header(fdt, magic))


fdt_mem_rsv
==============

::

    int fdt_get_mem_rsv(const void *fdt, int n, uint64_t *address, uint64_t *size)
    {
        const struct fdt_reserve_entry *re;

        FDT_RO_PROBE(fdt);
        re = fdt_mem_rsv(fdt, n);
        if(!re)
            return -FDT_ERR_BADOFFSET;

        *address = fdt64_ld(&re->address);
        *size = fdt64_ld(&re->size);

        return 0;
    }

``fdt_get_mem_rsv`` 用于获取dtb保留区中指定区域的地址和长度




fdt_next_node
=================

::

    //fdt: 指向dtb
    //offset: 指向当前device-node在dtb devicetree structure区域中的偏移
    //depth: 用于识别当前节点的深度
    int fdt_next_node(const void *fdt, int offset, int *depth)
    {
        int nexoffset = 0;
        uint32_t tag;

        //判断offset对应的device-node是否有效
        if(offset >= 0)
            if((nextoffset = fdt_check_node_offset_(fdt, offset)) < 0)

        do {
            offset = nextoffset;
            //获取当前tag的下一个tag及偏移
            tag = fdt_next_tag(fdt, offset, &nextoffset);

            switch(tag) {
            case FDT_PROP:
            case FDT_NOP:
                break;
            //如果tag值为FDT_BEGIN_NODE，那么当前节点包含了一个子节点
            case FDT_BEGIN_NODE:
                if(depth)
                    (*depth)++;
                break;
            case FDT_END_NODE:
                if(depth && ((--(*depth)) < 0))
                    return nextoffset;
                break;
            case FDT_END:
                if((nextoffset >= 0) || ((nextoffset == -FDT_ERR_TRUNCTED) && !depth))
                    return -FDT_ERR_NOTFOUND;
                else
                    return nextoffset;
            }
        } while(tag != FDT_BEGIN_NODE);

        return offset;
    }

``fdt_next_node`` 用于获得当前device-node的下一个device-node


fdt_next_tag
================

::
    
    uint32_t fdt_next_tag(const void *fdt, int startoffset, int *nextoffset)
    {
        const fdt32_t *tagp, *lenp;
        uint32_t tag;
        int offset = startoffset;
        const char *p;

        *nextoffset = -FDT_ERR_TRUNCATED;
        tagp = fdt_offset_ptr(fdt, offset, FDT_TAGSIZE);
        if(!tagp)
            return FDT_END;
        tag = fdt32_to_cpu(*tagp);
        offset += FDT_TAGSIZE;

        *nextoffset = -FDT_ERR_BADSTRUCTURE;
        switch(tag) {
        case FDT_BEGIN_NODE:
            do {
                p = fdt_offset_ptr(fdt, offset++, 1);
            } while(p && (*p != '\0'));
            if(!p)
                return FDT_END;
            break;

        case FDT_PROP:
            lenp = fdt_offset_ptr(fdt, offset, sizeof(*lenp));
            if(!lenp)
                return FDT_END;
            offset += sizeof(struct fdt_property) - FDT_TAGSIZE + fdt32_to_cpu(*lenp);
            if(fdt_version(fdt) < 0x10 && fdt32_to_cpu(*lenp) >= 8 && ((offset - fdt32_to_cpu(*lenp)) % 8) != 0)
                offset += 4;
            break;
        case FDT_END:
        case FDT_END_NODE:
        case FDT_NOP:
            break;
        }

    }



fdt_off_dt_strings
====================

::

    #define fdt_off_dt_strings(fdt) (fdt_get_header(fdt, off_dt_strings))
    #define fdt_off_mem_rsvmap(fdt) (fdt_get_header(fdt, off_mem_rsvmap))
    #define fdt_off_dt_struct(fdt) (fdt_get_header(fdt, off_dt_struct))


``fdt_off_dt_strings`` 用于读取dtb header的off_dt_strings信息．



fdt_offset_ptr
==================

::

    //fdt: 指向dtb
    //offset: device-node在dtb structure区域内的偏移
    //len: 表示device-node的长度
    const void *fdt_offset_ptr(const void *fdt, int offset, unsigned int len)
    {
        unsigned absoffset = offsdt + fdt_off_dt_struct(fdt);

        if((absoffset < offset) || ((absoffset + len) < absoffset) 
        || (absoffset + len) > fdt_totalsize(fdt))
            return NULL;

        if(fdt_version(fdt) >= 0x11)
            if(((offset + len) < offset) || ((offset + len) > fdt_size_dt_struct(fdt)))
                return NULL;

        return fdt_offset_ptr_(fdt, offset);
    }


``fdt_offset_ptr`` 通过device-node在dtb structure内的偏移获得指向device-node的指针



fdt_offset_ptr_
===================

::

    //fdt: 指向dtb
    //offset: device-node在dtb structure区块内的偏移
    static inline const void *fdt_ofset_ptr_(const void *fdt, int offset)
    {
        return (const char*)fdt + fdt_off_dt_struct(fdt) + offset;
    }


``fdt_offset_ptr_`` 通过device-node在dtb structure内的偏移得到指向device-node的指针．

.. note::
    dtb的结构涉及如下图所示

    +------------------------------------------+
    |           boot_param_header              |
    +------------------------------------------+
    |           memory reserve map             |
    +------------------------------------------+
    |         device-tree structure            |
    +------------------------------------------+
    |         device-tree strings              |
    +------------------------------------------+




fdt_reserved_mem_save_node
===================================

::

    #define MAX_RESERVED_REGIONS 32
    static struct reserved_mem reserved_mem[MAX_RESERVED_REGIONS];
    //node: 指向节点偏移
    //uname: 指向预留区的名字
    //base: 预留区的起始地址
    //size: 预留区的长度
    void __init fdt_reserved_mem_save_node(unsigned long node, const char *uname, 
                        phys_addr_t base, phys_addr_t size)
    {
        struct reserved_mem *rmem = &reserved_mem[reserved_mem_count];

        if(reserved_mem_count == ARRAY_SIZE(reserved_mem)) {
            pr_err("not enough space all defined regions.\n");
            return;
        }

        rmem->fdt_node = node;
        rmem->name = uname;
        rmem->base = base;
        rmem->size = size;

        reserved_mem_count++;

        return;
    }


``fdt_reserved_mem_save_node`` 用于将dts中"reserved-memory"添加到系统的reserved_mem[]数组中


.. note::
    内核使用一个struct reserved_mem数组维护着系统中所有的保留区




FDT_RO_PROBE
================


::

    #define FDT_RO_PROBE(fdt)   \
    {   \
        int err_; \
        if((err_ = fdt_ro_probe_(fdt)) != 0) \
            return err_;    \
    }

``FDT_RO_PROBE`` 用于检查dtb的完整性


fdt_ro_probe_
=================

::

    int fdt_ro_probe_(const void *fdt)
    {
        //检查DTB的MAGIC信息
        if(fdt_magic(fdt) == FDT_MAGIC) {
            if(fdt_version(fdt) < FDT_FIRST_SUPPORTED_VERSION)
                return -FDT_ERR_BADVERSION;
            if(fdt_last_comp_version(fdt) > FDT_LAST_SUPPORTED_VERSION)
                return -FDT_ERR_BADVERSION;
        } else if(fdt_magic(fdt) == FDT_SW_MAGIC) { 
            if(fdt_size_dt_struct(fdt) == 0)
                return -FDT_ERR_BADSTATE;
        } else {
            return -FDT_ERR_BADMAGIC;
        }

        return 0;
    }

``fdt_ro_probe_`` 用于一个只读dtb的最小健全性检查．


__fdt_scan_reserved_mem
=========================

::

    //node: 指向子节点的索引
    //uname: 子节点的名字
    //depth: 子节点的深度
    //data: 私有数据
    static int __init __fdt_scan_reserved_mem(unsigned long node, const char *uname,
                                        int depth, void *void)
    {
        static int found;
        int err;

        //判断节点是否是reserved-memory节点内的子节点
        if(!fount && depth == 1 && strcmp(uname, "reserved-memory") == 0) {
            if(__reserved_mem_check_root(node) != 0) { 
                pr_err("reserved memory: unsupported node format, ignoring\n");
                return 1;
            }
            fount = 1;
            return 0;
        } else if(!found) {
            return 0;
        } else if(found && depth < 2) {
            return 1;
        }

        //判断节点的status是否为okay
        if(!of_fdt_device_is_available(initial_boot_params, node))
            return 0;

        //将节点的reg属性对应的预留区加入到MEMBLOCK内存分配器的保留区
        err = __reserved_mem_reserve_reg(node, uname);
        if(err == -ENOENT && of_get_flat_dt_prop(node, "size", NULL))
            fdt_reserved_mem_save_node(node, uname, 0, 0);

        return 0;
    }

``__fdt_scan_reserved_mem`` 用于将dts中reserved-memory节点包含的子节点预留区加入到系统内进行维护．




fdt_size_dt_strings
=====================

::

    #define fdt_size_dt_strings(fdt) (fdt_get_header(fdt, size_dt_strings))


``fdt_size_dt_strings`` 用于读取dtb header的dt_strings_size信息


fdt_size_dt_struct
===================

::

    #define fdt_size_dt_struct(fdt) (fdt_get_header(fdt, size_dt_struct))


``fdt_size_dt_struct`` 用于读取dtb header的dt_struct_size信息


fdt_string_eq_
================

::

    static int fdt_string_eq_(const void *fdt, int stroffset, const char *s, int len)
    {
        int slen;
        const char *p = fdt_get_string(fdt, stroffset, &slen);

        return p && (slen == len) && (memcmp(p, s, len) == 0);
    }

``fdt_string_eq_`` 用于对比offset对应dtb devicetree strings区域内字符串与参数s给定的字符串是否相等


fdt_totalsize
================

::

    #define fdt_totalsize(fdt) (fdt_get_header(fdt, totalsize))


``fdt_totalsize`` 用于读取dtb header的totalsize信息


fill_pmd_pags
================

::

    static void __init fill_pmd_gaps(void)
    {
        struct static_vm *svm;
        struct vm_struct *vm;
        unsigned long addr, next = 0;
        pmd_t *pmd;

        list_for_each_entry(svm, &static_vmlist, list) {
            vm  = &svm->vm;
            addr = (unsigned long)vm->addr;
            if(addr < next)
                continue;

            if((addr & ~PMD_MASK) == SECTION_SIZE) {
                pmd = pmd_off_k(addr);
                if(pmd_none(*pmd))
                    pmd_empty_section_gap(addr & PMD_MASK);
            }
            addr += vm->size;
            if((addr & ~PMD_MASK) == SECTION_SIZE) {
                pmd = pmd_off_k(addr) + 1;
                if(pmd_none(*pmd))
                    pmd_empty_section_gap(addr);
            }
            next = (addr + PMD_SIZE - 1) & PMD_MASK;
        }
    }

``fill_pmd_gaps`` 用于检查静态映射区的虚拟地址，是否存在PMD入口值占用了一个，并且基数PMD入口


find_limits
===============

::

    static void __init find_limits(unsigned long *min, unsigned long *max_low, unsigned long *max_high)
    {
        *max_low = PFN_DOWN(memblock_get_current_limit());
        *min = PFN_UP(memblock_start_of_DRAM());
        *max_high = PFN_DOWN(memblock_end_of_DRAM());
    }


``find_limits`` 获得物理地址低端物理内存的起始页帧和终止页帧以及MEMBLOCK内存分配器支持的最大页帧


fix_to_virt
==============

::

    static __always_inline unsigned long fix_to_virt(const unsigned int idx)
    {
        BUILD_BUG_ON(idx >= __end_of_fixed_addresses);
        return __fix_to_virt(idx);
    }


``fix_to_virt`` 通过FIXMAP索引获得对应的虚拟地址



fixmap_pmd
=============

::

    static inline pmd_t * __init fixmap_pmd(unsigned long addr)
    {
        pgd_t *pgd = pgd_offset_k(addr);
        pgd_t *pud = pud_offset(pgd, addr);
        pgd_t *pmd = pmd_offset(pud, addr);

        return pmd;
    }


``fixmap_pmd`` 用于获得FIXMAP区间虚拟地址对应的PMD入口地址


flush_pmd_entry
===================

::

    static inline void flush_pmd_entry(void *pmd)
    {
        const unsigned int __tbl_flag = __cpu_tlb_flags;

        tlb_op(TLB_DCLEAN, "c7, c10, 1 @ flush_pmd", pmd);
        tlb_l2_op(TLB_L2CLEAN_FR, "c15, c9, 1 @ L2 flush_pmd", pmd);

        if(tlb_flag(TLB_WB))
            dsb(ishst);
    }


``flush_pmd_entry`` 的目的是 'clean data of unified cache line by mva to poc'


























