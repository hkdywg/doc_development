MIPI CSI传输协议解析
======================


* :download:`mipi_stand_protocol.pdf<res/MIPI_Alliance_Specification_for_Camera_S.pdf>` 

MIPI概述
-----------

**传输模式**

LP(Low-Power)模式: 用于传输控制信号,最高速率10MHZ

HS(High-Speed)模式: 用于高速传输素据,速率范围[80M-1.5Gbps] per lane

传输的最小单元为1字节,采用小端的方式即LSB first, MSB last

**Lane States**

LP mode有四种状态: LP00, LP01, LP10, LP11

HS mode有两种状态: HS-0, HS-1


**MIPI CLK 传输时序**

mipi csi clk存在两种工作模式,一种是连续时钟模式,传输过程中不会切换LP状态,另一种是非连续时钟信号模式,每传输一帧图像,帧blanking时会切换为LP状态

时序图如下

.. image::
    res/clk_transfer_timing.png

从时序图可以看到,clk lane会有一个LP11--->LP01--->LP00的时序,从而进入HS模式

如果camera sensor支持非连续时钟模式,建议配置为非连续时钟模式

**MIPI DATA 传输时序**

在数据线上由3种可能的操作模式: Escap mode, High-Speed(Burst) mode, Control mode

- Escap mode

进入时序: LP11-->LP10-->LP00-->LP01-->LP00

退出时序: LP10-->LP11

- High-Speed mode

进入时序：LP11-->P01-->LP00-->SoT(0001_1101)

退出时序：EoT-->P11

.. image::
    res/data_transfer_timing.png

- Turnaround

进入时序：LP11-->LP10-->LP00-->LP10-->LP00

退出时序：LP00-->LP10-->LP11

- MIPI典型时钟值

.. image::
    res/mipi_clk_type.jpg

.. image::
    res/mipi_data_type.jpg


.. note::
    UI即MIPI的CLK lane的高速时钟周期的二分之一，因为MIPI采用DDR时钟


Multi-Lane Distribution and Merging
--------------------------------------

.. image::
    res/multi_lane_dis.png

.. image::
    res/two_lan_transfer.png

.. image::
    res/four_lane_trans.png



Low Level Protocol
-------------------

在mipi底层传输协议中,由短包和长包组成,这两种数据包都是由SoT开始EoT结束

.. image::
    res/low_level_protocol.png

底层数据包格式
^^^^^^^^^^^^^^^^


**长包数据格式**

长包数据格式如下

.. image::
    res/long_package_struct.png

- Data ID: 定义了虚拟通道以及数据类型

- WC: 定义了8-bit的data payload字节数

- ECC: package header的ECC校验,包括Data ID和WC数据域

- Data Payload: 数据域

- CS: checksum(16-bit)

**短包数据格式**

.. image::
    res/short_package_struct.png

Data ID
^^^^^^^^

Data ID数据包格式如下

.. image::
    res/data_id_struct.png

Virtual Channel
""""""""""""""""""""

虚拟通道标识符的目的是为在数据流交错的不同数据流中提供单独的通道

.. image::
    res/vc_channel.png

即:MIPI接受端可以通过VC标识符将交错的几路视频数据进行拆分

.. image::
    res/vc_package.png


Data Type
""""""""""

.. image::
    res/data_type_class.png

- Synchronization Short Packet Data Types

.. image::
    res/data_type_codes.png

- Generic Short Packet Data Types

.. image::
    res/generic_short_dt.png

- Generic Long Packet Data Types

.. image::
    res/generic_long_di.png

- YUV Image Data Types

.. image::
    res/yuv_dt.png


- RGB Image Data Types

.. image::
    res/rgb_dt.png

- RAW Image Data Types

.. image::
    res/raw_dt.png

- User Defined Data Formats

用户自定义数据则可以传输任意数据,例如JPEG或者MPEG4,或者其他类型的通信数据.

.. image::
    res/user_dt.png


ECC
^^^^

.. image::
    res/ECC_Example.png

CS
^^^^

ECC对Package header进行校验,而Checksum则对数据域(data payload)进行校验,使用16-bit CRC算法

.. image::
    res/package_cs.png


Sync Short package
^^^^^^^^^^^^^^^^^^^^

帧同步信号以及行同步信号内由短包进行发送,在短包的data type域中定义


::

    0x00---->0x02---->0x03........0x02----->0x03------>0x01
    FS        LS       LE          LS        LE         FE


.. image::
    res/frame_trans.png


**hsync以及vsync示意**

.. image::
    res/line_frame_blanking.png


.. image::
    res/hsync_example.png


.. image::
    res/vsync_example.png

**frame示意图**

.. image::
    res/general_frame.png


.. image::
    res/digital_interlaced_frame.png


Data Type Interleaving
^^^^^^^^^^^^^^^^^^^^^^^^

CSI-2支持在同一视频数据中交错传输不同图像格式,也就是MIPI-CSI支持传输不同分辨率不同数据格式的图像.

有两种方式传输交错的视频数据1. 使用Data Type  2.使用Vrtual Channel

.. image::
    res/interleaved_trans.png

.. image::
    res/interleaved_trans_vc.png

.. image::
    res/packet_interleaved.png


Data Formats
--------------


YUV Image data
^^^^^^^^^^^^^^^

- Legacy YUV420 8-bit

.. image::
    res/legacy_yuv420_8.png

.. image::
    res/legacy_yuv420_frame.png

- YUV420 8-bit

.. image::
    res/yuv420-8.png

.. image::
    res/yuv420_8_frame.png

- YUV420 10-bit

.. image::
   res/yuv420_10.png

.. image::
    res/yuv420_10_frame.png

- YUV422 8-bit

.. image::
    res/yuv422_8.png

.. image::
    res/yuv422_8_frame.png

- YUV422 10-bit

.. image::
    res/yuv422_10.png

.. image::
    res/yuv422_10_frame.png


RGB Image data
^^^^^^^^^^^^^^^

- RGB888

.. image::
    res/rgb_888.png

.. image::
    res/rgb_888_frame.png

- RGB666

.. image::
    res/rgb_666.png

.. image::
    res/rgb_666_frame.png


- RGB565

.. image::
    res/rgb_565.png

.. image::
    res/rgb_565_frame.png
  

- RGB555

.. image::
    res/rgb_555.png

- RGB444

.. image::
    res/rgb_444.png


RAW Image data
^^^^^^^^^^^^^^^^

- RAW6

.. image::
    res/raw_6.png


.. image::
    res/raw_6_frame.png


- RAW7

.. image::
    res/raw_7.png

.. image::
    res/raw_7_frame.png

- RAW8

.. image::
    res/raw_8.png

.. image::
    res/raw_8_frame.png

- RAW10

.. image::
    res/raw_10.png

.. image::
    res/raw_10_frame.png

- RAW12

.. image::
    res/raw_12.png

.. image::
    res/raw_12_frame.png

- RAW14

.. image::
    res/raw_10.png

.. image::
    res/raw_14_frame.png


