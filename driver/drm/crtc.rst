crtc代码分析
================


struct drm_crtc结构体
-------------------------

::

    struct drm_crtc {
        /** @dev: parent DRM device */
        struct drm_device *dev;
        /** @port: OF node used by drm_of_find_possible_crtcs(). */
        struct device_node *port;
        /**
         * @head:
         *
         * List of all CRTCs on @dev, linked from &drm_mode_config.crtc_list.
         * Invariant over the lifetime of @dev and therefore does not need
         * locking.
         */
        struct list_head head;

        /** @name: human readable name, can be overwritten by the driver */
        char *name;

        /**
         * @mutex:
         *
         * This provides a read lock for the overall CRTC state (mode, dpms
         * state, ...) and a write lock for everything which can be update
         * without a full modeset (fb, cursor data, CRTC properties ...). A full
         * modeset also need to grab &drm_mode_config.connection_mutex.
         *
         * For atomic drivers specifically this protects @state.
         */
        struct drm_modeset_lock mutex;

        /** @base: base KMS object for ID tracking etc. */
        struct drm_mode_object base;

        /**
         * @primary:
         * Primary plane for this CRTC. Note that this is only
         * relevant for legacy IOCTL, it specifies the plane implicitly used by
         * the SETCRTC and PAGE_FLIP IOCTLs. It does not have any significance
         * beyond that.
         */
        struct drm_plane *primary;

        /**
         * @cursor:
         * Cursor plane for this CRTC. Note that this is only relevant for
         * legacy IOCTL, it specifies the plane implicitly used by the SETCURSOR
         * and SETCURSOR2 IOCTLs. It does not have any significance
         * beyond that.
         */
        struct drm_plane *cursor;

        /**
         * @index: Position inside the mode_config.list, can be used as an array
         * index. It is invariant over the lifetime of the CRTC.
         */
        unsigned index;

        /**
         * @cursor_x: Current x position of the cursor, used for universal
         * cursor planes because the SETCURSOR IOCTL only can update the
         * framebuffer without supplying the coordinates. Drivers should not use
         * this directly, atomic drivers should look at &drm_plane_state.crtc_x
         * of the cursor plane instead.
         */
        int cursor_x;
        /**
         * @cursor_y: Current y position of the cursor, used for universal
         * cursor planes because the SETCURSOR IOCTL only can update the
         * framebuffer without supplying the coordinates. Drivers should not use
         * this directly, atomic drivers should look at &drm_plane_state.crtc_y
         * of the cursor plane instead.
         */
        int cursor_y;

        /**
         * @enabled:
         *
         * Is this CRTC enabled? Should only be used by legacy drivers, atomic
         * drivers should instead consult &drm_crtc_state.enable and
         * &drm_crtc_state.active. Atomic drivers can update this by calling
         * drm_atomic_helper_update_legacy_modeset_state().
         */
        bool enabled;

        /**
         * @mode:
         *
         * Current mode timings. Should only be used by legacy drivers, atomic
         * drivers should instead consult &drm_crtc_state.mode. Atomic drivers
         * can update this by calling
         * drm_atomic_helper_update_legacy_modeset_state().
         */
        struct drm_display_mode mode;

        /**
         * @hwmode:
         *
         * Programmed mode in hw, after adjustments for encoders, crtc, panel
         * scaling etc. Should only be used by legacy drivers, for high
         * precision vblank timestamps in
         * drm_calc_vbltimestamp_from_scanoutpos().
         *
         * Note that atomic drivers should not use this, but instead use
         * &drm_crtc_state.adjusted_mode. And for high-precision timestamps
         * drm_calc_vbltimestamp_from_scanoutpos() used &drm_vblank_crtc.hwmode,
         * which is filled out by calling drm_calc_timestamping_constants().
         */
        struct drm_display_mode hwmode;

        /**
         * @x:
         * x position on screen. Should only be used by legacy drivers, atomic
         * drivers should look at &drm_plane_state.crtc_x of the primary plane
         * instead. Updated by calling
         * drm_atomic_helper_update_legacy_modeset_state().
         */
        int x;
        /**
         * @y:
         * y position on screen. Should only be used by legacy drivers, atomic
         * drivers should look at &drm_plane_state.crtc_y of the primary plane
         * instead. Updated by calling
         * drm_atomic_helper_update_legacy_modeset_state().
         */
        int y;

        /** @funcs: CRTC control functions */
        const struct drm_crtc_funcs *funcs;

        /**
         * @gamma_size: Size of legacy gamma ramp reported to userspace. Set up
         * by calling drm_mode_crtc_set_gamma_size().
         */
        uint32_t gamma_size;

        /**
         * @gamma_store: Gamma ramp values used by the legacy SETGAMMA and
         * GETGAMMA IOCTls. Set up by calling drm_mode_crtc_set_gamma_size().
         */
        uint16_t *gamma_store;

        /** @helper_private: mid-layer private data */
        const struct drm_crtc_helper_funcs *helper_private;

        /** @properties: property tracking for this CRTC */
        struct drm_object_properties properties;

        /**
         * @state:
         *
         * Current atomic state for this CRTC.
         *
         * This is protected by @mutex. Note that nonblocking atomic commits
         * access the current CRTC state without taking locks. Either by going
         * through the &struct drm_atomic_state pointers, see
         * for_each_oldnew_crtc_in_state(), for_each_old_crtc_in_state() and
         * for_each_new_crtc_in_state(). Or through careful ordering of atomic
         * commit operations as implemented in the atomic helpers, see
         * &struct drm_crtc_commit.
         */
        struct drm_crtc_state *state;

        /**
         * @commit_list:
         *
         * List of &drm_crtc_commit structures tracking pending commits.
         * Protected by @commit_lock. This list holds its own full reference,
         * as does the ongoing commit.
         *
         * "Note that the commit for a state change is also tracked in
         * &drm_crtc_state.commit. For accessing the immediately preceding
         * commit in an atomic update it is recommended to just use that
         * pointer in the old CRTC state, since accessing that doesn't need
         * any locking or list-walking. @commit_list should only be used to
         * stall for framebuffer cleanup that's signalled through
         * &drm_crtc_commit.cleanup_done."
         */
        struct list_head commit_list;

        /**
         * @commit_lock:
         *
         * Spinlock to protect @commit_list.
         */
        spinlock_t commit_lock;

    #ifdef CONFIG_DEBUG_FS
        /**
         * @debugfs_entry:
         *
         * Debugfs directory for this CRTC.
         */
        struct dentry *debugfs_entry;
    #endif

        /**
         * @crc:
         *
         * Configuration settings of CRC capture.
         */
        struct drm_crtc_crc crc;

        /**
         * @fence_context:
         *
         * timeline context used for fence operations.
         */
        unsigned int fence_context;

        /**
         * @fence_lock:
         *
         * spinlock to protect the fences in the fence_context.
         */
        spinlock_t fence_lock;
        /**
         * @fence_seqno:
         *
         * Seqno variable used as monotonic counter for the fences
         * created on the CRTC's timeline.
         */
        unsigned long fence_seqno;

        /**
         * @timeline_name:
         *
         * The name of the CRTC's fence timeline.
         */
        char timeline_name[32];

        /**
         * @self_refresh_data: Holds the state for the self refresh helpers
         *
         * Initialized via drm_self_refresh_helper_init().
         */
        struct drm_self_refresh_data *self_refresh_data;
    };


crtc相关的API
-----------------

- drm_crtc_init_with_planes

::

    int drm_crtc_init_with_planes(struct drm_device *dev, struct drm_crtc *crtc,
                      struct drm_plane *primary,
                      struct drm_plane *cursor,
                      const struct drm_crtc_funcs *funcs,
                      const char *name, ...)
    {
        struct drm_mode_config *config = &dev->mode_config;
        int ret;

        WARN_ON(primary && primary->type != DRM_PLANE_TYPE_PRIMARY);
        WARN_ON(cursor && cursor->type != DRM_PLANE_TYPE_CURSOR);

        /* crtc index is used with 32bit bitmasks */
        if (WARN_ON(config->num_crtc >= 32))
            return -EINVAL;

        WARN_ON(drm_drv_uses_atomic_modeset(dev) &&
            (!funcs->atomic_destroy_state ||
             !funcs->atomic_duplicate_state));

        crtc->dev = dev;
        crtc->funcs = funcs;

        INIT_LIST_HEAD(&crtc->commit_list);
        spin_lock_init(&crtc->commit_lock);

        drm_modeset_lock_init(&crtc->mutex);
        //创建类型为DRM_MODE_OBJECT_CRTC的struct drm_mode_object结构体
        ret = drm_mode_object_add(dev, &crtc->base, DRM_MODE_OBJECT_CRTC);
        if (ret)
            return ret;

        //设置名称
        if (name) {
            va_list ap;

            va_start(ap, name);
            crtc->name = kvasprintf(GFP_KERNEL, name, ap);
            va_end(ap);
        } else {
            crtc->name = kasprintf(GFP_KERNEL, "crtc-%d",
                           drm_num_crtcs(dev));
        }
        if (!crtc->name) {
            drm_mode_object_unregister(dev, &crtc->base);
            return -ENOMEM;
        }

        crtc->fence_context = dma_fence_context_alloc(1);
        spin_lock_init(&crtc->fence_lock);
        snprintf(crtc->timeline_name, sizeof(crtc->timeline_name),
             "CRTC:%d-%s", crtc->base.id, crtc->name);

        //初始化properties
        crtc->base.properties = &crtc->properties;

        list_add_tail(&crtc->head, &config->crtc_list);
        crtc->index = config->num_crtc++;
        /初始化primary plane, cursor plane
        crtc->primary = primary;
        crtc->cursor = cursor;
        if (primary && !primary->possible_crtcs)
            primary->possible_crtcs = drm_crtc_mask(crtc);
        if (cursor && !cursor->possible_crtcs)
            cursor->possible_crtcs = drm_crtc_mask(crtc);

        //调试相关的初始化
        ret = drm_crtc_crc_init(crtc);
        if (ret) {
            drm_mode_object_unregister(dev, &crtc->base);
            return ret;
        }

        //attach一些properties变量
        if (drm_core_check_feature(dev, DRIVER_ATOMIC)) {
            drm_object_attach_property(&crtc->base, config->prop_active, 0);
            drm_object_attach_property(&crtc->base, config->prop_mode_id, 0);
            drm_object_attach_property(&crtc->base,
                           config->prop_out_fence_ptr, 0);
            drm_object_attach_property(&crtc->base,
                           config->prop_vrr_enabled, 0);
        }

        return 0;
    }

- drm_mode_setcrtc

::

    int drm_mode_setcrtc(struct drm_device *dev, void *data,
                 struct drm_file *file_priv)
    {
        struct drm_mode_config *config = &dev->mode_config;
        struct drm_mode_crtc *crtc_req = data;
        struct drm_crtc *crtc;
        struct drm_plane *plane;
        struct drm_connector **connector_set = NULL, *connector;
        struct drm_framebuffer *fb = NULL;
        struct drm_display_mode *mode = NULL;
        struct drm_mode_set set;
        uint32_t __user *set_connectors_ptr;
        struct drm_modeset_acquire_ctx ctx;
        int ret;
        int i;

        if (!drm_core_check_feature(dev, DRIVER_MODESET))
            return -EOPNOTSUPP;

        /*
         * Universal plane src offsets are only 16.16, prevent havoc for
         * drivers using universal plane code internally.
         */
        if (crtc_req->x & 0xffff0000 || crtc_req->y & 0xffff0000)
            return -ERANGE;

        //找到需要的crtc实体
        crtc = drm_crtc_find(dev, file_priv, crtc_req->crtc_id);
        if (!crtc) {
            DRM_DEBUG_KMS("Unknown CRTC ID %d\n", crtc_req->crtc_id);
            return -ENOENT;
        }
        DRM_DEBUG_KMS("[CRTC:%d:%s]\n", crtc->base.id, crtc->name);

        plane = crtc->primary;

        /* allow disabling with the primary plane leased */
        if (crtc_req->mode_valid && !drm_lease_held(file_priv, plane->base.id))
            return -EACCES;

        mutex_lock(&crtc->dev->mode_config.mutex);
        DRM_MODESET_LOCK_ALL_BEGIN(dev, ctx,
                       DRM_MODESET_ACQUIRE_INTERRUPTIBLE, ret);

        //得到或者生成primary plane的framebuffer
        if (crtc_req->mode_valid) {
            /* If we have a mode we need a framebuffer. */
            /* If we pass -1, set the mode with the currently bound fb */
            if (crtc_req->fb_id == -1) {
                struct drm_framebuffer *old_fb;

                if (plane->state)
                    old_fb = plane->state->fb;
                else
                    old_fb = plane->fb;

                if (!old_fb) {
                    DRM_DEBUG_KMS("CRTC doesn't have current FB\n");
                    ret = -EINVAL;
                    goto out;
                }

                fb = old_fb;
                /* Make refcounting symmetric with the lookup path. */
                drm_framebuffer_get(fb);
            } else {
                fb = drm_framebuffer_lookup(dev, file_priv, crtc_req->fb_id);
                if (!fb) {
                    DRM_DEBUG_KMS("Unknown FB ID%d\n",
                            crtc_req->fb_id);
                    ret = -ENOENT;
                    goto out;
                }
            }
           //创建struct drm_display_mode结构体，并把应用层传递下来的参数赋值给结构体 
            mode = drm_mode_create(dev);
            if (!mode) {
                ret = -ENOMEM;
                goto out;
            }
            if (!file_priv->aspect_ratio_allowed &&
                (crtc_req->mode.flags & DRM_MODE_FLAG_PIC_AR_MASK) != DRM_MODE_FLAG_PIC_AR_NONE) {
                DRM_DEBUG_KMS("Unexpected aspect-ratio flag bits\n");
                ret = -EINVAL;
                goto out;
            }

            //赋值操作
            ret = drm_mode_convert_umode(dev, mode, &crtc_req->mode);
            if (ret) {
                DRM_DEBUG_KMS("Invalid mode (ret=%d, status=%s)\n",
                          ret, drm_get_mode_status_name(mode->status));
                drm_mode_debug_printmodeline(mode);
                goto out;
            }

            /*
             * Check whether the primary plane supports the fb pixel format.
             * Drivers not implementing the universal planes API use a
             * default formats list provided by the DRM core which doesn't
             * match real hardware capabilities. Skip the check in that
             * case.
             */
            if (!plane->format_default) {
                //检查pixel format是否支持
                ret = drm_plane_check_pixel_format(plane,
                                   fb->format->format,
                                   fb->modifier);
                if (ret) {
                    struct drm_format_name_buf format_name;
                    DRM_DEBUG_KMS("Invalid pixel format %s, modifier 0x%llx\n",
                              drm_get_format_name(fb->format->format,
                                      &format_name),
                              fb->modifier);
                    goto out;
                }
            }

            //检查framebuffer是否足够大，能否满足crtc viewport
            ret = drm_crtc_check_viewport(crtc, crtc_req->x, crtc_req->y,
                              mode, fb);
            if (ret)
                goto out;

        }

        if (crtc_req->count_connectors == 0 && mode) {
            DRM_DEBUG_KMS("Count connectors is 0 but mode set\n");
            ret = -EINVAL;
            goto out;
        }

        if (crtc_req->count_connectors > 0 && (!mode || !fb)) {
            DRM_DEBUG_KMS("Count connectors is %d but no mode or fb set\n",
                  crtc_req->count_connectors);
            ret = -EINVAL;
            goto out;
        }

        if (crtc_req->count_connectors > 0) {
            u32 out_id;

            /* Avoid unbounded kernel memory allocation */
            if (crtc_req->count_connectors > config->num_connector) {
                ret = -EINVAL;
                goto out;
            }

            connector_set = kmalloc_array(crtc_req->count_connectors,
                              sizeof(struct drm_connector *),
                              GFP_KERNEL);
            if (!connector_set) {
                ret = -ENOMEM;
                goto out;
            }

            for (i = 0; i < crtc_req->count_connectors; i++) {
                connector_set[i] = NULL;
                set_connectors_ptr = (uint32_t __user *)(unsigned long)crtc_req->set_connectors_ptr;
                if (get_user(out_id, &set_connectors_ptr[i])) {
                    ret = -EFAULT;
                    goto out;
                }
                //找到crtc绑定链接的connector
                connector = drm_connector_lookup(dev, file_priv, out_id);
                if (!connector) {
                    DRM_DEBUG_KMS("Connector id %d unknown\n",
                            out_id);
                    ret = -ENOENT;
                    goto out;
                }
                DRM_DEBUG_KMS("[CONNECTOR:%d:%s]\n",
                        connector->base.id,
                        connector->name);

                connector_set[i] = connector;
            }
        }

        set.crtc = crtc;
        set.x = crtc_req->x;
        set.y = crtc_req->y;
        set.mode = mode;
        set.connectors = connector_set;
        set.num_connectors = crtc_req->count_connectors;
        set.fb = fb;
        //设置struct drm_mode_set结构体
        if (drm_drv_uses_atomic_modeset(dev))
            ret = crtc->funcs->set_config(&set, &ctx);
        else
            ret = __drm_mode_set_config_internal(&set, &ctx);

    out:
        if (fb)
            drm_framebuffer_put(fb);

        if (connector_set) {
            for (i = 0; i < crtc_req->count_connectors; i++) {
                if (connector_set[i])
                    drm_connector_put(connector_set[i]);
            }
        }
        kfree(connector_set);
        drm_mode_destroy(dev, mode);

        /* In case we need to retry... */
        connector_set = NULL;
        fb = NULL;
        mode = NULL;

        DRM_MODESET_LOCK_ALL_END(ctx, ret);
        mutex_unlock(&crtc->dev->mode_config.mutex);

        return ret;
    }


func的一些介绍
-------------------

::

    //crtc控制接口，一般填写helper函数
    struct drm_crtc_funcs {
        //重置软硬件state, 由drm_mode_config_reset调用，一般赋值为
        //drm_atomic_helper_crtc_reset
        void (*reset)(struct drm_crtc *crtc);

        //设置鼠标图片，width/height应该是鼠标的宽高，handle是鼠标图片buf(drm_gem_obj
        //该接口已经废弃，使用鼠标层代替
        int (*cursor_set)(struct drm_crtc *crtc, struct drm_file *file_priv,
                  uint32_t handle, uint32_t width, uint32_t height);

        //同上，多了hot_x, hot_y
        int (*cursor_set2)(struct drm_crtc *crtc, struct drm_file *file_priv,
                   uint32_t handle, uint32_t width, uint32_t height,
                   int32_t hot_x, int32_t hot_y);

        //移动鼠标操作
        int (*cursor_move)(struct drm_crtc *crtc, int x, int y);

        //gamma设置
        int (*gamma_set)(struct drm_crtc *crtc, u16 *r, u16 *g, u16 *b,
                 uint32_t size,
                 struct drm_modeset_acquire_ctx *ctx);

        //drm_mode_config_cleanup调用该接口
        void (*destroy)(struct drm_crtc *crtc);

        //设置crtc的fb/connector/mode的属性，对应用户态drmModeSetCrtc接口atomic modeset操作
        //使用drm_atomic_helper_set_config接口赋值
        int (*set_config)(struct drm_mode_set *set,
                  struct drm_modeset_acquire_ctx *ctx);

        //page翻转接口，vsync同步的
        int (*page_flip)(struct drm_crtc *crtc,
                 struct drm_framebuffer *fb,
                 struct drm_pending_vblank_event *event,
                 uint32_t flags,
                 struct drm_modeset_acquire_ctx *ctx);

        //和page_flip类似，但该接口会等待特定的vbank
        int (*page_flip_target)(struct drm_crtc *crtc,
                    struct drm_framebuffer *fb,
                    struct drm_pending_vblank_event *event,
                    uint32_t flags, uint32_t target,
                    struct drm_modeset_acquire_ctx *ctx);

        //设置属性
        int (*set_property)(struct drm_crtc *crtc,
                    struct drm_property *property, uint64_t val);

        //拷贝crtc的drm_crtc_state对象，一般赋值为drm_atomic_helper_crtc_duplicate_state
        struct drm_crtc_state *(*atomic_duplicate_state)(struct drm_crtc *crtc);

        void (*atomic_destroy_state)(struct drm_crtc *crtc,
                         struct drm_crtc_state *state);

        //atomic操作中设置特定属性到state中，该接口一般可由drm_atomic_set_property调用
        int (*atomic_set_property)(struct drm_crtc *crtc,
                       struct drm_crtc_state *state,
                       struct drm_property *property,
                       uint64_t val);
        //获取atomic属性
        int (*atomic_get_property)(struct drm_crtc *crtc,
                       const struct drm_crtc_state *state,
                       struct drm_property *property,
                       uint64_t *val);

        //drm_dev_register之后，调用该接口进行额外的crtc操作
        int (*late_register)(struct drm_crtc *crtc);

        //与late接口相反
        void (*early_unregister)(struct drm_crtc *crtc);

        //以下接口与crc相关
        int (*set_crc_source)(struct drm_crtc *crtc, const char *source);

        int (*verify_crc_source)(struct drm_crtc *crtc, const char *source,
                     size_t *values_cnt);
        const char *const *(*get_crc_sources)(struct drm_crtc *crtc,
                              size_t *count);

        //打印crtc的atomic state属性，一般由drm_atomic_print_state调用
        void (*atomic_print_state)(struct drm_printer *p,
                       const struct drm_crtc_state *state);

        //获取硬件vblank counter计数
        u32 (*get_vblank_counter)(struct drm_crtc *crtc);

        //使能vblank中断
        int (*enable_vblank)(struct drm_crtc *crtc);

        void (*disable_vblank)(struct drm_crtc *crtc);
    };

- struct drm_crtc_helper_funcs

::

    struct drm_crtc_helper_funcs {
        //电源管理接口，一般由drm_helper_connector_dpms调用
        void (*dpms)(struct drm_crtc *crtc, int mode);

        //为modeset做准备，一般就是调用dpms接口关闭crtc(DRM_MODE_DPMS_OFF)
        void (*prepare)(struct drm_crtc *crtc);

        //与prepare接口对应，在modeset完成后，调用该接口来enable crtc
        void (*commit)(struct drm_crtc *crtc);

        //检查显示mode的有效性
        enum drm_mode_status (*mode_valid)(struct drm_crtc *crtc,
                           const struct drm_display_mode *mode);

        //验证并修正mode,由drm_atomic_helper_check_modeset调用
        bool (*mode_fixup)(struct drm_crtc *crtc,
                   const struct drm_display_mode *mode,
                   struct drm_display_mode *adjusted_mode);

        //设置display mode, crtc_set_mode会调用该接口
        int (*mode_set)(struct drm_crtc *crtc, struct drm_display_mode *mode,
                struct drm_display_mode *adjusted_mode, int x, int y,
                struct drm_framebuffer *old_fb);

        //更新crtc的display mode, 但不会修改其primary plane配置
        void (*mode_set_nofb)(struct drm_crtc *crtc);

        //设置fb和显示位置，drm_crtc_helper_set_config会调用该接口
        int (*mode_set_base)(struct drm_crtc *crtc, int x, int y,
                     struct drm_framebuffer *old_fb);

        int (*mode_set_base_atomic)(struct drm_crtc *crtc,
                        struct drm_framebuffer *fb, int x, int y,
                        enum mode_set_atomic);

        //关闭crtc
        void (*disable)(struct drm_crtc *crtc);

        //检查待更新的drm_crtc_state
        int (*atomic_check)(struct drm_crtc *crtc,
                    struct drm_crtc_state *state);

        //多plane的atomic update之前需要调用该接口
        void (*atomic_begin)(struct drm_crtc *crtc,
                     struct drm_crtc_state *old_crtc_state);
        //多plane的atomic update之后需要调用该接口
        void (*atomic_flush)(struct drm_crtc *crtc,
                     struct drm_crtc_state *old_crtc_state);

        //atomic enable crtc
        void (*atomic_enable)(struct drm_crtc *crtc,
                      struct drm_crtc_state *old_crtc_state);

        void (*atomic_disable)(struct drm_crtc *crtc,
                       struct drm_crtc_state *old_crtc_state);
    };

rcar_du_crtc_create
------------------------

::

    rcar_du_crtc_create
        drm_crtc_init_with_planes
        drm_crtc_helper_add
        drm_crtc_vblank_off
        rcar_du_crtc_crc_init



::

    static const struct drm_crtc_helper_funcs crtc_helper_funcs = {
        .atomic_check = rcar_du_crtc_atomic_check,
        .atomic_begin = rcar_du_crtc_atomic_begin,
        .atomic_flush = rcar_du_crtc_atomic_flush,
        .atomic_enable = rcar_du_crtc_atomic_enable,
        .atomic_disable = rcar_du_crtc_atomic_disable,
        .mode_valid = rcar_du_crtc_mode_valid,
    };









