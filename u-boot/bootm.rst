bootm原理
=========

基础知识
---------

- vmlinux

  vmlinux是可引导的，可压缩的内核镜像，vm代表virtual memory。vmlinux是elf格式的文件，是最原始的内核文件

- Image

  Image是经过objcopy处理的只包含二进制数据的内核代码，它已经不是elf格式了，但是还没有经过压缩

- zImage

  Image经过gzip压缩得到zImage
  
- uImage
  
  zImage加上一个64字节的头信息，在头中说明镜像文件的类型，加载位置，生成时间，大小等信息，变生成了uImage

- xipImage

  这种格式的镜像文件多放在nor flash上，且运行时不需要拷贝到内存中，可以直接在nor flash上运行


bootm实现
----------


bootm命令的定义

::

    U_BOOT_CMD(
        bootm,	CONFIG_SYS_MAXARGS,	1,	do_bootm,
        "boot application image from memory", bootm_help_text
    );


**bootm主函数**

::

    /*******************************************************************/
    /* bootm - boot application image from image in memory */
    /*******************************************************************/

    int do_bootm(cmd_tbl_t *cmdtp, int flag, int argc, char * const argv[])
    {
    #ifdef CONFIG_NEEDS_MANUAL_RELOC   //没定义
        static int relocated = 0;

        if (!relocated) {
            int i;

            /* relocate names of sub-command table */
            for (i = 0; i < ARRAY_SIZE(cmd_bootm_sub); i++)
                cmd_bootm_sub[i].name += gd->reloc_off;

            relocated = 1;
        }
    #endif

        /* determine if we have a sub command */
        argc--; argv++;
        if (argc > 0) {     //假设我们传了一个参数"0x10000000"
            char *endp;

            simple_strtoul(argv[0], &endp, 16);
            /* endp pointing to NULL means that argv[0] was just a
             * valid number, pass it along to the normal bootm processing
             *
             * If endp is ':' or '#' assume a FIT identifier so pass
             * along for normal processing.
             *
             * Right now we assume the first arg should never be '-'
             */
            if ((*endp != 0) && (*endp != ':') && (*endp != '#'))
                return do_bootm_subcommand(cmdtp, flag, argc, argv);
        }

        return do_bootm_states(cmdtp, flag, argc, argv, BOOTM_STATE_START |
            BOOTM_STATE_FINDOS | BOOTM_STATE_FINDOTHER |
            BOOTM_STATE_LOADOS |
    #ifdef CONFIG_SYS_BOOT_RAMDISK_HIGH
            BOOTM_STATE_RAMDISK |
    #endif
    #if defined(CONFIG_PPC) || defined(CONFIG_MIPS)
            BOOTM_STATE_OS_CMDLINE |
    #endif
            BOOTM_STATE_OS_PREP | BOOTM_STATE_OS_FAKE_GO |
            BOOTM_STATE_OS_GO, &images, 1);     //images是一个比较重要的全局变量
    }


下面列出bootm_headers的内容，等会一个一个填充


- do_bootm_states函数

::

    /**
     * Execute selected states of the bootm command.
     *
     * Note the arguments to this state must be the first argument, Any 'bootm'
     * or sub-command arguments must have already been taken.
     *
     * Note that if states contains more than one flag it MUST contain
     * BOOTM_STATE_START, since this handles and consumes the command line args.
     *
     * Also note that aside from boot_os_fn functions and bootm_load_os no other
     * functions we store the return value of in 'ret' may use a negative return
     * value, without special handling.
     *
     * @param cmdtp		Pointer to bootm command table entry
     * @param flag		Command flags (CMD_FLAG_...)
     * @param argc		Number of subcommand arguments (0 = no arguments)
     * @param argv		Arguments
     * @param states	Mask containing states to run (BOOTM_STATE_...)
     * @param images	Image header information
     * @param boot_progress 1 to show boot progress, 0 to not do this
     * @return 0 if ok, something else on error. Some errors will cause this
     *	function to perform a reboot! If states contains BOOTM_STATE_OS_GO
     *	then the intent is to boot an OS, so this function will not return
     *	unless the image type is standalone.
     */
    int do_bootm_states(cmd_tbl_t *cmdtp, int flag, int argc, char * const argv[],
                int states, bootm_headers_t *images, int boot_progress)
    {
        boot_os_fn *boot_fn;
        ulong iflag = 0;
        int ret = 0, need_boot_fn;

        images->state |= states;        //将传入的state赋值给image

        /*
         * Work through the states and see how far we get. We stop on
         * any error.
         */
        if (states & BOOTM_STATE_START)
            ret = bootm_start(cmdtp, flag, argc, argv);

        if (!ret && (states & BOOTM_STATE_FINDOS))
            ret = bootm_find_os(cmdtp, flag, argc, argv);

        if (!ret && (states & BOOTM_STATE_FINDOTHER))
            ret = bootm_find_other(cmdtp, flag, argc, argv);

        /* Load the OS */
        if (!ret && (states & BOOTM_STATE_LOADOS)) {
            iflag = bootm_disable_interrupts();     //关中断
            ret = bootm_load_os(images, 0);         //加载os
            if (ret && ret != BOOTM_ERR_OVERLAP)
                goto err;
            else if (ret == BOOTM_ERR_OVERLAP)
                ret = 0;
        }

        /* Relocate the ramdisk */
    #ifdef CONFIG_SYS_BOOT_RAMDISK_HIGH         //没定义
        if (!ret && (states & BOOTM_STATE_RAMDISK)) {
            ulong rd_len = images->rd_end - images->rd_start;

            ret = boot_ramdisk_high(&images->lmb, images->rd_start,
                rd_len, &images->initrd_start, &images->initrd_end);
            if (!ret) {
                env_set_hex("initrd_start", images->initrd_start);
                env_set_hex("initrd_end", images->initrd_end);
            }
        }
    #endif
    #if IMAGE_ENABLE_OF_LIBFDT && defined(CONFIG_LMB)
        if (!ret && (states & BOOTM_STATE_FDT)) {
            boot_fdt_add_mem_rsv_regions(&images->lmb, images->ft_addr);
            ret = boot_relocate_fdt(&images->lmb, &images->ft_addr,
                        &images->ft_len);
        }
    #endif

        /* From now on, we need the OS boot function */
        if (ret)
            return ret;
        boot_fn = bootm_os_get_boot_func(images->os.os);        //得到我们要运行的os函数
        need_boot_fn = states & (BOOTM_STATE_OS_CMDLINE |
                BOOTM_STATE_OS_BD_T | BOOTM_STATE_OS_PREP |
                BOOTM_STATE_OS_FAKE_GO | BOOTM_STATE_OS_GO);
        if (boot_fn == NULL && need_boot_fn) {
            if (iflag)
                enable_interrupts();
            printf("ERROR: booting os '%s' (%d) is not supported\n",
                   genimg_get_os_name(images->os.os), images->os.os);
            bootstage_error(BOOTSTAGE_ID_CHECK_BOOT_OS);
            return 1;
        }


        /* Call various other states that are not generally used */
        if (!ret && (states & BOOTM_STATE_OS_CMDLINE))
            ret = boot_fn(BOOTM_STATE_OS_CMDLINE, argc, argv, images);
        if (!ret && (states & BOOTM_STATE_OS_BD_T))
            ret = boot_fn(BOOTM_STATE_OS_BD_T, argc, argv, images);
        if (!ret && (states & BOOTM_STATE_OS_PREP)) {
    #if defined(CONFIG_SILENT_CONSOLE) && !defined(CONFIG_SILENT_U_BOOT_ONLY)
            if (images->os.os == IH_OS_LINUX)
                fixup_silent_linux();
    #endif
            ret = boot_fn(BOOTM_STATE_OS_PREP, argc, argv, images); //根据state状态的传入,这里会执行
        }

    #ifdef CONFIG_TRACE     //没定义
        /* Pretend to run the OS, then run a user command */
        if (!ret && (states & BOOTM_STATE_OS_FAKE_GO)) {
            char *cmd_list = env_get("fakegocmd");

            ret = boot_selected_os(argc, argv, BOOTM_STATE_OS_FAKE_GO,
                    images, boot_fn);
            if (!ret && cmd_list)
                ret = run_command_list(cmd_list, -1, flag);
        }
    #endif

        /* Check for unsupported subcommand. */
        if (ret) {
            puts("subcommand not supported\n");
            return ret;
        }

        /* Now run the OS! We hope this doesn't return */
        if (!ret && (states & BOOTM_STATE_OS_GO))
            ret = boot_selected_os(argc, argv, BOOTM_STATE_OS_GO,
                    images, boot_fn);

        /* Deal with any fallout */
    err:
        if (iflag)
            enable_interrupts();

        if (ret == BOOTM_ERR_UNIMPLEMENTED)
            bootstage_error(BOOTSTAGE_ID_DECOMP_UNIMPL);
        else if (ret == BOOTM_ERR_RESET)
            do_reset(cmdtp, flag, argc, argv);

        return ret;
    }


**bootm_start**

- boot_start函数

::

    static int bootm_start(cmd_tbl_t *cmdtp, int flag, int argc,
                   char * const argv[])
    {
        memset((void *)&images, 0, sizeof(images)); //将全局变量images清0，包括设置的states
        images.verify = env_get_yesno("verify");    //得到环境变量verify，定义为n表示不对zImage进行crc校验，y则校验

        boot_start_lmb(&images);    //没定义CONFIG_LMB,空函数

        bootstage_mark_name(BOOTSTAGE_ID_BOOTM_START, "bootm_start");
        images.state = BOOTM_STATE_START;   //标记状态

        return 0;
    }

**bootm_find_os**

- boot_find_os

::

    static int bootm_find_os(cmd_tbl_t *cmdtp, int flag, int argc,
                 char * const argv[])
    {
        const void *os_hdr;
        bool ep_found = false;
        int ret;

        /* get kernel image header, start address and length */
        os_hdr = boot_get_kernel(cmdtp, flag, argc, argv,
                &images, &images.os.image_start, &images.os.image_len);
        if (images.os.image_len == 0) {
            puts("ERROR: can't get kernel image!\n");
            return 1;
        }

        /* get image parameters */
        switch (genimg_get_format(os_hdr)) {
    #if defined(CONFIG_IMAGE_FORMAT_LEGACY)
        case IMAGE_FORMAT_LEGACY:
            images.os.type = image_get_type(os_hdr);    //填充各种os信息
            images.os.comp = image_get_comp(os_hdr);
            images.os.os = image_get_os(os_hdr);

            images.os.end = image_get_image_end(os_hdr);
            images.os.load = image_get_load(os_hdr);
            images.os.arch = image_get_arch(os_hdr);
            break;
    #endif
    #if IMAGE_ENABLE_FIT
        case IMAGE_FORMAT_FIT:
            if (fit_image_get_type(images.fit_hdr_os,
                           images.fit_noffset_os,
                           &images.os.type)) {
                puts("Can't get image type!\n");
                bootstage_error(BOOTSTAGE_ID_FIT_TYPE);
                return 1;
            }

            if (fit_image_get_comp(images.fit_hdr_os,
                           images.fit_noffset_os,
                           &images.os.comp)) {
                puts("Can't get image compression!\n");
                bootstage_error(BOOTSTAGE_ID_FIT_COMPRESSION);
                return 1;
            }

            if (fit_image_get_os(images.fit_hdr_os, images.fit_noffset_os,
                         &images.os.os)) {
                puts("Can't get image OS!\n");
                bootstage_error(BOOTSTAGE_ID_FIT_OS);
                return 1;
            }

            if (fit_image_get_arch(images.fit_hdr_os,
                           images.fit_noffset_os,
                           &images.os.arch)) {
                puts("Can't get image ARCH!\n");
                return 1;
            }

            images.os.end = fit_get_end(images.fit_hdr_os);

            if (fit_image_get_load(images.fit_hdr_os, images.fit_noffset_os,
                           &images.os.load)) {
                puts("Can't get image load address!\n");
                bootstage_error(BOOTSTAGE_ID_FIT_LOADADDR);
                return 1;
            }
            break;
    #endif
    #ifdef CONFIG_ANDROID_BOOT_IMAGE
        case IMAGE_FORMAT_ANDROID:
            images.os.type = IH_TYPE_KERNEL;
            images.os.comp = IH_COMP_GZIP;
            images.os.os = IH_OS_LINUX;

            images.os.end = android_image_get_end(os_hdr);
            images.os.load = android_image_get_kload(os_hdr);
            images.ep = images.os.load;
            ep_found = true;
            break;
    #endif
        default:
            puts("ERROR: unknown image format type!\n");
            return 1;
        }

        /* If we have a valid setup.bin, we will use that for entry (x86) */
        if (images.os.arch == IH_ARCH_I386 ||
            images.os.arch == IH_ARCH_X86_64) {
            ulong len;

            ret = boot_get_setup(&images, IH_ARCH_I386, &images.ep, &len);
            if (ret < 0 && ret != -ENOENT) {
                puts("Could not find a valid setup.bin for x86\n");
                return 1;
            }
            /* Kernel entry point is the setup.bin */
        } else if (images.legacy_hdr_valid) {
            images.ep = image_get_ep(&images.legacy_hdr_os_copy);   //对ep进行赋值
    #if IMAGE_ENABLE_FIT
        } else if (images.fit_uname_os) {
            int ret;

            ret = fit_image_get_entry(images.fit_hdr_os,
                          images.fit_noffset_os, &images.ep);
            if (ret) {
                puts("Can't get entry point property!\n");
                return 1;
            }
    #endif
        } else if (!ep_found) {
            puts("Could not find kernel entry point!\n");
            return 1;
        }

        if (images.os.type == IH_TYPE_KERNEL_NOLOAD) {
            if (CONFIG_IS_ENABLED(CMD_BOOTI) &&
                images.os.arch == IH_ARCH_ARM64) {
                ulong image_addr;
                ulong image_size;

                ret = booti_setup(images.os.image_start, &image_addr,
                          &image_size, true);
                if (ret != 0)
                    return 1;

                images.os.type = IH_TYPE_KERNEL;
                images.os.load = image_addr;
                images.ep = image_addr;
            } else {
                images.os.load = images.os.image_start;
                images.ep += images.os.image_start;
            }
        }

        images.os.start = map_to_sysmem(os_hdr);    //设置os.start

        return 0;
    }

- image_get_kern

image_get_kern 在boot_get_kern中调用

::

    /**
     * image_get_kernel - verify legacy format kernel image
     * @img_addr: in RAM address of the legacy format image to be verified
     * @verify: data CRC verification flag
     *
     * image_get_kernel() verifies legacy image integrity and returns pointer to
     * legacy image header if image verification was completed successfully.
     *
     * returns:
     *     pointer to a legacy image header if valid image was found
     *     otherwise return NULL
     */
    static image_header_t *image_get_kernel(ulong img_addr, int verify)
    {
        image_header_t *hdr = (image_header_t *)img_addr;

        if (!image_check_magic(hdr)) {  //魔数校验
            puts("Bad Magic Number\n");
            bootstage_error(BOOTSTAGE_ID_CHECK_MAGIC);
            return NULL;
        }
        bootstage_mark(BOOTSTAGE_ID_CHECK_HEADER);

        if (!image_check_hcrc(hdr)) {   //前64字节的crc校验
            puts("Bad Header Checksum\n");
            bootstage_error(BOOTSTAGE_ID_CHECK_HEADER);
            return NULL;
        }

        bootstage_mark(BOOTSTAGE_ID_CHECK_CHECKSUM);
        image_print_contents(hdr);  //打印头信息

        if (verify) {       //环境变量中会设置verify来决定是否需要校验
            puts("   Verifying Checksum ... ");
            if (!image_check_dcrc(hdr)) {
                printf("Bad Data CRC\n");
                bootstage_error(BOOTSTAGE_ID_CHECK_CHECKSUM);
                return NULL;
            }
            puts("OK\n");
        }
        bootstage_mark(BOOTSTAGE_ID_CHECK_ARCH);

        if (!image_check_target_arch(hdr)) {        //体系结构校验
            printf("Unsupported Architecture 0x%x\n", image_get_arch(hdr));
            bootstage_error(BOOTSTAGE_ID_CHECK_ARCH);
            return NULL;
        }
        return hdr;
    }


- image_print_contents

image_print_contents打印uimage头信息

::

    void image_print_contents(const void *ptr)
    {
        const image_header_t *hdr = (const image_header_t *)ptr;
        const char __maybe_unused *p;

        p = IMAGE_INDENT_STRING;
        printf("%sImage Name:   %.*s\n", p, IH_NMLEN, image_get_name(hdr));
        if (IMAGE_ENABLE_TIMESTAMP) {
            printf("%sCreated:      ", p);
            genimg_print_time((time_t)image_get_time(hdr));
        }
        printf("%sImage Type:   ", p);  //打印image类型提示符
        image_print_type(hdr);          //实际打印image类型
        printf("%sData Size:    ", p);
        genimg_print_size(image_get_data_size(hdr));
        printf("%sLoad Address: %08x\n", p, image_get_load(hdr));
        printf("%sEntry Point:  %08x\n", p, image_get_ep(hdr));

        if (image_check_type(hdr, IH_TYPE_MULTI) ||
                image_check_type(hdr, IH_TYPE_SCRIPT)) {
            int i;
            ulong data, len;
            ulong count = image_multi_count(hdr);

            printf("%sContents:\n", p);
            for (i = 0; i < count; i++) {
                image_multi_getimg(hdr, i, &data, &len);

                printf("%s   Image %d: ", p, i);
                genimg_print_size(len);

                if (image_check_type(hdr, IH_TYPE_SCRIPT) && i > 0) {
                    /*
                     * the user may need to know offsets
                     * if planning to do something with
                     * multiple files
                     */
                    printf("%s    Offset = 0x%08lx\n", p, data);
                }
            }
        } else if (image_check_type(hdr, IH_TYPE_FIRMWARE_IVT)) {
            printf("HAB Blocks:   0x%08x   0x0000   0x%08x\n",
                    image_get_load(hdr) - image_get_header_size(),
                    image_get_size(hdr) + image_get_header_size()
                            - 0x1FE0);
        }
    }

**bootm_load_os**

- bootm_load_os

::

    static int bootm_load_os(bootm_headers_t *images, int boot_progress)
    {
        image_info_t os = images->os;
        ulong load = os.load;
        ulong load_end;
        ulong blob_start = os.start;
        ulong blob_end = os.end;
        ulong image_start = os.image_start;
        ulong image_len = os.image_len;
        ulong flush_start = ALIGN_DOWN(load, ARCH_DMA_MINALIGN);
        ulong flush_len;
        bool no_overlap;
        void *load_buf, *image_buf;
        int err;

        load_buf = map_sysmem(load, 0);
        image_buf = map_sysmem(os.image_start, image_len);
        err = bootm_decomp_image(os.comp, load, os.image_start, os.type,
                     load_buf, image_buf, image_len,
                     CONFIG_SYS_BOOTM_LEN, &load_end);      //解压缩zImage
        if (err) {
            bootstage_error(BOOTSTAGE_ID_DECOMP_IMAGE);
            return err;
        }

        flush_len = load_end - load;
        if (flush_start < load)
            flush_len += load - flush_start;

        flush_cache(flush_start, ALIGN(flush_len, ARCH_DMA_MINALIGN));

    #if !(UBOOT_LOG_OPTIMIZE)
        printf("   kernel loaded to 0x%08lx, end = 0x%08lx\n", load, load_end);
    #endif
        bootstage_mark(BOOTSTAGE_ID_KERNEL_LOADED);

        no_overlap = (os.comp == IH_COMP_NONE && load == image_start);

        if (!no_overlap && load < blob_end && load_end > blob_start) {
            debug("images.os.start = 0x%lX, images.os.end = 0x%lx\n",
                  blob_start, blob_end);
            debug("images.os.load = 0x%lx, load_end = 0x%lx\n", load,
                  load_end);

            /* Check what type of image this is. */
            if (images->legacy_hdr_valid) {
                if (image_get_type(&images->legacy_hdr_os_copy)
                        == IH_TYPE_MULTI)
                    puts("WARNING: legacy format multi component image overwritten\n");
                return BOOTM_ERR_OVERLAP;
            } else {
                puts("ERROR: new format image overwritten - must RESET the board to recover\n");
                bootstage_error(BOOTSTAGE_ID_OVERWRITTEN);
                return BOOTM_ERR_RESET;
            }
        }

        lmb_reserve(&images->lmb, images->os.load, (load_end -
                                images->os.load));
        return 0;
    }

**bootm_os_get_boot_func**

- bootm_os_get_boot_func

::

    boot_os_fn *bootm_os_get_boot_func(int os)
    {
    #ifdef CONFIG_NEEDS_MANUAL_RELOC    //没定义不执行
        static bool relocated;

        if (!relocated) {
            int i;

            /* relocate boot function table */
            for (i = 0; i < ARRAY_SIZE(boot_os); i++)
                if (boot_os[i] != NULL)
                    boot_os[i] += gd->reloc_off;

            relocated = true;
        }
    #endif
        return boot_os[os];     //根据os类型返回对应的函数指针
    }

    static boot_os_fn *boot_os[] = {
        [IH_OS_U_BOOT] = do_bootm_standalone,
    #ifdef CONFIG_BOOTM_LINUX
        [IH_OS_LINUX] = do_bootm_linux,
    #endif
    #ifdef CONFIG_BOOTM_NETBSD
        [IH_OS_NETBSD] = do_bootm_netbsd,
    #endif
    #ifdef CONFIG_LYNXKDI
        [IH_OS_LYNXOS] = do_bootm_lynxkdi,
    #endif
    #ifdef CONFIG_BOOTM_RTEMS
        [IH_OS_RTEMS] = do_bootm_rtems,
    #endif
    #if defined(CONFIG_BOOTM_OSE)
        [IH_OS_OSE] = do_bootm_ose,
    #endif
    #if defined(CONFIG_BOOTM_PLAN9)
        [IH_OS_PLAN9] = do_bootm_plan9,
    #endif
    #if defined(CONFIG_BOOTM_VXWORKS) && \
        (defined(CONFIG_PPC) || defined(CONFIG_ARM))
        [IH_OS_VXWORKS] = do_bootm_vxworks,
    #endif
    #if defined(CONFIG_CMD_ELF)
        [IH_OS_QNX] = do_bootm_qnxelf,
    #endif
    #ifdef CONFIG_INTEGRITY
        [IH_OS_INTEGRITY] = do_bootm_integrity,
    #endif
    #ifdef CONFIG_BOOTM_OPENRTOS
        [IH_OS_OPENRTOS] = do_bootm_openrtos,
    #endif
    #ifdef CONFIG_BOOTM_OPTEE
        [IH_OS_TEE] = do_bootm_tee,
    #endif
    };


**boot_selected_os**

- boot_selected_os

::

    int boot_selected_os(int argc, char * const argv[], int state,
                 bootm_headers_t *images, boot_os_fn *boot_fn)
    {
        arch_preboot_os();
        boot_fn(state, argc, argv, images); //执行do_bootm_linux函数

        /* Stand-alone may return when 'autostart' is 'no' */
        if (images->os.type == IH_TYPE_STANDALONE ||
            IS_ENABLED(CONFIG_SANDBOX) ||
            state == BOOTM_STATE_OS_FAKE_GO) /* We expect to return */
            return 0;
        bootstage_error(BOOTSTAGE_ID_BOOT_OS_RETURNED);
        debug("\n## Control returned to monitor - resetting...\n");

        return BOOTM_ERR_RESET;
    }


- do_bootm_linux

::


    int do_bootm_linux(int flag, int argc, char *argv[], bootm_headers_t *images)
    {
        //前面传参flag=BOOTM_STATE_OS_PREP
        /* No need for those on ARC */
        if ((flag & BOOTM_STATE_OS_BD_T) || (flag & BOOTM_STATE_OS_CMDLINE))
            return -1;

        if (flag & BOOTM_STATE_OS_PREP)
            return boot_prep_linux(images);

        if (flag & (BOOTM_STATE_OS_GO | BOOTM_STATE_OS_FAKE_GO)) {
            boot_jump_linux(images, flag);
            return 0;
        }

        return -1;
    }

- boot_prep_linux

::

    static void boot_prep_linux(bootm_headers_t *images)
    {
        char *commandline = env_get("bootargs");    //获取bootargs环境变量

        if (IMAGE_ENABLE_OF_LIBFDT && images->ft_len) {
    #ifdef CONFIG_OF_LIBFDT
            debug("using: FDT\n");
            if (image_setup_linux(images)) {        //设置fdt
                printf("FDT creation failed! hanging...");
                hang();
            }
    #endif
        } else if (BOOTM_ENABLE_TAGS) {
            debug("using: ATAGS\n");
            setup_start_tag(gd->bd);    //设置起始头
            if (BOOTM_ENABLE_SERIAL_TAG)
                setup_serial_tag(&params);  //设置串口信息
            if (BOOTM_ENABLE_CMDLINE_TAG)
                setup_commandline_tag(gd->bd, commandline); //设置命令行参数,重要
            if (BOOTM_ENABLE_REVISION_TAG)
                setup_revision_tag(&params);    //设置版本，不重要
            if (BOOTM_ENABLE_MEMORY_TAGS)
                setup_memory_tags(gd->bd);  //设置内存信息，重要
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
            ret = image_setup_libfdt(images, *of_flat_tree, of_size, lmb);
            if (ret)
                return ret;
        }

        return 0;
    }


- boot_jump_linux 

::

    static void boot_jump_linux(bootm_headers_t *images, int flag)
    {
    #ifdef CONFIG_ARM64
        void (*kernel_entry)(void *fdt_addr, void *res0, void *res1,
                void *res2);
        int fake = (flag & BOOTM_STATE_OS_FAKE_GO);

        kernel_entry = (void (*)(void *fdt_addr, void *res0, void *res1,
                    void *res2))images->ep;

        debug("## Transferring control to Linux (at address %lx)...\n",
            (ulong) kernel_entry);
        bootstage_mark(BOOTSTAGE_ID_RUN_OS);

        announce_and_cleanup(fake);
    #ifdef X2_AUTOBOOT
            boot_stage_mark(3);
    #endif

        if (!fake) {
    #ifdef CONFIG_ARMV8_PSCI
            armv8_setup_psci();
    #endif
            do_nonsec_virt_switch();

            update_os_arch_secondary_cores(images->os.arch);

    #ifdef CONFIG_ARMV8_SWITCH_TO_EL1
            armv8_switch_to_el2((u64)images->ft_addr, 0, 0, 0,
                        (u64)switch_to_el1, ES_TO_AARCH64);
    #else
            if ((IH_ARCH_DEFAULT == IH_ARCH_ARM64) &&
                (images->os.arch == IH_ARCH_ARM))
                armv8_switch_to_el2(0, (u64)gd->bd->bi_arch_number,
                            (u64)images->ft_addr, 0,
                            (u64)images->ep,
                            ES_TO_AARCH32);
            else
                armv8_switch_to_el2((u64)images->ft_addr, 0, 0, 0,
                            images->ep,
                            ES_TO_AARCH64);
    #endif
        }
    #else   // else this armv7, not CONFIG_ARM64
        unsigned long machid = gd->bd->bi_arch_number;
        char *s;
        void (*kernel_entry)(int zero, int arch, uint params);
        unsigned long r2;
        int fake = (flag & BOOTM_STATE_OS_FAKE_GO);

        kernel_entry = (void (*)(int, int, uint))images->ep;
    #ifdef CONFIG_CPU_V7M
        ulong addr = (ulong)kernel_entry | 1;
        kernel_entry = (void *)addr;
    #endif
        s = env_get("machid");
        if (s) {
            if (strict_strtoul(s, 16, &machid) < 0) {
                debug("strict_strtoul failed!\n");
                return;
            }
            printf("Using machid 0x%lx from environment\n", machid);
        }

        debug("## Transferring control to Linux (at address %08lx)" \
            "...\n", (ulong) kernel_entry);
        bootstage_mark(BOOTSTAGE_ID_RUN_OS);
        announce_and_cleanup(fake);

        if (IMAGE_ENABLE_OF_LIBFDT && images->ft_len)
            r2 = (unsigned long)images->ft_addr;
        else
            r2 = gd->bd->bi_boot_params;

        if (!fake) {
    #ifdef CONFIG_ARMV7_NONSEC
            if (armv7_boot_nonsec()) {
                armv7_init_nonsec();
                secure_ram_addr(_do_nonsec_entry)(kernel_entry,
                                  0, machid, r2);
            } else
    #endif
                kernel_entry(0, machid, r2);
        }
    #endif
    }

    __weak void board_jump_and_run(ulong entry, int zero, int arch, uint params)
    {
        void (*kernel_entry)(int zero, int arch, uint params);

        kernel_entry = (void (*)(int, int, uint))entry;

        kernel_entry(zero, arch, params);
    }
