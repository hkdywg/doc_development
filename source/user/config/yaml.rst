yaml笔记
============

yaml标准文档 https://yaml.org/spec/1.2.2/

YAML是 ``YAML Ain't Markup Lanuage`` 的缩略词

- YAML是一种非常简单的基于文本的人类可读的语言内，用于数据交换

- YAML不是一种编程语言，它主要用于存储配置信息

- YAML减少了JSON和XML文件中大部分"噪音"格式，如引号，方括号，大括号

- YAML区分大小写，不允许使用制表符TAB键，遵循严格缩进


基础语法
------------

键对值
^^^^^^^

::

    <key>: <value>

其中<key>代表名称，<value>代表数据，之间用分割: (空格是必须的)

::

    name: hkdywg
    age: 30

对应的JSON描述为:

::

    {
        "name": "hkdywg"
        "age": 30
    }

列表
^^^^^^

列表通过在其项目前加上 ``-`` (连字符)来表示

::

    number:
        - one
        - two
        - three

这个列表是包含在对象里面的，如果我们想要如下JSON列表的表述呢

::

    [
        {
            "name": "hkdywg"
            "age": 30
        },
        {
            "name": "tester"
            "age": 18
        }
    ]

对应的YAML可以这样写

::

    - 

      name: hkdywg
      age: 30

    -

      name: tester
      age: 18

注释
^^^^^^

::

    # 这是一行注释

.. note::
    YAML不支持块或者多行注释


YAML中的类型
--------------

YAML支持的数据类型列表如下:

- Boolean

- Numbers

- Strings

- Arrays

- Maps

- Null

- Dates

- Timestamp

::

    dataType:
      string: "YAML"
      interger: 123
      float: 12.345
      boolean: true

.. note::
    根据YAML 1.2规范文档，"yes"和"no"不再被解释为布尔值

字符串(string)
^^^^^^^^^^^^^^^

字符串可以加单引号或双引号或没有引号

::

    quoted:
        - 'single quoted string'
        - "double quoted strings"
        - without quoted string


单行/多行文本
^^^^^^^^^^^^^^^

涉及字符串还有一个问题，当字符串比较多的时候，为了更好的展示，可以选择单行/多行文本展示

::

    # Multiline strings start with |
    execute: |
        sudo apt -y install libcurl
        sudo apt install -y tftp-hpa tftpd-hpa
        sudo sed -i 's/TFTP_DIRECTORY="\/var\/lib\/tftpboot"/TFTP_DIRECTORY="\/home\/tftp"/' /etc/de

    # Single strings start with >
    single-line-string: >
        this
        should
        be
        one
        line

.. note::
    当使用 ``>`` 字符而不是 ``|`` ,每一个新行都将被解释为一个空格

数值(Number)
^^^^^^^^^^^^^^

数值有整数，小数，整数，负数，正无穷大，NaN(not a number)，科学计数法，进制表示

::

    interger: 12
    decimal: 0.5
    positive: +12
    negative: -12
    positive infinity: .inf
    negative infinity: -.inf
    not a number: .nan
    number: 687_456
    scientific counting method: 2.3e4
    binary: 0b101010

空值(null)
^^^^^^^^^^^

YAML声明空值有以下几种方法

::

    manager: null
    blank:
    tilde: ~
    title: null
    ~: null key

时间戳(timestamp)
^^^^^^^^^^^^^^^^^^

时间戳表示单个时间点，它使用符号形式ISO8601．如果未添加时区，则假定该时区为UTC．要描述日期格式，可以省略时间部分

::

    time: 2023-03-17T01:13:58:35.02Z
    timestamp: 2023-03-17T01:13:58:35.02 +05:30
    datetime: 2023-03-17T01:13:58:35.02+05:30
    notimezone: 2023-03-17T01:13:58:35.02
    date: 2023-03-17


显示类型
^^^^^^^^^

默认情况下，YAML会自动推断数据类型，必要时也可以使用标签(tags)显示指定类型，比如整数类型两个英文感叹号 ``!!`` 再加上int就变成了一个整数tag　

::

    should-be-int: !!int 3.2
    should-be-string: !!str 30.25
    should-be-boolean: !!bool true


==================  ================================
 tags                   description
------------------  --------------------------------
 !!int                      interger
 !!float                    float
 !!str                      string
 !!bool                     boolean
 !!null                     null
 !!seq                      array
 !!map                      map
 !!set                      set
 !!omap                     order map
 !!pairs                    pairs
==================  ================================


高级功能
-----------

代码复用
^^^^^^^^^

任何代码都讲究个复用,最基本的就是定义变量，但YAML无法定义变量，YAML通过Node Anchors来解决

::

    #复用Value的值
    First occurrence: &anchor Value
    Second occurrence: *anchor

通过 ``&`` 标记一个节点，使用 ``*`` 字符引用它，从而达到复用

块样式和流样式
^^^^^^^^^^^^^^^^

**块样式**

在文档块样式使用块用于结构化文档，它更容易阅读，但不那么紧凑

::

    color:
      - red
      - grene
      - blue

**流样式**

YAML有一种称为flow style的替代语法，它允许在不依赖缩进的情况下内联编写序列和映射，分别使用一对方括号和大括号

::

    color: [red, blue]
    #或
    - { name: "hkdywg", age: 30 }



工具
------

- 校验YAML语法的正确性

  - `YAML Lint <http://www.yamllint.com/>`_
  - `YAML Validator <https://codebeautify.org/yaml-validator>`_

- 美化

  - `YAML Beautifier <https://codebeautify.org/yaml-beautifier>`_

- 转换

  - `YAML Converter(转换YAML到JSON, XML, CSV) <https://codebeautify.org/yaml-to-json-xml-csv>`_

  - `Online YAML Parser(输出YAML到JSON和PYTHON) <http://yaml-online-parser.appspot.com/>`_

  - `YAML to PDF Table Converter(YAML转换为PDF Table) <https://www.beautifyconverter.com/yaml-to-pdf-converter.php>`_

  - `js-yaml(YAML输出到JS) <https://nodeca.github.io/js-yaml/>`_









