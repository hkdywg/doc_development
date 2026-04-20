opendds简单示例
=======================

使用DCPS
-----------

定义数据类型
^^^^^^^^^^^^^

dds使用的每种数据类型都是使用IDL定义的，OpenDDS使用 ``#pragma`` 指令来标识dds传输和处理的数据类型．这些数据类型由 ``TAO IDL`` 和 ``OpenDDS IDL`` 编译器处理，
以生成必要的代码，以便opendds传输这些类型的数据．

::

    module Messenger {
    #pragma DCPS_DATA_TYPE "Messenger::Message"
    #pragma DCPS_DATA_KEY "Messenger::Message subject_id"
    struct Message {
            string from;
            string subject;
            long subject_id;
            string text;
            long count;
        };
    };

#pragram 标记用于opendds的数据类型，全范围型必须配合pragram使用．opendds要求数据类型是一个结构，该结构可以包含纯量类型(short, long, float等)，以及
enumerations, strings,sequences, arrays, structures,和unions．

此Opendds 范例定义了structure Messenger 在Messenger module 之中。

处理IDL
^^^^^^^^^

首先由TAO IDL编译器处理

::

    tao_idl Messager.idl

此外，我们需要使用opendds idl编译器处理IDL文件，以生成opendds需要编译和解密消息的序列化和密钥支持代码，以及data reader和data writer支持的类型代码．
此idl编译器位于 ``${DDS_ROOT}/bin`` 中，并为每个处理的IDL文件生成三个文件．这三个文件都以原始IDL文件名开头,例如运行以下命令

::

    opendds_idl Messager.idl

生成MessagerTypeSupport.idl, MessagerTypeSupportImpl.h和MessagerTypeSupportImpl.cpp,这些文件应该与使用这些消息类型的opendds应用程序链接．

一般情况下，我们不需要直接调用TAO或OpenDDS IDL编译器，使用 ``MPC`` 可以简化这个过程

- publisher和subscriber共同的MPC文件部分

::

    project(*idl): dcps {
        TypeSupport_Files {
            Messager.idl
        }
        custom_only = 1
    }

.. note::
    dcps父项目添加了类型支持自定义构建规则，上面的TypeSupport_Files部分告诉MPC使用OpenDDS IDL编译器从Messager.idl生成消息类型支持文件．


- publisher部分

::

    project(*Publisher): dcpsexe_with_tcp {
        exenme = publisher
        aafter += *idl
        TypeSupport_Files {
            Messager.idl
        }
        Source_Files {
            Publisher.cpp
        }
    }

dcpsexe_with_tcp项目链接在DCPS库中


- subscriber部分

::

    project(*Subscriber): dcpsexe_with_tcp {
        exename = subscriber
        after += *idl
        TypeSupport_Files {
            Messager.idl
        }
        Source_Files {
            Subscriber.cpp
            DataReaderListenerImpl.cpp
        }
    }


publisher
^^^^^^^^^^

- 初始化参与者

::

    int main() 
    {
        try {
            //TheParticipantFactoryWithArgs在Service_Participant.h中定义，并以命令行参数来初始化
            //Domain Participant Factory,这些参数用于初始化ORB也就是opendds服务本身
            DDS::DomainParticipantFactory_var dpf = TheParticipantFactoryWithArgs(argc, argv);
            //创建参与者,domain id范围(0x00000000 ~ 0x7FFFFFFF)
            DDS:DomainParticipant_var participant = dpf->create_participant(42, //domain ID
            PARTICIPANT_QOS_DEFAULT,
            0, //No listener required
            OpenDDS::DCPS::DEFAULT_STATUS_MASK);
        }
    }

- 注册数据类型和创建topic

::

    Messenger::MessageTypeSupport_var mts = 
        new Messenger::MessageTypeSupportImpl();
        //注册字符串数据类型
    if(DDS::RETCODE != mts->register_type(participant, "")) {
        std::cerr << "register_type failed" << std::endl;
        return -1;
    }
    CORBA::String_vaar type_name = mts->get_type_name();
    //使用默认的QOS规则创建名为test_topic的topic
    DDS::Topic_var topic = participant->create_topic("test_topic",
            type_name,
            TOPIC_QOS_DEFAULT,
            0,
            OpenDDS::DCPS::DEFAULT_STATUS_MASK);

- 创建publisher

::

    //使用默认QOS规则创建publisher
    DDS::Publisher_var pub = participant->create_publisher(PUBLISHER_QOS_DEFULT,
                            0,
                            OpenDDS::DCPS::DEFAULT_STATUS_MASK);


- 创建DataWriter并等待Subscriber

::

    DDS::DataWriter_var writer = pub->create_datawriter(topic,  //使用创建的topic
                            DATAWRITER_QOS_DEFAULT,
                            0,                                  //不需要监听
                            OpenDDS::DCPS::DEFAULT_STATUS_MASK);

    //将datawriter指向messageDataWriter
    Messenger::MessageDataWriter_var messge_writer = Messenger::MessageDataWriter::_narrow(writer);

等待用户所涉及的基本步骤是

1) 从我们创建的datawriter获取状态条件

2) 在条件中启用publication matched状态

3) 创建等待集

4) 将状态条件附加到等待集

5) 获取发布匹配状态

6) 如果匹配的当前计数为一个或多个，则从等待集中分离条件并继续发布

7) 等待等待集

::

    DDS::StatusCondition_var condition = writer->get_statuscondition();
    condition->set_enabled_statuses(DDS::PUBLICTION_MATCHED_STATUS);
    DDS::WaitSet_var ws = new DDS::WaitSet;
    ws->attach_condition(condition);
    while(true) {
        DDS::PublicationMatchedStatus matches;
        if(writer->get_publication_matched_status(matches) != DDS::RETCODE_OK)
            return -1;
        if(matches.current_count >= 1)
            break;
        DDS::ConditionSeq conditions;
        DDS::Duration_t timeout = {60, 0};
        if(ws->wait(conditions, timeout) != DDS::RETCODE_OK)
            return -2;
    }
    ws->detach_condition(conditon);

- 消息发布

::

    Messenger::Messge message;
    message.subject_id = 99;
    message.from = "ywg";
    message.subject = "review";
    message.text = "test opendds publish";
    message.count = 0;
    for(int i = 0; i < 10; i++)
    {
        DDS::ReturnCode_t error = message_writer->write(messge, DDS::HANDLE_NIL);
        ++message.count;
        ++message.subject_id;
    }


subscriber
^^^^^^^^^^^

- 初始化参与者

- 注册数据类型和创建主题

- 创建subscriber

::
    
    DDS::Subscriber_var sub = participant->create_subscriber(SUBSCRIBER_QOS_DEFAULT,
                            0,
                            OpenDDS::DCPS::DEFAULT_STATUS_MASK);

- 创建datareader和listener

::

    DDS::DataReaderListener_var listener =  new DataReaderListenerImpl;
    DDS::DataReader_var dr = sub->create_datareader(topic,
                        DAATAREADER_QOS_DEFAULT,
                        listener,
                        OpenDDS::DCPS::DEFALT_STATUS_MASK);


运行
^^^^^^^

首先需要启动 ``DCPSInfoRepo`` 服务，以便发布者和订阅者可以找到另外一个

.. note::
    如果通过将环境配置为使用RTPS发现来使用对等发现，则不需要执行此步骤. DCPSInfoRepo可执行文件位于${DDS_ROOT}/bin中

::

    ./bin/DCPSInfoRepo -o simple.ior
    #-o参数表示DCPSInfoRepo生成连接信息到simple.ior文件中,供发布者和订阅者使用

    ./subscriber -DCPSInforRepo file://simple.ior
    ./publisher -DCPSInforRepo file://simple.ior

