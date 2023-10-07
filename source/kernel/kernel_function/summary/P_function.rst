page_address_htable
=====================

::

    static struct page_address_slot {
        struct list_head lh;
        spinlock_t lock;
    } ___cacheline_aligned_in_smp page_address_htable[1<<PA_HASH_ORDER];


``page_address_htable`` 是一个全局变量，维护高端内存线性地址中永久映射的全局变量


page_address_init
=====================

::

    void __init page_address_init(void)
    {
        int i;

        for(i = 0; i < ARRAY_SIZE(page_address_htable); i++)
        {
            INIT_LIST_HEAD(&page_address_htable[i].lh);
            spin_lock_init(&page_address_htable[i].lock);
        }
    }

``page_address_init`` 用于初始化高端内存线性地址中永久映射的全局变量．内核使用全局数组page_address_htable维护高端内存页表池的链表，
并带一个自旋锁．



PAGE_OFFSET
==============

::

    config PAGE_OFFSET
        hex
        default PHYS_OFFSET if !MMU
        default 0x40000000 if VMSPLIT_1G
        default 0x80000000 if VMSPLIT_2G
        default 0xB0000000 if VMSPLIT_3G_OPT
        default 0xC0000000


``PAGE_OFFSET`` 宏用于指明内核空间虚拟地址的起始地址．其值与用户空间和内核空间虚拟地址划分有关，如果用于空间与内核空间按
1:3，那么内核空间虚拟地址从0x40000000开始．2:2则从0x80000000开始，3:1则从0xB0000000开始
 

__page_to_pfn
===============

::

    #define __page_to_pfn(page) ((unsigned long)((page) - mem_map) + ARCH_PFN_OFFSET)

``__page_to_pfn`` 用于将struct page转换成物理页帧号


parameq
==========

::

    bool parameq(const char *a, const char *b)
    {
        return parameqn(a, b, strlen(a) + 1);
    }

``parameq`` 用于对比a字符串是否与b字符串相等


parse_args
=============

::

    //doing: 标识符字符串
    //args: 包含启动参数的字符串
    //params: 内核参数列表
    //num: 内核参数的数量
    //unknown: 私有函数
    char *parse_args(const char *doing, char *args, const struct kernel_param *params, unsigned num,
            s16 min_level, s16 max_level, void *arg, int(*unknown)(char *param, char *val, const char *doing, void *arg))
    {
        char *param, *val, *err = NULL;

        //将args参数开始处的空格去掉
        args = skip_spaces(args);

        while(*args)
        {
            int ret;
            int irq_was_disabled;

            //从args字符串中获得一个参数的名字，并将其存储到param里，值存储在val中
            args = next_arg(args, &param, &val);
            if(!val && strcmp(param, "--") == 0)
                return err ? : args;
            //判断当前中断是否使能
            irq_was_disabled = irqs_disabled();
            //在内核参数中找到与参数名字相同的内核参数，并将内核参数的值设置成val的值
            ret = parse_one(param, val, doing, params, num, min_level, max_level, arg, unknown);
            if(irq_was_disabled && !irqs_disabled())
                pr_warn("%s: option '%s' enabled irq!\n", doing, param);

            swtich(ret)
            {
            case 9:
                continue;
            case -ENOENT:
                pr_err("%s: Unknown parameter '%s'\n", doing, param);
                break;
            case -ENOSPC:
                pr_err("%s: '%s' to large for paramters '%s'\n", doing, val ?:"", param);
                break;
            default:
                pr_err("%s: '%s' invalid for paramter '%s'\n", doing, val ?:"", param);
                break;
            }
            err = ERR_PTR(ret);
        }

        return err;
    }

``parse_args`` 用于从一个字符串中解析参数，并设置对应的内核参数


parse_early_options
======================

::

    void __init parse_early_options(char *cmdline)
    {
        parse_args("early options", cmdline, NULL, 0, 0, 0, NULL, do_early_param);
    }

``parse_early_options`` 用于初始化cmdline内早期启动参数


parse_early_param
====================

::

    void __init parse_early_param(void)
    {
        static int done __initdata;
        static char tmp_cmdline[COMMAND_LINE_SIZE] __initdata;

        if(done)
            return;

        strcpy(tmp_cmdline, boot_command_line, COMMAND_LINE_SIZE);
        parse_early_options(tmp_cmdline);
        done = 1;
    }

``parse_early_param`` 用于系统启动早期，设置指定的启动参数.函数定义了两个静态变量，函数首先判断done的值，以防止该函数被二次执行


parse_one
=============

::

    static int parse_one(char *param, char *val, const char *doing, const struct kernel_param *params,
        unsigned num_params, s16 min_level, s16 max_level, void *arg, int (*handle_unknown)(char *param, char *val, const char *doing, void *arg))
    {
        unsigned int i;
        int err;

        for(i = 0; i < num_params; i++) {
            //找到与参数param相同的kernel_param
            if(parameq(param, params[i].name)) {
                //检查kernel_param中成员进行检测
                if(params[i].level < min_level || param[i].level > max_level)
                    return 0;
                if(!val  && !(params[i].ops->flags & KERNEL_PARAM_OPS_FL_NOARG))
                    return -EINVAL;
                kernel_param_lock(params[i].mod);
                param_check_unsafe(&params[i]);
                //执行kernel_param中包含的set函数，该函数就是用cmdline中参数设置内核中启动的参数
                err = params[i].ops->set(val, &params[i]);
                kernel_param_unlock(params[i].mod);
                return err;
            }
        }

        //执行handle_unknown函数
        if(handle_unknown)
            return handle_unknown(param, val, doing, arg);

        return -ENOENT;
    }


``parse_one`` 用于解析cmdline里面的一个参数，并在内核启动过程中设置这个内核参数

.. note::
    内核将所有启动参数的钩子函数存放在"__param" section里，在这个section中，每个成员按struct kernel_param
    格式存储．


__per_cpu_offset
===================

::

    unsigned long __per_cpu_offset[NR_CPUS] __read_mostly;
    EXPORT_SYMBOL(__per_cpu_offset)


per_cpu_offset
==================

::

    #ifndef __per_cpu_offset
    extern unsigned long __per_cpu_offset[NR_CPUS];
    #define per_cpu_offset(x) (__per_cpu_offset[x])
    #endif

``per_cpu_offset`` 用于获得特定CPU在__per_cpu_offset[]数组中的偏移


PFN_DOWN
==========

::

    #define PFN_DOWN(x) ((x) >> PAGE_OFFSET)


PFN_PHYS
=============

::

    #define PFN_PHYS(x) ((phys_addr_t)(x) << PAGE_SHITF)

``PFN_PHYS`` 将物理页帧转换为物理地址．参数x指向物理页帧号


pfn_pte
==========

::

    #define pfn_pte(pfn, prot)  __pte(__pfn_to_phys(pfn) | pgprot_val(prot))
    #define __pfn_to_phys(pfn) PFN_PHYS(pfn)
    #define pgrpot_val(x) ((x).pgprot)


``pfn_pte`` 用于制作一个PTE入口项


PFN_UP
========

::

    #define PFN_UP(x) (((x) + PAGE_SIZE - 1) >> PAGE_SHIFT)

``PFN_UP`` 将参数x对应的下一个页帧号


PHYS_OFFSET
==============

::

    config PHYS_OFFSET
        hex "Physical address of main memory" if MMU
        depends on !ARM_PATCH_PHYS_VIRT
        default DRAM_BASE if !MMU
        default 0x00000000 if ARCH_EBSA110 || \
            ARCH_ROOTBRIDGE || ARCH_INTEGRATOR || ARCH_IOP13XX || \
            ARCH_KS8695 || ARCH_REALVIEW
        default 0x10000000 if ARCH_OMAP1 || ARCH_RPC
        default 0x20000000 if ARCH_S5PV210
        default 0xc0000000 if ARCH_SA1100
        help 
            Please provide the physical address corresponding to the localtion of main memory in your system


``PHYS_OFFSET`` 用于指明DRAM在地址总线上的偏移．其定义在"arch/arm/Kconfig"





PHYS_PFN
=============

::

    #define PHYS_PFN(x) ((unsigned long)((x) >> PAGE_SHIFT))

``PHYS_PFN`` 用于将物理地址转换成物理页帧号


__phys_to_pfn
==================

::

    #define __phys_to_pfn(paddr) PHYS_PFN(paddr)


__phys_to_virt
=================

::

   #define __fix_to_virt(x)     (FIXADDR_TOP - ((x) << PAGE_SHIFT)) 


``__fix_to_virt`` 用于FIXMAP索引获得对应的虚拟地址 


phys_to_virt
==============

::

    static inline void *phys_to_virt(phys_addr_t x)
    {
        return (void *)__phys_to_virt(x);
    }


pgd_addr_end
=================

::

    #define pgd_addr_end(addr, end)         \
    ({  unsigned long __boundary = ((addr) + PGDIR_SIZE) & PGDIR_MASK;  \
        (__boundary - 1 < (end) - 1) ? __boundary : (end);  \
    })

``pgd_addr_end`` 用于获得addr下一个PGDIR_SIZE地址


pgd_index
=============

::

    #define pgd_index(addr) ((addr) >> PGDIR_SHIFT)

``pgd_index`` 用于获得虚拟地址x在页目录中的索引


- 例如二级页表的32位地址上，页目录和页表的布局如下

::
    
    2-level Page Table

    32                        22                      12                      0
    +-------------------------+------------------------+----------------------+
    |     Directory           |        Table           |       Offset         |
    +-------------------------+------------------------+----------------------+
                              |  <------------ PGDIR_SHIFT -----------------> |
                                                       | <---PAGE_SHIFT-----> |
pgd_offset
=============

::

    #define pgd_offset(mm, addr)    ((mm)->pgd + pgd_index(addr))

``pgd_offset`` 用于获得虚拟地址对应的页目录内容


- 例如在二级页表中，页目录索引与进程页目录的关系如下图

::


    2-level Page Table

    32                        22                      12                      0
    +-------------------------+------------------------+----------------------+
    |     Directory           |        Table           |       Offset         |
    +-------------------------+------------------------+----------------------+
              |               |  <------------ PGDIR_SHIFT -----------------> |
              |                                        | <---PAGE_SHIFT-----> |
              |
              |
              |
              |
              |
              |
              |             +--------------+
              |             |              |
              |             +--------------+
              |             |              |
              o------------>+--------------+
                            |              |
                            +--------------+
                            |              |
                            +--------------+
                            |              |
                            +--------------+
                            |              |
                            +--------------+
                            |              |
                            +--------------+
                            |              |
                            +--------------+
                            |              |
                            +--------------+
                            |              |
  task_struct->mm->pgd----->+--------------+



pgd_offset_k
===============

::

    #deinf pgd_offset_k(addr)   pgd_offset(&init_mm, addr)


``pgd_offset_k`` 用于获得内核空间虚拟地址对应的页目录入口地址


- 例如在二级页表中，内核虚拟地址对应的页目录关系如下

::


    2-level Page Table

    32                        22                      12                      0
    +-------------------------+------------------------+----------------------+
    |     Directory           |        Table           |       Offset         |
    +-------------------------+------------------------+----------------------+
              |               |  <------------ PGDIR_SHIFT -----------------> |
              |                                        | <---PAGE_SHIFT-----> |
              |
              |
              |
              |
              |
              |
              |             +--------------+
              |             |              |
              |             +--------------+
              |             |              |
              o------------>+--------------+
                            |              |
                            +--------------+
                            |              |
                            +--------------+
                            |              |
                            +--------------+
                            |              |
                            +--------------+
                            |              |
                            +--------------+
                            |              |
                            +--------------+
                            |              |
                            +--------------+
                            |              |
          init_mm->pgd----->+--------------+



pgdat_end_pfn
=================

::

    static inline unsigned long pgdat_end_pfn(pg_data_t *pgdat)
    {
        return pgdat->node_start_pfn + pgdata->node_spanned_pages;
    }

``pgdat_end_pfn`` 用于获得pglist指向的结束页帧号．函数通过从pglist结构中获得起始页帧加上横跨页帧的数量，以此获得结束页帧号


__pgprot
=============

::

    #define __pgprot(x) ((pgprot_t) { (x) })



pgrot_val
===============

::

    #define pgrot_val(x)    ((x).pgprot)

``pgrot_val`` 用于获得PTE入口标志


pmd_addr_end
================

::

    #define pmd_addr_end(addr, end)     \
    ({  unsigned long __boundary = ((addr) + PMD_SIZE) & PMD_MASK;  \
        (__boundary - 1 < (end) - 1) ? __boundary: (end);   \
    })

``pmd_addr_end`` 用于获得addr下一个PMD_SIZE地址


pmd_bad
==========

::

    #define pmd_bad(pmd)    (pmd_val(pmd) & 2)

``pmd_bad`` 判断PMD入口项是否有效

pmd_clear
============

::

    #define pmd_clear(pmdp) \
    do {    \
        pmdp[0] = __pmd(0); \
        pmdp[1] = __pmd(0); \
        clean_pmd_entry(pmdp);  \
    } while(0)


``pmd_clear`` 用于清除一个PMD入口项

pmd_empty_section_gap
========================

::

    static void __init pmd_empty_section_gap(unsigned long addr)
    {
        vm_reserve_area_early(addr, SECTION_SIZE, pmd_empty_section_gap);
    }

    void __init vm_reserve_area_early(unsigned long addr, unsigned long size, void *caller)
    {
        struct vm_struct *vm;
        struct static_vm *svm;

        svm = early_alloc_aligned(sizeof(*svm), __alignof__(*svm));

        vm = &svm->vm;
        vm->addr = (void *)addr;
        vm->size = size;
        vm->flags = VM_IOREMAP | VM_ARM_EMPTY_MAPPING;
        vm->caller = caller;
        add_static_vm_early(svm);
    }

``pmd_empty_section_gap`` 将addr对应的虚拟空间加入到系统静态映射中预留区


pmd_none
=========

::

    #define pmd_none(pmd)   (!pmd_val(pmd))


``pmd_none`` 判断PMD入口项是否为空. 函数通过pmd_val函数读取PMD入口项的值，如果值为0，那么返回true,表示PMD入口项为空


pmd_off_k
===========

::

    static inline pmd_t *pmd_off_k(unsigned long virt)
    {
        return pmd_offset(pud_offset(pgd_offset_k(virt), virt), virt);
    }

``pmd_off_k`` 用于获得内核虚拟地址对应的PMD入口


pmd_offset
=============

::

    static inline pmd_t *pmd_offset(pud_t *pud, unsigned long address)
    {
        return (pmd_t *)pud;
    }

``pmd_offset`` 用于从PUD页表中获得PMD入口地址


pmd_page_vaddr
=================

::

    static inline pte_t *pmd_page_vaddr(pmd_t pmd)
    {
        return __va(pmd_val(pmd) & PHYS_MASK & (s32)PAGE_MASK);
    }

``pmd_page_vaddr`` 用于获得PMD入口对应的PTE页表基地址


__pmd_populate
=================

::

    static inline void __pmd_populate(pmd_t *pmdp, phys_addr_t pte, pmdval_t prot)
    {
        pmdval_t pmdval =  (pte + PTE_HWTABLE_OFF) | port;
        pmdp[0] = __pmd(pmdval);
    #ifndef CONFIG_ARM_LPAE
        pmdp[1] = __pmd(pmdval + 256 * sizeof(pte_t));
    #endif
        flush_pmd_entry(pmdp);
    }

``__pmd_populate`` 向指定的PMD入口填充PTE页表的物理地址与标志



pmd_populate_kernel
=====================

::

    static inline void pmd_populate_kernel(struct mm_struct *mm, pmd_t *pmdp, pte_t *ptep)
    {
        __pmd_populate(pmdp, __pa(ptep), _PAGE_KERNEL_TABLE);
    }

``pmd_populate_kernel`` 是为内核PMD入口填充PTE页表信息


pmd_val
==========

::

    #define pmd_val(x)  ((x).pmd)


populate_zone
=================

::

    static inline bool populate_zone(struct zone *zone)
    {
        return zone->present_pages;
    }

``populate_zone`` 用于判断ZONE是否已经包含物理内存


prepare_page_table
====================

::

    static inline void prepare_page_table(void)
    {
        unsigned long addr;
        phys_addr_t end;

        for(addr = 0; addr < MODULES_VADDR; addr += PMD_SIZE)
            pmd_clear(pmd_off_k(addr));

    #ifdef CONFIG_XIP_KERNEL
        addr = ((unsigned long)_exiprom + PMD_SIZE - 1) & PMD_MASK;
    #endif
        
        for( ; addr < PAGE_OFFSET; addr += PMD_SIZE)
            pmd_clear(pmd_offset_k(addr));

        end = memblock.memory.regions[0].base + memblock.memory.regions[0].size;
        if(end >= arm_lowmem_limit)
            end = arm_lowmem_limit;

        for(addr = __phys_to_virt(end); addr < VMALLOC_START; addr += PMD_SIZE)
            pmd_clear(pmd_off_k(addr));
    }


``prepare_page_table`` 函数的作用是建立页表之前，清除未使用的页表．函数分别找了三段虚拟地址，分别为

- 0地址到MODULE_VADDR

- MODULE_VADDR到PAGE_OFFSET

- 第一块DRM大于arm_lowmem_limit部分

对这三段地址分别使用pmd_off_k计算出pmd入口之后，使用pmd_clear将pmd项清除，并刷新TLB和Cache

