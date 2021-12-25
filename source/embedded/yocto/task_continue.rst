常见任务 二
============

升级recipes
------------

使用devtool upgrade
^^^^^^^^^^^^^^^^^^^^

要查看所有可用的命令选项，可使用以下帮助命令

::

    devtool upgrade -h

如果在不尝试升级本地版本的情况下查询上游的版本，可以使用以下命令

::

    devtool latest-version recipe_name
    例
    devtool latest-version dropbear
    ...
    ...
    INFO: Current version: 2020.80
    INFO: Latest version: 2020.81

升级recipes可以使用以下命令

::

    devtool upgrade recipe_name -V version
    # 省略版本号则将升级到最新版本
    devtool upgrade dropbear -V 2020.81

然后执行以下命令来重新构建recipes

::

     devtool build dropbear


手动升级recipes
^^^^^^^^^^^^^^^^

手动升级recipes通常需要以下几个步骤:

1) 更改版本: 重命名recipe，如果版本不是recipe名称的一部分，更改recipe内的PV值
2) 如果需要: 更新SRCREV: 如果源代码是从git获取的那就更新SRCREV以指向与新版本匹配的提交哈希
3) 构建软件: 使用bitbake构建recipe


**devshell  pydevshell**

可以通过以下方式启动

::

    bitbake dropbear -c devshell
    bitbake dropbear -c pdevshell

此命令会生成一个带有shell提示的终端，该终端下

1) PATH变量包括交叉工具链
2) pkgconfig变量找到正确的.pc文件 
3) configure命令会查找yocto站点文件和其他必要文件
4) 工作目录也会自动更改为源目录($S)


使用库
--------

下面是bitbake配置文件的一部分，其中可以看到静态库文件是如何定义的

::

		PACKAGE_BEFORE_PN ?= ""
		PACKAGES = "${PN}-dbg ${PN}-staticdev ${PN}-dev ${PN}-doc ${PN}-locale ${PACKAGE_BEFORE_PN} ${PN}"
		PACKAGES_DYNAMIC = "^${PN}-locale-.*"
		FILES = ""

		FILES:${PN} = "${bindir}/* ${sbindir}/* ${libexecdir}/* ${libdir}/lib*${SOLIBS} \
					${sysconfdir} ${sharedstatedir} ${localstatedir} \
					${base_bindir}/* ${base_sbindir}/* \
					${base_libdir}/*${SOLIBS} \
					${base_prefix}/lib/udev/rules.d ${prefix}/lib/udev/rules.d \
					${datadir}/${BPN} ${libdir}/${BPN}/* \
					${datadir}/pixmaps ${datadir}/applications \
					${datadir}/idl ${datadir}/omf ${datadir}/sounds \
					${libdir}/bonobo/servers"

		FILES:${PN}-bin = "${bindir}/* ${sbindir}/*"

		FILES:${PN}-doc = "${docdir} ${mandir} ${infodir} ${datadir}/gtk-doc \
					${datadir}/gnome/help"
		SECTION:${PN}-doc = "doc"

		FILES_SOLIBSDEV ?= "${base_libdir}/lib*${SOLIBSDEV} ${libdir}/lib*${SOLIBSDEV}"
		FILES:${PN}-dev = "${includedir} ${FILES_SOLIBSDEV} ${libdir}/*.la \
						${libdir}/*.o ${libdir}/pkgconfig ${datadir}/pkgconfig \
						${datadir}/aclocal ${base_libdir}/*.o \
						${libdir}/${BPN}/*.la ${base_libdir}/*.la"
		SECTION:${PN}-dev = "devel"
		ALLOW_EMPTY:${PN}-dev = "1"
		RDEPENDS:${PN}-dev = "${PN} (= ${EXTENDPKGV})"

		FILES:${PN}-staticdev = "${libdir}/*.a ${base_libdir}/*.a ${libdir}/${BPN}/*.a"
		SECTION:${PN}-staticdev = "devel"
		RDEPENDS:${PN}-staticdev = "${PN}-dev (= ${EXTENDPKGV})"


multilib允许多个版本的库同时存在

::

	MACHINE = "qemux86-64"
	require conf/multilib.conf
	MULTILIBS = "multilib:lib32"
	DEFAULTTUNE:virtclass-multilib-lib32 = "x86"
	IMAGE_INSTALL:append = "lib32-glib-2.0"


使用wic创建镜像分区
--------------------


wic支持七种命令cp, create, help, list, ls, rm, write

::

	wic -h	
	wic help command

可以使用list命令返回可用wic镜像

::

	  wic list images

	  #该命令输出的images内容，可对应wks_file(kickstart 文件)
	  genericx86                                    Create an EFI disk image for genericx86*
	  edgerouter                                    Create SD card image for Edgerouter
	  beaglebone-yocto                              Create SD card image for Beaglebone
	  efi-bootdisk
	  mkhybridiso                                   Create a hybrid ISO image
	  systemd-bootdisk                              Create an EFI disk image with systemd-boot
	  directdisk                                    Create a 'pcbios' direct disk image
	  qemuriscv                                     Create qcow2 image for RISC-V QEMU machines
	  sdimage-bootpart                              Create SD card image with a boot partition
	  directdisk-multi-rootfs                       Create multi rootfs image using rootfs plugin
	  directdisk-bootloader-config                  Create a 'pcbios' direct disk image with custom bootloader config
	  mkefidisk                                     Create an EFI disk image
	  qemux86-directdisk                            Create a qemu machine 'pcbios' direct disk image
	  directdisk-gpt                                Create a 'pcbios' direct disk image

wic支持两种操作模式，Raw和Cooked


**raw模式**

::

	$ wic create wks_file options ...

	  Where:

		 wks_file:
			An OpenEmbedded kickstart file.  You can provide
			your own custom file or use a file from a set of
			existing files as described by further options.

		 optional arguments:
		   -h, --help            show this help message and exit
		   -o OUTDIR, --outdir OUTDIR
								 name of directory to create image in
		   -e IMAGE_NAME, --image-name IMAGE_NAME
								 name of the image to use the artifacts from e.g. core-
								 image-sato
		   -r ROOTFS_DIR, --rootfs-dir ROOTFS_DIR
								 path to the /rootfs dir to use as the .wks rootfs
								 source
		   -b BOOTIMG_DIR, --bootimg-dir BOOTIMG_DIR
								 path to the dir containing the boot artifacts (e.g.
								 /EFI or /syslinux dirs) to use as the .wks bootimg
								 source
		   -k KERNEL_DIR, --kernel-dir KERNEL_DIR
								 path to the dir containing the kernel to use in the
								 .wks bootimg
		   -n NATIVE_SYSROOT, --native-sysroot NATIVE_SYSROOT
								 path to the native sysroot containing the tools to use
								 to build the image
		   -s, --skip-build-check
								 skip the build check
		   -f, --build-rootfs    build rootfs
		   -c {gzip,bzip2,xz}, --compress-with {gzip,bzip2,xz}
								 compress image with specified compressor
		   -m, --bmap            generate .bmap
		   --no-fstab-update     Do not change fstab file.
		   -v VARS_DIR, --vars VARS_DIR
								 directory with <image>.env files that store bitbake
								 variables
		   -D, --debug           output debug information


**Cooked模式**

::

	$ wic create wks_file -e IMAGE_NAME

	Where:

	   wks_file:
	  	An OpenEmbedded kickstart file.  You can provide
	  	your own custom file or use a file from a set of
	  	existing files provided with the Yocto Project
	  	release.

	   required argument:
	  	-e IMAGE_NAME, --image-name IMAGE_NAME
	  						 name of the image to use the artifacts from e.g. core-
	  						 image-sato


以下是genericx86.wks文件中用于生成image实际分区语言命令

::

	# short-description: Create an EFI disk image for genericx86*
	# long-description: Creates a partitioned EFI disk image for genericx86* machines
	part /boot --source bootimg-efi --sourceparams="loader=grub-efi" --ondisk sda --label msdos --active --align 1024
	part / --source rootfs --ondisk sda --fstype=ext4 --label platform --align 1024 --use-uuid
	part swap --ondisk sda --size 44 --label swap1 --fstype=swap

	bootloader --ptable gpt --timeout=5 --append="rootfstype=ext4 console=ttyS0,115200 console=tty0"


**示例**

cooked模式下运行

::
	
	wic create mkefidisk -e core-image-minimal	
	...
	...
	INFO: Creating image(s)...

	INFO: The new image(s) can be found here:
	  ./mkefidisk-202112241844-sda.direct

	The following build artifacts were used to create the image(s):
	  ROOTFS_DIR:                   /home/yinwg/ywg_workspace/yocto/yocto/build/tmp/work/qemux86_64-poky-linux/core-image-minimal/1.0-r0/rootfs
	  BOOTIMG_DIR:                  /home/yinwg/ywg_workspace/yocto/yocto/build/tmp/work/qemux86_64-poky-linux/core-image-minimal/1.0-r0/recipe-sysroot/usr/share
	  KERNEL_DIR:                   /home/yinwg/ywg_workspace/yocto/yocto/build/tmp/deploy/images/qemux86-64
	  NATIVE_SYSROOT:               /home/yinwg/ywg_workspace/yocto/yocto/build/tmp/work/core2-64-poky-linux/wic-tools/1.0-r0/recipe-sysroot-native

	INFO: The image(s) were created using OE kickstart file:
	  /home/yinwg/ywg_workspace/yocto/yocto/scripts/lib/wic/canned-wks/mkefidisk.wks
	
然后可以使用dd命令或者bmaptool命令将镜像写入存储设备

::

	sudo dd if=./mkefidisk-202112241844-sda.direct of=/dev/sda2 
	oe-run-native bmaptool copy ./mkefidisk-202112241844-sda.direct /dev/sda2

使用修改后的kickstart文件并以原始模式运行

::

    wic create test.wks -o /home/yinwg/yocto/build/test  \
	     --rootfs-dir /home/yinwg/yocto/build/tmp/work/qemux86-poky-linux/core-image-minimal/1.0-r0/rootfs \
		 --bootimg-dir /home/yinwg/yocto/build/tmp/work/qemux86-poky-linux/core-image-minimal/1.0-r0/recipe-sysroot/usr/share \
		 --kernel-dir /home/yinwg/yocto/build/tmp/deploy/images/qemux86 \
		 --native-sysroot /home/yinwg/yocto/build/tmp/work/i586-poky-linux/wic-tools/1.0-r0/recipe-sysroot-native

**使用wic操作image**

1) 列出分区

::

	$ wic ls tmp/deploy/images/qemux86/core-image-minimal-qemux86.wic
	Num     Start        End          Size      Fstype
	 1       1048576     25041919     23993344  fat16
	 2      25165824     72157183     46991360  ext4


2) 检查特定分区

::

	$ wic ls tmp/deploy/images/qemux86/core-image-minimal-qemux86.wic:1
	Volume in drive : is boot
	 Volume Serial Number is E894-1809
	Directory for ::/

	libcom32 c32    186500 2021-10-09  16:06
	libutil  c32     24148 2021-10-09  16:06
	syslinux cfg       220 2021-10-09  16:06
	vesamenu c32     27104 2021-10-09  16:06
	vmlinuz        6904608 2021-10-09  16:06
			5 files           7 142 580 bytes
							 16 582 656 bytes free


3) 删除分区内文件

::

	wic rm tmp/deploy/images/qemux86/core-image-minimal-qemux86.wic:1/vmlinuz

4) 增加分区内文件

::

	$ wic cp poky_sdk/tmp/work/qemux86-poky-linux/linux-yocto/4.12.12+git999-r0/linux-yocto-4.12.12+git999/arch/x86/boot/bzImage \
         poky/build/tmp/deploy/images/qemux86/core-image-minimal-qemux86.wic:1/vmlinuz


文件系统相关
-------------


**只使用systemd**

::

	DISTRO_FEATURES:append = "systemd"
	VIRTUAL-RUNTIME_init_manager = "systemd"

如果要防止sysVinit功能被自动启用，做如下设置

::

	DISTRO_FEATURES_BACKFILL_CONSIDERED = "sysvinit"

这样会删除多余的SysVinit脚本，要从iamge中完全删除initscripts，还需要设置此变量

::

	VIRTUAL-RUNTIME_initscripts = ""

**主image使用systemd，救援image使用sysvinit**

::

	DISTRO_FEATURES:append = " systemd"
	VIRTUAL-RUNTIME_init_manager = "systemd"

**选择设备管理器**

使用静态方法进行设备填充

::

	USE_DEVFS = "0"

如果为定义IMAGE_DEVICE_TABLES变量，则使用默认值 device_table-minimal.txt

::

	IMAGE_DEVICE_TABLES = "device_table-mymachine.txt"


makedevs在创建image期间，该程序会处理填充


**使用devtmpfs和设备管理器**

使用动态方法进行设备填充

::

	USE_DEVFS = "1"

要使用此设置，需要确保在配置内核时CONFIG_DEVTMPFS打开了。如果要更好的控制设备节点可以使用设备管理器如udev或者busybox-mdev

::

	VIRTUAL-RUNTIME_dev_manager = "udev"
	# Some alternative values
	# VIRTUAL-RUNTIME_dev_manager = "busybox-mdev"
	# VIRTUAL-RUNTIME_dev_manager = "systemd"


**创建只读根文件系统**


::

	IMAGE_FEATURES += "read-only-rootfs"
	或
	EXTRA_IMAGE_FEATURES = "read-only-rootfs"







































