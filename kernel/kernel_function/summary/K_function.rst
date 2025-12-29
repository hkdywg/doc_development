KERNEL_END
=============

::

    #define KERNEL_END __end

``KERNEL_END`` 指向内核镜像结束虚拟地址


KERNEL_START
================

::

    #ifdef CONFIG_XIP_KERNEL
    #define KERNEL_START        _sdata
    #else
    #define KERNEL_START        _stext
    #endif

``KERNEL_START`` 代表内核镜像的起始虚拟地址


kmap_init
============

::

    static void __init kmap_init(void)
    {
    #ifdef CONFIG_HIGHMEM
        pkmap_page_table = early_pte_alloc(pmd_off_k(PKMAP_BASE), PKMAP_BASE, _PAGE_KERNEL_TABLE);
    #endif
        early_pte_alloc(pmd_off_k(FIXADDR_START), FIXADDR_START, _PAGE_KERNEL_TABLE);
    }

``kmap_init`` 用于建立PMD对应的PTE页表



kuser_init
===============

::

    static void __init kuser_init(void *vectors)
    {
        extern char __kuser_helper_start[], __kuser_helper_end[];
        int kuser_sz = __kuser_helper_end  - __kuser_helper_start;

        memcpy(vectors + 0x1000 - kuser_sz, __kuser_helper_start, kuser_sz);

        if(tls_emu || has_tls_reg)
            memcpy(vectors + 0xfe0, vectors + 0xfe8, 4);
    }


``kuser_init`` 用于将__kuser_helper_start到__kuser_helper_end之间的内容拷贝到异常向量表的指定位置




