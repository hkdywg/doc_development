TASKE_SIZE
=============

::

    #define TASK_SIZE   (UL(CONFIG_PAGE_OFFSET) - UL(SZ_16M))


``TASK_SIZE`` 指向了用户空间堆栈的最大长度． CONFIG_PAGE_OFFSET指向内核虚拟空间的起始地址



task_thread_info
==================

::

    #ifdef CONFIG_THREAD_INFO_IN_TASK
    static inline struct thread_info *task_thread_info(struct task_thread *task)
    {
        return &task->thread_info;
    }
    #endif


``task_thread_info`` 通过进程的task_struct结构获得进程的thread_info结构．











