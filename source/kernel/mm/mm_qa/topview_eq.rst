内存管理顶层视角问答
==========================


- 在系统启动时，ARM Linux内核如何知道系统中有多大的内存空间？

- 在32bit Linux内核中，用户空间和内核空间的比例通常是3:1，可以修改成2:2吗？

- 物理内存页面如何添加到伙伴系统中，是一页一页添加，还是以2的几次幂来加入呢？

- 内核的一级页表存放在什么地方？二级页表又存放在什么地方？

- 用户进程的一级页表存放在什么地方？二级页表呢？

- 在ARM32系统中，页表是如何映射的？在ARM64系统中，页表又是如何映射的？

- 请简述Linux内核在理想情况下页面分配器(page allocator)是如何分配出连续物理页面的。

- 在页面分配器中，如何从分配掩码(gfp_mask)中确定可以从哪些zone中分配内存？

- 页面分配器是按照什么方向来扫描zone的？

- 为用户进程分配物理内存，分配掩码应该选用GFP_KERNEL，还是GFP_HIGHUSER_MOVABLE呢？

- slab分配器是如何分配和释放小块内存的？

- slab分配器中有一个着色的概念(cache color)，着色有什么作用？

- slab分配其中的slab对象有没有根据Per-CPU做一些优化？

- slab增长并导致大量不用的空闲对象，该如何解决？

- 请问kmalloc、vmalloc和malloc之间有什么区别以及实现上的差异？

- 使用用户态的API函数malloc()分配内存时，会马上为其分配物理内存吗？

- 假设不考虑libc的因素，malloc分配100Byte，那么实际上内核是为其分配100Byte吗？

- 假设两个用户进程打印的malloc()分配的虚拟地址是一样的，那么在内核中这两块虚拟内存是否打架了呢？

- vm_normal_page()函数返回的是什么样页面的struct page数据结构？为什么内存管理代码中需要这个函数？

- 请简述get_user_page()函数的作用和实现流程？

- 请简述follow_page()函数的作用和实现流程？

- 请简述私有映射和共享映射的区别。

- 为什么第二次调用mmap时，Linux内核没有捕捉到地址重叠并返回失败呢？

- struct page数据结构中的_count和_mapcount有什么区别？

- 匿名页面和page cache页面有什么区别？

- struct page数据结构中有一个锁，请问trylock_page()和lock_page()有什么区别？

- 在Linux 2.4.x内核中，如何从一个page找到所有映射该页面的VMA？反响映射可以带来哪些便利？

- 阅读Linux 4.0内核RMAP机制的代码，画出父子进程之间VMA、AVC、anon_vma和page等数据结构之间的关系图。

- 在Linux 2.6.34中，RMAP机制采用了新的实现，在Linux 2.6.33和之前的版本中称为旧版本RMAP机制。那么在旧版本RMAP机制中，如果父进程有1000个子进程，每个子进程都有一个VMA，这个VMA里面有1000个匿名页面，当所有的子进程的VMA同时发生写复制时会是什么情况呢？

- 当page加入lru链表中，被其他线程释放了这个page，那么lru链表如何知道这个page已经被释放了。

- kswapd内核线程何时会被唤醒？

- LRU链表如何知道page的活动频繁程度？

- kswapd按照什么原则来换出页面？

- kswapd按照什么方向来扫描zone？

- kswapd以什么标准来退出扫描LRU？

- 手持设备例如Android系统，没有swap分区或者swap文件，kswapd会扫描匿名页面LRU吗？

- swappiness的含义是什么？kswapd如何计算匿名页面和page cache之间的扫描比重？

- 当系统充斥着大量只访问一次的文件访问(use-one streaming IO)时，kswapd如何来规避这种风暴？

- 在回收page cache时，对于dirty的page cache，kswapd会马上回写吗？

- 内核有哪些页面会被kswapd写回交换分区？

- ARM32 Linux如何模拟这个Linux版本的L_PTE_YOUNG比特位呢？

- 如何理解Refault Distance算法？

- 请简述匿名页面的生命周期。在什么情况下会产生匿名页面？在什么条件下会释放匿名页面？

- KSM是基于什么原理来合并页面的？

- 在KSM机制里，合并过程中把page设置成写保护的函数write_protect_page()有这样一个判断：。这个判断的依据是什么？

- 如果多个VMA的虚拟页面同时映射了同一个匿名页面，那么此时page->index应该等于多少？

- 为什么Dirty COW小程序可以修改一个只读文件的内容？

- 在Dirty COW内存漏洞中，如果Diryt COW程序没有madviseThread线程，即只有procselfmemThread线程，能否修改foo文件的内容呢？

- 假设在内核空间获取了某个文件对应的page cache页面的struct page数据结构，而对应的VMA属性是只读，那么内核空间是否可以成功修改该文件呢？

- 如果用户进程使用只读属性(PROT_READ)来mmap映射一个文件到用户空间，然后使用memcpy来写这段内存空间，会是什么样的情况？

- 请画出内存管理中常用的数据结构的关系图，如mm_struct、vma、vaddr、page、pfn、pte、zone、paddr和pg_data等，并思考如下转换关系。

- 请画出在最糟糕的情况下分配若干个连续物理页面的流程图。

- 在Android中新添加了LMK(Low Memory Killer)，请描述LMK和OOM Killer之间的关系。

- 请描述一致性DMA映射dma_alloc_coherent()函数在AEM中是如何管理cache一致性的？

- 请描述流式DMA映射dma_map_single()函数在ARM中是如何管理cache一致性的？

- 为什么在Linux 4.8内核中要把基于zone的LRU链表机制迁移到基于Node呢？
