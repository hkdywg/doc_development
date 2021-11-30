platform驱动
==============

数据结构
---------

linux内核使用bus_type结构体表示总线

::

	 [include/linux/device.h]
     struct bus_type {
      const char      *name;	//总线名字
      const char      *dev_name;
      struct device       *dev_root;
      const struct attribute_group **bus_groups;	//总线属性
      const struct attribute_group **dev_groups;	//设备属性
      const struct attribute_group **drv_groups;	//驱动属性

      int (*match)(struct device *dev, struct device_driver *drv);
      int (*uevent)(struct device *dev, struct kobj_uevent_env *env);
      int (*probe)(struct device *dev);
      int (*remove)(struct device *dev);
      void (*shutdown)(struct device *dev);

      int (*online)(struct device *dev);
      int (*offline)(struct device *dev);

      int (*suspend)(struct device *dev, pm_message_t state);
      int (*resume)(struct device *dev);

      int (*num_vf)(struct device *dev);

      int (*dma_configure)(struct device *dev);

      const struct dev_pm_ops *pm;

      const struct iommu_ops *iommu_ops;

      struct subsys_private *p;
      struct lock_class_key lock_key;
  
      bool need_parent_lock;
  }; 

platform总线是bus_type的一个具体实例

::

	  [drivers/base/platform.c]
	  struct bus_type platform_bus_type = {
		  .name       = "platform",
		  .dev_groups = platform_dev_groups,
		  .match      = platform_match,
		  .uevent     = platform_uevent,
		  .dma_configure  = platform_dma_configure,
		  .pm     = &platform_dev_pm_ops,
	  };
	  EXPORT_SYMBOL_GPL(platform_bus_type);	

linux设备驱动模型下的总线都有两个重要的结构体:描述设备和驱动的结构体

::
	
	  [include/linux/platform_device.h]
	  struct platform_device {
		  const char  *name;
		  int     id;
		  bool        id_auto;
	      struct device   dev;	//嵌入device结构体
	      u64     platform_dma_mask;
	      u32     num_resources;
		  struct resource *resource;
	  
		  const struct platform_device_id *id_entry;
		  char *driver_override; /* Driver name to force a match */
	  
		  /* MFD cell pointer */
		  struct mfd_cell *mfd_cell;

		  /* arch specific additions */
	      struct pdev_archdata    archdata;
	  };	


::

	  struct platform_driver {
		  int (*probe)(struct platform_device *);
		  int (*remove)(struct platform_device *);
		  void (*shutdown)(struct platform_device *);
		  int (*suspend)(struct platform_device *, pm_message_t state);
		  int (*resume)(struct platform_device *);
		  struct device_driver driver;		//嵌入device_driver结构体
		  const struct platform_device_id *id_table;
		  bool prevent_deferred_probe;
	  };


platform驱动和设备的匹配
-------------------------

platform_bus_type是platform平台总线，其中platfrom_match就是匹配函数


::

	  static int platform_match(struct device *dev, struct device_driver *drv)
	  {
		  struct platform_device *pdev = to_platform_device(dev);
		  struct platform_driver *pdrv = to_platform_driver(drv);

		  /* When driver_override is set, only bind to the matching driver */
		  if (pdev->driver_override)
			  return !strcmp(pdev->driver_override, drv->name);

		  /* Attempt an OF style match first */
		  if (of_driver_match_device(dev, drv))
			  return 1;

		  /* Then try ACPI style match */
		  if (acpi_driver_match_device(dev, drv))
			  return 1;

		  /* Then try to match against the id table */
		  if (pdrv->id_table)
			  return platform_match_id(pdrv->id_table, pdev) != NULL;

		  /* fall-back to driver name match */
		  return (strcmp(pdev->name, drv->name) == 0);
	  }

of设备树匹配
^^^^^^^^^^^^^^^

OF类型的匹配，也就是设备树采用的匹配方式，Of_driver_match_device函数在文件include/linux/of_device.h中，device_driver结构体(表示设备驱动)中有个名为
of_match_table的成员变量，此成员变量保存着驱动的compatible匹配表，设备树中每个设备节点的compatible属性会和of_match_table表中的所有成员进行比较，查看
是否有相同的条目,如果有则表示设备和驱动匹配，匹配成功后probe函数就会执行

函数原型如下

::

	/**
	 * of_driver_match_device - Tell if a driver's of_match_table matches a device.
	 * @drv: the device_driver structure to test
	 * @dev: the device structure to match against
	 */
	static inline int of_driver_match_device(struct device *dev,
						 const struct device_driver *drv)
	{
		
		return of_match_device(drv->of_match_table, dev) != NULL;
	}

device_driver结构体如下

::

	struct device_driver {
		
		const char		*name;
		struct bus_type		*bus;

		struct module		*owner;
		const char		*mod_name;	/* used for built-in modules */

		bool suppress_bind_attrs;	/* disables bind/unbind via sysfs */

		const struct of_device_id	*of_match_table;
		const struct acpi_device_id	*acpi_match_table;

		int (*probe) (struct device *dev);
		int (*remove) (struct device *dev);
		void (*shutdown) (struct device *dev);
		int (*suspend) (struct device *dev, pm_message_t state);
		int (*resume) (struct device *dev);
		const struct attribute_group **groups;

		const struct dev_pm_ops *pm;

		struct driver_private *p;
	};

of_match_table就是采用设备树的时候驱动使用的匹配表,类型为of_device_id

::

	 struct of_device_id {
		
		 char name[32];
		 char type[32];
		 char compatible[128];
		 const void *data;
	};



示例如下

::

	  static const struct of_device_id omap_rtc_of_match[] = {
		  {
			  .compatible = "ti,am3352-rtc",
			  .data       = &omap_rtc_am3352_type,
		  }, {
			  .compatible = "ti,da830-rtc",
			  .data       = &omap_rtc_da830_type,
		  }, {
			  /* sentinel */
		  }
	  };
	  MODULE_DEVICE_TABLE(of, omap_rtc_of_match);


::

	  static struct platform_driver omap_rtc_driver = {
		  .probe      = omap_rtc_probe,
		  .remove     = omap_rtc_remove,
		  .shutdown   = omap_rtc_shutdown,
		  .driver     = {
			  .name   = "omap_rtc",
			  .pm = &omap_rtc_pm_ops,
			  .of_match_table = omap_rtc_of_match,
		  },
		  .id_table   = omap_rtc_id_table,
	  };

acpi匹配
^^^^^^^^^^^

如果of_driver_match_device没有匹配到则使用acpi进行匹配。首先从device中找到对应的acpi_device，找到acpi_device设备后就可以进行匹配了。acpi设备使用两种方式匹配

::

	  [drivers/acpi/bus.c]
	  bool acpi_driver_match_device(struct device *dev,
						const struct device_driver *drv)
	  {
		  if (!drv->acpi_match_table)
			  return acpi_of_match_device(ACPI_COMPANION(dev),
							  drv->of_match_table,
							  NULL);

		  return __acpi_match_device(acpi_companion_match(dev),
						 drv->acpi_match_table, drv->of_match_table,
						 NULL, NULL);
	  }
	  EXPORT_SYMBOL_GPL(acpi_driver_match_device);


id_table匹配
^^^^^^^^^^^^^^

id_table匹配，每个platform_driver结构体有一个id_table成员变量，顾名思义，保存了很多id信息。这些id信息存放着这个platform驱动所支持的驱动类型

示例如下

::

	  static const struct platform_device_id omap_rtc_id_table[] = {
		  {
			  .name   = "omap_rtc",
			  .driver_data = (kernel_ulong_t)&omap_rtc_default_type,
		  }, {
			  .name   = "am3352-rtc",
			  .driver_data = (kernel_ulong_t)&omap_rtc_am3352_type,
		  }, {
			  .name   = "da830-rtc",
			  .driver_data = (kernel_ulong_t)&omap_rtc_da830_type,
		  }, {
			  /* sentinel */
		  }
	  };


name匹配
^^^^^^^^^

如果前三种方式都不存在的话，就直接比较驱动和设备的那么字段，看看是否相同

::

	  static struct platform_driver omap_rtc_driver = {
		  .probe      = omap_rtc_probe,
		  .remove     = omap_rtc_remove,
		  .shutdown   = omap_rtc_shutdown,
		  .driver     = {
			  .name   = "omap_rtc",	//此字段为device和driver匹配的最后一种方式
			  .pm = &omap_rtc_pm_ops,
			  .of_match_table = omap_rtc_of_match,
		  },
		  .id_table   = omap_rtc_id_table,
	  };

platform总线下的驱动编写流程
-----------------------------

1. 首先定义一个platform_driver结构体变量
2. 然后实现结构体中各个成员变量，重点是实现匹配方式以及probe函数
3. 当我们定义并初始化好platform_driver结构体变量以后，需要在驱动入口函数里面调用platform_driver_register函数向内核注册一个platform驱动
4. 驱动卸载函数中通过platform_driver_unregister函数卸载

框架流程如下

::

	struct xxx_dev{
		
		struct cdev cdev;
		/* 设备结构体其他具体内容 */
	};

	struct xxx_dev xxxdev; /* 定义个设备结构体变量 */

	static int xxx_open(struct inode *inode, struct file *filp)
	{
		
		/* 函数具体内容 */
		return 0;
	}

	static ssize_t xxx_write(struct file *filp, const char __user *buf,
	size_t cnt, loff_t *offt)
	{
		
		/* 函数具体内容 */
		return 0;
	}

	/*
	* 字符设备驱动操作集
	*/
	static struct file_operations xxx_fops = {
		
		.owner = THIS_MODULE,
		 .open = xxx_open,
		.write = xxx_write,
	};

	/*
	* platform 驱动的 probe 函数
	* 驱动与设备匹配成功以后此函数就会执行
	*/
	static int xxx_probe(struct platform_device *dev)
	{
		
		......
		cdev_init(&xxxdev.cdev, &xxx_fops); /* 注册字符设备驱动 */
		/* 函数具体内容 */
		return 0;
	}

	static int xxx_remove(struct platform_device *dev)
	{
		
		......
		cdev_del(&xxxdev.cdev);/* 删除 cdev */
		/* 函数具体内容 */
		return 0;
	}
	/* 匹配列表 */
	static const struct of_device_id xxx_of_match[] = {
		
		{
		 .compatible = "xxx-gpio" },
		{
		 /* Sentinel */ }
	};

	/*
	* platform 平台驱动结构体
	*/
	static struct platform_driver xxx_driver = {
		
		.driver = {
		
		.name = "xxx",
		.of_match_table = xxx_of_match,
		},
		.probe = xxx_probe,
		.remove = xxx_remove,
	};

	 /* 驱动模块加载 */
	static int __init xxxdriver_init(void)
	{
		
		return platform_driver_register(&xxx_driver);
	}

	/* 驱动模块卸载 */
	static void __exit xxxdriver_exit(void)
	{
		
		 platform_driver_unregister(&xxx_driver);
	}

	 module_init(xxxdriver_init);
	 module_exit(xxxdriver_exit);
	 MODULE_LICENSE("GPL");
	 MODULE_AUTHOR("yinwg");


