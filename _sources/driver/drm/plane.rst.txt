plane代码分析
=====================

struct drm_plane结构体
------------------------

::

    struct drm_plane {
        /** @dev: DRM device this plane belongs to */
        struct drm_device *dev;

        struct list_head head;

        char *name;

        struct drm_modeset_lock mutex;

        /** @base: base mode object */
        struct drm_mode_object base;
        //plane绑定的crtc
        uint32_t possible_crtcs;
        //plane支持的fb像素format类型数组，format类型如DRM_FORMAT_ARGB8888
        uint32_t *format_types;
        //plane支持的fb像素format类型数组大小
        unsigned int format_count;

        bool format_default;

        //modifier数组，其存放的值DRM_FORMAT_MOD_LINEAR/DRM_FORMAT_MOD_X_TILED
        uint64_t *modifiers;
        //modifier数组大小
        unsigned int modifier_count;

        //d当前绑定的crtc
        struct drm_crtc *crtc;

        //no-atomic drivers用来标识当前绑定的fb
        struct drm_framebuffer *fb;

        //对于no-atomic drivers, old_fb用于在modeset操作时跟踪老的fb 
        struct drm_framebuffer *old_fb;

        /** @funcs: plane control functions */
        const struct drm_plane_funcs *funcs;

        /** @properties: property tracking for this plane */
        struct drm_object_properties properties;

        /** @type: Type of plane, see &enum drm_plane_type for details. */
        enum drm_plane_type type;

        /**
         * @index: Position inside the mode_config.list, can be used as an array
         * index. It is invariant over the lifetime of the plane.
         */
        unsigned index;

        /** @helper_private: mid-layer private data */
        const struct drm_plane_helper_funcs *helper_private;

        //表示plane的各种状态，如其绑定的crtc/fb等，用于atomic操作
        struct drm_plane_state *state;

        /**
         * @alpha_property:
         * Optional alpha property for this plane. See
         * drm_plane_create_alpha_property().
         */
        struct drm_property *alpha_property;
        /**
         * @zpos_property:
         * Optional zpos property for this plane. See
         * drm_plane_create_zpos_property().
         */
        struct drm_property *zpos_property;
        /**
         * @rotation_property:
         * Optional rotation property for this plane. See
         * drm_plane_create_rotation_property().
         */
        struct drm_property *rotation_property;
        /**
         * @blend_mode_property:
         * Optional "pixel blend mode" enum property for this plane.
         * Blend mode property represents the alpha blending equation selection,
         * describing how the pixels from the current plane are composited with
         * the background.
         */
        struct drm_property *blend_mode_property;

        /**
         * @color_encoding_property:
         *
         * Optional "COLOR_ENCODING" enum property for specifying
         * color encoding for non RGB formats.
         * See drm_plane_create_color_properties().
         */
        struct drm_property *color_encoding_property;
        /**
         * @color_range_property:
         *
         * Optional "COLOR_RANGE" enum property for specifying
         * color range for non RGB formats.
         * See drm_plane_create_color_properties().
         */
        struct drm_property *color_range_property;
    };


drm_universal_plane_init
----------------------------

::

    int drm_universal_plane_init(struct drm_device *dev, struct drm_plane *plane,
                     uint32_t possible_crtcs,
                     const struct drm_plane_funcs *funcs,
                     const uint32_t *formats, unsigned int format_count,
                     const uint64_t *format_modifiers,
                     enum drm_plane_type type,
                     const char *name, ...)
    {
        struct drm_mode_config *config = &dev->mode_config;
        unsigned int format_modifier_count = 0;
        int ret;

        /* plane index is used with 32bit bitmasks */
        if (WARN_ON(config->num_total_plane >= 32))
            return -EINVAL;

        WARN_ON(drm_drv_uses_atomic_modeset(dev) &&
            (!funcs->atomic_destroy_state ||
             !funcs->atomic_duplicate_state));

        //创建一个类型为DRM_MODE_OBJECT_PLANE的
        ret = drm_mode_object_add(dev, &plane->base, DRM_MODE_OBJECT_PLANE);
        if (ret)
            return ret;

        drm_modeset_lock_init(&plane->mutex);

        plane->base.properties = &plane->properties;
        plane->dev = dev;
        plane->funcs = funcs;
        plane->format_types = kmalloc_array(format_count, sizeof(uint32_t),
                            GFP_KERNEL);
        if (!plane->format_types) {
            DRM_DEBUG_KMS("out of memory when allocating plane\n");
            drm_mode_object_unregister(dev, &plane->base);
            return -ENOMEM;
        }

        /*
         * First driver to need more than 64 formats needs to fix this. Each
         * format is encoded as a bit and the current code only supports a u64.
         */
        if (WARN_ON(format_count > 64))
            return -EINVAL;

        if (format_modifiers) {
            const uint64_t *temp_modifiers = format_modifiers;
            while (*temp_modifiers++ != DRM_FORMAT_MOD_INVALID)
                format_modifier_count++;
        }

        if (format_modifier_count)
            config->allow_fb_modifiers = true;

        plane->modifier_count = format_modifier_count;
        plane->modifiers = kmalloc_array(format_modifier_count,
                         sizeof(format_modifiers[0]),
                         GFP_KERNEL);

        if (format_modifier_count && !plane->modifiers) {
            DRM_DEBUG_KMS("out of memory when allocating plane\n");
            kfree(plane->format_types);
            drm_mode_object_unregister(dev, &plane->base);
            return -ENOMEM;
        }

        if (name) {
            va_list ap;

            va_start(ap, name);
            plane->name = kvasprintf(GFP_KERNEL, name, ap);
            va_end(ap);
        } else {
            plane->name = kasprintf(GFP_KERNEL, "plane-%d",
                        drm_num_planes(dev));
        }
        if (!plane->name) {
            kfree(plane->format_types);
            kfree(plane->modifiers);
            drm_mode_object_unregister(dev, &plane->base);
            return -ENOMEM;
        }

        memcpy(plane->format_types, formats, format_count * sizeof(uint32_t));
        plane->format_count = format_count;
        memcpy(plane->modifiers, format_modifiers,
               format_modifier_count * sizeof(format_modifiers[0]));
        plane->possible_crtcs = possible_crtcs;
        plane->type = type;

        list_add_tail(&plane->head, &config->plane_list);
        plane->index = config->num_total_plane++;

        drm_object_attach_property(&plane->base,
                       config->plane_type_property,
                       plane->type);

        if (drm_core_check_feature(dev, DRIVER_ATOMIC)) {
            drm_object_attach_property(&plane->base, config->prop_fb_id, 0);
            drm_object_attach_property(&plane->base, config->prop_in_fence_fd, -1);
            drm_object_attach_property(&plane->base, config->prop_crtc_id, 0);
            drm_object_attach_property(&plane->base, config->prop_crtc_x, 0);
            drm_object_attach_property(&plane->base, config->prop_crtc_y, 0);
            drm_object_attach_property(&plane->base, config->prop_crtc_w, 0);
            drm_object_attach_property(&plane->base, config->prop_crtc_h, 0);
            drm_object_attach_property(&plane->base, config->prop_src_x, 0);
            drm_object_attach_property(&plane->base, config->prop_src_y, 0);
            drm_object_attach_property(&plane->base, config->prop_src_w, 0);
            drm_object_attach_property(&plane->base, config->prop_src_h, 0);
        }

        if (config->allow_fb_modifiers)
            create_in_format_blob(dev, plane);

        return 0;
    }


func
----------

- struct drm_plane_funcs

::

	/**
	 * struct drm_plane_funcs - driver plane control functions
	 */
	struct drm_plane_funcs {
	 
		/*使能配置plane的crtc和framebuffer.src_x/src_y/src_w/src_h指定fb的源区域
		 *crtc_x/crtc_y/crtc_w/crtc_h指定其显示在crtc上的目标区域
		 *atomic操作使用drm_atomic_helper_update_plane实现
		*/
		int (*update_plane)(struct drm_plane *plane,
					struct drm_crtc *crtc, struct drm_framebuffer *fb,
					int crtc_x, int crtc_y,
					unsigned int crtc_w, unsigned int crtc_h,
					uint32_t src_x, uint32_t src_y,
					uint32_t src_w, uint32_t src_h,
					struct drm_modeset_acquire_ctx *ctx);
	 
		/*DRM_IOCTL_MODE_SETPLANE IOCTL调用时，fb id参数，如果为0，就会调用该接口
		 *关闭plane， atomic modeset使用drm_atomic_helper_disable_plane()实现该hook
		 */
		int (*disable_plane)(struct drm_plane *plane,
					 struct drm_modeset_acquire_ctx *ctx);
	 
	 
		//该接口仅在driver卸载的时候通过drm_mode_config_cleanup()调用来清空plane资源
		void (*destroy)(struct drm_plane *plane);
	 
		/*reset plane的软硬件状态， 通过drm_mode_config_reset接口调用
		 *atomic drivers 使用drm_atomic_helper_plane_reset()实现该hook*/
		void (*reset)(struct drm_plane *plane);
	 
		/*设置属性的legacy入口， atomic drivers不使用*/
		int (*set_property)(struct drm_plane *plane,
					struct drm_property *property, uint64_t val);
	 
	 
		/*复制plane state, atomic driver必须要有该接口
		 *drm_atomic_get_plane_state会调用到该hook*/
		struct drm_plane_state *(*atomic_duplicate_state)(struct drm_plane *plane);
	 
		//销毁plane state
		void (*atomic_destroy_state)(struct drm_plane *plane,
						 struct drm_plane_state *state);
	 
		
		/*设置驱动自定义的属性， 通过drm_atomic_plane_set_property调用*/
		int (*atomic_set_property)(struct drm_plane *plane,
					   struct drm_plane_state *state,
					   struct drm_property *property,
					   uint64_t val);
	 
		//获取驱动自定义的属性， 通过drm_atomic_plane_get_property调用
		int (*atomic_get_property)(struct drm_plane *plane,
					   const struct drm_plane_state *state,
					   struct drm_property *property,
					   uint64_t *val);
		
		//drm_dev_register接口调用后，调用该hook注册额外的用户接口
		int (*late_register)(struct drm_plane *plane);
	 
		//drm_dev_unregister()前调用，unregister用户空间接口
		void (*early_unregister)(struct drm_plane *plane);
	 
	 
		//打印plane state, drm_atomic_plane_print_state()会调用
		void (*atomic_print_state)(struct drm_printer *p,
					   const struct drm_plane_state *state);
	 
		//检查format和modifier是否有效
		bool (*format_mod_supported)(struct drm_plane *plane, uint32_t format,
						 uint64_t modifier);
	};


- struct drm_plane_helper_funcs

::

	struct drm_plane_helper_funcs {
		
		//准备fb，主要包括设置fb fence,  映射fb虚拟地址等
		int (*prepare_fb)(struct drm_plane *plane,
				  struct drm_plane_state *new_state);
	 
		//和prepare_fb是相反的操作，比如解除fb虚拟地址的映射
		void (*cleanup_fb)(struct drm_plane *plane,
				   struct drm_plane_state *old_state);
	 
		//可选的检查plane属性的约束项
		int (*atomic_check)(struct drm_plane *plane,
					struct drm_atomic_state *state);
	 
		/*更新plane的属性状态到软硬件中， 这个接口才是真正更新参数*/
		void (*atomic_update)(struct drm_plane *plane,
					  struct drm_atomic_state *state);
		//disable plane 非必需，不做介绍
		void (*atomic_disable)(struct drm_plane *plane,
					   struct drm_atomic_state *state);
	 
		//异步检查 后续了解
		int (*atomic_async_check)(struct drm_plane *plane,
					  struct drm_atomic_state *state);
		//异步更新，后续了解
		void (*atomic_async_update)(struct drm_plane *plane,
						struct drm_atomic_state *state);
	};








