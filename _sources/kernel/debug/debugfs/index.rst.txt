kernel-debug之debugfs
---------------------

为了用户方便调试内核，kernel提供 ``procfs`` 、 ``sysfs`` 、``debugfs`` 以及 ``relayfs`` 来与用户空间进行数据交互。
尤其是 ``debugfs`` ,这是内核开发者实现的专门用来调试的文件系统接口，其他的工具或者接口都依赖于它。

内核中有三个常用的伪文件系统: procfs, debugfs,和sysfs

- procfs 历史最早，用来获取CPU，内存，设备驱动，进程等各种信息

- sysfs 跟 ``kobject`` 框架紧密联系，而 ``kobject`` 是为驱动模型而存在的，所以sysfs是为设备驱动服务的

- debugfs 从名字来看就是为debug而生，所以更加灵活

- relayfs 是一个快速的转发(relay)数据的文件系统，它以其功能而得名，它为那些需从 内核空间转发大量用户数据到用户空间的工具和应用提供了快速有效的转发机制。

procfs 文件系统
^^^^^^^^^^^^^^^

procfs 比较老的一种用户态与内核态的数据交互方式，内核的很多数据都是通过这种方式输出给用户的。内核的很多参数也可以通过procfs去设置。
除了 ``sysctl`` 出口到 ``/proc`` 下的参数，procfs提供的大多数内核参数都是只读的，实际上很多应用严重依赖procfs，因此它几乎是必不可少的组件.

procfs提供了一下api：

::

    struct proc_dir_entry *create_proc_entry(const char *name, mode_t mode, struct proc_dir_entry *parent)
    #该函数用于创建一个正常的proc条目，name指定名称，mode指定权限，parent指定目录。
    #如果要在/proc下创建条目，parent设置为NULL

    extern void remove_proc_entry(const char *name, struct proc_dir_entry *parent)
    #用于删除上面的条目

    struct  proc_dir_entry *proc_mkdir(const char * name, struct proc_dir_entry *parent)
    extern struct proc_dir_entry *proc_mkdir_mode(const char *name, mode_t mode, struct proc_dir_entry *parent)
    #该函数 用于创建一个proc目录

    struct proc_dir_entry *proc_symlink(const char * name, struct proc_dir_entry* parent, const char *dest)
    #该函数用于创建一个符号链接，name指定创建的名称，parent指定路径，dest指定链接到的proc条目名称

    struct  proc_dir_entry *proc_net_create(const char *name, mode_t mode, get_info_t *get_info)
    struct  proc_dir_entry *proc_net_fops_create(const char *name, mode_t mode, struct file_operations *fops)
    #该函数用于在/proc/net目录下创建，name指定名称，mode指定权限，get_info(fops)则指定操作函数

用户可以通过 ``cat`` 、``echo`` 等文件操作函数来设置和查看这些proc文件。

注：对于proc中的大文件，proc有一些限制，因为它提供的缓存只有一个页。因为对于超页的部分要做特别的考虑，处理起来也比较复杂。且
容易出错，所以proc不适合大数据量的输入输出。


sysfs 文件系统
^^^^^^^^^^^^^^

内核子系统或者设备驱动可以直接编译到内核，也可以编译成模块。编译到内核时，可以使用内核启动参数来向它们传递参数。如果编译成模块，则
可以通过命令行在插入模块时传递参数，或在运行时，通过 ``sysfs`` 来设置或读取模块数据。

``sysfs`` 是一个基于内存的文件系统，实际上它基于 ``ramfs`` ,sysfs提供了一种把内核数据结构以及属性开放给用户态的方式，它与 ``kobject``
 子系统紧密的结合在一起。

 ::

    mkdir -p /sysfs
    mount -t sysfs sysfs /sysfs

注：不要把 ``sysfs`` 和 ``sysctl`` 混淆， ``sysctl`` 是内核的一些控制参数，其目的是方便用户对内核的行为进行控制，而 ``sysfs`` 仅仅
是把内核的 ``kobject`` 对象的层次关系和属性开放给用户查看。因此sysfs的绝大部分是只读的,模块作为一个 ``kobject`` 也被出口到 ``sysfs``


