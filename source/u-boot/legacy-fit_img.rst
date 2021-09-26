Legacy-uImage & FIT-uImage
=============================

**比较Image、zImage、Legacy uImage、FIT uImage的区别**

1. 内核编译之后会生成两个文件，一个是Image，一个是zImage，其中Image维内核映像文件，而zImage则是Image的压缩文件(gzip压缩)

2. Legacy uImage是uboot专用的映像文件，它是在zImage之前加上一个长度为64字节的头，说明这个内核的版本、加载位置、生成时间、大小等信息。从0x40(64)之后就与zImage完全一样

3. FIT uImage是在lagacy uImage基础上，为了满足Linux Flattened Device Tree(FDT)的标准，而重新改进和定义出来的一种映像文件格式.将kernel fdt ramdisk等镜像打包到一个image file中，并且加上一些需要的信息
   ，uboot只要获得了这个image file就可以得到kernel fdt ramdisk等镜像的具体内容

也就是说uImage有两种类型,这两种类型的格式是不一样的，uboot从这两种uImage中解析出kernel信息的方式也是不一样的

.. note::
    这些信息都是通过mkimage工具生成uImage的时候附加上去的,并不是kernel原生镜像的内容


Legacy-uImage
---------------

**使能需要打开的宏**

::

    CONFIG_IMAGE_FORMAT_LEGACY=y

**如何制作 & 使用**

- 工具mkimage

编译完uboot之后会在uboot的tools目录下编译生成mkimage可执行文件

- 命令

::

    mkimage -A arm -O linux -C none -T kernel -a 0x20008000 -e 0x20008040 -n linux_Image -d zImage uImage
    各参数意义如下
	Usage: mkimage -l image
          -l ==> list image header information
       mkimage [-x] -A arch -O os -T type -C comp -a addr -e ep -n name -d data_file[:data_file...] image
          -A ==> set architecture to 'arch'
          -O ==> set operating system to 'os'
          -T ==> set image type to 'type'
          -C ==> set compression type 'comp'
          -a ==> set load address to 'addr' (hex)
          -e ==> set entry point to 'ep' (hex)
          -n ==> set image name to 'name'
          -d ==> use image data from 'datafile'
          -x ==> set XIP (execute in place)
       mkimage [-D dtc_options] [-f fit-image.its|-f auto|-F] [-b <dtb> [-b <dtb>]] [-i <ramdisk.cpio.gz>] fit-image
           <dtb> file is used with -f auto, it may occur multiple times.
          -D => set all options for device tree compiler
          -f => input filename for FIT source
          -i => input filename for ramdisk file


- 使用

将生成的legacy-uimage下载到参数中指定的load address中，使用bootm命令跳转到kernel中.但是注意，如果使用legacy-uimage后面还需跟上文件系统的ram地址以及dtb的ram地址

格式如下

::

	bootm legacy-uImage加载地址 ramdisk加载地址 dtb加载地址


- 格式头说明

uboot中用image_header来表示legacy-uImage的头部

::

	/*
	 * Legacy format image header,
	 * all data in network byte order (aka natural aka bigendian).
	 */
	typedef struct image_header {
		__be32		ih_magic;	/* Image Header Magic Number	*/	//幻数头，用来校验是否是一个legacy-uimage, 0x27051956
		__be32		ih_hcrc;	/* Image Header CRC Checksum	*/	//头部的crc校验
		__be32		ih_time;	/* Image Creation Timestamp	*/		//镜像创建的时间戳
		__be32		ih_size;	/* Image Data Size		*/			//镜像大小
		__be32		ih_load;	/* Data	 Load  Address		*/		//加载地址
		__be32		ih_ep;		/* Entry Point Address		*/		//入口地址
		__be32		ih_dcrc;	/* Image Data CRC Checksum	*/		//镜像的crc
		uint8_t		ih_os;		/* Operating System		*/			//操作系统类型
		uint8_t		ih_arch;	/* CPU architecture		*/			//cpu体系架构
		uint8_t		ih_type;	/* Image Type			*/			//镜像类型
		uint8_t		ih_comp;	/* Compression Type		*/			//压缩类型
		uint8_t		ih_name[IH_NMLEN];	/* Image Name		*/		//镜像名
	} image_header_t;


FIT-uImage
-----------

**原理说明**

flattened image tree,类似于FDT的一种实现机制，其通过一定语法格式将一些需要使用到的镜像(如kernel、dtb以及文件系统)组合到一起生成一个image文件，其主要使用四个组件

- its文件
  image source file，类似于dts文件，负责描述要生成的image的信息，需要自行构造

- itb文件
  最终得到的image文件，类似于dtb文件，也就是uboot可以直接对其进行识别和解析的fit-uimage

- mkimage
	mkimage则负责dtc的角色，用于通过解析its文件，获取对应的镜像，最终生成一个uboot可以直接进行识别和解析的itb文件

- image data file
  实际使用到的镜像文件

**使能需要打开的宏**

::

	CONFIG_FIT=y

**制作 & 使用**

1) its文件制作

mkimage是根据its文件中的描述来打包镜像生成itb文件

简单的示例如下

::

    /dts-v1/

    / {
        description = "u-boot uimage source file";
        #address-cells = <1>;

        images {
            kernel@j3 {
                description = "linux kernel for j3";
                data = /incbin/(/home/yinwg/build/out/linux/arch/arm64/boot/zImage);
                type = "kernel";
                arch = "arm64";
                os = "linux";
                compression = "none";
                load = <0x10000000>;
                entry = <0x10000000>;
            };

            fdt@j3 {
                description = "device tree for j3";
                data = /incbin/(/home/yinwg/build/out/linux/arch/arm64/boot/dts/holo_j3.dtb);
                type = "flat_dt";
                arch = "arm64";
                compress = "none";
                
            };
        };

        confifurations {
            default = "conf@j3";
            conf@j3 {
                description = "boot linux kernel";
                kernel = "kernel@j3";
                fdt = "fdt@j3";
            };
        };
    };


.. note::
	可以有多个kernel节点或者fdt节点，可以有多种configurations来对kernel fdt ramdisk来进行组合，使用fit-uimage可以兼容多种板子，而无需重新编译烧写

2) 生成fit-uimage

生成的命令相对legacy-uimage较为简单，因为信息都在its文件里面描述了

::

	mkimage -f its文件 要生成的itb文件

3) 使用

将生成的fit-uimage下载到参数中指定的load address中，使用bootm “实际load address”命令启动kernel

image source file语法
----------------------

image source file的语法和device tree source file完全一样，只不过自定义了一些特有的节点，包括images configurations等

1) image节点

指定要包含的二进制文件，可以指定多种类型的多个文件，每个文件都是images下的一个子node.可以包含以下关键字

- description: 描述，可以随便写
- data:二进制文件路径
- type:二进制文件的类型，"kernel" "ramdisk" "flat_dt"
- arch:平台类型
- os:操作系统类型
- compression:二机制文件的压缩格式
- load:二进制文件的加载位置
- entry:二进制文件的入口地址，一般kernel image需要提供，u-boot会跳到该地址上运行
- hash:使用的数据校验算法

2) configurations

可以将不同类型的二进制文件，根据不同的场景组合起来,形成一个个的配置项，u-boot在boot的时候以配置项为单位加载执行,这样就可以根据不同的场景方便的选择不同的配置


