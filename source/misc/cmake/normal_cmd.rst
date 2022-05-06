CMake常见指令
==============


常见指令语法
-------------

**PROJECT指令语法**

::

    PROJECT(projectname [CXX] [C] [Java])
    ##可以使用这个指令定义工程名称，并可指定工程支持的语言，支持的语言是可以忽略的，默认情况下支持所有语言。这个指令隐式的定义了两个cmake变量
    ##<project>_BINARY_DIR以及<project>_SOURCE_DIR
    #建议直接使用PROJECT_BINARY_DIR以及PROJECT_SOURCE_DIR,这样修改工程名称后也不会影响这两个变量


**SET指令语法**

::

    SET(VAR [VALUE] [CACHE TYPE DOCSTRING [FORCE]])
    #SET指令用来显式的定义变量


**MESSAGE指令语法**

::

    MESSAGE([SEND_ERROR | STATUS | FATAL_ERROR] "message to display" ...)
    #这个命令用于向终端输出用户定义的信息，包含了三种类型:SEND_ERROR(产生错误，生成过程被跳过)、STATUS(输出前缀为-的信息)、FATAL_ERROR(立即终止所有cmake过程)

**ADD_EXECUTABLE指令**

::

    ADD_EXECUTABLE(exe_name ${SRC_LIST})
    #定义可执行文件，以及对应的源码
