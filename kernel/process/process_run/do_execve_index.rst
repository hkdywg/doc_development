linux进程启动过程分析
=====================

fork clone等复制出来的是父进程的一个副本，那么我们想加载新的程序,可以通过execve来加载和启动新的程序

- exec()函数族

exec函数一共6个,其中execve为内核级别系统调用，其他(execl, execle, execlp, execv, execvp)都是调用execve的库函数

::
    
    int execl(const char *path, const char *arg, ...);
    int execlp(const char *path, const char *arg, ...);
    int execle(const char *path, const char *arg, ..., char *const envp[]);
    int execv(const char *path, const char *argv[]);
    int execvp(const char *file, const char *argv[]) 


linux下标准的可执行文件格式是 ``elf`` ,elf(executable and linking format)是一种对象文件的格式，用于定义不同类型的对象文件(object files)中都放了
什么东西以及都以什么样的格式去存放这些东西.

但是linux也支持其他不同的可执行程序格式,各种可执行程序的执行方式不尽相同，因此linux内核每种被注册的可执行程序格式都用 ``linux_bin_fmt`` 来存储，
其中记录了可执行程序的加载和执行函数，同时需要一种方法来保存可执行程序的信息,比如果可执行文件的路径，运行的参数和环境变量等信息,即 ``linux_bin_prm`` 结构

- struct linux_bin_prm结描述一个可执行程序

linux_bin_prm在include/linux/binfmts.h中定义,用来保存要执行的文件相关信息,包括可执行程序的路径，参数和环境变量等信息

::

    
    /*
     * This structure is used to hold the arguments that are used when loading binaries.
     */
    struct linux_binprm {
    #ifdef CONFIG_MMU
        struct vm_area_struct *vma;
        unsigned long vma_pages;
    #else
    # define MAX_ARG_PAGES	32
        struct page *page[MAX_ARG_PAGES];
    #endif
        struct mm_struct *mm;
        unsigned long p; /* current top of mem */
        unsigned long argmin; /* rlimit marker for copy_strings() */
        unsigned int
            /*
             * True after the bprm_set_creds hook has been called once
             * (multiple calls can be made via prepare_binprm() for
             * binfmt_script/misc).
             */
            called_set_creds:1,
            /*
             * True if most recent call to the commoncaps bprm_set_creds
             * hook (due to multiple prepare_binprm() calls from the
             * binfmt_script/misc handlers) resulted in elevated
             * privileges.
             */
            cap_elevated:1,
            /*
             * Set by bprm_set_creds hook to indicate a privilege-gaining
             * exec has happened. Used to sanitize execution environment
             * and to set AT_SECURE auxv for glibc.
             */
            secureexec:1;
    #ifdef __alpha__
        unsigned int taso:1;
    #endif
        unsigned int recursion_depth; /* only for search_binary_handler() */
        struct file * file; //要执行的文件
        struct cred *cred;	/* new credentials */
        int unsafe;		/* how unsafe this exec is (mask of LSM_UNSAFE_*) */
        unsigned int per_clear;	/* bits to clear in current->personality */
        int argc, envc; //命令行参数和环境变量数目
        const char * filename;	/* Name of binary as seen by procps */
        //要执行的文件名称
        const char * interp;	/* Name of the binary really executed. Most
                       of the time same as filename, but could be
                       different for binfmt_{misc,script} */
        unsigned interp_flags;
        unsigned interp_data;
        unsigned long loader, exec;

        struct rlimit rlim_stack; /* Saved RLIMIT_STACK used during exec. */

        char buf[BINPRM_BUF_SIZE];
    } __randomize_layout;

- struct linux_binfmt可执行程序的结构

linux_binfmt定义在include/linux/binfmts.h

::

    /*
     * This structure defines the functions that are used to load the binary formats that
     * linux accepts.
     */
    struct linux_binfmt {
        struct list_head lh;
        struct module *module;
        int (*load_binary)(struct linux_binprm *);
        int (*load_shlib)(struct file *);
        int (*core_dump)(struct coredump_params *cprm);
        unsigned long min_coredump;	/* minimal dump size */
    } __randomize_layout;

其提供了3种方法来加载和执行可执行程序

1) load_binary -- 通过读取存放在可执行文件中的信息为当前进程建立一个新的执行环境

2) load_shlib -- 用于动态的把一个共享库捆绑到一个运行的进程,这是由uselib()系统调用激活的

3) core_dump -- 在名为core的文件中,存放当前进程的执行上下文，这个文件通常是在进程收到一个缺省操作为"dump"的信号时创建,其格式取决于可执行程序的类型

execve加载可执行程序的过程
--------------------------

内核中实际执行execv()或execve()系统调用的程序是do_execve(),这个函数会打开目标映像文件，并从目标文件的头部读入若干(当前linux内核时128)字节(实际上就是填充elf文件头),
然后调用另外一个函数search_binary_handler(),在此函数里面，它会搜索我们上面提到的linux支持的可执行文件类型队列,让各种可执行程序的处理程序前来认领.如果匹配则调用load_binary
函数指针来处理目标映像文件.elf文件对应的是load_elf_binary函数

sys_execve()--->do_execve()--->do_execveat_common()--->search_binary_handler()--->load_elf_binary()

execve入口函数sys_execve

+--------------------------+---------------------------------------------------------+---------------------------------------------------------+
|      描述                |                   定义                                  |                 文件位置                                |
+==========================+=========================================================+=========================================================+
|                          |    类似如下形式                                         |                                                         |
| 系统调用号(体系结构相关) |    #define __NR_execve_117                              | arch/(体系结构)/include/uapi/asm/unistd.h               |
|                          |          __SYSCALL(117,sys_execve,3)                    |                                                         |
+--------------------------+---------------------------------------------------------+---------------------------------------------------------+
|                          | asmlinkage long sys_execve(const char __user \*filename |                                                         |
| 入口函数声明             |         ,const char __user \*const __user \*argv,       | include/linux/syscalls.h                                |
|                          |         const char __user \*const __user \*envp         |                                                         |
+--------------------------+---------------------------------------------------------+---------------------------------------------------------+
|                          |   SYSCALL_DEFINE3(execve,                               |                                                         |
| 系统调用实现             |          const char __user, file_name,                  |    fs/exec.c                                            |
|                          |         const cahr __user \*const __usr argv            |                                                         |
+--------------------------+---------------------------------------------------------+---------------------------------------------------------+

::

    SYSCALL_DEFINE3(execve,
            const char __user *, filename,
            const char __user *const __user *, argv,
            const char __user *const __user *, envp)
    {
        return do_execve(getname(filename), argv, envp);
    }

    //filenam------可执行程序名称
    //argv程序的参数
    //envp环境变量

do_execve函数定义在fs/exec.c中

::

    int do_execve(struct filename *filename,
        const char __user *const __user *__argv,
        const char __user *const __user *__envp)
    {
        struct user_arg_ptr argv = { .ptr.native = __argv };
        struct user_arg_ptr envp = { .ptr.native = __envp };
        return do_execveat_common(AT_FDCWD, filename, argv, envp, 0);
    }

    int do_execve_file(struct file *file, void *__argv, void *__envp)
    {
        struct user_arg_ptr argv = { .ptr.native = __argv };
        struct user_arg_ptr envp = { .ptr.native = __envp };

        return __do_execve_file(AT_FDCWD, NULL, argv, envp, 0, file);
    }

    /*
     * sys_execve() executes a new program.
     */
    static int __do_execve_file(int fd, struct filename *filename,
                    struct user_arg_ptr argv,
                    struct user_arg_ptr envp,
                    int flags, struct file *file)
    {
        char *pathbuf = NULL;
        struct linux_binprm *bprm; //很重要的数据结构,
        struct files_struct *displaced;
        int retval;

        if (IS_ERR(filename))
            return PTR_ERR(filename);

        /*
         * We move the actual failure in case of RLIMIT_NPROC excess from
         * set*uid() to execve() because too many poorly written programs
         * don't check setuid() return code.  Here we additionally recheck
         * whether NPROC limit is still exceeded.
         */
        if ((current->flags & PF_NPROC_EXCEEDED) &&
            atomic_read(&current_user()->processes) > rlimit(RLIMIT_NPROC)) {
            retval = -EAGAIN;
            goto out_ret;
        }

        /* We're below the limit (still or again), so we don't want to make
         * further execve() calls fail. */
        current->flags &= ~PF_NPROC_EXCEEDED;

        //调用ushare_files为进程复制一份文件表
        retval = unshare_files(&displaced);
        if (retval)
            goto out_ret;

        //调用kzalloc在堆上分配一份struct linux_binprm结构体
        retval = -ENOMEM;
        bprm = kzalloc(sizeof(*bprm), GFP_KERNEL);
        if (!bprm)
            goto out_files;

        retval = prepare_bprm_creds(bprm);
        if (retval)
            goto out_free;

        check_unsafe_exec(bprm);
        current->in_execve = 1;

        //查找并打开二进制文件
        if (!file)
            file = do_open_execat(fd, filename, flags);
        retval = PTR_ERR(file);
        if (IS_ERR(file))
            goto out_unmark;

        //调用sched_exec()找到最小负载的cpu,用来执行该二进制文件
        sched_exec();

        //根据获取的信息，填充struct  linux_binprm结构体中的file filename interp成员
        bprm->file = file;
        if (!filename) {
            bprm->filename = "none";
        } else if (fd == AT_FDCWD || filename->name[0] == '/') {
            bprm->filename = filename->name;
        } else {
            if (filename->name[0] == '\0')
                pathbuf = kasprintf(GFP_KERNEL, "/dev/fd/%d", fd);
            else
                pathbuf = kasprintf(GFP_KERNEL, "/dev/fd/%d/%s",
                            fd, filename->name);
            if (!pathbuf) {
                retval = -ENOMEM;
                goto out_unmark;
            }
            /*
             * Record that a name derived from an O_CLOEXEC fd will be
             * inaccessible after exec. Relies on having exclusive access to
             * current->files (due to unshare_files above).
             */
            if (close_on_exec(fd, rcu_dereference_raw(current->files->fdt)))
                bprm->interp_flags |= BINPRM_FLAGS_PATH_INACCESSIBLE;
            bprm->filename = pathbuf;
        }
        bprm->interp = bprm->filename;

      //创建进程的地址空间，并调用init_new_context检查当前进程是否使用自定义的局部描述符表
        retval = bprm_mm_init(bprm);
        if (retval)
            goto out_unmark;

        
        retval = prepare_arg_pages(bprm, argv, envp);
        if (retval < 0)
            goto out;
        //检查二进制文件的可执行权限,最后kernel_read()读取二进制文件头128字节
        //这些字节用于识别二进制文件的格式及其他信息,后续会使用到
        retval = prepare_binprm(bprm);
        if (retval < 0)
            goto out;
        //从内核空间获取二进制文件的路径名称
        retval = copy_strings_kernel(1, &bprm->filename, bprm);
        if (retval < 0)
            goto out;

        bprm->exec = bprm->p;
        //从用户空间拷贝环境变量
        retval = copy_strings(bprm->envc, envp, bprm);
        if (retval < 0)
            goto out;
        //从用户空间拷贝命令行参数
        retval = copy_strings(bprm->argc, argv, bprm);
        if (retval < 0)
            goto out;

        would_dump(bprm, bprm->file);

        /*
            至此,二进制文件已经被打开,struct linux_binprm结构体中也记录了重要信息
            下面需要识别该二进制文件的格式并最终运行该文件
        */

        retval = exec_binprm(bprm);
        if (retval < 0)
            goto out;

        /* execve succeeded */
        current->fs->in_exec = 0;
        current->in_execve = 0;
        rseq_execve(current);
        acct_update_integrals(current);
        task_numa_free(current, false);
        free_bprm(bprm);
        kfree(pathbuf);
        if (filename)
            putname(filename);
        if (displaced)
            put_files_struct(displaced);
        return retval;

    out:
        if (bprm->mm) {
            acct_arg_size(bprm, 0);
            mmput(bprm->mm);
        }

    out_unmark:
        current->fs->in_exec = 0;
        current->in_execve = 0;

    out_free:
        free_bprm(bprm);
        kfree(pathbuf);

    out_files:
        if (displaced)
            reset_files_struct(displaced);
    out_ret:
        if (filename)
            putname(filename);
        return retval;
    }


    static int exec_binprm(struct linux_binprm *bprm)
    {
        pid_t old_pid, old_vpid;
        int ret;

        /* Need to fetch pid before load_binary changes it */
        old_pid = current->pid;
        rcu_read_lock();
        old_vpid = task_pid_nr_ns(current, task_active_pid_ns(current->parent));
        rcu_read_unlock();

        ret = search_binary_handler(bprm);
        if (ret >= 0) {
            audit_bprm(bprm);
            trace_sched_process_exec(current, old_pid, bprm);
            ptrace_event(PTRACE_EVENT_EXEC, old_vpid);
            proc_exec_connector(current);
        }

        return ret;
    }


- search_binary_handler 识别二进制程序

::

    /*
     * cycle the list of binary formats handler, until one recognizes the image
     */
    int search_binary_handler(struct linux_binprm *bprm)
    {
        bool need_retry = IS_ENABLED(CONFIG_MODULES);
        struct linux_binfmt *fmt;
        int retval;

        /* This allows 4 levels of binfmt rewrites before failing hard. */
        if (bprm->recursion_depth > 5)
            return -ELOOP;

        retval = security_bprm_check(bprm);
        if (retval)
            return retval;

        retval = -ENOENT;
     retry:
        read_lock(&binfmt_lock);
        //遍历formats链表
        list_for_each_entry(fmt, &formats, lh) {
            if (!try_module_get(fmt->module))
                continue;
            read_unlock(&binfmt_lock);

            bprm->recursion_depth++;
            retval = fmt->load_binary(bprm);
            bprm->recursion_depth--;

            read_lock(&binfmt_lock);
            put_binfmt(fmt);
            if (retval < 0 && !bprm->mm) {
                /* we got to flush_old_exec() and failed after it */
                read_unlock(&binfmt_lock);
                force_sigsegv(SIGSEGV);
                return retval;
            }
            if (retval != -ENOEXEC || !bprm->file) {
                read_unlock(&binfmt_lock);
                return retval;
            }
        }
        read_unlock(&binfmt_lock);

        if (need_retry) {
            if (printable(bprm->buf[0]) && printable(bprm->buf[1]) &&
                printable(bprm->buf[2]) && printable(bprm->buf[3]))
                return retval;
            if (request_module("binfmt-%04x", *(ushort *)(bprm->buf + 2)) < 0)
                return retval;
            need_retry = false;
            goto retry;
        }

        return retval;
    }
    EXPORT_SYMBOL(search_binary_handler);
