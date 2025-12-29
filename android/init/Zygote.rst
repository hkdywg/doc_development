zygote进程孵化器
==================


在Android系统中, ``JavaVM(Java虚拟机)`` 以及运行系统关键服务的 ``SystemServer`` 都是由 ``Zygote`` 来创建的，我们称它为孵化器．
它通过 ``fork`` 的形式来创建 ``应用程序进程`` 和 ``SystemServer进程`` ．  

zygote启动过程
------------------

在 ``init.rc`` 脚本中，启动了Zygote进程

::

    on late-init
        trigger early-fs

        # Mount fstab in init.{$device}.rc by mount_all command. Optional parameter
        # '--early' can be specified to skip entries with 'latemount'.
        # /system and /vendor must be mounted by the end of the fs stage,
        # while /data is optional.
        trigger fs
        trigger post-fs

        # Mount fstab in init.{$device}.rc by mount_all with '--late' parameter
        # to only mount entries with 'latemount'. This is needed if '--early' is
        # specified in the previous mount_all command on the fs stage.
        # With /system mounted and properties form /system + /factory available,
        # some services can be started.
        trigger late-fs

        # Now we can mount /data. File encryption requires keymaster to decrypt
        # /data, which in turn can only be loaded when system properties are present.
        trigger post-fs-data

        # Load persist properties and override properties (if enabled) from /data.
        trigger load_persist_props_action

        # Should be before netd, but after apex, properties and logging is available.
        trigger load_bpf_programs

        # Now we can start zygote for devices with file based encryption
        # 触发zygote-start
        trigger zygote-start

        # Remove a file to wake up anything waiting for firmware.
        trigger firmware_mounts_complete

        trigger early-boot
        trigger boot


::

    on zygote-start && property:ro.crypto.state=unencrypted
        # A/B update verifier that marks a successful boot.
        exec_start update_verifier_nonencrypted
        start statsd
        start netd
        # 启动zygote服务
        start zygote
        start zygote_secondary


init.rc文件中会import init.zygote64.rc文件

::

    # 服务进程名zygote
    # 运行的二进制文件是/system/bin/app_process64
    # 启动参数是 -Xzygote /system/bin --zygote --start_system-server 
    service zygote /system/bin/app_process64 -Xzygote /system/bin --zygote --start-system-server
        class main
        priority -20
        user root
        group root readproc reserved_disk
        socket zygote stream 660 root system        #创建socket
        socket usap_pool_primary stream 660 root system
        onrestart exec_background - system system -- /system/bin/vdc volume abort_fuse  #当前进程重启时执行的命令
        onrestart write /sys/power/state on
        onrestart restart audioserver
        onrestart restart cameraserver
        onrestart restart media
        onrestart restart netd
        onrestart restart wificond
        writepid /dev/cpuset/foreground/tasks   #创建子进程时，向/dev/cpuset/foreground/tasks写入pid


``start`` 命令有一个对应的执行函数 ``do_start()`` ,定义在 ``system/core/init/builtins.cpp`` 中

::

    // Builtin-function-map start
    const BuiltinFunctionMap& GetBuiltinFunctionMap() {
        constexpr std::size_t kMax = std::numeric_limits<std::size_t>::max();
        // clang-format off
        static const BuiltinFunctionMap builtin_functions = {
            {"bootchart",               {1,     1,    {false,  do_bootchart}}},
            {"chmod",                   {2,     2,    {true,   do_chmod}}},
            {"chown",                   {2,     3,    {true,   do_chown}}},
            {"class_reset",             {1,     1,    {false,  do_class_reset}}},
            {"class_reset_post_data",   {1,     1,    {false,  do_class_reset_post_data}}},
            {"class_restart",           {1,     1,    {false,  do_class_restart}}},
            {"class_start",             {1,     1,    {false,  do_class_start}}},
            {"class_start_post_data",   {1,     1,    {false,  do_class_start_post_data}}},
            {"class_stop",              {1,     1,    {false,  do_class_stop}}},
            {"copy",                    {2,     2,    {true,   do_copy}}},
            {"domainname",              {1,     1,    {true,   do_domainname}}},
            {"enable",                  {1,     1,    {false,  do_enable}}},
            {"exec",                    {1,     kMax, {false,  do_exec}}},
            {"exec_background",         {1,     kMax, {false,  do_exec_background}}},
            {"exec_start",              {1,     1,    {false,  do_exec_start}}},
            {"export",                  {2,     2,    {false,  do_export}}},
            {"hostname",                {1,     1,    {true,   do_hostname}}},
            {"ifup",                    {1,     1,    {true,   do_ifup}}},
            {"init_user0",              {0,     0,    {false,  do_init_user0}}},
            {"insmod",                  {1,     kMax, {true,   do_insmod}}},
            {"installkey",              {1,     1,    {false,  do_installkey}}},
            {"interface_restart",       {1,     1,    {false,  do_interface_restart}}},
            {"interface_start",         {1,     1,    {false,  do_interface_start}}},
            {"interface_stop",          {1,     1,    {false,  do_interface_stop}}},
            {"load_persist_props",      {0,     0,    {false,  do_load_persist_props}}},
            {"load_system_props",       {0,     0,    {false,  do_load_system_props}}},
            {"loglevel",                {1,     1,    {false,  do_loglevel}}},
            {"mark_post_data",          {0,     0,    {false,  do_mark_post_data}}},
            {"mkdir",                   {1,     6,    {true,   do_mkdir}}},
            // TODO: Do mount operations in vendor_init.
            // mount_all is currently too complex to run in vendor_init as it queues action triggers,
            // imports rc scripts, etc.  It should be simplified and run in vendor_init context.
            // mount and umount are run in the same context as mount_all for symmetry.
            {"mount_all",               {0,     kMax, {false,  do_mount_all}}},
            {"mount",                   {3,     kMax, {false,  do_mount}}},
            {"perform_apex_config",     {0,     0,    {false,  do_perform_apex_config}}},
            {"umount",                  {1,     1,    {false,  do_umount}}},
            {"umount_all",              {0,     1,    {false,  do_umount_all}}},
            {"update_linker_config",    {0,     0,    {false,  do_update_linker_config}}},
            {"readahead",               {1,     2,    {true,   do_readahead}}},
            {"remount_userdata",        {0,     0,    {false,  do_remount_userdata}}},
            {"restart",                 {1,     1,    {false,  do_restart}}},
            {"restorecon",              {1,     kMax, {true,   do_restorecon}}},
            {"restorecon_recursive",    {1,     kMax, {true,   do_restorecon_recursive}}},
            {"rm",                      {1,     1,    {true,   do_rm}}},
            {"rmdir",                   {1,     1,    {true,   do_rmdir}}},
            {"setprop",                 {2,     2,    {true,   do_setprop}}},
            {"setrlimit",               {3,     3,    {false,  do_setrlimit}}},
            {"start",                   {1,     1,    {false,  do_start}}},
            {"stop",                    {1,     1,    {false,  do_stop}}},
            {"swapon_all",              {0,     1,    {false,  do_swapon_all}}},
            {"enter_default_mount_ns",  {0,     0,    {false,  do_enter_default_mount_ns}}},
            {"symlink",                 {2,     2,    {true,   do_symlink}}},
            {"sysclktz",                {1,     1,    {false,  do_sysclktz}}},
            {"trigger",                 {1,     1,    {false,  do_trigger}}},
            {"verity_update_state",     {0,     0,    {false,  do_verity_update_state}}},
            {"wait",                    {1,     2,    {true,   do_wait}}},
            {"wait_for_prop",           {2,     2,    {false,  do_wait_for_prop}}},
            {"write",                   {2,     2,    {true,   do_write}}},
        };
        // clang-format on
        return builtin_functions;
    }

**do_start()**

::

    static Result<void> do_start(const BuiltinArguments& args) {
        Service* svc = ServiceList::GetInstance().FindService(args[1]);     //找到zygote service对应信息
        if (!svc) return Error() << "service " << args[1] << " not found";
        if (auto result = svc->Start(); !result.ok()) {                     //启动对应的进程
            return ErrorIgnoreEnoent() << "Could not start service: " << result.error();
        }
        return {};
    }


``do_start()`` 首先是通过 ``FindService`` 去 ``ServiceList`` 中遍历，根据名字匹配出对应的 ``service`` 

::

    Result<void> Service::Start() {

        ... ...

        pid_t pid = -1;
        if (namespaces_.flags) {
            pid = clone(nullptr, nullptr, namespaces_.flags | SIGCHLD, nullptr);
        } else {
            pid = fork();   //从init进程中fork出zygote进程
        }
         
        ... ...
    }


app_process64
-----------------

init.zygote64.rc启动文件的地址为 ``system/bin/app_process64``

``app_process64`` 对应的代码定义在 ``frameworks/base/cmds/app_process/app_main.cpp`` 

在app_main.cpp中主要做的事情就是参数解析，这个函数有两种启动模式

- ``zygote模式`` ,也就是初始化zygote进程，传递的参数有"--start-system-server --socket-name=zygote", 前者表示启动SystemServer, 后者指定socket的名称

- ``application模式`` ，也就是普通应用程序，传递参数有"class名字"以及"class带的参数"


::

    int main(int argc, char* const argv[])
    {
        //将参数argv放到argv_String字符串中
        if (!LOG_NDEBUG) {
          String8 argv_String;
          for (int i = 0; i < argc; ++i) {
            argv_String.append("\"");
            argv_String.append(argv[i]);
            argv_String.append("\" ");
          }
          ALOGV("app_process main with argv: %s", argv_String.string());
        }

        //AppRuntime定义于app_main.cpp中，继承自AndroidRuntime
        //就是对Android运行环境的一种抽象，类似于java虚拟机对java程序的作用
        AppRuntime runtime(argv[0], computeArgBlockSize(argc, argv));
        // Process command line arguments
        // ignore argv[0]
        argc--;
        argv++;
        //这两个参数是java程序需要依赖的jar包，相当于import
        const char* spaced_commands[] = { "-cp", "-classpath" };
        // Allow "spaced commands" to be succeeded by exactly 1 argument (regardless of -s).
        bool known_command = false;

        int i;
        for (i = 0; i < argc; i++) {
            if (known_command == true) {
              runtime.addOption(strdup(argv[i]));
              // The static analyzer gets upset that we don't ever free the above
              // string. Since the allocation is from main, leaking it doesn't seem
              // problematic. NOLINTNEXTLINE
              ALOGV("app_process main add known option '%s'", argv[i]);
              known_command = false;
              continue;
            }

            for (int j = 0;
                 j < static_cast<int>(sizeof(spaced_commands) / sizeof(spaced_commands[0]));
                 ++j) {
              if (strcmp(argv[i], spaced_commands[j]) == 0) {
                known_command = true;
                ALOGV("app_process main found known command '%s'", argv[i]);
              }
            }

            //如果参数的第一个字符是'-' ,直接跳出循环
            //之前传入的第一个参数是-Xzygote,所以执行到就直接跳出了
            if (argv[i][0] != '-') {
                break;
            }
            if (argv[i][1] == '-' && argv[i][2] == 0) {
                ++i; // Skip --.
                break;
            }

            runtime.addOption(strdup(argv[i]));
            // The static analyzer gets upset that we don't ever free the above
            // string. Since the allocation is from main, leaking it doesn't seem
            // problematic. NOLINTNEXTLINE
            ALOGV("app_process main add option '%s'", argv[i]);
        }
        // Parse runtime arguments.  Stop at first unrecognized option.
        //从这里其实可以看出，通过app_main可以启动zygote, systemserver,以及普通的apk进程
        bool zygote = false;
        bool startSystemServer = false;
        bool application = false;
        String8 niceName;           //app_process的名称该为zygote
        String8 className;          //启动apk进程时，对应的类名

        //跳过一个参数，之前跳过了-Xzygote,这里继续跳过/system/bin,也就是所谓的"parent dir"
        ++i;  // Skip unused "parent dir" argument.
        while (i < argc) {
            const char* arg = argv[i++];
            if (strcmp(arg, "--zygote") == 0) {     //表示是zygote启动模式
                zygote = true;
                niceName = ZYGOTE_NICE_NAME;        //修改名字，zygote64或zygote
            } else if (strcmp(arg, "--start-system-server") == 0) { //表示启动system-server
                startSystemServer = true;
            } else if (strcmp(arg, "--application") == 0) { //表示普通应用程序
                application = true;
            } else if (strncmp(arg, "--nice-name=", 12) == 0) {
                niceName.setTo(arg + 12);
            } else if (strncmp(arg, "--", 2) != 0) {
                className.setTo(arg);
                break;
            } else {
                --i;
                break;
            }
        }

        Vector<String8> args;
        if (!className.isEmpty()) { //classname不为空，说明是application启动模式
            // We're not in zygote mode, the only argument we need to pass
            // to RuntimeInit is the application argument.
            //
            // The Remainder of args get passed to startup class main(). Make
            // copies of them before we overwrite them with the process name.
            args.add(application ? String8("application") : String8("tool"));
            runtime.setClassNameAndArgs(className, argc - i, argv + i);

            if (!LOG_NDEBUG) {
              String8 restOfArgs;
              char* const* argv_new = argv + i;
              int argc_new = argc - i;
              for (int k = 0; k < argc_new; ++k) {
                restOfArgs.append("\"");
                restOfArgs.append(argv_new[k]);
                restOfArgs.append("\" ");
              }
              ALOGV("Class name = %s, args = %s", className.string(), restOfArgs.string());
            }
        } else {        //zygote启动模式
            // We're in zygote mode.
            maybeCreateDalvikCache();       //创建Dalvik的缓存目录并定义权限

            if (startSystemServer) {        //增加start-system-server参数
                args.add(String8("start-system-server"));
            }

            char prop[PROP_VALUE_MAX];      //获取平台对应的abi信息
            if (property_get(ABI_LIST_PROPERTY, prop, NULL) == 0) {
                LOG_ALWAYS_FATAL("app_process: Unable to determine ABI list from property %s.",
                    ABI_LIST_PROPERTY);
                return 11;
            }

            String8 abiFlag("--abi-list=");
            abiFlag.append(prop);
            args.add(abiFlag);              //加入 --abi-list=

            // In zygote mode, pass all remaining arguments to the zygote
            // main() method.
            for (; i < argc; ++i) {
                args.add(String8(argv[i]));
            }
        }

        if (!niceName.isEmpty()) {      //修改进程别名
            runtime.setArgv0(niceName.string(), true /* setProcName */);
        }
        if (zygote) {       //调用Runtime的start函数，启动ZygoteInit
            runtime.start("com.android.internal.os.ZygoteInit", args, zygote);
        } else if (className) {
            runtime.start("com.android.internal.os.RuntimeInit", args, zygote);
        } else {
            fprintf(stderr, "Error: no class name or --zygote supplied.\n");
            app_usage();
            LOG_ALWAYS_FATAL("app_process: no class name or --zygote supplied.");
        }
    }

由上可知， ``Zygote`` 是通过 ``runtime.start`` 函数启动，此处的 ``runtime`` 是 ``AppRuntime``

**AndroidRuntime**

由于 ``AppRuntime`` 继承自 ``AndroidRuntime`` ,且没有重写 ``start()方法`` ,因此 ``zygote`` 的流程进入到了 ``AndroidRuntie.cpp``

::

    void AndroidRuntime::start(const char* className, const Vector<String8>& options, bool zygote)
    {
        //log输出，环境变换获取
        ... ...
        /* start the virtual machine */
        JniInvocation jni_invocation;
        jni_invocation.Init(NULL);      //初始化JNI,加载libart.so
        JNIEnv* env;
        //创建虚拟机，启动大多数参数由系统属性决定，最终startVm利用JNI_CreateJavaVm创建出虚拟机
        if (startVm(&mJavaVM, &env, zygote, primary_zygote) != 0) {
            return;
        }

        //回调AppRuntime的onVmCreated函数
        //对于zygote进程的启动流程而言，无实际操作，表示虚拟创建完成，但里面是空实现
        onVmCreated(env);
        
        ... ...

        char* slashClassName = toSlashClassName(className != NULL ? className : "");
        jclass startClass = env->FindClass(slashClassName); //找到class文件
        if (startClass == NULL) {
            ALOGE("JavaVM unable to locate class '%s'\n", slashClassName);
            /* keep going */
        } else {
            jmethodID startMeth = env->GetStaticMethodID(startClass, "main",
                "([Ljava/lang/String;)V");      //通过反射找到zygoteInit的main函数
            if (startMeth == NULL) {
                ALOGE("JavaVM unable to find main() in '%s'\n", className);
                /* keep going */
            } else {
                env->CallStaticVoidMethod(startClass, startMeth, strArray); //调用zygoteInit的main函数

            }
        }


    }


::

    //frameworks/base/core/jni/AndroidRuntime.cpp
    /*
     * Register android native functions with the VM.
     */
    /*static*/ int AndroidRuntime::startReg(JNIEnv* env)
    {
        ATRACE_NAME("RegisterAndroidNatives");
        /*
         * This hook causes all future threads created in this process to be
         * attached to the JavaVM.  (This needs to go away in favor of JNI
         * Attach calls.)
         */
        //定义Android创建线程的func:: javaCreateThreadEtc，这个函数内部通过linux的clone来创建线程
        androidSetCreateThreadFunc((android_create_thread_fn) javaCreateThreadEtc);

        ALOGV("--- registering native functions ---\n");

        /*
         * Every "register" function calls one or more things that return
         * a local reference (e.g. FindClass).  Because we haven't really
         * started the VM yet, they're all getting stored in the base frame
         * and never released.  Use Push/Pop to manage the storage.
         */
        //创建一个200容量的局部引用作用域，这个局部引用其实就是局部变量
        env->PushLocalFrame(200);
        //注册JNI函数
        if (register_jni_procs(gRegJNI, NELEM(gRegJNI), env) < 0) {
            env->PopLocalFrame(NULL);
            return -1;
        }
        //释放局部引用作用域
        env->PopLocalFrame(NULL);

        //createJavaThread("fubar", quickTest, (void*) "hello");

        return 0;
    }

``startReg`` 函数主要通过 ``register_jni_procs`` 来注册JNI函数,其中 ``gRegJNI`` 是一个全局数组

::

    static const RegJNIRec gRegJNI[] = {
            REG_JNI(register_com_android_internal_os_RuntimeInit),
            REG_JNI(register_com_android_internal_os_ZygoteInit_nativeZygoteInit),
            REG_JNI(register_android_os_SystemClock),
            REG_JNI(register_android_util_EventLog),
            REG_JNI(register_android_util_Log),
            REG_JNI(register_android_util_MemoryIntArray),
            REG_JNI(register_android_app_admin_SecurityLog),
            REG_JNI(register_android_content_AssetManager),
            REG_JNI(register_android_content_StringBlock),
            REG_JNI(register_android_content_XmlBlock),
            REG_JNI(register_android_content_res_ApkAssets),
            REG_JNI(register_android_text_AndroidCharacter),
            REG_JNI(register_android_text_Hyphenator),
            REG_JNI(register_android_view_InputDevice),
            REG_JNI(register_android_view_KeyCharacterMap),
            REG_JNI(register_android_os_Process),
            REG_JNI(register_android_os_SystemProperties),
            REG_JNI(register_android_os_Binder),
            REG_JNI(register_android_os_Parcel),
            REG_JNI(register_android_os_HidlMemory),
            REG_JNI(register_android_os_HidlSupport),
            REG_JNI(register_android_os_HwBinder),
            REG_JNI(register_android_os_HwBlob),
            REG_JNI(register_android_os_HwParcel),
            REG_JNI(register_android_os_HwRemoteBinder),
            REG_JNI(register_android_os_NativeHandle),
            REG_JNI(register_android_os_ServiceManager),
            REG_JNI(register_android_os_storage_StorageManager),
            REG_JNI(register_android_os_VintfObject),
            REG_JNI(register_android_os_VintfRuntimeInfo),
            REG_JNI(register_android_service_DataLoaderService),
            REG_JNI(register_android_view_DisplayEventReceiver),
            REG_JNI(register_android_view_InputApplicationHandle),
            REG_JNI(register_android_view_InputWindowHandle),
            REG_JNI(register_android_view_Surface),
            REG_JNI(register_android_view_SurfaceControl),
            REG_JNI(register_android_view_SurfaceSession),
            REG_JNI(register_android_view_CompositionSamplingListener),
            REG_JNI(register_android_view_TextureView),
            REG_JNI(register_com_google_android_gles_jni_EGLImpl),
            REG_JNI(register_com_google_android_gles_jni_GLImpl),
            REG_JNI(register_android_opengl_jni_EGL14),
            REG_JNI(register_android_opengl_jni_EGL15),
            REG_JNI(register_android_opengl_jni_EGLExt),
            REG_JNI(register_android_opengl_jni_GLES10),
            REG_JNI(register_android_opengl_jni_GLES10Ext),
            REG_JNI(register_android_opengl_jni_GLES11),
            REG_JNI(register_android_opengl_jni_GLES11Ext),
            REG_JNI(register_android_opengl_jni_GLES20),
            REG_JNI(register_android_opengl_jni_GLES30),
            REG_JNI(register_android_opengl_jni_GLES31),
            REG_JNI(register_android_opengl_jni_GLES31Ext),
            REG_JNI(register_android_opengl_jni_GLES32),
            REG_JNI(register_android_graphics_classes),
            REG_JNI(register_android_graphics_BLASTBufferQueue),
            REG_JNI(register_android_graphics_GraphicBuffer),
            REG_JNI(register_android_graphics_SurfaceTexture),
            REG_JNI(register_android_database_CursorWindow),
            REG_JNI(register_android_database_SQLiteConnection),
            REG_JNI(register_android_database_SQLiteGlobal),
            REG_JNI(register_android_database_SQLiteDebug),
            REG_JNI(register_android_os_Debug),
            REG_JNI(register_android_os_FileObserver),
            REG_JNI(register_android_os_GraphicsEnvironment),
            REG_JNI(register_android_os_MessageQueue),
            REG_JNI(register_android_os_SELinux),
            REG_JNI(register_android_os_Trace),
            REG_JNI(register_android_os_UEventObserver),
            REG_JNI(register_android_net_LocalSocketImpl),
            REG_JNI(register_android_net_NetworkUtils),
            REG_JNI(register_android_os_MemoryFile),
            REG_JNI(register_android_os_SharedMemory),
            REG_JNI(register_android_os_incremental_IncrementalManager),
            REG_JNI(register_com_android_internal_content_om_OverlayConfig),
            REG_JNI(register_com_android_internal_os_ClassLoaderFactory),
            REG_JNI(register_com_android_internal_os_Zygote),
            REG_JNI(register_com_android_internal_os_ZygoteInit),
            REG_JNI(register_com_android_internal_util_VirtualRefBasePtr),
            REG_JNI(register_android_hardware_Camera),
            REG_JNI(register_android_hardware_camera2_CameraMetadata),
            REG_JNI(register_android_hardware_camera2_legacy_LegacyCameraDevice),
            REG_JNI(register_android_hardware_camera2_legacy_PerfMeasurement),
            REG_JNI(register_android_hardware_camera2_DngCreator),
            REG_JNI(register_android_hardware_display_DisplayManagerGlobal),
            REG_JNI(register_android_hardware_HardwareBuffer),
            REG_JNI(register_android_hardware_SensorManager),
            REG_JNI(register_android_hardware_SerialPort),
            REG_JNI(register_android_hardware_UsbDevice),
            REG_JNI(register_android_hardware_UsbDeviceConnection),
            REG_JNI(register_android_hardware_UsbRequest),
            REG_JNI(register_android_hardware_location_ActivityRecognitionHardware),
            REG_JNI(register_android_media_AudioDeviceAttributes),
            REG_JNI(register_android_media_AudioEffectDescriptor),
            REG_JNI(register_android_media_AudioSystem),
            REG_JNI(register_android_media_AudioRecord),
            REG_JNI(register_android_media_AudioTrack),
            REG_JNI(register_android_media_AudioAttributes),
            REG_JNI(register_android_media_AudioProductStrategies),
            REG_JNI(register_android_media_AudioVolumeGroups),
            REG_JNI(register_android_media_AudioVolumeGroupChangeHandler),
            REG_JNI(register_android_media_MediaMetrics),
            REG_JNI(register_android_media_MicrophoneInfo),
            REG_JNI(register_android_media_RemoteDisplay),
            REG_JNI(register_android_media_ToneGenerator),
            REG_JNI(register_android_media_midi),

            REG_JNI(register_android_opengl_classes),
            REG_JNI(register_android_server_NetworkManagementSocketTagger),
            REG_JNI(register_android_ddm_DdmHandleNativeHeap),
            REG_JNI(register_android_backup_BackupDataInput),
            REG_JNI(register_android_backup_BackupDataOutput),
            REG_JNI(register_android_backup_FileBackupHelperBase),
            REG_JNI(register_android_backup_BackupHelperDispatcher),
            REG_JNI(register_android_app_backup_FullBackup),
            REG_JNI(register_android_app_Activity),
            REG_JNI(register_android_app_ActivityThread),
            REG_JNI(register_android_app_NativeActivity),
            REG_JNI(register_android_util_jar_StrictJarFile),
            REG_JNI(register_android_view_InputChannel),
            REG_JNI(register_android_view_InputEventReceiver),
            REG_JNI(register_android_view_InputEventSender),
            REG_JNI(register_android_view_InputQueue),
            REG_JNI(register_android_view_KeyEvent),
            REG_JNI(register_android_view_MotionEvent),
            REG_JNI(register_android_view_PointerIcon),
            REG_JNI(register_android_view_VelocityTracker),
            REG_JNI(register_android_view_VerifiedKeyEvent),
            REG_JNI(register_android_view_VerifiedMotionEvent),

            REG_JNI(register_android_content_res_ObbScanner),
            REG_JNI(register_android_content_res_Configuration),

            REG_JNI(register_android_animation_PropertyValuesHolder),
            REG_JNI(register_android_security_Scrypt),
            REG_JNI(register_com_android_internal_content_NativeLibraryHelper),
            REG_JNI(register_com_android_internal_os_FuseAppLoop),
            REG_JNI(register_com_android_internal_os_KernelCpuUidBpfMapReader),
            REG_JNI(register_com_android_internal_os_KernelSingleUidTimeReader),
    };


.. note::
    - 在Andorid中，每个进程运行在对应的虚拟机上，因此zygote首先就会负责创建出虚拟机

    - 为了反射调用java代码，必须有对应的JNI函数，因此zygote进行JNI函数的注册


ZygoteInit
---------------

::

    public class ZygoteInit {
        ... ...

         public static void main(String argv[]) {
            //调用native函数，确保当前没有其他线程在运行，主要还是处于安全的考虑
            ZygoteHooks.startZygoteNoThreadCreation();
            ... ...
            try {
            ... ...
                boolean startSystemServer = false;
                String zygoteSocketName = "zygote";
                String abiList = null;
                boolean enableLazyPreload = false;
                //解析参数，得到上述变量的值
                for (int i = 1; i < argv.length; i++) {
                    if ("start-system-server".equals(argv[i])) {
                        startSystemServer = true;
                    } else if ("--enable-lazy-preload".equals(argv[i])) {
                        enableLazyPreload = true;
                    } else if (argv[i].startsWith(ABI_LIST_ARG)) {
                        abiList = argv[i].substring(ABI_LIST_ARG.length());
                    } else if (argv[i].startsWith(SOCKET_NAME_ARG)) {
                        zygoteSocketName = argv[i].substring(SOCKET_NAME_ARG.length());
                    } else {
                        throw new RuntimeException("Unknown command line argument: " + argv[i]);
                    }
                }
                ... ...
                if (!enableLazyPreload) {
                    bootTimingsTraceLog.traceBegin("ZygotePreload");
                    EventLog.writeEvent(LOG_BOOT_PROGRESS_PRELOAD_START,
                            SystemClock.uptimeMillis());
                    preload(bootTimingsTraceLog);   //默认情况，预加载信息
                    EventLog.writeEvent(LOG_BOOT_PROGRESS_PRELOAD_END,
                            SystemClock.uptimeMillis());
                    bootTimingsTraceLog.traceEnd(); // ZygotePreload
                }

              //创建zygoteserver对象
              zygoteServer = new ZygoteServer(isPrimaryZygote);

                if (startSystemServer) {
                    //启动systemserver
                    Runnable r = forkSystemServer(abiList, zygoteSocketName, zygoteServer);

                    // {@code r == null} in the parent (zygote) process, and {@code r != null} in the
                    // child (system_server) process.
                    if (r != null) {
                        r.run();
                        return;
                    }
                }

                Log.i(TAG, "Accepting command socket connections");

                // The select loop returns early in the child process after a fork and
                // loops forever in the zygote.
                //zygote进程进入无限循环，处理请求
                caller = zygoteServer.runSelectLoop(abiList);

            }
         }
    };


``Zygote.main`` 函数除了安全相关的内容外，主要的工作就是注册 server socket, 预加载，启动systemserver以及进入无限循环处理请求消息

::

        //frameworks/base/core/java/android/internal/os/ZygoteInit.java
        static void preload(TimingsTraceLog bootTimingsTraceLog) {
            Log.d(TAG, "begin preload");
            bootTimingsTraceLog.traceBegin("BeginPreload");
            beginPreload();
            bootTimingsTraceLog.traceEnd(); // BeginPreload
            bootTimingsTraceLog.traceBegin("PreloadClasses");
            preloadClasses();               //读取文件system/etc/preloaded-classes,然后通过反射加载对应的类
            bootTimingsTraceLog.traceEnd(); // PreloadClasses
            bootTimingsTraceLog.traceBegin("CacheNonBootClasspathClassLoaders");
            cacheNonBootClasspathClassLoaders();
            bootTimingsTraceLog.traceEnd(); // CacheNonBootClasspathClassLoaders
            bootTimingsTraceLog.traceBegin("PreloadResources");
            preloadResources();             //负责加载一些常用的系统资源
            bootTimingsTraceLog.traceEnd(); // PreloadResources
            Trace.traceBegin(Trace.TRACE_TAG_DALVIK, "PreloadAppProcessHALs");
            nativePreloadAppProcessHALs();
            Trace.traceEnd(Trace.TRACE_TAG_DALVIK);
            Trace.traceBegin(Trace.TRACE_TAG_DALVIK, "PreloadGraphicsDriver");
            maybePreloadGraphicsDriver();
            Trace.traceEnd(Trace.TRACE_TAG_DALVIK);
            preloadSharedLibraries();       //一些必要库
            preloadTextResources();         //语言相关的字符信息
            // Ask the WebViewFactory to do any initialization that must run in the zygote process,
            // for memory sharing purposes.
            WebViewFactory.prepareWebViewInZygote();
            endPreload();
            warmUpJcaProviders();           //安全相关的
            Log.d(TAG, "end preload");

            sPreloadComplete = true;
        }

为了让系统运行时更加流畅，在zygote启动的时候，调用 ``preload`` 进行了一些 ``预加载操作``








