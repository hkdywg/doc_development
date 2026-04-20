AVB之AVTP
=============

以下内容主要介绍AVB协议族中的音视频传输协议AVTP(IEEE Std 1722-2016)

AVTP是个链路层传输协议，其主要作用有两个：

- 音视频数据封装: 将音视频数据封装成相应的格式在链路层传输

- 媒体同步:

    - 媒体时钟同步: 不同的媒体类型有自己的媒体时钟，这些媒体时钟都映射到gPTP时间(同一个时间坐标系)，接收端可以轻松进行媒体时钟恢复

    - 播放时间同步: 数据发送时指示接收方在未来的某个时间点播放，如果有多个接收者，他们就会在未来的同一时刻播放


音视频数据封装
---------------

AVTP是链路层传输协议，并且是基于VLAN的，在以太网帧中的位置如下：

.. image::
    res/AVTP_ETH.image

针对不同的音视频格式，AVTP有不同的header和payload格式，本文主要基于H264介绍AVTP


header结构
^^^^^^^^^^

下图是AVTP封装H264视频数据时的头部结构

.. image::
    res/avtp_header.image


- subtype: AVTP子类型，本例为压缩视频格式，一般简称为CVF

- tv: 它用来表示字段5是否有效，0表示无效，1表示有效．这是因为一个视频单元(NALU)会被拆分为多个AVTP包，规范要求只需要在最后一个AVTP包中添加时间戳即可

- sequence_num: 包序号，接收端判断是否丢包，乱序

- stream_id: 流id，用来标识本数据流．长度为64bit，前48bit与MAC地址定义规则一致，大部分直接拿MAC地址作为前48bit,后16bit根据需要自定义分配

- avtp_timestamp: AVTP Presentation time

- format: 用来表明payload承载的音视频数据是自定义格式还是RFC规范定义的格式

- format_subtype: payload承载的音视频数据自定义，本例中是H264格式

- M: 代表一个NALU的结束，如果一个NALU被拆分成多个AVTP报文，只有最后一个需要把M标志写成1

- h264_timestamp: h264时间戳

- ptv: 用来指示h264_timestamp字段是否有效


实际抓包数据

.. image::
    res/net_package.image


payload结构
^^^^^^^^^^^^^^

AVTP payload结构如下图所示：

.. image::
    res/AVTP_payload.image

h264帧由多个NALU单元组成，如下图所示

.. image::
    res/h264_payload.image

H264帧分为I帧，P帧，B帧三类，其中

- I帧不存在帧间依赖，可以单独解码成像

- P帧依赖本帧前面的I帧或P帧(这种依赖是从I帧依次传递过来的，所有中间任何一帧出错都会导致后续帧出错)

- B帧不仅依赖前面的帧，还依赖后面的帧

如果一个码流只有I帧和P帧，这种码流属于 ``非交叉式编码模式(Non-interleaved mode)`` ,帧的解码顺序和显示顺序是一致的．如果码流中包含了B帧，
就成为了 ``交叉编码模式(Interleaved mode)`` ,帧的解码顺序和显示顺序就不一定是一致的了．

RTP封装H264数据是以NALU为单位进行的，而不是以帧为单位进行的．RTP打包模式有下面三种：

- Single NAL unit mode: 单NALU模式，使用H.241

- Non-interleaved mode: 非交叉模式，NALU的解码顺序和显示顺序是一致的，先解码的NALU先显示

- Interleaved mode: 交叉模式，本模式下NALU的解码顺序和显示顺序是不一致的，比如有B帧的情况下

RTP打包使用哪种模式，有编码器决定的，不能随便填．


RTP包类型有包含以下几种

- 单个NALU: 一个数据报文包含一个完整的NALU

- 聚合多个NALU: 一个数据包文中包含多个NALU,根据这些NALU的时间戳是否相同，又分为下面两种

  - STAP: 一个数据报文包含多个NALU,这些NALU时间戳相同，又分为STAP-A和STAP-B方式

  - MTAP: 一个数据报文包含多个NALU，这些NALU时间戳不同，又分为MTAP16和MTAP24方式

- 分片方式: NALU太大，无法用一个数据包传输，需要分片，又分为FU-A和FU-B方式


打包模式和包类型之间的关系如下，并不能随便使用

.. image::
    res/package_mode.image


媒体同步
-----------

AVTP Presentation Time
^^^^^^^^^^^^^^^^^^^^^^^^

AVTP Presentation time的含义是呈现时间，表示接收方在该时刻需要将AVTP数据包payload中的音视频数据送到应用层进行处理，比如解码播放．


播放时间同步
^^^^^^^^^^^^^

播放时间同步用来指示接收端在某一时刻处理音视频数据，数据可以提前到，但不能迟到．

媒体时钟同步
^^^^^^^^^^^^^

媒体时钟同步解决的是采集速度和播放速度一致的问题(相对时间同步的问题)

视频的媒体时钟一般都是90khz,理想情况下，大家以同样的频率震荡，但是随着时间的流逝或者环境影响，会漂移，这就导致talker和listener的媒体时钟不同步，进而表现为播放不正常

媒体时钟恢复，是指listener根据avtp presentation time重建媒体时钟，使之和采集端保持同步，进而指导音视频以采集时的速率播放，流程如下

1. 在发送端talker把媒体时钟嵌入在展示时间戳中(采样点对应gPTP的某个时刻)

.. image::
    res/talker_timer.image

2. 在接收端，媒体时钟从展示时间戳中恢复(AVTP Presentation time和本地gPTP时间对比，二者同步的时刻对应一个Media clock的采样点),进而控制音视频的播放

.. image::
    res/listener_time.image

3. 媒体时钟回复模块示意图如下


.. image::
    res/media_time_sync.image


h264_timestamp
^^^^^^^^^^^^^^^^

AVTP中有了展示时间戳，为什么还要加上h264_timestamp时间戳呢？

在交叉编码模式下，解码顺序和显示顺序是不一致的，如下图所示视频数据是按照Frame0, Frame1的顺序依次采集的，接收端也要按这个顺序显示

.. image::
    res/frame_order.image

但由于存在B帧，编码器实际的输出顺序如下，接收端也要按照下面的顺序解码

.. image::
    res/frame_display_order.image

AVTP Presentation Time的作用是DTS(Decoding Time Stamp),在非交叉模式下，是可以正常工作的．但是在交叉模式下，由于解码顺序和显示顺序不一致，虽然能按正确的顺序
解码，但不能按正确的顺序显示．为了解决这个问题，才加上h264_timestamp
