关于kobject kset 和ktype
==========================

理解那些建立在kobject抽象之上的驱动模型的困难之一就是没有一个明确的入口,使用kobject需要了解几种不同的类型，而这些类型又会互相引用。

- kobject是一个struct kobject类型的对象，kobject包含一个名字和一个引用计数，同时一个kobject还包含一个父指针(允许对象被安排成层次结构)，一个特定的类型，通常
  情况下还有一个在sysfs虚拟文件系统里的表现。通常我们不关心kobject本身，而应该关注那些嵌入了Kobject的那些结构体，任何结构体都不允许包含一个以上的kobject
- ktype是嵌入了kobject的对象的类型，每个嵌入了kobject的对象都需要一个相应的ktype，ktype用来控制当kobject创建和销毁时所发生的操作
- kset是koject的一组集合，这些kobject可以是同样的ktype，也可以分别属于不同的ktype，kset是kobject集合的基本容器类型。kset也包含他们自己的kobject

当你看到一个sysfs目录里全部是其他目录时，通常每一个目录都对应一个在同一个kset里的kobject

kobject结构定义如下

::

    struct kobject {
        const char		*name;
        struct list_head	entry;
        struct kobject		*parent;
        struct kset		*kset;
        struct kobj_type	*ktype;
        struct kernfs_node	*sd; /* sysfs directory entry */
        struct kref		kref;
    #ifdef CONFIG_DEBUG_KOBJECT_RELEASE
        struct delayed_work	release;
    #endif
        unsigned int state_initialized:1;
        unsigned int state_in_sysfs:1;
        unsigned int state_add_uevent_sent:1;
        unsigned int state_remove_uevent_sent:1;
        unsigned int uevent_suppress:1;
    };

内嵌kobject
-------------

就内核代码而言，基本上不会创建一个单独的kobject，kobject通常被用来控制一个更大的特定域对象。因此你将发现kobject都被嵌入到了其他的结构体当中。

比如，driver/uio/uio.c里面uio代码包含了一个定义内存区域的uio设备

::

    struct uio_map {
        struct kobject kobj;
        struct uio_mem *mem;
    }

如果你有一个struct uio_map结构体，使用它的成员kobj就能找到嵌套的kobject，但是操作kobject的代码往往会引出一个相反的问题：如果给定一个struct kobject
指针，那么包含这个指针的结构体又是什么呢？这个时候需要使用container_of()宏函数

::

    container_of(pointer, type, member)

kobject的初始化
---------------

创建一个kobject的代码必须首先初始化这个对象，调用 ``kobject_init()`` 来设置一些内部字段(强制性的):

::

    void kobject_init(struct kobject *kobj, struct kobj_type *ktype);

因为每一个kobject都有一个关联的kobj_type，所以正确创建一个kobject时ktype是必须的，调用kobject_init()之后，必须使用kobject_add()在sysfs上注册kobject

::

    int kobject_add(struct kobject *kobj, struct kobject *parent, const char *fmt, ...);

这将为Kobject设置parent和name，如果这个kobject将关联于一个指定的kset，那么kobj->kset必须在kobject_add()之前被赋值，如果一个kset关联于一个kobject，那么在
调用kobject_add()时parent可以时NULL，这时kobject的parent将会时这个kset本身

还有一个函数可以同时初始化kobject并将其添加至kernel

::

    int kobject_init_and_add(struct kobject *kobj, struct kobj_type *ktype,
                            struct kobject *parent, const char *fmt, ...);


**uevents**

在一个kobject注册到核心之后，你需要通过kobject_uevent()向系统宣布它被创建了

::

    int kobject_uevent(struct kobject *kobj, enum kobject_action action);

当kobject首次被添加进kernel时使用KOBJ_ADD动作，移除时使用KOBJ_REMOVE动作

**引用计数**

一个kobject的主要功能之一就是在它被嵌入的对象中作为一个引用计数器，只要存在对该对象的引用，对象(和支持它的代码)就必须继续存在，操作一个kobject的引用计数的底层函数

::

    struct kobject *kobject_get(struct kobject *kobj);
    void kobject_put(struct kobject *kobj);

另外如果使用kobject的理由仅仅是使用引用计数的话，那么可以使用struct kref替代kobject

创建简单的kobject
------------------

有时开发人员希望有一种创建一个在sysfs层次中简单目录的方式，而并不想搞乱本来就错综复杂的ksets,show,store函数，可以使用如下函数

::

    struct kobject *kobject_create_and_add(char *name, struct kobject *parent);

此函数将创建一个kobject并将其放置在指定的父kobject在sysfs中的目录下，要创建与这个kobject关联的属性，使用函数

::

    int sysfs_create_file(struct kobject *kobj, struct attribute *attr);
    或
    int sysfs_create_group(struct kobject *kobj, struct attribute_group *grp);


ktypes和release方法
-------------------

一个被kobject保护的街头提不饿能在这个kobject引用计数到0之前被释放，而这个引用计数又不被创建这个kobject的代码所直接控制，所以必须在这个kobject的
最后一个引用消失时异步通知这些代码。

每个kobject必须有一个release方法，但是这个release方法并没有直接保存在kobject中而是关联在它的ktype成员中

::

    struct kobj_type {
        void (*release)(struct kobject *kobj);
        const struct sysfs_ops *sysfs_ops;
        struct attribute **default_attrs;
    } 


**kset**

::

    struct kset {
        struct list_head list;
        spinlock_t list_lock;
        struct kobject kobj;
        const struct kset_uevent_ops *uevent_ops;
    } __randomize_layout;

kset仅仅是一个需要相互关联的kobject集合，在这里没有任何规定他们必须是同样的ktye,但如果不是同样type则一定要小心处理

kset提供以下功能:
- 它就像一个装有一堆对象袋子，kset可以被kernel用来跟踪像"所有的块设备"或者"所有的PCI设备驱动"这样的东西
- 一个kset也是一个sysfs里的一个子目录，该目录中能看到这些相关的kobject，每个kset都包含一个kobject，这个kobject可以用来设置成其他kobject的parent。sysfs层次结构中顶层目录就是通过这样的方法构建的
- kset还可以支持kobject的"热插拔"，并会影响uevent事件如何报告给用户空间

以面向对象的观点来看，kset是一个顶层容器类，kset包含有他们自己的kobject，这个kobject是在kset代码管理之下的

::

    struct kset *kset_create_and_add(const char *name, struct kset_uevent_ops *u, struct kobject *parent);
    void kset_unregister(struct kset *kset);

如果一个kset希望控制那些与它相关联的kobject的uevent操作，可以使用struct kset_uevent_ops处理

::

    struct kset_uevent_ops {
        int (*filter)(struct kset *kset, struct kobject *kobj);
        const char *(*name)(struct kset *kset, struct kobject *kobj);
        int (*uevent)(struct kset *kset, struct kobject *kobj,
                        struct kobj_uevent_env *env);
                                  
    };

- filter函数允许kset阻止一个特定的kobject的uevent是否发送到用户空间，如果这个函数返回0，则uvent将不会被发出
- name函数用来重写那些将被uevent发送到用户空间的kset默认名称
- uevent函数将会向即将发送到用户空间的uevent添加更多的环境变量
