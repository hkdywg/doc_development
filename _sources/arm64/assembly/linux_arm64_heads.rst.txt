linux arm64 head.S详解
=======================

首先贴出head.S中主要的代码段

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

这几个函数为head.S中主要函数，一次执行，最后通过__primary_switch进入start_kernel函数开始C语言代码的执行


preserve_boot_args
^^^^^^^^^^^^^^^^^^^

::

    /*
     * Preserve the arguments passed by the bootloader in x0 .. x3
     */
    preserve_boot_args:
        mov	x21, x0				// x21=FDT

        adr_l	x0, boot_args			// record the contents of
        stp	x21, x1, [x0]			// x0 .. x3 at kernel entry
        stp	x2, x3, [x0, #16]

        dmb	sy				// needed before dc ivac with
                            // MMU off

        mov	x1, #0x20			// 4 x 8 bytes
        b	__inval_dcache_area		// tail call
    ENDPROC(preserve_boot_args)

bootloader把设备树的首地址赋值给了通用寄存器X0，因此现在X21保存着FDT的物理地址，用于后面的调用,同时也将x0寄存器腾了出来. 随后将x0~x3的值保存在boot_args标签所代表
的地址空间内,并使用用dmb sy设置指令屏障, 随后调用__inval_dcache_area将该片内存中的cache使无效

::

	 /*
	 * The recorded values of x0 .. x3 upon kernel entry.
	 */
	u64 __cacheline_aligned boot_args[4];


解释一下adr_l这个宏，该宏的含义是将boot_args标签的物理地址赋给了x0。adr_l宏最终会调用adrp指令，该指令的作用就是将符号地址变为运行地址，(vxlinux.lds.S中定义的标签地址都是
虚拟地址) ，运行时地址在目前情况下就是物理地址(此时MMU还没有打开)

el2_setup
^^^^^^^^^^^

ARMv8中有exception level的概念，即EL0~EL3一共4个level，这个概念代替了以往的普通模式，特权模式的概念。用户态所使用的app处于特权的最低等级EL0，内核OS运行于EL1层级，EL2则被用于
虚拟化的应用，提供Security支持的seurity monitor位于EL3

SPsel(stack pointer select)寄存器作用官方描述为Allow the Stack Pointer to be selected between SP_EL0 and SP_ELX.

currentEL,可以通过它获取当前所处的exception level


::

	adrp    x23, __PHYS_OFFSET
	and x23, x23, MIN_KIMG_ALIGN - 1    // KASLR offset, defaults to 0

	#define __PHYS_OFFSET 	(KERNEL_START - TEXT_OFFSET)

	#define KERNEL_START 	_text
	#define KERNEL_END 		_end

	/*
	 * arm64 requires the kernel image to placed
	 * TEXT_OFFSET bytes beyond a 2 MB aligned base
	 */
	#define MIN_KIMG_ALIGN		SZ_2M
	
这两行代码时找到kernel起始的物理地址保存于x23(2M大小对齐),注意__PHYS_OFFSET是虚拟地址空间的值

set_cpu_boot_mode_flag
^^^^^^^^^^^^^^^^^^^^^^^^

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


该函数也相对简单，目的很明确，就是设置__boot_cpu_mode的值。在前面的el2_setup函数中，level的值已经保存在w0中了。由于系统启动之后仍然需要了解cpu启动时候的exception level
,因此有一个全局变量__boot_cpu_mode用来保存启动时候的CPU mode

如果启动的时候是EL1 mode，会修改变量__boot_cpu_mode A域，将其修改为BOOT_CPU_MODE_EL1

如果启动的时候是EL2 mode，会修改变量__boot_cpu_mode B域，将其修改为BOOT_CPU_MODE_EL2

__create_page_tables
^^^^^^^^^^^^^^^^^^^^^

这是一段比较关键的代码，目的是建立页表，开启MMU

::


	/*
	 * Setup the initial page tables. We only setup the barest amount which is
	 * required to get the kernel running. The following sections are required:
	 *   - identity mapping to enable the MMU (low address, TTBR0)
	 *   - first few MB of the kernel linear mapping to jump to once the MMU has
	 *     been enabled
	 */
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

主要包含两个部分:

1) 为MMU的开启而准备的一致性映射identity mapping
2) 为内核的执行建立覆盖整个内核代码空间的线性映射swapper

什么是一致性映射?我们知道在开启MMU之前，代码执行所用的地址都是物理地址，而在开启MMU之后则使用虚拟地址，通过translation table进行转换，最终才得以访问物理memory。
也就是说在MMU开启的前后所使用的地址空间是不一样的

.........(这部分待完善，MMU部分看不明白)

__cpu_setup
^^^^^^^^^^^^^

.......这一段也跳过，日后再补


__primary_switch
^^^^^^^^^^^^^^^^^^^

::

	__primary_switch:
	#ifdef CONFIG_RANDOMIZE_BASE
		mov	x19, x0				// preserve new SCTLR_EL1 value
		mrs	x20, sctlr_el1			// preserve old SCTLR_EL1 value
	#endif

		adrp	x1, init_pg_dir
		bl	__enable_mmu
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

要进入start_kernel这样的C代码，没有stack可不行。用户空间的进程陷入内核态的时候，stack切换到内核栈，实际上就是该进程的thread info内存段(4k或8k)的顶部。
init_thread_union就是0号进程swapper的thread info内存段， add sp, x4, #THREAD_SIZE 指向了栈顶
