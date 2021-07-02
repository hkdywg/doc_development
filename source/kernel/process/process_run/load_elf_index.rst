elf文件加载过程
===============

从编译链接和运行的角度看,应用程序和库程序的连接有两种方式

一种是固定的、静态的连接,就是把需要用到的库函数的目标代码从程序库中抽取出来,链接进应用软件的目标映像中

另一种是动态链接,是指库函数的代码并不进入应用软件的目标印象,应用软件在编译链接阶段并不完成跟库函数的链接,而是把库函数的映像也交给用户,
到启动应用程序时才把程序库的印象也装入用户空间(并加以定位),再完成应用软件和库函数的链接

装入/启动elf映像必须由内核完成,而动态连接的实现则既可以在内核中完成,也可以在用户空间完成。GNU把对于动态链接的工作做了以下分工

1) elf载入和启动在内核中完成

2) 动态链接的实现则放在用户空间(glibc),并为此提供了一个称为"解释器"(ld-linux.so.2)工具软件，而解释器的载入启动是由内核负责


linux 可执行文件类型的注册机制
------------------------------

.. note::

    - 为什么linux可以运行elf文件
    内核对所支持的每种可执行程序类型都有一个struct linux_binfmt的数据结构,其定义如下

::

    /*
     * This structure defines the functions that are used to load the binary formats that
     * linux accepts.
     */
    struct linux_binfmt {
        struct list_head lh;
        struct module *module;
        int (*load_binary)(struct linux_binprm *); //通过读存放在可执行文件中的信息为当前进程建立一个新的执行环境
        int (*load_shlib)(struct file *);       //用于动态的把一个共享库捆绑到一个已经运行的进程,这是由uselib()系统调用激活的
        int (*core_dump)(struct coredump_params *cprm);     //core dump时执行
        unsigned long min_coredump;	/* minimal dump size */
    } __randomize_layout;

所有的linux_binfmt对象都处于一个链表中,可以通过 ``register_binfmt()`` 和 ``unregister_binfmt()`` 函数在链表中插入和删除元素,系统启动期间,为每个编译进
内核的可执行格式都执行register_binfmt函数.当我们执行一个可执行程序时，内核会list_for_each_entry遍历所有注册linux_binfmt对象,对其调用Load_binary函数来
尝试加载

::

    static struct linux_binfmt elf_format = {
        .module		= THIS_MODULE,
        .load_binary	= load_elf_binary,
        .load_shlib	= load_elf_library,
        .core_dump	= elf_core_dump,
        .min_coredump	= ELF_EXEC_PAGESIZE,
    };


内核空间的加载过程load_elf_binary
---------------------------------

内核中实际执行execv()或execve()系统调用的程序是do_execve(),这个函数会首先打开目标文件,并从文件的头部读入若干字节(目前是128)，然后调用另外一个函数
search_binary_handler(),在此函数里面,它会搜索上面提到的linux支持的可执行文件类型队列,让各种可执行程序的处理程序前来认领和处理,如果类型匹配,则调用load_binary函数

在elf文件格式中,处理函数就是load_elf_binary,其流程如下

1) 填充并检查目标程序elf头部

2) load_elf_phdrs加载目标程序的程序头表

3) 如果需要动态链接,则寻找和处理解释器段

4) 检查并读取解释器的程序表头

5) 装入目标程序的段segment

6) 填写程序的入口地址

7) create_elf_tables填写目标文件的参数环境变量等必要信息

8) start_kernel宏准备进入新的程序入口


load_elf_binary函数位于 fs/binfmt_elf.c中

- 填充并检查目标程序elf头部

::

	int executable_stack = EXSTACK_DEFAULT;
	struct {
		struct elfhdr elf_ex;
		struct elfhdr interp_elf_ex;
	} *loc;
	struct arch_elf_state arch_state = INIT_ARCH_ELF_STATE;
	struct pt_regs *regs;

	loc = kmalloc(sizeof(*loc), GFP_KERNEL);
	if (!loc) {
		retval = -ENOMEM;
		goto out_ret;
	}
	
	/* Get the exec-header */
	loc->elf_ex = *((struct elfhdr *)bprm->buf);
    //在load_elf_binary之前,内核已经使用映像文件的前128字节对bprm->buf进行了填充

	retval = -ENOEXEC;
	if (memcmp(loc->elf_ex.e_ident, ELFMAG, SELFMAG) != 0)
		goto out;

    //#define	ELFMAG		"\177ELF"
    //比较文件头的前4个字节

	if (loc->elf_ex.e_type != ET_EXEC && loc->elf_ex.e_type != ET_DYN)
		goto out;
    //检查文件类型是是否是ET_EXEC或者EX_DYN
	if (!elf_check_arch(&loc->elf_ex))
		goto out;
	if (elf_check_fdpic(&loc->elf_ex))
		goto out;
	if (!bprm->file->f_op->mmap)
		goto out;


- load_elf_phdrs加载目标文件的程序头表

::

	elf_phdata = load_elf_phdrs(&loc->elf_ex, bprm->file);
	if (!elf_phdata)
		goto out;

而这个load_elf_phdrs函数就是通过Kernel_read读入整个program header table,从函数代码中可以看到,一个可执行程序必须至少有一个段(segment),而所有段的大小之和不能超过64k

::

    /**
     * load_elf_phdrs() - load ELF program headers
     * @elf_ex:   ELF header of the binary whose program headers should be loaded
     * @elf_file: the opened ELF binary file
     *
     * Loads ELF program headers from the binary file elf_file, which has the ELF
     * header pointed to by elf_ex, into a newly allocated array. The caller is
     * responsible for freeing the allocated data. Returns an ERR_PTR upon failure.
     */
    static struct elf_phdr *load_elf_phdrs(const struct elfhdr *elf_ex,
                           struct file *elf_file)
    {
        struct elf_phdr *elf_phdata = NULL;
        int retval, err = -1;
        loff_t pos = elf_ex->e_phoff;
        unsigned int size;

        /*
         * If the size of this structure has changed, then punt, since
         * we will be doing the wrong thing.
         */
        if (elf_ex->e_phentsize != sizeof(struct elf_phdr))
            goto out;

        /* Sanity check the number of program headers... */
        /* ...and their total size. */
        size = sizeof(struct elf_phdr) * elf_ex->e_phnum;
        if (size == 0 || size > 65536 || size > ELF_MIN_ALIGN)
            goto out;

        elf_phdata = kmalloc(size, GFP_KERNEL);
        if (!elf_phdata)
            goto out;

        /* Read in the program headers */
        retval = kernel_read(elf_file, elf_phdata, size, &pos);
        if (retval != size) {
            err = (retval < 0) ? retval : -EIO;
            goto out;
        }

        /* Success! */
        err = 0;
    out:
        if (err) {
            kfree(elf_phdata);
            elf_phdata = NULL;
        }
        return elf_phdata;
    }


- 如果需要动态链接,则寻找和处理解释器段

::

	for (i = 0; i < loc->elf_ex.e_phnum; i++, elf_ppnt++) {
		char *elf_interpreter;
		loff_t pos;

        //检查是否有需要加载的解释器，解释器段的类型为"PT_INTERP"
		if (elf_ppnt->p_type != PT_INTERP)
			continue;

		/*
		 * This is the program interpreter used for shared libraries -
		 * for now assume that this is an a.out format binary.
		 */
		retval = -ENOEXEC;
		if (elf_ppnt->p_filesz > PATH_MAX || elf_ppnt->p_filesz < 2)
			goto out_free_ph;

		retval = -ENOMEM;
		elf_interpreter = kmalloc(elf_ppnt->p_filesz, GFP_KERNEL);
		if (!elf_interpreter)
			goto out_free_ph;

		pos = elf_ppnt->p_offset;
        //根据其位置的p_offset和大小p_filesz把整个解释器段的内容读入缓冲区
		retval = kernel_read(bprm->file, elf_interpreter,
				     elf_ppnt->p_filesz, &pos);
		if (retval != elf_ppnt->p_filesz) {
			if (retval >= 0)
				retval = -EIO;
			goto out_free_interp;
		}
		/* make sure path is NULL terminated */
		retval = -ENOEXEC;
		if (elf_interpreter[elf_ppnt->p_filesz - 1] != '\0')
			goto out_free_interp;

        //通过open_exec()打开解释器文件
		interpreter = open_exec(elf_interpreter);
		kfree(elf_interpreter);
		retval = PTR_ERR(interpreter);
		if (IS_ERR(interpreter))
			goto out_free_ph;

		/*
		 * If the binary is not readable then enforce mm->dumpable = 0
		 * regardless of the interpreter's permissions.
		 */
		would_dump(bprm, interpreter);

		/* Get the exec headers */
		pos = 0;
        //读取解释器的前128字节,即解释器映像的头部
		retval = kernel_read(interpreter, &loc->interp_elf_ex,
				     sizeof(loc->interp_elf_ex), &pos);
		if (retval != sizeof(loc->interp_elf_ex)) {
			if (retval >= 0)
				retval = -EIO;
			goto out_free_dentry;
		}

		break;

out_free_interp:
		kfree(elf_interpreter);
		goto out_free_ph;
	}

可以使用readelf -l查看program headers,其中的INTERP段标识了我们程序所需要的解释器

解释器段实际上只是一个字符串,即解释器的文件名,如"/lib/ld-linux.so.2"或者64位机器上对应的叫做"lib64/ld-linux-x886-64.so.2"

- 检查并读取解释器的程序表头

如果需要加载解释器,前面经过一趟for循环已经找到需要的解释器信息elf_interpreter,它也是当作一个elf文件,因此跟目标可执行程序一样,我们需要
load_elf_phdrs加载解释器的程序头表 program header table

::

	/* Some simple consistency checks for the interpreter */
    //检查解释器头的信息
	if (interpreter) {
		retval = -ELIBBAD;
		/* Not an ELF interpreter */
		if (memcmp(loc->interp_elf_ex.e_ident, ELFMAG, SELFMAG) != 0)
			goto out_free_dentry;
		/* Verify the interpreter has a valid arch */
		if (!elf_check_arch(&loc->interp_elf_ex) ||
		    elf_check_fdpic(&loc->interp_elf_ex))
			goto out_free_dentry;

		/* Load the interpreter program headers */
        //读入解释器的程序头
		interp_elf_phdata = load_elf_phdrs(&loc->interp_elf_ex,
						   interpreter);
		if (!interp_elf_phdata)
			goto out_free_dentry;


至此我们已经把目标执行程序和其所需要的解释器都加载初始化,并完成检查工作,也加载了程序头表,下面开始加载程序的段信息


- 装入目标程序的段segment

这段代码从目标文件的程序头中所搜类型位PT_LOAD的段(segment)。在二进制映像中只有PT_LOAD的段才是需要装入的,当然在装入之前需要确定装入的地址,只要考虑
的就是页面对齐还有该段的p_vaddr域的值.确定了装入地址后,就通过elf_map()建立用户空间虚拟地址空间与目标映像文件中某个连续区间之间的映射,其返回值就是
实际映射的起始地址

::


	/* Now we do a little grungy work by mmapping the ELF image into
	   the correct location in memory. */
	for(i = 0, elf_ppnt = elf_phdata;
	    i < loc->elf_ex.e_phnum; i++, elf_ppnt++) {
		int elf_prot, elf_flags;
		unsigned long k, vaddr;
		unsigned long total_size = 0;

        //搜索PT_LOAD段,这个是需要装入的
		if (elf_ppnt->p_type != PT_LOAD)
			continue;

		if (unlikely (elf_brk > elf_bss)) {
			unsigned long nbyte;
	            
			/* There was a PT_LOAD segment with p_memsz > p_filesz
			   before this one. Map anonymous pages, if needed,
			   and clear the area.  */
			retval = set_brk(elf_bss + load_bias,
					 elf_brk + load_bias,
					 bss_prot);
			if (retval)
				goto out_free_dentry;
			nbyte = ELF_PAGEOFFSET(elf_bss);
			if (nbyte) {
				nbyte = ELF_MIN_ALIGN - nbyte;
				if (nbyte > elf_brk - elf_bss)
					nbyte = elf_brk - elf_bss;
				if (clear_user((void __user *)elf_bss +
							load_bias, nbyte)) {
					/*
					 * This bss-zeroing can fail if the ELF
					 * file specifies odd protections. So
					 * we don't check the return value
					 */
				}
			}
		}

		elf_prot = make_prot(elf_ppnt->p_flags);

		elf_flags = MAP_PRIVATE | MAP_DENYWRITE | MAP_EXECUTABLE;

		vaddr = elf_ppnt->p_vaddr;
		/*
		 * If we are loading ET_EXEC or we have already performed
		 * the ET_DYN load_addr calculations, proceed normally.
		 */
		if (loc->elf_ex.e_type == ET_EXEC || load_addr_set) {
			elf_flags |= MAP_FIXED;
		} else if (loc->elf_ex.e_type == ET_DYN) {
			if (interpreter) {
				load_bias = ELF_ET_DYN_BASE;
				if (current->flags & PF_RANDOMIZE)
					load_bias += arch_mmap_rnd();
				elf_flags |= MAP_FIXED;
			} else
				load_bias = 0;

			/*
			 * Since load_bias is used for all subsequent loading
			 * calculations, we must lower it by the first vaddr
			 * so that the remaining calculations based on the
			 * ELF vaddrs will be correctly offset. The result
			 * is then page aligned.
			 */
			load_bias = ELF_PAGESTART(load_bias - vaddr);

			total_size = total_mapping_size(elf_phdata,
							loc->elf_ex.e_phnum);
			if (!total_size) {
				retval = -EINVAL;
				goto out_free_dentry;
			}
		}
        //虚拟地址空间和目标文件的映射
		error = elf_map(bprm->file, load_bias + vaddr, elf_ppnt,
				elf_prot, elf_flags, total_size);
		if (BAD_ADDR(error)) {
			retval = IS_ERR((void *)error) ?
				PTR_ERR((void*)error) : -EINVAL;
			goto out_free_dentry;
		}
        
- 填写程序的入口地址

完成了目标程序和解释器的加载,同时目标程序的各个段已经加载到内存中了,我们的目标程序已经准备好要执行了,但是还是缺少一样东西,就是我们程序的入口地址,没有入口地址,操作系统就不知道
从哪里开始执行内存中加载好的可执行映像

这段程序的逻辑非常简单,如果需要装入解释器,就通过load_elf_interp装入其映像,并把将来进入用户空间的入口地址设置成load_elf_interp的返回值,即解释器映像的入口地址

若不装入解释器,那么这个入口地址就是目标映像本身的入口地址

::


	if (interpreter) {
		unsigned long interp_map_addr = 0;

		elf_entry = load_elf_interp(&loc->interp_elf_ex,
					    interpreter,
					    &interp_map_addr,
					    load_bias, interp_elf_phdata);
		if (!IS_ERR((void *)elf_entry)) {
			/*
			 * load_elf_interp() returns relocation
			 * adjustment
			 */
			interp_load_addr = elf_entry;
			elf_entry += loc->interp_elf_ex.e_entry;
		}
		if (BAD_ADDR(elf_entry)) {
			retval = IS_ERR((void *)elf_entry) ?
					(int)elf_entry : -EINVAL;
			goto out_free_dentry;
		}
		reloc_func_desc = interp_load_addr;

		allow_write_access(interpreter);
		fput(interpreter);
	} else {
		elf_entry = loc->elf_ex.e_entry;
		if (BAD_ADDR(elf_entry)) {
			retval = -EINVAL;
			goto out_free_dentry;
		}
	}

- 填写目标的文件的参数环境变量等必要信息

::

	retval = create_elf_tables(bprm, &loc->elf_ex,
			  load_addr, interp_load_addr);
	if (retval < 0)
		goto out;
	current->mm->end_code = end_code;
	current->mm->start_code = start_code;
	current->mm->start_data = start_data;
	current->mm->end_data = end_data;
	current->mm->start_stack = bprm->p;

- start_thread宏准备进入新的程序入口

最后,start_thread这个宏会将eip和esp改成新的地址,就使得CPU在返回用户空间时就进入新的程序入口
