primary_switch
==================


::

    __primary_switch:
    #ifdef CONFIG_RANDOMIZE_BASE
        mov	x19, x0				    //上一步__cpu_setup中，x0保存了SCTLR_EL1_SET,
                                    //此处将x0中的值保存到x19中
        mrs	x20, sctlr_el1			//将sctlr_el1保存到x20中
    #endif



        adrp	x1, init_pg_dir     //将kernel image映射的页表地址保存到x1中
        bl	__enable_mmu            //打开MMU

``__enable_mmu`` 定义如下

主要完成以下任务

- 将idmap_pg_dir的物理地址映射到TTBR0;

- 将init_pg_dir的物理地址设置到TTBR1

- 用SCTLR_EL1_SET来设置sctlr_el1来开启MMU

::

    /*
     * Enable the MMU.
     *
     *  x0  = SCTLR_EL1 value for turning on the MMU.
     *  x1  = TTBR1_EL1 value
     *
     * Returns to the caller via x30/lr. This requires the caller to be covered
     * by the .idmap.text section.
     *
     * Checks if the selected granule size is supported by the CPU.
     * If it isn't, park the CPU
     */
    SYM_FUNC_START(__enable_mmu)
            mrs     x2, ID_AA64MMFR0_EL1
            ubfx    x2, x2, #ID_AA64MMFR0_TGRAN_SHIFT, 4
            cmp     x2, #ID_AA64MMFR0_TGRAN_SUPPORTED
            b.ne    __no_granule_support
            update_early_cpu_boot_status 0, x2, x3
            adrp    x2, idmap_pg_dir
            phys_to_ttbr x1, x1
            phys_to_ttbr x2, x2
            msr     ttbr0_el1, x2                   // load TTBR0
            offset_ttbr1 x1, x3
            msr     ttbr1_el1, x1                   // load TTBR1
            isb
            msr     sctlr_el1, x0
            isb
            /*
             * Invalidate the local I-cache so that any instructions fetched
             * speculatively from the PoC are discarded, since they may have
             * been dynamically patched at the PoU.
             */
            ic      iallu
            dsb     nsh
            isb
            ret
    SYM_FUNC_END(__enable_mmu)


重定位kernel

::

    #ifdef CONFIG_RELOCATABLE
        bl	__relocate_kernel
    #endif

**__relocate_kernel片段1**

::

    /*
     * Iterate over each entry in the relocation table, and apply the
     * relocations in place.
     */
    ldr     w9, =__rela_offset              // offset to reloc table
    ldr     w10, =__rela_size               // size of reloc table

    #arch/arm64/kernel/vmlinux.lds.S中定义
    .rela.dyn : ALIGN(8) {
            *(.rela .rela*)
    }
    __rela_offset   = ABSOLUTE(ADDR(.rela.dyn) - KIMAGE_VADDR);
    __rela_size     = SIZEOF(.rela.dyn);

.rela.dyn区域的起始地址相对kernel image的偏移以及大小w9, w10中

**__relocate_kernel片段2**

::

    mov_q   x11, KIMAGE_VADDR               //x11保存了KIMAGE_VADDR(__text链接地址)，是Kernel Image的起始虚拟地址
    add     x11, x11, x23                   //通过与之计算的x23(保存了__text 2M对齐的偏移量，一般为0)，进行2M对齐
                                               
    add     x9, x9, x11                     //x9保存了.rela.dyn区域的链接地址
    add     x10, x9, x10                    //x10保存了.rela.dyn的结束地址


**__relocate_kernel片段3**

::

    0:      cmp     x9, x10
            b.hs    1f
            ldp     x12, x13, [x9], #24             //获取entry的link addr和link flag
            ldr     x14, [x9, #-8]                  //获取entry的link value
            cmp     w13, #R_AARCH64_RELATIVE        //判断link flag, 获取重定位类型
            b.ne    0b
            add     x14, x14, x23                // relocate
            str     x14, [x12, x23]             //执行重定位，用link value 修改link addr中的值
            b       0b                          //通过循环将所有的动态链接符号执行重定位

    1:
            ret


.. note::
    - 重定位是连接符号引用与符号定义的过程。例如，程序调用函数时，关联的调用指令必须在执行时将控制权转移到正确的目标地址。
    可重定位文件必须包含说明如何修改其节内容的信息。通过此信息，可执行文件和共享目标文件可包含进程的程序映像的正确信息。重定位项即这些数据.

    - 什么是.rela.dyn段？该节保存的是重定位信息，数据内容是包含带有显示加数的重定位条目，每个条目固定大小(24个字节). .rela.dyn在动态链接
      的目标文件中保存的是需要被重定位的变量数据
 

- .rela.dyn中包含很多entry, 每个entry有24个字节，用于描述一个可重定位符号


::

    typedef struct {
        Elf64_Addr r_offset;  // 需要修改的地址（偏移量）
        Elf64_Xword r_info;   // 符号信息和重定位类型
        Elf64_Sxword r_addend; // 添加的常量值（如果有的话）
    } Elf64_Rela;


    +----------------+-----------------------------------+-----------------
    |     64 bit     |      64 bit     |      64 bit     |     ...
    +----------------+-----------------------------------+-----------------
    | sym0 link addr | sym0 reloc flag | sym0 link value | sym1 link ...
    +----------------+-----------------------------------+-----------------

.. note::
    对于ARM64架构，常见的重定位类型包括

    - R_AARCH64_ABS64: 64位绝对地址
    - R_AARCH64_GLOB_DAT: 全局数据符号
    - R_AARCH64_JUMP_SLOT: 跳转插槽，通常用于函数指针
    - R_AARCH64_RELATIVE: 与程序基地址相关的重定位


通过反编译vmlinux，可以看到.rela.dyn段的内容

::

     4485578 ffff800011280e20 <.rela.dyn>:
     4485579 ffff800011280e20:       10044768        .word   0x10044768     //link addr
     4485580 ffff800011280e24:       ffff8000        .word   0xffff8000     
     4485581 ffff800011280e28:       00000403        .word   0x00000403     //reloc flag
     4485582 ffff800011280e2c:       00000000        .word   0x00000000
     4485583 ffff800011280e30:       10047dd8        .word   0x10047dd8     //link value
     4485584 ffff800011280e34:       ffff8000        .word   0xffff8000
     4485585 ffff800011280e38:       10044770        .word   0x10044770
     4485586 ffff800011280e3c:       ffff8000        .word   0xffff8000
     4485587 ffff800011280e40:       00000403        .word   0x00000403
     .......





::

        ldr	x8, =__primary_switched
        adrp	x0, __PHYS_OFFSET
        br	x8
    ENDPROC(__primary_switch)
