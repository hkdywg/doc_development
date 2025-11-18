AVB之gPTP
==============

gPTP同步原理
--------------

gPTP校时机制

.. image::
    res/gPTP_topo.image

体系结构
^^^^^^^^^^^

AVB域内的每个节点都是一个时钟，由以下两个角色组成．

- 一个是主时钟，它是标准时间的来源

- 其他的都是从时钟，他们必须把自己的时间和主时钟调整一致


**绝对时间同步**


下图包含一个主时钟和一个从时钟，二者时间不同步．现在要把从时钟的时间校准到主时钟的时间，其中t1, t2为主时钟的对应时间，t2, t3为从时钟的
对应时间．

.. image::
    res/time_sync.image

主要流程如下

1. 主时钟在t1时刻发送sync命令，从时钟在t2时刻收到同步命令．这时候从时钟并不知道主时钟在什么时候发出这个sync命令的，但是知道自己在t2时刻收到该命令

2. 主时钟发送一个Follow_up命令，该命令中携带t1的值．从时钟收到后，知道上面的sync指令是在t1时刻发出的．此时从时钟拥有t1 t2两个值

3. 从时钟在t3时刻发出一个delay_req命令，主时钟在t4时刻收到该命令．此时从时钟知道t1, t2, t3三个值

4. 主时钟接着发送一个delay_resp响应从时钟的delay_req，该命令中携带t4的值．从时钟收到后，知道主时钟是在t4时刻收到delay_req命令的．此时从时钟知道t1, t2, t3, t4四个值

5. 我们假设路径传输延时是对称的，从时钟可以根据下面的公式计算路径传输延时(path_delay)，以及自己与主时钟的偏差(clock_offset)

::

    t2 - t1 = path_delay + clock_offset
    t4 - t3 = path_delay - clock_offset

由此可以算出

::

    path_delay = (t4 - t3 + t2 - t1) / 2
    clock_offset =(t3 - t4 + t2 - t1) / 2

6. 现在从时钟知道了自己与主时钟的时差clock_offset, 就可以调整自己的时间了．另外从时钟还知道自己与主时钟的路径传输延时path_delay, 该值
   对switch意义重大，因为在gPTP的P2P校时方式中，switch需要转发主时钟的校时信号，在转发的时候需要将该值放在补偿信息中


影响校时精度的因素
--------------------

传输时延不对称
^^^^^^^^^^^^^^^

前面提到的校时流程中，我们假设传输时延是对称的．实际情况中，路径有可能是不对称的，这会导致校时误差

gPTP对策:
    
- 要求网络内的节点都是时间敏感的

- 传输延时分段测量(P2P)减少平均误差

- 中间转发节点可以计算报文的驻留时间，保证校时信号传输时间的准确性

- 如果已知链路不对称，可以将该值写在配置文件中，对于endpoint在校时的时候会把该偏差考虑进去．对于bridge设备，在转发的时候，会在PTP报文的矫正域把对应的差值补偿过来

驻留时间
^^^^^^^^^

对于bridge设备，从接收报文到转发报文所消耗的时间，称为驻留时间．该值会具有一定的随机性，从而影响校时精度

gPTP对策: Bridge设备必须具有测量驻留时间的能力，在转发报文的时候，需要将驻留时间累加在PTP报文的矫正域中

时间戳采样点
^^^^^^^^^^^^^

为了达到高精度的时间同步，必须消除软件带来的不确定因素，这就要求必须把时间采样点放在最靠近传输介质的地方．

gPTP对策:　发送方与接收方都在MAC层记录报文发送及接收的时间戳．

时间频率
^^^^^^^^^


晶振频率越高，误差越小，校时越精确


传输路径延迟测量方式
^^^^^^^^^^^^^^^^^^^^^^

IEEE 1588支持两种路径时延测量方式: ``End-to-End(E2E)`` 和 ``Peer-to-Peer(P2P)`` ,二者不能在同一个网络中共存．

在E2E机制中，强调的是两个支持PTP的端点(一个master port, 一个slave port)之间的延时，这两个端点可能是直接相连的，也可能中间穿插了普通的交换机，时间敏感的
透明时钟(TC),在通信的双方看来，信息都是在master port和slave port之间传输，所以最终slave测量到的传输时延是从master到slave的端到端时延

在P2P机制中，要求网络内所有节点必须支持P2P，所以它强调的是相邻节点间的通信，最终测量的是相邻节点间的传输延时

二者主要的区别如下图所示：

- P2P测量的是相邻节点间的延时，路径测量报文不会跨节点传输，有利于网络扩展．E2E测量的是master port到slave port之间的延时，中间节点需要转发延时测量报文，
  网络规模较大时，报文可能泛滥，master节点压力较大

- master节点变更时，E2E需要重新测量到新master节点的路径传输时延，P2P只需关心相邻节点．

- E2E方式允许网络中有普通的switch(透传PTP报文即可，由于驻留时间随机，会影响测量精度)，而P2P要求网络中的switch必须支持P2P

- E2E机制中，校时报文和路径测量报文是耦合在一起的，P2P机制中有独立的报文负责路径测量，把校时和路径测量解耦了

.. image::
    res/E2E_P2P.image

gPTP要求使用P2P方式，并且要求网络中所有设备都支持PTP协议，路径传输延时测量只在相邻节点间进行．它使用Pdelay_Req, Pdelay_Resp, Pdelay_Resp_Follow_Up消息来测量路径传输延时


.. note::
    P2P中没有使用Sync报文，而是专门为路径测量新建了几个报文，降低了复杂度．


.. image::
    res/P2P_Sync.image


时钟类型
^^^^^^^^^^

PTP时钟可以分为两类：One-Step Clock和Two-Step Clock

.. image::
    res/clock_type.image


如果t1能在sync报文中就传递给slave节点，就省了一条报文，这是One-step clock的做法．这种时钟对硬件要求比two-step clock要高，成本也比较高．


gPTP校时过程
--------------

为了表述方便，这里做两点假设：

1. 假设下面三个设备都是one-step的clock，即sync报文发出后，不需要额外的follow-up报文告知sync报文是在哪个时刻发送的(实际上802.1AS要求时钟必须是two-step的)

2. 假设各设备已通过前面介绍的测量机制测量出路径传输延迟path_delay1, path_delay2

.. image::  
    res/time_sync_process.image


校时流程如下:

1. Grandmaster时钟在t1时刻发送时间同步报文sync到bridge, 报文sync的origin timestamp中填充时间信息t1,  校正域correction填充ns的的小数部分(sync报文的时间戳部分只能
   表示秒和纳秒，不足1纳秒的只能放在校正域)

2. bridge收到sync报文后，不仅要矫正自己的时钟，还要把sync报文转发出去

3. bridge根据sync报文调整自己的时钟，bridge在t2时刻收到sync报文，并从中解析出grandmaster是在t1时刻发送该报文的，以及grandmaster填充的校正值correction.在t2时刻
   grandmaster的时钟显示的值应该是

::

    t1 + correction + path_delay1

由此可以计算出bridge的时钟偏差，并调整自己的时钟

::

    clock_offset = t1 + correction + path_delay1 - t2


4. bridge转发sync报文，bridge将自己与上级节点的路径延时(path_delay1)和sync报文在自己这里的驻留时间(rEsidence_time)累加到sync报文的校正域，并转发出去．此时
   correction值如下

::

    correction = old_value_of_correction + path_delay1 + residence_time


5. End-Point在t4时刻收到sync报文，并从中解析出grandmaster是在t1时刻发送该报文的，以及bridge矫正后的correction．在t4时刻，grandmaster的时钟显示的值应该是

::

    t1 + correction + path_delay2

由此可以计算出end-point和grandmaster的时钟偏差，并调整自己的时钟

::

    clock_offset = t1 + correction + path_delay2 - t4


.. note::
    从上面的校时流程可以看出，整个校时过程像水面的波纹一样从grandmaster开始向外一层层的扩散，每个节点只关注自己与上级节点的传输延时，bridge负责将中间路径的传输
    延时和缓存时间逐段累加到矫正域

