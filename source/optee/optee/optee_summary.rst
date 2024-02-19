optee概述
============


TEE如何保证数据安全
------------------------

在没有集成trustzone的环境有一个风险就是当获取root权限之后，就可以随意访问所有的数据，这样的操作十分危险．为了保障这一部分数据在root权限下不被轻松获取，
因此在硬件层引入了trustzone技术

为确保用户数据的安全，ARM公司提出了trustzone技术，ARM在AXI系统总线上添加了一根额外的安全总线，
称为 ``NS位`` ，并将cortex分为两种状态: ``安全世界状态(secure world status, SWS)`` 和 ``正常世界状态(normal world status, NWS)`` ,并添加了一种叫做monitor的模式，cortex根据NS的值来判定
当前指令操作是需要安全操作还是非安全操作，并结合自身是否属于secure world状态来判定当前执行的指令操作．而cortex的状态切换操作由monitor来完成，
在ATF(arm trusted firmware)中完成．


在整个系统的软件层面，一般的操作系统(如Linux, Android)以及应用运行在正常世界状态中，TEE运行在安全世界状态中，正常世界状态内的开发资源相对于安全世界状态
较为丰富，因此通常称运行在正常世界状态中的环境为丰富执行环境(Rich Execution Environment, REE)


在真实环境中，可以将用户的敏感数据保存到TEE中，并由可信应用(Trusted Application, TA)使用重要算法和处理逻辑来完成对数据的处理．当需要使用用户的敏感数据做身份
验证时，则通过在REE侧定义具体的请求编号(IDentity, ID),从TEE侧获取验证结果．验证的整个过程中用户的敏感数据始终处于TEE中，REE侧无法查看到任何TEE中的数据．对于
REE而言，TEE中的TA相当于一个黑盒，只会接受有限且提前定义好的合法调用(TEEC)

.. note::
    当coretex处于secure world状态时，cortex会去执行TEE(Trusted execute enviorment)OS部分的代码，当cortex处于non-secure world状态时，cortex会去执行
    linux kernel部分的代码.而linux kernel无法访问TEE所有资源，只能通过特定的TA(Trust Application)和CA(Client Application)来访问TEE部分的特定资源．


TEE是基于trustzone技术搭建的安全执行环境．当cortex处于scure world状态时，coretex执行的是TEE OS的代码，而当前没有统一的TEE OS，各家厂商和组织都有自己的
实现方式，但是所有的方案都会遵循GP(GlobalPlatform)标准．包括高通的Qsee, Trustonic的tee OS, OP-TEE等.

.. note::
    各厂商的TEE OS都属于闭源的．


TEE解决方案
----------------

TEE是一套完整的安全解决方案，主要包含:

- 正常世界状态的客户端应用(Client Application, CA)

- 安全世界状态的可信应用，可信硬件驱动(Secure Driver, SD)

- 可信内核系统(Trusted Execution Environment Operation System, TEE OS)
  
其系统配置，内部逻辑，安全设备和安全资源的划分是与CPU的IC设计紧密挂钩的，使用ARM架构设计不同的CPU，TEE的配置完全不一样．


OP-TEE运行环境搭建
---------------------

OP-TEE是开源的TEE解决方案，下面以ubuntu 20.04为例搭建其仿真运行环境

环境准备
^^^^^^^^^


- 安装环境依赖

::

    sudo apt update && apt upgrade -y
    sudo apt install -y \
    android-tools-adb \
    android-tools-fastboot \
    autoconf \
    automake \
    bc \
    bison \
    build-essential \
    ccache \
    cpio \
    cscope \
    curl \
    device-tree-compiler \
    expect \
    flex \
    ftp-upload \
    gdisk \
    git \
    iasl \
    libattr1-dev \
    libcap-ng-dev \
    libfdt-dev \
    libftdi-dev \
    libglib2.0-dev \
    libgmp3-dev \
    libhidapi-dev \
    libmpc-dev \
    libncurses5-dev \
    libpixman-1-dev \
    libslirp-dev \
    libssl-dev \
    libtool \
    make \
    mtools \
    netcat \
    ninja-build \
    python-is-python3 \
    python3-crypto \
    python3-cryptography \
    python3-pip \
    python3-pyelftools \
    python3-serial \
    rsync \
    unzip \
    uuid-dev \
    wget \
    xdg-utils \
    xterm \
    xz-utils \
    zlib1g-dev


准备和编译
^^^^^^^^^^^^^

::

    mkdir optee && cd optee
    curl https://mirrors.tuna.tsinghua.edu.cn/git/git-repo -o ~/bin/repo
    chmod a+x ~/bin/repo
    export PATH=~/bin:$PATH
    #将~/bin/repo文件中的
    #REPO_URL = "https://gerrit.googlesource.com/git-repo"
    #更换为
    #EPO_URL = "https://mirrors.tuna.tsinghua.edu.cn/git/git-repo/"
    ~/bin/repo init -u https://github.com/OP-TEE/manifest.git -m qemu_v8.xml




