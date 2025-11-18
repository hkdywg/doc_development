Makefile规则介绍
=================

makefile定义了一些列的规则来指定，哪些文件需要先编译，哪些需要后编译，哪些需要重新编译

makefile的好处是：
- 自动化编译:一旦写好，只需要一个make命令，整个工程完全自动编译，极大的提高了软件开发的效率
- 节约编译时间(没改动的不编译)

make是一个命令工具，是一个解释makefile中指令的命令工具


Makefile规则
-------------

基本规则
^^^^^^^^^

一个简单的Makefile主要有5部分(显示规则、隐晦规则、变量定义、文件指示、注释)，其样式如下

::

    target:prerequistes
        command
        ...
        ...

这是一个文件依赖关系，也就是说target是由一个或者多个目标文件依赖于prerequistites中的文件，其生成的规则定义在command中，而且只要prerequisites中的一个以上文件比target
文件更新的话，command所定义的命令就会被执行，这是makefile的最基本规则，也是makefile中最核心的内容

其中:
- target:是目标文件，可以是object file，也可以是可执行文件，还可以是一个标签label
- prerequistes:是目标文件的依赖文件，如果依赖文件不存在，则会寻找其他规则生成依赖文件
- command：通过执行该命令由依赖问及那生成目标文件，注意每条命令前有且仅有一个tab保持缩进

1) 显示规则：说明如果生成一个或者多个目标文件(包括生成的文件，文件的依赖文件，生成的命令)

2) 隐晦规则: make的自动推导功能所执行的规则

3) 变量定义：Makefile中定义的变量

4) 文件指示：Makefile中引用其他Makefile，指定Makefile中有效部分，定义一个多行命令

5) 注释：Makeile中只有行注释# ，如果要使用或者输出#字符则需要转义 \#


GNU make的工作方式:

1. 读入主Makefile(主Makefile中可以引用其他Makefile)

2. 读入被include的其他Makefile

3. 初始化文件中的变量

4. 推导隐晦规则，并分析所有规则

5. 为所有的目标文件创建依赖关系链

6. 根据依赖关系决定哪些目标文件需要生成

7. 执行生成命令


Makefile中的注释有以下两种方式
- 单行注释： Makefile中以#字符后面的内容作为注释部分
- 多行注释：如果需要多行注释，在注释行后面加行反斜线\，则下一行也被注释

通配符
^^^^^^

- * : 表示任意一个或者多个字符
- ? : 表示任意一个字符
- [...] : 比如[abcd]表示abcd中的任意一个字符，[^abcd]表示除abcd意外的字符，[0~9]表示0~9中的任意一个数字
- ~ : 表示用户的home目录
- % : 通配符，如%.o:%.c表示所有的目标文件及其依赖文件

路径搜索
^^^^^^^^^

当一个Makefile中涉及到大量源文件时(这些源文件极有可能和Makefile不在同一个目录中)这时最好将源文件的路径明确在Makefile中，便于编译时的查找。Makefile中有个
特殊的变量VPATH就是完成这个功能的，制定了VPATH之后，如果当前目录中没有找到相应文件或依赖文件Makefile会到VPATH指定的路径中再去寻找

VPATH使用方法：
- vpath <dir>: 当前目录中找不到文件时就去dir中搜索,多个dir之间用:隔开
- vpath <pattern> <dir> : 符合<pattern>格式的文件，就从<dir>中搜索
- vpath <pattern> ：清除符合<pattern>格式的文件搜索路径
- vpath: 清除所有已经设置好的文件路径

::

    VPATH src:../parent-dir  ##当前目录找不到文件时，按顺序从src目录 ../parent-dir目录中查找文件
    VPATH %.h ./header  ##.h结尾的文件在./header目录中查找
    VPATTH %.h  ##清除上一条设置的规则
    VPATH   #清除所有VPATH的设置


makfile变量
----------------

makefile中变量的名字可以包含字符、数字、下划线(可以是数字开头)，但不应该含有 ``:`` ``#`` ``=`` 或者空字符。变量是大小写敏感的。
传统的Makefile变量名采用全大写的方式

变量的赋值有以下几种运算符
- =  基本的赋值，make会将整个makefile展开后再决定变量的值
- :=  覆盖之前的赋值，变量的值决定于它在makefile中的位置，而不是整个makefile展开后的最终值
- ?= 如果没有赋值就等于后面的值
- += 添加等号后面的值

make环境变量
^^^^^^^^^^^^^

- MAKEFILES

如果当前环境定义了一个MAKEFILES环境变量，make执行时首先将变量的值作为需要读入的makefile文件，多个文件之间使用空格分开．类似使用指示符include
包含其他makefile文件一样

- MAKEFILES_LIST

make程序在读取多个 Makefile 文件时，包括由环境变量 "MAKEFILES" 指定、命令行指定、当前工作下默认以及使用指示符"include" 指定包含的，
在对这些文件进行解析执行之前 make 读取的文件名将会被自动依次追加到变量 "MAKEFILES_LIST" 的定义域中。

这样可以通过测试此变量的最后一个字获取当前 make 程序正在处理的 Makfile 文件名。

::

    name1 := $(word $(words $(MAKEFILE_LIST)),$(MAKEFILE_LIST))
    include inc.mk
    name2 := $(word $(words $(MAKEFILE_LIST)),$(MAKEFILE_LIST))
     
    all:
        @echo name1 = $(name1)
        @echo name2 = $(name2)

输出结果为:

::

    name1 = Makefile
    name2 = inc.mk


- VPATH

GNU make 可以识别到一个特殊变量 "PATH"。通过变量 "PATH" 可以指定依赖文件的搜索路径，当规则的依赖文件在当前目录不存在时，make 会在此变量所指定的目录下去寻找这些依赖文件。
其实，"VPATH" 变量所指定的是 Makefile 中所有文件的搜索路径，包括了规则的依赖文件和目标文件。定义变量 "VPATH" 时，使用空格或者冒号（:）将多个需要搜索的目录分开。例如：

::

    VPATH = src:../headers

这样，就为所有规则的依赖指定了两个搜索目录，"src" 和 "../headers"。

- MAKELEVEL

在多级递归调用的 make 执行过程中，变量 "MAKELEVEL" 代表了调用的深度。在 make 一级级的执行过程中变量 "MAKELEVEL" 的值不断发生变化。

- MAKEFLAGS

在 make 的递归过程中，最上层make的命令行选项如 "-k"、"-s" 等会被自动的通过环境变量 "MAKEFLAGS" 传递给子 make 进程。

传递过程中变量 "MAKEFLAGS" 的值会被主控 make 自动的设置为包含执行 make 时的命令行选项的字符串。

执行多级的 make 调用时，当不希望传递 "MAKEFLAGS" 给子 make 时，需要再调用子程序 make 对这个变量进行赋空，例如： 

::

    subsystem:
        cd subdir && $(MAKE) MAKEFLAGS=


- CURDIR

在 make 递归调用中，变量 "CURDIR" 代表 make 的工作目录。当使用 "-C" 选项进入一个子目录后，此变量将被重新赋值。



shell变量
^^^^^^^^^

===============     ========================
   变量名               含义
---------------     ------------------------
   RM                rm -f
   AR                ar
   CC                cc
   CXX               g++
===============     ========================

自动变量
^^^^^^^^^

============    ===============================================
自动变量                含义
------------    -----------------------------------------------
$@              目标集合
$%              当目标是函数库文件时，表示其中的目标文件名
$<              第一个依赖目标，如果依赖是多个，则逐个表示
$?              比目标新的依赖集合
$^              所有依赖集合，去除重复的依赖
$+              所有依赖的集合，不会去除重复的依赖
============    ===============================================

其他常用功能
------------

定义命令包
^^^^^^^^^^

如果Makefile中出现一些相同命令序列，那么我们可以为这些相同的命令序列定义一个变量，定义这种命令序列的语法以 ``define`` 开始， 以 ``endef`` 结束，如

::

    define run-yacc
    yacc $(firstword $^)
    mv y.tab.c $@
    endef

    foo.c: foo.y
        $(run-yacc)     #run-yacc中$^就是foo.y $@就是foo.c

make参数
^^^^^^^^^

::

    -B,--always-make    ##认为所有的目标都需要更新
    -C <dir>, --directory=<dir>  ##指定读取makefile的目录
    -debug [=<opetarions>]   #输出make的调试信息，如果没有参数则输出最简单的调试信息，operation可以取如下值
                a: 也就是all，输出所有调试信息
                b: 也就是basic，只输出简单的调试信息，输出不需要重编译的目标
                v: 也就是verbose，在b选项的级别之上，输出信息包括哪个makefile被解析，不需要重编译的依赖文件
                i: 也就是implicit,输出所有的隐含规则
                j: 也就是jobs，输出执行规则中的详细信息，如命令的pid，返回码等
                m: 也就是makefile，输出make读取makefile，更新makefile，执行makefile的信息
    -d ##相当于-debug=a
    -e,--enviroment-overriders  #指明环境变量的值覆盖makefile中定义的变量的值
    -f=<file>  #指定需要执行的makefile
    -i,--ignore-errors  #在执行时忽略所有的错误
    -n #仅输出执行过程中的命令序列，但不执行
    -p #输出makefile中的所有数据，包含所有的规则和变量
