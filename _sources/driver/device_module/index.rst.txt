设备模型
==========

sysfs
-----

sysfs是一个基于内存的虚拟的文件系统，有kernel提供，挂载到/sys目录下，负责以设备树的形式向user space提供直观的设备和驱动信息。

sysfs以不同的视角展示当前系统接入的设备：

- /sys/block 历史遗留问题，存放块设备，提供一设备名(如sda)到/sys/devices的符号链接

- /sys/bus 按总线类型分类，在某个总线目录之下可以找到链接该总线的设备的符号链接，指向/sys/devices. 某个总线目录之下的drivers目录
  包含了该总线所需的所有驱动的符号链接。对应kernel中的struct bus_type

- /sys/calss 按设备功能分类，如输入设备在/sys/class/input之下，图形设备在/sys/class/graphics之下，是指向/sys/devices的符号链接。
  对应kernel中的struct class

- /sys/dev 按设备驱动程序分层(字符设备 块设备)，提供以major:minor为名到/sys/devices的符号链接。 对应Kernel中的struct device_driver

- /sys/devices 包含所有被发现的注册在各种总线上的各种物理设备。
  所有物理设备都按其在总线上的拓扑结构来显示，除了platform devices和system devices。
  platform devices 一般是挂载在芯片内部高速或者低速总线上的各种控制器和外设，能被CPU直接寻址。
  system devices不是外设，而是芯片内部的核心结构，比如CPU，timer等。对应kernel中的strcut device

- /sys/firmware 提供对固件的查询和操作接口(关于固件有专用于固件加载的一套api)

- /sys/fs 描述当前加载的文件系统，提供文件系统和文件系统已挂载的设备信息。

- /sys/kernel 提供kernel所有可调整参数，但大多数可调整参数依然存放在sysctl(/proc/sys/kernel)

- /sys/module 所有加载模块(包括内联、编译进kernel、外部的模块)信息，按模块类型分类。

- /sys/power 电源选项，可用于控制整个机器的电源状态，如写入控制命令进行关机、重启等。

sysfs支持多视角查看，通过符号链接，同样的信息可出现在多个目录下。

以硬盘sda为例，既可以在块设备目录/sys/block下找到，又可以在/sys/devices/pci0000:00/0000:00:10.0/host32/target32:0:0/下找到

统一设备模型
------------

linux统一设备模型中， ``kset`` ， ``kobject`` ， ``ktype`` 是实现设备模型的三个重要概念，他们构成了设备模型的基石

kobject/kset/ktype
^^^^^^^^^^^^^^^^^^^^

统一设备模型中最基本的对象

- kobject (设备对象)

::

    struct kobject{
        const char *name;               //名称，对应sysfs下的一个目录
        struct list_head entry;         //加入kset链表的结构
        struct kobject *parent;         //父节点指针，构成树状结构
        struct kset *kset;              //指向所属的kset
        struct kobj_type *ktype;        //类型
        struct kernfs_node *sd;         //VFS文件系统中的目录项，指向所属(sysfs)目录项
        struct kref kref;               //引用计数

        unsigned int state_initialized:1;           //是否已经初始化
        unsigned int state_in_sysfs:1;              //是否已经在sysfs中显示
        unsigned int state_add_uevent_sent:1;       //是否已经向user space发送add uevent
        unsigned int state_remove_uevent_sent:1;
        unsigned int uevent_suppress:1;             //是否忽略上报
    };

- kobj_type 

::

    struct kobj_type{
        void (*release)(struct kobject *kobj);          //析构函数，kobject的引用计数为0时调用
        const struct sysfs_ops *sysfs_ops;              //操作函数，当用户读取sysfs属性时调用show(),写入sysfs属性时调用store()
        struct attribute **default_attrs;               //默认属性，体现为该kobject目录下的文件
        const struct kobject_ns_type_operations *(*child_ns_type)(struct kobject *kobj);   //namespace 操作函数
        const void *(*namespace)(struct kobject *kobj);
    };

实际上这里实现的类似与对kobject的派生，包含不同kobj_type的kobject可以看作不同的子类。通过实现相同的函数来实现多态。
每一个kobject的数据结构(如kset、device、device_driver等)，都要实现自己的kobj_type，并实现其中的函数。

kobj_type的定义会如实的在sysfs中反映，其中的属性attribute会以attribute.name为文件名在该目录下创建文件，对该文件进行读写会调用
sysfs_ops 中定义的show()和store()

- kset

kobject的容器，维护了其包含的kobject链表，链表的最后一项指向kset.kobj，用于表示某一类型的kobject

::

    struct kset{
        struct list_head list;          //kobject链表头
        spinlock_t list_lock;           //自旋锁，保障操作安全
        struct kobject kobj;            //自身的kobject,也是归属于此kset的所有kobject的共同parent
        const struct kset_uevent_ops *uevent_ops;       //uevent 操作函数集。
    };

注意和kobj_type的关联，kobject会利用成员kset找到自己所属的kset，设置自身的ktype为kset.kobj.ktype。当没有指定的kset成员时，才会用ktype来建立关系。

.. note::
    kobject调用的是它所属的kset的uevent操作函数来发送uevent，如果kobject不属于任何kset，则无法发送uevent

device/driver/bus/class
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

linux设备模型的更上一层的表述是device/driver/bus/class。他们都定义在include/linux/device.h中

1)  /sys/bus 目录下的每个子目录都是注册好了的总线类型，每个子目录下包含两个子目录(devices和driver文件夹)。其中devices下是该总线类型下的所有设备，
    这些设备都是符号链接，指向/sys/devices。

2)  /sys/devices 目录是是全局设备结构体系，包含所有被发现的注册在总线上的各种物理设备。

3)  /sys/class  目录则是包含所有注册在kernel中的设备类型。

下图是一个usb设备的设备去驱动拓扑图

.. image::  
   res/linux_device_model01.png

在总线上管理着两个链表，分别管理着设备和驱动，当我们向系统注册一个驱动时，便会向驱动的管理链表插入我们的新驱动，同样当我们向系统注册一个设备时，便会
向设备的管理链表插入我们的新设备。在插入的同时总线会执行一个 ``bus_type`` 结构体中的 ``match`` 方法对新插入的设备/驱动进行匹配。匹配成功后会调用
device_driver结构体中probe方法，移除驱动或者设备时调用device_driver结构体中的remove方法。


- device

device描述了一项设备，对应数据结构device

::

    struct device{
        struct device *parent;  //表示该设备的父对象
        struct device_private *p;
        strcut kobject kobj;    //内嵌kobject，用于在sysfs中表达
        const char *init_name;  //指定设备名字
        const struct device_type  *type;
        struct mutex mutex;
        struct bus_type *bus;
        struct device_driver *driver; //表示该设备对应的驱动
        struct class *class;    //表示该设备挂载在哪条总线，当我们注册设备时，内核便会将该设备注册到对应的总线。
    };

可以使用以下函数注册和注销设备

::

    int device_register(struct device *dev);
    void device_unregister(struct device *dev);

其中维护了类型为device_private的指针p

::

    struct device_private{
        struct klist list_children;
        struct klist_node knode_parent;
        struct klist_node knode_driver;
        struct klist_node knode_bus;
        struct list_head deferred_probe;
        struct device *device;
    };

klist_node 用来作为所属driver链表，所属bus链表中的节点。

设备通过device_register来注册到系统中，通过device_unregister来从系统中卸载。

- driver

设备依赖于driver来进行驱动，对应的数据结构为device_driver

::

    struct device_driver{
        const char *name;       //驱动名称
        struct bus_type *bus;   //挂载在哪种总线上
        
        strcut module *owner;
        const char *mod_name;
        
        bool suppress_bind_attrs;//用于指定是否通过sysfs导出bind与unbind文件，
                                 //bind和unbind文件时驱动用于绑定/解绑关联的设备。
        enum probe_type probe_type;
        
        const strcut of_device_id *of_match_table; //指定驱动支持的设备类型，当内核使能设备树时，
                        //会利用该成员与设备树中的 ``compatible`` 属性进行比较
        const struct acpi_device_id *acpi_match_table;

        int(*probe)(strcut device *dev);    //设备与驱动匹配后会执行该回调函数
        int(*remove)(struct device *dev);
        void (*shutdown)(struct device *dev);
        int(*suspend)(struct device *dev, pm_message_t state);
        int(*resume)(struct device *dev);
        const struct attribute_group **groups;  //表示驱动的属性
        const struct dev_pm_ops *pm;

        struct driver_private *p;
    };

其中维护了类型为driver_private的指针p

::

    struct driver_private{
        struct kobject kobj;
        struct klist klist_device;
        struct klist_node knode_bus;
        struct module_kobject *mkobj;
        struct device_driver *driver;
    };

其维护了dirver自身的私有属性，比如由于他也是kobject的子类，因此包含了kobj。可通过driver_cteate_file/ dirver_remove_file来增删属性，属性将直接作用于p->kobj.

- bus

设备总是挂载在某一条总线上的，对应的数据结构为bus_type

::

    struct bus_type{
        const char *name;   //指定总线名称，会在/sys/bus目录下创建一个新的目录，目录名称就是该参数的值
        const char *dev_name;
        struct device *dev_root;
        struct device_attribute *dev_attrs;
        //分别表示总线、设备、驱动的属性。这些属性可以时内部变量、字符串等等，
        const struct attribute_group **bus_groups;
        const struct attribute_group **dev_groups;
        const struct attribute_group **drv_groups;
        //当向总线注册一个新的设备或者新的驱动时，会调用该回调函数。
        int (*match)(struct device *dev, struct device_driver *drv);
        //当总线上的设备发生添加、移除就会调用该函数。
        int (*uevent)(struct device *dev, struct kobj_uvent_env *env);
        //设备和驱动匹配后会调用该函数。
        int (*probe)(struct device *dev);
        int (*remove)(struct device *dev);
        void (*shutdown)(struct device *dev);

        int (*online)(struct device *dev);
        int (*offline)(struct device *dev);

        int (*suspend)(struct device *dev,pm_message_t state);
        int (*resume)(struct device *dev);
        //该结构它用于存放特定的私有数据，其成员klist_devices和klist_drivers记录了挂载在该总线上的设备和驱动。
        struct subsys_private *p;
        struct lock_class_key lock_key;
    };


通过以下函数注册和注销bus

::

    int bus_register(struct bus_type *bus);
    void bus_ungister(struct bus_type *bus);

其中维护了类型为subsys_private的指针P

::

    struct subsys_private{
        struct kset subsys;
        struct kset *devices_kset;
        struct list_head interface;
        struct mutex mutex;

        struct kset *drivers_kset;
        struct klist klist_devices;
        struct klist klist_drivers;
        struct blocking_nottifier_head bus_notifier;
        unsigned int drivers_autoprober:1;
        struct bus_type *bus;

        struct kset glue_dirs;
        struct class *class;
    };

它维护了bus自身的私有属性，它维护了挂载在该总线上的设备集合device_kset和与该总线相关的驱动程序集合drivers_kset

对应到sysfs中，每个bus_type对象对应/sys/bus目录下的一个子目录，子目录下必有devices和dirver文件夹，里面存放指向设备和驱动的符号链接。

下图是总线上关联设备和驱动之后的数据结构关系图：

.. image::  
   res/linux_device_driver_bus.png

- class

class对应一种设备分类，对应的数据结构为class

::

    struct class{
        const char *name;
        struct module *owner;

        struct class_attribute *class_attrs;
        const struct attribute_group **dev_grpoups;
        struct kobject *dev_kobj;

        int (*dev_uevent)(struct device *dev,struct kobj_uvent_env *env);
        char *(*devnode)(struct device *dev, umode_t *mode);

        void (*class_release)(struct class *class);
        void (*dev_release)(struct device *dev);

        int (*suspend)(struct device *dev,pm_message_t state);
        int (*resume)(struct device *dev);
        int (*shutdown)(struct device *dev);

        const struct kobj_ns_type_operation *ns_type;
        const void *(*namespace)(struct device *dev);

        const struct dev_pm_ops *pm;

        struct subsys_private *p;
    };

class 只是一种抽象的概念，用于描述接口相似的一类设备。

**小结**

- driver用于驱动device，其保存了所有能够被它所驱动的设备链表。

- bus是连接driver和device的桥梁，其保存了所有挂载在它上面的设备链表和驱动这些设备的驱动链表。

- class用于描述一类device，其保存了所有该类device的设备链表。


attribute
^^^^^^^^^^^^

用于定义设备模型中的各项属性，基本属性有两种，分别为普通属性attribute和二进制属性bin_attribute

::

    struct attribute{
        const char *name;
        umode_t mode;
        #ifdef CONFIG_DEBUG_LOCK_ALLOC
        bool ignore_lockdep:1;
        struct lock_class_key *key;
        struct lock_class_ket skey;
        #endif 
    };

    struct bin_attribute{
        struct attribute attr;
        size_t size;
        void *private;
        ssize_t (*read)(struct file *,struct kobject *,struct bin_attribute *,char *, loff_t , size_t);
        ssize_t (*write)(struct file *,struct kobject *,struct bin_attribute *,char *, loff_t ,size_t);
        int (*mmap)(struct file *,struct kobject *,struct bin_attribute *attr, struct vm_area_struct *vma);
    };

使用attribute生成的sysfs文件，只能用字符串的形式读写，而struct bin_attribute在attribute的基础上，增加了read、write函数，因此
它生成的sysfs文件可以用任何方式读写。

- attribute_gpoup

顾名思义就是属性组，将一组属性打包成一个对象，其包含了以attribute和bin_attribute指针数组。

::

    struct attribute_group{
        const char *name;
        umode_t (*is_visible)(struct kobject *,struct attribute *,int);
        umode_t (*is_bin_visible)(struct kobject *, struct bin_attribute *, int);
        struct attribute **attrs;
        struct bin_attribute **bin_attrs;
    };

- sysfs 映射

sysfs本质上是对统一设备模型中的各结构的映射。换句话说sysfs本质上就是通过vfs接口去读写kobject的层次结构后动态建立的内存文件系统。

::

    int __init sysfs_init(void)
    {
        int err;

        sysfs_root = kernfs_create_root(NULL, KERNFS_ROOT_EXTRA_OPEN_PERM_CHEACK, NULL);
        if(IS_ERR(sysfs_root))
            return PTR_ERR(sysfs_root);

        sysfs_root_kn = sysfs_root->kn;

        err = register_filesystem(&sysfs_fs_type);
        if(err)
        {
            kernfs_destroy_root(sysfs_root);
            return err;
        }
        return 0;
    }

sysfs_init通过kernfs_create_root创建新的kernfs层级，然后将其保存在静态全局变量中，供各处使用，然后通过register_filesystem将其注册到名
为sysfs的文件系统中。

- 目录映射

kobject 在sysfs中对应的是目录(dir)

当我们注册一个kobject时，会调用kobject_add 于是

::

    kobject_add===>kobject_add_varg===>kobject_add_internal===>create_dir====>sysfs_create_dir_ns

如果kobj有parent，则它的父节点为kobj->parent->sd

- 属性映射

属性在sysfs中对应的是文件(file)

当需要为设备添加属性时，可以调用device_create_file，于是

::

    deivice_create_file===>sysfs_create_file===>sysfs_create_file_ns====>sysfs_add_file_mode_ns===>__kernfs_create_file

创建的文件大小即为存放该属性值的长度，对于普通属性来说，大小为 PAGE_SIZE(4K)，而对于二进制属性来说，大小由属性自定义，即 bin_attribute.size 指定。

当用户对属性文件进行读写时，会调用绑定的读写函数，比如对于 mode 为 SYSFS_PREALLOC 且 kobj->ktype->sysfs_ops 定义了 show 和 store 函数的属性，
绑定是 sysfs_prealloc_kfops_rw 。这里的 kobj 指的是该属性的父节点，也就是属性所属设备的 kobj。

于是在读文件时，调用 sysfs_kf_read ，它会根据属性文件找到其父节点类型对应的 sysfs_ops ，然后调用 sysfs_ops.show 。show 需要将输出写到传入的 buf 缓冲区中，
并返回写入的长度。

在写文件时，调用 sysfs_kf_write ，它会根据属性文件找到其父节点类型对应的 sysfs_ops ，然后调用 sysfs_ops.store 。 store 可以从传入的 buf 缓冲区中，
读取用户写入的长度为 len 的内容。

但是需要注意的是， sysfs_ops 中的 show 和 store 函数并非是读写我们属性所需要的 show 和 store 。因为一个设备只有一个类型，因此 sysfs_ops 打扰 show 和 store
只有一种实现，但实际上 show 和 store 应该根据属性的不同而不同。怎么办呢？绕个弯子：在调用 sysfs_ops.show 和 sysfs_ops.store 时传入属性 attribute 的指针，
然后在函数中将指针转换为设备类型对应属性的指针后调用属性的 show 和 store 函数。这也就是 device_attribute 、 class_attribute 或一些设备自定义属性
(比如 cpuidle_driver_attr) 中定义有 show 和 store 函数的原因。




