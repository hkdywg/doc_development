shell内建命令
==============

所谓的shell内建命令，就是由bash自身提供的命令，而不是文件系统中的某个可执行文件

例如，用于进入或者切换目录的cd命令，该命令不是一个外部文件，只要在shell中就可以运行这个命令

可以用type来确定一个命令是否是内建命令:

::

    yinwg@yinwg-ThinkPad-E470:~/tmp/shell$ type cd
    cd 是 shell 内建

    yinwg@yinwg-ThinkPad-E470:~/tmp/shell$ type ifconfig 
    ifconfig 是 /sbin/ifconfig

可见cd是一个shell内建命令，而ifconfig是一i个外部文件

通常来说，内建命令比外部命令执行的更快，执行外部命令时不但会触发磁盘i/o还需要fork出一个单独的进程来执行，执行完成后再退出。而执行内建命令相当于调用当前shell进程的一个函数


**bash shell内建命令**


=================   =================================================================================================
    命令                                            说明
-----------------   -------------------------------------------------------------------------------------------------
:                   扩展参数列表，执行重定向操作
.                   读取并执行指定文件中的命令(在当前shell环境中)
alias               为指定的命令定义一个别名
bg                  将作业以后台模式运行
bind                将键盘序列绑定到一个readline函数或宏
break               退出for while select until循环
builtin             执行指定的shell内建命令
caller              返回活动子函数调用的上下文
cd                  将当前目录切换为指定目录
command             指行指定的命令，无需进行通常的shell查找
compgen             为指定的单词生产可能的补全选项
complete            显示指定的单词是如何补全的
compopt             修改指定单词的补全选项
continue            继续执行for while select until循环的下一次迭代
declare             声明一个变量或变量类型
dirs                显示当前存储目录的列表
disown              从进程作业表中删除指定的作业
echo                将指定字符串输出到STDOUT
enable              启用或禁用指定的内建shell命令
eval                将指定的参数拼接成一个命令，然后执行该命令
exec                用指定命令替换shell进程
exit                强制shell以指定的退出状态码退出
export              设置子shell子进程可用的变量
fc                  从历史记录中选择命令列表
fg                  将作业以前台模式运行
getopts             分析指定的位置参数
hash                查找并记住指定命令的全路径名
help                显示帮助文件
history             显示命令历史记录
jobs                列出活动作业
kill                向指定进程ID发送一个系统信号
let                 计算一个数学表达式中的每个参数
local               在函数中创建一个作用域受限的变量
logout              退出登录shell
mapfile             从STDIN读取数据行，并将其加入索引数组
popd                从目录栈中删除记录
printf              使用格式化字符串显示文本
pushd               向目录栈添加一个目录
pwd                 显示当前工作目录的路径名
read                从STDIN读取一行数据并将其赋给一个变量
readarray           从STDIN读取数据行并将其放入索引数组
readonly            从STDIN读取一行数据并将其赋值给一个不可修改的变量
return              强制函数以某个值退出，这个值可以被调用脚本提取
set                 设置并显示环境变量的值和shell属性
shift               将位置参数一次向下降一个位置
shopt               打开/关闭控制shell可选行为的变量值
source              读取并执行指定文件中的命令(在当前shell环境中)
suspend             暂停shell的执行，直到收到一个SIGCONT信号
test                基于指定条件返回退出状态码0或1
times               显示累计的用户和系统时间
trap                如果收到了指定的系统信号，执行指定的命令
type                显示指定的单词如果作为命令将会被如何解释
typeset             申明一个变量或者变量类型
ulimit              为系统用户设置指定的资源上限
umask               为新建的文件和目录设置默认权限
unalias             删除指定的别名
unset               删除指定的环境变量或shell属性
wait                等待指定的进程完成，并返回退出状态码
=================   =================================================================================================


**alias unallias用法**

alias用来设置命令别名，可以将一些比较长的命令进行简化。alias命令的作用只限于该次登入的操作

::

    alias 新的命令='原命令 -选项/参数'

    alias -p #打印已经设置号的命令别名

    alias ll="ls -l --color=tty"
    alias rm='rm -i'

    unalias -a  #取消所有命令别名

    unalias ll


**作业控制bg fg jobs disown wait suspend kill用法**

bg命令用于将作业放到后台运行，使前台可以执行其他任务，与命令后面加 `&` 的效果使一样的

jobs命令用于显示linux中的任务列表即任务状态，包括后台运行的任务。该命令可以显示任务号以及对应的进程号，其中任务号是以普通用户的视角进行的，而
进程号则是从系统管理员的角度来看的。一个任务可以对应一个或者多个进程号

::

    jobs (选项) (参数)
    -l:显示进程号
    -p:仅显示任务对应的进程号
    -n:显示任务状态的变化
    -r:仅输出运行状态(running)的任务
    -s:仅输出停止状态(stopped)的任务


::

    bg 1    #后台执行任务号为1的任务
    fg 1    #将任务号为1的任务放在前台执行

disown命令用于从当前shell中移除作业

::

    disown [-h] [-ar] [jobspec ... | pid ...]
    -h:标记每个作业标识符，这些作业将不会在shell中收到sighub信号
    -a:移除所有作业
    -r:移除运行的作业
    jobspec:要移除的作业标识符
    pid:要移除的作业pid

.. note::
    disown只是移除作业，其实作业并没有停止运行

wait命令用来等待指令完成，直到其执行完毕后返回终端。该指令在等待作业时，在作业标识号前必须添加备份号"%"

::

    wait %3 #等待作业号为3的作业完成

suspend命令执行shell的挂起操作,直到收到一个SIGCONT信号

kill发送信号到作业或者进程

::

    kill -s sig 信号名称
    kill -n sig 信号名称对应的数字
    -l 列出信号名称


**bind命令 builtin命令**

bind命令用于显示和设置命令行的键盘序列绑定功能，通过这一命令可以提高命令行中操作效率

builtin命令用于执行指定shell内部命令，当系统中定义了与shell内部命令相同的函数时，使用builtin显式地执行shell内部命令，从而忽略定义的shell函数。

::

    bind：用法： bind [-lpvsPSVX] [-m 键映射] [-f 文件名] [-q 名称] [-u 名称] [-r 键序列] [-x 键序列:shell-命令] [键序列:readline-函数 或 readline-命令]
    bing (选项)
    -f<按键配置文件>：载入指定的按键配置文件
    -l:列出所有功能
    -m<按键配置>：指定的按键配置
    -q<功能>:显示指定功能的按键
    -v:列出目前的按键配置与其功能


实例

::

    bind -x '"\C-l":ls -l'      #直接按CTRL+L就列出目录


**declare**

::

    declare (选项) (参数)
    选项:
    -f:仅显示函数
    r:将变量设置为只读
    x:指定的变量会成为环境变量，可供shell以外的程序来使用
    i:设置值可以是数值，字符串或运算式
    参数:
    shell变量  格式为"变量名=值"


**trap命令**

trap用于捕捉信号和其他事件执行命令

信号是一种进程间的通信机制，应用程序收到信号后，有三种处理方式：忽略、默认、或捕捉。如果是SIG_IGN，就忽略信号，如果是SIG_DFT,则会采用系统默认的处理动作，通常是终止进程
或者忽略该信号。如果给该信号指定了一个处理函数(捕捉)，则会中断当前进程正在执行的任务转而去执行该信号的处理函数

::

        trap "rm -f ${WORKDIR}/tmpfile;exit" 2  #收到信号2时执行删除文件操作
        trap '' 2   #忽略信号
        trap 1 2    #重置


**shift命令**

shift用来移动位置参数

::

    cat test.sh
    #!/bin/bash

    echo $1 $2 $3
    shift 2
    echo $1 $2 $3

    bash test.sh a b c d e f
    a b c
    c d e
