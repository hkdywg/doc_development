uedev简介
==============

udev完全工作在用户空间，当一个设备被插入或者移除时，内核会通过netlink套接字发送设备详细信息到用户空间，udev获取到设备信息，根据信息内容在/dev下创建并命名设备节点。

- 冷插拔的设备怎么办

由于冷插拔的设备在开机时就已经存在，在udev启动前已经被插入，针对这种情况，sysfs的设备都存在 ``uevent`` 文件，向该文件写入 ``add`` ，内核会重新发送netlink，之后udev就可以
受到设备的详细信息了，从而创建/dev下对应的设备节点。

udev规则
----------

- 配置文件

udev的配置文件位于/etc/udev/和/lib/udev

udev的主配置文件是/etc/udev/udev.conf，它包含一套变量，允许用户修改udev默认值，可以设置的变量如下：

udev_root 设备目录，默认是/dev

udev_log  日志等级(表示严重程度)，跟syslog一致，例如err,info,debug

- 规则文件

udev的规则文件一般位于/lib/udev/rules.d/，也可以位于/etc/udev/rules.d/

规则文件是按照字母顺序处理的，对于相同名字的规则文件，/etc/udev/rules.d比/lib/udev/rules.d优先

规则文件必须以.rules作为扩展名，否则不被当作规则文件。

规则文件的每一行哦第时key=vaule的格式，key有两种类型，1) ``匹配型key`` 2) ``赋值型key``

当所有匹配型key都匹配时，该规则即被采用，赋值型key就会获得相应的值。

一条规则有多个key=value组成，以英文逗号个凯，每个key有一个操作，取决于操作符，有效的操作符如下：

1)  == 比较是否相等
2)  != 比较是否不想等
3)  = 给一个key赋值，表示一个列表的key会被重置，并且把这个唯一的值传给它
4)  += 将一个值增加到key中
5)  := 将一个值传给一个key，并且不允许再修改这个key

- 匹配型key

下面的key可以匹配设备属性，部分key也可以用于匹配sysfs中父设备属性，不仅仅是产生事件的那个设备。如果在一个规则中，有多个key
匹配了一个父设备，则这些key必须匹配同一个父设备。

+------------------+----------------------------------------------------------------------------------------+
|    key           |                              description                                               |
+==================+========================================================================================+
|    ACTION        | 匹配事件的动作名                                                                       |        
+------------------+----------------------------------------------------------------------------------------+
|    DEVPATH       | 匹配事件的设备devpath                                                                  |        
+------------------+----------------------------------------------------------------------------------------+
|    KERNEL        | 匹配事件的设备名                                                                       |        
+------------------+----------------------------------------------------------------------------------------+
|    NAME          | 匹配网络接口或者设备节点名字，NAME只有在前面的规则中赋值之后才可以使用                 |        
+------------------+----------------------------------------------------------------------------------------+
|    SYMLINK       | 匹配设备节点的符号连接名字，只有在赋值之后才可以使用                                   |        
+------------------+----------------------------------------------------------------------------------------+
|    SUBSYSTEM     | 匹配设备子系统                                                                         |        
+------------------+----------------------------------------------------------------------------------------+
|    DRIVER        | 匹配设备的驱动名，只对绑定到一个驱动的设备有用                                         |        
+------------------+----------------------------------------------------------------------------------------+
| ATTR{filename}   | 匹配事件设备的sysfs属性                                                                |        
+------------------+----------------------------------------------------------------------------------------+
|    KERNELS       | 向上搜索devpath，知道找到一个匹配的设备名                                              |        
+------------------+----------------------------------------------------------------------------------------+
|    SUBSYSTEMS    | ...                                                                                    |        
+------------------+----------------------------------------------------------------------------------------+
|    DRIVERS       | ...                                                                                    |        
+------------------+----------------------------------------------------------------------------------------+
| ATTRS{filename}  | ...                                                                                    |        
+------------------+----------------------------------------------------------------------------------------+
|    ENV{key}      | 环境变量取值                                                                           |        
+------------------+----------------------------------------------------------------------------------------+
|    TAG           | 设备的TAG                                                                              |        
+------------------+----------------------------------------------------------------------------------------+
|    TEST{ }       | 测试一个文件是否存在                                                                   |        
+------------------+----------------------------------------------------------------------------------------+
|    PROGRAM       | 执行一个程序，如果程序成功返回，key为true，可以从RESULT把这个key读取                   |        
+------------------+----------------------------------------------------------------------------------------+
|    RESULT        | 匹配最近一次PROGRAM调用的返回字符串，应该在PROGRAM之后使用                             |        
+------------------+----------------------------------------------------------------------------------------+

支持一些shell的通配符

1)  * 代表0到无穷多个任意字符
2)  ? 代表【一定有一个】任意字符
3)  [] 代表一定有一个在括号内的字符

- 赋值型KEY

+------------------+----------------------------------------------------------------------------------------+
|    key           |                              description                                               |
+==================+========================================================================================+
|    NAME          |  根据这个规则创建的设备文件的文件名                                                    |        
+------------------+----------------------------------------------------------------------------------------+
|    SYMLINK       |                                                                                        |        
+------------------+----------------------------------------------------------------------------------------+
|    OWNER         |  设备文件的属组                                                                        |        
+------------------+----------------------------------------------------------------------------------------+
|    GROUP         |  设备文件所在的组                                                                      |        
+------------------+----------------------------------------------------------------------------------------+
|    MODE          |  设备文件的权限，采用8进制                                                             |        
+------------------+----------------------------------------------------------------------------------------+
|    ATTR{key}     |                                                                                        |        
+------------------+----------------------------------------------------------------------------------------+
|    TAG           |                                                                                        |        
+------------------+----------------------------------------------------------------------------------------+
|    RUN           | 为设备而执行的程序列表                                                                 |        
+------------------+----------------------------------------------------------------------------------------+
|    LABEL         | GOTO 可以跳到的地方                                                                    |        
+------------------+----------------------------------------------------------------------------------------+
|    GOTO          | 跳到下一个带有匹配名字的LABEL处                                                        |        
+------------------+----------------------------------------------------------------------------------------+
|    IMPORT        | 导入一个文件或者一个程序执行后而生成的规则集到当前文件                                 |        
+------------------+----------------------------------------------------------------------------------------+
|    WAIT_FOR      | 等待一个特定的设备文件的创建，主要是用作时序和依赖问题                                 |        
+------------------+----------------------------------------------------------------------------------------+
|    OPTIONS       | 特定选项：last_rule对这类设备终端规则执行。ignore_divice忽略当前规则                   |        
+------------------+----------------------------------------------------------------------------------------+

NAME、SYMLINK、PROGRAM、OWNER、GROUP、MODE、RUN这些filed支持一个简单的，类似于printf函数的格式字符串替换，可以的字符串替换如下；

1)  $kernel,%k  :该设备在内核中的名字(%k替换$kernel)
2)  $number,%n  :该设备的内核号码，例如sda1的内核号码是1
3)  $devpath,%p :该设备的devpath
4)  $id,%b      :向上搜索devpath，寻找SUBSYSTEMS，KERNELS，DRIVERS和ATTRS时，被匹配的设备名字
5)  $driver     :...被匹配的驱动名字
6)  $attr{file}, %s{file}   :一个被发现的设备的sysfs属性的值，如果该设备没有该属性，且前面的KERNELS ，SUBSYSTEMS，DRIVERS或ATTRS测试选择的是一个父设备，那么就用父设备的属性，如果属性是一个符号链，符号链的最后一个元素作为返回值。
7)  $env{key},%E{key}   :一个设备的属性值
8)  $major,%M   :主设备号
9)  $minor,%m   :次设备号
10) $result,%c  :由PROGRAM调用的外部程序返回的字符串，如果这个字符串包含空格，可以用%c{N}选中第N个字段。如果这个数字N后面有一个+字符，则表示选中这个字段开始的后面所有字符
11) $parent,%p  :父设备的节点名字
12) $name       :设备节点的名字，用一个空格作为分割符，该值只有在前面的规则赋值之后才存在
13) $links      :当前符号链的列表，用空格隔开
14) $root,%r    :udev_root的值
15) $sys,%S     :sysfs挂载点
16) $tempmpde,%N    :在真正的设备节点创建之前，创建的一个临时设备节点的名字，这个临时节点供外部程序使用。

- 查询设备信息

例如：设备sda的SYSFS{size}可以通过cat /sys/block/sda/size得到。SYSFS{model}信息可以通过cat /sys/block/sda/device/model得到

或者可以通过udevadm命令获取设备信息

::
    
    root@ArkV3:/dev# udevadm info --query=all --name=/dev/mmcblk0
    P: /devices/platform/interconnect@100000/4f80000.sdhci/mmc_host/mmc0/mmc0:0001/block/mmcblk0
    N: mmcblk0
    S: disk/by-id/mmc-S0J57X_0x11bc20a7
    S: disk/by-path/platform-4f80000.sdhci
    E: DEVLINKS=/dev/disk/by-id/mmc-S0J57X_0x11bc20a7 /dev/disk/by-path/platform-4f80000.sdhci
    E: DEVNAME=/dev/mmcblk0
    E: DEVPATH=/devices/platform/interconnect@100000/4f80000.sdhci/mmc_host/mmc0/mmc0:0001/block/mmcblk0
    E: DEVTYPE=disk
    E: ID_NAME=S0J57X
    E: ID_PART_TABLE_TYPE=dos
    E: ID_PART_TABLE_UUID=19c5099c
    E: ID_PATH=platform-4f80000.sdhci
    E: ID_PATH_TAG=platform-4f80000_sdhci
    E: ID_SERIAL=0x11bc20a7
    E: MAJOR=179
    E: MINOR=0
    E: SUBSYSTEM=block
    E: TAGS=:systemd:
    E: USEC_INITIALIZED=2619079

- 调试

以下内容为通过udevadm monitor监测SD卡的拔出以及插入事件

::

    root@ArkV3:~# udevadm monitor
    monitor will print the received events for:
    UDEV - the event which udev sends out after rule processing
    KERNEL - the kernel uevent

    KERNEL[95305.858326] remove   /devices/platform/interconnect@100000/4fb0000.sdhci/mmc_host/mmc1/mmc1:aaaa/block/mmcblk1/mmcblk1p2 (block)
    KERNEL[95305.863476] remove   /devices/platform/interconnect@100000/4fb0000.sdhci/mmc_host/mmc1/mmc1:aaaa/block/mmcblk1/mmcblk1p1 (block)
    UDEV  [95305.863909] remove   /devices/platform/interconnect@100000/4fb0000.sdhci/mmc_host/mmc1/mmc1:aaaa/block/mmcblk1/mmcblk1p2 (block)
    KERNEL[95305.865764] remove   /devices/virtual/bdi/179:96 (bdi)
    KERNEL[95305.865813] remove   /devices/platform/interconnect@100000/4fb0000.sdhci/mmc_host/mmc1/mmc1:aaaa/block/mmcblk1 (block)
    UDEV  [95305.866439] remove   /devices/virtual/bdi/179:96 (bdi)
    UDEV  [95305.869234] remove   /devices/platform/interconnect@100000/4fb0000.sdhci/mmc_host/mmc1/mmc1:aaaa/block/mmcblk1/mmcblk1p1 (block)
    UDEV  [95305.869314] remove   /devices/platform/interconnect@100000/4fb0000.sdhci/mmc_host/mmc1/mmc1:aaaa/block/mmcblk1 (block)
    KERNEL[95305.884325] unbind   /devices/platform/interconnect@100000/4fb0000.sdhci/mmc_host/mmc1/mmc1:aaaa (mmc)
    KERNEL[95305.884538] remove   /devices/platform/interconnect@100000/4fb0000.sdhci/mmc_host/mmc1/mmc1:aaaa (mmc)
    UDEV  [95305.887321] unbind   /devices/platform/interconnect@100000/4fb0000.sdhci/mmc_host/mmc1/mmc1:aaaa (mmc)
    UDEV  [95305.887671] remove   /devices/platform/interconnect@100000/4fb0000.sdhci/mmc_host/mmc1/mmc1:aaaa (mmc)

    KERNEL[95312.630739] add      /devices/platform/interconnect@100000/4fb0000.sdhci/mmc_host/mmc1/mmc1:aaaa (mmc)
    UDEV  [95312.634149] add      /devices/platform/interconnect@100000/4fb0000.sdhci/mmc_host/mmc1/mmc1:aaaa (mmc)
    KERNEL[95312.644368] add      /devices/virtual/bdi/179:96 (bdi)
    UDEV  [95312.646727] add      /devices/virtual/bdi/179:96 (bdi)
    KERNEL[95312.652352] add      /devices/platform/interconnect@100000/4fb0000.sdhci/mmc_host/mmc1/mmc1:aaaa/block/mmcblk1 (block)
    KERNEL[95312.652402] add      /devices/platform/interconnect@100000/4fb0000.sdhci/mmc_host/mmc1/mmc1:aaaa/block/mmcblk1/mmcblk1p1 (block)
    KERNEL[95312.652431] add      /devices/platform/interconnect@100000/4fb0000.sdhci/mmc_host/mmc1/mmc1:aaaa/block/mmcblk1/mmcblk1p2 (block)
    KERNEL[95312.652881] bind     /devices/platform/interconnect@100000/4fb0000.sdhci/mmc_host/mmc1/mmc1:aaaa (mmc)
    UDEV  [95312.713507] add      /devices/platform/interconnect@100000/4fb0000.sdhci/mmc_host/mmc1/mmc1:aaaa/block/mmcblk1 (block)
    UDEV  [95312.827378] add      /devices/platform/interconnect@100000/4fb0000.sdhci/mmc_host/mmc1/mmc1:aaaa/block/mmcblk1/mmcblk1p1 (block)
    UDEV  [95312.827647] add      /devices/platform/interconnect@100000/4fb0000.sdhci/mmc_host/mmc1/mmc1:aaaa/block/mmcblk1/mmcblk1p2 (block)
    UDEV  [95312.830561] bind     /devices/platform/interconnect@100000/4fb0000.sdhci/mmc_host/mmc1/mmc1:aaaa (mmc)
