kernel 启动概述
================


kernel启动之前的动作
---------------------

kernel镜像加载到ddr的相应位置
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

kernel一般会存在于存储设备上，比如FLASH/EMMC/SDCARD。因此需要先将kernel镜像加载到RAM的位置上，CPU才可以去访问到kernel，具体实现方法由
bootloader决定，可以是自动复制，也可以是根据bootloader cmdline模式下的输入命令来复制


硬件要求
^^^^^^^^^

根据 ``arch/arm64/kernel/head.S`` 的stext(kernel的入口函数)的注释头

::


    /*
     * Kernel startup entry point.
     * ---------------------------
     *
     * The requirements are:
     *   MMU = off, D-cache = off, I-cache = on or off,
     *   x0 = physical address to the FDT blob.
     *
     * This code is mostly position independent so you call this at
     * __pa(PAGE_OFFSET + TEXT_OFFSET).
     *
     * Note that the callee-saved registers are used for storing variables
     * that are useful before the MMU is enabled. The allocations are described
     * in the entry routines.
     */
        __HEAD
    _head:
        /*
         * DO NOT MODIFY. Image header expected by Linux boot-loaders.
         */
    #ifdef CONFIG_EFI
        /*
         * This add instruction has no meaningful effect except that
         * its opcode forms the magic "MZ" signature required by UEFI.
         */
        add	x13, x18, #0x16
        b	stext
    #else
        b	stext				// branch to kernel start, magic
        .long	0				// reserved
        ...

所以有要求如下

- MMU = off

MMU是用来处理物理地址到虚拟内存地址的映射，因此软件上需要先配置其映射表(也就是常说的页表),MMU关闭的情况下，CPU的寻址都是物理地址，也就是不需要经过转化直接访问相应的硬件，
一旦打开之后，CPU的寻址都是虚拟地址，都会经过MMU映射到真正的物理地址上，即使代码中写的是一个物理地址但也会被当做虚拟地址使用

地址映射表是由kernel自己创建的，在创建映射表之前的地址都是物理地址，所以必须保证MMU是关闭状态

- D-cache = off

CACHE是CPU核内存之间的告诉缓冲器，又分成数据缓冲器D-cache和指令缓冲器I-cache，D-cache一定要关闭，否则可能kernel刚启动的过程中，去取数据的时候，从Cache中取，而这个时候RAM中
的数据还没有Cache过来，导致数据存取异常。


跳转到kernel镜像入口的对应位置
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

bootloader需要通过设置PC指针到kernel的入口代码处(也就是kernel的加载位置)来实现kernel的跳转


kernel 启动第一阶段
-------------------

linux内核启动第一阶段，也就是常说的汇编阶段，也就是stext函数的实现内容，这部分主要完成的工作：CPU ID检查，machine ID检查，创建初始化页表，设置C代码运行环境，跳转到内核第一个真正
的C函数 ``start_kernel`` 执行

kernel 入口地址的指定
^^^^^^^^^^^^^^^^^^^^^^

在 ``arch/arm64/kernel/vmlinux.lds.S`` 中

::

    OUTPUT_ARCH(aarch64)
    ENTRY(_text)

    ...

	.head.text : {
		_text = .;
		HEAD_TEXT
	}

所以kernel入口地址是.head.text段的代码首地址

而.head_text段，通过include/linux/init.h中的宏定义__HEAD来表示

::

    /* For assembly routines */
    #define __HEAD		.section	".head.text","ax"
    #define __INIT		.section	".init.text","ax"
    #define __FINIT		.previous

    #define __INITDATA	.section	".init.data","aw",%progbits
    #define __INITRODATA	.section	".init.rodata","a",%progbits
    #define __FINITDATA	.previous

    #define __MEMINIT        .section	".meminit.text", "ax"
    #define __MEMINITDATA    .section	".meminit.data", "aw"
    #define __MEMINITRODATA  .section	".meminit.rodata", "a"


内核启动的入口点，在arch/arm64/kernel/head.S文件中

::

        __HEAD
    _head:
        /*
         * DO NOT MODIFY. Image header expected by Linux boot-loaders.
         */
    #ifdef CONFIG_EFI
        /*
         * This add instruction has no meaningful effect except that
         * its opcode forms the magic "MZ" signature required by UEFI.
         */
        add	x13, x18, #0x16
        b	stext
    #else
        b	stext				// branch to kernel start, magic
        .long	0				// reserved
    #endif
        le64sym	_kernel_offset_le		// Image load offset from start of RAM, little-endian
        le64sym	_kernel_size_le			// Effective size of kernel image, little-endian
        le64sym	_kernel_flags_le		// Informative flags, little-endian
        .quad	0				// reserved
        .quad	0				// reserved
        .quad	0				// reserved
        .ascii	ARM64_IMAGE_MAGIC		// Magic number
    #ifdef CONFIG_EFI
        .long	pe_header - _head		// Offset to the PE header.

    pe_header:
        __EFI_PE_HEADER
    #else
        .long	0				// reserved
    #endif

这段汇编代码中最重要的就是b stext，加载kernel镜像之后第一个运行的函数就是stext


stext函数
""""""""""

启动过程中的汇编阶段，是从arch/arm64/kernel/head.S文件开始，执行的起点是stext函数，入口函数是通过vmlinux.lds链接而成，在head.S中ENTRY(stext)指定

在汇编代码中,宏定义ENTRY和ENDPROC是成对出现的，表示定义一个函数，同时也要指定当前代码所在的段，如 __INIT

::

    #define __INIT  .section    ".init.text","ax"

        __INIT

    ENTRY(stext)
        ....
    ENPROC(stext)

内核启动的必要条件：MMU关闭，D-cache关闭，x0是传递给FDT blob的物理地址


stext函数开始执行


::

    __INIT

    /*
     * The following callee saved general purpose registers are used on the
     * primary lowlevel boot path:
     *
     *  Register   Scope                      Purpose
     *  x21        stext() .. start_kernel()  FDT pointer passed at boot in x0
     *  x23        stext() .. start_kernel()  physical misalignment/KASLR offset
     *  x28        __create_page_tables()     callee preserved temp register
     *  x19/x20    __primary_switch()         callee preserved temp registers
     *  x24        __primary_switch() .. relocate_kernel()
     *                                        current RELR displacement
     */
    ENTRY(stext)
    bl	preserve_boot_args
    bl	el2_setup			// Drop to EL1, w0=cpu_boot_mode
    adrp	x23, __PHYS_OFFSET
    and	x23, x23, MIN_KIMG_ALIGN - 1	// KASLR offset, defaults to 0
    bl	set_cpu_boot_mode_flag
    bl	__create_page_tables
    /*
     * The following calls CPU setup code, see arch/arm64/mm/proc.S for
     * details.
     * On return, the CPU will be ready for the MMU to be turned on and
     * the TCR will have been set.
     */
    bl	__cpu_setup			// initialise processor
    b	__primary_switch
    ENDPROC(stext)


- preserve_boot_args

保存从bootloader传递过来的x0~x3参数

::

    /*
     * Preserve the arguments passed by the bootloader in x0 .. x3
     */
    preserve_boot_args:
        mov	x21, x0				// x21=FDT  //将dtb的地址暂存在x21寄存器，释放出x0使用

        adr_l	x0, boot_args			// record the contents of   //x0保存boot_args变量的地址
        stp	x21, x1, [x0]			// x0 .. x3 at kernel entry     //将x0 x1的值保存在Boot_args[0] boot_args[1]
        stp	x2, x3, [x0, #16]       //将x2 x3的值保存在boot_args[2] boot_args[3]

        dmb	sy				// needed before dc ivac with
                            // MMU off

        mov	x1, #0x20			// 4 x 8 bytes
        b	__inval_dcache_area		// tail call
    ENDPROC(preserve_boot_args)
    

- set_cpu_boot_mode_flag

此函数用来设置__boot_cpu_mode flag,需要一个前提条件，w20寄存器中保存了CPU启动时的异常等级(exception level)

::


    /*
     * Sets the __boot_cpu_mode flag depending on the CPU boot mode passed
     * in w0. See arch/arm64/include/asm/virt.h for more info.
     */
    set_cpu_boot_mode_flag:
        adr_l	x1, __boot_cpu_mode
        cmp	w0, #BOOT_CPU_MODE_EL2
        b.ne	1f
        add	x1, x1, #4
    1:	str	w0, [x1]			// This CPU has booted in EL1
        dmb	sy
        dc	ivac, x1			// Invalidate potentially stale cache line
        ret
    ENDPROC(set_cpu_boot_mode_flag)

由于系统启动之后，需要了解CPU启动时候的exception level，因此需要一个全局变量__boot_cpu_mode来保存启动时的CPUmode

全局变量__boot_cpu_mode定义

::

    /*
     * We need to find out the CPU boot mode long after boot, so we need to
     * store it in a writable variable.
     *
     * This is not in .bss, because we set it sufficiently early that the boot-time
     * zeroing of .bss would clobber it.
     */
    ENTRY(__boot_cpu_mode)
        .long	BOOT_CPU_MODE_EL2
        .long	BOOT_CPU_MODE_EL1


- __create_page_tables

建立页初始化的过程

::

    __create_page_tables:
        mov	x28, lr

        /*
         * Invalidate the init page tables to avoid potential dirty cache lines
         * being evicted. Other page tables are allocated in rodata as part of
         * the kernel image, and thus are clean to the PoC per the boot
         * protocol.
         */
        adrp	x0, init_pg_dir
        adrp	x1, init_pg_end
        sub	x1, x1, x0
        bl	__inval_dcache_area

        /*
         * Clear the init page tables.
         */
        adrp	x0, init_pg_dir
        adrp	x1, init_pg_end
        sub	x1, x1, x0
    1:	stp	xzr, xzr, [x0], #16
        stp	xzr, xzr, [x0], #16
        stp	xzr, xzr, [x0], #16
        stp	xzr, xzr, [x0], #16
        subs	x1, x1, #64
        b.ne	1b

        mov	x7, SWAPPER_MM_MMUFLAGS

        /*
         * Create the identity mapping.
         */
        adrp	x0, idmap_pg_dir
        adrp	x3, __idmap_text_start		// __pa(__idmap_text_start)

    #ifdef CONFIG_ARM64_VA_BITS_52
        mrs_s	x6, SYS_ID_AA64MMFR2_EL1
        and	x6, x6, #(0xf << ID_AA64MMFR2_LVA_SHIFT)
        mov	x5, #52
        cbnz	x6, 1f
    #endif
        mov	x5, #VA_BITS_MIN
    1:
        adr_l	x6, vabits_actual
        str	x5, [x6]
        dmb	sy
        dc	ivac, x6		// Invalidate potentially stale cache line

        /*
         * VA_BITS may be too small to allow for an ID mapping to be created
         * that covers system RAM if that is located sufficiently high in the
         * physical address space. So for the ID map, use an extended virtual
         * range in that case, and configure an additional translation level
         * if needed.
         *
         * Calculate the maximum allowed value for TCR_EL1.T0SZ so that the
         * entire ID map region can be mapped. As T0SZ == (64 - #bits used),
         * this number conveniently equals the number of leading zeroes in
         * the physical address of __idmap_text_end.
         */
        adrp	x5, __idmap_text_end
        clz	x5, x5
        cmp	x5, TCR_T0SZ(VA_BITS)	// default T0SZ small enough?
        b.ge	1f			// .. then skip VA range extension

        adr_l	x6, idmap_t0sz
        str	x5, [x6]
        dmb	sy
        dc	ivac, x6		// Invalidate potentially stale cache line

    #if (VA_BITS < 48)
    #define EXTRA_SHIFT	(PGDIR_SHIFT + PAGE_SHIFT - 3)
    #define EXTRA_PTRS	(1 << (PHYS_MASK_SHIFT - EXTRA_SHIFT))

        /*
         * If VA_BITS < 48, we have to configure an additional table level.
         * First, we have to verify our assumption that the current value of
         * VA_BITS was chosen such that all translation levels are fully
         * utilised, and that lowering T0SZ will always result in an additional
         * translation level to be configured.
         */
    #if VA_BITS != EXTRA_SHIFT
    #error "Mismatch between VA_BITS and page size/number of translation levels"
    #endif

        mov	x4, EXTRA_PTRS
        create_table_entry x0, x3, EXTRA_SHIFT, x4, x5, x6
    #else
        /*
         * If VA_BITS == 48, we don't have to configure an additional
         * translation level, but the top-level table has more entries.
         */
        mov	x4, #1 << (PHYS_MASK_SHIFT - PGDIR_SHIFT)
        str_l	x4, idmap_ptrs_per_pgd, x5
    #endif
    1:
        ldr_l	x4, idmap_ptrs_per_pgd
        mov	x5, x3				// __pa(__idmap_text_start)
        adr_l	x6, __idmap_text_end		// __pa(__idmap_text_end)

        map_memory x0, x1, x3, x6, x7, x3, x4, x10, x11, x12, x13, x14

        /*
         * Map the kernel image (starting with PHYS_OFFSET).
         */
        adrp	x0, init_pg_dir
        mov_q	x5, KIMAGE_VADDR + TEXT_OFFSET	// compile time __va(_text)
        add	x5, x5, x23			// add KASLR displacement
        mov	x4, PTRS_PER_PGD
        adrp	x6, _end			// runtime __pa(_end)
        adrp	x3, _text			// runtime __pa(_text)
        sub	x6, x6, x3			// _end - _text
        add	x6, x6, x5			// runtime __va(_end)

        map_memory x0, x1, x5, x6, x7, x3, x4, x10, x11, x12, x13, x14

        /*
         * Since the page tables have been populated with non-cacheable
         * accesses (MMU disabled), invalidate the idmap and swapper page
         * tables again to remove any speculatively loaded cache lines.
         */
        adrp	x0, idmap_pg_dir
        adrp	x1, init_pg_end
        sub	x1, x1, x0
        dmb	sy
        bl	__inval_dcache_area

        ret	x28
    ENDPROC(__create_page_tables)


- __cpu_setup

cpu的初始化设置

::

    /* *	__cpu_setup
     *
     *	Initialise the processor for turning the MMU on.  Return in x0 the
     *	value of the SCTLR_EL1 register.
     */
        .pushsection ".idmap.text", "awx"
    ENTRY(__cpu_setup)
        tlbi	vmalle1				// Invalidate local TLB
        dsb	nsh

        mov	x0, #3 << 20
        msr	cpacr_el1, x0			// Enable FP/ASIMD
        mov	x0, #1 << 12			// Reset mdscr_el1 and disable
        msr	mdscr_el1, x0			// access to the DCC from EL0
        isb					// Unmask debug exceptions now,
        enable_dbg				// since this is per-cpu
        reset_pmuserenr_el0 x0			// Disable PMU access from EL0
        /*
         * Memory region attributes for LPAE:
         *
         *   n = AttrIndx[2:0]
         *			n	MAIR
         *   DEVICE_nGnRnE	000	00000000
         *   DEVICE_nGnRE	001	00000100
         *   DEVICE_GRE		010	00001100
         *   NORMAL_NC		011	01000100
         *   NORMAL		100	11111111
         *   NORMAL_WT		101	10111011
         */
        ldr	x5, =MAIR(0x00, MT_DEVICE_nGnRnE) | \
                 MAIR(0x04, MT_DEVICE_nGnRE) | \
                 MAIR(0x0c, MT_DEVICE_GRE) | \
                 MAIR(0x44, MT_NORMAL_NC) | \
                 MAIR(0xff, MT_NORMAL) | \
                 MAIR(0xbb, MT_NORMAL_WT)
        msr	mair_el1, x5
        /*
         * Prepare SCTLR
         */
        mov_q	x0, SCTLR_EL1_SET
        /*
         * Set/prepare TCR and TTBR. We use 512GB (39-bit) address range for
         * both user and kernel.
         */
        ldr	x10, =TCR_TxSZ(VA_BITS) | TCR_CACHE_FLAGS | TCR_SMP_FLAGS | \
                TCR_TG_FLAGS | TCR_KASLR_FLAGS | TCR_ASID16 | \
                TCR_TBI0 | TCR_A1 | TCR_KASAN_FLAGS
        tcr_clear_errata_bits x10, x9, x5

    #ifdef CONFIG_ARM64_VA_BITS_52
        ldr_l		x9, vabits_actual
        sub		x9, xzr, x9
        add		x9, x9, #64
        tcr_set_t1sz	x10, x9
    #else
        ldr_l		x9, idmap_t0sz
    #endif
        tcr_set_t0sz	x10, x9

        /*
         * Set the IPS bits in TCR_EL1.
         */
        tcr_compute_pa_size x10, #TCR_IPS_SHIFT, x5, x6
    #ifdef CONFIG_ARM64_HW_AFDBM
        /*
         * Enable hardware update of the Access Flags bit.
         * Hardware dirty bit management is enabled later,
         * via capabilities.
         */
        mrs	x9, ID_AA64MMFR1_EL1
        and	x9, x9, #0xf
        cbz	x9, 1f
        orr	x10, x10, #TCR_HA		// hardware Access flag update
    1:
    #endif	/* CONFIG_ARM64_HW_AFDBM */
        msr	tcr_el1, x10
        ret					// return to head.S
    ENDPROC(__cpu_setup)


主要包括：

1) cache和TLB的处理
2) memory attribute lookup table的创建
3) SCTLR_EL1 TCR_EL1的设定

- __primary_switch

主要工作是为打开MMU做准备

::

    __primary_switch:
    #ifdef CONFIG_RANDOMIZE_BASE
        mov	x19, x0				// preserve new SCTLR_EL1 value
        mrs	x20, sctlr_el1			// preserve old SCTLR_EL1 value
    #endif

        adrp	x1, init_pg_dir
        bl	__enable_mmu        //打开MMU
    #ifdef CONFIG_RELOCATABLE
    #ifdef CONFIG_RELR
        mov	x24, #0				// no RELR displacement yet
    #endif
        bl	__relocate_kernel
    #ifdef CONFIG_RANDOMIZE_BASE
        ldr	x8, =__primary_switched
        adrp	x0, __PHYS_OFFSET
        blr	x8

        /*
         * If we return here, we have a KASLR displacement in x23 which we need
         * to take into account by discarding the current kernel mapping and
         * creating a new one.
         */
        pre_disable_mmu_workaround
        msr	sctlr_el1, x20			// disable the MMU
        isb
        bl	__create_page_tables		// recreate kernel mapping

        tlbi	vmalle1				// Remove any stale TLB entries
        dsb	nsh

        msr	sctlr_el1, x19			// re-enable the MMU
        isb
        ic	iallu				// flush instructions fetched
        dsb	nsh				// via old mapping
        isb

        bl	__relocate_kernel
    #endif
    #endif
        ldr	x8, =__primary_switched
        adrp	x0, __PHYS_OFFSET
        br	x8
    ENDPROC(__primary_switch)

函数中通过__enable_mmu函数来开启MMU, 并调用__primary_switched函数

::

    /*
     * The following fragment of code is executed with the MMU enabled.
     *
     *   x0 = __PHYS_OFFSET
     */
    __primary_switched:
        adrp	x4, init_thread_union
        add	sp, x4, #THREAD_SIZE
        adr_l	x5, init_task
        msr	sp_el0, x5			// Save thread_info

        adr_l	x8, vectors			// load VBAR_EL1 with virtual
        msr	vbar_el1, x8			// vector table address
        isb

        stp	xzr, x30, [sp, #-16]!
        mov	x29, sp

        str_l	x21, __fdt_pointer, x5		// Save FDT pointer

        ldr_l	x4, kimage_vaddr		// Save the offset between
        sub	x4, x4, x0			// the kernel virtual and
        str_l	x4, kimage_voffset, x5		// physical mappings

        // Clear BSS
        adr_l	x0, __bss_start
        mov	x1, xzr
        adr_l	x2, __bss_stop
        sub	x2, x2, x0
        bl	__pi_memset
        dsb	ishst				// Make zero page visible to PTW

    #ifdef CONFIG_KASAN
        bl	kasan_early_init
    #endif
    #ifdef CONFIG_RANDOMIZE_BASE
        tst	x23, ~(MIN_KIMG_ALIGN - 1)	// already running randomized?
        b.ne	0f
        mov	x0, x21				// pass FDT address in x0
        bl	kaslr_early_init		// parse FDT for KASLR options
        cbz	x0, 0f				// KASLR disabled? just proceed
        orr	x23, x23, x0			// record KASLR offset
        ldp	x29, x30, [sp], #16		// we must enable KASLR, return
        ret					// to __primary_switch()
    0:
    #endif
        add	sp, sp, #16
        mov	x29, #0
        mov	x30, #0
        b	start_kernel
    ENDPROC(__primary_switched)

此函数中进行一些C环境的准备，并在最后执行start_kernel函数，内核的启动进入到C语言环境阶段


kernel 启动第二阶段
--------------------

linux内核启动的第二阶段也就是常说的C语言阶段，从 ``start_kernel`` 函数开始。 start_kernel函数是所有linux平台进入系统内核初始化后的入口函数，主要完成剩余的与硬件平台相关的初始化
工作，这些初始化操作有的是公共的，有的需要配置才会执行，内核工作需要的模块的初始化一次被调用：如内存管理、调度系统、异常处理等


start_kenel 
^^^^^^^^^^^^

start_kernel函数在init/main.c文件中，主要完成linux子系统的初始化工作，此部分初始化内容繁多，暂时略过...

::


    asmlinkage __visible void __init start_kernel(void)
    {
        char *command_line;
        char *after_dashes;

        set_task_stack_end_magic(&init_task);
        smp_setup_processor_id();
        debug_objects_early_init();

        cgroup_init_early();

        local_irq_disable();
        early_boot_irqs_disabled = true;

        /*
         * Interrupts are still disabled. Do necessary setups, then
         * enable them.
         */
        boot_cpu_init();
        page_address_init();
        pr_notice("%s", linux_banner);
        early_security_init();
        setup_arch(&command_line);
        setup_command_line(command_line);
        setup_nr_cpu_ids();
        setup_per_cpu_areas();
        smp_prepare_boot_cpu();	/* arch-specific boot-cpu hooks */
        boot_cpu_hotplug_init();

        build_all_zonelists(NULL);
        page_alloc_init();

        pr_notice("Kernel command line: %s\n", boot_command_line);
        /* parameters may set static keys */
        jump_label_init();
        parse_early_param();
        after_dashes = parse_args("Booting kernel",
                      static_command_line, __start___param,
                      __stop___param - __start___param,
                      -1, -1, NULL, &unknown_bootoption);
        if (!IS_ERR_OR_NULL(after_dashes))
            parse_args("Setting init args", after_dashes, NULL, 0, -1, -1,
                   NULL, set_init_arg);

        /*
         * These use large bootmem allocations and must precede
         * kmem_cache_init()
         */
        setup_log_buf(0);
        vfs_caches_init_early();
        sort_main_extable();
        trap_init();
        mm_init();

        ftrace_init();

        /* trace_printk can be enabled here */
        early_trace_init();

        /*
         * Set up the scheduler prior starting any interrupts (such as the
         * timer interrupt). Full topology setup happens at smp_init()
         * time - but meanwhile we still have a functioning scheduler.
         */
        sched_init();
        /*
         * Disable preemption - early bootup scheduling is extremely
         * fragile until we cpu_idle() for the first time.
         */
        preempt_disable();
        if (WARN(!irqs_disabled(),
             "Interrupts were enabled *very* early, fixing it\n"))
            local_irq_disable();
        radix_tree_init();

        /*
         * Set up housekeeping before setting up workqueues to allow the unbound
         * workqueue to take non-housekeeping into account.
         */
        housekeeping_init();

        /*
         * Allow workqueue creation and work item queueing/cancelling
         * early.  Work item execution depends on kthreads and starts after
         * workqueue_init().
         */
        workqueue_init_early();

        rcu_init();

        /* Trace events are available after this */
        trace_init();

        if (initcall_debug)
            initcall_debug_enable();

        context_tracking_init();
        /* init some links before init_ISA_irqs() */
        early_irq_init();
        init_IRQ();
        tick_init();
        rcu_init_nohz();
        init_timers();
        hrtimers_init();
        softirq_init();
        timekeeping_init();

        /*
         * For best initial stack canary entropy, prepare it after:
         * - setup_arch() for any UEFI RNG entropy and boot cmdline access
         * - timekeeping_init() for ktime entropy used in rand_initialize()
         * - rand_initialize() to get any arch-specific entropy like RDRAND
         * - add_latent_entropy() to get any latent entropy
         * - adding command line entropy
         */
        rand_initialize();
        add_latent_entropy();
        add_device_randomness(command_line, strlen(command_line));
        boot_init_stack_canary();

        time_init();
        perf_event_init();
        profile_init();
        call_function_init();
        WARN(!irqs_disabled(), "Interrupts were enabled early\n");

        early_boot_irqs_disabled = false;
        local_irq_enable();

        kmem_cache_init_late();

        /*
         * HACK ALERT! This is early. We're enabling the console before
         * we've done PCI setups etc, and console_init() must be aware of
         * this. But we do want output early, in case something goes wrong.
         */
        console_init();
        if (panic_later)
            panic("Too many boot %s vars at `%s'", panic_later,
                  panic_param);

        lockdep_init();

        /*
         * Need to run this when irqs are enabled, because it wants
         * to self-test [hard/soft]-irqs on/off lock inversion bugs
         * too:
         */
        locking_selftest();

        /*
         * This needs to be called before any devices perform DMA
         * operations that might use the SWIOTLB bounce buffers. It will
         * mark the bounce buffers as decrypted so that their usage will
         * not cause "plain-text" data to be decrypted when accessed.
         */
        mem_encrypt_init();

    #ifdef CONFIG_BLK_DEV_INITRD
        if (initrd_start && !initrd_below_start_ok &&
            page_to_pfn(virt_to_page((void *)initrd_start)) < min_low_pfn) {
            pr_crit("initrd overwritten (0x%08lx < 0x%08lx) - disabling it.\n",
                page_to_pfn(virt_to_page((void *)initrd_start)),
                min_low_pfn);
            initrd_start = 0;
        }
    #endif
        setup_per_cpu_pageset();
        numa_policy_init();
        acpi_early_init();
        if (late_time_init)
            late_time_init();
        sched_clock_init();
        calibrate_delay();
        pid_idr_init();
        anon_vma_init();
    #ifdef CONFIG_X86
        if (efi_enabled(EFI_RUNTIME_SERVICES))
            efi_enter_virtual_mode();
    #endif
        thread_stack_cache_init();
        cred_init();
        fork_init();
        proc_caches_init();
        uts_ns_init();
        buffer_init();
        key_init();
        security_init();
        dbg_late_init();
        vfs_caches_init();
        pagecache_init();
        signals_init();
        seq_file_init();
        proc_root_init();
        nsfs_init();
        cpuset_init();
        cgroup_init();
        taskstats_init_early();
        delayacct_init();

        poking_init();
        check_bugs();

        acpi_subsystem_init();
        arch_post_acpi_subsys_init();
        sfi_init_late();

        /* Do the rest non-__init'ed, we're now alive */
        arch_call_rest_init();
    }

::

    pr_notice("%s", linux_barner);

::

    /* FIXED STRINGS! Don't touch! */
    const char linux_banner[] =
            "Linux version " UTS_RELEASE " (" LINUX_COMPILE_BY "@"
            LINUX_COMPILE_HOST ") (" LINUX_COMPILER ") " UTS_VERSION "\n";
            ")"


执行的效果是，在内核启动的初期，打印内核版本号和构建信息

::

    [    0.000000 ] Linux version 4.14.74 (jenkins@MonoCI) (gcc version 6.5.0 (Linaro GCC 6.5-2018.12)) #2 SMP PREEMPT Mon Aug 23 12:17:44 CST 2021


setup_arch
^^^^^^^^^^^

setup_arch是体系结构相关的，该函数根据处理器、硬件平台具体型号设置系统，及解析系统命令行，系统内存管理初始化，统计并注册系统各种资源等，每个体系都有自己的setup_arch函数，
是由顶层Makefile中的arch变量定义的，参数是违背初始化的内部变量command_line

::

    void __init setup_arch(char **cmdline_p)
    {
        init_mm.start_code = (unsigned long) _text;
        init_mm.end_code   = (unsigned long) _etext;
        init_mm.end_data   = (unsigned long) _edata;
        init_mm.brk	   = (unsigned long) _end;

        *cmdline_p = boot_command_line;

        early_fixmap_init();
        early_ioremap_init();

        setup_machine_fdt(__fdt_pointer);

        /*
         * Initialise the static keys early as they may be enabled by the
         * cpufeature code and early parameters.
         */
        jump_label_init();
        parse_early_param();

        /*
         * Unmask asynchronous aborts and fiq after bringing up possible
         * earlycon. (Report possible System Errors once we can report this
         * occurred).
         */
        local_daif_restore(DAIF_PROCCTX_NOIRQ);

        /*
         * TTBR0 is only used for the identity mapping at this stage. Make it
         * point to zero page to avoid speculatively fetching new entries.
         */
        cpu_uninstall_idmap();

        xen_early_init();
        efi_init();
        arm64_memblock_init();

        paging_init();

        acpi_table_upgrade();

        /* Parse the ACPI tables for possible boot-time configuration */
        acpi_boot_table_init();

        if (acpi_disabled)
            unflatten_device_tree();

        bootmem_init();

        kasan_init();

        request_standard_resources();

        early_ioremap_reset();

        if (acpi_disabled)
            psci_dt_init();
        else
            psci_acpi_init();

        cpu_read_bootcpu_ops();
        smp_init_cpus();
        smp_build_mpidr_hash();

        /* Init percpu seeds for random tags after cpus are set up. */
        kasan_init_tags();

    #ifdef CONFIG_ARM64_SW_TTBR0_PAN
        /*
         * Make sure init_thread_info.ttbr0 always generates translation
         * faults in case uaccess_enable() is inadvertently called by the init
         * thread.
         */
        init_task.thread_info.ttbr0 = __pa_symbol(empty_zero_page);
    #endif

    #ifdef CONFIG_VT
        conswitchp = &dummy_con;
    #endif
        if (boot_args[1] || boot_args[2] || boot_args[3]) {
            pr_err("WARNING: x1-x3 nonzero in violation of boot protocol:\n"
                "\tx1: %016llx\n\tx2: %016llx\n\tx3: %016llx\n"
                "This indicates a broken bootloader or old kernel\n",
                boot_args[1], boot_args[2], boot_args[3]);
        }
    }


- setup_machine_fdt

setup_machine_fdt函数的输入参数是设备树(dtb)首地址，u-boot启动程序把设备树读取到内存中，之后在启动内核的同时，将设备树首地址传给内核，setup_machine_fdt函数的参数__fdt_pointer
就是u-boot传给内核的设备树地址，函数中的fdt表示设备树在内存中是一块连续地址存储的

::


    static void __init setup_machine_fdt(phys_addr_t dt_phys)
    {
        int size;
        void *dt_virt = fixmap_remap_fdt(dt_phys, &size, PAGE_KERNEL);  //此时已开启MMU，需要将dtb物理地址转换为虚拟地址
        const char *name;

        if (dt_virt)
            memblock_reserve(dt_phys, size);

        if (!dt_virt || !early_init_dt_scan(dt_virt)) {     //fdt扫描函数,经过此函数之后内核便可以通过调用fdt接口函数获取相关信息
            pr_crit("\n"
                "Error: invalid device tree blob at physical address %pa (virtual address 0x%p)\n"
                "The dtb must be 8-byte aligned and must not exceed 2 MB in size\n"
                "\nPlease check your bootloader.",
                &dt_phys, dt_virt);

            while (true)
                cpu_relax();
        }

        /* Early fixups are done, map the FDT as read-only now */
        fixmap_remap_fdt(dt_phys, &size, PAGE_KERNEL_RO);

        name = of_flat_dt_get_machine_name();
        if (!name)
            return;

        pr_info("Machine model: %s\n", name);
        dump_stack_set_arch_desc("%s (DT)", name);
    }

- console_init

console_init函数执行控制台的初始化工作，在console_init函数执行之前的printk打印信息，需要在console_init函数执行之后才能打印出来，在此之前printk的打印信息都被保存在一个缓存中

::

    kernel/printk/printk.c

    /*
     * Initialize the console device. This is called *early*, so
     * we can't necessarily depend on lots of kernel help here.
     * Just do some early initializations, and do the complex setup
     * later.
     */
    void __init console_init(void)
    {
        int ret;
        initcall_t call;
        initcall_entry_t *ce;

        /* Setup the default TTY line discipline. */
        n_tty_init();

        /*
         * set up the console device so that later boot sequences can
         * inform about problems etc..
         */
        ce = __con_initcall_start;
        trace_initcall_level("console");
        while (ce < __con_initcall_end) {
            call = initcall_from_entry(ce);
            trace_initcall_start(call);
            ret = call();
            trace_initcall_finish(call, ret);
            ce++;
        }
    }

此函数中会执行，__con_initcall_start和__con_initcall_end这两个地址之间的内容，这两个地址可以在vmlinux.lds中找到

::

    __con_initcall_start = .; 
    KEEP(*(.con_initcall.init)) 
    __con_initcall_end = .;

这两个地址之间，存放的是.con_initcall.init段的内容

::

    include/linux/init.h

    #define console_initcall(fn)    \
        static initcall_t __initcall_##fn##id __used  \
        __attribute__((__section_.con_initcall.init)) = fn

通过宏定义console_initcall(fn)将函数指针fn存放到.con_initcall.init段，之后在调用console_init()函数时，就会遍历__con_initcall_start和__con_initcall_end的
地址区域，依次运行存放在启动的函数fn


rest_init
^^^^^^^^^

在一系列的初始化之后，在rest_init函数中启动了三个进程 ``idle`` 、 ``kernel_init`` 、 ``kthreadd`` 来开始操作系统的正式运行

::


    noinline void __ref rest_init(void)
    {
        struct task_struct *tsk;
        int pid;

        rcu_scheduler_starting();
        /*
         * We need to spawn init first so that it obtains pid 1, however
         * the init task will end up wanting to create kthreads, which, if
         * we schedule it before we create kthreadd, will OOPS.
         */
        pid = kernel_thread(kernel_init, NULL, CLONE_FS);   //创建kernel_init内核线程，即init, 1号进程
        /*
         * Pin init on the boot CPU. Task migration is not properly working
         * until sched_init_smp() has been run. It will set the allowed
         * CPUs for init to the non isolated CPUs.
         */
        rcu_read_lock();
        tsk = find_task_by_pid_ns(pid, &init_pid_ns);
        set_cpus_allowed_ptr(tsk, cpumask_of(smp_processor_id()));
        rcu_read_unlock();

        numa_default_policy();
        pid = kernel_thread(kthreadd, NULL, CLONE_FS | CLONE_FILES);    //创建kthreadd内核线程，2号进程，用于管理和调度其他内核线程
        rcu_read_lock();
        kthreadd_task = find_task_by_pid_ns(pid, &init_pid_ns);
        rcu_read_unlock();

        /*
         * Enable might_sleep() and smp_processor_id() checks.
         * They cannot be enabled earlier because with CONFIG_PREEMPTION=y
         * kernel_thread() would trigger might_sleep() splats. With
         * CONFIG_PREEMPT_VOLUNTARY=y the init task might have scheduled
         * already, but it's stuck on the kthreadd_done completion.
         */
        system_state = SYSTEM_SCHEDULING;

        complete(&kthreadd_done);

        /*
         * The boot idle thread must execute schedule()
         * at least once to get things moving:
         */
        schedule_preempt_disabled();    //调用进程调度，并禁止内核抢占
        /* Call into cpu_idle with preempt disabled */
        cpu_startup_entry(CPUHP_ONLINE);    //0号进程完成kernel初始化工作，进入idle循环
    }

1) idle进程是操作系统的空闲进程，CPU空闲的时候会去运行它
2) kernel_init进程最开始只是一个函数，作为进程被启动，init进程是永远存在的,PID是1
3) kthreadd是内核守护进程，始终运行在内核空间，负责所有内核线程的调度和管理，PID是2

也就是说，系统启动后的第一个进程是IDLE，idle进程是唯一没有通过kernel_thread或fork产生的进程，idle创建了kernel_init进程作为1号进程，创建了kthreadd进程作为2号进程

kernel_init
^^^^^^^^^^^^

kernel_init函数在创建kernel_init进程时，作为进程被启动,虽然kernel_init最开始只是一个函数，但是在最后，通过系统调用将读取根文件系统下的init进程，完成从内核态到用户态的转变，
转变为用户态的1号进程，这个init进程是所有用户态进程的父进程，产生了大量的子进程，init进程是1号进程，是永远存在的

kernel_init_freeable
""""""""""""""""""""""

此函数主要工作如下

1) 等待内核线程kthreadd创建完成
2) 注册内核驱动模块 do_basic_setup
3) 启动默认控制台/dev/console

::


    static noinline void __init kernel_init_freeable(void)
    {
        /*
         * Wait until kthreadd is all set-up.
         */
        wait_for_completion(&kthreadd_done);
        //虽然kernel_init进程先创建，但是要在kthreadd线程创建完成才能执行

        /* Now the scheduler is fully set up and can do blocking allocations */
        gfp_allowed_mask = __GFP_BITS_MASK;

        /*
         * init can allocate pages on any node
         */
        set_mems_allowed(node_states[N_MEMORY]);

        cad_pid = task_pid(current);

        smp_prepare_cpus(setup_max_cpus);

        workqueue_init();

        init_mm_internals();

        do_pre_smp_initcalls();
        lockup_detector_init();

        smp_init();
        sched_init_smp();

        page_alloc_init_late();
        /* Initialize page ext after all struct pages are initialized. */
        page_ext_init();

        do_basic_setup();

        /* Open the /dev/console on the rootfs, this should never fail */
        if (ksys_open((const char __user *) "/dev/console", O_RDWR, 0) < 0)
            pr_err("Warning: unable to open an initial console.\n");

        (void) ksys_dup(0);
        (void) ksys_dup(0);
        /*
         * check if there is an early userspace init.  If yes, let it do all
         * the work
         */

        if (!ramdisk_execute_command)
            ramdisk_execute_command = "/init";

        if (ksys_access((const char __user *)
                ramdisk_execute_command, 0) != 0) {
            ramdisk_execute_command = NULL;
            prepare_namespace();
        }

        /*
         * Ok, we have completed the initial bootup, and
         * we're essentially up and running. Get rid of the
         * initmem segments and start the user-mode stuff..
         *
         * rootfs is available now, try loading the public keys
         * and default modules
         */

        integrity_load_keys();
    }

- bo_basic_setup

::

    /*
     * Ok, the machine is now initialized. None of the devices
     * have been touched yet, but the CPU subsystem is up and
     * running, and memory and process management works.
     *
     * Now we can finally start doing some real work..
     */
    static void __init do_basic_setup(void)
    {
        cpuset_init_smp();
        driver_init();
        init_irq_proc();
        do_ctors();
        usermodehelper_enable();
        do_initcalls();
    }

driver_init函数完成了与驱动程序相关的所有子系统的创建，实现了linux设备驱动的一个整体框架，但是它只是建立了目录结构，是设备驱动程序初始化的一部分
具体驱动模块的装载在do_initcalls函数中实现

::

    /**
     * driver_init - initialize driver model.
     *
     * Call the driver model init functions to initialize their
     * subsystems. Called early from init/main.c.
     */
    void __init driver_init(void)
    {
        /* These are the core pieces */
        devtmpfs_init();    //注册devtmpfs文件系统，启动devtmpfsd进程
        devices_init();     //初始化驱动模型中部分子系统，/dev/devices，/dev/cha，/dev/block
        buses_init();       //初始化驱动模型中的bus子系统
        classes_init();     //初始化驱动模型中的class子系统
        firmware_init();    //初始化驱动模型中的firmware子系统
        hypervisor_init();  //初始化驱动模型中的hypervisor子系统

        /* These are also core pieces, but must come after the
         * core core pieces.
         */
        of_core_init();     //初始化设备树访问过程
        platform_bus_init();    //初始化设备驱动模型中的bus/platform子系统，此节点是所有platform设备和驱动的总线模型
                                //所有的platform设备和驱动都会挂载到这个总线上
        cpu_dev_init();     //初始化驱动模型中的device/system/cpu子系统，该节点包含CPU相关属性
        memory_dev_init();  //初始化驱动模型中的device/system/memory子系统，该节点包含了内存相关属性
        container_dev_init();   //初始化系统总线类型为容器
    }


- do_initcalls

编译器在编译内核时，将一系列模块初始化函数的其实地址按照一定的顺序放在指定的section中，在内核启动的初始化阶段，do_initcalls函数中以函数指针的形式取出这些函数的起始地址
依次运行，以完成相应模块的初始化工作，这是设备驱动程序初始化的第二部分，由于内核模块可能存在依赖关系，因此这些模块的初始化顺序非常重要

::

    // init/main.c

    static void __init do_initcalls(void)
    {
        int level;

        for (level = 0; level < ARRAY_SIZE(initcall_levels) - 1; level++)
            do_initcall_level(level);
    }

对同一个level等级下的函数，依次遍历执行

::

    static void __init do_initcall_level(int level)
    {
        initcall_entry_t *fn;

        strcpy(initcall_command_line, saved_command_line);
        parse_args(initcall_level_names[level],
               initcall_command_line, __start___param,
               __stop___param - __start___param,
               level, level,
               NULL, &repair_env_string);

        trace_initcall_level(initcall_level_names[level]);
        for (fn = initcall_levels[level]; fn < initcall_levels[level+1]; fn++)
            do_one_initcall(initcall_from_entry(fn));
    }

执行某一个确定的函数

::

    int __init_or_module do_one_initcall(initcall_t fn)
    {
        int count = preempt_count();
        char msgbuf[64];
        int ret;

        if (initcall_blacklisted(fn))
            return -EPERM;

        do_trace_initcall_start(fn);
        ret = fn();
        do_trace_initcall_finish(fn, ret);

        msgbuf[0] = 0;

        if (preempt_count() != count) {
            sprintf(msgbuf, "preemption imbalance ");
            preempt_count_set(count);
        }
        if (irqs_disabled()) {
            strlcat(msgbuf, "disabled interrupts ", sizeof(msgbuf));
            local_irq_enable();
        }
        WARN(msgbuf[0], "initcall %pS returned with %s\n", fn, msgbuf);

        add_latent_entropy();
        return ret;
    }


::

    // include/linux/init.h

    #define __define_initcall(fn, id)   \
        static initcall_t __initcall##fn_id __used \
        __attribute__((__section__(".initcall" #id ".init"))) = fn;

__attribute__((__section__())) 表示把对象放在这个由括号中的名称所指代的section中


__define_initcall()宏的含义是

1) 声明一个名为__initcall_##fn的函数指针(其中##表示将两边的变量链接为有一个变量)
2) 将这个函数指针初始化为fn
3) 编译时，要将这个函数指针放到名为".initcall"#id".init"的section中

__define_initcall宏并不会被直接使用，而是被定义为其他的宏定义形式使用

::

    // include/linux/init.h


    #define pure_initcall(fn)		__define_initcall(fn, 0)

    #define core_initcall(fn)		__define_initcall(fn, 1)
    #define core_initcall_sync(fn)		__define_initcall(fn, 1s)
    #define postcore_initcall(fn)		__define_initcall(fn, 2)
    #define postcore_initcall_sync(fn)	__define_initcall(fn, 2s)
    #define arch_initcall(fn)		__define_initcall(fn, 3)
    #define arch_initcall_sync(fn)		__define_initcall(fn, 3s)
    #define subsys_initcall(fn)		__define_initcall(fn, 4)
    #define subsys_initcall_sync(fn)	__define_initcall(fn, 4s)
    #define fs_initcall(fn)			__define_initcall(fn, 5)
    #define fs_initcall_sync(fn)		__define_initcall(fn, 5s)
    #define rootfs_initcall(fn)		__define_initcall(fn, rootfs)
    #define device_initcall(fn)		__define_initcall(fn, 6)
    #define device_initcall_sync(fn)	__define_initcall(fn, 6s)
    #define late_initcall(fn)		__define_initcall(fn, 7)
    #define late_initcall_sync(fn)		__define_initcall(fn, 7s)


在编译生成的vmlinux.lds文件中可以找到initcall相关的定义

::


  __initcall_start = .; 
  KEEP(*(.initcallearly.init))
  __initcall0_start = .; 
  KEEP(*(.initcall0.init)) 
  KEEP(*(.initcall0s.init)) 
  __initcall1_start = .; 
  KEEP(*(.initcall1.init)) 
  KEEP(*(.initcall1s.init)) 
  __initcall2_start = .; 
  KEEP(*(.initcall2.init)) 
  KEEP(*(.initcall2s.init)) 
  __initcall3_start = .; 
  KEEP(*(.initcall3.init)) 
  KEEP(*(.initcall3s.init)) 
  __initcall4_start = .; 
  KEEP(*(.initcall4.init)) 
  KEEP(*(.initcall4s.init)) 
  __initcall5_start = .; 
  KEEP(*(.initcall5.init)) 
  KEEP(*(.initcall5s.init)) 
  __initcallrootfs_start = .; 
  KEEP(*(.initcallrootfs.init)) 
  KEEP(*(.initcallrootfss.init)) 
  __initcall6_start = .; 
  KEEP(*(.initcall6.init)) 
  KEEP(*(.initcall6s.init)) 
  __initcall7_start = .; 
  KEEP(*(.initcall7.init)) 
  KEEP(*(.initcall7s.init)) 
  __initcall_end = .;

这些section中总的开始位置被标识为__initcall_start，而在结尾被标识为__initcall_end

free_initmem
""""""""""""""

free_initmem函数用来释放所有init段中的内存

::

    // arch/arm64/mm/init.c

    void free_initmem(void)
    {
        free_reserved_area(lm_alias(__init_begin),
                   lm_alias(__init_end),
                   0, "unused kernel");
        /*
         * Unmap the __init region but leave the VM area in place. This
         * prevents the region from being reused for kernel modules, which
         * is not supported by kallsyms.
         */
        unmap_kernel_range((u64)__init_begin, (u64)(__init_end - __init_begin));
    }


启动用户态init进程
""""""""""""""""""""

::

	if (!try_to_run_init_process("/sbin/init") ||
	    !try_to_run_init_process("/etc/init") ||
	    !try_to_run_init_process("/bin/init") ||
	    !try_to_run_init_process("/bin/sh"))
		return 0;


::

    static int try_to_run_init_process(const char *init_filename)
    {
        int ret;

        ret = run_init_process(init_filename);

        if (ret && ret != -ENOENT) {
            pr_err("Starting init: %s exists but couldn't execute it (error %d)\n",
                   init_filename, ret);
        }

        return ret;
    }

::

    static int run_init_process(const char *init_filename)
    {
        argv_init[0] = init_filename;
        pr_info("Run %s as init process\n", init_filename);
        return do_execve(getname_kernel(init_filename),
            (const char __user *const __user *)argv_init,
            (const char __user *const __user *)envp_init);
    }

在大多数系统中，bootloader会传递参数给内核的main函数，这些参数中会包含init=/linuxrc参数，于是在kernel_init进程中，如果有execute_command = "linuxrc"，在经过
run_init_process函数的解析之后，得到需要运行的linuxrc，通过do_execve函数进入用户态，开始文件系统的初始化init进程

如果没有传递，则系统开始顺序执行/sbin/init /etc/init /bin/init /bin/sh 程序


init进程进行的工作

1) 为init设置信号处理过程
2) 初始化控制台
3) 解析/etc/inittab文件
4) 执行系统初始化命令，一般情况下会使用/etc/init.d/rcS
5) 执行所有导致init暂停的inittab命令(动作类型: wait)
6) 执行所有仅执行一次的inittab命令 (动作类型: once)

执行完以上工作后，init进程会循环执行以下进程

1) 执行所有终止时必须重新启动的inittab命令(动作类型: respawn)
2) 执行所有终止时必须重新启动但启动前必须询问用户的inittab命令(动作类型: askfirst)

- inittab

init程序会解析/etc/inittab初始化配置文件

::

    # /etc/inittab: init(8) configuration.
    # $Id: inittab,v 1.91 2002/01/25 13:35:21 miquels Exp $

    # The default runlevel.
    id:5:initdefault:

    # Boot-time system configuration/initialization script.
    # This is run first except when booting in emergency (-b) mode.
    si::sysinit:/etc/init.d/rcS

    # What to do in single-user mode.
    ~:S:wait:/sbin/sulogin

    # /etc/init.d executes the S and K scripts upon change
    # of runlevel.
    #
    # Runlevel 0 is halt.
    # Runlevel 1 is single-user.
    # Runlevels 2-5 are multi-user.
    # Runlevel 6 is reboot.

    l0:0:wait:/etc/init.d/rc 0
    l1:1:wait:/etc/init.d/rc 1
    l2:2:wait:/etc/init.d/rc 2
    l3:3:wait:/etc/init.d/rc 3
    l4:4:wait:/etc/init.d/rc 4
    l5:5:wait:/etc/init.d/rc 5
    l6:6:wait:/etc/init.d/rc 6
    # Normally not reached, but fallthrough in case of emergency.
    z6:6:respawn:/sbin/sulogin
    # AMA0:12345:respawn:/bin/start_getty 38400 ttyAMA0 vt102
    S0:12345:respawn:/bin/start_getty 0 ttyS0 vt102


inittab的内容以行为单位，行与行之间没有关联，每行都是一个独立的配置项，每一行的配置项都是由3个冒号分隔开的4个配置值组成，冒号是分隔符

inittab文件中的代码格式

::

    <id>:<runlevels>:<action>:<process>

.. note::
    id:  /dev/id ,用作终端的terminal:stdin、stdout、stderr、printf、scanf、err
    runlevels:
    action:执行时机，包括：sysinit、respawd、askfirst、waite、once、restart、ctriatdel、shutdown
    process: 应用程序和脚本
