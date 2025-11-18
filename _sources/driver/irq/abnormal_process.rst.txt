linux异常处理流程
=====================

linux异常处理与裸流程基本是一样的

1. 设置好异常向量表(把异常向量表放在异常向量的位置)
2. 写异常处理函数
3. 执行异常处理

- 异常向量表在启动过程中的流程所在的位置

::

    start_kernel()
        ...
        local_irq_disable()
        ...
        setup_arch(&command_line)
            paging_init
                devicemaps_init
                    early_trap_init(vectors)    //设置异常向量表
        ...
        trap_init()
        ...
        early_irq_init()
        init_IRQ()
        ...
        local_irq_enabled()



异常向量表的建立
-----------------

::

    void __init early_trap_init(void *vectors_base)
    {
    #ifndef CONFIG_CPU_V7M
        unsigned long vectors = (unsigned long)vectors_base; //异常向量表vectors的基址
        extern char __stubs_start[], __stubs_end[];     //汇编和链接脚本定义的各异常处理的核心代码
        extern char __vectors_start[], __vectors_end[];     //汇编中定义的异常向量表的标号 
        unsigned i;

        vectors_page = vectors_base;

        /*
         * Poison the vectors page with an undefined instruction.  This
         * instruction is chosen to be undefined for both ARM and Thumb
         * ISAs.  The Thumb version is an undefined instruction with a
         * branch back to the undefined instruction.
         */
        for (i = 0; i < PAGE_SIZE / sizeof(u32); i++)
            ((u32 *)vectors_base)[i] = 0xe7fddef1;

        /*
         * Copy the vectors, stubs and kuser helpers (in entry-armv.S)
         * into the vector page, mapped at 0xffff0000, and ensure these
         * are visible to the instruction stream.
         */
        //拷贝异常向量表到vectors起始地址
        memcpy((void *)vectors, __vectors_start, __vectors_end - __vectors_start);
        //拷贝异常处理核心代码到异常向量表base+0x1000位置
        memcpy((void *)vectors + 0x1000, __stubs_start, __stubs_end - __stubs_start);

        //从用户空间可以访问的内核段提供的用户代码拷贝到固定位置
        kuser_init(vectors_base);
        
        //刷异常向量这两页，如果icache中有相关代码的话
        flush_icache_range(vectors, vectors + PAGE_SIZE * 2);
    #else /* ifndef CONFIG_CPU_V7M */
        /*
         * on V7-M there is no need to copy the vector table to a dedicated
         * memory area. The address is configurable and so a table in the kernel
         * image can be used.
         */
    #endif
    }



异常向量表内容
---------------

以下内容在 arch/arm/kernel/entry-armv.S中定义

::

    .L__vectors_start:
        W(b)	vector_rst  //复位异常
        W(b)	vector_und  //未定义指令异常
        W(ldr)	pc, .L__vectors_start + 0x1000  //软中断swi异常
        W(b)	vector_pabt     //预取指异常
        W(b)	vector_dabt     //数据异常(如访问没有权限的地址)
        W(b)	vector_addrexcptn   //保留，没使用
        W(b)	vector_irq      //中断
        W(b)	vector_fiq      //快速中断

        .data
        .align	2

        .globl	cr_alignment
    cr_alignment:
        .space	4

以下内容在 arch/arm/kernel/vmlinux.lds.h中定义

::

    #define ARM_VECTORS							\
        __vectors_start = .;						\
        .vectors 0xffff0000 : AT(__vectors_start) {			\
            *(.vectors)						\
        }								\
        . = __vectors_start + SIZEOF(.vectors);				\
        __vectors_end = .;						\
                                        \
        __stubs_start = .;						\
        .stubs ADDR(.vectors) + 0x1000 : AT(__stubs_start) {		\
            *(.stubs)						\
        }								\
        . = __stubs_start + SIZEOF(.stubs);				\
        __stubs_end = .;						\
                                        \
        PROVIDE(vector_fiq_offset = vector_fiq - ADDR(.vectors));


vectors_start开始位置为0xffff0000


异常的初步跳转分析
------------------

::

    vector_rst:
     ARM(	swi	SYS_ERROR0	)   //复位异常，这里执行软中断异常
     THUMB(	svc	#0		)
     THUMB(	nop			)
        b	vector_und

    /*
     * Interrupt dispatcher     //irq中断处理
     */
        vector_stub	irq, IRQ_MODE, 4

        .long	__irq_usr			@  0  (USR_26 / USR_32)
        .long	__irq_invalid			@  1  (FIQ_26 / FIQ_32)
        .long	__irq_invalid			@  2  (IRQ_26 / IRQ_32)
        .long	__irq_svc			@  3  (SVC_26 / SVC_32)
        .long	__irq_invalid			@  4
        .long	__irq_invalid			@  5
        .long	__irq_invalid			@  6
        .long	__irq_invalid			@  7
        .long	__irq_invalid			@  8
        .long	__irq_invalid			@  9
        .long	__irq_invalid			@  a
        .long	__irq_invalid			@  b
        .long	__irq_invalid			@  c
        .long	__irq_invalid			@  d
        .long	__irq_invalid			@  e
        .long	__irq_invalid			@  f

    /*
     * Data abort dispatcher
     * Enter in ABT mode, spsr = USR CPSR, lr = USR PC
     */
        //数据异常
        vector_stub	dabt, ABT_MODE, 8

        .long	__dabt_usr			@  0  (USR_26 / USR_32)
        .long	__dabt_invalid			@  1  (FIQ_26 / FIQ_32)
        .long	__dabt_invalid			@  2  (IRQ_26 / IRQ_32)
        .long	__dabt_svc			@  3  (SVC_26 / SVC_32)
        .long	__dabt_invalid			@  4
        .long	__dabt_invalid			@  5
        .long	__dabt_invalid			@  6
        .long	__dabt_invalid			@  7
        .long	__dabt_invalid			@  8
        .long	__dabt_invalid			@  9
        .long	__dabt_invalid			@  a
        .long	__dabt_invalid			@  b
        .long	__dabt_invalid			@  c
        .long	__dabt_invalid			@  d
        .long	__dabt_invalid			@  e
        .long	__dabt_invalid			@  f

    /*
     * Prefetch abort dispatcher
     * Enter in ABT mode, spsr = USR CPSR, lr = USR PC
     */
        //预取指异常
        vector_stub	pabt, ABT_MODE, 4

        .long	__pabt_usr			@  0 (USR_26 / USR_32)
        .long	__pabt_invalid			@  1 (FIQ_26 / FIQ_32)
        .long	__pabt_invalid			@  2 (IRQ_26 / IRQ_32)
        .long	__pabt_svc			@  3 (SVC_26 / SVC_32)
        .long	__pabt_invalid			@  4
        .long	__pabt_invalid			@  5
        .long	__pabt_invalid			@  6
        .long	__pabt_invalid			@  7
        .long	__pabt_invalid			@  8
        .long	__pabt_invalid			@  9
        .long	__pabt_invalid			@  a
        .long	__pabt_invalid			@  b
        .long	__pabt_invalid			@  c
        .long	__pabt_invalid			@  d
        .long	__pabt_invalid			@  e
        .long	__pabt_invalid			@  f

    /*
     * Undef instr entry dispatcher
     * Enter in UND mode, spsr = SVC/USR CPSR, lr = SVC/USR PC
     */
        //未定义异常
        vector_stub	und, UND_MODE

        .long	__und_usr			@  0 (USR_26 / USR_32)
        .long	__und_invalid			@  1 (FIQ_26 / FIQ_32) .long	__und_invalid			@  2 (IRQ_26 / IRQ_32)
        .long	__und_svc			@  3 (SVC_26 / SVC_32)
        .long	__und_invalid			@  4
        .long	__und_invalid			@  5
        .long	__und_invalid			@  6
        .long	__und_invalid			@  7
        .long	__und_invalid			@  8
        .long	__und_invalid			@  9
        .long	__und_invalid			@  a
        .long	__und_invalid			@  b
        .long	__und_invalid			@  c
        .long	__und_invalid			@  d
        .long	__und_invalid			@  e
        .long	__und_invalid			@  f

        .align	5


::

    /*
     * Vector stubs.
     *
     * This code is copied to 0xffff1000 so we can use branches in the
     * vectors, rather than ldr's.  Note that this code must not exceed
     * a page size.
     *
     * Common stub entry macro:
     *   Enter in IRQ mode, spsr = SVC/USR CPSR, lr = SVC/USR PC
     *
     * SP points to a minimal amount of processor-private memory, the address
     * of which is copied into r0 for the mode specific abort handler.
     */
     //这是一个宏定义,上面代码中会用到此宏
        .macro	vector_stub, name, mode, correction=0
        .align	5

    vector_\name:
        .if \correction
        sub	lr, lr, #\correction
        .endif

        @
        @ Save r0, lr_<exception> (parent PC) and spsr_<exception>
        @ (parent CPSR)
        @
        stmia	sp, {r0, lr}		@ save r0, lr
        mrs	lr, spsr
        str	lr, [sp, #8]		@ save spsr

        @
        @ Prepare for SVC32 mode.  IRQs remain disabled.
        @
        mrs	r0, cpsr
        eor	r0, r0, #(\mode ^ SVC_MODE | PSR_ISETSTATE)
        msr	spsr_cxsf, r0

        @
        @ the branch table must immediately follow this code
        @
        and	lr, lr, #0x0f
     THUMB(	adr	r0, 1f			)
     THUMB(	ldr	lr, [r0, lr, lsl #2]	)
        mov	r0, sp
     ARM(	ldr	lr, [pc, lr, lsl #2]	)
        movs	pc, lr			@ branch to handler in SVC mode
    ENDPROC(vector_\name)



**irq中断**

::


    __irq_usr:
        usr_entry
        kuser_cmpxchg_check
        irq_handler
        get_thread_info tsk
        mov	why, #0
        b	ret_to_user_from_irq
     UNWIND(.fnend		)
    ENDPROC(__irq_usr)

user_entry ret_ro_user_from_irq等都在此文件中定义，此处不再列出

::

        .macro	irq_handler
        #ifdef CONFIG_GENERIC_IRQ_MULTI_HANDLER
            ldr	r1, =handle_arch_irq
            mov	r0, sp
            badr	lr, 9997f
            ldr	pc, [r1]
        #else
            arch_irq_handler_default
        #endif
        9997:
        .endm
