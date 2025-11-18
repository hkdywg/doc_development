linux内核定时器
====================

如果内核驱动中想周期性的做一些事情，可以使用内核定时器来完成


数据结构
-----------

::

      [include/linux/timer.h]
      struct timer_list {
          /*
           * All fields that change during normal runtime grouped to the
           * same cacheline
           */
          struct hlist_node   entry;
          unsigned long       expires;  //定时器唤醒时间
          void            (*function)(struct timer_list *); //唤醒后需要执行的函数
          u32         flags;
      
      #ifdef CONFIG_LOCKDEP
          struct lockdep_map  lockdep_map;
      #endif
      };

其中我们主要来填充唤醒时间和唤醒后要执行的函数，其他参数初始化可以使用系统提供的固定的定时器初始化函数


定时器初始化
--------------

::


    #define timer_setup(timer, callback, flags)         \
        __init_timer((timer), (callback), (flags))

    #define __init_timer(_timer, _fn, _flags)               \
        init_timer_key((_timer), (_fn), (_flags), NULL, NULL)

    /**
    * init_timer_key - initialize a timer
    * @timer: the timer to be initialized
    * @func: timer callback function
    * @flags: timer flags
    * @name: name of the timer
    * @key: lockdep class key of the fake lock used for tracking timer
    *       sync lock dependencies
    *
    * init_timer_key() must be done to a timer prior calling *any* of the
    * other timer functions.
    */
    void init_timer_key(struct timer_list *timer,
              void (*func)(struct timer_list *), unsigned int flags,
              const char *name, struct lock_class_key *key)
    {
      debug_init(timer);
      do_init_timer(timer, func, flags, name, key);
    }
    EXPORT_SYMBOL(init_timer_key);


具体的初始化在do_init_timer中完成

::

     static void do_init_timer(struct timer_list *timer,
                void (*func)(struct timer_list *),
                unsigned int flags,
                const char *name, struct lock_class_key *key)
	{
		  timer->entry.pprev = NULL;
		  timer->function = func;
		  timer->flags = flags | raw_smp_processor_id();
		  lockdep_init_map(&timer->lockdep_map, name, key, 0);
	  } 


初始化完成以后，需要使用下面的函数将初始化的参数加入到定时器链表中去

.. note::
	内核定时器是一个单次的定时器

::

	/**
	 * add_timer - start a timer
	 * @timer: the timer to be added
	 *
	 * The kernel will do a ->function(@timer) callback from the
	 * timer interrupt at the ->expires point in the future. The
	 * current time is 'jiffies'.
	 *
	 * The timer's ->expires, ->function fields must be set prior calling this
	 * function.
	 *
	 * Timers with an ->expires field in the past will be executed in the next
	 * timer tick.
	 */
	 void add_timer(struct timer_list *timer)
	 {
	    BUG_ON(timer_pending(timer));	//检测timer有没有被挂起
	    mod_timer(timer, timer->expires);	//没有挂起则修改定时器时间
	 }
	 EXPORT_SYMBOL(add_timer);

	//用来判断一个处在定时器管理队列中的定时器对象是否已经被调度执行
	static inline int timer_pending(const struct timer_list * timer)
	{
		return timer->entry.next != NULL;    /* 该值默认初始化是被初始化为NULL的 */
	}


- mod_timer

::

   int mod_timer(struct timer_list *timer, unsigned long expires)
   {
       return __mod_timer(timer, expires, 0);
   }


定时器删除
-----------


::

	int del_timer(struct timer_list *timer)
    {
        struct timer_base *base;
        unsigned long flags;
        int ret = 0;

        debug_assert_init(timer);

        if (timer_pending(timer)) {
            base = lock_timer_base(timer, &flags);
            ret = detach_if_pending(timer, base, true);
            raw_spin_unlock_irqrestore(&base->lock, flags);
        }

        return ret;
    }


定时器应用示例
---------------


::

	#include <linux/time.h>
 
	/* 定义一个定时器指针 */
	static struct timer_list *timer;
	 
	 
	/* 参数是timer中的变量data */
	void function_handle(unsigned long data)
	{
		/* 做你想做的事 */
		......
	 
		/* 因为内核定时器是一个单次的定时器,所以如果想要多次重复定时需要在定时器绑定的函数结尾重新装载时间,并启动定时 */
		/* Kernel Timer restart */
		mod_timer(timer,jiffies + HZ/50);
	}
	 
	int xxxx_init(void)
	{
		timer = kzalloc(sizeof(struct timer_list), GFP_KERNEL);
		if (!timer )
		{
			/* 错误处理 */
		}
	 
		/* 具体任务的注册等 */
		......
	 
		timer_setup(timer, function_handle, 0);                   /* 初始化定时器 */ 
		timer->expires = jiffies + (HZ/50);   /* 定时的时间点，当前时间的20ms之后 */  
		add_timer(timer);                     /* 添加并启动定时器 */
	}
	 
	 
	void xxxx_exit(void)
	{
		/* 具体任务的卸载等 */
		......
		
		/* 删除定时器 */
		del_timer(timer);
	}
	 
	 
	module_init(xxxx_init);
	module_exit(xxxx_exit);
	 
	MODULE_LICENSE("GPL");





























