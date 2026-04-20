Cmake基础知识
==============


变量与缓存
-------------

本地变量
^^^^^^^^^^

可以用以下方式申明一个本地(local)变量

::

    set(MY_VARIBLE "value")


变量名通常全部用大写,变量值根在其后，在使用时需要用 ${MY_VARIBLE}。CMake有作用域的概念，在申明一个变量后，你之可以在他的作用域内访问这个变量。如果你将一个汉书或一个文件放到
一个子目录中，这个变量将不再被定义。可以通过在变量申明末尾添加PARENT_SCOPE来将他的作用域定为上一级作用域

示例：

::

    set(MY_LIST "one" "two")
    set(MY_LIST "oneltwo")      #使用;分割变量


缓存变量
^^^^^^^^

CMake提供了一个缓存变量来允许你从命令行中设置变量。CMake中已经有一些预置的变量，像 CMAKE_BUILD_TYPE。如果一个变量还没有被定义，你可以这样申明并设置它


::

    set(MY_CACHE_VARIBLE "value" CACHE STRING "description")


这样写不会覆盖以定义的值，这是为了让你只能在命令行中设置这些变量，而不会在CMake文件执行时被重新覆盖。如果你想把这些变量作为一个临时的全局变量，可以按以下操作

::

    set(MY_CACHE_VARIBLE "value" CACHE STRING "" FORCE)     #强制设置该变量的值
    mark_as_advanced(MY_CACHE_VARIBLE)                      #mark_as_advanced修饰以后，用户在执行cmake ../ -L时不会列出该变量
    或
    set(MY_CACHE_VARIBLE "value" CACHE INTERNAL "")


常见的BOOL类型变量设置


::

    option(MY_OPTION "this is settable from command line" OFF)


环境变量
^^^^^^^^^^

::

    set(ENV{MY_ENV_STRING} value)   #设置环境变量
    $ENV{MY_ENV_STRING}     #获取环境变量


缓存
^^^^

缓存实际上就是个文本文件，CMakeCache.txt，当你运行CMake构建目录时会创建它。CMake可以通过它来记住你设置的所有东西，因此你可以不必在运行CMake的时候再次列出所有的选项。


属性
^^^^^

待完善


Cmake编程
----------

控制流程
^^^^^^^^^

CMake有一个if语句可以进行流程控制

::

    if(varible)
         # if varible is 'ON', 'YES' , 'TRUE' , 'Y', or non zero number
    else()
        # if varible is '0' , 'OFF' , 'NO', 'FALSE' , 'N' , 'IGNORE' , 'NOTFOUND' , '""' , or ends in '-NOTFOUND'
    endif()


如果CMake版本大于3.1，可以按以下方式写

::

    if("${variable}")
        # True if variable is not false-like
    else()
        # Note that undefined variables would be `""` thus false
    endif()

这里有一些关键字可以设置，例如

- 一元的: NOT , TARGET, EXISTS(文件) , DEFINED等
- 二元的: STREQUAL, AND, OR, MATCHES(正则表达式)，VERSION_LESS, VERSION_LESS_EQUAL
- 括号可以用来分组

宏定义与函数
^^^^^^^^^^^^^^

函数与宏只有作用域上存在区别，宏没有作用域的限制。

示例：

::

    function(SIMPLE REQUIRED_ARG)
        message(STATUS "simple arguments: ${REQUIRED_ARG}, followed by ${ARGN}")
        set(${REQUIRED_ARG} "From SIMPLE" PARENT_SCOPE)
    endfuntion()

    simple(This Foo Bar)
    message("Output: ${This}")


输出如下

::
    -- Simple argument: This, followed by Foo;Bar
    Output: From SIMPLE


CMake有一个变量名系统，可以通过cmake_parse_arguments函数来对变量进行命名与解析。

::

    function(COMPLEX)
        cmake_parse_arguments(
                COMPLEX_PREFIX
                "SINGLE;ANOTHER"
                "ONE_VALUE;ALSO_ONE_VALUE"
                "MULTI_VALUES"
                ${ARGN}
            )

    endfunction()

    complex(SINGLE ONE_VALUE value MULTI_VALUES some other values)


在调用这个函数后，会生成以下变量

::
    
    COMPLEX_PREFIX_SINGLE = TRUE
    COMPLEX_PREFIX_ANOTHER = FALSE
    COMPLEX_PREFIX_ONE_VALUE = "value"
    COMPLEX_PREFIX_ALSO_ONE_VALUE = <UNDEFINED>
    COMPLEX_PREFIX_MULTI_VALURES = "some"





Cmake与代码交互
------------------




项目组织
---------

示例：

::

    - project
    - .gitignore
    - README.md
    - LICENCE.md
    - CMakeLists.txt
    - cmake
      - FindSomeLib.cmake
      - something_else.cmake
    - include
      - project
        - lib.hpp
    - src
      - CMakeLists.txt
      - lib.cpp
    - apps
      - CMakeLists.txt
      - app.cpp
    - tests
      - CMakeLists.txt
      - testlib.cpp
    - docs
      - CMakeLists.txt
    - extern
      - googletest
    - scripts
      - helper.py



在Cmake中运行其他程序
-------------------------

配置时运行一条命令
^^^^^^^^^^^^^^^^^^

可以使用excute_progress来运行一条命令并获得他的结果。

下面是一个更新所有git子模块的例子

::

    find_package(Git QUIET)

    if(GIT_FOUND AND EXISTS "${PROJECT_SOURCE_DIR}/.git")
        execute_progress(COMMAND ${GIT_EXECUTABLE} submodule update --init --recursive
                        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
                        RESULT_VARIBLE GIT_SUBMOD_RESULT)
        if(NOT GIT_SUBMOD_RESULT "0")
            message(FATAL_ERROR "git submodule update --init --recursive failed with ${GIT_SUBMOD_RESULT}")
    endif()


在构建时运行一条命令
^^^^^^^^^^^^^^^^^^^^

::

    find_package(PythonInterp REQUIRED)
    add_custom_command(OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/include/Genetated.hpp"
        COMMAND "${PYTHON_EXECUTABLE}" "${CMAKE_CURRENT_BINARY_DIR}/scripts/GenerateHeader.py" --argument
        DEPENDS some_target)

    add_custom_target(generate_header ALL 
                      DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/include/Generated.hpp")


    install(FILES ${CMAKE_CURRENT_BINARY_DIR}/include/Generated.hpp DESTINATION include)


当你在add_custom_target命令中添加ALL关键字，头文件的生成过程会在some_target这些依赖目标完成后自动执行，当你把这个目标作为下一个目标的依赖，你也可以不加ALL关键字
    



示例
-------


















