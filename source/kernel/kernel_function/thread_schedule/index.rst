Linux内核API之进程调度
=========================

数据结构
------------





函数接口
----------

- complete

complete函数主要用于唤醒等待队列中的睡眠进程，并能记录等待队列被唤醒的次数，唤醒次数保存在参数的done字段中．此函数通过调用函数__wake_up_locked()唤醒等待队列中
的进程，传递的参数的只能是TASK_INTERRUPTIBLE或者TASK_UNINTERRUPTIBLE状态，并且唤醒进程不是同步的，只能按等待队列中的进程的顺序一个一个的唤醒．


::

    #include <linux/completion.h>
    struct completion {
        unsigned int done;      //保存等待队列的唤醒的次数
        wait_queue_head_t wait; //等待队列的头元素
    };

    //struct completion*为输出参数
    void complete(struct completion *);


测试代码


::

    static struct completion comple;
    static task_struct *old_thread;

    static int __init complete_test_func(void)
    {
        struct task_struct *result;
        wait_queue_t data;
        old_thread = current;
        kthread_create_on_node(thread_test, NULL, -1, NULL); //创建新的进程
        wake_up_process(result);
        init_completion(&comple);   //初始化全局变量
        init_waitqueue_entry(&data, current); //用当前进程初始化等待队列元素
        add_wait_queue(&(comple.wait), &data); //将当前进程加入等待队列中
        schedule_timeout_uninterruptible(1000); //使等待队列进程不可中断的等待状态
    }
