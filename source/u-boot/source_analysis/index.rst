source analysis
===============

目录结构
--------
::

    board:      开发板相关目录，平台依赖
    arch:       CPU相关目录，平台依赖
    include:    头文件目录，开发板的配置文件也在其中，configs存放开发板配置文件
    common:     通用多功能函数实现
    cmd:        cmd命令实现
    drivers:    通用设备驱动程序，包括以太网，flash驱动等
    fs:         文件系统支持
    lib:        通用库函数实现
    net:        网络相关工具
    tool:       工具
    script:     脚本

u-boot目录可分为3类：

1)  处理器体系结构或开发板硬件直接相关的
2)  通用函数或者驱动程序
3)  u-boot应用程序、工具或者文档


重要文件
--------

- include/configs/holo_ark_v3.h

开发板配置文件,包含spl loader配置信息，环境变量配置信息，地址配置信息等

- arch/arm/cpu/armv8/u-boot.lds

程序链接脚本，定义程序入口entry(_start),并安排各程序段衔接位置，程序首先运行start.s文件。

- arch/arm/cpu/armv8/start.S

程序首先运行的文件，程序刚开始运行的汇编代码，完成基本初始化。

- arch/arm/cpu/armv8/lowlevel_init.S

内存初始化，clock、SDRAM初始化代码（bootstrap中已完成，不执行）

- board/holomatic/holo_ark_v3/board.c

C语言入口start

- common/main.c

main_loop()定义于此。

- arch/arm/lib/interrupts.c

中断相关函数

main_loop()在没有字符输入的情况下。执行autoboot_command函数，boot kernel

u-boot 实际主要运行的三个位置::

    _start----->start_armboot-------->main_loop

生成文件
--------

::

    System.map:     uboot映像符号表，它包含了uboot全局变量和函数的地址信息。可供用户查看或由外部程序调试使用
    uboot.bin:      uboot映像原始二进制文件。
    uboot：         uboot映像elf格式文件。
    uboot.srec:     uboot映像的s_record格式。
    注：uboot和uboot.srec格式都自带定位信息
    tool/mkimge可转换为其他格式印象


u-boot启动流程
--------------

嵌入式系统启动的基本流程是这样的：

RoomBoot--->SPL--->u-boot--->linux kernel--->file system------>start application

1)  RoomBoot 是固化在芯片内部的代码，负责从各种外(sdcard、mmc、flash、)中加载spl到芯片内部的SRAM
2)  SPL的主要工作是初始化板载的DDRAM，然后将u-boot搬运到DDRAM中
3)  u-boot最主要的功能就是加载启动linux kernel

spl一般是地址无关的，设计成地址无关的主要目的是为了保证SPL被搬运到任何地方都能运行，这样设计是因为我们不知道spl会被放到
哪个地址运行。

位置无关码究其原因，主要是编译生成的汇编代码都是相对地址。

SPL启动流程分析
^^^^^^^^^^^^^^^

spl的入口代码是在arch/arm/lib/vector.S中的 ``_start`` 函数

- _start

::

    .macro ARM_VECTORS                                                                                                                                              
    #ifdef CONFIG_ARCH_K3                                                                                                                                                   
        ldr     pc, _reset                                                                                                                                                  
    #else                                                                                                                                                                   
        b   reset                                                                                                                                                           
    #endif                                                                                                                                                                  
        ldr pc, _undefined_instruction                                                                                                                                      
        ldr pc, _software_interrupt                                                                                                                                         
        ldr pc, _prefetch_abort                                                                                                                                             
        ldr pc, _data_abort                                                                                                                                                 
        ldr pc, _not_used                                                                                                                                                   
        ldr pc, _irq                                                                                                                                                        
        ldr pc, _fiq                                                                                                                                                        
        .endm             

    _start:
    #ifdef CONFIG_SYS_DV_NOR_BOOT_CFG
       .word   CONFIG_SYS_DV_NOR_BOOT_CFG
    #endif
       ARM_VECTORS                                                                                                                                                         
    #endif /* !defined(CONFIG_ENABLE_ARM_SOC_BOOT0_HOOK) */   

1)  _start中直接执行reset
2)  ldr pc, _xx定义的是中断的处理方式，类似中断向量表

注：spl阶段是不允许中断的，u-boot可以

- reset

代码路径：arch/arm/cpu/armv8/start.S

::

    reset:
	/* Allow the board to save important registers */
	b	save_boot_params
    .globl	save_boot_params_ret
    save_boot_params_ret:

    #if CONFIG_POSITION_INDEPENDENT
        /*
         * Fix .rela.dyn relocations. This allows U-Boot to be loaded to and
         * executed at a different address than it was linked at.
         */
    pie_fixup:
        adr	x0, _start		/* x0 <- Runtime value of _start */
        ldr	x1, _TEXT_BASE		/* x1 <- Linked value of _start */
        sub	x9, x0, x1		/* x9 <- Run-vs-link offset */
        adr	x2, __rel_dyn_start	/* x2 <- Runtime &__rel_dyn_start */
        adr	x3, __rel_dyn_end	/* x3 <- Runtime &__rel_dyn_end */
    pie_fix_loop:
        ldp	x0, x1, [x2], #16	/* (x0, x1) <- (Link location, fixup) */
        ldr	x4, [x2], #8		/* x4 <- addend */
        cmp	w1, #1027		/* relative fixup? */
        bne	pie_skip_reloc
        /* relative fix: store addend plus offset at dest location */
        add	x0, x0, x9
        add	x4, x4, x9
        str	x4, [x0]
    pie_skip_reloc:
        cmp	x2, x3
        b.lo	pie_fix_loop
    pie_fixup_done:
    #endif

    #ifdef CONFIG_SYS_RESET_SCTRL
        bl reset_sctrl
    #endif

    #if defined(CONFIG_ARMV8_SPL_EXCEPTION_VECTORS) || !defined(CONFIG_SPL_BUILD)
    .macro	set_vbar, regname, reg
        msr	\regname, \reg
    .endm
        adr	x0, vectors
    #else
    .macro	set_vbar, regname, reg
    .endm
    #endif
        /*
         * Could be EL3/EL2/EL1, Initial State:
         * Little Endian, MMU Disabled, i/dCache Disabled
         */
        switch_el x1, 3f, 2f, 1f
    3:	set_vbar vbar_el3, x0
        mrs	x0, scr_el3
        orr	x0, x0, #0xf			/* SCR_EL3.NS|IRQ|FIQ|EA */
        msr	scr_el3, x0
        msr	cptr_el3, xzr			/* Enable FP/SIMD */
    #ifdef COUNTER_FREQUENCY
        ldr	x0, =COUNTER_FREQUENCY
        msr	cntfrq_el0, x0			/* Initialize CNTFRQ */
    #endif
        b	0f
    2:	set_vbar	vbar_el2, x0
        mov	x0, #0x33ff
        msr	cptr_el2, x0			/* Enable FP/SIMD */
        b	0f
    1:	set_vbar	vbar_el1, x0
        mov	x0, #3 << 20
        msr	cpacr_el1, x0			/* Enable FP/SIMD */
    0:

        /*
         * Enable SMPEN bit for coherency.
         * This register is not architectural but at the moment
         * this bit should be set for A53/A57/A72.
         */
    #ifdef CONFIG_ARMV8_SET_SMPEN
        switch_el x1, 3f, 1f, 1f
    3:
        mrs     x0, S3_1_c15_c2_1               /* cpuectlr_el1 */
        orr     x0, x0, #0x40
        msr     S3_1_c15_c2_1, x0
    1:
    #endif

        /* Apply ARM core specific erratas */
        bl	apply_core_errata

        /*
         * Cache/BPB/TLB Invalidate
         * i-cache is invalidated before enabled in icache_enable()
         * tlb is invalidated before mmu is enabled in dcache_enable()
         * d-cache is invalidated before enabled in dcache_enable()
         */

        /* Processor specific initialization */
        bl	lowlevel_init

    #if defined(CONFIG_ARMV8_SPIN_TABLE) && !defined(CONFIG_SPL_BUILD)
        branch_if_master x0, x1, master_cpu
        b	spin_table_secondary_jump
        /* never return */
    #elif defined(CONFIG_ARMV8_MULTIENTRY)
        branch_if_master x0, x1, master_cpu

        /*
         * Slave CPUs
         */
    slave_cpu:
        wfe
        ldr	x1, =CPU_RELEASE_ADDR
        ldr	x0, [x1]
        cbz	x0, slave_cpu
        br	x0			/* branch to the given address */
    #endif /* CONFIG_ARMV8_MULTIENTRY */
    master_cpu:
        bl	_main


主要设置CPU的工作模式，禁用FIQ，IRQ。然后跳转到 ``lowlevel_init`` 中，然后跳转到 ``_main``


- lowlevel_init

代码路径：arch/arm/cpu/armv8/lowlevel_init.S

::

    ENTRY(lowlevel_init)
	/*
	 * Setup a temporary stack. Global data is not available yet.
	 */
    #if defined(CONFIG_SPL_BUILD) && defined(CONFIG_SPL_STACK)
        ldr	w0, =CONFIG_SPL_STACK
    #else
        ldr	w0, =CONFIG_SYS_INIT_SP_ADDR
    #endif
	bic	sp, x0, #0xf	/* 16-byte alignment for ABI compliance */

	/*
	 * Save the old LR(passed in x29) and the current LR to stack
	 */
	stp	x29, x30, [sp, #-16]!

	/*
	 * Call the very early init function. This should do only the
	 * absolute bare minimum to get started. It should not:
	 *
	 * - set up DRAM
	 * - use global_data
	 * - clear BSS
	 * - try to start a console
	 *
	 * For boards with SPL this should be empty since SPL can do all of
	 * this init in the SPL board_init_f() function which is called
	 * immediately after this.
	 */
	bl	s_init
	ldp	x29, x30, [sp]
	ret
    ENDPROC(lowlevel_init)

1)  设置栈指针
2)  确保sp 16字节对齐
3)  跳转到s_init中

- _main

代码路径： arch/arm/lib/crt0_64.S

::

    ENTRY(_main)

    /*
     * Set up initial C runtime environment and call board_init_f(0).
     */
    #if defined(CONFIG_TPL_BUILD) && defined(CONFIG_TPL_NEEDS_SEPARATE_STACK)
        ldr	x0, =(CONFIG_TPL_STACK)
    #elif defined(CONFIG_SPL_BUILD) && defined(CONFIG_SPL_STACK)
        ldr	x0, =(CONFIG_SPL_STACK)
    #elif defined(CONFIG_INIT_SP_RELATIVE)
        adr	x0, __bss_start
        add	x0, x0, #CONFIG_SYS_INIT_SP_BSS_OFFSET
    #else
        ldr	x0, =(CONFIG_SYS_INIT_SP_ADDR)
    #endif
        bic	sp, x0, #0xf	/* 16-byte alignment for ABI compliance */
        mov	x0, sp
        bl	board_init_f_alloc_reserve
        mov	sp, x0
        /* set up gd here, outside any C code */
        mov	x18, x0
        bl	board_init_f_init_reserve

        mov	x0, #0
        bl	board_init_f

    #if !defined(CONFIG_SPL_BUILD)
    /*
     * Set up intermediate environment (new sp and gd) and call
     * relocate_code(addr_moni). Trick here is that we'll return
     * 'here' but relocated.
     */
        ldr	x0, [x18, #GD_START_ADDR_SP]	/* x0 <- gd->start_addr_sp */
        bic	sp, x0, #0xf	/* 16-byte alignment for ABI compliance */
        ldr	x18, [x18, #GD_NEW_GD]		/* x18 <- gd->new_gd */

        adr	lr, relocation_return
    #if CONFIG_POSITION_INDEPENDENT
        /* Add in link-vs-runtime offset */
        adr	x0, _start		/* x0 <- Runtime value of _start */
        ldr	x9, _TEXT_BASE		/* x9 <- Linked value of _start */
        sub	x9, x9, x0		/* x9 <- Run-vs-link offset */
        add	lr, lr, x9
    #endif
        /* Add in link-vs-relocation offset */
        ldr	x9, [x18, #GD_RELOC_OFF]	/* x9 <- gd->reloc_off */
        add	lr, lr, x9	/* new return address after relocation */
        ldr	x0, [x18, #GD_RELOCADDR]	/* x0 <- gd->relocaddr */
        b	relocate_code

    relocation_return:

    /*
     * Set up final (full) environment
     */
        bl	c_runtime_cpu_setup		/* still call old routine */
    #endif /* !CONFIG_SPL_BUILD */
    #if !defined(CONFIG_SPL_BUILD) || CONFIG_IS_ENABLED(FRAMEWORK)
    #if defined(CONFIG_SPL_BUILD)
        bl	spl_relocate_stack_gd           /* may return NULL */
        /* set up gd here, outside any C code, if new stack is returned */
        cmp	x0, #0
        csel	x18, x0, x18, ne
        /*
         * Perform 'sp = (x0 != NULL) ? x0 : sp' while working
         * around the constraint that conditional moves can not
         * have 'sp' as an operand
         */
        mov	x1, sp
        cmp	x0, #0
        csel	x0, x0, x1, ne
        mov	sp, x0
    #endif

    /*
     * Clear BSS section
     */
        ldr	x0, =__bss_start		/* this is auto-relocated! */
        ldr	x1, =__bss_end			/* this is auto-relocated! */
    clear_loop:
        str	xzr, [x0], #8
        cmp	x0, x1
        b.lo	clear_loop

        /* call board_init_r(gd_t *id, ulong dest_addr) */
        mov	x0, x18				/* gd_t */
        ldr	x1, [x18, #GD_RELOCADDR]	/* dest_addr */
        b	board_init_r			/* PC relative jump */

        /* NOTREACHED - board_init_r() does not return */
    #endif

    ENDPROC(_main)


_main 所做的工作都是为调用C函数做前期的准备，这个C函数就是 ``board_init_f``

1)  重新对sp赋值，确认是16字节对齐
2)  board_init_f_alloc_reserve board_init_f_init_reserve C函数在栈顶保留一个global_data的大小，这个global_data是u-boot里面的一个全局数据
    很多地方都会用到，俗称gd_t
3)  跳转到board_init_r

- board_init_r 

代码路径： common/spl/spl.c

::

    void board_init_r(gd_t *dummy1, ulong dummy2)
    {
        int ret;
        u32 spl_boot_list[] = {
            BOOT_DEVICE_NONE,
            BOOT_DEVICE_NONE,
            BOOT_DEVICE_NONE,
            BOOT_DEVICE_NONE,
            BOOT_DEVICE_NONE,
        };
        struct spl_image_info spl_image;

        debug(">>" SPL_TPL_PROMPT "board_init_r()\n");

        spl_set_bd();

    #if defined(CONFIG_SYS_SPL_MALLOC_START)
        mem_malloc_init(CONFIG_SYS_SPL_MALLOC_START, CONFIG_SYS_SPL_MALLOC_SIZE);
        gd->flags |= GD_FLG_FULL_MALLOC_INIT;
    #endif

        if (!(gd->flags & GD_FLG_SPL_INIT)) {
            if (spl_init()) {
                hang();
            }
        }

    #if !defined(CONFIG_PPC) && !defined(CONFIG_ARCH_MX6)
        timer_init();
    #endif

        if (CONFIG_IS_ENABLED(BLOBLIST)) {
            ret = bloblist_init();
            if (ret) {
                debug("%s: Failed to set up bloblist: ret=%d\n", __func__, ret);
                puts(SPL_TPL_PROMPT "Cannot set up bloblist\n");
                hang();
            }
        }

        if (CONFIG_IS_ENABLED(HANDOFF)) {
            ret = setup_spl_handoff();
            if (ret) {
                puts(SPL_TPL_PROMPT "Cannot set up SPL handoff\n");
                hang();
            }
        }

    #if CONFIG_IS_ENABLED(BOARD_INIT)
        spl_board_init();
    #endif

    #if defined(CONFIG_SPL_WATCHDOG_SUPPORT) && CONFIG_IS_ENABLED(WDT)
        initr_watchdog();
    #endif

        if (IS_ENABLED(CONFIG_SPL_OS_BOOT) || CONFIG_IS_ENABLED(HANDOFF)) {
            dram_init_banksize();
        }

        bootcount_inc();

        memset(&spl_image, '\0', sizeof(spl_image));
    #ifdef CONFIG_SYS_SPL_ARGS_ADDR
        spl_image.arg = (void *)CONFIG_SYS_SPL_ARGS_ADDR;
    #endif
        spl_image.boot_device = BOOT_DEVICE_NONE;

        board_boot_order(spl_boot_list);

        if (boot_from_devices(&spl_image, spl_boot_list, ARRAY_SIZE(spl_boot_list))) {
            puts(SPL_TPL_PROMPT "failed to boot from all boot devices\n");
            hang();
        }

        spl_perform_fixups(&spl_image);

        if (CONFIG_IS_ENABLED(HANDOFF)) {
            ret = write_spl_handoff();
            if (ret) {
                printf(SPL_TPL_PROMPT "SPL hand-off write failed (err=%d)\n", ret);
            }
        }

        if (CONFIG_IS_ENABLED(BLOBLIST)) {
            ret = bloblist_finish();
            if (ret) {
                printf("Warning: Failed to finish bloblist (ret=%d)\n", ret);
            }
        }

    #ifdef CONFIG_CPU_V7M
        spl_image.entry_point |= 0x1;
    #endif

        switch (spl_image.os) {
        case IH_OS_U_BOOT:
            debug("Jumping to U-Boot\n");
            break;
    #if CONFIG_IS_ENABLED(ATF)
        case IH_OS_ARM_TRUSTED_FIRMWARE:
            debug("Jumping to U-Boot via ARM Trusted Firmware\n");
            spl_invoke_atf(&spl_image);
            break;
    #endif
    #if CONFIG_IS_ENABLED(OPTEE)
        case IH_OS_TEE:
            debug("Jumping to U-Boot via OP-TEE\n");
            spl_optee_entry(NULL, NULL, spl_image.fdt_addr, (void *)spl_image.entry_point);
            break;
    #endif
    #if CONFIG_IS_ENABLED(OPENSBI)
        case IH_OS_OPENSBI:
            debug("Jumping to U-Boot via RISC-V OpenSBI\n");
            spl_invoke_opensbi(&spl_image);
            break;
    #endif
    #ifdef CONFIG_SPL_OS_BOOT
        case IH_OS_LINUX:
            debug("Jumping to Linux\n");
            spl_fixup_fdt();
            spl_board_prepare_for_linux();
            jump_to_image_linux(&spl_image);
    #endif
        default:
            debug("Unsupported OS image.. Jumping nevertheless..\n");
        }
    #if CONFIG_VAL(SYS_MALLOC_F_LEN) && !defined(CONFIG_SYS_SPL_MALLOC_SIZE)
        debug("SPL malloc() used 0x%lx bytes (%ld KB)\n", gd->malloc_ptr, gd->malloc_ptr / 1024);
    #endif
        bootstage_mark_name(spl_phase() == PHASE_TPL ? BOOTSTAGE_ID_END_TPL : BOOTSTAGE_ID_END_SPL, "end " SPL_TPL_NAME);
    #ifdef CONFIG_BOOTSTAGE_STASH
        ret = bootstage_stash((void *)CONFIG_BOOTSTAGE_STASH_ADDR, CONFIG_BOOTSTAGE_STASH_SIZE);
        if (ret) {
            debug("Failed to stash bootstage: err=%d\n", ret);
        }
    #endif

        debug("loaded - jumping to U-Boot...\n");
        spl_board_prepare_for_boot();
        jump_to_image_no_args(&spl_image);
    }

1)  mem_malloc_init 进行memory的malloc池初始化，以后调用malloc就在这个池子中分配内存
2)  spl_init 包括fdt log等前期初始化工作
3)  timer_init  定时器初始化
4)  spl_board_init 根据配置选项完成相应的spl阶段外设初始化，包括console i2c misc watchdog
5)  boot_from_devices 设置从哪个外部设备启动(NAND  SDCARD NOR)
6） 将image从外部设备load到ram中
7)  判断image类型，如果是uboot则break，去运行u-boot。如果是linux则启动linux(说明：spl可以直接启动linux)

至此，SPL结束它的生命，控制权交给uboot或者linux

u-boot 启动流程分析
^^^^^^^^^^^^^^^^^^^

从编译系统可知，u-boo.bin的入口代码是arch/arm/lib/vectors.S中的_start函数

- _start

代码路径： arch/arm/lib/vectors.S

与SPL的执行流程基本一直，不同的地方是u-boot.bin阶段会负责处理异常中断。_start会跳转到reset

- reset

代码路径 arch/arm/cpu/armv8/start.S

与spl的reset执行流程一致。reset会跳转到_main

- _main

代码路径： arch/arm/lib/crt0_64.S

前一部分与spl的执行基本一致，board_init_f函数的调用会有不同。两个阶段调用的函数名虽然都是一样的，但实现的文件是不同的。
spl的board_init_f是在arch/arm/lib/spl.c中实现的，而u-boot.bin阶段是在arch/arm/mach-k3/j721e_init.c中实现的，这个不同是由
编译阶段决定的。

第二部分主要的事情是 ``relocate_code``

u-boot.bin 的链接地址是在编译阶段决定的，假设这个链接地址是0x20000000,SPL在load uboot.bin的时候，需要把它load到这个地址，然后
jump到这个地址运行。

注意：u-boot.bin是地址相关的，只有link address,load address , run address这三者一致才可正常运行。当代码运行到 ``b relocate_code`` 
这个位置时，代表u-boot.bin已经被加约定地址。

relocate_code意思时把u-boot.bin余下部分的code全部搬运到另外一个地址运行。

relocate_code 代码在arch/arm/lib/relocate_64.S中实现

第三部分是 ``board_init_r``,该函数的实现在/common/board_r.c 中。

- board_init_f

代码路径： arch/arm/mach-k3/j721e_init.c

::

    void board_init_f(ulong dummy)
    {
    #if defined(CONFIG_K3_J721E_DDRSS) || defined(CONFIG_K3_LOAD_SYSFW)
        int ret;
        struct udevice *dev;
    #endif

        store_boot_index_from_rom();

        ctrl_mmr_unlock();

    #ifdef CONFIG_CPU_V7R
        disable_linefill_optimization();
        setup_k3_mpu_regions();
    #endif

        spl_early_init();

    #ifdef CONFIG_K3_LOAD_SYSFW
        ret = uclass_find_device_by_seq(UCLASS_SERIAL, 0, true, &dev);
        if (!ret) {
            pinctrl_select_state(dev, "default");
        }

        /*
         * Load, start up, and configure system controller firmware. Provide
         * the U-Boot console init function to the SYSFW post-PM configuration
         * callback hook, effectively switching on (or over) the console
         * output.
         */
        k3_sysfw_loader(k3_mmc_stop_clock, k3_mmc_restart_clock);

        /* Prepare console output */
        preloader_console_init();

        /* Disable ROM configured firewalls right after loading sysfw */
    #ifdef CONFIG_TI_SECURE_DEVICE
        remove_fwl_configs(cbass_hc_cfg0_fwls, ARRAY_SIZE(cbass_hc_cfg0_fwls));
        remove_fwl_configs(cbass_hc0_fwls, ARRAY_SIZE(cbass_hc0_fwls));
        remove_fwl_configs(cbass_rc_cfg0_fwls, ARRAY_SIZE(cbass_rc_cfg0_fwls));
        remove_fwl_configs(cbass_rc0_fwls, ARRAY_SIZE(cbass_rc0_fwls));
        remove_fwl_configs(infra_cbass0_fwls, ARRAY_SIZE(infra_cbass0_fwls));
        remove_fwl_configs(mcu_cbass0_fwls, ARRAY_SIZE(mcu_cbass0_fwls));
        remove_fwl_configs(wkup_cbass0_fwls, ARRAY_SIZE(wkup_cbass0_fwls));
    #endif
    #else
        /* Prepare console output */
        preloader_console_init();
    #endif

    #if defined(CONFIG_TARGET_J721E_A72_EVM) || defined(CONFIG_TARGET_J721E_R5_EVM)
        /* Perform EEPROM-based board detection */
        do_board_detect();
    #endif

    #if defined(CONFIG_CPU_V7R) && defined(CONFIG_K3_AVS0)
        ret = uclass_get_device_by_driver(UCLASS_MISC, DM_GET_DRIVER(k3_avs), &dev);
        if (ret) {
            printf("AVS init failed: %d\n", ret);
        }
    #endif

    #if defined(CONFIG_K3_J721E_DDRSS)
        ret = uclass_get_device(UCLASS_RAM, 0, &dev);
        if (ret) {
            panic("DRAM init failed: %d\n", ret);
        }
    #endif
    }

1)  设置CPU工作状态
2)  load u-boot.bin,可以从mmc DFU或者UART获取到
3)  console初始化

- board_init_r

代码路径： common/board_r.c

::

    void board_init_r(gd_t *new_gd, ulong dest_addr)
    {
        /*
         * Set up the new global data pointer. So far only x86 does this
         * here.
         * TODO(sjg@chromium.org): Consider doing this for all archs, or
         * dropping the new_gd parameter.
         */
    #if CONFIG_IS_ENABLED(X86_64)
        arch_setup_gd(new_gd);
    #endif

    #ifdef CONFIG_NEEDS_MANUAL_RELOC
        int i;
    #endif

    #if !defined(CONFIG_X86) && !defined(CONFIG_ARM) && !defined(CONFIG_ARM64)
        gd = new_gd;
    #endif
        gd->flags &= ~GD_FLG_LOG_READY;

    #ifdef CONFIG_NEEDS_MANUAL_RELOC
        for (i = 0; i < ARRAY_SIZE(init_sequence_r); i++)
            init_sequence_r[i] += gd->reloc_off;
    #endif

        if (initcall_run_list(init_sequence_r))
            hang();

        /* NOTREACHED - run_main_loop() does not return */
        hang();
    }

board_init_r中一个重要的函数是 ``initcall_run_list(init_sequrnce_r)`` ,此函数会顺序调用 ``init_sequence_r`` 中的
函数列表。如下

::

    static init_fnc_t init_sequence_r[] = {
        initr_trace,
        initr_reloc,
        /* TODO: could x86/PPC have this also perhaps? */
    #ifdef CONFIG_ARM
        initr_caches,
        /* Note: For Freescale LS2 SoCs, new MMU table is created in DDR.
         *	 A temporary mapping of IFC high region is since removed,
         *	 so environmental variables in NOR flash is not available
         *	 until board_init() is called below to remap IFC to high
         *	 region.
         */
    #endif
        initr_reloc_global_data,
    #if defined(CONFIG_SYS_INIT_RAM_LOCK) && defined(CONFIG_E500)
        initr_unlock_ram_in_cache,
    #endif
        initr_barrier,
        initr_malloc,
        log_init,
        initr_bootstage,	/* Needs malloc() but has its own timer */
        initr_console_record,
    #ifdef CONFIG_SYS_NONCACHED_MEMORY
        initr_noncached,
    #endif
    #ifdef CONFIG_OF_LIVE
        initr_of_live,
    #endif
    #ifdef CONFIG_DM
        initr_dm,
    #endif
    #if defined(CONFIG_ARM) || defined(CONFIG_NDS32) || defined(CONFIG_RISCV) || \
        defined(CONFIG_SANDBOX)
        board_init,	/* Setup chipselects */
    #endif
        /*
         * TODO: printing of the clock inforamtion of the board is now
         * implemented as part of bdinfo command. Currently only support for
         * davinci SOC's is added. Remove this check once all the board
         * implement this.
         */
    #ifdef CONFIG_CLOCKS
        set_cpu_clk_info, /* Setup clock information */
    #endif
    #ifdef CONFIG_EFI_LOADER
        efi_memory_init,
    #endif
        initr_binman,
    #ifdef CONFIG_FSP_VERSION2
        arch_fsp_init_r,
    #endif
        initr_dm_devices,
        stdio_init_tables,
        initr_serial,
        initr_announce,
    #if CONFIG_IS_ENABLED(WDT)
        initr_watchdog,
    #endif
        INIT_FUNC_WATCHDOG_RESET
    #ifdef CONFIG_NEEDS_MANUAL_RELOC
        initr_manual_reloc_cmdtable,
    #endif
    #if defined(CONFIG_PPC) || defined(CONFIG_M68K) || defined(CONFIG_MIPS)
        initr_trap,
    #endif
    #ifdef CONFIG_ADDR_MAP
        initr_addr_map,
    #endif
    #if defined(CONFIG_BOARD_EARLY_INIT_R)
        board_early_init_r,
    #endif
        INIT_FUNC_WATCHDOG_RESET
    #ifdef CONFIG_POST
        initr_post_backlog,
    #endif
        INIT_FUNC_WATCHDOG_RESET
    #if defined(CONFIG_PCI) && defined(CONFIG_SYS_EARLY_PCI_INIT)
        /*
         * Do early PCI configuration _before_ the flash gets initialised,
         * because PCU resources are crucial for flash access on some boards.
         */
        initr_pci,
    #endif
    #ifdef CONFIG_ARCH_EARLY_INIT_R
        arch_early_init_r,
    #endif
        power_init_board,
    #ifdef CONFIG_MTD_NOR_FLASH
        initr_flash,
    #endif
        INIT_FUNC_WATCHDOG_RESET
    #if defined(CONFIG_PPC) || defined(CONFIG_M68K) || defined(CONFIG_X86)
        /* initialize higher level parts of CPU like time base and timers */
        cpu_init_r,
    #endif
    #ifdef CONFIG_CMD_NAND
        initr_nand,
    #endif
    #ifdef CONFIG_CMD_ONENAND
        initr_onenand,
    #endif
    #ifdef CONFIG_MMC
        initr_mmc,
    #endif
        initr_env,
    #ifdef CONFIG_SYS_BOOTPARAMS_LEN
        initr_malloc_bootparams,
    #endif
        INIT_FUNC_WATCHDOG_RESET
        initr_secondary_cpu,
    #if defined(CONFIG_ID_EEPROM) || defined(CONFIG_SYS_I2C_MAC_OFFSET)
        mac_read_from_eeprom,
    #endif
        INIT_FUNC_WATCHDOG_RESET
    #if defined(CONFIG_PCI) && !defined(CONFIG_SYS_EARLY_PCI_INIT)
        /*
         * Do pci configuration
         */
        initr_pci,
    #endif
        stdio_add_devices,
        initr_jumptable,
    #ifdef CONFIG_API
        initr_api,
    #endif
        console_init_r,		/* fully init console as a device */
    #ifdef CONFIG_DISPLAY_BOARDINFO_LATE
        console_announce_r,
        show_board_info,
    #endif
    #ifdef CONFIG_ARCH_MISC_INIT
        arch_misc_init,		/* miscellaneous arch-dependent init */
    #endif
    #ifdef CONFIG_MISC_INIT_R
        misc_init_r,		/* miscellaneous platform-dependent init */
    #endif
        INIT_FUNC_WATCHDOG_RESET
    #ifdef CONFIG_CMD_KGDB
        initr_kgdb,
    #endif
        interrupt_init,
    #ifdef CONFIG_ARM
        initr_enable_interrupts,
    #endif
    #if defined(CONFIG_MICROBLAZE) || defined(CONFIG_M68K)
        timer_init,		/* initialize timer */
    #endif
    #if defined(CONFIG_LED_STATUS)
        initr_status_led,
    #endif
        /* PPC has a udelay(20) here dating from 2002. Why? */
    #ifdef CONFIG_CMD_NET
        initr_ethaddr,
    #endif
    #if defined(CONFIG_GPIO_HOG)
        gpio_hog_probe_all,
    #endif
    #ifdef CONFIG_BOARD_LATE_INIT
        board_late_init,
    #endif
    #if defined(CONFIG_SCSI) && !defined(CONFIG_DM_SCSI)
        INIT_FUNC_WATCHDOG_RESET
        initr_scsi,
    #endif
    #ifdef CONFIG_BITBANGMII
        initr_bbmii,
    #endif
    #ifdef CONFIG_CMD_NET
        INIT_FUNC_WATCHDOG_RESET
        initr_net,
    #endif
    #ifdef CONFIG_POST
        initr_post,
    #endif
    #if defined(CONFIG_IDE) && !defined(CONFIG_BLK)
        initr_ide,
    #endif
    #ifdef CONFIG_LAST_STAGE_INIT
        INIT_FUNC_WATCHDOG_RESET
        /*
         * Some parts can be only initialized if all others (like
         * Interrupts) are up and running (i.e. the PC-style ISA
         * keyboard).
         */
        last_stage_init,
    #endif
    #ifdef CONFIG_CMD_BEDBUG
        INIT_FUNC_WATCHDOG_RESET
        initr_bedbug,
    #endif
    #if defined(CONFIG_PRAM)
        initr_mem,
    #endif
    #if defined(CONFIG_M68K) && defined(CONFIG_BLOCK_CACHE)
        blkcache_init,
    #endif
        run_main_loop,
    };


此函数列表囊括了C语言实现的u-boot 几乎所有功能。通过函数名可大概了解到实现的功能

最后一个函数run_main_loop会跳转到main_loop中执行。

- main_loop

代码路径： common/main.c

::

    /* We come here after U-Boot is initialised and ready to process commands */
    void main_loop(void)
    {
        const char *s;

        bootstage_mark_name(BOOTSTAGE_ID_MAIN_LOOP, "main_loop");

        if (IS_ENABLED(CONFIG_VERSION_VARIABLE))
            env_set("ver", version_string);  /* set version variable */

        cli_init();

        if (IS_ENABLED(CONFIG_USE_PREBOOT))
            run_preboot_environment_command();

        if (IS_ENABLED(CONFIG_UPDATE_TFTP))
            update_tftp(0UL, NULL, NULL);

        s = bootdelay_process();
        if (cli_process_fdt(&s))
            cli_secure_boot_cmd(s);

        autoboot_command(s);

        cli_loop();
        panic("No CLI available");
    }

1)  bootstage_mark_name设置当前状态为main_loop
2)  设置环境变量env
3)  run_preboot_environment_command 运行环境变量preboot所定义的命令
4)  如果定义了CONFIG_UPDATE_TFTP则通过tftp下在filename到某个地址然后将其烧录到flash中
5)  bootdelay_process 从环境变量bootdelay获取需要等待多少时间，超时时间内没有字符键入则
    从环境变量bootcmd中获取对应的命令然后执行

至此u-boot结束它的生命周期，控制权交由kernel


