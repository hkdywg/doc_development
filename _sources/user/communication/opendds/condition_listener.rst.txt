condition和listener
======================

DDS规范定义了用于通知应用程序DCPS通信状态改变的两个单独的机制．大多数状态类型定义包含与状态改变相关的信息结构，并且可以由应用程序使用条件
或监听器来检测．

每个实体类型(域参与者，主题，发布者，订阅者，数据读取器和数据写入器)定义其自己对应的监听器接口．应用程序可以实现此接口，然后将其监听器实现附加到实体．
条件和等待集合一起使用，以便应用程序同步等待事件．条件的基本使用模式包括创建条件对象，将他们附加到等待集，然后等待等待集，直到触发其中一个条件．
wait的结果告诉应用程序哪些条件被触发，允许应用程序获取相应的状态信息．

通信状态
----------

主题状态类型
^^^^^^^^^^^^^

``INCONSISTENT_TOPIC`` 状态表示尝试注册的主题已存在且具有不同的特性．

::

    struct InconsistentTopicStatus {
        long total_count;   //已报告为不一致的主题累积计数
        long total_count_change;    //上次访问以来的主题不一致累积计数
    }

订阅者状态类型
^^^^^^^^^^^^^^^

``DATA_ON_READERS`` 状态指示新数据在与订阅者关联的读取器上可用．应用程序可以调用 ``get_datareaders()`` 以获取具有可用数据的数据读取器集合．


数据读取器状态类型
^^^^^^^^^^^^^^^^^^^

``SAMPLE_REJECTED`` 状态指示由数据读取器接收的样本已被拒绝．相关的IDL如下

::

    enum SampleRejectedStatusKind {
        NOT_REJECTED,
        REJECTED_BY_INSTANCES_LIMIT,
        REJECTED_BY_SAMPLES_LIMIT,
        REJECTED_BY_SAMPLES_PER_INSTANCE_LIMIT
    };
    struct SampleRejectedStatus {
        long total_count;
        long total_count_change;
        SampleRejectedStatusKind last_reason;   //最近一次被拒绝的原因
        InstanceHandle_t last_instance_handle; //最近一次被拒绝的实例
    };

``LIVELINESS_CHANGED`` 状态表示与此数据读取器相关的数据写入器改变，相关的IDL如下

::

    struct LivelinessChangedStatus {
        long alive_count;   //表示此读取器正在读取的主题上当前处于活动状态的数据写入器总数
        long not_alive_count;
        long alive_count_change;
        long not_alive_count_change;
        InstanceHandle_t last_publication_handle;   //最后一个数据写入者句柄
    }


``REQUESTED_DEADLINE_MISSED`` 状态表示


``REQUESED_INCOMPATIBLE_QOS`` 状态表示所请求的一个或多个QoS策略值与提供的QoS策略值不兼容．


``DAT_AVAILABLE`` 状态表示样本在数据写入器上可用．

``SAMPLE_LOST`` 状态表示数据丢失，且从未被数据读取器接收


数据写入器状态类型
^^^^^^^^^^^^^^^^^^^^^


``LIVELINESS_LOST`` 状态表示任何链接的数据读取器认为此数据写入器不再活动

``OFFERED_DEADLINE_MISSED`` 数据写入器实例错过了最后时限

``PUBLICATION_MATCHED`` 表示数据读取器已被匹配或先前匹配的数据读取器已停止匹配


listener
------------

每个状态操作采用on_<status_name>(<entity>, <status_struct>)的形式

下面是将listener附加到数据读取器的示例

::

    DDS::DataReaderListener_var listener (new DataReaderListenerImpl);
    DDS::DataReader_var dr = sub->create_datareader(topic,
                    DATAREADER_QOS_DEFAULT,
                    listener,
                    DDS::DATA_AVAILABLE_STATUS);

    //使用set_listener修改, 当有可读数据或通信状态改变时调用listener操作
    dr->set_listener(lister, DDS::DATA_AVAILABLE_STATUS | DDS::LIVELINESS_CHANGED_STATUS);


- topic listener

::

    interface TopicListener : Listener {
         void on_inconsistent_topic(in Topic the_topic,
         in InconsistentTopicStatus status);
    };


- datawriter listener

::

    interface DataWriterListener : Listener {
         void on_offered_deadline_missed(in DataWriter writer,
         in OfferedDeadlineMissedStatus status);
         void on_offered_incompatible_qos(in DataWriter writer,in OfferedIncompatibleQosStatus status);
         void on_liveliness_lost(in DataWriter writer, in LivelinessLostStatus status);
         void on_publication_matched(in DataWriter writer, in PublicationMatchedStatus status);
    };


- datareader listener

::

    interface DataReaderListener : Listener {
         void on_requested_deadline_missed(in DataReader the_reader, in RequestedDeadlineMissedStatus status);
         void on_requested_incompatible_qos(in DataReader the_reader, in RequestedIncompatibleQosStatus status);
         void on_sample_rejected(in DataReader the_reader,in SampleRejectedStatus status);
         void on_liveliness_changed(in DataReader the_reader,in LivelinessChangedStatus status);
         void on_data_available(in DataReader the_reader);
         void on_subscription_matched(in DataReader the_reader,in SubscriptionMatchedStatus status);
         void on_sample_lost(in DataReader the_reader, in SampleLostStatus status);
    };


- subscriber listener

::

    interface SubscriberListener : DataReaderListener {
         void on_data_on_readers(in Subscriber the_subscriber);
    };


- participant listener

::

    interface DomainParticipantListener : TopicListener, PublisherListener, SubscriberListener {
    };



condition
------------


DDS规范定义了四种类型的条件

1) 状态条件

2) 读条件

3) 查询条件

4) 保护条件


::

    DDS::ConditionSeq active;
    DDS::Duration tm = {10, 0};
    int ret = ws->wait(active, tm);
    if(ret == DDS::RETCODE_TIMEOUT) {
        std::cout << "wait time out" << std::endl;
    } else if(ret == DDS::RETCODE_OK) {
        DDS::OfferedIncompatibleQosStatus incompatibleStatus;
        data_writer->get_offered_incompatible_qos(incompatiblesttatus);
    }
