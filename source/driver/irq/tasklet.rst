tasklet
===========


由于软中断必须使用可重入函数，这就导致设计上的复杂度变高，而如果某种应用并不需要在多个CPU上并行执行，那么软中断其实是没有必要的，因此诞生了tasklet.
他具有以下特性

1. 一种特定类型的tasklet只能运行在一个CPU上，不能并行，只能串行执行
2. 多个不同类型的tasklet可以并行在多个cpu上
3. 软中断是静态分配的，在内核编译好之后，就不能改变。但tasklet就灵活许多，可以在运行时改变(如添加模块时)


tasklet是利用软中断实现的一种下半部机制，本质上是软中断的一个变种，运行在中断上下文。如果不需要软中断的并行特性，tasklet就是一种好的选择


数据结构
-----------

::

     struct tasklet_struct
     {
         struct tasklet_struct *next;       //将多个tasklet链接成单向循环链表
         unsigned long state;               //TASKLET_STATE_SCHED  TASKLET_STATE_RUN
         atomic_t count;                    //0激活tasklet 非0禁用tasklet
         void (*func)(unsigned long);       //用户自定义函数
         unsigned long data;                //函数入参
     };


::

    //kernel/softirq.c
    static DEFINE_PER_CPU(struct tasklet_head, tasklet_vec);//低优先级
    static DEFINE_PER_CPU(struct tasklet_head, tasklet_hi_vec);//高优先级

定义一个tasklet
----------------

- 静态声明

::

      #define DECLARE_TASKLET(name, func, data) \
      struct tasklet_struct name = { NULL, 0, ATOMIC_INIT(0), func, data }

      //tasklet->count初始化为0，表示tasklet处于激活状态      

      #define DECLARE_TASKLET_DISABLED(name, func, data) \
      struct tasklet_struct name = { NULL, 0, ATOMIC_INIT(1), func, data }

- 动态声明

::

      void tasklet_init(struct tasklet_struct *t, 
                void (*func)(unsigned long), unsigned long data) 
      { 
          t->next = NULL; 
          t->state = 0; 
          atomic_set(&t->count, 0);
          t->func = func;
          t->data = data;
      }


tasklet软中断注册
-------------------

::

    void __init softirq_init(void)
    {
            int cpu;

            for_each_possible_cpu(cpu) {
                    per_cpu(tasklet_vec, cpu).tail =
                            &per_cpu(tasklet_vec, cpu).head;
                    per_cpu(tasklet_hi_vec, cpu).tail =
                            &per_cpu(tasklet_hi_vec, cpu).head;
            }

            open_softirq(TASKLET_SOFTIRQ, tasklet_action);
            open_softirq(HI_SOFTIRQ, tasklet_hi_action);
    }

start_kernel执行时会执行softirq_init它会初始化各个cpu core的tasklet和tasklet_hi链表，另外还会注册TASKLET_SOFTIRQ和HI_SOFTIRQ这两个软中断，他们的软中断处理函数分别为
tasklet_action和tasklet_hi_action,在这两个软中断处理函数中分别会遍历tasklet_vec链表和tasklet_hi_vec链表

tasklet执行
-----------

::

	//kernel/softirq.c
	static __latent_entropy void tasklet_action(struct softirq_action *a)
	|--tasklet_action_common(a, this_cpu_ptr(&tasklet_vec), TASKLET_SOFTIRQ);
			|--struct tasklet_struct *list;
			|  //关中断的前提下获取tasklet_vec链表头保存在list
			|--local_irq_disable();
			|  list = tl_head->head;
			|  tl_head->head = NULL;
			|  tl_head->tail = &tl_head->head; 
			|  local_irq_enable();
			|--while (list)
					struct tasklet_struct *t = list;
					list = list->next;
					//保证在同一个cpu上运行此tasklet
					if (tasklet_trylock(t))
						//t->count为0表示该tasklet处于可执行状态
						if (!atomic_read(&t->count))
							if (!test_and_clear_bit(TASKLET_STATE_SCHED,&t->state))
								BUG();
							t->func(t->data);
							//清除tasklet->state的TASKLET_STATE_RUN标记
							tasklet_unlock(t);
							continue;
					local_irq_disable();
					t->next = NULL;
					*tl_head->tail = t;
					tl_head->tail = &t->next;
					__raise_softirq_irqoff(softirq_nr);
					local_irq_enable();
 


tasklet调度
------------

::

	static inline void tasklet_schedule(struct tasklet_struct *t)
	|--if (!test_and_set_bit(TASKLET_STATE_SCHED, &t->state))
	 		__tasklet_schedule(t);
				|--__tasklet_schedule_common(t, &tasklet_vec,TASKLET_SOFTIRQ);
						|--local_irq_save(flags);
						|--head = this_cpu_ptr(headp);
						|--t->next = NULL;
						|--*head->tail = t;
						|--head->tail = &(t->next); 
						|--raise_softirq_irqoff(softirq_nr);
						|--local_irq_restore(flags);

1. taslet_schedule首先会检测tasklet_struct->state有没有置位TASKLET_STATE_SCHED标志位，如果已经置位TASKLET_STATE_SCHED，则会退出，因此在tasklet_action执行时要先清除TASKLET_STATE_SCHED标志，以让其它的tasklet执行tasklet_schedule
2. __tasklet_schedule：如果没有设置表示还没有执行，置位的同时调用__tasklet_schedule只是触发软中断，即将tasklet挂入到tasklet_vec链表，由于tasklet_vec链表是per cpu的，因此会加入到当前的CPU的tasklet_vec,执行时也会有对应的CPU执行。如果已经置位TASKLET_STATE_SCHED标志位，直接退出，所以如果一个tasklet没有执行，多次执行tasklet_schedule，也不会将这个tasklet挂载到其它的cpu的tasklet_vec链表，除非在本cpu的tasklet_vec链表的这个tasklet执行完了，清空了tasklet->state的TASKLET_STATE_SCHED标志位，下次执行tasklet_schedule时才有机会链入其它的cpu上的tasklet_vec链表


以一个常见的设备驱动为例，在硬件中断处理函数中调用tasklet_schedule函数去触发tasklet来处理一些数据，例如数据复制，数据转换等


::

	static irqreturn_t scdrv_event_interrupt(int irq, void *subch_data)
	{
		struct subch_data_s *sd = subch_data;
		unsigned long flags;
		int status;

		spin_lock_irqsave(&sd->sd_rlock, flags);
		status = ia64_sn_irtr_intr(sd->sd_nasid, sd->sd_subch);

		if ((status > 0) && (status & SAL_IROUTER_INTR_RECV)) {
			//触发tasklet来处理
			tasklet_schedule(&sn_sysctl_event);
		}
		spin_unlock_irqrestore(&sd->sd_rlock, flags);
		return IRQ_HANDLED;
	}





















































