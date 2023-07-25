__va
==========

::

    #define __va(x)     ((void *)__phys_to_virt((phys_addr_t)(x)))


``__va`` 用于将一个物理地址转换成虚拟地址



vectors_base
================

::

    #define vectors_base()  (vectors_high() ? 0xffff0000 : 0)

``vectors_base`` 用于返回exception vector所在的虚拟地址


vectors_high
================

::

    #if __LINUX_ARM_ARCH__ >= 4
    #define vectors_high()  (get_cr() & CR_V)
    #else
    #define vectors_high() (0)
    #endif


``vectors_high`` 用于指明exception vector所在的位置，由SCTLR寄存器的'bit-13 V'决定．如果该bit为0，则exception vector位于0x00000000,反之
则为0xffff0000


vm_area_add_early
=====================

::

    static struct vm_struct *vmlist __initdata;

    void __init vm_area_early(struct vm_struct *vm)
    {
        struct vm_struct *tmp, **p;

        //判断vmap_initialized是否为true
        BUG_ON(vmap_initialized);

        for(p = &vmlist; (tmp = *p) != NULL; p = &tmp->next)
        {
            if(tmp->addr >= vm->addr) { 
                BUG_ON(tmp->addr < vm->addr + vm->size);
                break;
            } else {
                BUG_ON(tmp->addr + tmp->size > vm->addr);
            }
        }

        vm->next = *p'
        *p = vm;
    }

``vm_area_early`` 将一个vm_struct加入到内核早期的vmlist


vm_reseve_area_early
=======================


::

    void __init vm_reserve_area_early(unsigned long addr, unsigned long size, void *caller)
    {
        struct vm_struct *vm;
        struct static_vm *svm;

        svm = early_alloc_aligned(sizeof(*svm), __alignof__(*svm));

        vm = &svm->vm;
        vm->addr = (void *)addr;
        vm->size = size;
        vm->flags = VM_IOREMAP | VM_ARM_EMPTY_MAPPING;
        vm->caller = caller;
        add_static_vm_early(svm);
    }


``vm_reserve_area_early`` 给指定虚拟地址建立静态预留映射，但不对映实际的物理地址，只做预留作用



vmalloc_min
=============

::

    static void * __initdata vmmaloc_min = (void *)(VMALLOC_END - (240 << 20) - VMALLOC_OFFSET);


``vmalloc_min`` 用于指向VMMALOC内存区域最低地址



