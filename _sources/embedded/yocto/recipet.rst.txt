recipet语法
============

详细语法规范可参考 https://docs.yoctoproject.org/bitbake/bitbake-user-manual/bitbake-user-manual-metadata.html

**变量赋值和操作**

变量赋值允许将值分配给变量，赋值可以是静态文件，也可以包括其他变量的内容，除了赋值之外还支持追加和前置操作

::

    S = "${WORKDIR}/postfix-${PV}"
    CFLAGS += "-DNO_ASM"
    SRC_URI:append = " file://fixup.patch"


**函数**

函数提供了一些要执行的操作，通常使用函数来覆盖任务h函数的默认实现或补充默认函数

::

	do_install () {
		autotools_do_install
		install -d ${D}${base_bindir}
		mv ${D}${bindir}/sed ${D}${base_bindir}/sed
		rmdir ${D}${bindir}/
	}

**关键字**

bitbake recipet仅使用几个关键字，可以使用关键字包含常用函数(inherit)，从其他文件(include和require)加载recipet，并将变量导出到环境(export)

::

	export POSTCONF = "${STAGING_BINDIR}/postconf"
	inherit autoconf
	require otherfile.inc

**注释**

任何以(#)开头的行都被视为注释行

::

	# This is a comment


**行继续(\)**

使用反斜杠(\)字符将语句拆分为多行, 斜杠后面不能有任何字符

**使用变量**

::
	
	SRC_URI = "${SOURCEFORGE_MIRROR}/libpng/zlib-${PV}.tar.gz"


**引用赋值**

::

	VAR1 = "${OTHERVAR}"
	VAR2 = "The version is ${PV}"

**条件赋值(?=)**

条件赋值用于为变量赋值，但仅限于当前变量未赋值时。

::

	VAR1 ?= "new value"     #VAR1当前为空，则设置"new value"

::


**附加(+=)**

::

	SRC_URI += "file://fix-makefile.patch"

**前置(=+)**

这种操作符号可将值前置到现有变量

**append(:append)**

使用append运算符将值附加到现有变量,添加到开头

::

    SRC_URI:append = " file://fix-makefile.patch"
    SRC_URI:append:sh4 = " file://fix-makefile.patch"

**prepending(:prepend)**

使用append运算符将值附加到现有变量,添加到末尾


**使用python进行复杂操作**

::

    SRC_URI = "ftp://ftp.info-zip.org/pub/infozip/src/zip${@d.getVar('PV',1).replace('.', '')}.tgz"


