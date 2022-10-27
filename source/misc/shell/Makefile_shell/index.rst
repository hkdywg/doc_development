Makefile与shell的区别
=====================

变量引用
--------

shell中所有引用要以$打头的变量其后要加{}, 而在Makefile中以$打头的后要加()如下

::

    Makefile
    PATH:=/opt/toolchain
    SUBPATH:=$(PATH)

    shell
    PATH:=/opt/toolchain
    SUBPATH:=${PATH}

Makefile中所有以$打头的单词都会被解释称Makefile中的变量
如果需要调用shell中的变量,都需要加上两个$符号($$),如下:

::

    PATH=/opt/toolchain
    all:
        echo $(PATH)      #引用的是Makefile中的变量
        echo $$PATH       #引用的是shell中的PATH环境变量


通配符区别
----------

shell中 ``*`` 表示所有字符,Makfile中 ``%`` 表示所有字符


打印输出
--------

在Makefile中只能在target中调用shell脚本，其他地方是不能输出的，比如如下代码没有任何输出

::

    var="hello"
    echo "$(var)"
    all:

代码片段
--------

Makefile中执行shell,每一行都是一个进程,不同行之间变量不能传递,所以Makefile中shell不管多长也要写在一行

::

    SUBDIR=src example
    all:
        @for subdir in $(SUBDIR);   \
        do \
            echo "building ";   \
        done

makfile中的反引号``
--------------------

反引号括起来的字符串被shell解释为命令行，执行时shell首先执行该命令行，并以它的标准输出结果取代整个反引号部分

::

    PATH=`pwd`
    TODAY=`date`
    等同于
    PATH=$(shell pwd)
    TODAY=$(shell date)


makefile中嵌入脚本
------------------

::

    env:
        sh $(SRC_PATH)/scripts/connect.sh
        find $(SRC_PATH) -name "sysinfo.cfg" | xargs rm -f



**Makefile中使用shell的source命令**

makefile中使用source,报错"source Command not found” 

解决方法：

::

    Makefile的默认shell是/bin/sh, 本身是不支持source的，可以将shell的默认执行程序修改为/bin/bash

    SHELL:=/bin/bash





