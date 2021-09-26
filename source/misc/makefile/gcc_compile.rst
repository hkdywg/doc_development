gcc编译选项总结
=================

介绍
-----

gcc和g++分别是gnu的c以及c++编译器，gcc/g++在执行编译工作的时候，总共需要4步

1) 预处理，生成.i的文件(由预处理器cpp完成)
2) 将预处理后的文件转换成汇编文件，生成.s文件(由编译器egcs完成)
3) 由汇编变为目标代码(机器代码)生成.o文件(由汇编器as完成)
4) 连接目标代码，生成可执行程序(由链接器ld完成)


详细可参考gcc官方文档 https://gcc.gnu.org/onlinedocs/gcc/Option-Summary.html


常用编译选项
-------------

::

    -c 只编译生成目标文件
    -E 只运行C预编译器
    -g 生成调试信息
    -IDIRECTORY 指定额外的头文件搜索路径DIRECTORY
    -LDIRECTORY 指定额外的函数库搜索路径
    -lLIBRARY 连接时搜索指定的函数库LIBRARY
    -o 生成指定的输出文件
    -O0 不进行优化处理
    -O 或 -O1 优化生成代码
    -O2 进一步优化
    -O3 比-O2更进一步优化，包括inline函数
    -shared 生成共享目标文件，通常用在建立共享库时
    -static 禁止使用共享连接
    -w 不生成任何警告信息
    -Wall 生成所有警告信息



参数详解
^^^^^^^^^

- -c

只激活预处理，编译和汇编，生成obj文件

::
    
    gcc -c hello.c
    只会生成hello.o文件

- -S

只激活预处理和编译，生成汇编代码.s

::

    gcc -S hello.c
    生成hello.s文件

- -E

只激活预处理，这个不生成文件，你需要把它重定向到一个输出文件里面

::

    gcc -E hello.c > log

- -o 

指定目标文件名，缺省情况下gcc编译出来的文件是a.out

::

    gcc -o hello hello.c


- -include file

包含某个文件，功能类似于在文件中使用#include <filename>

::

    gcc hello.c -include src/hello.h

- -Dmacro

相当于C语言中的 #define macro

- -Dmacro=defn

相当于C语言中的#define macro defn

- -Umacro

相当于C语言中的#undef macro

- -Idir

在你用#include "filename"的时候，gcc会首先在当前目录查找你指定的头文件，如果没有找到，则会去缺省的头文件路径找，如果使用-I指定了目录，
则会首先在指定的路径查找，如果找不到再去按顺序查找

- -Ldir

指定编译的时候搜索库的路径


- -static

禁止使用动态库，编译出来的东西比较大，但不要需要动态链接库就可以运行

- -share

使用动态库，生成的文件比较小，一般由其他应用程序进行连接

- -fPIC

产生位置无关的代码，当产生共享库的时候，应该创建位置无关的代码，这会让共享库使用任意的地址而不是固定的地址

::

    gccc -shared -fPIC -o hello.so hello.c

- -v

参数-v提供详细信息，打印gcc编译一个文件的时候的所有步骤

- -Werror

使用这个参数可以将所有的警告信息转换为错误

- -std

指定支持的c/c++标准


