socket概述
=============

socket主要分为 ``流式套接字SOCK_STREAM`` 和 ``数据报套接字SOCK_DGRAM`` . SOCK_STREAM是一种可靠的，双向的有序的通讯流，对应使用的是TCP协议．SOCK_DGRAM是
不可靠的，无序的通讯流，对应使用的UDP协议

基本的编程接口有: socket, bind, listen, accept, connect, send, recv等

socket函数接口
---------------

- 创建通信套接字:socket

socket函数创建一个通信的端点，并返回一个指向该端点的文件描述符(linux下一切皆是文件)

::

    #include <sys/types.h>
    #include <sys/socket.h>

    /*
     * domain: 通信协议簇，例如AF_INET, AF_UNIX...
     * type: SOCK_STREAM, SOCK_DGRAM
     * protocal: 通常为0
     * return: 成功返回文件描述符，失败返回-1,并设置erron
     */
    int socket(int domain, int type, int protocol);

例如服务器端创建一个用于接收客户端连接的socket代码

::

    int server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if(-1 == server_fd) {
        perror("socket");
        exit(-1);
    }

- 分配套接字名称: bind

当用socket函数创建套接字后，并没有为它分配IP地址和端口，我们还需要bind函数来将指定的IP和端口号分配给已经创建的socket

::

    #include <sys/types.h>
    #include <sys/socket.h>

    /*
     * sockfd: socket 返回的文件描述符
     * addr: 含有要绑定的IP和端口的地址结构体指针
     * addrlen: 第二个参数的大小，使用sizeof来计算
     * return: 成功返回0, 失败返回-1,并设置erron
     */
    int bind(int sockfd, const struct sockaddr *addr, socklen_t addrlen);

.. note::
    第二个参数需要注意，参数指定的是struct sockaddr \*类型，一般不直接使用这个结构体，这个类型在linux上有需要的变种，例如sockaddr_in和sockaddr_un,
    经常使用后面这两个结构定义IP和端口，然后强制转换

::

    // struct sockaddr_un myaddr;
    struct sockaddr_in myaddr;
    myaddr.sin_family = AF_INET;
    //接受任何IP的连接
    myaddr.sin_add.s_addr = htonl(INADDR_ANY);
    myaddr.sin_port = htons(8080);
    if(bind(server_fd, (struct sockaddr*)&myaddr, sizeof(sockaddr_in)) == -1) {
        perror("bind");
        exit(-1);
    }


- 开始监听: listen

使用listen来建立一个监听客户端连接的队列

::

    #include <sys/types.h>
    #include <sys/socket.h>

    /*
     * sockfd: 监听的socket描述符
     * backlog: 建立的最大连接数
     * return: 成功返回0, 失败返回-1,并设置erron
    */
    int listen(int sockfd, int backlog);

例如创建一个可以监听10个客户端连接请求的队列

::

    if(listen(server_fd, 10) == -1) {
        perror("listen");
        exit(-1);
    }


- 接收连接请求: accept

网络编程的核心异步就是建立客户端和服务器端的连接，使用accept来建立两者的连接

::

    #include <sys/types.h>
    #include <sys/socket.h>

    /*
     * sockfd: 已经创建的本地正在监听的socket
     * addr: 保存连接的客户端的地址信息
     * addrlen: sockaddr的长度指针
     * return: 成功返回客户端的socket文件描述符，失败返回-1,并设置erron
    */
    int accept(int sockfd, struct sockaddr *addr, socklen_t *addrlen);

后面两个参数需要定义，但是不需要初始化，在连接成功后客户端的socket信息会自动填入

::

    struct sockaddr_in clientaddr;
    int clientaddr_len = sizeof(clientaddr);

    int client_fd = accept(server_fd, (struct sockaddr *)&clientaddr, &clientaddr_len);
    if(client_fd == -1) {
        perror("accept");
        exit(-1);
    }


- 发送数据: send, sendto

在建立连接后，当然要发送数据，既然socket也是文件，发送数据其实就是写文件，我们使用send函数来发送socket数据

::

    #include <sys/types.h>
    #include <sys/socket.h>

    /*
     * sockfd: 接收数据的socket
     * buf: 要发送的上数据
     * len: 数据长度
     * flags: 当这个参数为0,该函数等价与write
     * return: 成功返回发送的字节数，失败返回-1,并设置erron
    */
    ssize_t send(int sockfd, const void *buf, size_t len, int flags);

    /* sendto 功能是将数据发送到指定的地址dest_addr, 其他参数基本相同 */
    ssize_t sendto(int sockfd, const void *buf, size_t len, int flags,
                    const struct sockaddr *dest_addr, socklen_t addrlen);


例如服务器在建立连接后发送一个字符串到客户端:

::

    char msg[] = "Hello Client...";
    send(client_fd, msg, strlen(msg), 0);
    sendto(client_fd, msg, strlen(msg), 0, (struct sockaddr*)&dst_addr, sizeof(dest_addr));


- 接收数据:recv, recvfrom

既然有发送数据，必然有接收数据的函数，与send类似, recv的功能也跟 read几乎相同

::

    #include <sys/types.h>
    #include <sys/socket.h>

    /*
     * sockfd: 接收的socket fd
     * buf: 接收缓冲区
     * len: 缓冲区长度
     * flags: 当这个参数为0, 该函数等价为readd
     * return: 成功返回接收的字节数，失败返回-1,并设置erron
    */
    ssize_t recv(int sockfd, void *buf, size_t len, int flags);
    sszie_t recvfrom(int sockfd, void *buf, size_t len, int flags, 
                        struct sockaddr *src_addr, socklen_t *addr);

例如接收服务器发送的字符串

::

    char msg_buf[100] = {0x55};
    recv(server_fd, msg_buf, 100, 0);

    int srcaddr_len = sizeof(src_addr);
    recvfrom(server_fd, msg_buf, 100, 0, (struct sockaddr*)&src_addr, &srcaddr_len);



