kernel_init
============

0号进程创建1号进程的方式如下

::

    kernel_thread(kernel_init, NULL, CLONE_FS);

1号进程的执行函数就是 ``kernel_init`` ，这个函数定义在 ``init/main.c`` 中,代码实现如下

::

    static int __ref kernel_init(void *unused)
    {
        int ret;

        kernel_init_freeable();
        /* need to finish all async __init code before freeing the memory */
        async_synchronize_full();
        ftrace_free_init_mem();
        free_initmem();
        mark_readonly();

        /*
         * Kernel mappings are now finalized - update the userspace page-table
         * to finalize PTI.
         */
        pti_finalize();

        system_state = SYSTEM_RUNNING;
        numa_default_policy();

        rcu_end_inkernel_boot();

        if (ramdisk_execute_command) {
            ret = run_init_process(ramdisk_execute_command);
            if (!ret)
                return 0;
            pr_err("Failed to execute %s (error %d)\n",
                   ramdisk_execute_command, ret);
        }

        /*
         * We try each of these until one succeeds.
         *
         * The Bourne shell can be used instead of init if we are
         * trying to recover a really broken machine.
         */
        if (execute_command) {
            ret = run_init_process(execute_command);
            if (!ret)
                return 0;
            panic("Requested init %s failed (error %d).",
                  execute_command, ret);
        }
        if (!try_to_run_init_process("/sbin/init") ||
            !try_to_run_init_process("/etc/init") ||
            !try_to_run_init_process("/bin/init") ||
            !try_to_run_init_process("/bin/sh"))
            return 0;

        panic("No working init found.  Try passing init= option to kernel. "
              "See Linux Documentation/admin-guide/init.rst for guidance.");
    }

kernel_init 函数执行内核的部分初始化工作,及系统配置,并创建若干个用于高速缓存和虚拟内存管理的内核线程

init进程
---------

1号进程调用do_execve运行可执行程序init，并演变为用户态1号进程,即init进程。init进程有许多重要的任务,比如启动getty(用于用户登录)、实现运行级别、以及处理孤立进程

0号进程---->1号内核进程---->1号用户进程---->getty进程---->shell进程

内核会在几个位置来查询init,按优先级顺序依次为 1. /sbin/init  2. /etc/init  3./bin/init  4/bin/sh

init程序是一个可以由用户编写的进程,以下是init的几个变种

+-------------------+------------------------------------------------------------------------------------------+
|    init包         |                                  说明                                                    |
+===================+==========================================================================================+
|  sysvinit         |  早期使用的初始化进程工具,目前逐渐淡出linux的历史舞台                                    |
+-------------------+------------------------------------------------------------------------------------------+
|  upstart          |  debian,ubuntu等系统使用的init daemon                                                    |
+-------------------+------------------------------------------------------------------------------------------+
|  systemd          |  systemd是linux中最新的初始化系统(init),可以提高系统的启动速度                           |
+-------------------+------------------------------------------------------------------------------------------+


kerner_init分析
----------------

+------------------------+-----------------------------------------------------------------------------------------------------------------------------+
|   执行流程             |                                           说明                                                                              |
+========================+=============================================================================================================================+
|  kernel_init_freeable  | 完成初始化工作,准备文件系统,准备模块信息                                                                                    |
+------------------------+-----------------------------------------------------------------------------------------------------------------------------+
| async_synchronize_full | 用来加速linux kernel开机的效率                                                                                              |
|                        |                                                                                                                             |
+------------------------+-----------------------------------------------------------------------------------------------------------------------------+
| free_initmem           | free_initmem(in arch/arm/mm/init.c)释放kernel介于__init_begin到__init_end属于init Section的函数的所有内存,并把page个数加到  |
|                        | tatolram_pages中,作为后续kernel在配置mem时可以使用的pages                                                                   |
|                        |                                                                                                                             |
+------------------------+-----------------------------------------------------------------------------------------------------------------------------+
| system_state           | 设置运行状态为SYSTEM_RUNNING                                                                                                |
+------------------------+-----------------------------------------------------------------------------------------------------------------------------+
|                        |  a.如果ramdisk_execute_command不为0就执行该命令为init user process                                                          |
|                        |  b.如果execute_command不为0，就行执行该命令称为init user process                                                            |
| 加载init进程           |  c.依序执行/sbin/init /etc/init /bin/init /bin/sh                                                                           |
|                        |                                                                                                                             |
|                        |                                                                                                                             |
+------------------------+-----------------------------------------------------------------------------------------------------------------------------+

kernel_init_freeable流程分析
----------------------------

::

    static noinline void __init kernel_init_freeable(void)
    {
        /*
         * Wait until kthreadd is all set-up.
         */
        wait_for_completion(&kthreadd_done);
        //等待kernel thread kthreadd(pid=2)创建完毕

        /* Now the scheduler is fully set up and can do blocking allocations */
        gfp_allowed_mask = __GFP_BITS_MASK;
        //设置bitmask,使得init进程可以使用PM并且运行I/O阻塞操作


        /*
         * init can allocate pages on any node
         */
        set_mems_allowed(node_states[N_MEMORY]);
        //分配物理页面

        cad_pid = task_pid(current);
        //设置目前运行进程init的pid号到cad_pid(cad_pid用来接收ctrl-alt-del reboot signal的进程，如果设置cad=1表示可以处理来自ctl-alt-del的动作)，
        //最后会调用ctrl_alt_del(void)函数并确认cad是否为1确定后将执行cad_work=deferred_cad,执行kernel_restart

        smp_prepare_cpus(setup_max_cpus);
        //体系结构相关的函数,实例在arch/arm64/kernel/smp.c中,调用smp_prepare_cpus时会以全局的setup_max_cpus为参数表示在编译核心时设定的CPU最大数量

        workqueue_init();
        //工作者队列初始化

        init_mm_internals();

        do_pre_smp_initcalls();
        //实例在init/main.c中,会透过函数do_one_initcall执行symbol中__initcall_start与__initcall0_start之间的函数
        lockup_detector_init();

        smp_init();
        //实例在kernel/smp.c中,函数主要是bootstrap处理器,运行active多核心架构下的其他处理器
        sched_init_smp();

        page_alloc_init_late();
        /* Initialize page ext after all struct pages are initialized. */
        page_ext_init();

        do_basic_setup();
        //实例在init/main.c中

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
        //函数实现位于drivers/base/init.c中,初始化linux driver system model
        init_irq_proc();
        //初始化/proc/irq与其下的file node
        do_ctors();
        // init/main.c中实现,执行位于__ctors_start和__ctors_end中得代码段
        usermodehelper_enable();
        //kernel/kmod.c中实现,产生khelper workqueue
        do_initcalls();
    }

::

    static void __init do_initcalls(void)
    {
        int level;

        for (level = 0; level < ARRAY_SIZE(initcall_levels) - 1; level++)
            do_initcall_level(level);
    }
    //initcall函数调用,编译到内核中驱动在此函数中加载
