唤醒抢占
========

进程的创建
------------

fork vfork和clone的系统调用的入口地址分别是sys_fork,sys_vfork和sys_clone，而他们的定义是依赖于体系结构的,而他们呢最后都调用了_do_fork，在_do_fork中通过copy_process复制进程
的信息，调用wake_up_new_task将子进程加入到调度器中

1) dup_task_struct为其分配了新的堆栈

2) 调用了sched_fork,将其置为TASK_RUNNING

3) copy_thread(_tls)中将父进程的寄存器上下文复制给子进程,保证了父子进程的堆栈信息是一致的

4) 将ret_from_fork的地址设置为eip寄存器的值

5) 为新进程分配并设置新的pid

6) 最终子进程从ret_from_fork开始执行

处理新进程
----------

- 负荷权重load_weight

CFS进程的负荷权重跟进程的优先级相关,优先级越高的进程，负荷权重越高

- 虚拟运行时间vruntime

虚拟运行时间是通过进程的实际运行时间和进程的权重计算出来的，在CFS调度器中,将进程优先级这个概念弱化，而是强调进程的权重,一个进程的权重越大则说明这个进程更需要运行,因此它的虚拟运行时间就
越小，这样被调度的机会就越大，而CFS调度器中的权重在内核是对用户态进程的优先级nice值，通过prio_to_weight数组进程nice值和权重的转换计算出来的


::

    static void task_fork_fair(struct task_struct *p)
    {
        struct cfs_rq *cfs_rq;
        struct sched_entity *se = &p->se, *curr;
        struct rq *rq = this_rq();
        struct rq_flags rf;

        rq_lock(rq, &rf);
        update_rq_clock(rq);

        cfs_rq = task_cfs_rq(current);
        curr = cfs_rq->curr;
        if (curr) {
            update_curr(cfs_rq);    //更新统计量
            se->vruntime = curr->vruntime;
        }
        place_entity(cfs_rq, se, 1);    //调整调度实体se的虚拟运行时间

        //如果设置了sysctl_sched_child_run_first期望se进程先运行,但se进程的虚拟运行时间却大于当前进程curr
        //此时我们需要保证se的entity_key小于curr，才能保证se先运行,内核此处是通过swap(curr,se)的虚拟运行时间来完成的
        if (sysctl_sched_child_runs_first && curr && entity_before(curr, se)) {
            /*
             * Upon rescheduling, sched_class::put_prev_task() will place
             * 'current' within the tree based on its new key value.
             */
            swap(curr->vruntime, se->vruntime);     //由于curr的vruntime较小,为了使se先运行交换两者的vruntime
            resched_curr(rq);   //设置重调度标识
        }

        se->vruntime -= cfs_rq->min_vruntime;
        rq_unlock(rq, &rf);
    }


新创建的进程核睡眠后苏醒的进程为了保证他们的vruntime与系统中的vruntime差距不会太大,会使用place_entity来设置其虚拟运行时间vruntime,在place_entity中重新设置vruntime值
以cfs->min_vruntime为基础，给与一定的补偿，但不能补偿太多，这样在醒来或者创建后有能力抢占CPU是大概率事件，这也是CFS调度算法的本意，即保证交互式进程的响应速度,因为交互式
进程等待用户输入会频繁休眠

在多CPU的系统上,不同CPU的负载不一样,有的忙一些有的闲一些,每个CPU都有自己的运行队列，如果一个进程在不同的CPU之间迁移，如果一个进程从min_vruntime更小的CPU (A) 上迁移到min_vruntime更大的CPU (B) 上，可能就会占便宜了，因为CPU (B) 的运行队列中进程的vruntime普遍比较大，迁移过来的进程就会获得更多的CPU时间片。这显然不太公平

CFS是这样做的

- 当进程从一个CPU的运行队列中出来(dequeue_entity)的时候,它的vruntime要减去队列的min_vruntime值

- 当进程加入到另一个CPU的运行队列(enqueue_entity)的时候，它的vruntime要加上该队列的min_vruntime值

- 当进程刚刚创建以某个cfs_rq的min_vruntime为基准设置其虚拟运行时间后,也要减去队列的min_vruntime值

