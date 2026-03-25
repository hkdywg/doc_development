CMA连续内存分配机制原理
==========================

在linux内存管理体系中，连续大块物理内存的分配始终是核心难点，频繁的内存分配和释放极易造成物理内存
碎片化，导致摄像头、硬件音视频编解码等外设，以及DMA传输等关键场景所需的连续内存无法被高效获取，
进而影响设备正常运行与系统性能发挥。在此背景下，连续内存分配器(CMA, Contiguous Memory Allocator)
应运而生，成为解决这一痛点的关键组件。

.. note::
    CMA并非简单的内存预留工具，其核心价值在于平衡内存复用与连续分配需求------系统启动时预留一部分
    连续物理内存，设备驱动闲置时，该区域可被伙伴系统用于分配可移动页面，提升内存利用率。当设备需要
    连续内存时，系统通过页面迁移腾出预留区域，保障需求高效满足。


当系统长时间运行时，内存的使用变得越来越复杂，内存碎片化问题逐渐凸显。内存碎片化可以分为内部碎片化
和外部碎片化。 ``内部碎片化`` 是指分配给进程的内存块中，实际使用的部分小于分配的大小，造成了内存块
内部的浪费。 ``外部碎片化`` 则是指内存中存在许多小块的空闲内存，但由于它们不连续，无法满足大块内存的分配需求.


CMA工作原理
----------------

- 内存预留机制


系统启动阶段，CMA会根据预先设定的规则，从系统的物理内存中精心挑选并预留出一块特定的物理内存区域。预留区域的大小可以
通过多种方式来确定，比如在设备树中进行定义，或者内核编译选项或者通过内核启动参数来指定。

常见的内核启动参数格式为cma=size[@start-end], 例如cma=256M@3G-4G

编译内核时可以通过编译选项 ``CONFIG_CMA_SIZE_MBYTES`` 来指定CMA区域的大小。系统启动时会通过 ``dma_contiguous_reserve`` 函数
会根据内核编译选项或者从设备树中解析出的信息，计算出CMA区域的起始地址和大小，然后通过 ``memblock`` 机制将这部分内存标记为预留状态


::

	reserved-memory {
		#address-cells = <2>;
		#size-cells = <2>;
		ranges;

		/* For Audio DSP */
		adsp_reserved: linux,adsp@57000000 {
			compatible = "shared-dma-pool";     
			reusable;   
			reg = <0x00000000 0x57000000 0x0 0x01000000>;
		};

		/* global autoconfigured region for contiguous allocations */
		linux,cma@58000000 {
			compatible = "shared-dma-pool"; //这是CMA区域在设备树中的标准标识
			reusable;  //表示该CMA区域未被大块连续内存请求占用时，可以被系统其他部分复用
			reg = <0x00000000 0x58000000 0x0 0x10000000>;   //定义了起始地址和大小
			linux,cma-default;  //标记为系统默认的CMA区域，系统中有多个CMA区域时，可以通过这种方式指定一个默认区域
		};

		/* device specific region for contiguous allocations */
		mmp_reserved: linux,multimedia@68000000 {
			compatible = "shared-dma-pool";
			reusable;
			reg = <0x00000000 0x68000000 0x0 0x04000000>;
		};
	};

- 内存迁移机制

内存迁移的触发条件主要是当普通的内存分配无法满足大块连续内存请求时，且此时CMA区域内存在被其他普通进程占用。例如，当一个
视频编码模块需要申请一块较大的连续内存来存储编码数据，而系统的普通内存由于碎片化无法提供足够大的连续内存块时，CMA机制就会介入

**具体的内存迁移过程涉及多个步骤和内核组件的协同工作**

1. 页面选择与隔离：CMA首先会根据分配请求确定需要迁移的页面范围。然后将涉及该页面范围的pageblock从buddy系统中隔离出来。在linux
内存管理中，pageblock是一个物理上连续的内存区域，包含多个页面。CMA通过将pageblock的迁移类型由 ``MIGRATE_CMA`` 变更为 ``MIGRATE_ISOLATE`` 
来实现隔离，因为buddy系统不会从MIGRATE_ISOLATE迁移类型的pageblock分配页面。

2. 页面迁移: 在隔离pageblock后，CMA会对范围内已被占用的页面进行迁移处理。这涉及到将页面中的数据从原内存位置复制到新的内存位置。
迁移过程中需要确保数据的完整性和一致性，同时要处理好页面的映射关系，保证进程对内存的访问不受影响(会涉及到更新进程的页表)。

3. 内存分配: 当页面迁移完成后，CMA区域就会出现一块连续的空闲内存空间，此时CMA就可以将这块连续内存分配给请求者。

4. 迁移后处理: 内存分配完成后，CMA还需要对迁移过程中进行一些后续处理，例如更新CMA区域的使用状态信息，包括已使用内存大小，空闲内存大小等


- CMA数据结构


::

	struct cma {
		unsigned long   base_pfn;     // CMA区域物理地址的起始页帧号
		unsigned long   count;        // CMA区域总体的页数
		unsigned long   *bitmap;      // 位图，用于描述页的分配情况
		unsigned int order_per_bit;   // 位图中每个bit描述的物理页面的order值，其中页面数为2^order值
		struct mutex    lock;         // 互斥锁，用于保护对CMA区域的访问
	#ifdef
	 CONFIG_CMA_DEBUGFS
		struct hlist_head mem_head;   // 用于调试文件系统的链表头
		spinlock_t mem_head_lock;     // 保护链表的自旋锁
	#endif
		const char *name;             // CMA区域的名称
	};

CMA提供了一系列的接口函数来实现内存的分配和释放操作，主要的分配函数是 ``dma_alloc_from_contiguous`` ,释放的函数是 ``dma_release_from_contiguous``

::

    struct page *dma_alloc_from_contiguous(struct device *dev, size_t count,
                           unsigned int align, bool no_warn)
    {
        if (align > CONFIG_CMA_ALIGNMENT)
            align = CONFIG_CMA_ALIGNMENT;

        return cma_alloc(dev_get_cma_area(dev), count, align, no_warn);

    }

    bool dma_release_from_contiguous(struct device *dev, struct page *pages,
                     int count)
    {
        return cma_release(dev_get_cma_area(dev), pages, count);

    }
