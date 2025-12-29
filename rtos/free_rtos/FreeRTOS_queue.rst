FreeRTOS 队列
=================


队列函数
-------------

使用队列的流程：创建队列，写队列，读队列，删除队列

创建
^^^^^^

队列的创建有两种方法: 

- 动态分配内存: 队列的内存在函数内部动态分配

- 静态分配内存: 队列的内存要事先分配好

::

    // uxQueueLength: 队列长度，最多存放多少个数据
    // uxItemSize: 每个数据的大小
    // 动态内存分配法
    QueueHandle_t xQueueCreate(UBaseType_t uxQueueLength, UBaseType_t uxItemSize);


    // uxQueueLength: 队列长度
    // uxItemSize: 每个数据的大小
    // pucQueueStorageBuffer: 需指向uint8_t数组，此数组大小至少为uxQueueLength * uxItemSize
    // pxQueueBuffer: 必须执行一个StaticQueue_t结构体，用来保存队列的数据结构
    QueueHandle_t xQueueCreateStatic(UBaseType_t uxQueueLength, UBaseType_t uxItemSize,
                                        uint8_t *pucQueueStorageBuffer, StaticQueue_t *pxQueueBuffer);


复位
^^^^^^^

队列刚被创建时，里面没有数据，使用过程中可以调用 ``xQueueReset`` 把队列恢复为初始状态

::

    BaseType_t xQueueReset(QueueHandle_t pxQueue)


删除
^^^^^

删除队列的函数为 ``vQueueDelete`` 只能删除使用动态方法创建的队列，然后释放内存

::

    void vQueueDelete(QueueHandle_t xQueu)


写队列
^^^^^^^^^^

可以把数据写到队列头部，也可以写到尾部．这些函数有两个版本: 在任务中使用，在ISR中使用

::

    //往队列尾部写入数据，如果没有空间，阻塞时间为TicksToWait
    BaseType_t xQueueSend(QueueHandle_t xQueue, const void *pvItemToQueue, TickType_t xTicksToWait)

    //往队列尾部写入数据，此函数在中断函数中使用，不可阻塞
    BaseType_t xQueueSendToBackFromISR(QueueHandle_t xQueue, const void *pvItemToQueue, BaseType_t *pxHigherPriorityTaskWoken)

    //往队列头部写入数据
    BaseType_t xQueueSendToFront(QueueHandle_t xQueue, const void *pvItemToQueue, TickType_t xTickToWait);

    //往队列头部写入数据，不可阻塞
    BaseType_t xQueueSendToFrontFromISR(QueueHandle_t xQueue, const void *pvItemToQueue, BaseType_t *pxHigherPriorityTaskWoken);


读队列
^^^^^^^^

::

    BaseType_t xQueueReceive(QueueHandle_t xQueue, void *cosnt pvBuffer, TickType_t xTicksToWait)

    BaseType_t xQueueReceiveFromISR(QueueHandle_t xQueue, void *pvBuffer, BaseType_t *pxTaskWoken)


查询
^^^^^

::

    //返回队列中可用数据的个数
    UBaseType_t uxQueueMessagesWaiting(const QueueHandle_t xQueue);

    //返回队列中可用空间的个数
    UBaseType_t uxQueueSpaceAvalible(const QueueHandle_t xQueue)






