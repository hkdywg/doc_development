链接脚本实例之vmlinux.lds分析
==============================

基础部分
---------

段说明
^^^^^^^^

- text段

代码段，通常指用来存放程序执行代码的一块内存区域，这部分区域的大小在程序运行前就已经确定

- data段

数据段，通常是指用来存放程序中已经初始化的全局变量的一块内存区域，数据段属于静态内存分配

- bss段

通常是指用来存放程序中未初始化的全局变量和静态变量的一块内存区域，BSS段属于静态内存分配

- init段

linux定义的一种初始化过程中才会用到的段，一旦初始化完成，那么这些段所占的内存就会被释放掉

各种地址说明
^^^^^^^^^^^^^

- 加载地址

程序中的指令和变量等加载到RAM上的地址

- 运行地址

CPU执行第一条程序中指令时的执行地址，也就是PC寄存器中的值

- 链接地址

链接过程中链接器未指令和变量分配的地址


.. note::
    如果没有打开MMU,并且使用的位置相关设计，那么加载地址、运行地址、链接地址三者需要一致，需要保证链接地址和加载地址是一致的，否则会导致程序跑飞。如果没有
    打开MMU且使用的位置无关设计，那么运行地址和加载地址应该是一致的。如果打开了MMU那么运行地址和链接地址相同


vmlinux.lds分析
-----------------

 vmlinux.lds的生成规则在script的makefile.build中

 ::

    $(obj)/%.lds: $(src)/%.lds.S FORCE
        $(call if_changed_dep,cpp_lds_S)


一些有助于我们分析vmlinux.lds的内容
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


kernel在启动过程中会打印一些和memory信息相关的log

::

	Memory: 514112K/524288K available (2128K kernel code, 82K rwdata, 696K rodata, 1024K init, 204K bss, 10176K reserved, 0K cma-reserved)
	Virtual kernel memory layout:
		vector  : 0xffff0000 - 0xffff1000   (   4 kB)
		fixmap  : 0xffc00000 - 0xfff00000   (3072 kB)
		vmalloc : 0xe0800000 - 0xff800000   ( 496 MB)
		lowmem  : 0xc0000000 - 0xe0000000   ( 512 MB)
		modules : 0xbf000000 - 0xc0000000   (  16 MB)
		  .text : 0xc0008000 - 0xc03c228c   (3817 kB)
		  .init : 0xc0400000 - 0xc0500000   (1024 kB)
		  .data : 0xc0500000 - 0xc0514ba0   (  83 kB)
		   .bss : 0xc0514ba0 - 0xc0547d74   ( 205 kB)

这部分log是在mm/page_alloc.c中的mem_init_print_info函数中打印的.重点关注链接过程中一些段的位置

::

		  .text : 0xc0008000 - 0xc03c228c   (3817 kB)
		  .init : 0xc0400000 - 0xc0500000   (1024 kB)
		  .data : 0xc0500000 - 0xc0514ba0   (  83 kB)
		   .bss : 0xc0514ba0 - 0xc0547d74   ( 205 kB)

编译之后会生成System.map文件，该文件是内核的符号表，在这里可以找到函数地址，变量地址，包括一些链接过程中的地址定义等等


vmlinux.lds注解
^^^^^^^^^^^^^^^^

::

    OUTPUT_ARCH(aarch64) //定义一个特殊的体系结构：arm64
    ENTRY(_text)    //第一条被执行的程序被称为入口点或入口地址(entry point)，此处定义入口地址为"_text"
    jiffies = jiffies_64;   //jiffies变量是一个计数器存储系统从系统启动的tick时间流逝
    PECOFF_FILE_ALIGNMENT = 0x200;
    SECTIONS
    {
     /DISCARD/ : {
     
     
      *(.exitcall.exit)
      *(.discard)
      *(.discard.*)
      *(.interp .dynamic)
      *(.dynsym .dynstr .hash .gnu.hash)
      *(.eh_frame)
     }  //这些section的输入section都被去除，不在输出section中
     . = (((((((-(((1)) << ((((48))) - 1))))) + (0x08000000))) + (0x08000000))) + 0x00080000;
     .head.text : {     //定义一个head.text的输出节
      _text = .;        //标号_text地址
      KEEP(*(.head.text)) //再连接命令行中使用了选项-gc-sections后，链接器可能将某些它认为没用的section过滤掉，此时如有必要强制链接器保留
                         //一些特定section,可用关键字KEEP达到此目的
     }
     .text : {  //真正的代码段
      _stext = .;
       __exception_text_start = .;
       *(.exception.text)
       __exception_text_end = .;
       . = ALIGN(8); __irqentry_text_start = .; *(.irqentry.text) __irqentry_text_end = .;  //ALIGN(8)重新定义了当前地址8个字节对齐后的地址 //中断代码段
       . = ALIGN(8); __softirqentry_text_start = .; *(.softirqentry.text) __softirqentry_text_end = .;  //软中断代码段
       . = ALIGN(8); __entry_text_start = .; *(.entry.text) __entry_text_end = .;
       . = ALIGN(8); *(.text.hot .text .text.fixup .text.unlikely) *(.text..refcount) *(.ref.text)
       . = ALIGN(8); __sched_text_start = .; *(.sched.text) __sched_text_end = .;       //调度代码段
       . = ALIGN(8); __cpuidle_text_start = .; *(.cpuidle.text) __cpuidle_text_end = .; //cpudile代码段
       . = ALIGN(8); __lock_text_start = .; *(.spinlock.text) __lock_text_end = .;  //spinlock锁代码段
       . = ALIGN(8); __kprobes_text_start = .; *(.kprobes.text) __kprobes_text_end = .;     //kprobes代码段
       . = ALIGN(0x00001000); __hyp_idmap_text_start = .; *(.hyp.idmap.text) __hyp_idmap_text_end = .; __hyp_text_start = .; *(.hyp.text) __hyp_text_end = .;
       . = ALIGN(0x00001000); __idmap_text_start = .; *(.idmap.text) __idmap_text_end = .;  //idmap代码段
       . = ALIGN(0x00001000); __hibernate_exit_text_start = .; *(.hibernate_exit.text) __hibernate_exit_text_end = .;
       . = ALIGN((1 << 16)); __entry_tramp_text_start = .; *(.entry.tramp.text) . = ALIGN((1 << 16)); __entry_tramp_text_end = .;
       *(.fixup)
       *(.gnu.warning)
      . = ALIGN(16);
      *(.got)   //got: 全局偏移表格代码段
     }
     . = ALIGN(0x00010000);
     _etext = .;        //ADDR(.rodata)返回.rodata节的VMA(虚拟地址)，AT申明了LMA(加载地址的位置),此处计算出的LMA=VMA
     . = ALIGN(((1 << 16))); .rodata : AT(ADDR(.rodata) - 0) { __start_rodata = .; *(.rodata) *(.rodata.*) __start_ro_after_init = .; *(.data..ro_after_init) . = ALIGN(8); __start___jump_table = .; KEEP(*(__jump_table)) __stop___jump_table = .; __end_ro_after_init = .; . = ALIGN(8); __start___tracepoints_ptrs = .; KEEP(*(__tracepoints_ptrs)) __stop___tracepoints_ptrs = .; *(__tracepoints_strings) } .rodata1 : AT(ADDR(.rodata1) - 0) { *(.rodata1) } .pci_fixup : AT(ADDR(.pci_fixup) - 0) { __start_pci_fixups_early = .; KEEP(*(.pci_fixup_early)) __end_pci_fixups_early = .; __start_pci_fixups_header = .; KEEP(*(.pci_fixup_header)) __end_pci_fixups_header = .; __start_pci_fixups_final = .; KEEP(*(.pci_fixup_final)) __end_pci_fixups_final = .; __start_pci_fixups_enable = .; KEEP(*(.pci_fixup_enable)) __end_pci_fixups_enable = .; __start_pci_fixups_resume = .; KEEP(*(.pci_fixup_resume)) __end_pci_fixups_resume = .; __start_pci_fixups_resume_early = .; KEEP(*(.pci_fixup_resume_early)) __end_pci_fixups_resume_early = .; __start_pci_fixups_suspend = .; KEEP(*(.pci_fixup_suspend)) __end_pci_fixups_suspend = .; __start_pci_fixups_suspend_late = .; KEEP(*(.pci_fixup_suspend_late)) __end_pci_fixups_suspend_late = .; } .builtin_fw : AT(ADDR(.builtin_fw) - 0) { __start_builtin_fw = .; KEEP(*(.builtin_fw)) __end_builtin_fw = .; } __ksymtab : AT(ADDR(__ksymtab) - 0) { __start___ksymtab = .; KEEP(*(SORT(___ksymtab+*))) __stop___ksymtab = .; } __ksymtab_gpl : AT(ADDR(__ksymtab_gpl) - 0) { __start___ksymtab_gpl = .; KEEP(*(SORT(___ksymtab_gpl+*))) __stop___ksymtab_gpl = .; } __ksymtab_unused : AT(ADDR(__ksymtab_unused) - 0) { __start___ksymtab_unused = .; KEEP(*(SORT(___ksymtab_unused+*))) __stop___ksymtab_unused = .; } __ksymtab_unused_gpl : AT(ADDR(__ksymtab_unused_gpl) - 0) { __start___ksymtab_unused_gpl = .; KEEP(*(SORT(___ksymtab_unused_gpl+*))) __stop___ksymtab_unused_gpl = .; } __ksymtab_gpl_future : AT(ADDR(__ksymtab_gpl_future) - 0) { __start___ksymtab_gpl_future = .; KEEP(*(SORT(___ksymtab_gpl_future+*))) __stop___ksymtab_gpl_future = .; } __kcrctab : AT(ADDR(__kcrctab) - 0) { __start___kcrctab = .; KEEP(*(SORT(___kcrctab+*))) __stop___kcrctab = .; } __kcrctab_gpl : AT(ADDR(__kcrctab_gpl) - 0) { __start___kcrctab_gpl = .; KEEP(*(SORT(___kcrctab_gpl+*))) __stop___kcrctab_gpl = .; } __kcrctab_unused : AT(ADDR(__kcrctab_unused) - 0) { __start___kcrctab_unused = .; KEEP(*(SORT(___kcrctab_unused+*))) __stop___kcrctab_unused = .; } __kcrctab_unused_gpl : AT(ADDR(__kcrctab_unused_gpl) - 0) { __start___kcrctab_unused_gpl = .; KEEP(*(SORT(___kcrctab_unused_gpl+*))) __stop___kcrctab_unused_gpl = .; } __kcrctab_gpl_future : AT(ADDR(__kcrctab_gpl_future) - 0) { __start___kcrctab_gpl_future = .; KEEP(*(SORT(___kcrctab_gpl_future+*))) __stop___kcrctab_gpl_future = .; } __ksymtab_strings : AT(ADDR(__ksymtab_strings) - 0) { *(__ksymtab_strings) } __init_rodata : AT(ADDR(__init_rodata) - 0) { *(.ref.rodata) } __param : AT(ADDR(__param) - 0) { __start___param = .; KEEP(*(__param)) __stop___param = .; } __modver : AT(ADDR(__modver) - 0) { __start___modver = .; KEEP(*(__modver)) __stop___modver = .; . = ALIGN(((1 << 16))); __end_rodata = .; } . = ALIGN(((1 << 16)));
     . = ALIGN(8); __ex_table : AT(ADDR(__ex_table) - 0) { __start___ex_table = .; KEEP(*(__ex_table)) __stop___ex_table = .; }
     .notes : AT(ADDR(.notes) - 0) { __start_notes = .; KEEP(*(.note.*)) __stop_notes = .; }
     . = ALIGN((1 << 16));
     idmap_pg_dir = .;
     . += ((((((48)) - 4) / (16 - 3))) * (1 << 16));
     tramp_pg_dir = .;
     . += (1 << 16);
     swapper_pg_dir = .;
     . += (1 << 16);
     swapper_pg_end = .;
     . = ALIGN(0x00010000);
     __init_begin = .;
     __inittext_begin = .;
     . = ALIGN(8); .init.text : AT(ADDR(.init.text) - 0) { _sinittext = .; *(.init.text .init.text.*) *(.text.startup) *(.meminit.text*) _einittext = .; }
     .exit.text : {
      *(.exit.text) *(.text.exit) *(.memexit.text)
     }
     . = ALIGN(4);
     .altinstructions : {
      __alt_instructions = .;
      *(.altinstructions)
      __alt_instructions_end = .;
     }
     .altinstr_replacement : {
      *(.altinstr_replacement)
     }
     . = ALIGN((1 << 16));
     __inittext_end = .;
     __initdata_begin = .;
     .init.data : {
      KEEP(*(SORT(___kentry+*))) *(.init.data init.data.*) *(.meminit.data*) *(.init.rodata .init.rodata.*) *(.meminit.rodata) . = ALIGN(8); __clk_of_table = .; KEEP(*(__clk_of_table)) KEEP(*(__clk_of_table_end)) . = ALIGN(8); __reservedmem_of_table = .; KEEP(*(__reservedmem_of_table)) KEEP(*(__reservedmem_of_table_end)) . = ALIGN(8); __timer_of_table = .; KEEP(*(__timer_of_table)) KEEP(*(__timer_of_table_end)) . = ALIGN(8); __cpu_method_of_table = .; KEEP(*(__cpu_method_of_table)) KEEP(*(__cpu_method_of_table_end)) . = ALIGN(32); __dtb_start = .; KEEP(*(.dtb.init.rodata)) __dtb_end = .; . = ALIGN(8); __irqchip_of_table = .; KEEP(*(__irqchip_of_table)) KEEP(*(__irqchip_of_table_end)) . = ALIGN(8); __governor_thermal_table = .; KEEP(*(__governor_thermal_table)) __governor_thermal_table_end = .; . = ALIGN(8); __earlycon_table = .; KEEP(*(__earlycon_table)) __earlycon_table_end = .; . = ALIGN(8); __start_lsm_info = .; KEEP(*(.lsm_info.init)) __end_lsm_info = .; . = ALIGN(8); __start_early_lsm_info = .; KEEP(*(.early_lsm_info.init)) __end_early_lsm_info = .;
      . = ALIGN(16); __setup_start = .; KEEP(*(.init.setup)) __setup_end = .;
      __initcall_start = .; KEEP(*(.initcallearly.init)) __initcall0_start = .; KEEP(*(.initcall0.init)) KEEP(*(.initcall0s.init)) __initcall1_start = .; KEEP(*(.initcall1.init)) KEEP(*(.initcall1s.init)) __initcall2_start = .; KEEP(*(.initcall2.init)) KEEP(*(.initcall2s.init)) __initcall3_start = .; KEEP(*(.initcall3.init)) KEEP(*(.initcall3s.init)) __initcall4_start = .; KEEP(*(.initcall4.init)) KEEP(*(.initcall4s.init)) __initcall5_start = .; KEEP(*(.initcall5.init)) KEEP(*(.initcall5s.init)) __initcallrootfs_start = .; KEEP(*(.initcallrootfs.init)) KEEP(*(.initcallrootfss.init)) __initcall6_start = .; KEEP(*(.initcall6.init)) KEEP(*(.initcall6s.init)) __initcall7_start = .; KEEP(*(.initcall7.init)) KEEP(*(.initcall7s.init)) __initcall_end = .;
      __con_initcall_start = .; KEEP(*(.con_initcall.init)) __con_initcall_end = .;
      . = ALIGN(4); __initramfs_start = .; KEEP(*(.init.ramfs)) . = ALIGN(8); KEEP(*(.init.ramfs.info))
      *(.init.rodata.* .init.bss)
     }
     .exit.data : {
      *(.exit.data .exit.data.*) *(.fini_array .fini_array.*) *(.dtors .dtors.*) *(.memexit.data*) *(.memexit.rodata*)
     }
     . = ALIGN((1 << 16)); .data..percpu : AT(ADDR(.data..percpu) - 0) { __per_cpu_load = .; __per_cpu_start = .; *(.data..percpu..first) . = ALIGN((1 << 16)); *(.data..percpu..page_aligned) . = ALIGN((1 << (6))); *(.data..percpu..read_mostly) . = ALIGN((1 << (6))); *(.data..percpu) *(.data..percpu..shared_aligned) __per_cpu_end = .; }
     .rela.dyn : ALIGN(8) {
      *(.rela .rela*)
     }
     __rela_offset = ABSOLUTE(ADDR(.rela.dyn) - (((((((-(((1)) << ((((48))) - 1))))) + (0x08000000))) + (0x08000000))));
     __rela_size = SIZEOF(.rela.dyn);
     . = ALIGN(0x00010000);
     __initdata_end = .;
     __init_end = .;
     _data = .;
     _sdata = .;
     . = ALIGN((1 << 16)); .data : AT(ADDR(.data) - 0) { . = ALIGN((2 * (((1)) << 16))); __start_init_task = .; init_thread_union = .; init_stack = .; KEEP(*(.data..init_task)) KEEP(*(.data..init_thread_info)) . = __start_init_task + (((1)) << 16); __end_init_task = .; . = ALIGN((1 << 16)); __nosave_begin = .; *(.data..nosave) . = ALIGN((1 << 16)); __nosave_end = .; . = ALIGN((1 << 16)); *(.data..page_aligned) . = ALIGN((1 << (6))); *(.data..cacheline_aligned) . = ALIGN((1 << (6))); *(.data..read_mostly) . = ALIGN((1 << (6))); *(.xiptext) *(.data) *(.ref.data) *(.data..shared_aligned) *(.data.unlikely) __start_once = .; *(.data.once) __end_once = .; . = ALIGN(32); *(__tracepoints) . = ALIGN(8); __start___verbose = .; KEEP(*(__verbose)) __stop___verbose = .; CONSTRUCTORS } . = ALIGN(8); __bug_table : AT(ADDR(__bug_table) - 0) { __start___bug_table = .; KEEP(*(__bug_table)) __stop___bug_table = .; }
     .mmuoff.data.write : ALIGN(0x00000800) {
      __mmuoff_data_start = .;
      *(.mmuoff.data.write)
     }
     . = ALIGN(0x00000800);
     .mmuoff.data.read : {
      *(.mmuoff.data.read)
      __mmuoff_data_end = .;
     }

     __pecoff_data_rawsize = ABSOLUTE(. - __initdata_begin);
     _edata = .;
     . = ALIGN(0); __bss_start = .; . = ALIGN(0); .sbss : AT(ADDR(.sbss) - 0) { *(.dynsbss) *(.sbss) *(.scommon) } . = ALIGN(0); .bss : AT(ADDR(.bss) - 0) { *(.bss..page_aligned) *(.dynbss) *(.bss) *(COMMON) } . = ALIGN(0); __bss_stop = .;
     . = ALIGN((1 << 16));
     init_pg_dir = .;
     . += ((1 << 16) * ( 1 + (((((_end)) >> (((16 - 3) * (4 - (4 - 3)) + 3))) - ((((((((((-(((1)) << ((((48))) - 1))))) + (0x08000000))) + (0x08000000))) + 0x00080000)) >> (((16 - 3) * (4 - (4 - 3)) + 3))) + 1 + (1))) + (0) + (((((_end)) >> (((16 - 3) * (4 - (2)) + 3))) - ((((((((((-(((1)) << ((((48))) - 1))))) + (0x08000000))) + (0x08000000))) + 0x00080000)) >> (((16 - 3) * (4 - (2)) + 3))) + 1 + (1)))));
     init_pg_end = .;
     __pecoff_data_size = ABSOLUTE(. - __initdata_begin);
     _end = .;
     .stab 0 : { *(.stab) } .stabstr 0 : { *(.stabstr) } .stab.excl 0 : { *(.stab.excl) } .stab.exclstr 0 : { *(.stab.exclstr) } .stab.index 0 : { *(.stab.index) } .stab.indexstr 0 : { *(.stab.indexstr) } .comment 0 : { *(.comment) }
     _kernel_size_le_lo32 = (((_end - _text) & 0xffffffff) & 0xffffffff); _kernel_size_le_hi32 = (((_end - _text) >> 32) & 0xffffffff); _kernel_offset_le_lo32 = (((0x00080000) & 0xffffffff) & 0xffffffff); _kernel_offset_le_hi32 = (((0x00080000) >> 32) & 0xffffffff); _kernel_flags_le_lo32 = (((((0 << 0) | (((16 - 10) / 2) << (0 + 1)) | (1 << ((0 + 1) + 2)))) & 0xffffffff) & 0xffffffff); _kernel_flags_le_hi32 = (((((0 << 0) | (((16 - 10) / 2) << (0 + 1)) | (1 << ((0 + 1) + 2)))) >> 32) & 0xffffffff);
    }
    ASSERT(__hyp_idmap_text_end - (__hyp_idmap_text_start & ~(0x00001000 - 1)) <= 0x00001000,
     "HYP init code too big or misaligned")
    ASSERT(__idmap_text_end - (__idmap_text_start & ~(0x00001000 - 1)) <= 0x00001000,
     "ID map text too big or misaligned")
    ASSERT(__hibernate_exit_text_end - (__hibernate_exit_text_start & ~(0x00001000 - 1))
     <= 0x00001000, "Hibernate exit text too big or misaligned")
    ASSERT((__entry_tramp_text_end - __entry_tramp_text_start) == (1 << 16),
     "Entry trampoline text too big")
    ASSERT(_text == ((((((((-(((1)) << ((((48))) - 1))))) + (0x08000000))) + (0x08000000))) + 0x00080000), "HEAD is misaligned")


gcc除了有默认的section,例如.text、.data、.bss、.debug、.dynsym等，也支持用户自定义的section，linux内核中大量的使用gcc的扩展 ``__attribute__((section("section_name"))`` 生成自定义的section
