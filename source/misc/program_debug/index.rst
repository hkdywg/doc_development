调试手段
========

编译阶段

1)  nm              获取二进制文件包含的符号信息
2)  strings         获取二进制文件包含的字符串常量
3)  strip           去除二进制文件包含的字符
4)  readelf         显示目标文件详细信息
5)  objdump         尽可能反汇编出源代码
6)  addr2line       根据地址查找代码行


运行阶段

1)  gdb             强大的调试工具
2)  ldd             显示程序需要使用的动态库和实际使用的动态库
3)  strace          跟踪程序当前的系统调用
4)  time            查看程序执行时间，用户态时间，内核态时间
5)  gprof           显示用户态各函数执行时间
6)  valgrind        显示内存错误
7)  mtrace          检查内存错误

编译阶段
--------

nm
^^

nm 命令可以查看二进制目标文件(可以是库文件或者可执行文件)的符号表

nm 为name的缩写

strings
^^^^^^^

strings 可以打印文件中可打印的字符，这个文件可以是文件文件，可执行文件，动态链接库，静态连接库

strip
^^^^^

strip可以从特定文件中剥离掉一些符号信息和调试信息。

那strip命令有什么用处呢？经过strip处理后的文件会变小，但是依然可以运行。这样可以节省很多空间。

strip之后nm看不到任何信息

readelf
^^^^^^^

readelf用来读取elf文件中的内容，elf(executable & linkable format)是一种文件格式，我们常见的目标文件，动态库文件和可执行文件都属于这个类型。

objdump
^^^^^^^

objdump工具用来显示二进制文件的信息，就是以一种可阅读的格式让你更多的了解二进制二年间可能带有的附加信息。

1) -f 显示文件头信息
2) -D 反汇编所有section
3) -h 显示目标文件各section的头部摘要信息
4) -x 显示所有可以用的头信息，包括符号表、重定位入口。-x 等价于-a -f -h -r -t同时指定
5) -i 显示文件的重定位入口，如果和-d或者-D一起使用，重定位部分以反汇编后的格式显示出
6) -r 显示文件的重定位入口。
7) -S 尽可能的反汇编出源代码，尤其是当编译的时候指定了-g这种调试参数时，效果比较明显。
8) -t 显示文件的符号表入口。类似于nm -s提供的信息

示例：

::

    objdump -x main


dmesg && addr2line
^^^^^^^^^^^^^^^^^^

在应用程序运行中发生segment fault时没有生成core文件可以通过 ``dmesg`` 和 ``addr2line`` 进行问题查找。

以下为示例内容 

::

    #include <stdio.h>

    int main()
    {
        char *string_ptr = NULL;

        *string_ptr = "core dump";

        return 0;
    }

对main.c文件进行编译，注意需要增加 ``-g`` 选项，以生成需要的debug符号内容。

::

    gcc -g main.c -o main

然后运行 ./main ,发现发生了segment fault，通过 ``dmesg`` 查看错误发生时的打印信息

::

    [108081.093508] main[18210]: segfault at 0 ip 000055949e6fe64e sp 00007ffff2936400 error 6 in main[55949e6fe000+1000]

以上信息说明：
系统当前时间    进程名字以及PID     segfault at 引起故障的地址  ip指令的内存地址    sp堆栈指针地址 [55949e6fe000+1000] 崩溃时映射的虚拟内存起始地址和大小

::

    addr2line -e main 64e
    addr2line -e main ip地址-模块入口地址


运行阶段
--------

gdb
^^^

GDB是gnu开源组织发布的一个强大的unix下的程序条是工具。

GDB主要完成以下四方面的功能:

1) 启动程序，可以按照自定义需求去运行程序
2) 调试程序，可以让程序在指定位置停住
3) 当程序停止运行时，可以检查此时程序中方发生的事
4) 动态的改变程序的执行环境

- 运行程序

::

    gdb <program>
    program也就是你的执行文件，一般在但前目录下
    
    gdb <program> core
    用gdb同时调试一个运行程序和core文件，core是程序非法执行后core dump后产生的文件

    gdb <program> <PID>
    如果你的程序是一个服务程序，那么你可以指定这个程序运行时的进程ID，gdb会自动attach上去，并调试它。
    同样用gdb调试一个已经在运行的程序也可以用此方法

GDB启动时可以加上一些GDB的启动开关，详细的可以用dgb -help查看，下面列举一些比较常用的参数

::

    -symbols <file>
    -s <file>
    从指定文件中读取符号表

    -se <file>
    从指定文件中读取符号表信息，并把他用在可执行文件中

    -core <file>
    -c <file>
    调试时core dump的core文件。

    -directory <directory>
    -d <directory>
    加入一个源文件搜索路径，默认搜索路径时环境变量中PATH所定义的路径


GDB输入命令时，可以用敲击两次TAB键来补齐命令的全称，如果有重复的gdb会进行补齐。

程序的运行常需要做以下四方面的事
1)  程序运行参数

::

    set args 可指定运行时参数
    如：set args 10 "test gdb"
    show args 可以查看设置好的运行参数

2)  运行环境

::

    path <dir>
    可指定程序运行路径
    show path
    查看程序的运行路径
    set environment varname [=value]
    设置环境变量，如set env USER=ywg
    show environment [varname]
    查看环境变量


3)  工作目录

::

    cd <dir>
    相当于shell的cd命令
    pwd
    显示当前所在目录

4)  程序的输入输出

::

    info terminal 显示你程序用到的终端模式
    使用重定向控制程序输出。 如： run > outfile
    tty命令可以指定输入输出的终端设备 如： tty /dev/tty10

GDB中有以下几种方式暂停：断点(breakpoint)、观察点(catch point)、信号(signal)、线程停止(thread stop)。如果要恢复程序运行，可以使用c或者continue命令

- 设置断点

::

    break <function>
    break <linenum>
    break filename:function
    break filename:linenum
    break +offset
    break -offset
    在当前行号前面或者后面的offset行停住，offset为自然数
    break *address
    在程序运行的内存地址处停住
    break
    break命令没有参数时，表示在下一条指令处停住
    break ... if <condition>
    ... 可以是上述参数，condition表示条件，在条件成立时停住，
    如 break main.c:print_message if flag==1

    info breakpoints [n]
    info break [n]
    查看断点信息

- 设置观察点

观察点一般用来观察某个表达式(变量也是一种表达式)的值是否有变化，如果有变化马上停住程序 

::

    watch <expr>
    为表达式(变量)expr设置一个观察点，一旦表达式有变化，马上停住程序
    rwatch <expr>
    当表达式expr被读时，程序停住
    awatch <expr>
    当表达式的值被读或者被写时，停住程序
    info watchpoints
    列出观察点

- 设置捕捉点

可以通过设置捕捉点来捕捉程序运行时的一些事件，如载入共享库或者c++的异常

::
    
    catch <event>
    tcatch <event>
    只设置一次捕捉点，当程序停住后自动删除

当event发生时，停住程序，event可以是下面的内容

1)  throw一个c++抛出的异常。(throw)
2)  catch一个c++捕捉到的异常。(catch为关键字)
3)  exec 调用系统调用exec时
4)  fork 调用系统调用fork时
5)  vfork 调用系统调用vfork时
6)  load或者load <filename> 载入共享库时 
7)  unload或者unload <filename> 卸载共享库时

- 维护停止点

如果觉得已定义好的停止点没有用了，可以使用delete、clear、disable、enable这几个命令来进行维护

::

    clear
    清除所有已定义的停止点
    clear <function>
    clear <filename:function>
    
    clear <linenum>
    clear <filename:linenum>

    delete [breakpoints][range...]
    删除指定断点，如果不指定断点号则删除所有断点

    disable [breakpoints][range...]

    enable [breakpoints][range...]

    enable [breakpoints] once range...
    enable [breakpoints] delete range...

- 维护停止条件

一般来说，为断点设置一个条件，可以使用if关键字，后面跟其断点条件。并且条件设置好后，我们可以用condition命令来修改断点条件. 目前只有break可watch支持if，catch不支持

::

    condition <bnum> <expression>
    修改断点号为bnum的停止条件为expression

    condition <bnum>
    清除断点后为bnum的停止条件

    还有一个比较特殊的维护命令ignore，你可以指定程序运行时，忽略停止条件几次

    ignore <bnum> <count>
    表示忽略断点号为bnum的停止条件几次

- 为停止点设定运行命令

我们可以使用gdb提供的commond命令来设置停止点的运行命令，也就是说，当运行的程序停止时，我们可以让其自动运行一些别的命令

::

    commonds [bnum]
    ...command-list...
    end

    为断点bnum指定一个命令列表，当程序被该断点停住时，gdb会自动运行命令列表中的命令。

- 恢复程序运行和单步调试

::

    continue [ignore-count]
    c [ignore-count]
    fg [ignore-count]
    恢复程序运行，直到程序结束，或者下一个断点到来。ignore-count表示忽略其后的断点次数，c，fg都是一样的意思

    step <count>
    单步跟踪，如果有函数调用则进入函数。

    next <count>
    同时是单步跟踪，如果有函数调用不会就进入函数

    set step-mode
    set step-mode on
    打开step-mode模式，在进行单步跟踪时，程序不会因为没有debug信息而不停住

    set step-mode off

    finish
    运行程序，直到当前函数完成返回，并打印函数返回时的堆栈地址和返回值及参数值等信息

    until或u
    当你厌倦了在一个循环体内单步跟踪时，这个命令可以运行程序直到退出循环体

    stepi或si
    nexti或ni
    单步跟踪一条机器指令。一条程序代码可能由数条机器指令完成，stepi和nexti可以但不执行机器指令

-   信号

信号是一种软中断，是一种处理异步事件的方法。
你可以要求gdb收到指定信号时马上停止正在运行的程序，以提供你调试，你可以用dgb的handle命令来完成这一功能。

::

    handle <signal> <keywords...>
    在gdb中点以一个信号处理，信号<signal>可以以SIG开始或者不以SIG开头，可以点一个一个要处理信号的范围(如：SIGIO-SIGKILL,表示要处理SIGIO到SIGKILL的信号其中包括SIGIO，SIGIOT，SIGKILL三个信号)
    也可以用关键字all来标明要处理所有信号

    nostop
    当被调试的程序收到信号时，不会停止程序，但会打印消息告诉你受到这种信号

    stop
    当调试的程序受到信号时，程序停止运行

    print
    。。。。。。。gdb显示一条消息

    noprint
    。。。。。。。gdb不显示消息

    pass
    noignore
    。。。。。。。gdb不处理信号，这表示，gdb会把这个信号交给调试程序会处理

    nopass
    ignore
    。。。。。。。gdb不会让调试程序来处理这个信号

    info signals
    info handle
    查看有哪些信号在gdb检测中

-   线程

::

    break <linespec> thread <threadno>
    break <linespec> thread <threadno> if ...
    linespec指定了断点设置在源程序的行号，threadno指定了线程ID，注意这个ID是GDB分配的，可以通过info threads命令来查看运行程序中的线程信息。如果不指定线程ID则认为是在
    所有线程上都设置断点。

    backtrace
    bt
    打印当前函数调用栈的所有信息

    backtrace <n>
    bt <n>
    表示只打印n层的栈信息

    如果要查看某一层的信息，需要切换当前的栈，一般来说，程序停止时，最顶层的栈就是当前栈，如果需要查看栈下层的详细信息，则需要切换当前栈

    frame <n>
    f <n>
    n是一个从0开始的整数，是栈中的层编号。frame 0表示栈顶

    up <n>
    表示向栈的上面移动n层

    down <n>

    frame或f
    会打印出这些信息，栈的层编号，当前的函数名，函数参数值，函数所在的文件及行号，函数执行到的语句

    info frame
    info f
    这个命令会打印出更详细的当前栈层信息，只不过，大多是是运行时的内存地址。比如函数地址，调用函数的地址，目前函数是什么程序语言写成的，函数参数地址以及值，局部变量地址等

    info args
    打印当前函数的参数名及值

    info locals
    打印当前函数中所有局部变量及其值

    info catch
    打印出当前函数中异常处理信息


-   查看值

::

    file::varaible
    function::varible
    例：p main.c::flag

    局部变量和全局变量重名时，局部变量会隐藏全局变量

    查看数组或者指针的值
    例：char *array = "ywg test gdb"
    p *array@12

    输出格式

    p i
    p/a i   
    按十六进制格式显示i值
    p/f i
    按浮点数格式显示i值
    p/c i
    按字符格式显示i值


-   自动显示

你可以设置一些自动显示的变量，，单程序停住时，这些变量自动显示,相关的命令时display

::

    display <expr>
    display/<fmt> <expr>
    display/<fmt> <addr>
    expr是一个表达式，fmt是显示的格式，

    display/i $pc
    $pc是gdb的环境变量，表示指定的地址，/i表示输出格式为机器指令码

    undisplay <dnums>
    delet display <dnums>
    disable display <dnum>
    enable display <dnum>

-   查看寄存器

::

    info registers
    查看寄存器的值

    info all-registers

    info registers <regname>
    寄存器放置了程序运行时的数据，比如程序当前运行的指令地址(ip)，程序的当前堆栈地址(sp)

    也可以使用print命令来访问寄存器的情况，如 p $eip


-   修改变量值

::

    print x=4

    set var x=4

-   跳转执行

::

    jump <linespec>
    指定下一条语句的执行点，<linespec>可以是文件的行号，也可以是file:line格式，可以是+num这种偏移量格式

    jump <address>
    这里的address是代码行的内存地址

    注意：jump命令不会改变当前程序栈中的内容，所有当你从一个函数跳到另一个函数时，当函数运行完进行弹栈操作时必然会发生错误，所有最好是在同一函数中进行跳转

    熟悉汇编的人应该知道，程序运行时，有一个寄存器时用于保存当前代码所在的内存地址，所有jump命令也就是改变了这个寄存器中的值，于是你可以使用set $pc来更改跳转执行的地址

    set $pc = 0x485

-   产生信号

::

    signal <signal>
    

-   强制函数返回

::

    return
    return <expresstion>

-   强制调用函数

::

    call <expr>
    

ldd
^^^

示例：

::

    ldd main
	linux-vdso.so.1 (0x00007ffd26b78000)
	libc.so.6 => /lib/x86_64-linux-gnu/libc.so.6 (0x00007f0666ed7000)
	/lib64/ld-linux-x86-64.so.2 (0x00007f06674ca000)
    
1) 第一列：程序需要依赖什么库
2) 第二列：系统提供的和程序需要的库所对应的库
3) 第三列：库加载的地址

ldd用来查看程序所需要的共享库，常用来解决程序因缺少莫哥库文件而不能运行的一些问题。

- 原理：

ldd不是个编译好的可执行程序，而是一个shell脚本。ldd显示可执行模块的dependency的工作原理，其实质是通过ld-linux.so(elf动态库的装载器)实现的。
ld-linux.so模块会优先于executable模块程序工作，并获得控制权，因此当上述的那些环境变量被设置时，ld-linux.so选择了显示可执行模块的dependency。


strace
^^^^^^

strace是一个集诊断、调试、统计与一体的工具，我们可以使用strace对应用的系统调用和信号传递的跟踪结果来对应用进行分析，以达到解决问题或者了解应用工作过程的目的。

time
^^^^

time命令用来计算某个程序的运行耗时(real)、用户态cpu耗时(user)、系统态cpu耗时(sys)。

误区一:real_time = user_time + sys_time

real_time 是时钟走过的时间，user_time是程序在用户态的cpu时间，sys_time为程序在核心态的cpu时间。

cpu_usage = (user_time + sys_time)/real_time * 100%

误区二：real_time > user_time + sys_time 

单核cpu的时候上述公式确实满足，但是多核的情况就不一样了。

gprof
^^^^^

gprof在性能优化章节进行详细描述。

valgrind
^^^^^^^^


mtrace
^^^^^^
