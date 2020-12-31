用户态GPIO操作
==============

sysfs接口
---------

用户可使用sysfs按照gpio序号操作GPIO，目录为/sys/class/gpio 
通常使用export将指定序号的gpio导出，导出后会产生一个gpio<number>的目录
改目录下有value、dirction、edge、active_state的设置和操作的接口

实际使用中有许多问题

1)  用户空间获取和设置GPIO之需要读写gpio/value这个文件，频繁操作会造成大量的上下文切换的性能损耗，而且频率也上不去。
2)  所有的gpio按照序号排序，没有很好的体现gpiochop的模型。
3)  在读取event中会出现上下文切换，如果在上下文切换时再发现一个event可能会无法获取而导致丢失。
4)  没有详细的应用程序权限区分，只要是可以操作设备文件的特权用户都可以操作任何gpio设备，可能会造成竟态问题。
5)  想要使用每个gpio都必须单独导出，并且使用过程中要使用多个就必须导出多个。
6)  polling操作不好，容易丢失时间并且每个口都需要一个poll一个打开文件。

使用示例::

    $ echo 483 > /sys/class/gpio/export
    导出gpio
    $ echo out > /sys/class/gpio/gpio483/direction
    设置GPIO方向
    $ echo 1 > /sys/class/gpio/gpio483/value

    $ echo in > /sys/class/gpio/gpio483/direction
    $ cat /sys/class/gpio/gpio483/value


字符设备接口
------------

新的字符GPIO驱动接口将单独的gpiochip变为一个/dev目录下的字符设备文件,之后通过C语言的ioctl接口来申请和操作gpio

新的GPIO驱动需要在4.8内核以上的版本才会支持

有以下特性

1)  每一个gpiochip对应一个/dev的gpiochip<number>文件。
2)  使用ioctl、poll、read等方法操作。
3)  支持同时申请多个IO口、设置、获取多个IO值
4)  可以通过别名定位gpiochip和line。
5)  可以为line增加open drain和open source标识。
6)  每一个line都有consumer字符串,用户表示line的使用者
7)  支持uevent，更好的poll,不会丢失事件。

C语言接口
^^^^^^^^^

C语言API接口主要有以下功能

-   获取chip_info
-   获取line_info
-   申请lines以对其进行操作
-   设置line的值
-   获取line的值
-   申请line以产生事件
-   polling事件
-   读取事件


* 常用操作

::

    ## set gpio chip 0 pin 10 to low
    struct gpiod_line *line;
    struct gpiod_chip *chip;

    chip = gpiod_chip_open(0);
    line = gpiod_chip_getline(chip, 10);
    
    gpiod_line_request_output(line, GPIOD_TEST_CONSUER, 0);
    

    ## get gpio chip 1 pin 36 value
    chip = gpiod_chip_open(1);
    line = gpiod_chip_getline(chip,36);

    gpiod_line_request_input(line, "test_admin");
    value = gpiod_line_get_value(line);

-   libgpiod支持event操作

::

    ## event 操作

    struct gpiod_line_event ev;
    struct gpiod_line *line;
    struct gpiod_chip *chip;
    struct timespec ts = {1, 0};  #1s timeout

    chip = gpiod_chip_open(0);
    line = gpiod_chip_get_line(30);

    gpiod_line_request_rising_edge_events(line, "test_event");
    //gpiod_line_request_falling_edge_events(line, "test_event");
    //gpiod_line_request_both_edges_events(line, "test_event");
    gpiod_line_event_wait(line，&ts);
    gpiod_line_event_read(line, &ev);

    if(ev.event_type == GPIOD_LINE_EVENT_RISING_EDGE)
        printf("event rising get!\n");

更详细的描述可以查看源码或者源码目录下的tests文件.

命令行工具(gpiod-tools)
^^^^^^^^^^^^^^^^^^^^^^^

- 列出所有的GPIO

  ::

  $ gpiodetect
    gpiochip0 [600000.gpio] (128 lines)
    gpiochip1 [601000.gpio] (36 lines)

- 列出某个gpio chip的情况
  
  ::

    $ gpioinfo 0
    gpiochip0 - 128 lines:
        line   0:      unnamed       unused   input  active-high 
        line   1:      unnamed       unused   input  active-high 
        line   2:      unnamed       unused   input  active-high 
        line   3:      unnamed       unused   input  active-high 
        line   4:      unnamed       unused   input  active-high 
        line   5:      unnamed       unused   input  active-high 
        line   6:      unnamed       unused   input  active-high 
        line   7:      unnamed       unused   input  active-high 
        line   8:      unnamed       unused   input  active-high 
        line   9:      unnamed       unused   input  active-high 
        line  10:      unnamed       unused   input  active-high 
        line  11:      unnamed       unused  output  active-high 
        line  12:      unnamed       unused  output  active-high 

- 设置gpio

  ::

    $ gpioset 0 9=1
    $ gpioget 0 9

- 监控gpio状态

  ::

    $ gpiomon 0 9
    event: FALLING EDGE offset: 99 timestamp: [1609407267.241196770]
    event:  RISING EDGE offset: 99 timestamp: [1609407272.243466065]
    event: FALLING EDGE offset: 99 timestamp: [1609407274.245885040]
    event:  RISING EDGE offset: 99 timestamp: [1609407279.248305575]

