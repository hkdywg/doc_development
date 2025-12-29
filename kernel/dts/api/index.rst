设备树操作常用API
=================

内核中用下面这个结构描述设备树中的一个节点，后面的API都需要一个device_node对象作为参数传入。

::
    
    struct device_node {
        const char *name;
        phandle phandle;
        const char *full_name;
        struct fwnode_handle fwnode;

        struct property *properties;
        struct property *deadprops;
        struct device_node *parent;
        struct device_node *child;
        struct device_node *sibling;
    #if defined(CONFIG_OF_KOBJ)
        struct kobject kobj;
    #endif 
        unsigned long _flags;
        void *data;
    #if defined(CONFIG_SPARC)
        unsigned int unique_id;
        strcut of_ifq_controller *irq_trans;
    #endif 
    };

struct device_node
    -->节点名
    -->设备类型
    -->全路径节点名
    -->父节点指针
    -->子节点指针

- 查找节点API

::

    /*
        bref 通过compatible属性查找指定节点
        from 指向开始路径的节点，如果为NULL，则从根节点开始
        type device_type设备类型，可以为NULL
        compat 指向 节点的compatible属性值(字符串)的首地址
        成功：得到节点的首地址 失败：NULL 
    */ 
    struct device_node *of_find_compatible_node(struct device_node *from, const char *type, const char *compat);

    /*
        bref 通过compatible属性查找指定节点
        from------
        matches 指向设备ID表，注意ID表必须以NULL结束
        例如
        const struct of_device_id mydemo_of_match[] = {
            {.compatible = "fs4412,mydemo"},
            {}
        };
    */
    struct device_node *of_find_matching_node(struct device_node *from,  const struct of_device_id *matches);

    //全路径查找指定节点
    struct device_node *of_find_node_by_path(const char *path);


    //通过节点名查找指定节点
    struct device_node *of_find_node_by_name(struct device_node *from, const char *name);


- 提取通用属性API

::

    /*
        提取属性的值
        np 设备节点指针
        name 属性名称
        lenp属性值字节数
        成功：属性值首地址 失败：NULL 
    */
    struct property *of_find_property(cosnt struct device_node *np,  const char *name, int *lenp);

    /*
        得到属性值中数据的数量
        np 设备节点指针
        propername 属性名称
        elem_size 每个数据的单位
        成功：属性值的数据个数 失败：负数
    */
    int of_property_count_elems_of_size(const struct device_node *np, const char *propname, int elem_size);

    /*
        得到属性值中指定标号的32位数据值
        np 设备节点指针
        propname 属性值中指定数据的标号
        out_value 输出参数，得到指定数据的值
        成功：0 失败：负数
    */
    int of_property_read_u32_index(const struct device_node *np, cosnt char *propname, u32 index, u32 *out_value);

    /*
        提取字符串(属性值)
        np 设备节点指针
        propname 属性名称
        out_string 输出参数，指向字符串(属性值)
        成功：0 失败：负数
    */
    int of_propery_read_string(struct device_node *np, cosnt char *propname, const char **out_string);


- 提取addr属性API

::

    /*
        提取默认属性"#address-cells"的值
        np 设备节点指针
        成功：地址的数量 失败：负值
    */
    int of_n_addr_cells(strcut device_node *np);

    //提取"#size-cells"的值 
    int of_n_size_cell(struct device_node *np);

    /*
        提取I/O口地址
        np 设备节点指针
        index 地址标号
        size 输出参数,I/O地址的长度
        flags 输出参数，类型(IORESOURCE——IO，IORESOURCE_MEM)
        成功：I/O地址的首地址，失败：NULL
    */
    __be32 *of_get_address(struct device_node *np, int index, u64 *size, unsigned int *flags);

    /*
        从设备树中提取I/O地址转换成物理地址
        np 设备节点指针
        in_addr 设备树提取的I/O地址
        成功：物理地址 失败：OF_BAD_ADDR
    */
    u64 of_translate_address(strcut device_node *np, cosnt __be32 *in_addr);

    /*
        提取I/O地址并映射成虚拟地址
        np-----
        index I/O地址的标号
        成功：映射好的虚拟地址，失败：NULL 
    */
    void __iomem *of_iomap(struct device_node *np, int index);

    /*
        提取I/O地址并申请I/O资源及映射成虚拟地址
        np--
        index--
        name 设备名，申请I/O地址时使用
        成功：映射好虚拟地址，失败：NULL
    */
    void __iomem *of_io_request_and_map(strcut device_node *np, int index, const char *name);


- 提取resource属性API

::

    /*
        从设备树中提取资源resource(I/O地址)
        np 设备节点指针
        index I/O 地址资源的标号
        r 输出参数，指向资源resource
        成功：0 失败：负数
    */
    int of_address_to_resource(strcut device_node *np, int index, struct resource *r);

- 提取GPIO属性API

::

    /*
        从设备树中提取GPIO口
        np---
        propname---
        index gpio口引脚标号
        成功：得到GPIO口编号 失败：负数
    */
    int of_get_named_gpio(struct device_node *np, const char *propname, int index);

- 提取irq属性API

::

    /*
        从设备树中提取中断号
        np---
        index 要提取的中断号标号
        成功：中断号 失败：负数
    */
    int of_irq_count(struct device_node *np);

- 提取MAC属性

::

    void of_get_mac_address(struct device_node *np);


驱动调用示例
------------


::

    int iic_probe(struct i2c_client *clent, const struct i2c_device_id *id)
    {
        struct device dev;
        char *string;
        unsigned int mint;
        dev = client->dev;

        of_property_read_string(dev.of_node, "string_test", &string);
        of_property_read_u32(dev.of_name, "mint", &mint);
        return 0;
    }
