hardware design
===============

原理图、PCB设计
---------------

* :download:`holo-ark-v4-sch.pdf<res/HoloArk_V40_200917a.pdf>`

* :download:`板卡标注图<res/ark-v4-标注.png>`



硬件问题汇总
============

电源
------------

问题1 
    vx_app_tidl_avp3.out 运行后板子啸叫

问题原因 
    vx_app_tidl_avp3.out 运行后资源占用起伏较大，造成电流波动大，
    板卡啸叫来源于电容，而非电感。电容由于电流波动引起压电效应，
    电容形变较大时，且频率在人耳可听的范围。便认为产生啸叫

网络
------------


emmc
------------

