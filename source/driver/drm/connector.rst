connector代码分析
=======================

drm_connector结构体
---------------------

::

    struct drm_connector {
        /** @dev: parent DRM device */
        struct drm_device *dev;
        /** @kdev: kernel device for sysfs attributes */
        struct device *kdev;
        /** @attr: sysfs attributes */
        struct device_attribute *attr;

        /**
         * @head:
         *
         * List of all connectors on a @dev, linked from
         * &drm_mode_config.connector_list. Protected by
         * &drm_mode_config.connector_list_lock, but please only use
         * &drm_connector_list_iter to walk this list.
         */
        struct list_head head;

        /** @base: base KMS object */
        struct drm_mode_object base;

        /** @name: human readable name, can be overwritten by the driver */
        char *name;

        /**
         * @mutex: Lock for general connector state, but currently only protects
         * @registered. Most of the connector state is still protected by
         * &drm_mode_config.mutex.
         */
        struct mutex mutex;

        /**
         * @index: Compacted connector index, which matches the position inside
         * the mode_config.list for drivers not supporting hot-add/removing. Can
         * be used as an array index. It is invariant over the lifetime of the
         * connector.
         */
        unsigned index;

        /**
         * @connector_type:
         * one of the DRM_MODE_CONNECTOR_<foo> types from drm_mode.h
         */
        int connector_type;
        /** @connector_type_id: index into connector type enum */
        int connector_type_id;
        /**
         * @interlace_allowed:
         * Can this connector handle interlaced modes? Only used by
         * drm_helper_probe_single_connector_modes() for mode filtering.
         */
        bool interlace_allowed;
        /**
         * @doublescan_allowed:
         * Can this connector handle doublescan? Only used by
         * drm_helper_probe_single_connector_modes() for mode filtering.
         */
        bool doublescan_allowed;
        /**
         * @stereo_allowed:
         * Can this connector handle stereo modes? Only used by
         * drm_helper_probe_single_connector_modes() for mode filtering.
         */
        bool stereo_allowed;

        /**
         * @ycbcr_420_allowed : This bool indicates if this connector is
         * capable of handling YCBCR 420 output. While parsing the EDID
         * blocks it's very helpful to know if the source is capable of
         * handling YCBCR 420 outputs.
         */
        bool ycbcr_420_allowed;

        /**
         * @registration_state: Is this connector initializing, exposed
         * (registered) with userspace, or unregistered?
         *
         * Protected by @mutex.
         */
        enum drm_connector_registration_state registration_state;

        /**
         * @modes:
         * Modes available on this connector (from fill_modes() + user).
         * Protected by &drm_mode_config.mutex.
         */
        struct list_head modes;

        /**
         * @status:
         * One of the drm_connector_status enums (connected, not, or unknown).
         * Protected by &drm_mode_config.mutex.
         */
        enum drm_connector_status status;

        /**
         * @probed_modes:
         * These are modes added by probing with DDC or the BIOS, before
         * filtering is applied. Used by the probe helpers. Protected by
         * &drm_mode_config.mutex.
         */
        struct list_head probed_modes;

        /**
         * @display_info: Display information is filled from EDID information
         * when a display is detected. For non hot-pluggable displays such as
         * flat panels in embedded systems, the driver should initialize the
         * &drm_display_info.width_mm and &drm_display_info.height_mm fields
         * with the physical size of the display.
         *
         * Protected by &drm_mode_config.mutex.
         */
        struct drm_display_info display_info;

        /** @funcs: connector control functions */
        const struct drm_connector_funcs *funcs;

        /**
         * @edid_blob_ptr: DRM property containing EDID if present. Protected by
         * &drm_mode_config.mutex. This should be updated only by calling
         * drm_connector_update_edid_property().
         */
        struct drm_property_blob *edid_blob_ptr;

        /** @properties: property tracking for this connector */
        struct drm_object_properties properties;

        /**
         * @scaling_mode_property: Optional atomic property to control the
         * upscaling. See drm_connector_attach_content_protection_property().
         */
        struct drm_property *scaling_mode_property;

        /**
         * @vrr_capable_property: Optional property to help userspace
         * query hardware support for variable refresh rate on a connector.
         * connector. Drivers can add the property to a connector by
         * calling drm_connector_attach_vrr_capable_property().
         *
         * This should be updated only by calling
         * drm_connector_set_vrr_capable_property().
         */
        struct drm_property *vrr_capable_property;

        /**
         * @colorspace_property: Connector property to set the suitable
         * colorspace supported by the sink.
         */
        struct drm_property *colorspace_property;

        /**
         * @path_blob_ptr:
         *
         * DRM blob property data for the DP MST path property. This should only
         * be updated by calling drm_connector_set_path_property().
         */
        struct drm_property_blob *path_blob_ptr;

        /**
         * @max_bpc_property: Default connector property for the max bpc to be
         * driven out of the connector.
         */
        struct drm_property *max_bpc_property;

    #define DRM_CONNECTOR_POLL_HPD (1 << 0)
    #define DRM_CONNECTOR_POLL_CONNECT (1 << 1)
    #define DRM_CONNECTOR_POLL_DISCONNECT (1 << 2)

        /**
         * @polled:
         *
         * Connector polling mode, a combination of
         *
         * DRM_CONNECTOR_POLL_HPD
         *     The connector generates hotplug events and doesn't need to be
         *     periodically polled. The CONNECT and DISCONNECT flags must not
         *     be set together with the HPD flag.
         *
         * DRM_CONNECTOR_POLL_CONNECT
         *     Periodically poll the connector for connection.
         *
         * DRM_CONNECTOR_POLL_DISCONNECT
         *     Periodically poll the connector for disconnection, without
         *     causing flickering even when the connector is in use. DACs should
         *     rarely do this without a lot of testing.
         *
         * Set to 0 for connectors that don't support connection status
         * discovery.
         */
        uint8_t polled;

        /**
         * @dpms: Current dpms state. For legacy drivers the
         * &drm_connector_funcs.dpms callback must update this. For atomic
         * drivers, this is handled by the core atomic code, and drivers must
         * only take &drm_crtc_state.active into account.
         */
        int dpms;

        /** @helper_private: mid-layer private data */
        const struct drm_connector_helper_funcs *helper_private;

        /** @cmdline_mode: mode line parsed from the kernel cmdline for this connector */
        struct drm_cmdline_mode cmdline_mode;
        /** @force: a DRM_FORCE_<foo> state for forced mode sets */
        enum drm_connector_force force;
        /** @override_edid: has the EDID been overwritten through debugfs for testing? */
        bool override_edid;

    #define DRM_CONNECTOR_MAX_ENCODER 3
        /**
         * @encoder_ids: Valid encoders for this connector. Please only use
         * drm_connector_for_each_possible_encoder() to enumerate these.
         */
        uint32_t encoder_ids[DRM_CONNECTOR_MAX_ENCODER];

        /**
         * @encoder: Currently bound encoder driving this connector, if any.
         * Only really meaningful for non-atomic drivers. Atomic drivers should
         * instead look at &drm_connector_state.best_encoder, and in case they
         * need the CRTC driving this output, &drm_connector_state.crtc.
         */
        struct drm_encoder *encoder;

    #define MAX_ELD_BYTES	128
        /** @eld: EDID-like data, if present */
        uint8_t eld[MAX_ELD_BYTES];
        /** @latency_present: AV delay info from ELD, if found */
        bool latency_present[2];
        /**
         * @video_latency: Video latency info from ELD, if found.
         * [0]: progressive, [1]: interlaced
         */
        int video_latency[2];
        /**
         * @audio_latency: audio latency info from ELD, if found
         * [0]: progressive, [1]: interlaced
         */
        int audio_latency[2];

        /**
         * @ddc: associated ddc adapter.
         * A connector usually has its associated ddc adapter. If a driver uses
         * this field, then an appropriate symbolic link is created in connector
         * sysfs directory to make it easy for the user to tell which i2c
         * adapter is for a particular display.
         *
         * The field should be set by calling drm_connector_init_with_ddc().
         */
        struct i2c_adapter *ddc;

        /**
         * @null_edid_counter: track sinks that give us all zeros for the EDID.
         * Needed to workaround some HW bugs where we get all 0s
         */
        int null_edid_counter;

        /** @bad_edid_counter: track sinks that give us an EDID with invalid checksum */
        unsigned bad_edid_counter;

        /**
         * @edid_corrupt: Indicates whether the last read EDID was corrupt. Used
         * in Displayport compliance testing - Displayport Link CTS Core 1.2
         * rev1.1 4.2.2.6
         */
        bool edid_corrupt;

        /** @debugfs_entry: debugfs directory for this connector */
        struct dentry *debugfs_entry;

        /**
         * @state:
         *
         * Current atomic state for this connector.
         *
         * This is protected by &drm_mode_config.connection_mutex. Note that
         * nonblocking atomic commits access the current connector state without
         * taking locks. Either by going through the &struct drm_atomic_state
         * pointers, see for_each_oldnew_connector_in_state(),
         * for_each_old_connector_in_state() and
         * for_each_new_connector_in_state(). Or through careful ordering of
         * atomic commit operations as implemented in the atomic helpers, see
         * &struct drm_crtc_commit.
         */
        struct drm_connector_state *state;

        /* DisplayID bits. FIXME: Extract into a substruct? */

        /**
         * @tile_blob_ptr:
         *
         * DRM blob property data for the tile property (used mostly by DP MST).
         * This is meant for screens which are driven through separate display
         * pipelines represented by &drm_crtc, which might not be running with
         * genlocked clocks. For tiled panels which are genlocked, like
         * dual-link LVDS or dual-link DSI, the driver should try to not expose
         * the tiling and virtualize both &drm_crtc and &drm_plane if needed.
         *
         * This should only be updated by calling
         * drm_connector_set_tile_property().
         */
        struct drm_property_blob *tile_blob_ptr;

        /** @has_tile: is this connector connected to a tiled monitor */
        bool has_tile;
        /** @tile_group: tile group for the connected monitor */
        struct drm_tile_group *tile_group;
        /** @tile_is_single_monitor: whether the tile is one monitor housing */
        bool tile_is_single_monitor;

        /** @num_h_tile: number of horizontal tiles in the tile group */
        /** @num_v_tile: number of vertical tiles in the tile group */
        uint8_t num_h_tile, num_v_tile;
        /** @tile_h_loc: horizontal location of this tile */
        /** @tile_v_loc: vertical location of this tile */
        uint8_t tile_h_loc, tile_v_loc;
        /** @tile_h_size: horizontal size of this tile. */
        /** @tile_v_size: vertical size of this tile. */
        uint16_t tile_h_size, tile_v_size;

        /**
         * @free_node:
         *
         * List used only by &drm_connector_list_iter to be able to clean up a
         * connector from any context, in conjunction with
         * &drm_mode_config.connector_free_work.
         */
        struct llist_node free_node;

        /** @hdr_sink_metadata: HDR Metadata Information read from sink */
        struct hdr_sink_metadata hdr_sink_metadata;
    };


drm_connector的主要初始化接口为 ``drm_connector_init``

- drm_connector_init

::

    int drm_connector_init(struct drm_device *dev,
                   struct drm_connector *connector,
                   const struct drm_connector_funcs *funcs,
                   int connector_type)
    {
        //获取drm_mode_config结构体，一个drm设备只有一个struct drm_mode_config结构体
        //里面配置了一些参数
        struct drm_mode_config *config = &dev->mode_config;
        int ret;
        //获取connector_ida，后面会分配
        struct ida *connector_ida =
            &drm_connector_enum_list[connector_type].ida;

        WARN_ON(drm_drv_uses_atomic_modeset(dev) &&
            (!funcs->atomic_destroy_state ||
             !funcs->atomic_duplicate_state));

        //生成类型为DRM_MODE_OBJECT_CONNECTOR的struct drm_mode_object结构体
        //connector->base.id会在用户态接口drmModeGetResources调用时，作为connector_id返回用户态
        //后续用户态可以通过connector_id，调用drmModeGetConnector找到drm_connector，并获取相关参数
        ret = __drm_mode_object_add(dev, &connector->base,
                        DRM_MODE_OBJECT_CONNECTOR,
                        false, drm_connector_free);
        if (ret)
            return ret;

        //得到properties
        connector->base.properties = &connector->properties;
        connector->dev = dev;
        connector->funcs = funcs;

        //生成drm_mode_config的connector_ida并作为该connector的index索引
        /* connector index is used with 32bit bitmasks */
        ret = ida_simple_get(&config->connector_ida, 0, 32, GFP_KERNEL);
        if (ret < 0) {
            DRM_DEBUG_KMS("Failed to allocate %s connector index: %d\n",
                      drm_connector_enum_list[connector_type].name,
                      ret);
            goto out_put;
        }
        connector->index = ret;
        ret = 0;

        //生成该connector的type的connector_ida
        connector->connector_type = connector_type;
        connector->connector_type_id =
            ida_simple_get(connector_ida, 1, 0, GFP_KERNEL);
        if (connector->connector_type_id < 0) {
            ret = connector->connector_type_id;
            goto out_put_id;
        }
        //初始化connector名称及链表，mutex等
        connector->name =
            kasprintf(GFP_KERNEL, "%s-%d",
                  drm_connector_enum_list[connector_type].name,
                  connector->connector_type_id);
        if (!connector->name) {
            ret = -ENOMEM;
            goto out_put_type_id;
        }

        INIT_LIST_HEAD(&connector->probed_modes);
        INIT_LIST_HEAD(&connector->modes);
        mutex_init(&connector->mutex);
        connector->edid_blob_ptr = NULL;
        connector->tile_blob_ptr = NULL;
        connector->status = connector_status_unknown;
        connector->display_info.panel_orientation =
            DRM_MODE_PANEL_ORIENTATION_UNKNOWN;

        drm_connector_get_cmdline_mode(connector);

        /* We should add connectors at the end to avoid upsetting the connector
         * index too much. */
        spin_lock_irq(&config->connector_list_lock);
        list_add_tail(&connector->head, &config->connector_list);
        config->num_connector++;
        spin_unlock_irq(&config->connector_list_lock);

        if (connector_type != DRM_MODE_CONNECTOR_VIRTUAL &&
            connector_type != DRM_MODE_CONNECTOR_WRITEBACK)
            drm_connector_attach_edid_property(connector);

        drm_object_attach_property(&connector->base,
                          config->dpms_property, 0);

        drm_object_attach_property(&connector->base,
                       config->link_status_property,
                       0);

        drm_object_attach_property(&connector->base,
                       config->non_desktop_property,
                       0);
        drm_object_attach_property(&connector->base,
                       config->tile_property,
                       0);

        if (drm_core_check_feature(dev, DRIVER_ATOMIC)) {
            drm_object_attach_property(&connector->base, config->prop_crtc_id, 0);
        }

        connector->debugfs_entry = NULL;
    out_put_type_id:
        if (ret)
            ida_simple_remove(connector_ida, connector->connector_type_id);
    out_put_id:
        if (ret)
            ida_simple_remove(&config->connector_ida, connector->index);
    out_put:
        if (ret)
            drm_mode_object_unregister(dev, &connector->base);

        return ret;
    }




用户态操作
-----------------

- 用户态获取connector_id逻辑

::

    //用户态
    drmModeGetResources
        drmIoctl(fd, DRM_IOCTL_MODE_GETRESOURCES, &res)
        //res.crtc_id_ptr指向设备的所有crtc_id

    //内核态
    DRM_IOCTL_DEF(DRM_IOCTL_MODE_GETRESOURCES, drm_mode_getresources, 0)
        drm_mode_getresources
            drm_connector_list_iter_begin(dev, &conn_iter)
                drm_for_each_connector_iter(connector, &conn_iter)  //遍历connector
                    put_user(connector->base.id, connector_id + count)  //拷贝id到用户态
            drm_connector_list_iter_end(&conn_iter)



- 用户态根据connector_id获取drm_connector

::

    //用户态
    drmModeGetConnector()
        conn.connector_id = connector_id
        drmIoctl(fd, DRM_IOCTL_MODE_GETCONNECTOR, &conn)

    //内核态
    DRM_IOCTL_DEF(DRM_IOCTL_MODE_GETCONNECTOR, drm_mode_getconnector, 0)
        drm_mode_getconnector
            connector = drm_connector_lookup(dev, file_priv, out_resp->connector_id)
            //根据用户态传进来的id和type
            mo = drm_mode_object_find(dev, file_priv, id, DRM_MODE_OBJECT_CONNECTOR)
            return obj_to_connector(mo)


- base.properties

记录connector的属性(如CRTC_ID/EDID/等),这些属性首先在drm_mode_create_standard_properties创建初始化并保存在
dev->mode_config中

::

    //以CRTC_ID属性为例
    drm_mode_config_init
        drmm_mode_config_init
            drm_mode_create_standard_properties
                //创建名称为DRTC_ID的属性
                prop = drm_property_create_object(dev, DRM_MODE_PROP_ATOMIC, "CRTC_ID", DRM_MDOE_OBJECT_CRTC)
                    //创建属性
                    drm_property_create
                        //将该property保存在mode_config的property_list链表
                        list_add_tail(&property->head, &dev->mode_config.property_list)
                //保存到mode_config.prop_crtc_id中
                dev->mode_config.prop_crtc_id = prop


- properties的获取

::

    //用户态
    drmModeObjectGetProperties
        //通过connector_id以及DRM_MODE_OBJECT_CONNECTOR获取其属性
        drmIoctl(fd, DRM_IOCTL_MODE_OBJ_GETPROPERTIES, &properties)

    //内核态
    DRM_IOCTL_DEF(DRM_IOCTL_MODE_OBJ_GETPROPERTIES, drm_mode_obj_get_properties_ioctl, 0)
        //根据obj_id(connector_id)和obj_type(DRM_MODE_OBJECT_CONNECTOR)获取connector的drm_mode_object实例obj
        obj = drm_mode_object_find(dev, file_priv, arg->obj_id, arg->obj_type)
        //遍历connector->base.properties并拷贝到用户态
        //这里仅拷贝了properties的id和value，并没有拷贝名称
        drm_mode_object_get_properties(obj, file_priv->atomic, arg->props_ptr, arg->prop_values_ptr, ...)


    //上述获取的是connector的所有属性id, value, 如果要获取特定名称的属性，还需如下操作
    //用户态
    drmModeGetProperty
        drmIoctl(fd, DRM_IOCTL_MODE_GETPROPERTY, &prop)
    //内核态
    DRM_IOCTL_DEF(DRM_IOCTL_MODE_GETPROPERTY, drm_mode_getproperty_ioctl, 0)














