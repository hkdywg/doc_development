linux oops问题分析
====================

Oops是当内核运行时出现严重的错误时，输出的一段包含丰富信息的错误报告，oops可以看成内核级的Segmentation Fault. 例如空指针引用、
非法内存访问、内核堆栈溢出等无法正常处理的错误情况时，就会输出Oops信息

这些信息涵盖了导致出现错误的代码位置，以及当时的寄存器状态，堆栈信息等


linux内核三种异常
--------------------

linux内核三种异常: ``BUG`` 、 ``oops`` 、 ``crash``

BUG
^^^^^^^

BUG是指那些不符合内核的正常设计，但内核能够检测出来并且对系统运行不会产生影响的问题，比如在原子上下文中休眠，在内核中使用BUG标识.

这里的BUG和软件缺陷不是一回事，其实是kernel中用于拦截内核程序超出预期的行为，属于软件主动汇报异常的一种机制。一般来说有两种用到的情况

- 软件开发中，若发现代码逻辑出现致命fault后就可以调用BUG()来让kernel死掉，这样方便定位问题

- 另一种情况是由于某种特殊原因(通常是为了debug而需要抓ramdump)，我们需要 进入kernel panic情况下使用

arm64中BUG()定义如下

::

    #define __BUG_FLAGS(flags)				\
        asm volatile (__stringify(ASM_BUG_FLAGS(flags)));

    #define BUG() do {					\
        __BUG_FLAGS(0);					\
        unreachable();					\
    } while (0)

    
__BUG_FLAGS(0)可翻译为 ``brk 0x800`` 

brk指令会触发一个同步异常，内核异常处理流程中会进入 ``panic()`` ，从而导致kernel panic

oops
^^^^^^

Oops就意味着内核出现异常，此时会将异常时出错的原因，CPU状态、出错的指令地址、数据地址及其他寄存器，函数调用的顺序
甚至栈里面的内容打印出来

例如在编写驱动或者内核模块时，当对指针进行非法取值时导致内核发生一个oops错误。

::

    arch/arm64/mm/fault.c
    static void die_kernel_fault(const char *msg, unsigned long addr,
         unsigned int esr, struct pt_regs *regs)
    {
         bust_spinlocks(1);
         
         pr_alert("Unable to handle kernel %s at virtual address %016lx\n", msg,
         addr);
         
         mem_abort_decode(esr);
         
         show_pte(addr);
         die("Oops", regs, esr);
         bust_spinlocks(0);
         do_exit(SIGKILL);
    }

通过die()会进行oops异常处理。

::

    void die(const char *str, struct pt_regs *regs, int err)
    {
        int ret;
        unsigned long flags;

        raw_spin_lock_irqsave(&die_lock, flags);

        oops_enter();

        console_verbose();
        bust_spinlocks(1);
        ret = __die(str, err, regs);

        if (regs && kexec_should_crash(current))
            crash_kexec(regs);

        bust_spinlocks(0);
        add_taint(TAINT_DIE, LOCKDEP_NOW_UNRELIABLE);
        oops_exit();

        if (in_interrupt())
            panic("Fatal exception in interrupt");
        if (panic_on_oops)
            panic("Fatal exception");

        raw_spin_unlock_irqrestore(&die_lock, flags);

        if (ret != NOTIFY_STOP)
            do_exit(SIGSEGV);
    }

::

    static int __die(const char *str, int err, struct pt_regs *regs)
    {
        static int die_counter;
        int ret;

        pr_emerg("Internal error: %s: %x [#%d]" S_PREEMPT S_SMP "\n",
             str, err, ++die_counter);

        /* trap and error numbers are mostly meaningless on ARM */
        ret = notify_die(DIE_OOPS, str, regs, err, 0, SIGSEGV);
        if (ret == NOTIFY_STOP)
            return ret;

        print_modules();
        show_regs(regs);

        dump_kernel_instr(KERN_EMERG, regs);

        return ret;
    }

- notify_die会通知所有对oops感兴趣的模块并进行callback

- print_modules打印模块状态不为MODULE_STATE_UNFORMED的模块信息

- show_regs打印PC、LR、SP等寄存器信息，同时打印调用堆栈信息

- dump_kernel_instr打印PC指针和前4条指令

panic
^^^^^^^

panic本身时"恐慌"的意思，这里指的是kernel发生了致命错误导致无法继续进行下去的情况。根据实际情况Oops最终也可能会导致panic的发生


::

    void panic(const char *fmt, ...)
    {
        static char buf[1024];
        va_list args;
        long i, i_next = 0, len;
        int state = 0;
        int old_cpu, this_cpu;
         bool _crash_kexec_post_notifiers = crash_kexec_post_notifiers;

        // 禁止本地中断，避免出现死锁，因为无法防止中断处理程序(在获取panic锁后运行),再次调用panic
        local_irq_disable();
        //禁止任务抢占
        preempt_disable_notrace();
        //通过this_cpu确认是否调用panic的cpu是否为panic_cpu
        this_cpu = raw_smp_processor_id();
        old_cpu  = atomic_cmpxchg(&panic_cpu, PANIC_CPU_INVALID, this_cpu);

        if (old_cpu != PANIC_CPU_INVALID && old_cpu != this_cpu)
            panic_smp_self_stop();
        //把console的打印级别放开
        console_verbose();
        bust_spinlocks(1);
        va_start(args, fmt);
        len = vscnprintf(buf, sizeof(buf), fmt, args);
        va_end(args);

        if (len && buf[len - 1] == '\n')
            buf[len - 1] = '\0';
        //解析panic所携带的mesage,
        pr_emerg("Kernel panic - not syncing: %s\n", buf);
    #ifdef CONFIG_DEBUG_BUGVERBOSE
        /*
         * Avoid nested stack-dumping if a panic occurs during oops processing
         */
        if (!test_taint(TAINT_DIE) && oops_in_progress <= 1)
            dump_stack();
    #endif

        //如果kgdb使能，在停掉所有的CPU之前，跳转kgdb断点云南行kgdb_panic
        kgdb_panic(buf);

        //根据当前是否设置了转储内核 (使能CONFIG_KEXEC_CORE)确定是否实际执行转储操作
        //如果执行转储操作会通过kexec将系统切换到新的kdump内核 ，并不会返回
        if (!_crash_kexec_post_notifiers) {
            printk_safe_flush_on_panic();
            __crash_kexec(NULL);

            smp_send_stop();
        } else {
            //停掉其他CPU，只留当前CPU干活
            crash_smp_send_stop();
        }

        //通知所有对panic感兴趣的模块进行回调，添加一些kmsg信息到输出
        atomic_notifier_call_chain(&panic_notifier_list, 0, buf);

        /* Call flush even twice. It tries harder with a single online CPU */
        printk_safe_flush_on_panic();
        //dump内核log buffer中的log信息
        kmsg_dump(KMSG_DUMP_PANIC);

        if (_crash_kexec_post_notifiers)
            __crash_kexec(NULL);

    #ifdef CONFIG_VT
        unblank_screen();
    #endif
        console_unblank();

        //关掉所有debug锁
        debug_locks_off();
        console_flush_on_panic(CONSOLE_FLUSH_PENDING);

        panic_print_sys_info();

        if (!panic_blink)
            panic_blink = no_blink;
        //如果配置了panic_timeout则在超时后重启系统
        if (panic_timeout > 0) {
            pr_emerg("Rebooting in %d seconds..\n", panic_timeout);

            for (i = 0; i < panic_timeout * 1000; i += PANIC_TIMER_STEP) {
                touch_nmi_watchdog();
                if (i >= i_next) {
                    i += panic_blink(state ^= 1);
                    i_next = i + 3600 / PANIC_BLINK_SPD;
                }
                mdelay(PANIC_TIMER_STEP);
            }
        }
        if (panic_timeout != 0) {
            if (panic_reboot_mode != REBOOT_UNDEFINED)
                reboot_mode = panic_reboot_mode;
            emergency_restart();
        }
    #ifdef __sparc__
        {
            extern int stop_a_enabled;
            /* Make sure the user can actually press Stop-A (L1-A) */
            stop_a_enabled = 1;
            pr_emerg("Press Stop-A (L1-A) from sun keyboard or send break\n"
                 "twice on console to return to the boot prom\n");
        }
    #endif
    #if defined(CONFIG_S390)
        disabled_wait();
    #endif
        pr_emerg("---[ end Kernel panic - not syncing: %s ]---\n", buf);

        /* Do not scroll important messages printed above */
        suppress_printk = 1;
        local_irq_enable();
        for (i = 0; ; i += PANIC_TIMER_STEP) {
            touch_softlockup_watchdog();
            if (i >= i_next) {
                i += panic_blink(state ^= 1);
                i_next = i + 3600 / PANIC_BLINK_SPD;
            }
            mdelay(PANIC_TIMER_STEP);
        }
    }

.. note::
    - oops发生时，内核检测到发生了无法恢复的错误，但整个系统可能仍然能够继续运行。典型触发场景为 ``空指针解引用`` 、 ``非法内存访问`` 、 ``某些驱动程序错误`` .
      会产生oops日志，可以通过dmesg看到，如果oops发生在内核关键路径，可能导致内核奔溃

    - panic是比oops更严重的错误，表示系统进入不可恢复的状态，需要立即停止运行。典型触发场景为 ``多次oops触发panic`` 、 ``关键内核数据结构破环`` 、 ``panic显示调用`` 




