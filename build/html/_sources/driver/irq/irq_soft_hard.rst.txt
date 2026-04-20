创建软硬中断号映射
=====================

of_platform_default_populate_init
----------------------------------

::

    static int __init of_platform_default_populate_init(void)
    |--//Handle certain compatibles explicitly
    |--for_each_matching_node(node, reserved_mem_matches)
    |     of_platform_device_create(node, NULL, NULL);
    |--node = of_find_node_by_path("/firmware");
    |--if (node)
    |      of_platform_populate(node, NULL, NULL, NULL);
    |      of_node_put(node);
    |  //Populate everything else
    |--of_platform_default_populate(NULL, NULL, NULL);
           |--of_platform_populate(root, of_default_bus_match_table, lookup,parent);
                  |--for_each_child_of_node(root, child)
                         //Create a device for a node and its children
                         of_platform_bus_create(child, of_default_bus_match_table, lookup, parent, true);
                             |  //对amba设备的处理，包含对中断号映射处理
                             |--if (of_device_is_compatible(bus, "arm,primecell"))
                             |      of_amba_device_create(bus, bus_id, platform_data, parent);
                             |  //Alloc, initialize and register an of_device
                             |--of_platform_device_create_pdata(bus, bus_id, platform_data, parent);
                             |  //对platform device的处理
                             |--for_each_child_of_node(bus, child)
                                    of_platform_bus_create(child, matches, lookup, &dev->dev, strict);



start_kernel-->arch_call_rest_init---->...----->do_initcalls会调用of_platform_default_populate_init，此处我们重点关注of_amba_device_create，其中包含了软硬中断的映射

::

	of_amba_device_create(bus, bus_id, platform_data, parent)
    |--struct amba_device *dev;
    |--dev = amba_device_alloc(NULL, 0, 0);
    |--初始化dev通用设备信息
    |--for (i = 0; i < AMBA_NR_IRQS; i++)
    |       //创建软硬中断号映射并将软中断号保存在dev->irq[i]
    |       dev->irq[i] = irq_of_parse_and_map(node, i);
    |           |--struct of_phandle_args oirq;
    |           |  //解析中断属性存放到oirq->args[]中
    |           |--of_irq_parse_one(dev, index, &oirq);
    |           |--irq_create_of_mapping(&oirq)
    |                  |--struct irq_fwspec fwspec; 
    |                  |--of_phandle_args_to_fwspec(oirq->np, oirq->args,oirq->args_count, &fwspec);
    |                  |--irq_create_fwspec_mapping(&fwspec);
    |--of_address_to_resource(node, 0, &dev->res);
    |--amba_device_add(dev, &iomem_resource);


of_amba_device_create的过程会通过irq_of_parse_and_map为每一个硬件中断号创建映射，并将分配的软中断号保存在dev->irq[i]中

::

	irq_create_fwspec_mapping(struct irq_fwspec *fwspec)
    |--domain = irq_find_matching_fwspec(fwspec, DOMAIN_BUS_WIRED);
    |  //对硬中断号进行转换保存在hwirq中，对于gic，GIC硬中断号=dts硬中断号+32
    |--irq_domain_translate(domain, fwspec, &hwirq, &type)
    |   //如果已经映射过则通过硬件中断号查找到虚拟中断号
    |--virq = irq_find_mapping(domain, hwirq);
    |  //否则将根据硬件中断号，分配软件虚拟中断号, 期间会创建irq_desc
    |--if (irq_domain_is_hierarchy(domain)) //级联的domain
    |      virq = irq_domain_alloc_irqs(domain, 1, NUMA_NO_NODE, fwspec);
    |  else
    |      virq = irq_create_mapping(domain, hwirq);
    |--irq_data = irq_get_irq_data(virq);
    |  //设置触发类型到irq_data, 它将在request_threaded_irq->__setup_irq时会使用来设置irqaction
    |--irqd_set_trigger_type(irq_data, type);
    |--return virq;

irq_create_mapping
--------------------

::

    irq_create_mapping(struct irq_domain *host, irq_hw_number_t hwirq)
    |  //Map a hardware interrupt into linux irq space,每个硬中断号只能映射到一个软中断号
    |--irq_create_mapping_affinity(host, hwirq, NULL);
           |--struct device_node *of_node;
           |--of_node = irq_domain_get_of_node(domain);
           |  //Check if mapping already exists,如果存在，通过硬中断号，可以找到软中断号
           |--virq = irq_find_mapping(domain, hwirq);
           |  if (virq) 
           |      return virq;
           |--virq = irq_domain_alloc_descs(-1, 1, hwirq, of_node_to_nid(of_node),affinity);
           |  //建立软中断号和硬中断号的映射关系
           |--irq_domain_associate(domain, virq, hwirq)

irq_create_mapping首先通过irq_find_mapping检查是否软硬中断号映射已经存在，如果不存在则通过irq_domain_alloc_descs分配中断描述符，并返回软中断号，irq_domain_associate主要是通过线性映射或radix tree映射，以硬中断号为索引，建立硬中断号与软中断号的映射关系


   
















