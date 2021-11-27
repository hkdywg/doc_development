输入核心层
============

输入核心层，是input子系统实现的核心。对上(事件驱动层)提供事件注册接口等，对下(设备驱动层)提供设备注册接口，输入信息反馈接口


设备驱动层接口
---------------


1. 申请设备描述符结构体变量，同时初始化一些通用性数据结构

::

      /**
       * input_allocate_device - allocate memory for new input device
       *
       * Returns prepared struct input_dev or %NULL.
       *
       * NOTE: Use input_free_device() to free devices that have not been
       * registered; input_unregister_device() should be used for already
       * registered devices.
       */
      struct input_dev *input_allocate_device(void)
      {
          static atomic_t input_no = ATOMIC_INIT(-1);
          struct input_dev *dev;

          dev = kzalloc(sizeof(*dev), GFP_KERNEL);
          if (dev) {
              dev->dev.type = &input_dev_type;  //绑定设备信息
              dev->dev.class = &input_class;       //绑定在sysfs所属的类
              device_initialize(&dev->dev);        //设备初始化
              mutex_init(&dev->mutex);
              spin_lock_init(&dev->event_lock);
              timer_setup(&dev->timer, NULL, 0);    //内核定时器初始化
              INIT_LIST_HEAD(&dev->h_list);
              INIT_LIST_HEAD(&dev->node);

              dev_set_name(&dev->dev, "input%lu",
                       (unsigned long)atomic_inc_return(&input_no));

              __module_get(THIS_MODULE);
          }

          return dev;
      }

2. 设置dev设备的能力，只有注册前设置它的能力，将来设备注册后，发送的信息才能上报。注:该函数每次只能设置一个能力

根据type类型设置code到相应的typebit

::

     /**
       * input_set_capability - mark device as capable of a certain event
       * @dev: device that is capable of emitting or accepting event
       * @type: type of the event (EV_KEY, EV_REL, etc...)
       * @code: event code
       *
       * In addition to setting up corresponding bit in appropriate capability
       * bitmap the function also adjusts dev->evbit.
       */
      void input_set_capability(struct input_dev *dev, unsigned int type, unsigned int code)
      {
          switch (type) {
          case EV_KEY:
              __set_bit(code, dev->keybit);
              break;

          case EV_REL:
              __set_bit(code, dev->relbit);
              break;

          case EV_ABS:
              input_alloc_absinfo(dev);
              if (!dev->absinfo)
                  return;

              __set_bit(code, dev->absbit);
              break;

          case EV_MSC:
              __set_bit(code, dev->mscbit);
              break;

          case EV_SW:
              __set_bit(code, dev->swbit);
              break;

          case EV_LED:
              __set_bit(code, dev->ledbit);
              break;

          case EV_SND:
              __set_bit(code, dev->sndbit);
              break;

          case EV_FF:
              __set_bit(code, dev->ffbit);
              break;

          case EV_PWR:
              /* do nothing */
              break;


              default:
          pr_err("%s: unknown type %u (code %u)\n", __func__, type, code);
          dump_stack();
          return;
      }

      __set_bit(type, dev->evbit);
    }


3. 具体设备注册(需要前两步申请空间和填充能力才能注册)

::

    
    int input_register_device(struct input_dev *dev)
    {
        struct input_devres *devres = NULL;
        struct input_handler *handler;
        unsigned int packet_size;
        const char *path;
        int error;

        if (test_bit(EV_ABS, dev->evbit) && !dev->absinfo) {
            dev_err(&dev->dev,
                "Absolute device without dev->absinfo, refusing to register\n");
            return -EINVAL;
        }

        if (dev->devres_managed) {
            devres = devres_alloc(devm_input_device_unregister,
                          sizeof(*devres), GFP_KERNEL);
            if (!devres)
                return -ENOMEM;

            devres->input = dev;
        }

        /* Every input device generates EV_SYN/SYN_REPORT events. */
        __set_bit(EV_SYN, dev->evbit);  //通用的同步包

        /* KEY_RESERVED is not supposed to be transmitted to userspace. */
        __clear_bit(KEY_RESERVED, dev->keybit);

        /* Make sure that bitmasks not mentioned in dev->evbit are clean. */
        input_cleanse_bitmasks(dev);

        packet_size = input_estimate_events_per_packet(dev);
        if (dev->hint_events_per_packet < packet_size)
            dev->hint_events_per_packet = packet_size;

        dev->max_vals = dev->hint_events_per_packet + 2;
        dev->vals = kcalloc(dev->max_vals, sizeof(*dev->vals), GFP_KERNEL);
        if (!dev->vals) {
            error = -ENOMEM;
            goto err_devres_free;
        }

        /*
         * If delay and period are pre-set by the driver, then autorepeating
         * is handled by the driver itself and we don't do it in input.c.
         */
        if (!dev->rep[REP_DELAY] && !dev->rep[REP_PERIOD])
            input_enable_softrepeat(dev, 250, 33);

        if (!dev->getkeycode)
            dev->getkeycode = input_default_getkeycode;

        if (!dev->setkeycode)
            dev->setkeycode = input_default_setkeycode;

        if (dev->poller)
            input_dev_poller_finalize(dev->poller);

        error = device_add(&dev->dev);
        if (error)
            goto err_free_vals;

        path = kobject_get_path(&dev->dev.kobj, GFP_KERNEL);
        pr_info("%s as %s\n",
            dev->name ? dev->name : "Unspecified device",
            path ? path : "N/A");
        kfree(path);

        error = mutex_lock_interruptible(&input_mutex);
        if (error)
            goto err_device_del;

        list_add_tail(&dev->node, &input_dev_list);

        list_for_each_entry(handler, &input_handler_list, node)
            input_attach_handler(dev, handler);

        input_wakeup_procfs_readers();

        mutex_unlock(&input_mutex);

        if (dev->devres_managed) {
            dev_dbg(dev->dev.parent, "%s: registering %s with devres.\n",
                __func__, dev_name(&dev->dev));
            devres_add(dev->dev.parent, devres);
        }
        return 0;

    err_device_del:
        device_del(&dev->dev);
    err_free_vals:
        kfree(dev->vals);
        dev->vals = NULL;
    err_devres_free:
        devres_free(devres);
        return error;
    }
    EXPORT_SYMBOL(input_register_device);


4. handler和dev做匹配，如果匹配上则把两者绑定

::

    static int input_attach_handler(struct input_dev *dev, struct input_handler *handler)
    {
        const struct input_device_id *id;
        int error;
     
        id = input_match_device(handler, dev);    /* 匹配handler和dev */
        if (!id)
            return -ENODEV;
     
        error = handler->connect(handler, dev, id);    /* 做具体的绑定handler和dev工作，由具体的事驱动层实现 */
        if (error && error != -ENODEV)
            printk(KERN_ERR
                "input: failed to attach handler %s to device %s, "
                "error: %d\n",
                handler->name, kobject_name(&dev->dev.kobj), error);
     
        return error;
    }

此函数在注册dev和handler的时候都会调用

5. 匹配handler和dev

每一个事件驱动层在实现的时候都要实现一个struct input_device_id的表，用来表示该事件驱动可以支持的设备

struct input_device_id数据结构如下

::

      struct input_device_id {

          kernel_ulong_t flags; //flag表明下面四个要不要匹配

          __u16 bustype;
          __u16 vendor;
          __u16 product;
          __u16 version;

          kernel_ulong_t evbit[INPUT_DEVICE_ID_EV_MAX / BITS_PER_LONG + 1];
          kernel_ulong_t keybit[INPUT_DEVICE_ID_KEY_MAX / BITS_PER_LONG + 1];
          kernel_ulong_t relbit[INPUT_DEVICE_ID_REL_MAX / BITS_PER_LONG + 1];
          kernel_ulong_t absbit[INPUT_DEVICE_ID_ABS_MAX / BITS_PER_LONG + 1];
          kernel_ulong_t mscbit[INPUT_DEVICE_ID_MSC_MAX / BITS_PER_LONG + 1];
          kernel_ulong_t ledbit[INPUT_DEVICE_ID_LED_MAX / BITS_PER_LONG + 1];
          kernel_ulong_t sndbit[INPUT_DEVICE_ID_SND_MAX / BITS_PER_LONG + 1];
          kernel_ulong_t ffbit[INPUT_DEVICE_ID_FF_MAX / BITS_PER_LONG + 1];
          kernel_ulong_t swbit[INPUT_DEVICE_ID_SW_MAX / BITS_PER_LONG + 1];
          kernel_ulong_t propbit[INPUT_DEVICE_ID_PROP_MAX / BITS_PER_LONG + 1];

          kernel_ulong_t driver_info;
      };


::

      static const struct input_device_id *input_match_device(struct input_handler *handler,
                              struct input_dev *dev)
      {
          const struct input_device_id *id;
      
          for (id = handler->id_table; id->flags || id->driver_info; id++) {
              if (input_match_device_id(dev, id) &&
                  (!handler->match || handler->match(handler, dev))) {
                  return id;
              }
          }
      
          return NULL;
      }

      bool input_match_device_id(const struct input_dev *dev,
                 const struct input_device_id *id)
      {
          if (id->flags & INPUT_DEVICE_ID_MATCH_BUS)
              if (id->bustype != dev->id.bustype)
                  return false;
      
          if (id->flags & INPUT_DEVICE_ID_MATCH_VENDOR)
              if (id->vendor != dev->id.vendor)
                  return false;
      
          if (id->flags & INPUT_DEVICE_ID_MATCH_PRODUCT)
              if (id->product != dev->id.product)
                  return false;
      
          if (id->flags & INPUT_DEVICE_ID_MATCH_VERSION)
              if (id->version != dev->id.version)
                  return false;
      
          if (!bitmap_subset(id->evbit, dev->evbit, EV_MAX) ||
              !bitmap_subset(id->keybit, dev->keybit, KEY_MAX) ||
              !bitmap_subset(id->relbit, dev->relbit, REL_MAX) ||
              !bitmap_subset(id->absbit, dev->absbit, ABS_MAX) ||
              !bitmap_subset(id->mscbit, dev->mscbit, MSC_MAX) ||
              !bitmap_subset(id->ledbit, dev->ledbit, LED_MAX) ||
              !bitmap_subset(id->sndbit, dev->sndbit, SND_MAX) ||
              !bitmap_subset(id->ffbit, dev->ffbit, FF_MAX) ||
              !bitmap_subset(id->swbit, dev->swbit, SW_MAX) ||
              !bitmap_subset(id->propbit, dev->propbit, INPUT_PROP_MAX)) {
              return false;
          }

          return true;
      }


事件驱动层
-----------

1. handler注册

::

      int input_register_handler(struct input_handler *handler)
      {
          struct input_dev *dev;
          int error;

          error = mutex_lock_interruptible(&input_mutex);
          if (error)
              return error;

          INIT_LIST_HEAD(&handler->h_list); //初始化链表

          list_add_tail(&handler->node, &input_handler_list); //加入到input_handler_list链表中

          list_for_each_entry(dev, &input_dev_list, node)
              input_attach_handler(dev, handler);           //dev与handler匹配

          input_wakeup_procfs_readers();    //更新proc系统

          mutex_unlock(&input_mutex);
          return 0;
      }
      EXPORT_SYMBOL(input_register_handler); 


2. handle的注册(其实就是把handler和dev的链表加入到handle的数据中)

::

      int input_register_handle(struct input_handle *handle)
      {
          struct input_handler *handler = handle->handler;
          struct input_dev *dev = handle->dev;
          int error;

          /*
           * We take dev->mutex here to prevent race with
           * input_release_device().
           */
          error = mutex_lock_interruptible(&dev->mutex);
          if (error)
              return error;

          /*
           * Filters go to the head of the list, normal handlers
           * to the tail.
           */
          if (handler->filter)
              list_add_rcu(&handle->d_node, &dev->h_list);
          else
              list_add_tail_rcu(&handle->d_node, &dev->h_list);

          mutex_unlock(&dev->mutex);

          /*
           * Since we are supposed to be called from ->connect()
           * which is mutually exclusive with ->disconnect()
           * we can't be racing with input_unregister_handle()
           * and so separate lock is not needed here.
           */
          list_add_tail_rcu(&handle->h_node, &handler->h_list);

          if (handler->start)
              handler->start(handle);

          return 0;
      }



























