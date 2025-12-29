sysfs源码分析
===============

源码文件 fs/sysfs

sysfs的初始化和挂载
--------------------

sysfs文件系统的初始化是在sysfs_init中完成的

::

    static struct file_system_type sysfs_fs_type = {
        .name			= "sysfs",
        .init_fs_context	= sysfs_init_fs_context,
        .kill_sb		= sysfs_kill_sb,
        .fs_flags		= FS_USERNS_MOUNT,
    };

    int __init sysfs_init(void)
    {
        int err;

        sysfs_root = kernfs_create_root(NULL, KERNFS_ROOT_EXTRA_OPEN_PERM_CHECK,
                        NULL);
        if (IS_ERR(sysfs_root))
            return PTR_ERR(sysfs_root);

        sysfs_root_kn = sysfs_root->kn;
        //注册sysfs文件系统
        err = register_filesystem(&sysfs_fs_type);
        if (err) {
            kernfs_destroy_root(sysfs_root);
            return err;
        }

        return 0;
    }


在sysfs文件系统中创建目录
--------------------------

在linux设备模型中，每注册一个kobjcet就会为之创建一个目录，创建目录的接口为 ``sysfs_create_dir_ns`` ,代码如下

::


    /**
     * sysfs_create_dir_ns - create a directory for an object with a namespace tag
     * @kobj: object we're creating directory for
     * @ns: the namespace tag to use
     */
    int sysfs_create_dir_ns(struct kobject *kobj, const void *ns)
    {
        struct kernfs_node *parent, *kn;
        kuid_t uid;
        kgid_t gid;

        if (WARN_ON(!kobj))
            return -EINVAL;
        //如果kobject没有指定父节点，则将其父节点指定为sysfs的根目录
        if (kobj->parent)
            parent = kobj->parent->sd;
        else
            parent = sysfs_root_kn;

        if (!parent)
            return -ENOENT;

        kobject_get_ownership(kobj, &uid, &gid);
        //创建目录
        kn = kernfs_create_dir_ns(parent, kobject_name(kobj),
                      S_IRWXU | S_IRUGO | S_IXUGO, uid, gid,
                      kobj, ns);
        if (IS_ERR(kn)) {
            if (PTR_ERR(kn) == -EEXIST)
                sysfs_warn_dup(parent, kobject_name(kobj));
            return PTR_ERR(kn);
        }

        kobj->sd = kn;
        return 0;
    }



在sysfs文件系统中创建一般属性文件
----------------------------------

kobject的每一项属性都对应在sysfs文件系统中的一个文件，文件名称与属性名称相同。 创建一般属性的接口为 ``sysfs_create_file_ns`` ,代码如下

::

    /**
     * sysfs_create_file_ns - create an attribute file for an object with custom ns
     * @kobj: object we're creating for
     * @attr: attribute descriptor
     * @ns: namespace the new file should belong to
     */
    int sysfs_create_file_ns(struct kobject *kobj, const struct attribute *attr,
                 const void *ns)
    {
        kuid_t uid;
        kgid_t gid;

        if (WARN_ON(!kobj || !kobj->sd || !attr))
            return -EINVAL;

        kobject_get_ownership(kobj, &uid, &gid);
        return sysfs_add_file_mode_ns(kobj->sd, attr, false, attr->mode,
                          uid, gid, ns);

    }
    EXPORT_SYMBOL_GPL(sysfs_create_file_ns);

    int sysfs_add_file_mode_ns(struct kernfs_node *parent,
                   const struct attribute *attr, bool is_bin,
                   umode_t mode, kuid_t uid, kgid_t gid, const void *ns)
    {
        struct lock_class_key *key = NULL;
        const struct kernfs_ops *ops;
        struct kernfs_node *kn;
        loff_t size;

        if (!is_bin) {
            struct kobject *kobj = parent->priv;
            const struct sysfs_ops *sysfs_ops = kobj->ktype->sysfs_ops;

            /* every kobject with an attribute needs a ktype assigned */
            if (WARN(!sysfs_ops, KERN_ERR
                 "missing sysfs attribute operations for kobject: %s\n",
                 kobject_name(kobj)))
                return -EINVAL;

            if (sysfs_ops->show && sysfs_ops->store) {
                if (mode & SYSFS_PREALLOC)
                    ops = &sysfs_prealloc_kfops_rw;
                else
                    ops = &sysfs_file_kfops_rw;
            } else if (sysfs_ops->show) {
                if (mode & SYSFS_PREALLOC)
                    ops = &sysfs_prealloc_kfops_ro;
                else
                    ops = &sysfs_file_kfops_ro;
            } else if (sysfs_ops->store) {
                if (mode & SYSFS_PREALLOC)
                    ops = &sysfs_prealloc_kfops_wo;
                else
                    ops = &sysfs_file_kfops_wo;
            } else
                ops = &sysfs_file_kfops_empty;

            size = PAGE_SIZE;
        } else {
            struct bin_attribute *battr = (void *)attr;

            if (battr->mmap)
                ops = &sysfs_bin_kfops_mmap;
            else if (battr->read && battr->write)
                ops = &sysfs_bin_kfops_rw;
            else if (battr->read)
                ops = &sysfs_bin_kfops_ro;
            else if (battr->write)
                ops = &sysfs_bin_kfops_wo;
            else
                ops = &sysfs_file_kfops_empty;

            size = battr->size;
        }

    #ifdef CONFIG_DEBUG_LOCK_ALLOC
        if (!attr->ignore_lockdep)
            key = attr->key ?: (struct lock_class_key *)&attr->skey;
    #endif

        kn = __kernfs_create_file(parent, attr->name, mode & 0777, uid, gid,
                      size, ops, (void *)attr, ns, key);
        if (IS_ERR(kn)) {
            if (PTR_ERR(kn) == -EEXIST)
                sysfs_warn_dup(parent, attr->name);
            return PTR_ERR(kn);
        }
        return 0;
    }

在sysfs文件系统中创建二进制文件
--------------------------------


sysfs文件系统中的链接文件
--------------------------

