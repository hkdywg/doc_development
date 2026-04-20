进程上下文切换
================

当一个进程从内核中移出,另一个进程称为活动的，这些进程之间便发生了上下文切换，操作系统必须记录进程和新进程使之活动的所需要的所有信息.
这些信息称之为上下文，它描述了进程的现有状态,进程上下文是可执行程序代码的重要组成部分,实际上是进程执行活动全过程的静态描述，可以看成
是用户进程传递给内核这些参数以及内核要保存的那一整套的变量和寄存器值和当时的环境等

进程上下文信息包括，指向可执行文件的指针，栈，内存(数据段和堆),进程状态，优先级,程序io状态,授予权限,调度信息，审计信息,有关资源的信息
(文件描述符和读写指针)，事件和信号的信息,寄存器组(栈指针,指令计数器等)等

CPU总是处于以下三种状态之一

1) 内核态，运行于进程上下文，内核代表进程运行于内核空间

2) 内核态,运行于中断上下文，内核代表硬件运行于内核空间

3) 用户态，运行于用户空间

用于空间的应用程序，通过系统调用进入内核空间,这个时候用户空间的进程要传递很多变量参数的值给内核,内核态运行的时候也要保存用户进程的一些
寄存器值，变量等。所谓的进程上下文

硬件通过触发信号导致内核调用中断处理程序,进入内核空间,这个过程中硬件的一些变量和参数也要传递给内核，内核通过这些参数进行中断处理,所谓中断上下文

.. note::
    注意:进程调度和抢占的区别
    进程调度不一定发生抢占,但是抢占时一定发生了调度

context_switch注释
------------------

::

    /*
     * context_switch - switch to the new MM and the new thread's register state.
     */
    static __always_inline struct rq *
    context_switch(struct rq *rq, struct task_struct *prev,
               struct task_struct *next, struct rq_flags *rf)
    {
        //完成进程切换的准备工作
        prepare_task_switch(rq, prev, next);

        /*
         * For paravirt, this is coupled with an exit in switch_to to
         * combine the page table reload and the switch backend into
         * one hypercall.
         */
        arch_start_context_switch(prev);

        /*
         * kernel -> kernel   lazy + transfer active
         *   user -> kernel   lazy + mmgrab() active
         *
         * kernel ->   user   switch + mmdrop() active
         *   user ->   user   switch
         */
         //内核线程无虚拟地址空间,mm=NULL
        if (!next->mm) {                                // to kernel
            enter_lazy_tlb(prev->active_mm, next);      //这种加速上下文切换的技术称为惰性TLB

            next->active_mm = prev->active_mm;  //内核线程的active_mm为上一个进程的active_mm
            if (prev->mm)                           // from user
                mmgrab(prev->active_mm);
            else
                prev->active_mm = NULL;
        } else {                                        // to user  //不是内核线程，则需要切换虚拟地址空间
            membarrier_switch_mm(rq, prev->active_mm, next->mm);
            /*
             * sys_membarrier() requires an smp_mb() between setting
             * rq->curr / membarrier_switch_mm() and returning to userspace.
             *
             * The below provides this either through switch_mm(), or in
             * case 'prev->active_mm == next->mm' through
             * finish_task_switch()'s mmdrop().
             */
            switch_mm_irqs_off(prev->active_mm, next->mm, next);

            if (!prev->mm) {                        // from kernel
                /* will mmdrop() in finish_task_switch(). */
                rq->prev_mm = prev->active_mm;      //更新运行队列的prev_mm成员
                prev->active_mm = NULL;     //将prev的active_mm的值清空
            }
        }

        rq->clock_update_flags &= ~(RQCF_ACT_SKIP|RQCF_REQ_SKIP);

        prepare_lock_switch(rq, next, rf);

        /* Here we just switch the register state and the stack. */
        switch_to(prev, next, prev);    //切换进程的执行环境,包括堆栈和寄存器，同时返回上一个执行的程序
        //switch_to之后的代码只有在当前进程再次被选择运行(恢复执行)时才会运行,而此时当前进程恢复执行时的上一个进程可能跟参数传入时的prev不同
        //甚至可能是系统中任意一个随机的进程,因此switch_to通过第三个参数将此进程返回

        //路障同步,一般用编译器指令实现，确保了switch_to和finish_task_switch的执行顺序,不会因为任何可能的优化而改变
        barrier();

        //进程切换之后的处理工作
        return finish_task_switch(prev);
    }

prepare_arch_switch切换前的准备工作
------------------------------------

::

    static inline void
    prepare_task_switch(struct rq *rq, struct task_struct *prev,
                struct task_struct *next)
    {
        kcov_prepare_switch(prev);
        sched_info_switch(rq, prev, next);
        perf_event_task_sched_out(prev, next);
        rseq_preempt(prev);
        fire_sched_out_preempt_notifiers(prev, next);
        prepare_task(next);
        prepare_arch_switch(next);
    }

switch_to完成进程切换
---------------------

最后用switch_to完成了进程的切换,该函数切换了寄存器状态和栈,新进程在该调用后开始执行,而switch_to之后的代码只有在当前进程下一次选择运行时才会执行

内核在switch_to中执行如下操作

1) 进程切换,即esp的切换,由于从esp可以找到进程的描述符

2) 硬件上下文切换,设置ip寄存器的值,并jmp到___switch_to函数

3) 堆栈切换，即ebp的切换，ebp是栈底指针，它确定了当前用户空间属于哪个进程


- 为什么switch_to需要三个参数

调度过程

::

    #define switch_to(prev, next, last)					\
        do {								\
            ((last) = __switch_to((prev), (next)));			\
        } while (0)

    /*
     * Thread switching.
     */
    __notrace_funcgraph struct task_struct *__switch_to(struct task_struct *prev,
                    struct task_struct *next)
    {
        struct task_struct *last;

        fpsimd_thread_switch(next);
        tls_thread_switch(next);
        hw_breakpoint_thread_switch(next);
        contextidr_thread_switch(next);
        entry_task_switch(next);
        uao_thread_switch(next);
        ptrauth_thread_switch(next);
        ssbs_thread_switch(next);

        /*
         * Complete any pending TLB or cache maintenance on this CPU in case
         * the thread migrates to a different CPU.
         * This full barrier is also required by the membarrier system
         * call.
         */
        dsb(ish);

        /* the actual thread switch */
        last = cpu_switch_to(prev, next);

        return last;
    }
