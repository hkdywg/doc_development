linux kernel debug tools
========================

kerel-debug之kdump
------------------

一般情况下kernel crash时系统处于死机状态，无法通过一般手段获取故障发生时的
现场信息。这种情况下kdump-kexec机制应运而生。
kexec可在一个内核运行时加载另一个内核，而且不进行硬件初始化。在跳过u-boot
而且没有硬件重启的情况下可以保留上一个内核的运行现场。
产生crash的内核称为生产内核，发生crash后运行的另外一个内核称为捕获内核。
生产内核在发生crash时通过kdump生成vmcore文件，vmcore文件包含函数调用栈信息
cpu寄存器信息等。在捕获内核中可以通过dgdb等工具查看并调试。

什么是kexec?

    kexec是实现kdump机制的关键，它包括2个组成部分：一是内核空间的系统调用
    kexec_load负责在生产内核启动时将捕获内核加载到指定地址。二是用户空间的
    kexec-tools，他将捕获内核的地址传递给生产内核，从而在系统崩溃时能找到
    捕获内核的地址并运行。

什么是kdump
    
    kdump的概念出现在2005年左右，是迄今为止最为可靠的内核转存机制。kdump是
    一种基于kexec的内核崩溃转存机制。当系统崩溃时，kdump使用kexec启动到第二
    个内核。第二个内核通常叫捕获内核，生产内核会预留一部分内存给捕获内核使用，
    由于kdump利用kexec启动捕获内核绕过了boot，没有硬件复位，使得生产内核 的内
    存得以保留。这是内核崩溃转存的本质。

kexec安装

::

    wget https://mirrors.edge.kernel.org/pub/linux/utils/kernel/kexec/kexec-tools-2.0.17.tar.gz
    tar xvzf kexec-tools-2.0.17.tar.gz
    ./configure --build=x86_64-linux --host=aarch64-unknown-linux-gnu --target=aarch64-unknown-linux-gnu
    make ARCH=arm64 clean all
    make install

注：以上操作直接在目标板系统中执行

kernel 配置

内核编译时需要打开以下选项（最好使用menuconfig的方式，手动修改.config容易漏掉依赖项配置）

::

    CONFIG_KEXEC=y
    CONFIG_SYSFS=y
    CONFIG_DEBUG_INFO=y
    CONFIG_CRASH_DUMP=y
    CONFIG_PROC_VMCORE=y


