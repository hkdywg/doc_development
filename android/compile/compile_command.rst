android编译命令
===================

android系统源码编译

::

    #!/bin/bash

    CPU_NUM=`cat /proc/cpuinfo | grep processor | wc -l`

    sudo apt-get install -y uuid uuid-dev
                            zlib1g-dev liblz-dev liblzo2-2 liblzo2-dev lzop git-core curl
                            u-boot-tools mtd-utils android-tools-fsutils
    sudo apt install bc bison ccache build-essential curl flex g++-multilib gcc-multilib git gnupg gperf libxml2 lib32z1-dev liblz4-tool libncurses5-dev libsdl1.2-dev libwxgtk3.0-gtk3-dev imagemagick git lunzip lzop schedtool squashfs-tools xsltproc zip zlib1g-dev openjdk-8-jdk python2 perl  xmlstarlet virtualenv xz-utils rr jq libncurses5 pngcrush lib32ncurses-dev git-lfs libxml2 openjdk-11-jdk-headless


    ##更换为国内源
    export REPO_URL='https://mirrors.tuna.tsinghua.edu.cn/git/git-repo/'
    curl https://storage.googleapis.com/git-repo-downloads/repo > ./repo
    chmod a+x ./repo
    #./repo init -u https://android.googlesource.com/platform/manifest -b android-11.0.0_r22
    ./repo init -u https://aosp.tuna.tsinghua.edu.cn/platform/manifest -b android-11.0.0_r22
    ./repo sync -c j${CPU_NUM}
    source build/setenv.sh
    lunch aosp_car_arm64-userdebug
    make -j8


编译命令
-------------

代码编译
^^^^^^^^^^^^

::

    #初始化编译环境，包括后面的lunch及make指令
    source build/setenv.sh
    #指定此次编译的目标设备及编译类型
    lunch aosp_car_arm64-userdebug
    make -j8

所有的编译命令都可以在 ``setenv.sh`` 中找到对应的function，如lunch, make命令


======================= ====================================================
    编译指令　                  解释
----------------------- ----------------------------------------------------
 m                          在源码树的根目录执行编译
 mm                         编译当前路径下所有模块，但不包含依赖
 mmm [module_path]          编译指定路径下的所有模块，但不包含依赖
 mma                        编译当前路径下的所有模块，且包含依赖
 mmma [module_path]         编译指定路径下的所有模块，且包含依赖
 make [module_path]         无参数，则表示编译整个android源码
======================= ====================================================

**编译指令使用实例**


======================  =========================== ===================================================================
 模块　                     make 命令　                     mmm命令
----------------------  --------------------------- -------------------------------------------------------------------
 init                       make init                   mmm system/core/init
 zygote                     make app_process            mmm frameworks/base/cmds/app_process
 system_server              make services               mmm frameworks/base/services
 java framework             make framework              mmm frameworks/base
 framework资源              make framework-res          mmm frameworks/base/core/res
 jni framework            make libandroid_runtime       mmm frameworks/base/core/jni
 binder                     make libbinder              mmm frameworks/native/libs/binder
======================  =========================== ===================================================================

.. note::
    编译系统采用增量编译，只会编译发生变化的目标文件，当需要重新编译所有的相关模块，则需要编译命令后增加参数-B

代码搜索
^^^^^^^^^^

================================    ====================================================================
    搜索指令　                                  解释
--------------------------------    --------------------------------------------------------------------
 cgrep                               所有的C/C++文件执行搜索操作
 jgrep                               所有的java文件执行搜索操作
 ggrep                               所有的Gradle文件执行搜索操作
 mangrep [keyword]                   所有AndroidMainfest.xml文件进行搜索操作
 mgrep [keyword]                     所有Android.mk文件执行搜索操作
 sepgrep [keyword]                   所有sepolicy文件执行搜索操作
 resgrep [keyword]                   所有本地res/\*.xml文件执行搜索操作
 sgrep [keyword]                     所有资源文件执行搜索操作
================================    ====================================================================

以上所有指令用法的最终实现都是基于grep命令


导航指令
^^^^^^^^^^^^^

=================== =================================================
    导航指令　          解释
------------------- -------------------------------------------------
    croot               切换到Android根目录
    cproj               切换到工程的根目录
 godir [filename]       跳转到包含某个文件的目录
=================== =================================================

信号查询
^^^^^^^^^^^

======================  =================================================
 查询指令                   解释
----------------------  -------------------------------------------------
 hmm                        查询所有指令的help信息
 findmakefile               查询当前目录所在工程的Android.mk文件路径
 print_lunch_menu           查询lunch可选的product
 printconfig                查询各项编译变量值
 gettop                     查询Android源码的根目录
 gettargetarch              获取TARGET_ARCH值
======================  =================================================


编译系统
------------

**Makefile分类**

Android编译系统是Android源码的一部分，用于编译Android系统，Android SDK及相关文档．该编译系统由Make文件，
shell以及Python脚本共同组成

整个Build系统的Make文件分为三大类

- 系统核心的Make文件: 定义了Build系统的架构，文件全部位于路径build/core，其他Make文件都是基于该框架编写的

- 针对产品的Make文件: 定义了具体某个手机的Make文件，文件路径位于device

- 针对模块的Make文件: 整个系统分为各个独立的模块，每个模块都有一个专门的Make文件，名称统一为"Android.mk"，该文件定义了当前模块的编译方式


**编译产物**

经过make编译后的产物，都位于out目录，主要关注以下几个目录

- out/host: Android开发工具的产物，包含SDK各种工具，比如adb, dex2oat, aapt等

- out/target/common: 通用的一些编译产物，包含java应用代码和JAVA库

- out/targer/product/[product_name]: 针对特定设备的编译产物以及平台相关C/C++代码和二进制文件

.. note::
    - system.img: 挂载为根分区，主要包含Android OS的系统文件
    - ramdisk.img: 主要包含init.rc文件和配置文件
    - userdata.img: 被挂载在/data,主要包含用户及应用程序相关的数据

**Android.mk解析**

在源码树中每一个模块的所有文件通常都相应有一个自己的文件夹，在该模块的目录下有一个名称为 ``Android.mk`` 的文件．编译系统正是以模块为单位进行编译，
每个模块都有唯一的模块名，一个模块可以有依赖多个其他模块，模块间的依赖关系就是通过模块名来引用的．也就是说当模块需要依赖一个jar包或者apk时，必须
先将jar包或apk定义为一个模块，然后再依赖相应的模块

对于Android.mk文件，通常包含下面两行

::

    LOCAL_PATH := $(call my-dir)    #设置编译路径为当前文件夹所在路径
    include $(CLEAR_VARS)           #清空编译环境的变量

为了方便编译模块，编译系统设置了很多的编译环境变量

- LOCAL_SRC_FILES: 当前模块包含的所有源码文件

- LOCAL_MODULE: 当前模块的名称(具有唯一性)

- LOCAL_PACKAGE_NAME: 当前APK应用的名称(具有唯一性)

- LOCAL_C_INCLUDES: C/C++所需的头文件路径

- LOCAL_STATIC_LIBRARIES: 当前模块在静态连接时需要的库名

- LOCAL_SHARED_LIBRARIES: 当前模块在运行时依赖的动态库名

- LOCAL_STATIC_JAVA_LIBRARIES: 当前模块依赖的java静态库

- LOCAL_CERTIFICATE: 签署当前应用的证书名号层，比如platform

- LOCAL_MODULE_TAGS: 当前模块所包含的标签，可以包含多标签，可能值为eng,user,development;w

编译系统还定义了一些便捷函数

- $(call my-dir): 获取当前文件夹路径

- $(call all-java-files-under,): 获取指定目录下的所有java文件

- $(call all-c-files-under,): 获取指定目录下的所有C文件

- $(call all-laidl-files-under,): 获取指定目录下的所有AIDL文件

- $(call all-makefiles-under,): 获取指定目录下的所有Make文件


示例

::

    LOCAL_PATH := $(call my-dir)
    include $(CLEAR_VARS)

    #获取所有子目录中的java文件
    LOCAL_SRC_FILES := $(call all-subdir-java-files)

    # 当前模块依赖的动态java库名称
    LOCAL_JAVA_LIBRARIES := com.gityuan.lib

    # 当前模块的名称
    LOCAL_MODULE := demo

    # 将当前模块编译成一个静态的Java库
    include $(BUILD_STATIC_JAVA_LIBRARY)













