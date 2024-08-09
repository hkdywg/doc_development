VKMS示例
=============

VKMS是"Virtual Kernel Mode Setting"的缩写，之所以称他为Virtual KMS, 是因为该驱动不需要真实的硬件，他完全是一个软件
虚拟的"显示设备"，甚至连显示都算不上，因为当它运行时，你看不到任何显示内容。它唯一能提供的就是一个由高精度timer模拟
的VSYNC中断信号。

该驱动存在的真实目的，主要是为了DRM框架自测试。虽然看不到VKMS的显示效果，但是在驱动流程上，它实现了modesetting该有
的基本操作(Modesetting是指在显示器上渲染图像的过程中，调整显示器的分辨率、刷新率、像素格式等参数)

代码存放在drivers/gpu/drm/vkms/目录下

目前VKMS驱动已经集成了如下功能

- Atomic Modeset

- VBlank

- Dumb Buffer

- Cursor & Primary Plane

- Framebuffer CRC校验

- Plane Composition

- GEM Prime Import

最简单的VKMS驱动
------------------

::

    #include <drm/drmP.h>

    static struct drm_device drm;   //用于抽象一个完整的DRM设备

    static struct drm_driver vkms_driver = {
        .name = "vkms",
        .desc = "virtual kernel mode setting",
        .date = "2022-8-9",
        .major = 1,
        .minor = 0,
    };

    static int __init vkms_init(void)
    {
        drm_dev_init(&drm, &vkms_driver, NULL);
        drm_register(&drm, 0);

        return 0;
    }

    module_init(vkms_init);

当次驱动注册进内核后，内核会做一下事情

- 创建设备节点: /dev/dri/card0

- 创建sysfs节点: /sys/class/drm/card0

- 创建debugfs节点: /sys/kernel/debug/dri/0

但该驱动目前什么事情也做不了，唯一能做的就是查看该驱动的名字

::

    cat /sys/kernel/debug/dri/0/name
    vkms unique=vkms


VKMS驱动添加fops操作接口
-------------------------

::

    #include <drm/drmP.h>

    static struct drm_device drm;   //用于抽象一个完整的DRM设备

    static const struct file_operations vkms_fops = {
        .owner = THIS_MODULE,
        .open = drm_open,
        .release = drm_release,
        .unlocked_ioctl = drm_ioctl,
        .poll = drm_poll,
        .read = drm_read,
    };

    static struct drm_driver vkms_driver = {
        .fops = &vkms_fops,     //增加fops操作接口

        .name = "vkms",
        .desc = "virtual kernel mode setting",
        .date = "2022-8-9",
        .major = 1,
        .minor = 0,
    };

    static int __init vkms_init(void)
    {
        drm_dev_init(&drm, &vkms_driver, NULL);
        drm_register(&drm, 0);

        return 0;
    }

    module_init(vkms_init);

有了fops,我们就可以对card0进行open/read操作了。同时可以进行一些ioctl操作了，但是只限于drm相关的只读操作且不需要调用
相关回调函数的操作。

到目前为止，凡是和Modesetting相关的操作，还是操作不了

添加drm mode objects
-------------------------

::

    #include <drm/drmP.h>

    static struct drm_device drm;   //用于抽象一个完整的DRM设备

    //增加drm mode object
    static struct drm_plane primary;
    static struct drm_crtc crtc;
    static struct drm_encoder encoder;
    static struct drm_connector connector;

    //增加drm mode object对应的回调函数结构体
    static const struct drm_plane_funcs vkms_plane_funcs;
    static const struct drm_crtc_funcs vkms_crtc_funcs;
    static const struct drm_encoder_funcs vkms_encoder_funcs;
    static const struct drm_connector_funcs vkms_connector_funs;

    static const u32 vkms_formats[] = {
        DRM_FORMAT_XRGS8888,
    };

    static void vkms_modeset_init(void)
    {
        drm_mode_config_init(&drm); //初始化KMS框架,本质上是初始化drm_device中mode_config结构体

        //最后初始化drm_device中包含的drm_connector， drm_crtc等对象
        drm_universal_plane_init(&drm, &primary, 0, &vkms_plane_funcs, vkms_formats, ARRAY_SIZE(vkms_formats),
                            NULL, DRM_PLANE_TYPE_PRIMARY, NULL);

        drm_crtc_init_with_planes(&drm, &crtc, &primary, NULL, &vkms_crtc_funcs, NULL);

        drm_encoder_init(&drm, &encoder, &vkms_encoder_funcs, DRM_MODE_ENCODER_VIRTUAL, NULL);

        drm_connector_init(&drm, &connector, &vkms_connector_funcs, DRM_MODE_CONNECTOR_VIRTUAL);
    }

    static const struct file_operations vkms_fops = {
        .owner = THIS_MODULE,
        .open = drm_open,
        .release = drm_release,
        .unlocked_ioctl = drm_ioctl,
        .poll = drm_poll,
        .read = drm_read,
    };

    static struct drm_driver vkms_driver = {
        .driver_features = DRIVER_MODESET,      //添加DRIVER_MODESET标志位，告诉DRM Core当前驱动支持modesetting操作
        
        .fops = &vkms_fops,     //增加fops操作接口

        .name = "vkms",
        .desc = "virtual kernel mode setting",
        .date = "2022-8-9",
        .major = 1,
        .minor = 0,
    };

    static int __init vkms_init(void)
    {
        drm_dev_init(&drm, &vkms_driver, NULL);

        vkms_modeset_init();

        drm_register(&drm, 0);

        return 0;
    }

    module_init(vkms_init);


由于上面4个object在创建时，他们的callback funcs没有赋初值，所以真正的modeset操作目前还无法正常运行，不过至少可以使用一些
只读的modeset ioctl了(不需要调用DRM相关回调函数的操作)


添加FB和GEM支持
-------------------

::

    #include <drm/drmP.h>
    #include <drm/drm_encoder.h>
    #include <drm/drm_fb_cma_helper.h>
    #include <drm/drm_gem_cma_helper.h>

    static struct drm_device drm;   //用于抽象一个完整的DRM设备

    //增加drm mode object
    static struct drm_plane primary;
    static struct drm_crtc crtc;
    static struct drm_encoder encoder;
    static struct drm_connector connector;

    //增加drm mode object对应的回调函数结构体
    static const struct drm_plane_funcs vkms_plane_funcs;
    static const struct drm_crtc_funcs vkms_crtc_funcs;
    static const struct drm_encoder_funcs vkms_encoder_funcs;
    static const struct drm_connector_funcs vkms_connector_funs;

    static const u32 vkms_formats[] = {
        DRM_FORMAT_XRGS8888,
    };

    //定义了一些函数指针，用于管理驱动程序中的显示模式配置
    //这些函数指针包括添加和删除连接器、CRTC和编解码器，以及更新显示模式等功能
    //这些函数在驱动程序中被调用以进行显示模式的管理和配置
    static const struct drm_mode_config_funcs vkms_mode_funcs = {
        .fb_create = drm_fb_cma_create,     //根据给定的帧缓冲参数，创建一个新的帧缓冲设备，并返回其句柄
    };

    static void vkms_modeset_init(void)
    {
        drm_mode_config_init(&drm); //初始化KMS框架,本质上是初始化drm_device中mode_config结构体

        //填充mode_config中min_width, max_width, max_height,这些值是framebuffer大小限制
        drm.mode_config.max_width = 8192;
        drm.mode_config.max_height = 8192;
        //设置mode_config->func指针，本质上是一组由驱动程序实现的回调函数，涵盖KMS中一些相当基本的操作
        drm.mode_config.funcs = &vkms_mode_funcs;

        //最后初始化drm_device中包含的drm_connector， drm_crtc等对象
        drm_universal_plane_init(&drm, &primary, 0, &vkms_plane_funcs, vkms_formats, ARRAY_SIZE(vkms_formats),
                            NULL, DRM_PLANE_TYPE_PRIMARY, NULL);

        drm_crtc_init_with_planes(&drm, &crtc, &primary, NULL, &vkms_crtc_funcs, NULL);

        drm_encoder_init(&drm, &encoder, &vkms_encoder_funcs, DRM_MODE_ENCODER_VIRTUAL, NULL);

        drm_connector_init(&drm, &connector, &vkms_connector_funcs, DRM_MODE_CONNECTOR_VIRTUAL);
    }

    static const struct file_operations vkms_fops = {
        .owner = THIS_MODULE,
        .open = drm_open,
        .release = drm_release,
        .unlocked_ioctl = drm_ioctl,
        .poll = drm_poll,
        .read = drm_read,

        //DRM的GEM对象映射到用户空间，以便用于空间使用
        .mmap = drm_gem_cma_mmap,   
    };

    static struct drm_driver vkms_driver = {
        .driver_features = DRIVER_MODESET,      //添加DRIVER_MODESET标志位，告诉DRM Core当前驱动支持modesetting操作
        
        .fops = &vkms_fops,     //增加fops操作接口

        //增加fb相关操作
        .dumb_create = drm_gem_cma_dumb_create,     //用于创建dumb buffer,也就是一个简单的、未映射的内存区域。
                                                    //通常用于测试或者临时存储
        .gem_vm_ops = &drm_gem_cma_vm_ops,          //用于实现GEM内存管理机制的各种功能
                                                    //用户空间程序请求显存时被调用，用于控制显存的访问权限、分配显存
        .gem_free_object_unlocked = drm_gem_cma_free_object,

        .name = "vkms",
        .desc = "virtual kernel mode setting",
        .date = "2022-8-9",
        .major = 1,
        .minor = 0,
    };

    static int __init vkms_init(void)
    {
        drm_dev_init(&drm, &vkms_driver, NULL);

        vkms_modeset_init();

        drm_register(&drm, 0);

        return 0;
    }

    module_init(vkms_init);

现在可以使用ioctl进行一些标准的GEM和FB操作了

在drm_mode_config结构体中存在一个类型为drm_mode_config_func的回调函数指针结构体，用于驱动程序向内核注册显示器模式
配置。这些函数指针包含添加和删除连接器，CRTC和编码器，以及更新显示模式等功能。

.. note::
    drm_mode_config_funcs结构体中fb_create创建一个新的帧缓冲对象，但并不是分配内存，frambuffer不涉及内存的分配与
    释放。framebuffer通过访问GEM对象来获取内存区域的物理地址信息。



实现callback funcs并添加Legacy Modeset支持
----------------------------------------------

::

    #include <drm/drmP.h>
    #include <drm/drm_encoder.h>
    #include <drm/drm_fb_cma_helper.h>
    #include <drm/drm_gem_cma_helper.h>

    static struct drm_device drm;   //用于抽象一个完整的DRM设备

    //增加drm mode object
    static struct drm_plane primary;
    static struct drm_crtc crtc;
    static struct drm_encoder encoder;
    static struct drm_connector connector;

	static void vkms_crtc_dpms(struct drm_crtc *crtc, int mode)
	{

	}
	 
	static int vkms_crtc_mode_set(struct drm_crtc *crtc,
					struct drm_display_mode *mode,
					struct drm_display_mode *adjusted_mode,
					int x, int y, struct drm_framebuffer *old_fb)
	{
		return 0;
	}
	 
	static void vkms_crtc_prepare(struct drm_crtc *crtc)
	{
	}
	 
	static void vkms_crtc_commit(struct drm_crtc *crtc)
	{

	}

	static const struct drm_crtc_helper_funcs vkms_crtc_helper_funcs = {
		.dpms = vkms_crtc_dpms,
		.mode_set = vkms_crtc_mode_set,
		.prepare = vkms_crtc_prepare,
		.commit = vkms_crtc_commit,
	};

    static int vkms_crtc_page_flip(struct drm_crtc *crtc,
                                    struct drm_framebuffer *fb,
                                    struct drm_pending_vblank_event *event,
                                    uint32_t page_flip_flags,
                                    struct drm_modeset_acquire_ctx *ctx)
    {
        unsigned long flags;

        crtc->primary->fb = fb;
        if(event) {
            spin_lock_irqsave(&crtc->dev->event_lock, flags);
            drm_crtc_send_vblank_event(crtc, event);
            spin_unlock_irqsave(&crtc->dev->event_lock, flags);
        }

        return 0;
    }

    //增加drm mode object对应的回调函数结构体
    static const struct drm_plane_funcs vkms_plane_funcs = {
        .update_plane = drm_primary_helper_update,
        .disable_plane = drm_primary_helper_disable,
        .destroy = drm_plane_cleanup,
    };

    static const struct drm_crtc_funcs vkms_crtc_funcs = {
        .set_config = drm_crtc_helper_set_config,
        .page_flip = vkms_cetc_page_flip,
        .destroy = drm_crtc_cleanup,
    };
    static const struct drm_encoder_funcs vkms_encoder_funcs;
    static const struct drm_connector_funcs vkms_connector_funs;

    static const u32 vkms_formats[] = {
        DRM_FORMAT_XRGS8888,
    };

	static int vkms_connector_get_modes(struct drm_connector *connector)
	{
		int count;

		count = drm_add_modes_noedid(connector, 8192, 8192);
		drm_set_preferred_mode(connector, 1024, 768);

		return count;
	}

	static struct drm_encode *vkms_connector_best_encoder(struct drm_connector *connector)
	{
		return &encoder;
	}

	static const struct drm_connector_helper_funcs vkms_conn_helper_funcs = {
		.get_modes = vkms_connector_get_modes,
		.best_encoder = vkms_connector_best_encoder,
	};

	static const struct drm_connector_funcs vkms_connector_funcs = {
		.dpms = drm_helper_connector_dpms,
		.fill_modes = drm_helper_probe_single_connector_modes,
		.destroy = drm_connector_cleanup,
	};

	static const struct encoder_funcs vkms_encoder_funcs = {
		.destroy = drm_encoder_cleanup,
	};


    //定义了一些函数指针，用于管理驱动程序中的显示模式配置
    //这些函数指针包括添加和删除连接器、CRTC和编解码器，以及更新显示模式等功能
    //这些函数在驱动程序中被调用以进行显示模式的管理和配置
    static const struct drm_mode_config_funcs vkms_mode_funcs = {
        .fb_create = drm_fb_cma_create,     //根据给定的帧缓冲参数，创建一个新的帧缓冲设备，并返回其句柄
    };

    static void vkms_modeset_init(void)
    {
        drm_mode_config_init(&drm); //初始化KMS框架,本质上是初始化drm_device中mode_config结构体

        //填充mode_config中min_width, max_width, max_height,这些值是framebuffer大小限制
        drm.mode_config.max_width = 8192;
        drm.mode_config.max_height = 8192;
        //设置mode_config->func指针，本质上是一组由驱动程序实现的回调函数，涵盖KMS中一些相当基本的操作
        drm.mode_config.funcs = &vkms_mode_funcs;

        //最后初始化drm_device中包含的drm_connector， drm_crtc等对象
        drm_universal_plane_init(&drm, &primary, 0, &vkms_plane_funcs, vkms_formats, ARRAY_SIZE(vkms_formats),
                            NULL, DRM_PLANE_TYPE_PRIMARY, NULL);

        drm_crtc_init_with_planes(&drm, &crtc, &primary, NULL, &vkms_crtc_funcs, NULL);
		drm_crtc_helper_add(&crtc, &vkms_crtc_helper_funcs);

        drm_encoder_init(&drm, &encoder, &vkms_encoder_funcs, DRM_MODE_ENCODER_VIRTUAL, NULL);
        drm_connector_init(&drm, &connector, &vkms_connector_funcs, DRM_MODE_CONNECTOR_VIRTUAL);
		drm_connector_helper_add(&connector, &vkms_conn_helper_funcs);
		drm_mode_connector_attach_encoder(&connector, &encoder);
    }

    static const struct file_operations vkms_fops = {
        .owner = THIS_MODULE,
        .open = drm_open,
        .release = drm_release,
        .unlocked_ioctl = drm_ioctl,
        .poll = drm_poll,
        .read = drm_read,

        //DRM的GEM对象映射到用户空间，以便用于空间使用
        .mmap = drm_gem_cma_mmap,   
    };

    static struct drm_driver vkms_driver = {
        .driver_features = DRIVER_MODESET,      //添加DRIVER_MODESET标志位，告诉DRM Core当前驱动支持modesetting操作
        
        .fops = &vkms_fops,     //增加fops操作接口

        //增加fb相关操作
        .dumb_create = drm_gem_cma_dumb_create,     //用于创建dumb buffer,也就是一个简单的、未映射的内存区域。
                                                    //通常用于测试或者临时存储
        .gem_vm_ops = &drm_gem_cma_vm_ops,          //用于实现GEM内存管理机制的各种功能
                                                    //用户空间程序请求显存时被调用，用于控制显存的访问权限、分配显存
        .gem_free_object_unlocked = drm_gem_cma_free_object,

        .name = "vkms",
        .desc = "virtual kernel mode setting",
        .date = "2022-8-9",
        .major = 1,
        .minor = 0,
    };

    static int __init vkms_init(void)
    {
        drm_dev_init(&drm, &vkms_driver, NULL);

        vkms_modeset_init();

        drm_register(&drm, 0);

        return 0;
    }

    module_init(vkms_init);





