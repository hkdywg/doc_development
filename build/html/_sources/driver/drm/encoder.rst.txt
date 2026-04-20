encoder代码分析
====================

struct drm_encoder结构体
---------------------------

::

    
    struct drm_encoder {
        struct drm_device *dev;
        struct list_head head;

        struct drm_mode_object base;
        char *name;
        /**
         * @encoder_type:
         *
         * One of the DRM_MODE_ENCODER_<foo> types in drm_mode.h. The following
         * encoder types are defined thus far:
         *
         * - DRM_MODE_ENCODER_DAC for VGA and analog on DVI-I/DVI-A.
         *
         * - DRM_MODE_ENCODER_TMDS for DVI, HDMI and (embedded) DisplayPort.
         *
         * - DRM_MODE_ENCODER_LVDS for display panels, or in general any panel
         *   with a proprietary parallel connector.
         *
         * - DRM_MODE_ENCODER_TVDAC for TV output (Composite, S-Video,
         *   Component, SCART).
         *
         * - DRM_MODE_ENCODER_VIRTUAL for virtual machine displays
         *
         * - DRM_MODE_ENCODER_DSI for panels connected using the DSI serial bus.
         *
         * - DRM_MODE_ENCODER_DPI for panels connected using the DPI parallel
         *   bus.
         *
         * - DRM_MODE_ENCODER_DPMST for special fake encoders used to allow
         *   mutliple DP MST streams to share one physical encoder.
         */
        int encoder_type;

        /**
         * @index: Position inside the mode_config.list, can be used as an array
         * index. It is invariant over the lifetime of the encoder.
         */
        unsigned index;

        /**
         * @possible_crtcs: Bitmask of potential CRTC bindings, using
         * drm_crtc_index() as the index into the bitfield. The driver must set
         * the bits for all &drm_crtc objects this encoder can be connected to
         * before calling drm_encoder_init().
         *
         * In reality almost every driver gets this wrong.
         *
         * Note that since CRTC objects can't be hotplugged the assigned indices
         * are stable and hence known before registering all objects.
         */
        uint32_t possible_crtcs;

        /**
         * @possible_clones: Bitmask of potential sibling encoders for cloning,
         * using drm_encoder_index() as the index into the bitfield. The driver
         * must set the bits for all &drm_encoder objects which can clone a
         * &drm_crtc together with this encoder before calling
         * drm_encoder_init(). Drivers should set the bit representing the
         * encoder itself, too. Cloning bits should be set such that when two
         * encoders can be used in a cloned configuration, they both should have
         * each another bits set.
         *
         * In reality almost every driver gets this wrong.
         *
         * Note that since encoder objects can't be hotplugged the assigned indices
         * are stable and hence known before registering all objects.
         */
        uint32_t possible_clones;

        /**
         * @crtc: Currently bound CRTC, only really meaningful for non-atomic
         * drivers.  Atomic drivers should instead check
         * &drm_connector_state.crtc.
         */
        struct drm_crtc *crtc;
        struct drm_bridge *bridge;
        const struct drm_encoder_funcs *funcs;
        const struct drm_encoder_helper_funcs *helper_private;
    };

- encoder_type 

::

    static const struct drm_prop_enum_list drm_encoder_enum_list[] = {
        { DRM_MODE_ENCODER_NONE, "None" },
        { DRM_MODE_ENCODER_DAC, "DAC" },
        { DRM_MODE_ENCODER_TMDS, "TMDS" },
        { DRM_MODE_ENCODER_LVDS, "LVDS" },
        { DRM_MODE_ENCODER_TVDAC, "TV" },
        { DRM_MODE_ENCODER_VIRTUAL, "Virtual" },
        { DRM_MODE_ENCODER_DSI, "DSI" },
        { DRM_MODE_ENCODER_DPMST, "DP MST" },
        { DRM_MODE_ENCODER_DPI, "DPI" },
    };

- struct drm_encoder_funcs

::

    struct drm_encoder_funcs {
        /**
         * @reset:
         *
         * Reset encoder hardware and software state to off. This function isn't
         * called by the core directly, only through drm_mode_config_reset().
         * It's not a helper hook only for historical reasons.
         */
        void (*reset)(struct drm_encoder *encoder);

        /**
         * @destroy:
         *
         * Clean up encoder resources. This is only called at driver unload time
         * through drm_mode_config_cleanup() since an encoder cannot be
         * hotplugged in DRM.
         */
        void (*destroy)(struct drm_encoder *encoder);

        /**
         * @late_register:
         *
         * This optional hook can be used to register additional userspace
         * interfaces attached to the encoder like debugfs interfaces.
         * It is called late in the driver load sequence from drm_dev_register().
         * Everything added from this callback should be unregistered in
         * the early_unregister callback.
         *
         * Returns:
         *
         * 0 on success, or a negative error code on failure.
         */
        int (*late_register)(struct drm_encoder *encoder);

        /**
         * @early_unregister:
         *
         * This optional hook should be used to unregister the additional
         * userspace interfaces attached to the encoder from
         * @late_register. It is called from drm_dev_unregister(),
         * early in the driver unload sequence to disable userspace access
         * before data structures are torndown.
         */
        void (*early_unregister)(struct drm_encoder *encoder);
    };


- drm_encoder_helper_funcs

::

    struct drm_encoder_helper_funcs {
        /**
         * @dpms:
         *
         * Callback to control power levels on the encoder.  If the mode passed in
         * is unsupported, the provider must use the next lowest power level.
         * This is used by the legacy encoder helpers to implement DPMS
         * functionality in drm_helper_connector_dpms().
         *
         * This callback is also used to disable an encoder by calling it with
         * DRM_MODE_DPMS_OFF if the @disable hook isn't used.
         *
         * This callback is used by the legacy CRTC helpers.  Atomic helpers
         * also support using this hook for enabling and disabling an encoder to
         * facilitate transitions to atomic, but it is deprecated. Instead
         * @enable and @disable should be used.
         */
        void (*dpms)(struct drm_encoder *encoder, int mode);

        /**
         * @mode_valid:
         *
         * This callback is used to check if a specific mode is valid in this
         * encoder. This should be implemented if the encoder has some sort
         * of restriction in the modes it can display. For example, a given
         * encoder may be responsible to set a clock value. If the clock can
         * not produce all the values for the available modes then this callback
         * can be used to restrict the number of modes to only the ones that
         * can be displayed.
         *
         * This hook is used by the probe helpers to filter the mode list in
         * drm_helper_probe_single_connector_modes(), and it is used by the
         * atomic helpers to validate modes supplied by userspace in
         * drm_atomic_helper_check_modeset().
         *
         * This function is optional.
         *
         * NOTE:
         *
         * Since this function is both called from the check phase of an atomic
         * commit, and the mode validation in the probe paths it is not allowed
         * to look at anything else but the passed-in mode, and validate it
         * against configuration-invariant hardward constraints. Any further
         * limits which depend upon the configuration can only be checked in
         * @mode_fixup or @atomic_check.
         *
         * RETURNS:
         *
         * drm_mode_status Enum
         */
        enum drm_mode_status (*mode_valid)(struct drm_encoder *crtc,
                           const struct drm_display_mode *mode);

        /**
         * @mode_fixup:
         *
         * This callback is used to validate and adjust a mode. The parameter
         * mode is the display mode that should be fed to the next element in
         * the display chain, either the final &drm_connector or a &drm_bridge.
         * The parameter adjusted_mode is the input mode the encoder requires. It
         * can be modified by this callback and does not need to match mode. See
         * also &drm_crtc_state.adjusted_mode for more details.
         *
         * This function is used by both legacy CRTC helpers and atomic helpers.
         * This hook is optional.
         *
         * NOTE:
         *
         * This function is called in the check phase of atomic modesets, which
         * can be aborted for any reason (including on userspace's request to
         * just check whether a configuration would be possible). Atomic drivers
         * MUST NOT touch any persistent state (hardware or software) or data
         * structures except the passed in adjusted_mode parameter.
         *
         * This is in contrast to the legacy CRTC helpers where this was
         * allowed.
         *
         * Atomic drivers which need to inspect and adjust more state should
         * instead use the @atomic_check callback. If @atomic_check is used,
         * this hook isn't called since @atomic_check allows a strict superset
         * of the functionality of @mode_fixup.
         *
         * Also beware that userspace can request its own custom modes, neither
         * core nor helpers filter modes to the list of probe modes reported by
         * the GETCONNECTOR IOCTL and stored in &drm_connector.modes. To ensure
         * that modes are filtered consistently put any encoder constraints and
         * limits checks into @mode_valid.
         *
         * RETURNS:
         *
         * True if an acceptable configuration is possible, false if the modeset
         * operation should be rejected.
         */
        bool (*mode_fixup)(struct drm_encoder *encoder,
                   const struct drm_display_mode *mode,
                   struct drm_display_mode *adjusted_mode);

        /**
         * @prepare:
         *
         * This callback should prepare the encoder for a subsequent modeset,
         * which in practice means the driver should disable the encoder if it
         * is running. Most drivers ended up implementing this by calling their
         * @dpms hook with DRM_MODE_DPMS_OFF.
         *
         * This callback is used by the legacy CRTC helpers.  Atomic helpers
         * also support using this hook for disabling an encoder to facilitate
         * transitions to atomic, but it is deprecated. Instead @disable should
         * be used.
         */
        void (*prepare)(struct drm_encoder *encoder);

        /**
         * @commit:
         *
         * This callback should commit the new mode on the encoder after a modeset,
         * which in practice means the driver should enable the encoder.  Most
         * drivers ended up implementing this by calling their @dpms hook with
         * DRM_MODE_DPMS_ON.
         *
         * This callback is used by the legacy CRTC helpers.  Atomic helpers
         * also support using this hook for enabling an encoder to facilitate
         * transitions to atomic, but it is deprecated. Instead @enable should
         * be used.
         */
        void (*commit)(struct drm_encoder *encoder);

        /**
         * @mode_set:
         *
         * This callback is used to update the display mode of an encoder.
         *
         * Note that the display pipe is completely off when this function is
         * called. Drivers which need hardware to be running before they program
         * the new display mode (because they implement runtime PM) should not
         * use this hook, because the helper library calls it only once and not
         * every time the display pipeline is suspend using either DPMS or the
         * new "ACTIVE" property. Such drivers should instead move all their
         * encoder setup into the @enable callback.
         *
         * This callback is used both by the legacy CRTC helpers and the atomic
         * modeset helpers. It is optional in the atomic helpers.
         *
         * NOTE:
         *
         * If the driver uses the atomic modeset helpers and needs to inspect
         * the connector state or connector display info during mode setting,
         * @atomic_mode_set can be used instead.
         */
        void (*mode_set)(struct drm_encoder *encoder,
                 struct drm_display_mode *mode,
                 struct drm_display_mode *adjusted_mode);

        /**
         * @atomic_mode_set:
         *
         * This callback is used to update the display mode of an encoder.
         *
         * Note that the display pipe is completely off when this function is
         * called. Drivers which need hardware to be running before they program
         * the new display mode (because they implement runtime PM) should not
         * use this hook, because the helper library calls it only once and not
         * every time the display pipeline is suspended using either DPMS or the
         * new "ACTIVE" property. Such drivers should instead move all their
         * encoder setup into the @enable callback.
         *
         * This callback is used by the atomic modeset helpers in place of the
         * @mode_set callback, if set by the driver. It is optional and should
         * be used instead of @mode_set if the driver needs to inspect the
         * connector state or display info, since there is no direct way to
         * go from the encoder to the current connector.
         */
        void (*atomic_mode_set)(struct drm_encoder *encoder,
                    struct drm_crtc_state *crtc_state,
                    struct drm_connector_state *conn_state);

        /**
         * @get_crtc:
         *
         * This callback is used by the legacy CRTC helpers to work around
         * deficiencies in its own book-keeping.
         *
         * Do not use, use atomic helpers instead, which get the book keeping
         * right.
         *
         * FIXME:
         *
         * Currently only nouveau is using this, and as soon as nouveau is
         * atomic we can ditch this hook.
         */
        struct drm_crtc *(*get_crtc)(struct drm_encoder *encoder);

        /**
         * @detect:
         *
         * This callback can be used by drivers who want to do detection on the
         * encoder object instead of in connector functions.
         *
         * It is not used by any helper and therefore has purely driver-specific
         * semantics. New drivers shouldn't use this and instead just implement
         * their own private callbacks.
         *
         * FIXME:
         *
         * This should just be converted into a pile of driver vfuncs.
         * Currently radeon, amdgpu and nouveau are using it.
         */
        enum drm_connector_status (*detect)(struct drm_encoder *encoder,
                            struct drm_connector *connector);

        /**
         * @atomic_disable:
         *
         * This callback should be used to disable the encoder. With the atomic
         * drivers it is called before this encoder's CRTC has been shut off
         * using their own &drm_crtc_helper_funcs.atomic_disable hook. If that
         * sequence is too simple drivers can just add their own driver private
         * encoder hooks and call them from CRTC's callback by looping over all
         * encoders connected to it using for_each_encoder_on_crtc().
         *
         * This callback is a variant of @disable that provides the atomic state
         * to the driver. If @atomic_disable is implemented, @disable is not
         * called by the helpers.
         *
         * This hook is only used by atomic helpers. Atomic drivers don't need
         * to implement it if there's no need to disable anything at the encoder
         * level. To ensure that runtime PM handling (using either DPMS or the
         * new "ACTIVE" property) works @atomic_disable must be the inverse of
         * @atomic_enable.
         */
        void (*atomic_disable)(struct drm_encoder *encoder,
                       struct drm_atomic_state *state);

        /**
         * @atomic_enable:
         *
         * This callback should be used to enable the encoder. It is called
         * after this encoder's CRTC has been enabled using their own
         * &drm_crtc_helper_funcs.atomic_enable hook. If that sequence is
         * too simple drivers can just add their own driver private encoder
         * hooks and call them from CRTC's callback by looping over all encoders
         * connected to it using for_each_encoder_on_crtc().
         *
         * This callback is a variant of @enable that provides the atomic state
         * to the driver. If @atomic_enable is implemented, @enable is not
         * called by the helpers.
         *
         * This hook is only used by atomic helpers, it is the opposite of
         * @atomic_disable. Atomic drivers don't need to implement it if there's
         * no need to enable anything at the encoder level. To ensure that
         * runtime PM handling works @atomic_enable must be the inverse of
         * @atomic_disable.
         */
        void (*atomic_enable)(struct drm_encoder *encoder,
                      struct drm_atomic_state *state);

        /**
         * @disable:
         *
         * This callback should be used to disable the encoder. With the atomic
         * drivers it is called before this encoder's CRTC has been shut off
         * using their own &drm_crtc_helper_funcs.disable hook.  If that
         * sequence is too simple drivers can just add their own driver private
         * encoder hooks and call them from CRTC's callback by looping over all
         * encoders connected to it using for_each_encoder_on_crtc().
         *
         * This hook is used both by legacy CRTC helpers and atomic helpers.
         * Atomic drivers don't need to implement it if there's no need to
         * disable anything at the encoder level. To ensure that runtime PM
         * handling (using either DPMS or the new "ACTIVE" property) works
         * @disable must be the inverse of @enable for atomic drivers.
         *
         * For atomic drivers also consider @atomic_disable and save yourself
         * from having to read the NOTE below!
         *
         * NOTE:
         *
         * With legacy CRTC helpers there's a big semantic difference between
         * @disable and other hooks (like @prepare or @dpms) used to shut down a
         * encoder: @disable is only called when also logically disabling the
         * display pipeline and needs to release any resources acquired in
         * @mode_set (like shared PLLs, or again release pinned framebuffers).
         *
         * Therefore @disable must be the inverse of @mode_set plus @commit for
         * drivers still using legacy CRTC helpers, which is different from the
         * rules under atomic.
         */
        void (*disable)(struct drm_encoder *encoder);

        /**
         * @enable:
         *
         * This callback should be used to enable the encoder. With the atomic
         * drivers it is called after this encoder's CRTC has been enabled using
         * their own &drm_crtc_helper_funcs.enable hook.  If that sequence is
         * too simple drivers can just add their own driver private encoder
         * hooks and call them from CRTC's callback by looping over all encoders
         * connected to it using for_each_encoder_on_crtc().
         *
         * This hook is only used by atomic helpers, it is the opposite of
         * @disable. Atomic drivers don't need to implement it if there's no
         * need to enable anything at the encoder level. To ensure that
         * runtime PM handling (using either DPMS or the new "ACTIVE" property)
         * works @enable must be the inverse of @disable for atomic drivers.
         */
        void (*enable)(struct drm_encoder *encoder);

        /**
         * @atomic_check:
         *
         * This callback is used to validate encoder state for atomic drivers.
         * Since the encoder is the object connecting the CRTC and connector it
         * gets passed both states, to be able to validate interactions and
         * update the CRTC to match what the encoder needs for the requested
         * connector.
         *
         * Since this provides a strict superset of the functionality of
         * @mode_fixup (the requested and adjusted modes are both available
         * through the passed in &struct drm_crtc_state) @mode_fixup is not
         * called when @atomic_check is implemented.
         *
         * This function is used by the atomic helpers, but it is optional.
         *
         * NOTE:
         *
         * This function is called in the check phase of an atomic update. The
         * driver is not allowed to change anything outside of the free-standing
         * state objects passed-in or assembled in the overall &drm_atomic_state
         * update tracking structure.
         *
         * Also beware that userspace can request its own custom modes, neither
         * core nor helpers filter modes to the list of probe modes reported by
         * the GETCONNECTOR IOCTL and stored in &drm_connector.modes. To ensure
         * that modes are filtered consistently put any encoder constraints and
         * limits checks into @mode_valid.
         *
         * RETURNS:
         *
         * 0 on success, -EINVAL if the state or the transition can't be
         * supported, -ENOMEM on memory allocation failure and -EDEADLK if an
         * attempt to obtain another state object ran into a &drm_modeset_lock
         * deadlock.
         */
        int (*atomic_check)(struct drm_encoder *encoder,
                    struct drm_crtc_state *crtc_state,
                    struct drm_connector_state *conn_state);
    };
    

drm_encoder_init
--------------------

::

    int drm_encoder_init(struct drm_device *dev,
                 struct drm_encoder *encoder,
                 const struct drm_encoder_funcs *funcs,
                 int encoder_type, const char *name, ...)
    {
        int ret;

        /* encoder index is used with 32bit bitmasks */
        if (WARN_ON(dev->mode_config.num_encoder >= 32))
            return -EINVAL;

        //与connector类似，生成一个类型为DRM_MODE_OBJECT_ENCODER的struct drm_mode_object结构体
        ret = drm_mode_object_add(dev, &encoder->base, DRM_MODE_OBJECT_ENCODER);
        if (ret)
            return ret;

        //初始化encoder成员变量
        encoder->dev = dev;
        encoder->encoder_type = encoder_type;
        encoder->funcs = funcs;
        if (name) {
            va_list ap;

            va_start(ap, name);
            encoder->name = kvasprintf(GFP_KERNEL, name, ap);
            va_end(ap);
        } else {
            encoder->name = kasprintf(GFP_KERNEL, "%s-%d",
                          drm_encoder_enum_list[encoder_type].name,
                          encoder->base.id);
        }
        if (!encoder->name) {
            ret = -ENOMEM;
            goto out_put;
        }

        //将encoder加入到结构体struct drm_mode_config的encoder链表中
        list_add_tail(&encoder->head, &dev->mode_config.encoder_list);
        encoder->index = dev->mode_config.num_encoder++;

    out_put:
        if (ret)
            drm_mode_object_unregister(dev, &encoder->base);

        return ret;
    }

- drm_mode_getencoder

::


    int drm_mode_getencoder(struct drm_device *dev, void *data,
                struct drm_file *file_priv)
    {
        struct drm_mode_get_encoder *enc_resp = data;
        struct drm_encoder *encoder;
        struct drm_crtc *crtc;

        if (!drm_core_check_feature(dev, DRIVER_MODESET))
            return -EOPNOTSUPP;

        //根据传入的id找到encoder
        encoder = drm_encoder_find(dev, file_priv, enc_resp->encoder_id);
        if (!encoder)
            return -ENOENT;

        drm_modeset_lock(&dev->mode_config.connection_mutex, NULL);
        //找到encoder适配的crtc
        crtc = drm_encoder_get_crtc(encoder);
        if (crtc && drm_lease_held(file_priv, crtc->base.id))
            enc_resp->crtc_id = crtc->base.id;
        else
            enc_resp->crtc_id = 0;
        drm_modeset_unlock(&dev->mode_config.connection_mutex);

        enc_resp->encoder_type = encoder->encoder_type;
        enc_resp->encoder_id = encoder->base.id;
        enc_resp->possible_crtcs = drm_lease_filter_crtcs(file_priv,
                                  encoder->possible_crtcs);
        enc_resp->possible_clones = encoder->possible_clones;

        return 0;
    }


rcar_du_encoder_init
-------------------------

::

    //drivers/gpu/drm/rcar-du/rcar_du_encoder.c
    int rcar_du_encoder_init(struct rcar_du_device *rcdu,
                 enum rcar_du_output output,
                 struct device_node *enc_node)
    {
        struct rcar_du_encoder *renc;
        struct drm_encoder *encoder;
        struct drm_bridge *bridge;
        int ret;

        renc = devm_kzalloc(rcdu->dev, sizeof(*renc), GFP_KERNEL);
        if (renc == NULL)
            return -ENOMEM;

        rcdu->encoders[output] = renc;
        renc->output = output;
        encoder = rcar_encoder_to_drm_encoder(renc);

        dev_dbg(rcdu->dev, "initializing encoder %pOF for output %u\n",
            enc_node, output);

        /*
         * Locate the DRM bridge from the DT node. For the DPAD outputs, if the
         * DT node has a single port, assume that it describes a panel and
         * create a panel bridge.
         */
        if ((output == RCAR_DU_OUTPUT_DPAD0 ||
             output == RCAR_DU_OUTPUT_DPAD1) &&
            rcar_du_encoder_count_ports(enc_node) == 1) {
            struct drm_panel *panel = of_drm_find_panel(enc_node);

            if (IS_ERR(panel)) {
                ret = PTR_ERR(panel);
                goto done;
            }

            bridge = devm_drm_panel_bridge_add(rcdu->dev, panel,
                               DRM_MODE_CONNECTOR_DPI);
            if (IS_ERR(bridge)) {
                ret = PTR_ERR(bridge);
                goto done;
            }
        } else {
            bridge = of_drm_find_bridge(enc_node);
            if (!bridge) {
                if (output == RCAR_DU_OUTPUT_HDMI0 ||
                    output == RCAR_DU_OUTPUT_HDMI1) {
    #if IS_ENABLED(CONFIG_DRM_RCAR_DW_HDMI)
                    ret = -EPROBE_DEFER;
    #else
                    ret = 0;
    #endif
                    goto done;
                } else if (output == RCAR_DU_OUTPUT_LVDS0 ||
                       output == RCAR_DU_OUTPUT_LVDS1) {
    #if IS_ENABLED(CONFIG_DRM_RCAR_LVDS)
                    ret = -EPROBE_DEFER;
    #else
                    ret = 0;
    #endif
                    goto done;
                } else if (output == RCAR_DU_OUTPUT_MIPI_DSI0 ||
                       output == RCAR_DU_OUTPUT_MIPI_DSI1) {
    #if IS_ENABLED(CONFIG_DRM_RCAR_MIPI_DSI)
                    ret = -EPROBE_DEFER;
    #else
                    ret = 0;
    #endif
                    goto done;
                } else {
                    ret = -EPROBE_DEFER;
                    goto done;
                }
            }

            if (output == RCAR_DU_OUTPUT_LVDS0 ||
                output == RCAR_DU_OUTPUT_LVDS1)
                rcdu->lvds[output - RCAR_DU_OUTPUT_LVDS0] = bridge;
        }

        /*
         * On Gen3 skip the LVDS1 output if the LVDS1 encoder is used as a
         * companion for LVDS0 in dual-link mode.
         */
        if (rcdu->info->gen >= 3 && output == RCAR_DU_OUTPUT_LVDS1) {
            if (rcar_lvds_dual_link(bridge)) {
                ret = -ENOLINK;
                goto done;
            }
        }

        renc->bridge = bridge;

        ret = drm_encoder_init(rcdu->ddev, encoder, &encoder_funcs,
                       DRM_MODE_ENCODER_NONE, NULL);
        if (ret < 0)
            goto done;

        drm_encoder_helper_add(encoder, &encoder_helper_funcs);

        /*
         * Attach the bridge to the encoder. The bridge will create the
         * connector.
         */
        ret = drm_bridge_attach(encoder, bridge, NULL);
        if (ret) {
            drm_encoder_cleanup(encoder);
            return ret;
        }

    done:
        if (ret < 0) {
            if (encoder->name)
                encoder->funcs->destroy(encoder);
            devm_kfree(rcdu->dev, renc);
        }

        return ret;
    }


- 调用关系

::

    rcar_du_probe
    |-- rcar_du_modeset_init
    |---|---drm_mode_config_init
        |---rcar_du_properties_init
        |---drm_vblank_init
        |---rcar_du_planes_init
        |---rcar_du_vsps_init
        |---rcar_du_crtc_create
        |---rcar_du_encoders_init
        |   |---rcar_du_encoders_init_one
        |       |---rcar_du_encoder_init
        |---rcar_du_writeback_init
    |---drm_dev_register
    |---drm_fbdev_generic_setup

