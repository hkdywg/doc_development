Makefile函数总结
================

makefile函数调用，很像变量的使用，也是以"$"来标识的，其语法如下

::

    $(<function> <arguments>)

function就是函数名,arguments为函数参数，参数间以 ``,`` 隔开,函数名与参数之间以空格隔开


字符串处理函数
---------------


.. function:: subst from,to,text

    字符串替换函数，将字符串text中的from替换为to

    :param from,to,text:  from待替换的字符，to目标字符，text待处理的字符串
    :rtype: 返回替换完成的字符串

示例：

::

    $(subst ee,EE,feet on eth street)
    返回结果为fEEt on eth strEEt

.. function:: patsubst pattern,replacement,text

    模式字符串替换函数，查找text中的单词(单词以空格、tab、回车、换行分割)是否符合pattern模式，如果匹配的话则以replacement替换

    :param pattern,replacement:  pattern匹配的模式，replace替换的字符串
    :rtype: 返回替换完成的字符串

示例：

::

    $(patsubst %.c,%.o,bar.c test.c
    返回结果为bar.o test.o


.. function:: strip string

    去空格函数，去掉sting字符串中开头和结尾的空字符,并将中间的连续多个空字符合并为一个空字符

    :param string:  要处理的字符串
    :rtype: 返回替换完成的字符串

示例：

::

    $(strip         a       b c d)
    返回结果为 a b c d


.. function:: findstring find,in

    查找字符串函数，在字符串in中查找find字符串

    :param find,in:  输入字符串in,查找字符串find
    :rtype: 如果找到则返回find字符串，没有找到则返回空字符串

示例：

::

    $(findstring cat,cat dog)
    返回结果为 cat

.. function:: filter pattern, text

    过滤函数，以pattern模式过滤text字符串中的单词，patter可以有多个模式

    :param pattern, text:  pattern:过滤模式  text:需要处理的字符串
    :rtype: 返回符合模式pattern的字串

示例：

::

    sources := foo.c bar.c baz.s ugh.h
    foo: $(sources)
        gcc $(filter %.c, %.s, $(sources)) -o foo

    filter返回结果为 foo.c bar.c baz.s


.. function:: filter-out pattern, text

    反过滤函数，以pattern模式过滤text字符串中的单词，去除符合模式的单词，patter可以有多个模式

    :param pattern, text:  pattern:过滤模式  text:需要处理的字符串
    :rtype: 返回去除符合模式pattern后的字串

示例：

::

    sources := foo.c bar.c baz.s 
    foo: $(sources)
        gcc $(filter-out %.c, $(sources)) -o foo

    filter-out返回结果为 baz.s


.. function:: sort list

    排序函数，给字符串list中的单词进行排序(升序)

    :param list: 需要排序的字符串 
    :rtype: 返回排序后的字符串

示例：

::

    $(sort this is a test string)
    返回结果为 a i string test this 

.. function:: word n,text

    取单词函数，取字符串text中的第n个单词，从一开始

    :param n, text: n第n个单词    text需要处理的字符串
    :rtype: 返回第n个单词

示例：

::

    $(word 4, this is a test string)
    返回结果为 test


.. function:: words text

    字符串统计函数，统计text中单词的个数

    :param  text: text需要处理的字符串
    :rtype: 返回text中有多个单词

示例：

::

    $(words  this is a test string)
    返回结果为 5

.. function:: firstword text

    取首单词函数，返回字符串的第一个单词

    :param  text: text需要处理的字符串
    :rtype: 返回text的第一个单词

示例：

::

    $(firstword this is a test string)
    返回结果为 this



文件名操作函数
---------------

.. function:: dir names

    取目录函数，从文件名序列names中取出目录部分

    :param  names: names需要处理的文件名
    :rtype: 返回names文件的目录部分

示例：

::

    $(dir /usr/bin/bzip2)
    返回结果为 /usr/bin

.. function:: notdir names

    取文件函数，从文件名序列names中取出文件部分

    :param  names: names需要处理的文件名
    :rtype: 返回names文件的文件部分

示例：

::

    $(dir /usr/bin/bzip2)
    返回结果为 bzip2

.. function:: suffix names

    取后缀函数 

    :param  names: names需要处理的文件名
    :rtype: 返回names文件的后缀名

示例：

::

    $(suffix foo.c bar.s)
    返回结果为 .c .s

.. function:: basename names

    取前缀函数 

    :param  names: names需要处理的文件名
    :rtype: 返回names文件的前缀

示例：

::

    $(basename foo.c bar.s)
    返回结果为 foo bar

.. function:: addsuffix suffix,names

    增加后缀函数

    :param  suffix, names: suffix添加的后缀名 names需要处理的文件名
    :rtype: 返回添加完后缀名的文件名序列

示例：

::

    $(addsuffix .o, foo bar)
    返回结果为 foo.o bar.o

.. function:: addsprefix prefix,names

    增加前缀函数 

    :param  prefix, names: prefix添加的前缀名 names需要处理的文件名
    :rtype: 返回添加完前缀名的文件名序列

示例：

::

    $(addsuffix test_, foo.c bar.c)
    返回结果为 test_foo.c test_bar.c

.. function:: join list1,list2

    字符串连接函数,把字符串list2对应的加到list1的后面，如果<list1>的单词个数要比<list2>的多，那么，<list1>中的多出来的单词将保持原样。如果<list2>的单词个数要比<list1>多，那么，<list2>多出来的单词将被复制到<list1>中

    :param  list1, list2: 需要连接的字符串list1 list2
    :rtype: 返回连接过后的字符串

示例：

::

    $(join aa bb, 11 22 33)
    返回结果为 aa11 bb22 33


foreach函数
-----------

foreach函数和别的函数不一样，因为这个函数是用来做循环用的，Makefile中的foreach函数几乎是仿照shell中的for语句构建的

.. function:: foreach par,list,text

    这个函数的意思是把参数list中的单词逐一取出放到参数所指定的变量中，然后再执行text中包含的表达式,每一次text会返回一个字符串，循环过程中返回的的字符串会以空格分割,循环结束时整个返回

    :param  par, list: par变量， list循环列表
    :rtype: 返回text的所有返回值

示例：

::
    names := foo bar
    $(foreach par,$(names),$(addsufix .c,$(par)))
    返回结果为 foo.c bar.c


if 函数
--------

.. function:: if condition, then-part, else-part

    if判断函数，也可以不含else部分。表达式condition为真则执行then-part部分,否则执行else-part部分

    :param  condition, then-part, else-part: condition条件判断表达式
    :rtype: 返回then-part或else-part的执行结果

示例：

::

    source := Makefile.build xxx_defconfig
    $(if $(filter %.c,$(source)), $(addprefix uboot_,$(source)), $(addsufix .cmd,$(source)))
    返回结果为 uboot_Makefile.build uboot_xxx_defconfig

call函数
---------

call函数是唯一一个可以用来创建新的参数化的函数，你可以写一个非常复杂的表达式，这个表达式中你可以定义很多参数，然后你可以用call函数来向这个表达式传递参数

.. function:: call expression, parm1, parm2

    调用自定义的表达式expression

    :param  expression, param: express调用的表达式  pram参数
    :rtype: expression的返回值

示例：

::

    reverse = $(2) $(1)
    foo = $(call revers, a, b)
    此时foo的值就等于 b a


origin函数
----------

.. function:: origin variable

    返回变量是从哪里来的

    :param  variable: 需要判断的变量
    :rtype: 变量来源


shell函数
---------

shell函数是Makefile中直接调用shell命令

::

    contexts := $(shell cat foo)
    files := $(shell echo *.c)
