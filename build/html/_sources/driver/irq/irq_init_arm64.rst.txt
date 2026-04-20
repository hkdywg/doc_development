ARM64中断初始化
=================

init_IRQ
----------

ARM64的中断初始化主要在init_IRQ中完成，包括中断栈的初始化以及中断控制器的初始化


::


    void __init init_IRQ(void)
    {
        init_irq_stacks();  //中断栈的初始化，中断栈将从vmalloc区域分配，每个CPU的中断栈指针将保存在全局per-cpu变量irq_stack_ptr中
        irqchip_init();     //初始化irq控制器，并注册irq_domain
        if (!handle_arch_irq)
            panic("No interrupt controller found.");

        if (system_uses_irq_prio_masking()) {
            /*
             * Now that we have a stack for our IRQ handler, set
             * the PMR/PSR pair to a consistent state.
             */
            WARN_ON(read_sysreg(daif) & PSR_A_BIT);
            local_daif_restore(DAIF_PROCCTX_NOIRQ);
        }
    }

    void __init irqchip_init(void)
    {
        //扫描__irqchip_of_table，匹配DTB中定义的中断控制器，匹配成功则调用中断控制器设置的初始化函数
        of_irq_init(__irqchip_of_table);
        acpi_probe_device_table(irqchip);
    }


of_irq_init
-------------

首先看一下__irqchip_of_table的来历

::

    //include/linux/of.h 
    #if defined(CONFIG_OF) && !defined(MODULE)
    #define _OF_DECLARE(table, name, compat, fn, fn_type)			\
        static const struct of_device_id __of_table_##name		\
            __used __section(__##table##_of_table)			\
             = { .compatible = compat,				\
                 .data = (fn == (fn_type)NULL) ? fn : fn  }
    #else
    #define _OF_DECLARE(table, name, compat, fn, fn_type)			\
        static const struct of_device_id __of_table_##name		\
            __attribute__((unused))					\
             = { .compatible = compat,				\
                 .data = (fn == (fn_type)NULL) ? fn : fn }
    #endif

    #define OF_DECLARE_1(table, name, compat, fn) \
            _OF_DECLARE(table, name, compat, fn, of_init_fn_1)
    #define OF_DECLARE_1_RET(table, name, compat, fn) \
            _OF_DECLARE(table, name, compat, fn, of_init_fn_1_ret)
    #define OF_DECLARE_2(table, name, compat, fn) \
            _OF_DECLARE(table, name, compat, fn, of_init_fn_2)

    //include/linux/irqchip.h
    #define IRQCHIP_DECLARE(name, compat, fn) OF_DECLARE_2(irqchip, name, compat, fn)

对于每种中断控制器，都会通过IRQCHIP_DECLARE静态声明自己的struct of_device_id 结构体。下面针对GIC-V4进行分析

::


    IRQCHIP_DECLARE(gic_400, "arm,gic-400", gic_of_init);

    等价于

    static const struct of_device_id __of_table_gic-400  \
        __used __section("__irqchip_of_table")  \
        = { .compatible = "arm,gic-400" ,   \
            .data = gic_of_init }


不同的中断控制器有对应的IRQCHIP_DECLARE声明，他们都位于__irqchip_of_table段，of_irq_init就是遍历__irqchip_of_table段中所有的中断控制器，
对其执行相应的中断控制器初始化

::


    void __init of_irq_init(const struct of_device_id *matches)
    {
        const struct of_device_id *match;
        struct device_node *np, *parent = NULL;
        struct of_intc_desc *desc, *temp_desc;
        struct list_head intc_desc_list, intc_parent_list;

        INIT_LIST_HEAD(&intc_desc_list);    //初始化两个list，分别为dts节点中init-controller属性的list和init-controller-parent属性的list
        INIT_LIST_HEAD(&intc_parent_list);

        for_each_matching_node_and_match(np, matches, &match) {     //遍历每个中断控制器为其建立intc_dest,并设置每个中断控制器的parent
            if (!of_property_read_bool(np, "interrupt-controller") ||   //如果当前节点不是interrupt-controller或者处于disabled状态则继续遍历
                    !of_device_is_available(np))
                continue;

            if (WARN(!match->data, "of_irq_init: no init function for %s\n",
                 match->compatible))
                continue;

            /*
             * Here, we allocate and populate an of_intc_desc with the node
             * pointer, interrupt-parent device_node etc.
             */
            desc = kzalloc(sizeof(*desc), GFP_KERNEL);      //为desc分配空间
            if (!desc) {
                of_node_put(np);
                goto err;
            }

            desc->irq_init_cb = match->data;    //中断初始化回调，match->data就是上面的__of_table_gic-400.data
            desc->dev = of_node_get(np);
            desc->interrupt_parent = of_irq_find_parent(np);    //解析当前节点的parent
            if (desc->interrupt_parent == np)
                desc->interrupt_parent = NULL;
            list_add_tail(&desc->list, &intc_desc_list);
        }

        /*
         * The root irq controller is the one without an interrupt-parent.
         * That one goes first, followed by the controllers that reference it,
         * followed by the ones that reference the 2nd level controllers, etc.
         */
        while (!list_empty(&intc_desc_list)) {
            /*
             * Process all controllers with the current 'parent'.
             * First pass will be looking for NULL as the parent.
             * The assumption is that NULL parent means a root controller.
             */
            list_for_each_entry_safe(desc, temp_desc, &intc_desc_list, list) {
                int ret;

                if (desc->interrupt_parent != parent)
                    continue;

                list_del(&desc->list);

                of_node_set_flag(desc->dev, OF_POPULATED);

                pr_debug("of_irq_init: init %pOF (%p), parent %p\n",
                     desc->dev,
                     desc->dev, desc->interrupt_parent);
                //执行中断初始化函数
                ret = desc->irq_init_cb(desc->dev,
                            desc->interrupt_parent);
                if (ret) {
                    of_node_clear_flag(desc->dev, OF_POPULATED);
                    kfree(desc);
                    continue;
                }

                /*
                 * This one is now set up; add it to the parent list so
                 * its children can get processed in a subsequent pass.
                 */
                list_add_tail(&desc->list, &intc_parent_list);
            }

            /* Get the next pending parent that might have children */
            desc = list_first_entry_or_null(&intc_parent_list,
                            typeof(*desc), list);
            if (!desc) {
                pr_err("of_irq_init: children remain, but no parents\n");
                break;
            }
            list_del(&desc->list);
            parent = desc->dev;
            kfree(desc);
        }

        list_for_each_entry_safe(desc, temp_desc, &intc_parent_list, list) {
            list_del(&desc->list);
            kfree(desc);
        }
    err:
        list_for_each_entry_safe(desc, temp_desc, &intc_desc_list, list) {
            list_del(&desc->list);
            of_node_put(desc->dev);
            kfree(desc);
        }
    }


gic_of_init
--------------

::

    //drivers/irqchip/irq-gic.c
    int __init
    gic_of_init(struct device_node *node, struct device_node *parent)
    {
        struct gic_chip_data *gic;
        int irq, ret;

        if (WARN_ON(!node))
            return -ENODEV;

        if (WARN_ON(gic_cnt >= CONFIG_ARM_GIC_MAX_NR))
            return -EINVAL;

        gic = &gic_data[gic_cnt];

        ret = gic_of_setup(gic, node);  //根据device node初始化gic
        if (ret)
            return ret;

        /*
         * Disable split EOI/Deactivate if either HYP is not available
         * or the CPU interface is too small.
         */
        if (gic_cnt == 0 && !gic_check_eoimode(node, &gic->raw_cpu_base))
            static_branch_disable(&supports_deactivate_key);

        ret = __gic_init_bases(gic, &node->fwnode); //此函数中会设置中断处理的主函数
        if (ret) {
            gic_teardown(gic);
            return ret;
        }

        if (!gic_cnt) {
            gic_init_physaddr(node);
            gic_of_setup_kvm_info(node);
        }

        if (parent) {
            irq = irq_of_parse_and_map(node, 0);
            gic_cascade_irq(gic_cnt, irq);
        }

        if (IS_ENABLED(CONFIG_ARM_GIC_V2M))
            gicv2m_init(&node->fwnode, gic_data[gic_cnt].domain);

        gic_cnt++;
        return 0;
    }


::


    static int __init __gic_init_bases(struct gic_chip_data *gic,
                       struct fwnode_handle *handle)
    {
        char *name;
        int i, ret;

        if (WARN_ON(!gic || gic->domain))
            return -EINVAL;

        if (gic == &gic_data[0]) {
            /*
             * Initialize the CPU interface map to all CPUs.
             * It will be refined as each CPU probes its ID.
             * This is only necessary for the primary GIC.
             */
            for (i = 0; i < NR_GIC_CPU_IF; i++)
                gic_cpu_map[i] = 0xff;
    #ifdef CONFIG_SMP
            set_smp_cross_call(gic_raise_softirq);
    #endif
            cpuhp_setup_state_nocalls(CPUHP_AP_IRQ_GIC_STARTING,
                          "irqchip/arm/gic:starting",
                          gic_starting_cpu, NULL);
            //设置中断顶层处理函数handle_arch_irq为gic_handle_irq，此为中断处理的主函数
            set_handle_irq(gic_handle_irq);
            if (static_branch_likely(&supports_deactivate_key))
                pr_info("GIC: Using split EOI/Deactivate mode\n");
        }

        if (static_branch_likely(&supports_deactivate_key) && gic == &gic_data[0]) {
            name = kasprintf(GFP_KERNEL, "GICv2");
            gic_init_chip(gic, NULL, name, true);
        } else {
            name = kasprintf(GFP_KERNEL, "GIC-%d", (int)(gic-&gic_data[0]));
            gic_init_chip(gic, NULL, name, false);  //进一步初始化gic_chip
        }

        ret = gic_init_bases(gic, handle);  //中断控制器初始化
        if (ret)
            kfree(name);

        return ret;
    }



