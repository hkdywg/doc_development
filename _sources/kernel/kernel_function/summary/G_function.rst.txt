get_cr
=========

::

    static inline unsigned long get_cr(void)
    {
        unsigned long val;
        asm("mrc p15, 0, %0, c1, c0, 0 @ get CR" : "=r" (val) : : "cc");
        return val;
    }

``get_cr`` 用于获得arm的SCTLR(System Control Register)系统控制器


__get_cpu_architecture
==========================















