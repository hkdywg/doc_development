bitbake 总结
==============

bitbake命令
------------

::

    $ bitbake -h
	Usage: bitbake [options] [recipename/target recipe:do_task ...]

    Executes the specified task (default is 'build') for a given set of target recipes (.bb files).
    It is assumed there is a conf/bblayers.conf available in cwd or in BBPATH which
    will provide the layer, BBFILES and other configuration information.

	Options:
	  --version             show program's version number and exit
	  -h, --help            show this help message and exit
	  -b BUILDFILE, --buildfile=BUILDFILE
							Execute tasks from a specific .bb recipe directly.
							WARNING: Does not handle any dependencies from other
							recipes.
	  -k, --continue        Continue as much as possible after an error. While the
							target that failed and anything depending on it cannot
							be built, as much as possible will be built before
							stopping.
	  -f, --force           Force the specified targets/task to run (invalidating
							any existing stamp file).
	  -c CMD, --cmd=CMD     Specify the task to execute. The exact options
							available depend on the metadata. Some examples might
							be 'compile' or 'populate_sysroot' or 'listtasks' may
							give a list of the tasks available.
	  -C INVALIDATE_STAMP, --clear-stamp=INVALIDATE_STAMP
							Invalidate the stamp for the specified task such as
							'compile' and then run the default task for the
							specified target(s).
	  -r PREFILE, --read=PREFILE
							Read the specified file before bitbake.conf.
	  -R POSTFILE, --postread=POSTFILE
							Read the specified file after bitbake.conf.
	  -v, --verbose         Enable tracing of shell tasks (with 'set -x'). Also
							print bb.note(...) messages to stdout (in addition to
							writing them to ${T}/log.do_&lt;task&gt;).
	  -D, --debug           Increase the debug level. You can specify this more
							than once. -D sets the debug level to 1, where only
							bb.debug(1, ...) messages are printed to stdout; -DD
							sets the debug level to 2, where both bb.debug(1, ...)
							and bb.debug(2, ...) messages are printed; etc.
							Without -D, no debug messages are printed. Note that
							-D only affects output to stdout. All debug messages
							are written to ${T}/log.do_taskname, regardless of the
							debug level.
	  -q, --quiet           Output less log message data to the terminal. You can
							specify this more than once.
	  -n, --dry-run         Don't execute, just go through the motions.
	  -S SIGNATURE_HANDLER, --dump-signatures=SIGNATURE_HANDLER
							Dump out the signature construction information, with
							no task execution. The SIGNATURE_HANDLER parameter is
							passed to the handler. Two common values are none and
							printdiff but the handler may define more/less. none
							means only dump the signature, printdiff means compare
							the dumped signature with the cached one.
	  -p, --parse-only      Quit after parsing the BB recipes.
	  -s, --show-versions   Show current and preferred versions of all recipes.
	  -e, --environment     Show the global or per-recipe environment complete
							with information about where variables were
							set/changed.
	  -g, --graphviz        Save dependency tree information for the specified
							targets in the dot syntax.
	  -I EXTRA_ASSUME_PROVIDED, --ignore-deps=EXTRA_ASSUME_PROVIDED
							Assume these dependencies don't exist and are already
							provided (equivalent to ASSUME_PROVIDED). Useful to
							make dependency graphs more appealing
	  -l DEBUG_DOMAINS, --log-domains=DEBUG_DOMAINS
							Show debug logging for the specified logging domains
	  -P, --profile         Profile the command and save reports.
	  -u UI, --ui=UI        The user interface to use (knotty, ncurses, taskexp or
							teamcity - default knotty).
	  --token=XMLRPCTOKEN   Specify the connection token to be used when
							connecting to a remote server.
	  --revisions-changed   Set the exit code depending on whether upstream
							floating revisions have changed or not.
	  --server-only         Run bitbake without a UI, only starting a server
							(cooker) process.
	  -B BIND, --bind=BIND  The name/address for the bitbake xmlrpc server to bind
							to.
	  -T SERVER_TIMEOUT, --idle-timeout=SERVER_TIMEOUT
							Set timeout to unload bitbake server due to
							inactivity, set to -1 means no unload, default:
							Environment variable BB_SERVER_TIMEOUT.
	  --no-setscene         Do not run any setscene tasks. sstate will be ignored
							and everything needed, built.
	  --skip-setscene       Skip setscene tasks if they would be executed. Tasks
							previously restored from sstate will be kept, unlike
							--no-setscene
	  --setscene-only       Only run setscene tasks, don't run any real tasks.
	  --remote-server=REMOTE_SERVER
							Connect to the specified server.
	  -m, --kill-server     Terminate any running bitbake server.
	  --observe-only        Connect to a server as an observing-only client.
	  --status-only         Check the status of the remote bitbake server.
	  -w WRITEEVENTLOG, --write-log=WRITEEVENTLOG
							Writes the event log of the build to a bitbake event
							json file. Use '' (empty string) to assign the name
							automatically.
	  --runall=RUNALL       Run the specified task for any recipe in the taskgraph
							of the specified target (even if it wouldn't otherwise
							have run).
	  --runonly=RUNONLY     Run only the specified task within the taskgraph of
							the specified targets (and any task dependencies those
							tasks may have).


示例
^^^^^

**执行单个任务**

::

	bitbake -b dropbear_2020.81.bb

在dropbear_2020.81.bb 上运行清理任务


::

	bitbake -b dropbear_2020.81.bb -c clean


.. note::
	-b选项明确指出不处理recipe的依赖性


**针对一组recipe执行任务**

::

	bitbake dropbear 	#这样会同时处理其依赖项
	bitbake -c clean dropbear
	bitbake apt:do_fetch dropbear:do_compile   #执行不同recipe的不同任务


**生成依赖**

::

	bitbake -g dropbear
	bitbake -g -I virtual/kernel -I eglibc dropbear

执行命令后会在当前路径下生成两个文件

1) task-depends.dot: 显示任务之间的依赖，这些依赖项与bitbake的内部任务执行列表相匹配
2) pn-buildlist: 显示要构建的目标的简单列表


bitbake运行机制
----------------

解析基础配置元数据
^^^^^^^^^^^^^^^^^^

bitbake 做的第一件事就是解析基本配置元数据，基本配置元数据由bblayers.conf文件组成，用于确定bitbake需要识别那些layer。

在解析配置文件之前，bitbake会检查某些变量:

1) BB_ENV_WHITELIST
2) BB_ENV_EXTRAWHITE
3) BB_PRESERVE_ENV
4) BB_ORIGENV
5) BITBAKE_UI

前四个变量与bitbake在执行任务期间如何处理shell环境变量有关,默认情况下bitbake会清除环境变量并提供对shell执行环境的严格控制.通过使用前四个变量，可以控制
bitbake在执行任务期间允许在shell中使用的环境变量

基本配置元数据是全局的，因此会影响所有执行的recipe和task

解析配置文件后，bitbake使用其基本的继承机制，即通过类文件，继承一些标准类。当遇到负责获取该类的继承指令时，bitbake会解析该类。base.bbclass文件始终包含在内。

使用以下命令可以获取执行环境中使用的配置和类文件

::

	bitbake -e > mybb.log



定位和解析recipe
^^^^^^^^^^^^^^^^^^^


在配置阶段，bitbake将设置BBFILES, bitbake使用它来构建要解析的recipe列表。一种常见的约定时使用recipe文件名来定义元数据片段

::

	PN = "${@bb.parse.vars_from_file(d.getVar('FILE', False),d)[0] or 'defaultpkgname'}"
	PV = "${@bb.parse.vars_from_file(d.getVar('FILE', False),d)[1] or '1.0'}"

比如名为“something_1.2.3.bb”的配方会将PN设置 为“something”，将PV 设置为“1.2.3”。

当一个recipe解析完成时，bitbake有一个recipe定义的任务列表和一组由键和值组成的数据以及关于任务的依赖信息。


语法
-----

变量
^^^^^^

"="运算符不会立即扩展右侧的变量引用, 

::

	A = "${B} baz"
	B = "${C} bar"
	C = "foo"
	*At this point, ${A} equals "foo bar baz"*
	C = "qux"
	*At this point, ${A} equals "qux bar baz"*
	B = "norf"
	*At this point, ${A} equals "norf baz"*

":=" 则是立即变量扩展

::

	T = "123"
	A := "test ${T}"
	T = "456"
	B := "${T} ${C}"
	C = "cval"
	C := "${C}append"

A包含“test 123”，即使T的最终值为“456”。

+=和=+m 这两个运算符在当前值和前置或附加值之间插入一个空格

::

	B = "bval"
	B += "additionaldata"
	C = "cval"
	C =+ "test"

变量B包含“bval additionaldata”并C包含“test cval”。


.=和=不插入空格

::

	B = "bval"
	B .= "additionaldata"
	C = "cval"
	C =. "test"

变量B包含“bvaladditionaldata”并C包含“testcval”。

append和prepend运算符，不插入空格。

::

	B = "bval"
	B:append = " additional data"
	C = "cval"
	C:prepend = "additional data "
	D = "dval"
	D:append = "additional data"

变量B为"baval additional data", C变量为"additional data cval"

remove

::

	FOO = "123 456 789 123456 123 456 123 456"
	FOO:remove = "123"
	FOO:remove = "456"
	FOO2 = " abc def ghi abcdef abc def abc def def"
	FOO2:remove = "\
		def \
		abc \
		ghi \
		"

变量FOO为"789 123456", FOO2为"abcdef"

.. note::
	+=和:append不能一起使用

变量标志是bitbake对变量属性的实现，这是一种将额外信息标记到变量上的方法。

::

	CACHE[doc] = "The directory holding the cache of the metadata."

使用内联python变量扩展来设置变量

::

	DATA = "${@time.strftime('%Y%m%d',time.gtime())}"	#将DATA变量设置为当前日期
	#从bitbake的内部数据字典中提取变量的值
	PN = "${@bb.parse.vars_from_file(d.getVar('FILE', False),d)[0] or 'defaultpkgname'}"
	PV = "${@bb.parse.vars_from_file(d.getVar('FILE', False),d)[1] or '1.0'}"


unset关键字可以删除变量或变量标志

::

	unset DATA
	unset do_fetch[noexec]


指定bitbake的路径名时，不能使用"~"作为主目录的快捷方式。

export关键字将变量导出到运行任务的环境中

::

	export ENV_VARIABLE
	ENV_VARIABLE = "value from the environment"

	do_foo() {
		bbplain "$ENV_VARIABLE"
	}


共享
-----

bitbake允许通过包含文件(.inc)和类文件(.bbclass)共享元数据。bitbake包含include，inherit，INHERIT和require指令来进行元数据共享。bitbake使用BBPATH变量来定位所需的inc和class文件，
bitbake在当前目录中搜索include和require指令。为了让bitbake找到对应的文件，需要位于BBPATH的classes子目录中

inherit指令来继承类(.bbclass)功能，在inherit语句之后recipe可以使用继承类的任何值和函数. 与include或者require指令相比，inherit指令的一个优点是可以有条件的继承类文件


::

	inherit autotools	#在BBPATH目录中搜索classes/autotools.bbclass
	INHERIT += "autotools pkgconfig"
	include test_defs.inc
	require foo.inc


.. note::
	当找不到文件时，include不会产生错误，require会生成错误


功能
-----

bitbake支持以下类型的函数:

1) shell函数：用shell脚本编写并直接作为函数
2) bitbake风格的python函数: 用python编写并由bitbake使用
3) python函数: 用python编写并由python执行的函数
4) 匿名python函数: 在解析过程中自动执行的python函数

shell函数
^^^^^^^^^^^

::

	do_foo() {
		bbplain first
		fn
	}

	fn:prepend() {
		bbplain second
	}

	fn() {
		bbplain third
	}

	do_foo:append() {
		bbplain fourth
	}

运行do_foo打印以下内容

::

	recipename do_foo: first
	recipename do_foo: second
	recipename do_foo: third
	recipename do_foo: fourth


bitbake风格的python函数
^^^^^^^^^^^^^^^^^^^^^^^^^

::

	python some_python_function () {
		d.setVar("TEXT", "Hello World")
		print d.getVar("TEXT")
	}

python的"bb"和"os"模块已经导入，数据存储("d")是一个全局变量，并且始终自动可用


python函数
^^^^^^^^^^^^

::

	def get_depends(d):
		if d.getVar('SOMECONDITION'):
			return "dependencywithcond"
		else:
			return "dependency"

	SOMECONDITION = "1"
	DEPENDS = "${@get_depends(d)}"

DEPENDS变量会赋值为dependencywithcond

bitbake风格的函数和python函数的区别

1) 只有bitbake风格的python函数可以是tasks
2) Overrides and override-style运算符只能应用于bitbake风格的python函数
3) 只有常规的python函数可以接收参数和返回值
4) 可变标志，例如[dirs] [cleandirs]和[lockfiles]可以在bitbake风格的python函数可以使用
5) bitbake风格的python函数生成一个单独的${T}/run.函数名.pid脚本，该脚本被执行以运行该函数
6) bitbake风格的python函数通常是任务，由bitbake直接调用，也可以使用该bb.build.exec_func()函数从python代码中手动调用


任务
-----

将函数提升为任务
^^^^^^^^^^^^^^^^^^

::

	python do_printdate () {
		import time
		print time.strftime('%Y%m%d', time.gmtime())
	}
	addtask printdate after do_fetch before do_build

addtask第一个参数是要提升为任务的函数的名称，如果名称不易"do\_"开头，则隐式添加"do\_"，此例中do_printdata依赖do_fetch，do_build依赖do_printdata


删除任务
^^^^^^^^

::

	deltask printdata

使用deltask命令删除任务并该任务具有依赖关系，则不会重新连接依赖关系,如果希望依赖项保持完整，则使用[noexec] varflag禁用任务,而不是删除它

::
	
	do_b[noexec] = "1"


**变量标志**

变量标志(varflags)有助于控制任务的功能和依赖项，bitbake使用以下命令形式将varflags读写和写入数据存储

::

	variable = d.getVarFlags("variable")
	self.d.setVarFlags("FOO",{"func": True})


bitbake有一组已定义的varflags可用于recipe和class，任务支持许多控制任务各种功能的标志：

1) [cleandirs]: 应在任务运行之前创建的空目录，已存在的目录将被删除并重新创建以清空他们
2) [depends]: 控制任务间的依赖关系
3) [deptask]: 控制任务构建时的依赖关系
4) [dirs]: 应该在任务运行之前创建的目录
5) [lockfiles]: 指定在任务执行时要锁定的一个或多个锁定文件，只有一个任务可以持有一个锁定文件，任何试图锁定一个已经锁定的文件的任务都会阻塞。可以使用此变量标志类实现互斥
6) [noexec]: 设置为"1"时，将任务标记为空，不需要执行。
7) [nostamp]: 当设置为"1"时，告诉bitbake不为任务生成stamp文件，这意味着该任务应该始终被执行
8) [number_threads]: 在执行期间将任务限制为特定数量的并发线程
9) [postfuncs]: 任务完成后调用的函数列表
10) [prefuncs]: 任务执行之前调用的函数列表
11) [rdepends]: 控制任务间运行时依赖关系
12) [rdeptask]: 控制任务运行时依赖性
13) [recideptask]: 
14) [recrdeptask]: 控制任务递归运行时依赖项
15) [stamp-extra-info]: 附加到任务的stamp信息
16) [umask]: 用于运行任务的umask
17) [vardeps]: 指定一个空格分隔的附加变量列表，以计算其签名的目的添加到变量的依赖项中。向此列表添加变量很有用，例如，当函数以不允许 BitBake 自动确定引用变量的方式引用变量时。
18) [vardepsexclude]: 指定一个以空格分隔的变量列表，为了计算其签名，应该从变量的依赖项中排除这些变量。
19) [vardepvalue]: 如果设置，则指示 BitBake 在计算变量签名时忽略变量的实际值而使用指定的值。
20) [vardepvalueexclude]: 指定在计算变量签名时要从变量值中排除的以管道分隔的字符串列表。

依赖
-----


构建依赖
^^^^^^^^^^

bitbake使用DEPENDS变量来管理构建时依赖项，[deptask]表示DEPENDS中列出的每个项目的任务必须在该任务执行之前完成

::

	do_configure[deptask] = "do_populate_sysroot"


运行时依赖
^^^^^^^^^^^^

bitabke使用PACKAGES、RDEPENDS和RRECOMMENDS变量来管理运行时依赖项。[rdeptask]可用于表示运行时依赖任务

::

	do_package_qa[rdeptask] = "do_packagedata"

递归依赖
^^^^^^^^^

bitbake使用该[recrdeptask]标志来管理递归任务依赖项，

::

	do_rootfs[recrdeptask] += "do_packagedata"


任务间依赖
^^^^^^^^^^^

bitbake 使用[depends]来管理任务间依赖关系

::

	do_patch[depends] = "quilt-native:do_populate_sysroot"


**访问数据的函数**

===============================================	=============================================================================================================================================================
		operation 										Description
----------------------------------------------- -------------------------------------------------------------------------------------------------------------------------------------------------------------
 d.getVar("X", expand)                           返回变量"X"的值，如果变量X不存在返回None
 d.setVar("X", "value")                          将变量X设置为value
 d.appendVar("X", "value")                       将value添加到变量X的末尾
 d.prependVar("X", "value")                      将value添加到变量X的开头
 d.delVar("X")                                   删除X
 d.renameVar("X", "Y")                           将变量X重命名为Y
 d.getVarFlag("X", flag, expand)                 返回变量X命名标志值
 d.setVarFlag("X", flag, "value")
 d.appendVarFlag("X", flag, "value")             将value附加到变量X的命名标志上
 d.prependVarFlag("X", flag, "value")
 d.delVarFlag("X", flag)                         删除变量X的命名标志
 d.setVarFlags("X", flagsdict)                   设置flagsdict() 参数中指定的标志。setVarFlags不清除以前的标志。将此操作视为addVarFlags.
 d.getVarFlags("X")                              返回flagsdict变量“X”的标志之一。如果变量“X”不存在，则返回“None”。
 d.delVarFlags("X")                              删除变量“X”的所有标志。如果变量“X”不存在，则什么也不做。
 d.expand(expression)                            扩展指定字符串表达式中的变量引用。对不存在的变量的引用保持原样。例如，如果变量“X”不存在，则扩展为文字字符串“foo ${X}”。d.expand("foo ${X}")
===============================================	=============================================================================================================================================================

代码获取
----------

local file
^^^^^^^^^^^

::

    SRC_URI = "file://relativefile.patch"
    SRC_URI = "file:///Users/ich/very_important_software"


http/ftp wget
^^^^^^^^^^^^^^^

::

    SRC_URI = "http://oe.handhelds.org/not_there.aac"
    SRC_URI = "ftp://oe.handhelds.org/not_there_as_well.aac"
    SRC_URI = "ftp://you@oe.handhelds.org/home/you/secret.plan"


cvs
^^^^

::

    SRC_URI = "cvs://CVSROOT;module=mymodule;tag=some-version;method=ext"
    SRC_URI = "cvs://CVSROOT;module=mymodule;date=20060126;localdir=usethat"


================   ===================================================================================================================================================
 参数                      描述
----------------   ---------------------------------------------------------------------------------------------------------------------------------------------------
 method              与cvs服务器通信的协议，
 module              指定要检出的模块，必须提供此参数
 tag                 指定cvs tag
 date                指定日期
 localdir            用于重命名模块
 rsh                 与method结合使用
 scmdata             当设置为keep时，使用cvs元数据保存在fetcher创建的tarball中
 fullpath            控制结果检出是在模块级别（默认情况下）还是在更深的路径中。
 norecurse           使fetcher只检出指定的目录，而不会递归到任何子目录
 port                与cvs服务器连接的端口
================   ===================================================================================================================================================

svn
^^^^^

::

    SRC_URI = "svn://myrepos/proj1;module=vip;protocol=http;rev=667"
    SRC_URI = "svn://myrepos/proj1;module=opie;protocol=svn+ssh"
    SRC_URI = "svn://myrepos/proj1;module=trunk;protocol=http;path_spec=${MY_DIR}/proj1"


================   ===================================================================================================================================================
 参数                      描述
----------------   ---------------------------------------------------------------------------------------------------------------------------------------------------
 module             要检出的svn模块的名称，必须提供此参数
 path_spec          用于检出指定svn模块的特定目录
 protocal           要使用的协议，默认为"svn"
 rev                要检出的源代码的修订版本
 scmdata            当设置为keep时，使.svn目录在编译时可用，默认情况下这些目录被删除
 ssh                当protocal设置为svn+ssh时使用的可选参数
 transportuser      需要时，设置传输的用户名
================   ===================================================================================================================================================


git
^^^^^^

::

    SRC_URI = "git://git.oe.handhelds.org/git/vip.git;tag=version-1"
    SRC_URI = "git://git.oe.handhelds.org/git/vip.git;protocol=http"

================   ===================================================================================================================================================
 参数                      描述
----------------   ---------------------------------------------------------------------------------------------------------------------------------------------------
 protocal           用于获取文件的协议，可以是http、https、ssh和rsync
 nocheckout         设置为1时，告诉fetcher在解包时不检出源代码
 rebaseable         表示上游的git仓库可以rebase
 nobranch           当设置为1时，告诉fetcher不检查分支的SHA验证
 bareclone          告诉fetcher将一个裸克隆克隆到目标目录中，而不检查工作树
 branch             要clone的git分支
 rev                要检出的版本号
 tag                指定检出代码的标签
 subpath            设定检出文件的子目录，默认为全部检出
 destsuffix         设定检出代码的存储路径
================   ===================================================================================================================================================


repo
^^^^^

::

    SRC_URI = "repo://REPOROOT;protocol=git;branch=some_branch;manifest=my_manifest.xml"
    SRC_URI = "repo://REPOROOT;protocol=file;branch=some_branch;manifest=my_manifest.xml"







