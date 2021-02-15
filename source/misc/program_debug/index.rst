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
