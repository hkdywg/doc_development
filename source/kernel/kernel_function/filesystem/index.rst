Linux内核API之文件系统
=========================

vfs_fstat
------------

``vfs_fstat`` 根据第一个参数fd查找相应的文件，获取文件的属性信息，然后将属性信息保存在函数的第二个参数stat中

::

    #include <linux/fs.h>
    //内核源码kernel/stat.c
    int vfs_fstat(unsigned int fd, struct kstat *stat)


- fd: 文件描述符，与用户态下open打开文件返回值意义相同

- stat: 用于保存文件的基本信息


``vfs_getattr`` 获取当前虚拟文件系统的属性

::

    #include <linux/fs.h>
    //kernel源码fs/stat.c
    int vfs_getattr(struct path *path, struct kstat *stat)

- path: 虚拟文件系统路径

- stat: 用于保存文件系统信息


:: 

    struct path {
        struct vfsmount *mnt;
        struct dentry *dentry;
    }


``vfs_statfs`` 根据第一个参数dentry获取整个文件系统的一些基本信息，将其保存在第二个参数buf中，此基本信息包括当前文件系统的类型，
文件系统的块数目，文件系统的块大小，文件系统的文件数目，文件系统的文件名长度等信息

::

    #include <linux/fs.h>
    //kenel源码fs/statfs.c
    int vfs_statfs(struct dentry *dentry, struct kstatfs *buf)

    struct kstatfs {
        long f_type;    //文件系统的类型
        long f_bszie;   //文件系统的块大小
        u64  f_blocks;  //文件系统块的数目
        u64  f_bfree;
        u64  f_avail;   //文件系统中可用的块数目
        u64  f_files;   //文件系统中文件的数目
        u64  f_ffree;
        __kernel_fsid_t f_fsid;
        long f_namelen;
        long f_frsize;
        long f_flags;
        long f_spare[4];
    };


**测试代码**

::

    #include <linux/init.h>
    #include <linux/module.h>
    #include <linux/fs.h>
    #include <linux/statfs.h>
    #include <linux/sched.h>
    #include <linux/fs_struct.h>

    static int vfs_statfs_init(void)
    {
        struct path path;
        struct dentry *dentry = NULL;
        static struct kstatfs buf;
        struct inode *inode;

        dentry = current->fs->pwd.dentry;
        path.dentry = dentry;
        path.mnt  = current->fs->pwd.mnt;
        inode = dentry->d_inode;

        vfs_statfs(&path, &buf);
        printk("f_bsize is :%ld\n", buf.f_bsize);
        printk("f_frsize is :%ld\n", buf.f_frsize);
        printk("f_type is :%ld\n", buf.f_type);
        printk("f_blocks is :%lld\n", buf.f_blocks);
        printk("f_bfree is :%lld\n", buf.f_bfree);
        printk("f_bavail is :%lld\n", buf.f_bavail);
        printk("f_files is :%lld\n", buf.f_files);
        printk("f_ffree is :%lld\n", buf.f_ffree);
        printk("f_fsid is :%ld\n", buf.f_fsid);
        printk("f_namelen is :%ld\n", buf.f_namelen);

        printk("inode->i_sb->s_dev = %d\n", inode->i_sb->s_dev);
        printk("inode->i_ino = %d\n", inode->i_ino);
        printk("inode->i_mode = %d\n", inode->i_mode);
        printk("inode->i_nlink = %d\n", inode->i_nlink);
        printk("inode->i_uid = %d\n", inode->i_uid);
        printk("inode->i_gid = %d\n", inode->i_gid);

        vfs_getattr(&path, &stat);
        printk("stat.dev = %d\n", stat.dev);
        printk("stat.ino = %d\n", stat.ino);
        printk("stat.mode = %d\n", stat.mode);
        printk("stat.nlink = %d\n", stat.nlink);
        printk("stat.uid = %d\n", stat.uid);
        printk("stat.gid = %d\n", stat.gid);

    }

    static void vfs_statfs_exit(void)
    {
        return;
    }

    module_init(vfs_statfs_init);
    module_exit(vfs_statfs_exit);


current_umask
----------------

``current_umask`` 用来返回当前文件的权限值掩码


=============================== =============================================================   
 掩码　                                                 描述
------------------------------- -------------------------------------------------------------
 S_IRWXU                            文件所有者具有读写执行权限
 S_IRUSR                            文件所有者具有读权限
 S_IWUSR                            文件所有者具有写权限
 S_IXUSR                            文件所有者具有执行权限
 S_IRWXG                            用户组具有读写执行权限
 S_IRGRP                            用户组具有读权限
 S_IWGRP                            用户组具有写权限
 S_IXGRP                            用户组具有执行权限
 S_IRWXO                            其他用户具有读写执行权限
 S_IROTH                            其他所有用户具有读权限
 S_IWOTH                            其他所有用户具有写权限
 S_IXOTH                            其他所有用户具有执行权限
=============================== =============================================================   


::

    #include <linux/fs.h>
    //kernel源码fs/fs_struct.c
    int current_umask(void)


``get_fs_type`` 用于根据输入参数的名字*name, 获取对应文件系统类型的描述符信息

::

    #include <linux/fs.h>
    //kernel源码fs/__filesystems.c
    struct file_system_type *get_fs_type(const char *name)

    struct file_system_type {
        const char *name;           //文件系统名
        int fs_flags;               //文件系统类型标志

    #define FS_REQUIRES_DEV         1
    #define FS_BINARY_MOUNTDATA     2
    #define FS_HAS_SUBTYPE          4
    #define FS_USERNS_MOUNT         8
    #define FS_USERNS_DEV_MOUNT     16
    #define FS_RENAME_DOES_D_MOVE   32768

        //挂载文件系统的方法
        struct dentry *(*mount)(struct file_system_type *, int, const char *, void *);
        //删除超级块的方法
        void (*kill_sb)(struct super_block *);
        struct module *owner;   //指向实现文件系统的模块的指针
        struct file_system_type *next;  //指向文件系统类型链表下一个元素的指针
        struct list_head fs_supers;     //具有相同文件系统类型的超级块对象链表的头
    };

``get_max_files`` 返回在文件系统中可以同时打开的最大文件数目

::

    #include <linux/fs.h>
    //kernel源码fs/file_table.c
    int get_max_files(void)

``get_super`` 由参数*dev所指定的块设备获取超级块

::

    #include <linux/fs.h>
    //kernel源码fs/super.c
    struct super_block *get_super(struct block_device *bdev)

- bdev: 用来指定所获取的是哪个设备上的超级块

::

    struct block_device {
        dev_t   bd_dev;         //block_device的搜索编号
        int     bd_openers;     //打开该设备计数器
        struct inode *bd_inode;
        struct super_block *bd_super;   //块设备文件系统超级块结构体，用来操作块文件系统
        struct mutex    bd_mutex;       //打开/关闭互斥量
        struct list_head bd_inodes;         //设备节点链表
        void *bd_claiming;
        void *bd_holder;
        bool bd_write_holder;
        #ifdef CONFIG_SYSFS
        struct list_head bd_holder_list;
        #endif
        struct block_device *bd_contains;   //含有非分区块结构体
        unsigned bd_block_size;     //用来描述块大小，在申请队列中进行设置
        struct hd_struct *bd_part;  //硬件分区结构
        unsigned bd_part_count; //被打开设备的分区次数及统计信息
        int bd_invalidated;
        struct gendisk *bd_disk;    //虚拟块设备下层的通用磁盘结构
        struct request_queue *bd_queue;
        struct list_head bd_list;
        unsigned long bd_private;
        int bd_fsfreeze_count;
        struct mutex bd_fsfreeze_mutex;
    };

    struct super_block {
        struct list_head    s_list;                 //指向超级块链表的指针
        dev_t               s_dev;                  //设备标识符
        unsigned char       s_blocksize_bits;       //以位为单位的块大小
        unsigned long       s_blocksize;            //以字节为单位的块大小
        unsigned long long  s_maxbytes;             //文件的最大字节数
        struct file_system_type *s_type;            //文件系统类型
        const struct super_operations *s_ops;       //超级块方法
        struct dquot_operations     *s_qcop;        //磁盘限额处理的方法
        const struct export_operations *s_export_op;//网络文件系统使用的输出操作
        unsigned long       s_flags;                //安装标志
        unsigned long       s_magic;                //文件系统的魔数
        struct dentry       *s_root;                //文件系统根目录的目录项对象
        struct rw_semaphore s_umount;               //卸载所用的信号量
        int                 s_count;                //引用计数器
        atomic_t            s_active;               //次级引用计数器
        #ifdef CONFIG_SECURITY
        void *s_security;                           //指向超级块安全数据结构的指针
        #endif
        struct xattr_handler    **s_xattr;          //指向超级块扩展属性结构的指针
        struct list_head        s_inodes;           //所有索引节点的链表
        struct hlist_head       s_anon;             //用于处理网络文件系统的匿名目录项的链表
        struct list_head        s_mounts;           //
        struct block_device     *s_bdev;
        struct backing_dev_info *s_bdi;
        struct mtd_info         *s_mtd;
        struct hlist_head       s_instance;         //用于给定文件系统类型的超级块对象链表的指针
        unsigned int            s_quota_types; 
        struct quota_info       s_dpuot;            //磁盘限额的描述符
        struct sb_writers       s_writers;
        char                    s_id[32];           //包含超级块的块设备名称
        u8                      s_uuid[16];         //UUID
        void                    *s_fs_info;         //指向特定文件系统的超级块信息的指针
        unsigned int            s_max_links;        
        fmode_t                 s_mode;
        u32                     s_time_gran;        //时间戳的最小单位
        struct mutex            s_vfs_rename_mutex;
        char                    *s_subtype;
        char                    *s_options;
    };



``have_submounts`` 用来检查在parent所指定的目录及其子目录上是否有挂载点

::

    #include <linux/dcache.h>
    //kernel源码fs/dcache.c
    int have_submounts(struct dentry *parent)


**测试代码**

::

    #include <linux/module.h>
    #include <linux/init.h>
    #include <linux/fs.h>
    #include <linux/fs_struct.h>
    #include <linux/path.h>
    #include <linux/sched.h>

    int get_fs_type_init(void)
    {
        const char *name = "ext4";

        struct file_system_type fs = get_fs_type(name);
        printk("the filesystem's name is: %s\n", fs->name);

        int data = get_max_files(); //获取系统中文件数目
        printk("get max files is = %d\n", data);

        struct super_block *sb;
        struct block_device *bdev = current->fs->pwd.dentry->d_sb->s_bdev;     //获取当前文件对应的block_device描述符信息

        sb = get_super(bdev);   //获取bdev所对应的超级块
        printk("the superblock dev number is %d\n", sb->s_dev);

        struct dentry *dentry_parent = current->fs->pwd.dentry->d_parrent;
        data = have_submounts(dentry_parent);
        if(data == 0)
            printk("current dentry has not submount.\n");
        else 
            printk("current dentry has submount.\n");

        return 0;
    }

    void get_fs_type_exit(void)
    {
        return;
    }

    module_init(get_fs_type_init);
    module_exit(get_fs_type_exit);





























