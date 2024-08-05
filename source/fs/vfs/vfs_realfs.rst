vfs与real_fs关联
=====================


虚拟文件系统(VFS)提供了一种抽象接口，使不同类型的实际文件系统可以通过统一的接口进行操作．VFS是一个中间层，它将用户空间的系统调用
映射到具体的文件系统操作上．实际的文件系统通过实现这些标准化接口，并将这些接口与VFS进行挂钩．

文件系统的注册与挂载
----------------------

文件系统类型的注册
^^^^^^^^^^^^^^^^^^^^^

每种实际文件系统在内核中都需要进行注册，这通常在文件系统模块加载时完成．注册时，文件系统需要提供一组操作函数，这些函数定义了文件
系统的行为．具体的，这些函数会存储在 ``file_system_type`` 结构中

::

    /**
     * 对内核支持的每一种文件系统，存在一个这样的结构对其进行描述。
     */
    struct file_system_type {
        /**  
         * 文件系统类型的名称 
         */
        const char *name;
        /**  
         * 此文件系统类型的属性 
         */
        int fs_flags;
        /**  
         * 函数指针，当安装此类型的文件系统时，就由VFS调用此例程从设备上将此文件系统的superblock读入内存中
         */ 
        struct super_block *(*get_sb) (struct file_system_type *, int, 
                           const char *, void *);
        /**  
         * 删除超级块的方法。
         */
        void (*kill_sb) (struct super_block *);
        /**  
         * 指向实现文件系统的模块的指针。
         */
        struct module *owner;
        /**  
         * 下一个文件系统指针。
         */
        struct file_system_type * next;
        /**  
         * 具有相同文件系统类型的超级块对象链表的头。
         */
        struct list_head fs_supers;
    };

内核通过 ``register_filesystem`` 函数将文件系统类型注册到VFS

::

    static struct file_system_type ext2_fs_type = {
    .owner      = THIS_MODULE,
    .name       = "ext2",
    .get_sb     = ext2_get_sb,
    .kill_sb    = kill_block_super,
    .fs_flags   = FS_REQUIRES_DEV,
    };

    static int __init init_ext2_fs(void)
    {
        int err = init_ext2_xattr();
        if (err)
            return err; 
        err = init_inodecache();
        if (err)
            goto out1;
        err = register_filesystem(&ext2_fs_type);
        if (err)
            goto out; 
        return 0;
    out:
        destroy_inodecache();
    out1:
        exit_ext2_xattr();
        return err; 
    }

    module_init(init_ext2_fs)


VFS与具体的文件系统操作挂钩
------------------------------

VFS使用一组标准化的操作接口来与实际的文件系统交互．这些定义在 ``super_operations`` , ``inode_operations``, ``file_operation`` 等结构中.

**超级块操作: 定义了与超级块相关的操作，例如读取inode, 同步文件系统等**


::

    struct super_operations {
        struct inode *(*alloc_inode)(struct super_block *sb);
        void (*destroy_inode)(struct inode *);
        void (*write_inode) (struct inode *, struct writeback_control *wbc);
        int (*sync_fs)(struct super_block *sb, int wait);
        // 其他操作函数
    };


**inode操作: 定义了与inode相关的操作，如创建inode,查找目录项等**

::

    struct inode_operations {
        struct dentry *(*lookup) (struct inode *,struct dentry *, unsigned int);
        int (*create) (struct inode *,struct dentry *, umode_t, bool);
        int (*link) (struct dentry *,struct inode *,struct dentry *);
        int (*unlink) (struct inode *,struct dentry *);
        // 其他操作函数
    };

**文件操作: 定义了与文件描述符相关的操作，如读写文件等**

::

    struct file_operations {
        loff_t (*llseek) (struct file *, loff_t, int);
        ssize_t (*read) (struct file *, char __user *, size_t, loff_t *);
        ssize_t (*write) (struct file *, const char __user *, size_t, loff_t *);
        int (*open) (struct inode *, struct file *);
        int (*release) (struct inode *, struct file *);
        // 其他操作函数
    };

mount一个文件系统时，会调用 ``do_new_mount`` 函数，此函数中完成mount相关操作

::

   static int do_new_mount(struct nameidata *nd, char *type, int flags,
            int mnt_flags, char *name, void *data)
	{
		struct vfsmount *mnt;

		if (!type || !memchr(type, 0, PAGE_SIZE))
			return -EINVAL;

		/* we need capabilities... */
		/* 检查权限 */
		if (!capable(CAP_SYS_ADMIN))
			return -EPERM;

		/**  
		 * do_kern_mount可能让当前进程睡眠。
		 * 同时，另外一个进程可能在完全相同的安装点上安装文件系统或者甚至更改根文件系统。
		 * 验证在该安装点上最近安装的文件系统是否仍然指向当前的namespace。如果不是，则返回错误码
		 */
		mnt = do_kern_mount(type, flags, name, data);
		if (IS_ERR(mnt))
			return PTR_ERR(mnt);

		/* 将子文件系统实例与父文件系统装载点进行关联 */
		return do_add_mount(mnt, nd, mnt_flags, NULL);
	}
	 

- do_kern_mount

::

	struct vfsmount *                                                                                                                                                                                          
	do_kern_mount(const char *fstype, int flags, const char *name, void *data)
	{
		 /** 
		 * 获得文件系统名称对应的文件系统对象。
		 */
		struct file_system_type *type = get_fs_type(fstype);
		struct super_block *sb = ERR_PTR(-ENOMEM);
		struct vfsmount *mnt;

		mnt = alloc_vfsmnt(name);

		/**
		 * 调用文件系统的get_sb分配并初始化一个新的超级块。
		 * 例如ext2的get_sb方法是ext2_get_sb。
		 */
		sb = type->get_sb(type, flags, name, data);
		if (IS_ERR(sb))
			goto out_free_secdata;
		error = security_sb_kern_mount(sb, secdata);
		if (error)
			goto out_sb;
		mnt->mnt_sb = sb;
		/**
		 * 将此字段初始化为与文件系统根目录对应的目录项对象的地址。并增加其引用计数值。
		 */
		mnt->mnt_root = dget(sb->s_root);
		mnt->mnt_mountpoint = sb->s_root;
		/**
		 * 将mnt_parent指向自身，表示它是一个独立的根。
		 * 上层调用者可以修改它。
		 */
		mnt->mnt_parent = mnt;
		mnt->mnt_namespace = current->namespace;

		return mnt;
	}

- do_add_mount

::

	int do_add_mount(struct vfsmount *newmnt, struct nameidata *nd, 
         int mnt_flags, struct list_head *fslist)
	{
		...
		//以下代码为attach_mnt函数中内容，attach_mnt被do_add_mount函数调用
		mnt->mnt_parent = mntget(nd->mnt);
		mnt->mnt_mountpoint = dget(nd->dentry);
		//将新的vfs mount加入到mount链表中。open函数调用时会检查目录项是否是一个文件系统的挂载点，会遍历mount链表
		list_add(&mnt->mnt_hash, mount_hashtable+hash(nd->mnt, nd->dentry));                                                                                                                                   
		list_add_tail(&mnt->mnt_child, &nd->mnt->mnt_mounts);
		nd->dentry->d_mounted++;
		...
	}

文件系统的mount操作中，以下代码行是实际的文件系统与vfs关联的关键步骤，open/read/write等操作也会被vfs重定向到实际文件系统中

::

	mnt->mnt_root = dget(sb->s_root); 
	mnt->mnt_mountpoint = sb->s_root;

	mnt->mnt_parent = mnt;  
	mnt->mnt_namespace = current->namespace;

	mnt->mnt_parent = mntget(nd->mnt);
	mnt->mnt_mountpoint = dget(nd->dentry); 
	list_add(&mnt->mnt_hash, mount_hashtable+hash(nd->mnt, nd->dentry));  


**open文件**

::

	struct file *filp_open(const char * filename, int flags, int mode)
	{
		...
		//路径查找中，会对每一个找到的目录项进行挂载点判断

		//在当前目录中搜索下一个分量
		err = do_lookup(nd, &this, &next);
		检查刚解析的分量是否对应一个文件系统的挂载点
		follow_mount(struct vfsmount **mnt, struct dentry **dentry)
		{
			while (d_mountpoint(*dentry)) { 
				/* 在哈希表中查找当前路径的文件系统装载实例 */
				struct vfsmount *mounted = lookup_mnt(*mnt, *dentry);
											{
												struct list_head * head = mount_hashtable + hash(mnt, dentry);
												struct list_head * tmp = head;
												struct vfsmount *p, *found = NULL;

												spin_lock(&vfsmount_lock);
												for (;;) {
													tmp = tmp->next;
													p = NULL;
													if (tmp == head)
														break;
													p = list_entry(tmp, struct vfsmount, mnt_hash);
													if (p->mnt_parent == mnt && p->mnt_mountpoint == dentry) {
														found = mntget(p);
														break;
													}
												}
												spin_unlock(&vfsmount_lock);
												return found;
											}
				if (!mounted)/* 未加载文件系统，退出 */
					break;             
				/* 将文件系统的根目录作为当前路径，继续查找 */
				mntput(*mnt);
				*mnt = mounted;
				dput(*dentry);
				//此步骤较为关键，此步骤后文件操作重定向为实际文件系统对应的inode操作
				*dentry = dget(mounted->mnt_root);
				res = 1;
    		}
		}

		...
	}

.. note::
	mount操作中的 ``mnt->mnt_root = dget(sb->s_root);`` ``mnt->mnt_parent = mntget(nd->mnt);`` ``mnt->mnt_mountpoint = dget(nd->dentry);`` 设置vfs mount挂载点关键信息。
	open操作中则在路径查找的过程中对每一级目录进行挂载点对比(if (p->mnt_parent == mnt && p->mnt_mountpoint == dentry)),如果这一级目录为文件系统挂载点，则 ``修改dentry(*dentry = dget(mounted->mnt_root);)`` 
	这一步骤较为关键。此步骤后对目录项及文件的操作均重定向为实际文件系统对应的inode操作




