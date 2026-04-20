输入事件驱动层
=================

系统将输入事件层分为三种，evdev(通用各种类型输入类设备)、mousedev、joydev

框架以及数据结构
-----------------

::

      static struct input_handler evdev_handler = {
          .event      = evdev_event,    //打包数据，并上报事件
          .events     = evdev_events,   
          .connect    = evdev_connect,  //和dev匹配后做响应连接
          .disconnect = evdev_disconnect,   //exit时会使用
          .legacy_minors  = true,
          .minor      = EVDEV_MINOR_BASE,   //次设备号开始
          .name       = "evdev",
          .id_table   = evdev_ids,  //匹配规则,edev是所有都可以匹配
      };

      static int __init evdev_init(void)
      {
          return input_register_handler(&evdev_handler);
      }

      static void __exit evdev_exit(void)
      {
          input_unregister_handler(&evdev_handler);
      }

      module_init(evdev_init);
      module_exit(evdev_exit);


evdev有个重要的数据结构


::

      struct evdev {
          int open;     //打开引用计数
          struct input_handle handle;   //关联的input_handle
          wait_queue_head_t wait;   //等待队列
          struct evdev_client __rcu *grab;
          struct list_head client_list; //evdev_client链表，说明一个evdev设备可以处理多个evdev_client,可以有多个进程访问
          spinlock_t client_lock; /* protects client_list */
          struct mutex mutex;
          struct device dev;
          struct cdev cdev;
           bool exist;
      };


接口实现
------------

evdev_connect
^^^^^^^^^^^^^^^^

在注册handler和dev时，如果匹配上了就会调用此函数

::

      static int evdev_connect(struct input_handler *handler, struct input_dev *dev,
               const struct input_device_id *id)
      {
          struct evdev *evdev;
          int minor;
          int dev_no;
          int error;
        
          //获取一个未使用的次设备号
          minor = input_get_new_minor(EVDEV_MINOR_BASE, EVDEV_MINORS, true);
          if (minor < 0) {
              error = minor;
              pr_err("failed to reserve new minor: %d\n", error);
              return error;
          }
      
          evdev = kzalloc(sizeof(struct evdev), GFP_KERNEL);
          if (!evdev) {
              error = -ENOMEM;
              goto err_free_minor;
          }
      
          //初始化新申请的evdev
          INIT_LIST_HEAD(&evdev->client_list);
          spin_lock_init(&evdev->client_lock);
          mutex_init(&evdev->mutex);
          init_waitqueue_head(&evdev->wait);    //初始化一个等待队列
          evdev->exist = true;
      
          dev_no = minor;
          /* Normalize device number if it falls into legacy range */
          if (dev_no < EVDEV_MINOR_BASE + EVDEV_MINORS)
              dev_no -= EVDEV_MINOR_BASE;
          dev_set_name(&evdev->dev, "event%d", dev_no);

          evdev->handle.dev = input_get_device(dev);    //input_dev绑定到evdev的handle中
          evdev->handle.name = dev_name(&evdev->dev);
          evdev->handle.handler = handler;      //绑定handle
          evdev->handle.private = evdev;

          evdev->dev.devt = MKDEV(INPUT_MAJOR, minor);
          evdev->dev.class = &input_class;  //evdev里面的设备属于input_class
          evdev->dev.parent = &dev->dev;
          evdev->dev.release = evdev_free;
          device_initialize(&evdev->dev);   //初始化evdev里面的dev通用数据

          error = input_register_handle(&evdev->handle);    //注册handle
          if (error)
              goto err_free_evdev;

          cdev_init(&evdev->cdev, &evdev_fops);     //创建设备
          error = cdev_device_add(&evdev->cdev, &evdev->dev);
          if (error)
              goto err_cleanup_evdev;

          return 0;

       err_cleanup_evdev:
          evdev_cleanup(evdev);
          input_unregister_handle(&evdev->handle);
       err_free_evdev:
          put_device(&evdev->dev);
       err_free_minor:
          input_free_minor(minor);
          return error;
      }


evdev_event
^^^^^^^^^^^^

evdev_event函数将一个设备驱动层发送过来的事件打包

::

      /*
       * Pass incoming events to all connected clients.
       */
      static void evdev_events(struct input_handle *handle,
                   const struct input_value *vals, unsigned int count)
      {
          struct evdev *evdev = handle->private;    //evdev本身绑定在handle里面的private
          struct evdev_client *client;
          ktime_t *ev_time = input_get_timestamp(handle->dev);  

          rcu_read_lock();

          client = rcu_dereference(evdev->grab);

          if (client)
              evdev_pass_values(client, vals, count, ev_time);
          else
              list_for_each_entry_rcu(client, &evdev->client_list, node)
                  evdev_pass_values(client, vals, count, ev_time);

          rcu_read_unlock();
      }

      /*
       * Pass incoming event to all connected clients.
       */
      static void evdev_event(struct input_handle *handle,
                  unsigned int type, unsigned int code, int value)
      {
          struct input_value vals[] = { { type, code, value } };    

          evdev_events(handle, vals, 1);
      }

- 发送数据给client函数

::

      static void evdev_pass_values(struct evdev_client *client,
              const struct input_value *vals, unsigned int count,
              ktime_t *ev_time)
      {
          struct evdev *evdev = client->evdev;
          const struct input_value *v;
          struct input_event event;
          struct timespec64 ts;
          bool wakeup = false;

          if (client->revoked)
              return;

          ts = ktime_to_timespec64(ev_time[client->clk_type]);
          event.input_event_sec = ts.tv_sec;
          event.input_event_usec = ts.tv_nsec / NSEC_PER_USEC;

          /* Interrupts are disabled, just acquire the lock. */
          spin_lock(&client->buffer_lock);

          for (v = vals; v != vals + count; v++) {
              if (__evdev_is_filtered(client, v->type, v->code))
                  continue;

              if (v->type == EV_SYN && v->code == SYN_REPORT) {
                  /* drop empty SYN_REPORT */
                  if (client->packet_head == client->head)
                      continue;

                  wakeup = true;
              }
              //将数据打包成标准格式
              event.type = v->type;
              event.code = v->code;
              event.value = v->value;
              __pass_event(client, &event);
          }

          spin_unlock(&client->buffer_lock);

          if (wakeup)
              wake_up_interruptible(&evdev->wait);  //唤醒等待队列上的进程
      }


::

      static void __pass_event(struct evdev_client *client,
               const struct input_event *event)
      {
          client->buffer[client->head++] = *event;  //把数据包写入client缓冲队列中,方便app读取
          client->head &= client->bufsize - 1;
      
          if (unlikely(client->head == client->tail)) {
              /*
               * This effectively "drops" all unconsumed events, leaving
               * EV_SYN/SYN_DROPPED plus the newest event in the queue.
               */
              client->tail = (client->head - 2) & (client->bufsize - 1);
      
              client->buffer[client->tail] = (struct input_event) {
                  .input_event_sec = event->input_event_sec,
                  .input_event_usec = event->input_event_usec,
                  .type = EV_SYN,
                  .code = SYN_DROPPED,
                  .value = 0,
              };
      
              client->packet_head = client->tail;
          }
      
          if (event->type == EV_SYN && event->code == SYN_REPORT) {
              client->packet_head = client->head;
              kill_fasync(&client->fasync, SIGIO, POLL_IN); //发送一个异步通知，通知打开该client的应用程序，执行信号处理函数
          }
      }

file_operations
^^^^^^^^^^^^^^^

应用层通过系统调用会调用file_operations中定义的函数接口

::

      static const struct file_operations evdev_fops = {
          .owner      = THIS_MODULE,
          .read       = evdev_read,
          .write      = evdev_write,
          .poll       = evdev_poll,
          .open       = evdev_open,
          .release    = evdev_release,
          .unlocked_ioctl = evdev_ioctl,
      #ifdef CONFIG_COMPAT
          .compat_ioctl   = evdev_ioctl_compat,
      #endif
          .fasync     = evdev_fasync,
          .flush      = evdev_flush,
          .llseek     = no_llseek,
      };


下面主要分析open和read函数

::

      static int evdev_open(struct inode *inode, struct file *file)
      {
          struct evdev *evdev = container_of(inode->i_cdev, struct evdev, cdev);    //通过inode可以获取对应的evdev
          unsigned int bufsize = evdev_compute_buffer_size(evdev->handle.dev);
          struct evdev_client *client;
          int error;

          //分配client来处理event，同一个文件打开n次就需要分配n个client
          client = kvzalloc(struct_size(client, buffer, bufsize), GFP_KERNEL);
          if (!client)
              return -ENOMEM;

          client->bufsize = bufsize;    //设置bufsize
          spin_lock_init(&client->buffer_lock);
          client->evdev = evdev;    //client和具体的evdev绑定
          evdev_attach_client(evdev, client);   //将client添加到evdev的client_list链表中

          error = evdev_open_device(evdev);
          if (error)
              goto err_free_client;

          file->private_data = client;  //将文件的私有数据指向该client
          stream_open(inode, file);

          return 0;

       err_free_client:
          evdev_detach_client(evdev, client);
          kvfree(client);
          return error;
      }

::

  static int evdev_open_device(struct evdev *evdev)
  {
      int retval;

      retval = mutex_lock_interruptible(&evdev->mutex);
      if (retval)
          return retval;

      if (!evdev->exist)
          retval = -ENODEV;
      else if (!evdev->open++) {    //打开计数加一
          retval = input_open_device(&evdev->handle);   //这个打开设备的函数是在核心层定义的,最终会调用设备驱动层的open函数
          if (retval)
              evdev->open--;
      }

      mutex_unlock(&evdev->mutex);
      return retval;
  }


- read函数

::

      static ssize_t evdev_read(struct file *file, char __user *buffer,
                size_t count, loff_t *ppos)
      {
          struct evdev_client *client = file->private_data;
          struct evdev *evdev = client->evdev;  //得到应用程序读取数据的设备
          struct input_event event;
          size_t read = 0;
          int error;

          if (count != 0 && count < input_event_size()) //读取的数据长度至少要满足一个input_event的大小
              return -EINVAL;

          for (;;) {
              if (!evdev->exist || client->revoked)
                  return -ENODEV;

                //当client缓冲区无数据，文件非阻塞打开，则直接返回错误
              if (client->packet_head == client->tail &&
                  (file->f_flags & O_NONBLOCK))
                  return -EAGAIN;

              /*
               * count == 0 is special - no IO is done but we check
               * for error conditions (see above).
               */
              if (count == 0)
                  break;

              while (read + input_event_size() <= count &&
                     evdev_fetch_next_event(client, &event)) {

                  if (input_event_to_user(buffer + read, &event))   //将数据拷贝到用户空间
                      return -EFAULT;

                  read += input_event_size();
              }

              if (read)
                  break;

              //当client没有数据时，将应用程序添加到evdev->wait等待队列
              if (!(file->f_flags & O_NONBLOCK)) {
                  error = wait_event_interruptible(evdev->wait,
                          client->packet_head != client->tail ||
                          !evdev->exist || client->revoked);
                  if (error)
                      return error;
              }
          }

          return read;
      }


::

      static int evdev_fetch_next_event(struct evdev_client *client,
                    struct input_event *event)
      {
          int have_event;
      
          spin_lock_irq(&client->buffer_lock);
      
          have_event = client->packet_head != client->tail; //头不等于尾说明有数据
          if (have_event) {
              *event = client->buffer[client->tail++];  //一次读完一个包
              client->tail &= client->bufsize - 1;
          }
      
          spin_unlock_irq(&client->buffer_lock);

          return have_event;
      }






