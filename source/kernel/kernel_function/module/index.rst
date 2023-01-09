Linux内核API之模块机制
========================

数据结构
------------

::

   struct module
   {
        /*
         * 模块当前状态，state取值有四种情况
         * MODULE_STATE_LIVE: 指示模块当前正在使用
         * MODULE_STATE_COMING: 指示模块当前正在被加载
         * MODULE_STATE_GOING: 指示模块当前正在被卸载
         * MODULE_STATE_UNFORMED, 指示模块伪被设置，未定型
        */
        enum module_state_state;
        struct list_head list;  //指向模块链表的下一个模块
        char name[MODULE_NAME_LEN]; //特定的模块名称
        ...
        /*向内核空间导出的符号*/
        const struct kernel_symbol *syms;   //指向模块的符号表，表大小为num_syms
        const unsigned long *crcs;
        unsigned int num_syms;  //模块中符号的个数
        /*内核参数*/
        struct kernel_param *kp;
        unsigned int num_kp;
        /*基于GPL-only的可移除符号*/
        unsigned int num_gpl_syms;
        const struct kernel_symbol *gpl_syms;
        const unsigned long *gpl_crcs;
        ...
        /*异常处理函数表*/
        unsigned int num_exentries;
        struct exception_table_entry *extable;
        /*指向初始化方法的函数指针*/
        int (*init)(void);
        /*模块初始化时函数的内存地址*/
        void *module_init;
        /*模块的内存起始地址*/
        void *module_core;
        /*模块目标代码的初始化部分和执行部分所占内存空间大小*/
        unsigned int init_size, core_size;
        /*init和core段中可执行代码所在内存空间的大小*/
        unsigned int init_text_size, core_text_size;
        /*模块RO区域大小，包括text+rodata两部分区域*/
        unsigned int init_ro_size, core_ro_size;
        /*基于特定体系结构的模块值*/
        struct mod_arch_specific arch;
        /*标识内核是否加入了非自由软件的模块*/
        ...
        #ifdef CONFIG_SMP
        void *percpu;   //每个CPU数据
        unsigned int percpu_size;
        #endif
        ...
        #ifdef CONFIG_MODULE_UNLOAD
        struct list_head source_list;   //所有依赖于该模块的模块
        struct list_head target_list;   //所有该模块依赖的模块
        voi (*exit)(void);
        atomic_t refcnt;    //记录模块被引用的次数
        #endif
   }




函数接口
--------------

- __module_address

__module_address函数功能描述: __module_address()根据给定的一个内存地址addr,获得该内存地址所在的模块

::

    #include <linux/module.h>

    /*
    *  addr: 表示内存地址
       return: 如果内存地址addr在某一模块的地址空间中，则返回指向该
            　 模块的结构体指针，否则返回NULL
    */
    struct module *__module_address(unsigned long addr)


测试代码

::

    int a_module(void)  //此处定义一个自己添加的内核函数
    {
        return 0;
    }

    int __init __module_address_init(void)
    {
        struct module *ret;
        unsigned long addr = (unsigned long)a_module;
        /*调用__module_address函数之前，必须禁止中断，以防止模块在执行操作期间被释放*/
        preempt_disable();
        ret = __module_address(addr);
        preempt_enable();
        if(ret != NULL) {
            printk("ret->name: %s\n", ret->name);
            printk("ret->state: %s\n", ret->state);
            printk("ret->core_size: %s\n", ret->core_size);
            printk("refs of %s is %d \n", ret->name, module_refcount(ret));

        }
        return 0;
    }

- __module_text_address

__module_text_address函数功能描述: 该函数的功能是获得一个模块指针，它要满足两个条件: addr所表示的内存地址落在该模块的代码段中

::

    #include <linux/module.h>

    /*
     * addr: 表示内存地址
       return: 返回值是一个struct module类型的指针内，如果内存地址addr在某一模块的代码段中，则返回
       　   　 指向该模块的指针
    */
    struct module *__module_text_address(unsigned long addr)


测试代码


::

    int __init __module_text_address_init(void)
    {
        unsigned long addr = (unsigned long)fun_a;  //addr为函数fun_a的入口地址
        struct module *ret;
        preempt_disable();
        ret = __module_text_address(addr);
        preempt_enable();
        if(ret != NULL) {
            printk("ret->name: %s\n", ret->name);   //输出模块名
            printk("ret->state: %d\n", ret->state); //输出模块状态
            printk("ret->core_size: %d\n", ret->core_size); //输出模块core段所占空间大小
        }
    }

- __print_symbol

__print_symbol函数功能描述:　该函数的功能与sprint_symbol的函数功能是相似的，实际上，__print_symbol函数的实现中调用了函数sprint_symbol

该函数根据一个内存中的地址address查找一个内核符号，并将该符号的基本信息，例如符号名name, 它在内核符号表中的偏移offset和大小size等信息以
格式化串fmt形式输出，而sprint_symbol函数则是将这些信息放到文本缓冲区buffer中

::

    #include <linux/kallsyms.h>

    /*
     * fmt:输出内核符号基本信息所依据的格式串
       address: 内核符号中的某一地址
    */
    void __print_symbol(const char *fmt, unsigned long address)


测试代码

::

    int __init __print_symbol_init(void)
    {
        char *fmt;
        unsigned long address;
        char *name;
        struct module *fmodule = NULL;
        
        address = (unsigned long)__builtin_return_address(0); //当前函数的返回地址
        fmt = "it is the first part, \n %s";
        __print_symbol(fmt, address);

        name = "psmouse";
        fmodule = find_module(name);    //查找模块名"psmouse"的模块
        if(fmodule != NULL) {
            printk("fmodule->name: %s\n", fmodule->name);
            address = (unsigned long)fmodule->module_core;
            fmt = "it is the second part, \n %s";
            __print_symbol(fmt, address);
        }
    }

- __symbol_get

__symbol_get函数的功能是根据给定的内核符号名symbol,获得该符号的内存地址，找到其所在的内核模块，并将该模块的引用计数加1

::

    #include <linux/module.h>

    /*
     * symbol: 字符串常量，代表内核符号名
     * return: 返回一个void类型指针，其值代表内核符号symbol的地址
    */
    void *__symbol_get(const char *symbol)


测试代码

::

    int __init __symbol_get_init(void)
    {
        const char *symbol_name;
        void *addr;

        symbol_name = "symbol_a";
        addr = __symbol_get(symbol_name);

        if(addr != NULL)
            printk("the address of %s is : %lx\n", symbol_name, (unsigned long)addr);
    }


- __symbol_put

该函数根据给定的内核符号名symbol，找到其所在的内核模块，并将该模块的引用计数减1

::

    #include <linux/module.h>

    /*
     * symbol: 字符串常量，代表内核符号名
    */
    void __symbol_put(const char *symbol)


- find_module

该函数用来获得一个指向模块的指针，他是根据给定的模块名字查找模块链表，如果找到一个与给定的模块名字相匹配的模块，则返回该模块指针

::

    #include <linux/module.h>
    /*
     * name: 表示所要查找的模块名字
     * return: 返回指向查找到的名字为name的模块
    */
    struct module *find_module(const char *name)

测试代码

::

    int __init find_module_init(void)
    {
        const char *name = "test_module";
        struct module *fmodule = find_module(name);

        if(fmodule != NULL) {
            printk("fmodule->name: %s\n", fmodule->name);
            printk("fmodule->state: %d\n", fmodule->state);
            printk("fmodule->core_size: %d\n", fmodule->core_size);
            printk("module_refcount(fmodule): %d\n", module_refcount(fmodule));
        }
    }


- find_symbol

该函数通过给定的内核符号的名字,以及其他参数查找内核符号，并返回描述该符号的结构体指针

::

    #include <linux/module.h>

    /*
     * name: 表示待查找的内核符号名字
     * owner: 二级指针，指向所查找的内核符号所属的内核模块指针，是一个输出型参数
     * crc: 二级指针，表示内核符号的crc值所在的地址，是一个输出型参数
     * gplok: 如果为真，表示内核符号所属的模块支持GPL许可
     * warn: 表示是否输出警告信息
    */
    const struct kernel_symbol *find_symbol(const char *name, struct module **owner,
                                            const unsigned long **src, bool gplok, bool warn)
    

测试代码

::

    int __init find_symbol_init(void)
    {
        const char *name = "symbol_a";
        struct kernel_symbol *ksymbol;
        struct module *owner;
        const unsigned long *crc;
        bool gplok = true;
        bool warn = true;
        ksymbol = find_symbol(name, &owner, &crc, gplok, warn);
        if(ksymbol != NULL) {
            printk("ksymbol->value: %lx\n", ksymbol->value);
            printk("ksymbol->name: %s\n", ksymbol->name);
        }
        if(owner != NULL) {
            printk("owner->name: %s\n", owner->name);
        }
    }


- module_is_live

该函数是判断模块mod是否处于活动状态

::

    #include <linux/module.h>
    /*
     * mod: 模块结构体指针，结构体中包含模块的名称，状态，所属的模块链表等
     * return: 1表示处于live
    */
    static inline int module_is_live(struct module *mod)


测试代码

::

    void __init module_is_alive_init(void)
    {
        int ret = module_is_alive(THIS_MODULE);

        if(ret == 1) {
            printk("state is live!\n");
        }
    }
