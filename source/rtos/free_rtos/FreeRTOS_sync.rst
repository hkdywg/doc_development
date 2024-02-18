FreeRTOS同步机制
===================

信号量
----------

::

    //创建二进制信号量
    SempaphoreHandle_t xSemaphoreCreateBinary(void);

    //静态创建二进制信号量
    SempaphoreHandle_t xSemaphoreCreateBinaryStatic(StaticSemaphore_t *pxSemphoreBuffer);
