uboot向kernel的传参机制--bootm与tags
=====================================

u-boot在启动内核时，会向内核传递一些参数，可以通过两种方式传递参数给内核，一种是通过参数链表(ttagged list)方式，一种是通过设备树方式。这些参数主要包括
系统的根设备标志，页面大小，内存的起始地址和大小等参数。


struct tag传递参数
-------------------

u-boot把要传递给kernel的参数保存在struct tag数据结构中，启动内核时，把这个结构体的物理地址传递给kernel，kernel会通过这个地址分析出u-boot传递的参数

主要数据结构介绍
^^^^^^^^^^^^^^^^^

首先看一下两个比较重要的数据结构 ``struct global_data`` 和 ``struct tag``

**struct global_data**

该数据结构定义在  `include/asm-generic/global_data.h` 中,其中包含了体系相关的数据结构 `struct arch_global_data arch`

::

    typedef struct global_data {
        bd_t *bd;
        unsigned long flags;
        unsigned int baudrate;
        unsigned long cpu_clk;		/* CPU clock in Hz!		*/
        unsigned long bus_clk;
        /* We cannot bracket this with CONFIG_PCI due to mpc5xxx */
        unsigned long pci_clk;
        unsigned long mem_clk;
    #if defined(CONFIG_LCD) || defined(CONFIG_VIDEO)
        unsigned long fb_base;		/* Base address of framebuffer mem */
    #endif
    #if defined(CONFIG_POST)
        unsigned long post_log_word;	/* Record POST activities */
        unsigned long post_log_res;	/* success of POST test */
        unsigned long post_init_f_time;	/* When post_init_f started */
    #endif
    #ifdef CONFIG_BOARD_TYPES
        unsigned long board_type;
    #endif
        unsigned long have_console;	/* serial_init() was called */
    #if CONFIG_IS_ENABLED(PRE_CONSOLE_BUFFER)
        unsigned long precon_buf_idx;	/* Pre-Console buffer index */
    #endif
        unsigned long env_addr;		/* Address  of Environment struct */
        unsigned long env_valid;	/* Environment valid? enum env_valid */
        unsigned long env_has_init;	/* Bitmask of boolean of struct env_location offsets */
        int env_load_prio;		/* Priority of the loaded environment */

        unsigned long ram_base;		/* Base address of RAM used by U-Boot */
        unsigned long ram_top;		/* Top address of RAM used by U-Boot */
        unsigned long relocaddr;	/* Start address of U-Boot in RAM */
        phys_size_t ram_size;		/* RAM size */
        unsigned long mon_len;		/* monitor len */
        unsigned long irq_sp;		/* irq stack pointer */
        unsigned long start_addr_sp;	/* start_addr_stackpointer */
        unsigned long reloc_off;
        struct global_data *new_gd;	/* relocated global data */

    #ifdef CONFIG_DM
        struct udevice	*dm_root;	/* Root instance for Driver Model */
        struct udevice	*dm_root_f;	/* Pre-relocation root instance */
        struct list_head uclass_root;	/* Head of core tree */
    #endif
    #ifdef CONFIG_TIMER
        struct udevice	*timer;		/* Timer instance for Driver Model */
    #endif

        const void *fdt_blob;		/* Our device tree, NULL if none */
        void *new_fdt;			/* Relocated FDT */
        unsigned long fdt_size;		/* Space reserved for relocated FDT */
    #ifdef CONFIG_OF_LIVE
        struct device_node *of_root;
    #endif
        struct jt_funcs *jt;		/* jump table */
        char env_buf[32];		/* buffer for env_get() before reloc. */
    #ifdef CONFIG_TRACE
        void		*trace_buff;	/* The trace buffer */
    #endif
    #if defined(CONFIG_SYS_I2C)
        int		cur_i2c_bus;	/* current used i2c bus */
    #endif
    #ifdef CONFIG_SYS_I2C_MXC
        void *srdata[10];
    #endif
        unsigned int timebase_h;
        unsigned int timebase_l;
    #if CONFIG_VAL(SYS_MALLOC_F_LEN)
        unsigned long malloc_base;	/* base address of early malloc() */
        unsigned long malloc_limit;	/* limit address */
        unsigned long malloc_ptr;	/* current address */
    #endif
    #ifdef CONFIG_PCI
        struct pci_controller *hose;	/* PCI hose for early use */
        phys_addr_t pci_ram_top;	/* top of region accessible to PCI */
    #endif
    #ifdef CONFIG_PCI_BOOTDELAY
        int pcidelay_done;
    #endif
        struct udevice *cur_serial_dev;	/* current serial device */
        struct arch_global_data arch;	/* architecture-specific data */
    #ifdef CONFIG_CONSOLE_RECORD
        struct membuff console_out;	/* console output */
        struct membuff console_in;	/* console input */
    #endif
    #ifdef CONFIG_DM_VIDEO
        ulong video_top;		/* Top of video frame buffer area */
        ulong video_bottom;		/* Bottom of video frame buffer area */
    #endif
    #ifdef CONFIG_BOOTSTAGE
        struct bootstage_data *bootstage;	/* Bootstage information */
        struct bootstage_data *new_bootstage;	/* Relocated bootstage info */
    #endif
    #ifdef CONFIG_LOG
        int log_drop_count;		/* Number of dropped log messages */
        int default_log_level;		/* For devices with no filters */
        struct list_head log_head;	/* List of struct log_device */
        int log_fmt;			/* Mask containing log format info */
    #endif
    } gd_t;


在 `arch/arm/include/asm/global_data.h`

::

	#ifdef CONFIG_ARM64
	#define DECLARE_GLOBAL_DATA_PTR     register volatile gd_t *gd asm ("x18")
	#else
	#define DECLARE_GLOBAL_DATA_PTR     register volatile gd_t *gd asm ("r9")
	#endif
	#endif

在需要使用gd指针的时候,只需要加入DECLARE_GLOBAL_DATA_PTR这句话就可以了,可以知道gd指针始终是放在r9或者x18中的

其中的第一个变量,bd_t结构体，定义在 `include/asm-generic/u-boot.h` 中

::

	typedef struct bd_info {
		unsigned long	bi_memstart;	/* start of DRAM memory */
		phys_size_t	bi_memsize;	/* size	 of DRAM memory in bytes */
		unsigned long	bi_flashstart;	/* start of FLASH memory */
		unsigned long	bi_flashsize;	/* size	 of FLASH memory */
		unsigned long	bi_flashoffset; /* reserved area for startup monitor */
		unsigned long	bi_sramstart;	/* start of SRAM memory */
		unsigned long	bi_sramsize;	/* size	 of SRAM memory */
	#ifdef CONFIG_ARM
		unsigned long	bi_arm_freq; /* arm frequency */
		unsigned long	bi_dsp_freq; /* dsp core frequency */
		unsigned long	bi_ddr_freq; /* ddr frequency */
	#endif
	#if defined(CONFIG_MPC8xx) || defined(CONFIG_E500) || defined(CONFIG_MPC86xx)
		unsigned long	bi_immr_base;	/* base of IMMR register */
	#endif
	#if defined(CONFIG_M68K)
		unsigned long	bi_mbar_base;	/* base of internal registers */
	#endif
	#if defined(CONFIG_MPC83xx)
		unsigned long	bi_immrbar;
	#endif
		unsigned long	bi_bootflags;	/* boot / reboot flag (Unused) */
		unsigned long	bi_ip_addr;	/* IP Address */
		unsigned char	bi_enetaddr[6];	/* OLD: see README.enetaddr */
		unsigned short	bi_ethspeed;	/* Ethernet speed in Mbps */
		unsigned long	bi_intfreq;	/* Internal Freq, in MHz */
		unsigned long	bi_busfreq;	/* Bus Freq, in MHz */
	#if defined(CONFIG_CPM2)
		unsigned long	bi_cpmfreq;	/* CPM_CLK Freq, in MHz */
		unsigned long	bi_brgfreq;	/* BRG_CLK Freq, in MHz */
		unsigned long	bi_sccfreq;	/* SCC_CLK Freq, in MHz */
		unsigned long	bi_vco;		/* VCO Out from PLL, in MHz */
	#endif
	#if defined(CONFIG_M68K)
		unsigned long	bi_ipbfreq;	/* IPB Bus Freq, in MHz */
		unsigned long	bi_pcifreq;	/* PCI Bus Freq, in MHz */
	#endif
	#if defined(CONFIG_EXTRA_CLOCK)
		unsigned long bi_inpfreq;	/* input Freq in MHz */
		unsigned long bi_vcofreq;	/* vco Freq in MHz */
		unsigned long bi_flbfreq;	/* Flexbus Freq in MHz */
	#endif

	#ifdef CONFIG_HAS_ETH1
		unsigned char   bi_enet1addr[6];	/* OLD: see README.enetaddr */
	#endif
	#ifdef CONFIG_HAS_ETH2
		unsigned char	bi_enet2addr[6];	/* OLD: see README.enetaddr */
	#endif
	#ifdef CONFIG_HAS_ETH3
		unsigned char   bi_enet3addr[6];	/* OLD: see README.enetaddr */
	#endif
	#ifdef CONFIG_HAS_ETH4
		unsigned char   bi_enet4addr[6];	/* OLD: see README.enetaddr */
	#endif
	#ifdef CONFIG_HAS_ETH5
		unsigned char   bi_enet5addr[6];	/* OLD: see README.enetaddr */
	#endif

		ulong	        bi_arch_number;	/* unique id for this board */
		ulong	        bi_boot_params;	/* where this board expects params */
	#ifdef CONFIG_NR_DRAM_BANKS
		struct {			/* RAM configuration */
			phys_addr_t start;
			phys_size_t size;
		} bi_dram[CONFIG_NR_DRAM_BANKS];
	#endif /* CONFIG_NR_DRAM_BANKS */
	} bd_t;

bd_t中的变量 `bi_boot_params` 表示传递给内核的参数的位置，u-boot中命令bdinfo也是查看该结构体的值

global data介绍及背后的思考
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

要理解global data的意义，需要理解以下的事实:

u-boot是一个bootloader，有些情况下他可能位于系统的只读存储器(rom或者flash)中，并从那里开始执行。因此，这种情况下，在uboot执行的前期(在将自己copy到可读写的存储器之前)它所在
的存储空间是不可写的，这会有两个问题:

- 堆栈无法使用，无法执行函数调用，也就是说C环境不可用
- 没有data段(或正确初始化的data段)可用,不同函数或者代码之间，无法通过全局变量的形式共享数据

针对问题一，通常的解决方案是：

u-boot运行起来之后，在那些不需要执行任何初始化动作即可使用的、可读写的存储区域开辟一段堆栈(stack)空间。一般来说，大部分的平台都有自己的sram可用作堆栈空间，如果实在不行，也可借用
CPU的data cache方法

针对问题二,解决方案要稍微复杂一些

首先对于开发者而言，在u-boot被拷贝到可读写的ram(这个动作被称作relacation)之前，永远不要使用全局变量，其次在relocation之前不同模块之间确实有通过全局变量传递数据的需求怎么办，这就是
global data需要解决的事情。。

为了在relocation之前通过全局变量的形式传递数据，u-boot设计了一个巧妙的方法:在堆栈配置好之后，在堆栈开始的位置，为struct global_data预留空间，并将开始地址(就是一个struct global_data指针)保存在
一个寄存器中，后续的传递，都是通过保存在寄存器中的指针实现。对于arm64平台而言,该指针保存在了X18寄存器中

在 `arch/arm/lib/crt0_64.S` 中有如下实现

::

	bl board_init_f_alloc_reserve	//board_init_f_alloc_reserve的返回值(x0)就是global data的指针
	mov sp,x0
	/* set up gd here, outside any C code */
	mv x18,x0
    bl board_init_init_reserve

内核参数链表的格式和说明可以从内核源码目录 `arch/arm/include/asm/setup.h` 中找到，链表必须以ATAG_CORE开始，以ATAG_NONE结束

::

	struct tag {
		struct tag_header hdr;
		union {
			struct tag_core		core;
			struct tag_mem32	mem;
			struct tag_videotext	videotext;
			struct tag_ramdisk	ramdisk;
			struct tag_initrd	initrd;
			struct tag_serialnr	serialnr;
			struct tag_revision	revision;
			struct tag_videolfb	videolfb;
			struct tag_cmdline	cmdline;

			/*
			 * Acorn specific
			 */
			struct tag_acorn	acorn;

			/*
			 * DC21285 specific
			 */
			struct tag_memclk	memclk;
		} u;
	};

	struct tag_ramdisk {
		u32 flags;	/* bit 0 = load, bit 1 = prompt */
		u32 size;	/* decompressed ramdisk size in _kilo_ bytes */
		u32 start;	/* starting block of floppy-based RAM disk image */
	};

	struct tag_cmdline {
		char	cmdline[1];	/* this is the minimum size */
	};

	...

参数结构包括两个部分，一个是tag_header, 一个是u联合体

tag_header结构体定义如下，

::

	struct tag_header {
		u32 size;	//表示整个tag结构体的大小，用字的个数表示而不是字节，等于tag_header加上u联合体的大小
		u32 tag;	//整个tag结构体的标记，如ATAG_CORE
	};


现在来分析boot_prep_linux函数

::

    /* Subcommand: PREP */
    static void boot_prep_linux(bootm_headers_t *images)
    {
        char *commandline = env_get("bootargs");    //获取环境变量bootargs,这就是要传递给kernel的参数

        if (IMAGE_ENABLE_OF_LIBFDT && images->ft_len) {
    #ifdef CONFIG_OF_LIBFDT
            debug("using: FDT\n");
            if (image_setup_linux(images)) {
                printf("FDT creation failed! hanging...");
                hang();
            }
    #endif
        } else if (BOOTM_ENABLE_TAGS) {
            debug("using: ATAGS\n");
            setup_start_tag(gd->bd);	//通过bd结构体中的参数在内存中的存放位置gd->bd->bi_boot_params来构建初始化tag结构,
										//表明参数结构的开始
            if (BOOTM_ENABLE_SERIAL_TAG)
                setup_serial_tag(&params);	//构建串口参数的tag结构
            if (BOOTM_ENABLE_CMDLINE_TAG)
                setup_commandline_tag(gd->bd, commandline);	//构建命令行参数的tag结构
            if (BOOTM_ENABLE_REVISION_TAG)
                setup_revision_tag(&params);
            if (BOOTM_ENABLE_MEMORY_TAGS)
                setup_memory_tags(gd->bd);
            if (BOOTM_ENABLE_INITRD_TAG) {
                /*
                 * In boot_ramdisk_high(), it may relocate ramdisk to
                 * a specified location. And set images->initrd_start &
                 * images->initrd_end to relocated ramdisk's start/end
                 * addresses. So use them instead of images->rd_start &
                 * images->rd_end when possible.
                 */
                if (images->initrd_start && images->initrd_end) {
                    setup_initrd_tag(gd->bd, images->initrd_start,
                             images->initrd_end);
                } else if (images->rd_start && images->rd_end) {
                    setup_initrd_tag(gd->bd, images->rd_start,
                             images->rd_end);
                }
            }
            setup_board_tags(&params);
            setup_end_tag(gd->bd);
        } else {
            printf("FDT and ATAGS support not compiled in - hanging\n");
            hang();
        }
    }

- setup_start_tag

::

	static void setup_start_tag (bd_t *bd)
	{
		params = (struct tag *)bd->bi_boot_params;	//获取struct tag指针

		params->hdr.tag = ATAG_CORE;	//设置参数链表开始标签
		params->hdr.size = tag_size (tag_core);

		params->u.core.flags = 0;
		params->u.core.pagesize = 0;
		params->u.core.rootdev = 0;

		params = tag_next (params);
	}
	#define tag_next(t)	((struct tag *)((u32 *)(t) + (t)->hdr.size))

- setup_commandline_tag

::

	static void setup_commandline_tag(bd_t *bd, char *commandline)
	{
		char *p;
	printf("set cmd line ...\n");
		if (!commandline)
			return;

		/* eat leading white space */
		for (p = commandline; *p == ' '; p++);

		/* skip non-existent command lines so the kernel will still
		 * use its default command line.
		 */
		if (*p == '\0')
			return;

		params->hdr.tag = ATAG_CMDLINE;
		params->hdr.size =
			(sizeof (struct tag_header) + strlen (p) + 1 + 4) >> 2;

		strcpy (params->u.cmdline.cmdline, p);

		params = tag_next (params);
	}

设备树传参
-----------

新版本的linux内核都采用设备树的方式进行板级设备信息描述，uboot在启动内核的时候需要将设备树的地址传递给kernel。跟以前的方式不同，采用设备树时
不再使用struct tag进行参数传递，设备数中本身有对需要传递参数的描述，uboot中将设备树进行解析并设置对应参数。kernel直接解析uboot传递的设备树并从中
找到要传递参数

boot_prep_linux函数中有两个主分支，定义设备树时运行分支一,没有定义时采用struct tag进行参数传递

::

    int image_setup_linux(bootm_headers_t *images)
    {
        ulong of_size = images->ft_len;
        char **of_flat_tree = &images->ft_addr;
        struct lmb *lmb = &images->lmb;
        int ret;

        if (IMAGE_ENABLE_OF_LIBFDT)
            boot_fdt_add_mem_rsv_regions(lmb, *of_flat_tree);

        if (IMAGE_BOOT_GET_CMDLINE) {
            ret = boot_get_cmdline(lmb, &images->cmdline_start,
                    &images->cmdline_end);
            if (ret) {
                puts("ERROR with allocation of cmdline\n");
                return ret;
            }
        }

        if (IMAGE_ENABLE_OF_LIBFDT) {
            ret = boot_relocate_fdt(lmb, of_flat_tree, &of_size);
            if (ret)
                return ret;
        }

        if (IMAGE_ENABLE_OF_LIBFDT && of_size) {
            ret = image_setup_libfdt(images, *of_flat_tree, of_size, lmb);  //此函数中会调用fdt_chosen进行参数传递
            if (ret)
                return ret;
        }

        return 0;
    }

    int fdt_chosen(void *fdt)
    {
        int   nodeoffset;
        int   err;
        char  *str;		/* used to set string properties */

        err = fdt_check_header(fdt);
        if (err < 0) {
            printf("fdt_chosen: %s\n", fdt_strerror(err));
            return err;
        }

        /* find or create "/chosen" node. */
        nodeoffset = fdt_find_or_add_subnode(fdt, 0, "chosen");
        if (nodeoffset < 0)
            return nodeoffset;
        str = env_get("bootargs");
        if (str) {
            err = fdt_setprop(fdt, nodeoffset, "bootargs", str,
                      strlen(str) + 1);
            if (err < 0) {
                printf("WARNING: could not set bootargs %s.\n",
                       fdt_strerror(err));
                return err;
            }
        }

        return fdt_fixup_stdout(fdt, nodeoffset);
    }
