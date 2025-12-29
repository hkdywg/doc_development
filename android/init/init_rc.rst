init.rc
=============


init.rc语法
----------------

init.rc是一个配置文件，由Android初始化语言(Android Init Language)编写，编写的脚本init.rc是在init进程启动后执行的启动脚本.
init.rc主要包含5种类型语句．

- Action

- Command

- Service

- Option

- Import

1. 所有这些都是以行为单位,各种记号由空格来隔开．

2. C语言风格的反斜杠可用于记号间插入空格．

3. 双引号也可用于防止字符串被空格分割成多个记号

4. 行末的反斜杠用于折行，注释行以井号开头(允许以空格开头)


.. note::
    这指示一个语法文件，就像一个xml文件一样，没有执行顺序的，解析器通过读这个文件获取想要的数据，包括service, action.
    Action和Service声明一个新的分组Section.所有的命令或选项都属于最近声明的分组．位于第一个分组之前的命令或选项将会被
    忽略．Action和Service都有唯一的名字．如有重名的情况，第二个申明的将会被作为错误忽略


``init.rc`` 文件大致分为两大部分

- 一部分是以 ``on`` 关键字开头的"动作列表"(action list)

**Action类型语句格式**

::

    on <trigger> [&& <trigger>] ##设置触发器
        <command>
        <command>               ##动作触发之后执行的命令
        ...

.. note::
    trigger触发器本质上是一个字符串，能够匹配某种包含该字符串的事件．trigger又被细分为事件触发器(event trigger)和属性触发器(property trigger).
    一个Action可以有多个属性触发器，但是最多有一个事件触发器

几种常见的事件触发器

============================    =========================================================================
  类型　                                    说明
----------------------------    -------------------------------------------------------------------------
 boot                            init.rc被装载后触发
 device-added-<path>             指定设备被添加时触发
 device-removed-<path>           指定设备被移除时触发
 service-exited-<name>           在特定服务(service)退出时触发
 early-init                      初始化之前触发
 late-init                       初始化之后触发
 init                            初始化时触发(在/init.conf启动配置文件被装载之后)
============================    =========================================================================

- 另一部分是以"Service"关键字开头的"服务列表"(service list)

**Service类型语句格式**

::

    Service <name> <pathname> [ <argument> ]    ##<Service的名字><执行程序路径><传递参数>
        <option>                                ##option是service的修饰词，影响什么时候，如何启动service
        <option>
        ...

.. note::
    option是service的可选项，与service配合使用

    - oneshot: service退出后不再重启

    - onrestart: 当服务重启时，执行相应的命令


init.rc注释
---------------

::

    # Copyright (C) 2012 The Android Open Source Project
    #
    # IMPORTANT: Do not create world writable files or directories.
    # This is a common source of Android security bugs.
    #

    ## import <filename>, 插入一个init配置文件，扩展当前配置
    import /init.environ.rc
    import /system/etc/init/hw/init.usb.rc
    import /init.${ro.hardware}.rc
    import /vendor/etc/init/hw/init.${ro.hardware}.rc
    import /system/etc/init/hw/init.usb.configfs.rc
    import /system/etc/init/hw/init.${ro.zygote}.rc

    # 触发条件early-init,在early-init阶段调用以下命令
    # Cgroups are mounted right before early-init using list from /etc/cgroups.json
    on early-init
        # 打开文件/proc/sys/kernel/sysrq,并写入0
        # Disable sysrq from keyboard
        write /proc/sys/kernel/sysrq 0

        # Android doesn't need kernel module autoloading, and it causes SELinux
        # denials.  So disable it by setting modprobe to the empty string.  Note: to
        # explicitly set a sysctl to an empty string, a trailing newline is needed.
        write /proc/sys/kernel/modprobe \n

        # Set the security context of /adb_keys if present.
        # 恢复指定文件到file_contexts配置中指定的安全上下文环境
        restorecon /adb_keys

        # Set the security context of /postinstall if present.
        restorecon /postinstall

        # 创建目录
        mkdir /acct/uid

        # memory.pressure_level used by lmkd
        chown root system /dev/memcg/memory.pressure_level
        chmod 0040 /dev/memcg/memory.pressure_level
        # app mem cgroups, used by activity manager, lmkd and zygote
        mkdir /dev/memcg/apps/ 0755 system system
        # cgroup for system_server and surfaceflinger
        # mkdir <path> [mode] [owner] [group],如果没有指定，默认权限为755,属于root用户和root组
        mkdir /dev/memcg/system 0550 system system

        # symlink the Android specific /dev/tun to Linux expected /dev/net/tun
        mkdir /dev/net 0755 root root
        # 创建软连接
        symlink ../tun /dev/net/tun

        # set RLIMIT_NICE to allow priorities from 19 to -20
        # 执行start ueventd．ueventd是一个service，后面有定义
         start ueventd

        ... ...

        # Healthd can trigger a full boot from charger mode by signaling this
        # property when the power button is held.
        # 属性触发器，在sys.boot_from_charger_mode=1时执行下述命令 
        on property:sys.boot_from_charger_mode=1
        # 停止指定类别服务类下的所有已运行的服务
            class_stop charger
        # 触发一个事件，将该action排在某个action之后(用于action排队)
            trigger late-init

        ... ...

        # Mount filesystems and start core system services.
        # 上面触发的late-init事件
        on late-init
            trigger early-fs

            # Mount fstab in init.{$device}.rc by mount_all command. Optional parameter
            # '--early' can be specified to skip entries with 'latemount'.
            # /system and /vendor must be mounted by the end of the fs stage,
            # while /data is optional.
            trigger fs
            trigger post-fs

        ... ...

        on boot
            # basic network init
            # 初始化网络
            ifup lo
            hostname localhost
            domainname localdomain

        ... ...

        # 控制台进程
        service console /system/bin/sh
            # 为当前service设定一个类别，相同类别的服务将会同时启动或者停止，默认类名是default
            class core
            # 服务需要一个控制台
            console
            # 服务不会自动启动，必须通过服务名显示启动
            disabled
            # 在执行此服务之前切换用户名，当前默认的是root
            user shell
            group shell log readproc
            seclabel u:r:shell:s0
            setenv HOSTNAME console



init.rc代码解析
------------------

**LoadBootScripts**

::

    // system/core/init/init.cpp

    static void LoadBootScripts(ActionManager& action_manager, ServiceList& service_list) {
        //创建解析器 parser
        Parser parser = CreateParser(action_manager, service_list);
        std::string bootscript = GetProperty("ro.boot.init_rc", "");
        //如果bootscript不存在则解析init.rc文件
        if (bootscript.empty()) {
            //实际的解析过程
            parser.ParseConfig("/system/etc/init/hw/init.rc");
            if (!parser.ParseConfig("/system/etc/init")) {
                late_import_paths.emplace_back("/system/etc/init");
            }
            // late_import is available only in Q and earlier release. As we don't
            // have system_ext in those versions, skip late_import for system_ext.
            parser.ParseConfig("/system_ext/etc/init");
            if (!parser.ParseConfig("/product/etc/init")) {
                late_import_paths.emplace_back("/product/etc/init");
            }
            if (!parser.ParseConfig("/odm/etc/init")) {
                late_import_paths.emplace_back("/odm/etc/init");
            }
            if (!parser.ParseConfig("/vendor/etc/init")) {
                late_import_paths.emplace_back("/vendor/etc/init");
            }
        } else {
            parser.ParseConfig(bootscript);
        }
    }


**CreateParser**

::

    Parser CreateParser(ActionManager& action_manager, ServiceList& service_list) {
        Parser parser;
        //添加一个ServiceParser, 解析service
        parser.AddSectionParser("service", std::make_unique<ServiceParser>(
                                                   &service_list, GetSubcontext(), std::nullopt));
        //添加一个ActionParser, 解析On
        parser.AddSectionParser("on", std::make_unique<ActionParser>(&action_manager, GetSubcontext()));
        //添加一个ImportParser, 解析import
        parser.AddSectionParser("import", std::make_unique<ImportParser>(&parser));
        return parser;
    }


**parser.ParseConfig**

::

    bool Parser::ParseConfig(const std::string& path) {
        if (is_dir(path.c_str())) {         //判断传入参数是否为目录地址
            return ParseConfigDir(path);    //递归目录，最终仍是调用ParseConfigFile来解析实际的文件
        }
        return ParseConfigFile(path);       //传入参数为文件地址，则直接解析
    }


**ParseConfigDir**


::

    bool Parser::ParseConfigDir(const std::string& path) {
        LOG(INFO) << "Parsing directory " << path << "...";
        std::unique_ptr<DIR, decltype(&closedir)> config_dir(opendir(path.c_str()), closedir);
        if (!config_dir) {
            PLOG(INFO) << "Could not import directory '" << path << "'";
            return false;
        }
        dirent* current_file;
        std::vector<std::string> files;
        while ((current_file = readdir(config_dir.get()))) {
            // Ignore directories and only process regular files.
            if (current_file->d_type == DT_REG) {
                std::string current_path =
                    android::base::StringPrintf("%s/%s", path.c_str(), current_file->d_name);
                files.emplace_back(current_path);
            }
        }
        // Sort first so we load files in a consistent order (bug 31996208)
        std::sort(files.begin(), files.end());
        for (const auto& file : files) {
            //调用ParseConfigFile函数解析
            if (!ParseConfigFile(file)) {
                LOG(ERROR) << "could not import file '" << file << "'";
            }
        }
        return true;
    }


**ParseConfigFile**

::

    bool Parser::ParseConfigFile(const std::string& path) {
        LOG(INFO) << "Parsing file " << path << "...";
        android::base::Timer t;
        auto config_contents = ReadFile(path);  //读取指定文件的内容，保存为字符串形式
        if (!config_contents.ok()) {
            LOG(INFO) << "Unable to read config file '" << path << "': " << config_contents.error();
            return false;
        }

        ParseData(path, &config_contents.value());  //解析获取的字符串
        
        LOG(VERBOSE) << "(Parsing " << path << " took " << t << ".)";
        return true;
    }   


**ParseData**

::

    void Parser::ParseData(const std::string& filename, std::string* data) {
        data->push_back('\n');  // TODO: fix tokenizer
        data->push_back('\0');

        //解析用的结构体
        parse_state state;
        state.line = 0;
        state.ptr = data->data();
        state.nexttoken = 0;

        SectionParser* section_parser = nullptr;
        int section_start_line = -1;
        std::vector<std::string> args;

        // If we encounter a bad section start, there is no valid parser object to parse the subsequent
        // sections, so we must suppress errors until the next valid section is found.
        bool bad_section_found = false;

        auto end_section = [&] {
            bad_section_found = false;
            if (section_parser == nullptr) return;

            if (auto result = section_parser->EndSection(); !result.ok()) {
                parse_error_count_++;
                LOG(ERROR) << filename << ": " << section_start_line << ": " << result.error();
            }

            section_parser = nullptr;
            section_start_line = -1;
        };

        for (;;) {
            //next_token以行为单位分割参数传递过来的字符串
            switch (next_token(&state)) {
                case T_EOF:
                    end_section();  //解析结束

                    for (const auto& [section_name, section_parser] : section_parsers_) {
                        section_parser->EndFile();
                    }
                    return;
                case T_NEWLINE: {
                    state.line++;
                    if (args.empty()) break;
                    // If we have a line matching a prefix we recognize, call its callback and unset any
                    // current section parsers.  This is meant for /sys/ and /dev/ line entries for
                    // uevent.
                    auto line_callback = std::find_if(
                        line_callbacks_.begin(), line_callbacks_.end(),
                        [&args](const auto& c) { return android::base::StartsWith(args[0], c.first); });
                    if (line_callback != line_callbacks_.end()) {
                        end_section();

                        if (auto result = line_callback->second(std::move(args)); !result.ok()) {
                            parse_error_count_++;
                            LOG(ERROR) << filename << ": " << state.line << ": " << result.error();
                        }
                    } else if (section_parsers_.count(args[0])) {
                        end_section();  //结束上一个parser的工作
                        section_parser = section_parsers_[args[0]].get();
                        section_start_line = state.line;
                        if (auto result =
                                    section_parser->ParseSection(std::move(args), filename, state.line);
                            !result.ok()) {
                            parse_error_count_++;
                            LOG(ERROR) << filename << ": " << state.line << ": " << result.error();
                            section_parser = nullptr;
                            bad_section_found = true;
                        }
                    } else if (section_parser) {
                        if (auto result = section_parser->ParseLineSection(std::move(args), state.line);
                            !result.ok()) {
                            parse_error_count_++;
                            LOG(ERROR) << filename << ": " << state.line << ": " << result.error();
                        }
                    } else if (!bad_section_found) {
                        parse_error_count_++;
                        LOG(ERROR) << filename << ": " << state.line
                                   << ": Invalid section keyword found";
                    }
                    args.clear();
                    break;
                case T_TEXT:
                    args.emplace_back(state.text);
                    break;
            }
        }
    }










