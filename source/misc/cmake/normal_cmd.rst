CMake常见指令
==============


常见指令语法
-------------

- project指令语法

::

    project(projectname [CXX] [C] [Java])
    ##可以使用这个指令定义工程名称，并可指定工程支持的语言，支持的语言是可以忽略的，默认情况下支持所有语言。这个指令隐式的定义了两个cmake变量
    ##<project>_BINARY_DIR以及<project>_SOURCE_DIR
    #建议直接使用PROJECT_BINARY_DIR以及PROJECT_SOURCE_DIR,这样修改工程名称后也不会影响这两个变量


- set指令语法

::

    set(VAR [VALUE] [CACHE TYPE DOCSTRING [FORCE]])
    #set指令用来显式的定义变量


- message指令语法

::

    message([SEND_ERROR | STATUS | FATAL_ERROR] "message to display" ...)
    #这个命令用于向终端输出用户定义的信息，包含了三种类型:SEND_ERROR(产生错误，生成过程被跳过)、STATUS(输出前缀为-的信息)、FATAL_ERROR(立即终止所有cmake过程)

- add_library: 该指令的主要作用就是将指定的源文件生成链接文件，然后添加到工程中去

::

    add_library(<name> [STATIC | SHARED | MODULE | OBJECT]
                [EXCLUDE_FROM_ALL]
                source1 [source2 ...])

.. note::
    name:表示库文件的名字，该库文件会根据命令中列出的源文件来创建
    STATIC|SHARED|MODULE|OBJECT: 分别对应静态库，动态库，MODULE(一种不会被链接到其他目标中的插件，但可能会运行时加载), OBJECT(可以将源代码编译为对象文件)

- option: 为用户提供一个可选项，如果没有指定，将使用OFF作为初始值

::
    
    option(<option_variable> "help string" [initial value])
    #<option_variable>: 选项名
    #"help string" 提示用户的信息
    #[initial value]: 变量初始值ON or OFF
    例：
    option(WITH_BLUEFS "libbluefs library" OFF)
    构建过程中，会提示libbluefs library文字，等待用户输入(ON or OFF),输入的值保存在WITH_BLUEFS变量里

- execute_process: 执行进程．该命令可以执行一个或多个命令作为当前命令的子命令，将输出结果保存在cmake变量或文件中，所有的进程使用单个的标准错误输出管道

::

    execute_process(COMMAND <cmd1> [args1 ...]
                    COMMAND <cmd2> [args2...] [...]
                    [WORKING_DIRECTORY <directory>]
                    [TIMEOUT <seconds>]
                    [RESULT_VARIABLE <variable>]
                    [OUTPUT_VARIABLE <variable>]
                    [ERROR_VARIABLE <variable>]
                    [INPUT_FILE <file>]
                    [OUTPUT_FILE <file>]
                    [ERROR_FILE <file>]
                    [OUTPUT_QUIET]
                    [ERROR_QUIET]
                    [OUTPUT_STRIP_TRAILING_WHITESPACE]
                    [ERROR_STRIP_TRAILING_WHITESPACE]


.. note::
    如果指定了WORKING_DIRECTORY，则指定的目录将作为子进程当前的工作目录
    如果指定了TIMEOUT,则如果在指定时间内子进程未完成，将会被中断
    RESULT_VARIABLE保存最后命令执行的结果
    OUTPUT_VARIABLE,ERROR_VARIABLE保存标准输出和标准错误输出的内容
    OUTPUT_QUIET,ERROR_QUIER忽略标准输出和错误输出


例

::

    excute_process(
        COMMAND
        ${PYTHON_EXECUTABLE} "-c" "print('hello, world!')"
        RESULT_VARIABLE _status
        OUTPUT_VARIABLE _hello_world
        ERROR_QUIET
    )

- target_sources:往source文件中追加源文件

::

    add_executable(test_app "")

    target_sources(test_app 
        PRIVATE
        subsource.cpp
        PUBLIC
        subsource.h)

.. note::
    源文件一般指定为PRIVATE，因为源文件只是在构建时使用，而头文件指定为PUBLIC，是因为构建和编译时都会使用


- add_custom_command: 为生成的构建系统添加一条自定义的构建规则


有两种使用方法:

方法一:　增加一个自定义命令用来产生一个输出

::

  add_custom_command(OUTPUT output1 [output2...]            #输出，可以输出到一个变量中
                COMMAND command1 [ARGS] [args1...]          #自定义的命令
                COMMAND command2 [ARGS] [args2...]
                [MAIN_DEPENDENCY depend]
                [DEPENDS[depends...]]                       #列出该命令的依赖项
                [IMPLICIT_DEPENDS<lang1> depend1 ...]
                [WORKING_DIRECTORY dir]                     #指定在哪个目录下执行该命令
                [COMMENT comment] [VERBATIM] [APPEND])      #COMMENT提示信息会在构建时打印出来，
                                                            #VERBATIM告诉Cmake为指定的生成器和平台生成正确的命令，来确保是与平台无关的


方法二:

::

    add_custom_command(TARGET target
                        PRE_BUILD | PRE_LINK | POST_BUILD
                        COMMAND command1 [args1...]
                        COMMAND command2 [args2...]
                        [WORKING_DIRECTORY dir] 
                        [COMMENT comment] [VERBATIM])

- function & macro


::

    function(<name> [arg1 [arg2 [arg3 ...]]])
        COMMAND1(ARGS ...)
        COMMAND2(ARGS ...)
    endfunction(<name>)

    macro(<name> [arg1 [arg2 [arg3 ...]]])
        COMMAND1(ARGS ...)
        COMMAND2(ARGS ...)
    endmacro(<name>)

.. note::
    相同点: function和macro都没有返回值
    不同点:function和macro的变量作用域不同，如果宏内修改变量值宏外相同名称的变量值也会更改，function内则不会，如果想达到同样的效果则需要使用关键字PARENT_SCOPE



- check_cxx_compiler_flag: 判断C++编译器是否支持某flag，flag可以是-g,-std=c++11等

::

    check_cxx_compiler_flag(<flag> <var>)
    例
    check_cxx_compiler_flag("-std=c++11" COMPILER_SUPPORTS_CXX11)
    unset(COMPILER_SUPPORTS_CXX11 CACHE)
    if(COMPILER_SUPPORTS_CXX11)
        set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")
    else()
        message(STATUS "the compiler has no C++11 support")
    endif()

check_c_compiler_flag使用方法类似


- configure_file: 拷贝input文件到output,并更改其中的内容

::
    
    configure_file(<input> <output>
                    [COPYONLY] [ESCAPE_QUOTES] [@ONLY]
                    [NEWLINE_STYLE [UNIX|DOS|WIN32|LF|CRLF]])


- set_target_properties: 为目标文件设置属性，语法如下

::

    set_target_properties(target1 target2 ...
                        PROPERTIES prop1 value1
                        prop2 value2...)


- include_directories: 添加头文件目录，相当于把路径添加到环境变量中

- link_directories: 添加库文件目录，相当于把需要链接的库文件目录添加到LD_LIBRARY_PATH中

- find_library: 查找库所在的目录

- list: 列表操作，有以下方法

::

    #返回list的长度
    list(LENGTH <list> <output variable>)       
    #返回list中index的element到value中
    list(GET <list> <element index> [<element index> ...] <output variable>)
    #添加新的element到list中
    list(APPEND <list> [<element> ...])
    #返回list中element的index,没有找到返回-1
    list(FIND <list> <value> <output variable>)
    #将新element插入到list中的index位置
    list(INSERT <list> <element_index> <element> [<element> ...])
    #从list中删除某个element
    list(REMOVE_ITEM <list> <value> [<value> ...])
    #从list中删除指定index的element
    list(REMOVE_AT <list> <index> [<index> ...])
    #从list中删除重复的element
    list(REMOVE_DUPLICATES <list>)
    #将list的内容反转
    list(REVERSE <list>)
    #将list按字母顺序排序
    list(SORT <list>)

- file: 文件操作命令


::

    #Reading
        file(READ <filename> <out-var> [...])
        file(STRINGS <filename> <out-var> [...])
        file(<HASH> <filename> <out-var>)
        file(TIMESTAMP <filename> <out-var> [...])
        file(GET_RUNTIME_DEPENDENCIES [...])

    #Writing
        file({WRITE | APPEND} <filename> <content> ...)
        file({TOUCH | TOUCH_NOCREATE} [<file> ...])
        file(GENERATE OUTPUT <output-file> [...])

    #Filesystem
        file({GLOG | GLOB_RECURSE} <out-var> [...] [<globbing-expr>...])
        file(RENAME <oldname> <newname>)
        file({REMOVE | REMOVE_RECURSE} [<files> ...])
        file(MAKE_DIRECTORY [<dir>...])
        file({COPY | INSTALL} <file>... DESTINATION <dir> [...])
        file(SIZE <filename> <out-var>)
        file(READ_SYMLINK <linkname> <out-var>)
        file(CREATE_LINK <original> <linkname> [...])

    #Path Conversion
        file(RELATIVE_PATH <out-var> <directory> <file>)
        file({TO_CMAKE_PATH | TO_NATIVE_PATH} <path> <out-var>)

    #Transfer
        file(DOWNLOAD <url> <file> [...])
        file(UPLOAD <file> <url> [...])

    #Locking
        file(LOCK <path> [...])


- string

::
    
    #search and replace
        string(FIND <string> <substring> <out-var> [...])
        string(REPLACE <match-string> <replace-string> <out-var> <input> ...)

    #Regular Expressions
        string(REGEX MATCH <match-regex> <out-var> <input>...)
        string(REGEX MATCHALL <match-regex> <out-var> <input>...)
        string(REGEX REPLACE <match-regex> <replace-expr> <out-var> <input>...)

    #Manipulation
        string(APPEND <string-var> [<input>...])
        string(PREPEND <string-var> [<input>...])
        string(CONCAT <out-var> [<input>...])
        string(JOIN <glue> <out-var> [<input>...])


- fin_package: 寻找外部项目，并加载设置


::

    find_package(<package> [version] [EXACT] [QUIET] [MODULE]
                [REQUIRED] [[COMPONENTS] [components...]]
                [OPTIONAL_COMPONENTS components...]
                [NO_POLICY_SCOPE])


- cmake_parse_arguments: CMake参数解析命令，可以用于解析函数或宏的参数列表

::

    cmake_parse_arguments(<prefix> <options> <one_value_keywords> <multi_value_keywords> <args>...)
    cmake_parse_arguments(PARSE_ARGV <N> <prefix> <options> <one_value_keywords> <multi_value_keywords>)


.. note::
    options:可选值，此处包含可选项的变量的名称，对应的值为TRUE或FALSE
    one_value_keywords:单值关键词列表
    multi_value_keywords:多值关键词列表
    args:参数，一般传入${ARGN}即可
    prefix:前缀，解析出的参数都会按照prefix_参数名的形式形成新的变量


::

    function(my_install)
        set(options OPTIONAL FAST)
        set(oneValueArgs DESTINATION RENAME)
        set(multiValueArgs TARGETS CONFIGURATIONS)
        cmake_parse_arguments(my_install "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})
    endfunction()

    函数调用
    my_install(TARGETS foo bar DESTINATION bin OPTIONAL blub)
    #可选值OPTIONAL和FAST，函数调用时传入了OPTIONAL
    #单值关键词列表包含DESTINATION和RENAME，函数调用时传入DESTINATION，参数名为bin
    #多值关键词列表包含TARGETS和CONFIGURATIONS









