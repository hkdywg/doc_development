代码分析
--------

以下内容以Device Tree相关的数据流分析为索引，对ARM linux kernel的代码进行解析，主要的数据流包括

1)  初始化流程，也就是扫描dtb并将其转换位device tree structure
2） 传递运行时参数以及platform的识别流程
3)  将device tree structure并入linux kernel的设备驱动模型


