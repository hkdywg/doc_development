linux wait queue
================

涉及源码目录

::

    kernel/include/linux/wait.h
    kernel/kernel/sched/wait.c
    kernel/include/linux/sched.h
    kernel/kernel/sched/core.c

概述
----

linux内核的等待队列事非常重要的数据结构,在内核驱动中广为使用,它是以双向循环链表为基础的数据结构,与进程的休眠唤醒机制紧密相连，是实现异步事件通知
、跨进程通信、同步资源访问等技术的底层技术支撑。

等待队列有两种数据结构：等待队列头(wait_queue_head)和等待队列项(wait_queue_entry),两者都有一个list_head类型的task_list.
双向链表通过task_list将等待队列头和一系列的等待队列项串起来

等待队列
--------

struct wait_queue_entry
^^^^^^^^^^^^^^^^^^^^^^^

::

    struct wait_queue_entry {
          unsigned int        flags;
          void            *private;
          wait_queue_func_t   func;
          struct list_head    entry;
                  
    };

可以通过DECLARE_WAITQUEUE(name)来创建类型为wait_queue_entry类型的等待队列name

::

      #define __WAITQUEUE_INITIALIZER(name, tsk) {                    \
            .private    = tsk,                          \
            .func       = default_wake_function,                \
            .entry      = { NULL, NULL  } }
                        
      #define DECLARE_WAITQUEUE(name, tsk)                        \
            struct wait_queue_entry name = __WAITQUEUE_INITIALIZER(name, tsk)


struct wait_queue_head
^^^^^^^^^^^^^^^^^^^^^^

::

    struct wait_queue_head {
        spinlock_t      lock;
        struct list_head    head;
    };
    typedef struct wait_queue_head wait_queue_head_t;

可以通过DECLARE_WAITQUEUE_HEAD(name)

::

  #define __WAIT_QUEUE_HEAD_INITIALIZER(name) {                   \
        .lock       = __SPIN_LOCK_UNLOCKED(name.lock),          \
        .head       = { &(name).head, &(name).head  } }

  #define DECLARE_WAIT_QUEUE_HEAD(name) \
        struct wait_queue_head name = __WAIT_QUEUE_HEAD_INITIALIZER(name)


add_wait_queue
^^^^^^^^^^^^^^

::

  void add_wait_queue(struct wait_queue_head *wq_head, struct wait_queue_entry *wq_entry)
  {
        unsigned long flags;
          
        wq_entry->flags &= ~WQ_FLAG_EXCLUSIVE;
        spin_lock_irqsave(&wq_head->lock, flags);
        __add_wait_queue(wq_head, wq_entry);
        spin_unlock_irqrestore(&wq_head->lock, flags);
  }

  static inline void __add_wait_queue(struct wait_queue_head *wq_head, struct wait_queue_entry *wq_entry)
  {
        list_add(&wq_entry->entry, &wq_head->head);
  }

该方法用于将wait_entry等待队列项挂到等待队列头wq_head中

休眠与唤醒
----------

wait_event
^^^^^^^^^^

::


    #define ___wait_event(wq_head, condition, state, exclusive, ret, cmd)		\
    ({										\
        __label__ __out;							\
        struct wait_queue_entry __wq_entry;					\
        long __ret = ret;	/* explicit shadow */				\
                                            \
        init_wait_entry(&__wq_entry, exclusive ? WQ_FLAG_EXCLUSIVE : 0);	\
        for (;;) {								\
            long __int = prepare_to_wait_event(&wq_head, &__wq_entry, state);/*检测当前进程是否有待处理的信号*/ \
                                            \
            if (condition)							\
                break;							\
                                            \
            if (___wait_is_interruptible(state) && __int) {			\
                __ret = __int;						\
                goto __out;						\
            }								\
                                            \
            cmd;	/*schedule(), 进入睡眠，从进程就绪队列中选择一个高优先级的进程来代替当前进程运行*/							\
        }									\
        finish_wait(&wq_head, &__wq_entry);					\
    __out:	__ret;									\
    })

    #define __wait_event(wq_head, condition)					\
        (void)___wait_event(wq_head, condition, TASK_UNINTERRUPTIBLE, 0, 0,	\
                    schedule())

    /**
     * wait_event - sleep until a condition gets true
     * @wq_head: the waitqueue to wait on
     * @condition: a C expression for the event to wait for
     *
     * The process is put to sleep (TASK_UNINTERRUPTIBLE) until the
     * @condition evaluates to true. The @condition is checked each time
     * the waitqueue @wq_head is woken up.
     *
     * wake_up() has to be called after changing any variable that could
     * change the result of the wait condition.
     */
    #define wait_event(wq_head, condition)						\
    do {										\
        might_sleep();								\
        if (condition)								\
            break;								\
        __wait_event(wq_head, condition);					\
    } while (0)

  
prepare_to_wait_event
^^^^^^^^^^^^^^^^^^^^^

::

  long prepare_to_wait_event(struct wait_queue_head *wq_head, struct wait_queue_entry *wq_entry, int state)
  {
        unsigned long flags;
        long ret = 0;

        spin_lock_irqsave(&wq_head->lock, flags);
        if (signal_pending_state(state, current)) {
            list_del_init(&wq_entry->entry);
            ret = -ERESTARTSYS;
        } else {
        if (list_empty(&wq_entry->entry)) {
          if (wq_entry->flags & WQ_FLAG_EXCLUSIVE)
            __add_wait_queue_entry_tail(wq_head, wq_entry);
          else
            __add_wait_queue(wq_head, wq_entry);
          }
          set_current_state(state);
        }
        spin_unlock_irqrestore(&wq_head->lock, flags);
        return ret;
          
  }
    
wake_up
^^^^^^^

::

     #define wake_up(x)          __wake_up(x, TASK_NORMAL, 1, NULL)
     
     void __wake_up(struct wait_queue_head *wq_head, unsigned int mode,
                     int nr_exclusive, void *key)
     { 
         __wake_up_common_lock(wq_head, mode, nr_exclusive, 0, key);
     }

     static int __wake_up_common(struct wait_queue_head *wq_head, unsigned int mode,
                int nr_exclusive, int wake_flags, void *key,
                wait_queue_entry_t *bookmark)
     {
         wait_queue_entry_t *curr, *next;
         int cnt = 0;

         lockdep_assert_held(&wq_head->lock);

         if (bookmark && (bookmark->flags & WQ_FLAG_BOOKMARK)) {
             curr = list_next_entry(bookmark, entry);

             list_del(&bookmark->entry);
             bookmark->flags = 0;
         } else
             curr = list_first_entry(&wq_head->head, wait_queue_entry_t, entry);

         if (&curr->entry == &wq_head->head)
             return nr_exclusive;

         list_for_each_entry_safe_from(curr, next, &wq_head->head, entry) {
             unsigned flags = curr->flags;
             int ret;

             if (flags & WQ_FLAG_BOOKMARK)
                 continue;
             //调用唤醒函数,一般唤醒函数为default_wake_function
             ret = curr->func(curr, mode, wake_flags, key);
             if (ret < 0)
                 break;
             if (ret && (flags & WQ_FLAG_EXCLUSIVE) && !--nr_exclusive)
                 break;

             if (bookmark && (++cnt > WAITQUEUE_WALK_BREAK_CNT) &&
                     (&next->entry != &wq_head->head)) {
                 bookmark->flags = WQ_FLAG_BOOKMARK;
                 list_add_tail(&bookmark->entry, &next->entry);
                 break;
             }
         }

         return nr_exclusive;
     }

     static void __wake_up_common_lock(struct wait_queue_head *wq_head, unsigned int mode,
                 int nr_exclusive, int wake_flags, void *key)
     {
         unsigned long flags;
         wait_queue_entry_t bookmark;

         bookmark.flags = 0;
         bookmark.private = NULL;
         bookmark.func = NULL;
         INIT_LIST_HEAD(&bookmark.entry);

         do {
             spin_lock_irqsave(&wq_head->lock, flags);
             nr_exclusive = __wake_up_common(wq_head, mode, nr_exclusive,
                             wake_flags, key, &bookmark);
             spin_unlock_irqrestore(&wq_head->lock, flags);
         } while (bookmark.flags & WQ_FLAG_BOOKMARK);
     }


default_wake_function
^^^^^^^^^^^^^^^^^^^^^

此函数为默认的唤醒函数

::

      int default_wake_function(wait_queue_entry_t *curr, unsigned mode, int wake_flags,
        void *key)
      {
          return try_to_wake_up(curr->private, mode, wake_flags);
            
      }
