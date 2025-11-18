GNU链接脚本
=============

链接脚本原理
-------------

每一个链接过程都由链接脚本(linker script,一般以lds作为文件的后缀名)控制。链接脚本主要用于规定如何把输入文件内的section放入到输出文件中，
并控制输出文件内内容各部分在程序地址空间内的布局。链接器有个默认的内置链接脚本，可以使用ld -verbose查看，ld -T选项可以指定的链接脚本，它
将代替默认的链接脚本

基本概念
^^^^^^^^

链接器把一个或多个输入文件合并成一个输出文件

- 输入文件指的是目标文件或链接脚本文件
- 输出文件值得是目标文件或可执行文件

目标文件(包括可执行文件)具有固定的格式，在gnu/linux平台下，一般为ELF格式。目标文件中的每个section至少包括两个信息：名字和大小，大部分section还包含
于它相关联的一块数据，称为section contents。一个section可被标记为loadable或allocatable

loadable section: 输出文件运行时，相应的section内容将被加载到进程的虚拟地址空间

allocatable section: 内容为空的section可标记为"可分配的"，在输出文件运行时，在进程虚拟地址空间中腾出大小同section指定大小的部分，某些情况下这块内从必须清零

这两个section中通常包含两个地址，VMA(virtual memory address 虚拟内存地址或程序地址空间地址), LMA(load memory address 加载内存地址或进程地址空间地址)

loadable section: 输出文件运行时，相应的section内容将被加载到进程的虚拟地址空间

allocatable section: 内容为空的section可标记为"可分配的"，在输出文件运行时，在进程虚拟地址空间中腾出大小同section指定大小的部分，某些情况下这块内从必须清零

这两个section中通常包含两个地址，VMA(virtual memory address 虚拟内存地址或程序地址空间地址), LMA(load memory address 加载内存地址或进程地址空间地址)。VMA是执行
输出文件时section所在的地址，而LMA是加载输出文件时section所在的地址，通常VMA或LMA是相同的，但在嵌入式系统中，经常存在加载地址和执行地址不同的情况，比如将输出文件
加载到开发板的flash中(由LMA指定)，而运行时将位于flash中的输出文件复制到SDRAM中(由VMA指定)

- 符号(Symbol) : 每个目标文件都有符号表(SYSBOL TABLE),包含已定义的符号(对应全局变量和static变量和定义的函数名字)和未定义符号(未定义的函数的名字和引用)信息
- 符号值 ：每个符号对应一个地址. 即符号值，可以使用nm命令查看

- 脚本格式

链接脚本由一系列的命令组成，每个命令由一个关键字(一般在其后紧跟相关参数)或一条对符号的赋值语句组成，命令由分号";"隔开。文件名或格式名内如果包含分号";"或其他分隔符
，则要用引号""将名字全称引用起来。

链接脚本赋值语句
^^^^^^^^^^^^^^^^^^^

表达式语法和C语言的表达式语法一样，表达式的值都是整形，如果ld的运行主机和生成文件的目标机都是32位，则表达式是32位数据否则是64位数据，表达式的格式如下：

::

    SYMBOL = EXPRESSION
    SYMOBL += EXPRESSION
    SYMBOL -= EXPRESSION
    SYMBOL *= EXPRESSION
    SYMBOL /= EXPRESSION
    SYMBOL <<= EXPRESSION
    SYMBOL >>= EXPRESSION
    SYMBOL &= EXPRESSION
    SYMBOL |= EXPRESSION

除第一类表达式外，使用其他表达式需要SYMBOL被定义

``.`` 是一个特殊符号，它是一个定位器，一个位置指针，指向程序地址空间某位置(或某section内的偏移，如果它在SECTIONS命令内的某section描述内)，该符号只能在SECTIONS命令内使用

注意：赋值语句包含4个语法元素：符号名，操作符，表达式，分号，缺一不可。赋值语句可以出现在链接脚本的三个地方

1. SECTIONS 命令内
2. SECTIONS 命令内的section描述内
3. 全局位置

一个简单例子：

::

    floating_point = 0; /*全局位置*/
    SECTIONS
    {
        DemoText :
        {
            *(.text)
            _etext = .; /*section描述内*/
        }

        _bdata = (. + 3) & ~4;  /*SECTIONS命令内*/

        .data : { *(.data) }
    }

- 操作符优先级

::

    1.  left ! - ~ (1)
    2.  left * / %
    3.  left + -
    4.  left >> <<
    5.  left == != > < <= >=
    6.  left &
    7.  left |
    8.  left &&
    9.  left ||
    10. right ?:
    11. right &= += -= *= /= (2)

.. note::
    (1) 表示前缀符 (2) 表示后缀符

链接器延迟计算大部分表示计算，但是对待与链接过程紧密相关的表达式，链接器会立即计算表达式，如果不能计算则报错

- 相对值和绝对值

在输出section描述符内的表达式，链接器取其相对值，相对于该section的开始位置的偏移。在SECTIONS命令内且非输入section描述内的表达式，链接器去其绝对值，通过
ABSOLUTE关键字转换成绝对值，即在原来值得基础上加上表达式所处得section得VMA值

- 链接脚本相关得内建函数

::

    1.  ABSOLUTE(EXP)   转换成绝对值
    2.  ADDR(SECTION)   返回某section得VMA值
    3.  ALIGN(EXP)      返回定位符.得修调值，对齐后的值(. + EXP -1) & ~ (EXP - 1)
    4.  DEFINED(SYMBOL) 如果符号SYMBOL在全局符号表内，且被定义了，那么返回1，否则返回0
    5.  LOADADDR(SECTION) 返回某SECTION的LMA
    6.  MAX(EXP1,EXP2)  返回大者
    7.  MIN(EXP1,EXP2)  返回小者
    8.  SIZEOF(SECTION) 返回SECTION的大小，当SECTION没有被分配时，链接器会报错
    9.  SIZEOF_HEADERS  返回输出文件的文件头大小，用以确定第一个section的开始地址
    10. NEXT(EXP) 返回下一个能被使用的地址，该地址时EXP的倍数，类似于ALIGN(EXP).除非使用MEMORY命令定义了一些非连续的内存块，否则NEXT(EXP)与ALIGN一定相同


链接脚本语法
-------------

脚本命令
^^^^^^^^

- ENTRY(SYMBOL): 将符号SYMBOL的值设置成入口地址

入口地址(entry point):进程执行的第一条用户空间的指令在进程地址空间的地址。

ld有多种方法设置进程入口地址，按以下顺序执行(编号越前，优先级越高)

1. ld命令行的-e选项
2. 链接脚本的ENTRY(SYMBOL)命令
3. 如果定义了start符号，使用start符号值
4. 如果存在.text section，则使用.text section的第一个字节的位置值
5. 使用值0

- INCLUDE filename:包含其他名为filename的链接脚本

相当于c程序中的#include指令，用以包含另一个链接脚本。脚本搜索路径由-L选项指定，INCLUDE指令可以嵌套使用最大深度为10

- INPUT(files): 将括号内的文件作为链接过程的输入文件

ld首先在当前目录下寻找该文件，如果没有找到则由-L指定的搜索路径下搜索，file可以为-lfile形式，就像命令行的-l选项一样，如果该命令出现在暗含的脚本内，
则该命令内的file在连接过程中的顺序由该暗含的脚本在命令行内的顺序决定

- GROUP(files): 指定需要重复搜索符号定义的多个输入文件

files必须是库文件，且file文件作为一组被ld重复扫描，直到不再有新的未定义的引用出现

- OUTPUT(filename): 定义输出文件的名字

同ld的-o选项，不过ld的-o选项优先级更高，所以它可以用来定义默认的输出文件名

- SEARCH_DIR(path): 定义搜索路径

同ld的-L选项，不过ld的-L指定的路径要比它定义的优先级高

- STARTUP(filename): 指定filename为第一个输入文件

在链接过程中，每个输入文件是有顺序的，此命令设置文件filename为第一个输入文件

- OUTPUT_FORMAT(BFDNAME): 设置输出文件使用的BFD格式

同ld选项-o format BFDNAME，不过ld选项优先级更高

- OUTPUT_FORMAT(DEFAULT,BIG,LITTLE):定义三种输出文件的格式(大小端)


SECTIONS命令
^^^^^^^^^^^^^

SECTIONS命令告诉ld如何把输入文件的sections映射到输出文件的各个section:如何将输入section合并为输出section，如何把输出section放入到程序地址空间(VMA)和进程地址空间(LMA),
该命令格式如下

::

    SECTIONS
    {
        SECTIONS-COMMAND
        SECTIONS-COMMAND
        ...
    }


SECTION-COMMAND有四种

1. ENTRY命令
2. 符号赋值语句
3. 一个输出section的描述(output section description)
4. 一个section叠加描述(overlay description)

如果整个链接脚本内没有SECTIONS命令，那么ld将所有同名输入section合并为一个输出section内，各输入section的顺序为他们被链接器发现的顺序。如果某输入section没有在SECTIONS命令内
提到，那么该section将被直接拷贝成输出section

- 输出section描述

::

    SECTION [ADDRESS] [(TYPE)] : [AT(LMA)]
    {
        OUTPUT-SECTION-COMMAND
        OUTPUT-SECTION-COMMAND
        ...
    } [>REGION] [AT>LMA_REGION] [:PHDR HDR ...] [=FILEEXP]

    
[]内的内容为可选项，一般不需要

SECTION: section名字

SECTION左右的空白、圆括号、冒号是必须的，换行符和其他空格是可选的

每个OUTPUT-SECTION-COMMAND为以下四种之一：

1) 符号赋值语句
2) 一个输入section描述
3) 直接包含的数据值
4) 一个特殊的输出section关键字


输出section名字(SECTION):必须符合输出文件格式要求比如：a.out格式的文件只允许存在.text、.data、和.bss section名。而有的格式只允许存在数字名字，那么此时应该用引号将所有名字内
的数字组合在一起，另外，还有一些格式允许任何序列的字符存在于section名字内，此时如果名字内包含特殊字符(比如空格逗号等)，那么需要用引号将其组合在一起

输出section地址(ADDRESS)：ADDRESS是一个表达式，它的值用于设置VMA。如果没有该选项且有REGION选项，那么链接器将根据REGION设置VMA，如果也没有REGION选项，那么链接器将根据定位符号
的值设置该section的VMA，将定位符号的值调整到满足输出section对齐要求后的值，输出section的对齐要求为：该输出section描述内用到的所有输入section的对齐要求中最严格的


- 输入section描述 

最常见的输出section描述命令是输入section描述,输入section描述是最基本的链接脚本描述

::

    FILENAME(EXCLUDE_FILE (FILENAME1 FILENAME2 ...) SECTION1 SECTION2 ...)

FILENAME:   文件名，可以是一个特定的文件的名字，也可以是一个字符串模式

SECTION: 名字，可以是一个特定的section名字，也可以是一个字符串模式

例：

::

    *(.text) //表示所有输入文件的.text section
    (*(EXCLUDE_FILE (*crtend.o *otherfile.o) .ctors))  //表示除crtend.o otherfile.o文件外的所有输入文件的.ctors section
    data.o(.data)   //表示data.o文件中的.data section
    data.o   //表示data.o文件的所有section
    *(.text .data)  //表示所有文件的.text section和.data section，顺序是第一个文件的.text section 第一个文件的.data section，第二个文件的.text section 第二个文件的.data section
    *(.text) *(.data)  //表示所有文件的.text section和.data section，顺序是所有文件的.text section，所有文件的.data section

    
**链接器是如何找到对应文件的**

当FILENAME是一个特定的文件名时，链接器会查看它是否在链接命令行内出现或在INPUT命令行中出现

当FILENAME是一个字符串模式时，链接器仅仅只查看它是否在链接命令行命令中出现

字符串模式内可存在以下通配符：

\*:  表示任意多个字符

?: 表示任意一个字符

[CHARS]: 表示任意一个CHARS内的字符，可用 ``-`` 号表示范围，如：a-z

:  表示引用下一个紧跟的字符

在文件名内，通配符不匹配文件夹分隔符/，但当字符串模式仅包含通配符*时除外。任何一个文件的任意section只能在SECTIONS命令内出现一次

通用符号(common symbol)的输入section,在许多目标文件格式中，通用符号并没有占用一个section，链接器认为：输入文件的所有通用符号在名为COMMON的section内

::

    .bss { *(.bss) *(COMMON) }   //将所有输入文件的bss段以及通用符号放入到输出.bss section中


**在输出section中存放数据命令**

1) BYTE(EXPRESSION) 1字节
2) SHORT(EXPRESSION) 2字节
3) LONG(EXPRESSION) 4字节
4) QUAD(EXPRESSION) 8字节
5) SQUAD(EXPRESSION) 64位处理器的代码时，8字节

::

    SECTIONS 
    { 
        .text : 
        { 
            *(.text) 
        } 
        LONG(1) 
        .data : 
        {
            *(.data)
        }
    }

.. note::
    在当前输出section内可能存在未描述的存储区域(比如由于对齐造成的空隙)，可以用FILL(EXPRESSION)命令决定这些存储区域的内容，EXPRESSION的前两字节有效，
    这两字节在必要时可以重复被使用以填充这类存储区域。如FILE(0x9090)。在输出section描述中可以有=FILEEXP属性，它的作用如同FILE()命令,但是FILE命令只
    作用于该FILE指令之后的section区域，而=FILEEXP属性作用于整个输出section区域，且FILE命令的优先级更高


**输出section内命令的关键字**

1) CREATE_OBJECT_SYMBOLS: 为每个输入文件建立一个符号，符号名为输入文件的名字，每个符号所在的section是出现该关键字的section
2) CONSTRUCTORS: 与c++内的构造函数和析构函数相关

有一个特殊的输出section，名为 ``/DISCARD/`` ,被改section引用的任何输入section将不会出现在输出文件


**输出section属性**

1) TYPE: 每个输出section都有一个类型，如果没有指定TYPE类型，那么链接器根据输出section引用的输入section类型设置该输出section的类型，它可以有以下五种值
    
    A. NOLOAD: 该section在程序运行时，不被载入内存
    B. DESCT,COPY,INFO,OVERLAY : 这些类型很少被使用，只是为了向后兼容才被保留下来，这种类型的section必须被标记为“不可加载的",以便在程序运行时不为他们分配内存

2) LMA: 默认情况下，LMA等于VMA，但可以通过关键字AT()指定LMA

::

    SECTIONS
    {
        .text 0x1000 : { *(.text) _etext = .;}
        .mdata 0x2000:
        AT(ADDR (.text) + SIZEOF(.text))
        {_data = .;*(.data);_edata =.;}
        .bss 0x3000:
        {_bstart = .;*(.bss) *(COMMON); _bend = .;}
    }

- MEMORY命令

在默认情况下，链接器可以为section分配任意位置的存储区域。可以使用MEMORY命令定义存储区域，并通过输出section描述的REGION属性显示的将输出section现定于某块存储区域，
当存储区域大小不能满足要求时，链接器会报告该错误

::

    MEMORY {
        NAME1[(ATTR)]: ORIGIN = ORIGIN1, LENGTH = LEN1
        NAME2[(ATTR)]: ORIGIN = ORIGIN2, LENGTH = LEN2
        ...
    }


1) NAME: 存储区域的名字，这个名字可以与符号名，文件名，section名重复，因为它处于一个独立的名字空间
2) ATTR: 定义该存储区域的属性，属性值可以是以下7个字符 R 、W 、X 、A(可分配的section) 、L(初始化了的section)、 l(同L) 、!(不满足该字符之后的任一属性的section)
3) ORIGIN: 关键字，区域的开始地址，可简写成org或o
4) LENGTH: 关键字，区域的大小，可简写成len或l

- PHDRS命令

该命令仅在产生ELF目标文件时有效。ELF目标文件格式用program headers程序头来描述程序如何被载入内存，可以用objdump -p命令查看。当在本地ELF系统运行ELF目标文件格式的程序时，
系统加载器通过读取程序头信息以知道如何将程序加载到内存中。在连接脚本中不指定PHDRS命令时，链接器能够很好的创建程序头，但是有时需要更精确的描述程序头，这时候PHDRS命令
就派上用场了

::

    PHDRS
    {
        NAME TYPE [ FILEHDR ] [PHDRS] [AT (ADDRESS)]
        [ FLAGS (FLAGS) ];
    }

1) NAME: 程序段名，此名字可以与符号名，section名，文件名重复，因为它在一个独立的名字空间内
2) TYPE: PT_NULL 0 (表示未被使用的程序段) PT_LOAD 1 (表示该程序段在程序运行时应该被加载) PT_DYNAMIC 2 (表示该程序段包含动态连接信息) PT_INTERP 3(表示该程序段内包含程序加载器的名字在linux下常见的程序加载器是ld-linux.so.2) PT_NOTE 4(表示该程序段内包含程序的说明信息) PT_SHLIB 5(保留) PT_PHDR 6(表示该程序段包含程序头信息)
3) AT(ADDRESS): 定义该程序段的加载位置(LMA),该属性将覆盖该程序段内的section的AT()属性

例

::

    PHDRS
    {
        headers PT_PHDR PHDRS;
        interp PT_INTERP;
        text PT_LOAD FILEHDR PHDRS;
        data PT_LOAD;
        dynamic PT_DYNAMIC;
    }

    SECTIONS
    {
        . = SIZEOF_HEADERS;
        .interp : {*(.interp)} : text: interp
        .text : {*(.text)} :text
        .rodata : {*(.rodata)}
        ...
        . = . + 0x1000;
        .data : {*(.data)} : data
        .dynamic : {*(.dynamic)} :data :dynamic
    }
