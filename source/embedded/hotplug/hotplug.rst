linux 热插拔之udev和mdev
==========================

热插拔是内核用户空间之间,通过调用用户空间程序(如hotplug udev mdev)的交互, 当需要通知用户内核发生了某种热插拔事件时,
内核才调用这个用户空间程序.linux的热插拔是一个连接底层硬件,内核空间和用户空间程序的机制.

udev
-----

udev工作原理
^^^^^^^^^^^^^

当内核发现系统中添加或者删除了某个新的设备时,会产生一个hotplug event并查找/proc/sys/kernel/hotplug找出管理设备连接的用户空间程序.
若udev已经启动,内核会通知udev去检测sysfs中关于这个新设备的信息并创建设备节点.udev会执行udevd程序读取sys文件系统,以便读取该设备的硬件
信息(如/dev/vcs, 在/sys/class/tty/vcs/dev存放的是"7:0",即/dev/vcs的主次设备号),同时会在/etc/udev/rules.d/下检查规则文件对该设备的使用权限

当设备插入或移除时,hotplug机制会让内核通过netlink socket向内核传递一个事件的发生,udevd通过标准的socket机制,创建socket连接来获取内核广播的
uevent事件,并解析这些uevent事件.

- netlink socket: 内核调用kobject_uevent函数发送 message给用户空间,该功能由内核的统一设备模型里的子系统这一层实现

可以通过以下命令模拟uevent事件

::

    echo "add" > /sys/block/mtdblock2/uevent
















mdev
--------
