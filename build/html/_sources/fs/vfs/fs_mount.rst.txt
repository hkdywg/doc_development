文件系统mount
==================

linux使用系统的根文件系统(system's root filesystem):它由内核在引导阶段直接安装，并拥有系统初始化脚本及最基本的系统程序．

其他文件系统要么由初始化脚本安装，要么由用户直接安装在已安装文件系统的目录上．作为一个目录树，每个文件系统都有自己的根目录(root directory),
安装文件系统的这个目录称之为安装点(mount point).已安装文件系统属于安装点目录的一个子文件系统．


根文件系统安装
-------------------


安装根文件系统是系统初始化的关键部分.编译内核时，或者向最初的启动装入程序传递一个合适的"root"选项时，根文件系统可以被指定为/dev目录下的一个设备文件．


安装根文件系统分为两个阶段:

- 内核安装特殊rootfs文件系统，该文件系统仅提供一个作为初始安装点的空目录

- 内核在空目录上安装实际根文件系统


.. note::
    为什么内核不怕麻烦，要在安装实际根文件系统之前安装rootfs文件系统呢？rootfs文件系统允许内核改变实际根文件系统．事实上，在某些情况下，内核逐个
    安装和卸载几个根文件系统．例如，系统启动时内核把存放在ramdisk中的一个最小文件系统作为根安装．在这个初始根文件系统程序探测信息系统硬件(SSD, EMMC, UFS?),
    装入所必须的内核模块后，然后从物理块设备重新安装根文件系统．


.. note::
    用于挂载根文件系统的rootfs事实上是一个ramfs


rootfs安装
^^^^^^^^^^^^^^^

::

    start_kernel
        vfs_caches_init
            dcache_init
            inode_init
            files_init
            mnt_init
                sysfs_init
                init_rootfs     #注册rootfs文件系统
                init_mount_tree #在rootfs中挂载最初的根目录
                    do_kern_mount("rootfs", 0, "rootfs", NULL)
                        type->get_sb(type, flags, name, data)   #调用文件系统的get_sb方法分配并初始化一个新的超级块 
                        mnt->mnt_sb = sb;
                        mnt->mnt_parent = mnt
                        mnt->mnt_namespace = current->namespace
        


实际根文件系统安装
^^^^^^^^^^^^^^^^^^^^^


::

    start_kernel
        rest_init
            init
                prepare_namespace   #实际的根文件系统安装
                    mount_devfs
                    root_device_name = saved_root_name  #从启动参数"root"中获取设备文件名
                    mount_root  #窒息向嗯真正的挂载
                        create_dev("/dev/root", ROOT_DEV, root_device_name) #调用sys_mknod在rootfs中创建设备文件/dev/root
                        mount_block_root("/dev/root", root_mountflags)
                            do_mount_root
                                sys_mount(name, "/root", fs, flags, data)
                    


普通文件系统安装
---------------------

mount系统调用用来安装普通文件系统，它对应的内核服务例程为 ``sys_mount``


::

    sys_mount
        do_mount
            do_new_mount
                do_kern_mount   #进行文件系统安装操作
                    struct vfsmount *mnt  = alloc_vfsmnt(name)  #分配文件系统挂载描述符
                    struct file_system_type *type = get_fs_type(fstype) #获取文件系统类型
                    sb = type->get_sb(type, flags, name, data); #获取超级块
                    mnt->mnt_sb = sb;
                do_mount_mount  #将子文件系统实例与父文件系统装载点进行关联





