yocto源目录结构
=================

顶层核心组件
-------------

bitbake
^^^^^^^^^

bitbake是一个元数据解释器，它读取yocto项目元数据并运行该数据定义的任务。

当运行bitbake命令，bitbake/bin/目录中对应的可执行文件将会启动。

build
^^^^^^

此目录包含用户配置文件和构建过程中的输出文件。

documentation
^^^^^^^^^^^^^^

该目录包含 Yocto 项目文档的源代码以及允许您生成 PDF 和 HTML 版本手册的模板和工具。

meta
^^^^^

此目录包含最小的底层openembedded-core元数据。

meta-poky
^^^^^^^^^^

在meta内容之上，这个目录添加了足够的元数据来定义poky参考

meta-yocto-bsp
^^^^^^^^^^^^^^^

此目录包含yocto项目参考硬件板卡支持包

meta-selftest
^^^^^^^^^^^^^^

此目录添加了openembedded自测试使用的recipe和附加文件，以验证构建系统的行为.

meta-skeleton
^^^^^^^^^^^^^^

该目录包含用于BSP和内核开发的模板recipe

scripts
^^^^^^^^^

该目录包含在yocto项目环境中实现额外功能的各种集成脚本(例如qemu脚本)


构建目录
----------

当运行环境设置脚本oe-init-build-env时，默认会创建build目录，在后续的解析和处理中可以通过TOPDIR回去build目录的名称

- build/conf/local.conf

此配置文件包含所有本地用户配置，通常会修改此文件来修改MACHINE    PACKAGE_CLASSES     DL_DIR

- build/conf/bblayers.conf

此配置文件定了layer，他们是目录树，由bitbake遍历。

-  build/cache/sanity_info

此文件指示健全性检查的状态并在构建期间创建。

- build/downloads/

此目录包含下载文件tarball，可以通过DL_DIR变量来控制此目录的位置

- build/sstate-cache/

此目录包含共享状态缓存,可以通过SSTATE_DIR变量来控制此目录的位置

- build/tmp

bitbake构建过程中的输出都在此目录，TMPDIR指向该目录

- build/tmp/buildstats

此目录存储构建统计信息

- build/tmp/cache

当bitbake解析元数据时，它会缓存结果到build/tmp/cache以加快构建

- build/tmp/deploy

此目录包含bitbake构建过程的任何"最终结果"输出，DEPLOY_DIR指向该目录

- build/tmp/deploy/deb

此目录包含.deb构建产生的包

- build/tmp/deploy/images

此目录包含基本输出对象，包括bootloader，内核，以及根文件系统等内容

如果不小心删除了此处的文件，可以通过以下命令重新创建

::

    bitbake virtual/kernel  #重新创建
    bitbake -c clean virtual/kernel   #删除

- build/tmp/deploy/sdk

此目录会保存工具链安装程序脚本,这些脚本执行时会安装与目标硬件匹配的sysroot

- build/tmp/sstate-control

此目录用于存储共享状态清单文件，共享状态代码使用这些文件来记录每个sstate任务安装的文件

- build/tmp/log

此目录包含log文件

- build/tmp/work

此目录为bitbake的工作目录

元数据
-------

- meta/calsses

此目录包含*.bbclass文件，class文件用于抽象公共代码，以便它可以被多个包重用,每个包都继承base.bbclass文件

- meta/conf

该目录包含核心配置文件集bitbake.con，所有其他配置文件都从这些配置文件开始

- meta/conf/machine

该目录包含所有机器配置文件

- meta/recipes-bsp

该目录包含任何连接到特定硬件或硬件配置信息的内容,如"uboot"和"grub"

- meta/recipes-devtools

此目录包含工具集，可以应用到目标


