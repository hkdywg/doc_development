raw_local_irq_disable
============================

::

    #define raw_local_irq_disable()     arch_local_irq_disable()

``raw_local_irq_disable`` 用于禁止本地中断，其作为一个过度接口，用于指向与体系相关的函数．



raw_smp_processor_id
=======================

::

    #define raw_smp_processor_id    (current_thread_info()->cpu)

    static inline struct thread_info *current_thread_info(void)
    {
        return (struct thread_info *)(current_stack_pointer & ~(THREAD_SIZE - 1));
    }

``raw_smp_processor_id`` 用于获得当前SMP系统使用的CPU号


rmem_cma_device_init
=======================

::

    static int rmem_cma_device_init(struct reserved_mem *rmem, struct device *dev)
    {
        dev_set_cma_area(dev, rmem->priv);
        return 0;
    }

    static inline void dev_set_cma_area(struct device *dev, struct cma *cma)
    {
        if(dev)
            dev->cma_area = cma;
    }

``rmem_cma_device_init`` 用于在CMA region初始化过程中，设置CMA region对应的device


rmem_cma_device_release
==========================

::

    static void rmem_cma_device_release(struct reserved_mem *rmem, struct device *dev)
    {
        dev_set_cma_area(dev, NULL);
    }


rmem_cma_setup
=================

::

    static int __init rmem_cma_setup(struct reserved_mem *rmem)
    {
        phys_addr_t align = PAGE_SIZE << max(MAX_ORDER - 1, pageblock_order);
        phys_addr_t mask = align - 1;
        unsigned long node = rmem->fdt_node;
        struct cma *cma;
        int err;

        if(!of_get_flat_dt_prop(node, "reusable", NULL) || of_get_flat_dt_prop(node, "no-map", NULL))
            return -EINVAL;

        if((rmem->base & mask) || (rmem->size & mask)) {
           pr_err("Reserved memory: incorrect alignment of CMA region\n");
           return -EINVAL;
        }

        err = cma_init_reserved_mem(rmem->base, rmem->size, 0, rmem->name, &cma);
        if(err) {
            pr_err("Reserved memory: unable to setup CMA region\n");
            return err;
        }
            
        dma_contiguous_early_fixup(rmem->base, rmem->size);

        if(of_get_flat_dt_prop(node, "linux, cma-default", NULL))
            dma_contiguous_set_default(cma);

        rmem->ops = &rmem_cma_ops;
        rmem->priv = cma;

        return 0;
    }

    RESERVEDMEM_OF_DECLARE(cma, "shared-dma-pool", rmem_cma_setup);

``rmem_cma_setup`` 将dts中reserved-memory节点的子节点，compatible属性值为"shared-dma-pool"的节点为CMA region


rmem_dma_setup
==================

::

    static int __init rmem_dma_setup(struct reserved_mem *rmem)
    {
        unsigned long node = rmem->fdt_node;

        //判断rmem对应的节点是否包含reusable属性
        if(of_get_flat_dt_prop(node, "reusable", NULL))
            return -EINVAL;

    #ifdef CONFIG_ARM
        if(!of_get_flat_dt_prop(node, "no-map", NULL)) {
            pr_err("Reserved memory: regions without no-map are not yet supported\n");
            return -EINVAL;
        }

        if(of_get_flat_dt_prop(node, "linux,dma-default", NULL)) {
            dma_reserved_default_memory = rmem;
        }
    #endif
        
        rmem->ops = &rmem_dma_ops;
        
        return 0;
    }

``rmem_dma_setup`` 用于初始化DMA的预留区


.. note::
    DMA的物理内存区域是不能给其他程序使用，所以要将DMA设置为独占，但"reusable"属性的存在代表不独占重复使用


RESERVEDMEM_OF_DECLARE
==========================

::

    #define RESERVEDMEM_OF_DECLARE(name, compat, init)      \
        _OF_DECLARE(reservedmem, name, compat, init, reservedmem_of_init_fn)

``RESERVEDMEM_OF_DECLARE`` 宏用在__reservedmem_of_table section内建立一个struct of_device_id其compat成员就是compat参数，并且该数据结构
的data成员就是init参数


__reserved_mem_alloc_size
=============================

::

    static int __init __reserved_mem_alloc_size(unsigned long node, const char *uname, phys_addr_t *res_base,
                                                        phys_addr_t *res_size)
    {
        int t_len = (dt_root_addr_cells + dt_root_size_cells) * sizeof(__be32);
        phys_addr_t start = 0, end = 0;
        phys_addr_t base = 0, align = 0, size;
        int len;
        const __be32 *prop;
        int nomap;
        int ret;

        //
        prop = of_get_flat_dt_prop(node, "size", &len);
        if(!prop)
            return -EINVAL;
        if(len != dt_root_size_cells * sizeof(__be32))
            return -EINVAL;

        size = dt_mem_next_cell(dt_root_size_cells, &prop);

        nomap = of_get_flat_dt_prop(node, "no-map", &len);

        prop = of_get_flat_dt_prop(node, "alignment", &len);
        if(prop) {
            if(len != dt_root_addr_cells * sizeof(__be32)) {
                return -EINVAL;
            }
            align = dt_mem_next_cell(dt_root_addr_cells, &prop);
        }

        if(IS_ENABLED(CONFIG_CMA) && of_flat_dt_is_compatible(node, "shared-dma-pool")
            && of_get_flat_dt_prop(node, "reusable", NULL) && 
            !of_get_flat_dt_prop(node, "no-map", NULL)) {
            unsigned long order = max_t(unsigned long, MAX_ORDER - 1, pageblock_order);
            align = max(align, (phys_addr_t)PAGE_SIZE << order);
        }

        prop = of_get_flat_dt_prop(node, "alloc-ranges", &len);
        if(prop) {
            if(len % t_len != 0)
                return -EINVAL;

            base = 0;
            while(len > 0) {
                start = dt_mem_next_cell(dt_root_addr_cells, &prop);
                end =  start + dt_mem_next_cell(dt_root_addr_cells, &prop);

                ret = early_init_dt_alloc_reserved_memory_arch(size, align, start, end, nomap, &base);

                if(ret == 0)
                    break;

                len -= t_len;
            }
        } else {
            ret = early_init_dt_alloc_reserved_memory_arch(size, align, 0, 0, nomap, &base);

        }

        if(base == 0)
            return -ENOMEM;

        *res_base = base;
        *res_size = size;
    }

``__reserved_mem_alloc_size`` 用于为dts reserved-memory节点中特定子节点分配内存，该类节点包含size属性，但不包含reg属性，
因此要对这类子节点分配物理内存．这类节点例如

::

    reserved-memory {
        #address-cells = <1>;
        #size-cells = <1>;
        ranges;

        default-pool  {
            compatible = "shared-dma-pool";
            size = <0x2000000>;
            alloc-ranges = <0x61000000 0x4000000>;
            alignment = <0x1000000>;
            reusable;
            linux,cma-default;
        };
    };


__reserved_mem_check_root
==============================

::

    static int __init __reserved_mem_check_root(unsigned long node)
    {
        const __be32 *prop;

        prop = of_get_flat_dt_prop(node, "#size-cells", NULL);
        if(!prop || be32_to_cpup(prop) != dt_root_size_cells)
            return -EINVAL;

        prop = of_get_flat_dt_prop(node, "#address-cells", NULL);
        if(!prop || be32_to_cpup(prop) != dt_root_size_cells)
            return -EINVAL;

        prop = of_get_flat_dt_prop(node, "ranges", NULL);
        if(!prop)
            return -EINVAL;

        return 0;

    }

``__reserved_mem_check_root`` 用于检查指定node的"#size-cells"属性值和"#address-cells"属性值是否一致，
并确保节点包含"ranges"属性


__reserved_mem_init_node
============================

::

    //rmem为reserved_mem[]数组中的成员
    static int __init __reserved_mem_init_node(struct reserved_mem *rmem)
    {
        extern const struct of_device_id __reservedmem_of_table[];
        const struct of_device_id *i;

        //获得__reservedmem_of_table表基地址，表里都是__reservedmem_of_table section成员
        //每个成员都包含特定的初始化程序
        for(i = __reservedmem_of_table; i < &__rmem_of_table_sentinel; i++)
        {
            reservedmem_of_init_fn initfn = i->data;
            const char *compat = i->compatible;
            
            //遍历所有成员，如果rmem对应节点的compatible和遍历到成员的compatible相同
            //则使用成员的初始化函数初始化该节点
            if(!of_flat_dt_is_compatible(rmem->fdt_node, compat))
                continue;

            if(initfn(rmem) == 0) {
                return 0; 
            }
        }

        return -ENOENT;
    }

``__reserved_mem_init_node`` 用于初始化rmem对应的节点



__rmem_check_for_overlap
==========================

::

    static void __init __rmem_check_for_overlap(void)
    {
        int i;

        //如果预留区的数量小于2，则没必要检测
        if(reserved_mem_count < 2)
            return;

        //对reserved_mem数组中预留区按基地址进行排序
        sort(reserved_mem, reserved_mem_count, sizeof(reserved_mem[0]), __rmem_cmp, NULL);

        for(i = 0; i < reserved_mem_count - 1; i++)
        {
            struct reserved_mem *this, *next;

            this = &reserved_mem[i];
            next = &reserved_mem[i + 1];
            if(!(this->base && next->base))
                continue;

            if(this->base + this->size > next->base)
            {
                phys_addr_t this_end, next_end;

                this_end = this->base + this->size; 
                next_end = next->base + next->size;
            }
        }
    }

``__rmem_check_for_overlap`` 检查reserved_mem维护的预留区是否存在重叠部分．


__round_mask
================

::

    #define __round_mask(x, y)      ((__typeof__(x))((y)-1))

