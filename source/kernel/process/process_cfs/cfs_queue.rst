CFS队列操作
============

完全公平调度器CFS中两个函数可用来增删队列的成员：enqueue_task_fair和dequeue_task_fair分别来向CFS就绪队列中添加或者删除进程

enqueue_task_fair入队操作
-------------------------

enqueue_task_fair函数
^^^^^^^^^^^^^^^^^^^^^^

向就绪队列中放置新进程的工作由函数enqueue_task_fair函数完成，该函数定义在 kernel/sched/fair.c中

该函数将task_struct \*p所指向的进程插入到rq所在的就绪队列中,除了指向所述的就绪队列rq和task_struct的指针外，该函数还有另外一个参数wakeup.这使得可以指定
入队的进程是否最近才被唤醒并转换为运行状态(此时需指定wakeup=1),还是此前就是可运行的(那么wakeup=0)

::

    /*
     * The enqueue_task method is called before nr_running is
     * increased. Here we update the fair scheduling stats and
     * then put the task into the rbtree:
     */
    static void
    enqueue_task_fair(struct rq *rq, struct task_struct *p, int flags)
    {
        struct cfs_rq *cfs_rq;
        struct sched_entity *se = &p->se;
        int idle_h_nr_running = task_has_idle_policy(p);

        /*
         * The code below (indirectly) updates schedutil which looks at
         * the cfs_rq utilization to select a frequency.
         * Let's add the task's estimated utilization to the cfs_rq's
         * estimated utilization, before we update schedutil.
         */
        util_est_enqueue(&rq->cfs, p);

        /*
         * If in_iowait is set, the code below may not trigger any cpufreq
         * utilization updates, so do it here explicitly with the IOWAIT flag
         * passed.
         */
        if (p->in_iowait)
            cpufreq_update_util(rq, SCHED_CPUFREQ_IOWAIT);

        for_each_sched_entity(se) {
            if (se->on_rq)
                break;
            cfs_rq = cfs_rq_of(se);
            enqueue_entity(cfs_rq, se, flags);

            /*
             * end evaluation on encountering a throttled cfs_rq
             *
             * note: in the case of encountering a throttled cfs_rq we will
             * post the final h_nr_running increment below.
             */
            if (cfs_rq_throttled(cfs_rq))
                break;
            cfs_rq->h_nr_running++;
            cfs_rq->idle_h_nr_running += idle_h_nr_running;

            flags = ENQUEUE_WAKEUP;
        }

        for_each_sched_entity(se) {
            cfs_rq = cfs_rq_of(se);
            cfs_rq->h_nr_running++;
            cfs_rq->idle_h_nr_running += idle_h_nr_running;

            if (cfs_rq_throttled(cfs_rq))
                break;

            update_load_avg(cfs_rq, se, UPDATE_TG);
            update_cfs_group(se);
        }

        if (!se) {
            add_nr_running(rq, 1);
            if (flags & ENQUEUE_WAKEUP)
                update_overutilized_status(rq);

        }

        if (cfs_bandwidth_used()) {
            for_each_sched_entity(se) {
                cfs_rq = cfs_rq_of(se);

                if (list_add_leaf_cfs_rq(cfs_rq))
                    break;
            }
        }

        assert_list_leaf_cfs_rq(rq);

        hrtick_update(rq);
    }
