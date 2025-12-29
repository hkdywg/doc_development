linux中断处理
==============

注册中断
-----------

中断函数注册接口

::

    int request_threaded_irq(unsigned int irq, irq_handler_t handler,
                         irq_handler_t thread_fn, unsigned long irqflags,
                         const char *devname, void *dev_id)


=============   ==========================================================================================
参数            说明
-------------   ------------------------------------------------------------------------------------------
irq             IRQ软中断号
hanlder         中断发生时优先执行handler,如果此参数为NULL且thread_fn不为空，系统执行默认的handler
thread_fn       中断线程化的处理程序，如果不为空会创建一个内核线程。handler和thread_fn不能同时为空
irqflags        中断标志位
devname         中断名称
dev_id          传递给中断处理程序的参数
=============   ==========================================================================================


::

    request_threaded_irq(irq, handler, thread_fn,  irqflags，devname, dev_id)
    |  //对于共享中断，通常通过dev_id来查询寄存器，确定哪个外设产生的中断
    |--if (((irqflags & IRQF_SHARED) && !dev_id) || 
    |        (!(irqflags & IRQF_SHARED) && (irqflags & IRQF_COND_SUSPEND)) ||
    |        ((irqflags & IRQF_NO_SUSPEND) && (irqflags & IRQF_COND_SUSPEND)))
    |      return -EINVAL;
    |--desc = irq_to_desc(irq);
    |  //判断是否设置_IRQ_NOREQUEST标志，它是系统预留的
    |  //_IRQ_PER_CPU_DEVID标志是per cpu中断，需要用request_percpu_irq()函数注册中断
    |--if (!irq_settings_can_request(desc) ||
    |         WARN_ON(irq_settings_is_per_cpu_devid(desc)))
    |      return -EINVAL;
    |  //primary handler和thread_fn不能同时为NULL，primary handler为NULL，
    |  //则采用默认的irq_default_primary_handler
    |--if (!handler)
    |      if (!thread_fn) 
    |          return -EINVAL;
    |      handler = irq_default_primary_handler;
    |  //分配并初始化irqaction
    |--action = kzalloc(sizeof(struct irqaction), GFP_KERNEL)
    |  action->handler = handler;//初始化primary handler
    |  action->thread_fn = thread_fn;//初始化线程中断处理函数
    |  action->flags = irqflags;
    |  action->name = devname;
    |  action->dev_id = dev_id;
    |  //使能irq chip供电
    |--irq_chip_pm_get(&desc->irq_data)
    |  //注册irqaction到irq_desc
    |--__setup_irq(irq, desc, action)

__setup_irq承担了主要的注册工作

- __setup_irq

::

    __setup_irq(unsigned int irq, struct irq_desc *desc, struct irqaction *new) 
    |--new->irq = irq;
    |  //设置触发类型，它在irq_create_fwspec_mapping创建软硬中断映射时初始化
    |--if (!(new->flags & IRQF_TRIGGER_MASK))
    |      new->flags |= irqd_get_trigger_type(&desc->irq_data);
    |--nested = irq_settings_is_nested_thread(desc);
    |  //如果支持中断嵌套，thread_fn不能为NULL, primary handler为空默认设为irq_nested_primary_handler
    |  if (nested)
    |      new->handler = irq_nested_primary_handler;
    |  else
    |      //判断是否支持中断线程化,如果支持则强制中断线程化
    |      if (irq_settings_can_thread(desc))
    |          irq_setup_forced_threading(new);
    |  //>>>>>>对没有嵌套的中断线程处理函数创建内核线程
    |--if (new->thread_fn && !nested)
    |      setup_irq_thread(new, irq, false);
    |      if (new->secondary)
    |          setup_irq_thread(new->secondary, irq, true);
    |  //IRQCHIP_ONESHOT_SAFE表示中断控制器不支持中断嵌套(中断控制器支持ONESHOT)？
    |--if (desc->irq_data.chip->flags & IRQCHIP_ONESHOT_SAFE)
    |      new->flags &= ~IRQF_ONESHOT;
    |  //request irq chip resource
    |--if (!desc->action)
    |      irq_request_resources(desc);
    |  //>>>>>共享中断的处理
    |  //old非null，表示irq_desc已经注册了中断，代表共享中断
    |--old_ptr = &desc->action;
    |  old = *old_ptr;
    |  if (old)
    |      //NMI中断不支持共享？
    |      if (desc->istate & IRQS_NMI)
    |          ret = -EINVAL;
    |          goto out_unlock;
    |      //非共享中断、触发类型不一致、IRQF_ONESHOT标志不一致为不匹配情况
    |      if (!((old->flags & new->flags) & IRQF_SHARED) ||
    |                   (oldtype != (new->flags & IRQF_TRIGGER_MASK)) ||
    |                   ((old->flags ^ new->flags) & IRQF_ONESHOT)) 
    |          goto mismatch;
    |      //old_ptr循环移动指向irq_desc的irqaction链表的最后一个元素的next,thread_mask记录共享中断irqaction
    |      do {
    |          thread_mask |= old->thread_mask;
    |          old_ptr = &old->next;
    |          old = *old_ptr;
    |      } while (old);
    |      shared = 1;//表示一个共享中断
    |  
    |--if (new->flags & IRQF_ONESHOT)
    |      new->thread_mask = 1UL << ffz(thread_mask);
    |  // primary handler为NULL，又不支持ONESHOT的控制器，对于电平触发的中断会引发中断风暴
    |  else if (new->handler == irq_default_primary_handler && 
    |       !(desc->irq_data.chip->flags & IRQCHIP_ONESHOT_SAFE))
    |      ret = -EINVAL;
    |      goto out_unlock;
    |  //>>>>>>非共享中断的处理
    |--if (!shared)
    |      init_waitqueue_head(&desc->wait_for_threads);
    |      __irq_set_trigger(desc,new->flags & IRQF_TRIGGER_MASK);
    |      irq_activate(desc);
    |      清/设desc->istate标志，清/设&desc->irq_data标志
    |      if (irq_settings_can_autoenable(desc))
    |          irq_startup(desc, IRQ_RESEND, IRQ_START_COND);
    |  //将新的irqaction连入irq_desc的irqaction链表
    |--*old_ptr = new;
    |  //Check whether we disabled the irq via the spurious handler
    |  //before. Reenable it and give it another chance.？
    |--if (shared && (desc->istate & IRQS_SPURIOUS_DISABLED))
    |      desc->istate &= ~IRQS_SPURIOUS_DISABLED; 
    |      __enable_irq(desc);
    |--irq_setup_timings(desc, new);
    |--if (new->thread)
    |      wake_up_process(new->thread);
    |--if (new->secondary)
    |      wake_up_process(new->secondary->thread);
    |--register_irq_proc(irq, desc);
    |--register_handler_proc(irq, new);


__setup_irq会处理共享中断和非共享中断，最终会将irqaction链入irq_desc的irqaction链表完成注册。对于中断线程化会创建线程并会将其加入就绪队列。

1. irq_setup_forced_threading：如果没有设置_IRQ_NOTHREAD标志，则说明可以被中断线程化，则irq_setup_forced_threading执行强制中断线程化，它通过new->thread_fn = new->handler 将主中断处理函数赋值给中断线程函数，后面会通过setup_irq_thread来创建线程专门执行主处理函数，实现了中断处理的线程化
2. setup_irq_thread：会通过kthread_create创建内核线程，调度策略SCHED_FIFO，优先级50，对于中断线程化的情况，则主处理函数线程会"irq/中断号-中断名"为线程名，原有的线程处理函数线程会以"irq/中断号-s-中断名"; 对于非中断线程化的情况，则只会为线程处理函数线程创建名为"irq/中断号-中断名"的线程。同时会设置中断亲和标志IRQTF_AFFINITY？
3. 对于共享中断的处理：如果irq_desc上已经有irq_action，而本次又要链接新的irq_action，则说明为一个共享中断，共享中断需要检查不匹配的情况，在最后会将old_ptr循环移动指向irq_desc的irqaction链表的最后一个元素的next，old指向*old_ptr，同时thread_mask每个bit代表一个irqaction,记录了所有的共享中断，当desc->thread_active等于0，才能算中断处理完成。
4. new->handler == irq_default_primary_handler && !(desc->irq_data.chip->flags & IRQCHIP_ONESHOT_SAFE))：primary handler为irq_default_primary_handler ，说明请求时为NULL，有一种情况，如msi中断，中断控制器本身支持ONESHOT，则会设置IRQCHIP_ONESHOT_SAFE，没有设置IRQCHIP_ONESHOT_SAFE，说明中断控制器不支持ONESHOT，但是对于电平触发的中断，如果不设置primary handler，控制器又不支持ONESHOT，就会引发中断风暴，因此此情况下一定要设置primary handler
5. 非共享中断的处理：初始化desc->wait_for_threads等待队列？设置触发类型？清/设desc->istate标志，清/设&desc->irq_data标志
6. \*old_ptr = new：将新的irqaction连入irq_desc的irqaction链表
7. wake_up_process：唤醒中断线程

中断处理
-----------

gic_handle_irq
^^^^^^^^^^^^^^^

::

    <drivers/irqchip/irq-gic.c>
    static void __exception_irq_entry gic_handle_irq(struct pt_regs *regs)
    |--struct gic_chip_data *gic = &gic_data[0];
    |--void __iomem *cpu_base = gic_data_cpu_base(gic);
    |--do {
           //读取GIC的GICC_IAR寄存器，读取行为本身是对中断的ack
           irqstat = readl_relaxed(cpu_base + GIC_CPU_INTACK);
           //获取发生中断的硬中断号
           irqnr = irqstat & GICC_IAR_INT_ID_MASK;
           if (unlikely(irqnr >= 1020))
               break;
           //写入GICC_EOIR寄存器，通知CPU interface中断处理完成
           if (static_branch_likely(&supports_deactivate_key))
               writel_relaxed(irqstat, cpu_base + GIC_CPU_EOI);
           isb();
           //对SGI私有中断的处理
           if (irqnr <= 15)
               smp_rmb();
               this_cpu_write(sgi_intid, irqstat);
           handle_domain_irq(gic->domain, irqnr, regs);
       } while (1);


generic_handle_irq在__gic_init_bases函数中被设置为默认的中断处理函数，在前面的文章中已经解释过了

1. 读GIC的GICC_IAR寄存器，读取行为本身是对中断的ack，会让中断从pending状态进入到active状态
2. 写入GICC_EOIR寄存器，通知CPU interface中断处理完成，让中断从active状态进入到inactive状态
3. handle_domain_irq: 对于gic中断控制器会执行gic_of_init初始化，它会创建并注册irq_domain.第一个参数gic->domain就是gic初始化时创建的，它代表了中断控制器。。irqnr为硬中断号，通过硬
   中断号可以知道软中断号，然后以软中断号为索引可以获取到irq_desc，进一步获取到irq_data并获取到irqaction进行处理

handle_domain_irq
^^^^^^^^^^^^^^^^^^^^^

::

    handle_domain_irq(struct irq_domain *domain,unsigned int hwirq, struct pt_regs *regs)
    |--__handle_domain_irq(domain, hwirq, true, regs);
           |--unsigned int irq = hwirq;
           |--irq_enter();
           |  //以硬中断号为索引软中断号返回给irq
           |--irq = irq_find_mapping(domain, hwirq);
           |--generic_handle_irq(irq);
           |--irq_exit();


1. irq_enter: 显式的告诉linux内核现在进入中断上下文，主要通过增加preempt.count的HARDIRQ域计数值来实现
2. irq_find_mapping: 以硬中断号为索引找到软中断号,这里irq_domain会维护软硬件中断号的映射关系
3. generic_handle_irq: 为通用中断处理的主函数
4. irq_exit：irq_enter对应，退出中断上下文


generic_handle_irq
^^^^^^^^^^^^^^^^^^^^^^^^

::

    int generic_handle_irq(unsigned int irq)
    |--struct irq_desc *desc = irq_to_desc(irq);
    |--generic_handle_irq_desc(desc);
    |--desc->handle_irq(desc)
           |--handle_fasteoi_irq（desc）
                  |--handle_irq_event(desc);
                         |--__handle_irq_event_percpu(desc, &flags);
                                |--for_each_action_of_desc(desc, action)
                                       |  //标记中断被强制线程化
                                       |--if (irq_settings_can_thread(desc) &&
                                       |           !(action->flags & (IRQF_NO_THREAD | IRQF_PERCPU | IRQF_ONESHOT)))
                                       |       lockdep_hardirq_threaded();
                                       |--res = action->handler(irq, action->dev_id);   
                                       |--switch (res)
                                          //primary handler处理完毕，需要唤醒中断线程
                                          case IRQ_WAKE_THREAD:
                                              __irq_wake_thread(desc, action);
                                          //无中断线程
                                          case IRQ_HANDLED:
                                              *flags |= action->flags;   


1. handle_arch_irq可以理解为中断从底层处理进入顶层处理的入口，而desc->handle_irq为中断的回调。最终会调用action->handler，此处为驱动程序中注册的中断处理函数
2. action->handler函数如果返回的是IRQ_WAKE_THREAD则唤醒中断线程执行，中断线程在注册中断时创建，如果返回IRQ_HANDLED则表示没有中断线程

.. note::
    request_threaded_irq会将参数hanlder传递给action->handler，如果此函数为空，将采用默认的irq_default_primary_hanlder。









