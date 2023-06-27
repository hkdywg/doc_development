list_add_tail
==============

::

    static inline void list_add_tail(struct list_head *new, struct list_head *head)
    {
        __list_add(new, head->prev, head);
    }

    static inline void __list_add(struct list_head *new,
                                  struct list_head *prev,
                                  struct list_head *next)
    { 
        if(!__list_add_valid(new, prev, next))
            return;

        next->prev = new;
        new->next = next;
        new->prev = prev;
        WRITE_ONCE(prev->next, new);
    }


``list_add_tail`` 将一个新节点加入到链表的末尾


list_for_each_entry
======================

::

    #define list_for_each_entry(pos, head, member)      \
        for(pos = list_first_entry(head, typeof(*pos), member));    \
            &pos->member != (head);     \
            pos = list_next_entry(pos, member)


``list_for_each_entry`` 用于遍历内嵌双链表的结构


local_irq_disable
=====================

::

    #define local_irq_disable() do { raw_local_irq_disable(); } while(0)

    #define raw_local_irq_disable() arch_local_irq_disable()

    static inline void arch_local_irq_disable(void)
    {
        asm volatible(
            "   cpsid i         @ arch_local_irq_disable"    
            :
            :
            : "memory", "cc");
    }



``local_irq_disable`` 用于禁止本地中断


lookup_processor
==================

::

    struct proc_info_list *lookup_processor(u32 midr)
    {
        struct proc_info_list *list = lookup_processor_type(midr);

        if(!list) {
            pr_err("CPU%u: configuration botched (ID %08x), CPU halted\n", smp_processor_id(), midr);
        }
        
        return list;
    }

``lookup_processor`` 用于获得体系芯片相关的proc_info_list结构

lookup_processor_type
=======================

::

    ENTRY(loopup_processor_type)
        stmfd   sp!, {r4 - r6, r9, lr}
        mov r9, r0
        bl  __lookup_processor_type
        mov r0, r5
        ldmfd sp!, {r4 -r6, r9, pc}
    ENDPROC(lookup_processor_type)





