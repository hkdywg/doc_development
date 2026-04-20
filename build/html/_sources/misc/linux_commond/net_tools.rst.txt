网络调试工具
============

bmon 强大的网络带宽监视和调试工具
---------------------------------

可以通过以下命令启动bmon

::

    bmon
    或者可以指定网络,以下命令将监视enp4s0网络接口
    bmon -p enp4s0
    也可以使用-r指定间隔
    bmon -r 2 -p enp4s0

bmon可以用来监控网络带宽，可查看TX和RX，方便用来定位带宽导致的问题


iperf 命令
----------

iperf是一个网络性能测试工具，可以用来测试tcp和udp的最大带宽性能，具有多种参数和udp特性，可以根据需要进行调整，
可以报告带宽，延迟抖动和数据包丢失。

iperf 分别运行在客户端和服务器端，所以在测试时需要在进行通信的测试的双方分别运行iperf。

- 通用配置选项

::

    -F,--file name      //客户端：从文件中读取并写入网络，而不是使用随机数据
                        //服务器端：从网络读取并写入文件，而不是将数据丢弃

    -V，--verbose       //更详细的输出

    -B,--bind host      //绑定到主机一个地址，对于客户端，这设置了出战接口。对于服务器，这将设置传入的接口

    --logfile file      //将输出发送到一个日志文件

- 服务器选项

::

    -s,--server         //在服务器模式下运行iperf
    
    -D,--daemon         //在后台运行服务器作为守护进程

- 客户端选项

::

    -c,--client host        //在客户端模式下运行iper

    -u,--udp                //使用UDP

    -t,--time n             //设置传输总时间，默认是10s

    -b,--bandwidth n[KM]    //UDP模式使用的带宽，默认是1Mbit/sec

    -N,--no-delay           //设置TCP不延迟选项，使nagle算法失效

    -P，--paranlel n        //线程数，默认是1线程

    -4，--version4          //只使用IPV4


- 应用实例

服务器端

::

    yinwg@yinwg-ThinkPad-E470:~$ iperf3 -s -V
    iperf 3.1.3
    Linux yinwg-ThinkPad-E470 5.4.0-65-generic #73~18.04.1-Ubuntu SMP Tue Jan 19 09:02:24 UTC 2021 x86_64
    -----------------------------------------------------------
    Server listening on 5201
    -----------------------------------------------------------
    Time: Fri, 05 Mar 2021 01:18:41 GMT
    Accepted connection from 192.168.199.2, port 45332
          Cookie: ARK.1614907121.724677.7b5fc3d948282c
          TCP MSS: 1448 (default)
    [  5] local 192.168.199.1 port 5201 connected to 192.168.199.2 port 45334
    Starting Test: protocol: TCP, 1 streams, 131072 byte blocks, omitting 0 seconds, 10 second test
    [ ID] Interval           Transfer     Bandwidth
    [  5]   0.00-1.00   sec  25.7 MBytes   216 Mbits/sec
    [  5]   1.00-2.00   sec  25.8 MBytes   216 Mbits/sec
    [  5]   2.00-3.00   sec  25.8 MBytes   216 Mbits/sec
    [  5]   3.00-4.00   sec  25.8 MBytes   216 Mbits/sec
    [  5]   4.00-5.00   sec  25.8 MBytes   216 Mbits/sec
    [  5]   5.00-6.00   sec  25.8 MBytes   216 Mbits/sec
    [  5]   6.00-7.00   sec  25.8 MBytes   216 Mbits/sec
    [  5]   7.00-8.00   sec  25.8 MBytes   216 Mbits/sec
    [  5]   8.00-9.00   sec  25.8 MBytes   216 Mbits/sec
    [  5]   9.00-10.00  sec  25.8 MBytes   216 Mbits/sec
    [  5]  10.00-10.00  sec  84.8 KBytes   214 Mbits/sec
    - - - - - - - - - - - - - - - - - - - - - - - - -
    Test Complete. Summary Results:
    [ ID] Interval           Transfer     Bandwidth
    [  5]   0.00-10.00  sec  0.00 Bytes  0.00 bits/sec                  sender
    [  5]   0.00-10.00  sec   258 MBytes   216 Mbits/sec                  receiver
    CPU Utilization: local/receiver 13.4% (3.3%u/10.1%s), remote/sender 0.0% (0.0%u/0.0%s)
    iperf 3.1.3
    Linux yinwg-ThinkPad-E470 5.4.0-65-generic #73~18.04.1-Ubuntu SMP Tue Jan 19 09:02:24 UTC 2021 x86_64
    -----------------------------------------------------------
    Server listening on 5201
    -----------------------------------------------------------

客户端

::

    root@ARK:~# iperf3 -c 192.168.199.1
    Connecting to host 192.168.199.1, port 5201
    [  4] local 192.168.199.2 port 45334 connected to 192.168.199.1 port 5201
    [ ID] Interval           Transfer     Bandwidth       Retr  Cwnd
    [  4]   0.00-1.00   sec  26.4 MBytes   221 Mbits/sec    0    102 KBytes
    [  4]   1.00-2.00   sec  25.8 MBytes   216 Mbits/sec    0    102 KBytes
    [  4]   2.00-3.00   sec  25.7 MBytes   216 Mbits/sec    0    102 KBytes
    [  4]   3.00-4.00   sec  25.8 MBytes   216 Mbits/sec    0    102 KBytes
    [  4]   4.00-5.00   sec  25.7 MBytes   216 Mbits/sec    0    102 KBytes
    [  4]   5.00-6.00   sec  25.8 MBytes   216 Mbits/sec    0    102 KBytes
    [  4]   6.00-7.00   sec  26.2 MBytes   219 Mbits/sec    0    168 KBytes
    [  4]   7.00-8.00   sec  26.2 MBytes   219 Mbits/sec    0    242 KBytes
    [  4]   8.00-9.00   sec  25.8 MBytes   216 Mbits/sec    0    242 KBytes
    [  4]   9.00-10.00  sec  25.7 MBytes   216 Mbits/sec    0    242 KBytes
    - - - - - - - - - - - - - - - - - - - - - - - - -
    [ ID] Interval           Transfer     Bandwidth       Retr
    [  4]   0.00-10.00  sec   259 MBytes   217 Mbits/sec    0             sender
    [  4]   0.00-10.00  sec   258 MBytes   216 Mbits/sec                  receiver

    iperf Done.


netstat 命令
------------

netstat 命令用于显示各种网络相关信息，如网络连接，路由表，接口状态，多播成员等等。

netstat 输出结果可以分为两部分

一部分是：active interrnet connections,称为有源TCP连接，其中Recv-Q和Send-Q指的是接收队列和发送队列一般为0

一部分是：active unix domain sockets,称为有源unix域套接口(和网络套接字一样，只能用于本机通信，性能可以提高一倍)

proto显示使用的协议，refcnt表示连接到本套接口上的进程号，types表示套接口的类型，state显示套接口当前的状态，path表示连接到套接口的其他进程使用的路径名。

- 常见参数

::

    -a      显示所有选项

    -t      仅显示tcp相关选项

    -u      仅显示udp相关选项

    -l      仅列出所有在listen的服务状态

    -p      显示建立相关连接的程序名

    -r      显示路由表

    -e      显示扩展信息，例如uid

    -s      按各个协议进行统计

    -c      每隔一个固定时间，执行该netstat命令


- 命令实例


::

    netstat -a | more       //列出所有端口

    netstat -au             //列出所有udp端口
    激活Internet连接 (服务器和已建立连接的)
    Proto Recv-Q Send-Q Local Address           Foreign Address         State
    udp        0      0 0.0.0.0:44527           0.0.0.0:*
    udp        0      0 localhost:domain        0.0.0.0:*
    udp        0      0 0.0.0.0:bootpc          0.0.0.0:*
    udp        0      0 0.0.0.0:bootpc          0.0.0.0:*
    udp        0      0 0.0.0.0:tftp            0.0.0.0:*
    udp        0      0 0.0.0.0:sunrpc          0.0.0.0:*
    udp        0      0 0.0.0.0:37209           0.0.0.0:*
    udp        0      0 0.0.0.0:49720           0.0.0.0:*
    udp        0      0 0.0.0.0:ipp             0.0.0.0:*
    udp        0      0 0.0.0.0:45790           0.0.0.0:*
    udp        0      0 0.0.0.0:829             0.0.0.0:*
    udp        0      0 224.0.0.251:mdns        0.0.0.0:*
    udp        0      0 224.0.0.251:mdns        0.0.0.0:*
    udp        0      0 224.0.0.251:mdns        0.0.0.0:*
    udp        0      0 224.0.0.251:mdns        0.0.0.0:*

    netstat -lt             //列出所有的在监听的tcp端口

    netstat -lx             //列出所有监听的unix端口

    netstat -r              //显示路由表信息
    root@ARK:~# netstat -r
    Kernel IP routing table
    Destination     Gateway         Genmask         Flags   MSS Window  irtt Iface
    default         192.168.199.1   0.0.0.0         UG        0 0          0 usb0
    192.168.1.0     0.0.0.0         255.255.255.0   U         0 0          0 eth0
    192.168.199.0   0.0.0.0         255.255.255.0   U         0 0          0 usb0

    netstat -i              //显示网络接口列表
    Kernel Interface table
    Iface      MTU    RX-OK RX-ERR RX-DRP RX-OVR    TX-OK TX-ERR TX-DRP TX-OVR Flg
    enp4s0    1500 681787887      0 215214 0       6151104      0      0      0 BMRU
    enx20210  1500   756690      0      0 0        379179      0      0      0 BMRU
    lo       65536   609276      0      0 0        609276      0      0      0 LRU
    wlp5s0    1500  5444407      0 948041 0          4651      0     19      0 BMRU

    netstat -ap | grep ssh  //找出程序运行的端口


tcpdump
-------------

网络上的流量数据包非常多，如果想要抓取所需要的数据包，就需要进行过滤，所以学习抓包工具其实就是学习如何定义过滤器的过程

``tcpdump`` 命令行

::

    tcpdump option proto dir type

- option: 可选参数

  - [-aAbdDefhHIJKILnNOpqRStuUvxX] [-B size]

  - [-c count] [-C file_size] [-E alog:secret] [-F file]

  - [-G seconds] [-i interface] [-j tstamptype]

  - [-M secret] [-P in|out|inout] [-r file] [-s snaplen]

  - [-T type] [-V file] [-W filecount]

  - [-y datalinktype] [-z command] [-Z user]

- proto: 类过滤器，根据协议进行过滤，可识别的关键词:tcp, udp, icmp, ip, ip6, arp, rarp, ether, wlan, fddi, tr, decnet
- type: 类过滤器，可识别的关键词有: host, net, port, portrange, 这些词后面需要再接参数
- direction: 类过滤器，根据数据流进行过滤，可识别的关键词有: src, dst,同时可以使用逻辑运算符进行组合，比如src or dst 

tcpdump输出内容
^^^^^^^^^^^^^^^^^

tcpdump输出实例

::

    21:26:49.013621 IP          172.20.20.1.15605    >        172.20.20.2.5920: Flags [P.], seq 49:97, ack 106048, win 4723, length 48
    时间戳　        网络协议    发送方IP+端口号　　数据流向     接收方IP+端口号  flag标识符  seq号　　　ack号　　　win窗口      数据长度


.. note::
    Flags标识符
    - [S]: SYN(开始连接)

    - [P]: PSH(推送数据)

    - [F]: FIN(结束连接)

    - [R]: RST(重置连接)

    - [.]: 没有Flag,(意思是除上面四种类型外的其他情况，有可能是ACK也有可能URG)


常规过滤规则
^^^^^^^^^^^^^^

- 基于IP地址过滤: host

:: 

    tcpdump host 172.29.4.43
    tcpdump -i ens33 src 172.29.4.43
    tcpdump -i ens33 dst 172.29.4.37

- 基于网段进行过滤

::

    tcpdump net 172.29.4.23/56
    #网段同样可以细分为源网段和目标网段
    tcpdump src net 172.29
    tcpdump dst net 172.29

- 基于端口进行过滤

::

    tcpdump port 8088
    tcpdump src port 8088
    tcpdump dst port 8088
    #同时指定两个端口
    tcpdump port 80 or port 8088
    tcpdump portrange 8000-8088

.. note::
    对于一些常见协议的默认端口可以直接使用协议名，如果http=80, https=443
    tcpdump tcp port http

- 基于协议进行过滤: proto

::

    tcpdump icmp


可选参数解析
^^^^^^^^^^^^^^^

**设置不解析域名提升速度**

- -n: 不把ip转化成域名，直接显示ip，避免执行DNS lookups的过程，速度会快很多

- -nn: 不把协议和端口转化成名字

- -N: 不打印出host的域名部分，如果设置了此规则，tcpdump将会打印'nic'而不是'nic.ddn.mil'

**过滤结果输出到文件**

使用tcpdump工具抓到包后，往往需要借助其他工具进行分析，比如常见的wireshark

::

    #将抓到的icmp包保存到icmp.pcap文件中
    tcpdump icmpp -w icmp.pcap

**从文件中读取包数据**

::
    
    tcpdump icmp -r all.pcap


**控制详细内容的输出**

- -v: 产生详细的输出，比如包的TTL, id标识，数据包长度，以及IP包的一些选项

- -vv: 产生比-v更详细的输出，比如NFS回应包中的附加域将会被打印，SMB数据包也会被完全解码

- -vvv: 产生比-vv更详细的输出，比如telent时所使用的SB，SE选项将会被打印

**控制时间的显示**

- -t: 在每行的输出中不输出时间戳

- -tt: 在每行的输出中输出时间戳

- -ttt: 输出每两行打印时间间隔

- -tttt: 在每行打印的时间戳之前添加日期的打印

**显示数据包的头部**

- -x: 以16进制的形式打印每个包的头部数据(不包括数据链路层的头部)

- -xx: 以16进制的形式打印每个包的头部数据(包括数据链路层的头部)

- -X: 以16进制和ASCII码的形式打印每个包的数据(不包括数据链路层的头部)

- -XX: 以16进制和ASCII码的形式打印每个包的数据(包括数据链路层的头部)

**过滤指定网卡的数据包**

- -i: 指定要过滤的网卡接口，如果要查看所有网卡可以"-i any"

**过滤特定流向的数据包**

- -Q: 选择入方向还是出方向，可选项有:in, out, inout, 也可以使用 --direction=[direction]这种写法

**其他一些常用参数**

- -A: 以ASCII码的方式显示每一个数据包，方便查看数据

- -l: 基于行的输出，便于保存查看

- -q: 简洁的打印输出，即打印很少的协议相关信息，从而输出行都比较简短

- -c: 捕获count个包后tcpdump就退出

- -s: tcpdump默认只会截取前96字节的内容，要想截取所有的报文内容可以使用 ``-s number`` ,number就是要截取的报文字节数，如果是0的话表示截取报文全部内容

- -S:使用绝对序列号，而不是相对序列号

- -C: file-size, tcpdump在把原始数据包直接保存在文件中之前会检查此文件大小是否超过了file-size,如果超过了将会关闭此文件，然后创建一个新文件用于保存数据，
  新创建的文件名与-w选项指定的文件名一致，但文件名后面多了一个数字，该数字会从1开始

- -F: 使用file文件作为过滤条件表达式的输入

**对输出内容进行控制的参数**

- -D: 显示所有可用的网络接口的列表

- -e: 每行的打印输出中将包含数据包的数据链路层头部信息

- -E: 揭秘IPSEC数据

- -L: 列出网络接口所支持的数据链路层的类型后退出

- -Z: 后接用户名，在抓包时会受到权限的限制，如果以root用户启动tcpdump则有超级权限

- -d: 打印出易读的包匹配码

- -dd: 以C语言的形式打印出包匹配码

- -ddd: 以十进制数的形式打印出包匹配码










