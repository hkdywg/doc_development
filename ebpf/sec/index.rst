SEC 写法基本规则
==================================================

符号含义
--------

**type** - 精确匹配，必须完全写成 ``SEC("type")``，不能加 extras

**type+** - 可选附加，可以是 ``SEC("type")`` 或 ``SEC("type/extras")``，extras 用于自动附加

基本格式
--------

.. code-block:: c

   SEC("type")            // 精确匹配类型
   SEC("type/extras")     // 带附加信息的类型


追踪类程序 SEC 写法（最常用）
==================================================


kprobe / kretprobe - 内核函数探针
---------------------------------

用于追踪内核函数的入口和返回点。

**可用 SEC 写法**::

   SEC("kprobe/<function>")           -- 内核函数入口探针
   SEC("kprobe/<function>+<offset>")  -- 函数内偏移位置探针
   SEC("kretprobe/<function>")        -- 内核函数返回探针
   SEC("ksyscall/<syscall>")          -- syscall 入口（基于 kprobe）
   SEC("kretsyscall/<syscall>")       -- syscall 返回

**格式规则**::

   kprobe/<function>[+<offset>]

- ``function`` 字符限制：``a-zA-Z0-9_.``
- ``offset`` 必须是非负整数

**示例**::

   SEC("kprobe/do_unlinkat")
   int kp_do_unlinkat(struct pt_regs *ctx) { ... }

   SEC("kprobe/do_unlinkat+10")
   int kp_do_unlinkat_offset(struct pt_regs *ctx) { ... }

   SEC("kretprobe/do_unlinkat")
   int kret_do_unlinkat(struct pt_regs *ctx) { ... }


fentry / fexit - BTF 函数追踪（推荐）
-------------------------------------

基于 BTF 的函数追踪，性能更好，参数访问更方便。

**可用 SEC 写法**::

   SEC("fentry/<function>")      -- 函数入口（BTF tracing）
   SEC("fentry.s/<function>")    -- Sleepable 函数入口
   SEC("fexit/<function>")       -- 函数退出（可获取返回值）
   SEC("fexit.s/<function>")     -- Sleepable 函数退出
   SEC("fmod_ret/<function>")    -- 可修改返回值
   SEC("freplace/<function>")    -- 函数替换

**格式规则**::

   fentry[.s]/<function>

**示例**::

   SEC("fentry/do_unlinkat")
   int BPF_PROG(trace_unlinkat, int dfd, struct filename *name) { ... }

   SEC("fexit/do_unlinkat")
   int BPF_PROG(trace_unlinkat_exit, int dfd, struct filename *name, int ret) { ... }

**fentry vs kprobe 对比**::

   特性          fentry                kprobe
   ----------    --------------------   --------------------
   性能          更快（基于 BTF）       较慢
   参数访问      自动类型化             需手动从 pt_regs 读取
   依赖          需要 BTF               无需 BTF
   适用          现代内核（5.5+）       所有内核


tracepoint - 内核 tracepoint
----------------------------

追踪内核预定义的 tracepoint 事件。

**可用 SEC 写法**::

   SEC("tracepoint/<category>/<name>")  -- 标准写法
   SEC("tp/<category>/<name>")          -- 简写

**格式规则**::

   tracepoint/<category>/<name>

**示例**::

   SEC("tracepoint/syscalls/sys_enter_openat")
   SEC("tp/syscalls/sys_enter_openat")

   SEC("tracepoint/kmem/kmalloc")
   SEC("tp/sched/sched_process_exec")


raw_tracepoint - 原始 tracepoint
--------------------------------

无 BTF 信息的原始 tracepoint 访问。

**可用 SEC 写法**::

   SEC("raw_tracepoint/<tracepoint>")   -- 原始 tracepoint
   SEC("raw_tracepoint.w/<tracepoint>") -- 可写版本
   SEC("raw_tp/<tracepoint>")           -- 简写

**格式规则**::

   raw_tracepoint[.w]/<tracepoint>


uprobe / uretprobe - 用户态函数探针
-----------------------------------

追踪用户态程序的函数调用。

**可用 SEC 写法**::

   SEC("uprobe/<path>:<function>")           -- 用户态函数入口
   SEC("uprobe/<path>:<function>+<offset>")  -- 带偏移
   SEC("uretprobe/<path>:<function>")        -- 用户态函数返回
   SEC("uprobe.s/<path>:<function>")         -- Sleepable

**格式规则**::

   uprobe[.s]/<path>:<function>[+<offset>]

**示例**::

   SEC("uprobe/libc.so.6:malloc")
   SEC("uretprobe/libc.so.6:malloc")
   SEC("uprobe./home/user/myapp:main+0x10")


uprobe.multi - 多函数探针
-------------------------

一次追踪多个用户态函数，支持通配符。

**可用 SEC 写法**::

   SEC("uprobe.multi/<path>:<pattern>")      -- 多函数入口
   SEC("uretprobe.multi/<path>:<pattern>")   -- 多函数返回

**格式规则**::

   uprobe.multi[.s]/<path>:<function-pattern>

- ``pattern`` 支持 ``*`` 和 ``?`` 通配符

**示例**::

   SEC("uprobe.multi/libc.so.6:malloc*")  // malloc, malloc_zone, ...
   SEC("uprobe.multi./lib/mylib.so:my_func_*")


kprobe.multi - 多内核函数探针
-----------------------------

一次追踪多个内核函数，支持通配符。

**可用 SEC 写法**::

   SEC("kprobe.multi/<pattern>")      -- 多函数入口
   SEC("kretprobe.multi/<pattern>")   -- 多函数返回

**格式规则**::

   kprobe.multi/<pattern>

- ``pattern`` 支持 ``*`` 和 ``?`` 通配符
- 字符限制：``a-zA-Z0-9_.*?``

**示例**::

   SEC("kprobe.multi/do_*")       // do_unlinkat, do_open, ...
   SEC("kprobe.multi/sys_*")      // sys_read, sys_write, ...


USDT - 用户静态定义追踪点
-------------------------

追踪用户态程序中定义的 USDT probe。

**可用 SEC 写法**::

   SEC("usdt/<path>:<provider>:<name>")  -- USDT 探针

**格式规则**::

   usdt/<path>:<provider>:<name>

**示例**::

   SEC("usdt./lib/myapp.so:myapp:trace_point")
   SEC("usdt./usr/lib/libc.so.6:libc:malloc")


LSM - Linux 安全模块
--------------------

实现 LSM (Linux Security Module) hook。

**可用 SEC 写法**::

   SEC("lsm/<hook>")          -- LSM hook
   SEC("lsm.s/<hook>")        -- Sleepable LSM hook
   SEC("lsm_cgroup/<hook>")   -- cgroup LSM

**格式规则**::

   lsm[.s]/<hook>

**示例**::

   SEC("lsm/file_open")
   SEC("lsm.s/bprm_check_security")


iter - BPF 迭代器
-----------------

迭代内核数据结构，如进程、map 等。

**可用 SEC 写法**::

   SEC("iter/<struct-name>")   -- 迭代器
   SEC("iter.s/<struct-name>") -- Sleepable 迭代器

**格式规则**::

   iter[.s]/<struct-name>

**示例**::

   SEC("iter/task")        // 迭代 task_struct
   SEC("iter/task_file")   // 迭代 task 的文件
   SEC("iter.s/bpf_map")   // Sleepable 迭代 bpf_map


网络类程序 SEC 写法
==================================================


XDP - 数据路径处理
----------------------

在网卡驱动层处理数据包，性能最高。

**可用 SEC 写法**::

   SEC("xdp")  -- XDP 程序（通用）

**示例**::

   SEC("xdp")
   int xdp_handler(struct xdp_md *ctx) { ... }


TC - 流量控制
------------------

在网络协议栈处理数据包。

**可用 SEC 写法**::

   SEC("tc/ingress")      -- 入口流量
   SEC("tc/egress")       -- 出口流量
   SEC("tcx/ingress")     -- 新版入口（推荐）
   SEC("tcx/egress")      -- 新版出口（推荐）
   SEC("classifier")      -- 旧版（已废弃）
   SEC("action")          -- 旧版（已废弃）

.. note::
   ``tc``、``classifier``、``action`` 已废弃，推荐使用 ``tcx/*``


Socket 相关
---------------

处理 socket 层的各种事件。

**可用 SEC 写法**::

   SEC("socket")                  -- socket 过滤器
   SEC("sk_msg")                  -- socket 消息处理
   SEC("sk_skb")                  -- socket skb 处理
   SEC("sk_skb/stream_parser")    -- 流解析器
   SEC("sk_skb/stream_verdict")   -- 流裁决
   SEC("sk_lookup")               -- socket 查找
   SEC("sk_reuseport")            -- 端口重用选择
   SEC("sk_reuseport/migrate")    -- 端口重用迁移
   SEC("sockops")                 -- socket 操作


Cgroup 类程序 SEC 写法
==================================================

用于 cgroup 范围的网络和系统控制。

**可用 SEC 写法**::

   SEC("cgroup/dev")              -- 设备访问控制
   SEC("cgroup/skb")              -- cgroup skb
   SEC("cgroup_skb/ingress")      -- 入口 skb
   SEC("cgroup_skb/egress")       -- 出口 skb
   SEC("cgroup/connect4")         -- IPv4 连接
   SEC("cgroup/connect6")         -- IPv6 连接
   SEC("cgroup/bind4")            -- IPv4 绑定
   SEC("cgroup/bind6")            -- IPv6 绑定
   SEC("cgroup/sendmsg4")         -- IPv4 发送消息
   SEC("cgroup/sendmsg6")         -- IPv6 发送消息
   SEC("cgroup/recvmsg4")         -- IPv4 接收消息
   SEC("cgroup/recvmsg6")         -- IPv6 接收消息
   SEC("cgroup/getsockopt")       -- 获取 socket 选项
   SEC("cgroup/setsockopt")       -- 设置 socket 选项
   SEC("cgroup/sysctl")           -- sysctl 控制
   SEC("cgroup/sock_create")      -- socket 创建
   SEC("cgroup/sock_release")     -- socket 释放


其他程序类型
==================================================


struct_ops - 结构体操作
-----------------------

将 BPF 程序作为内核结构体的回调函数。

**可用 SEC 写法**::

   SEC("struct_ops")    -- 结构体操作
   SEC("struct_ops.s")  -- Sleepable 结构体操作

.. note::
   ``name`` 部分被忽略，实际附加在 struct initializer 中定义::

      SEC(".struct_ops")
      struct my_ops ops = { .callback = my_func };


syscall - BPF syscall 程序
------------------------------

通过 syscall 触发的 BPF 程序。

**可用 SEC 写法**::

   SEC("syscall")  -- syscall 类型（Sleepable）


LWT - 轻量级隧道
---------------------

处理轻量级隧道的数据包。

**可用 SEC 写法**::

   SEC("lwt_in")    -- 隧道入口
   SEC("lwt_out")   -- 隧道出口
   SEC("lwt_xmit")  -- 隧道传输


perf_event
----------

附加到 perf 事件的 BPF 程序。

**可用 SEC 写法**::

   SEC("perf_event")  -- perf 事件程序


Sleepable 程序标记
==================================================

带 ``.s`` 后缀的 SEC 表示程序可以睡眠，即可以调用可能睡眠的 BPF helper 函数。

**示例**::

   SEC("fentry.s/do_unlinkat")      -- Sleepable fentry
   SEC("fexit.s/do_unlinkat")       -- Sleepable fexit
   SEC("lsm.s/file_open")           -- Sleepable LSM
   SEC("uprobe.s/libc:malloc")      -- Sleepable uprobe


完整 SEC 写法速查表
==================================================

::

   场景            SEC 写法                             extras 格式
   ----------      --------------------------------     -------------------------
   内核函数入口    SEC("kprobe/<func>")                 /<function>[+<offset>]
   内核函数返回    SEC("kretprobe/<func>")              /<function>
   BTF 函数入口    SEC("fentry/<func>")                 /<function>
   BTF 函数返回    SEC("fexit/<func>")                  /<function>
   Tracepoint      SEC("tp/<cat>/<name>")               /<category>/<name>
   用户态函数      SEC("uprobe/<path>:<func>")          /<path>:<function>[+<offset>]
   USDT            SEC("usdt/<path>:<prov>:<name>")     /<path>:<provider>:<name>
   LSM hook        SEC("lsm/<hook>")                    /<hook>
   XDP             SEC("xdp")                           无 extras
   TC 入口         SEC("tcx/ingress")                   /ingress
   迭代器          SEC("iter/<struct>")                 /<struct-name>


extras 附加信息来源
==================================================

SEC 中 extras 部分的值需要从特定来源获取：

::

   程序类型        extras 来源              查看方法
   ----------      --------------------     ----------------------------------------
   kprobe          内核函数名               /sys/kernel/debug/tracing/available_filter_functions
   fentry          内核函数名（需 BTF）     BTF + vmlinux.h
   tracepoint      category/name           /sys/kernel/debug/tracing/events/<cat>/<name>
   uprobe          用户态符号               readelf -s <binary> 或 nm
   USDT            USDT 定义                readelf -n <binary> 或 bpftool usdt list
   LSM             LSM hook 名              include/linux/lsm_hook_defs.h
   iter            迭代器结构名             BTF + 内核源码


实际代码示例汇总
==================================================

追踪类示例
----------

.. code-block:: c

   // === kprobe ===
   SEC("kprobe/do_unlinkat")
   int kp_handler(struct pt_regs *ctx) {}

   // === fentry ===
   SEC("fentry/do_unlinkat")
   int BPF_PROG(fentry_handler, int dfd, struct filename *name) {}

   // === fexit ===
   SEC("fexit/do_unlinkat")
   int BPF_PROG(fexit_handler, int dfd, struct filename *name, int ret) {}

   // === tracepoint ===
   SEC("tp/syscalls/sys_enter_openat")
   int tp_handler(void *ctx) {}

   // === uprobe ===
   SEC("uprobe/libc.so.6:malloc")
   int uprobe_handler(struct pt_regs *ctx) {}

   // === USDT ===
   SEC("usdt./app:provider:event")
   int usdt_handler(void *ctx) {}

网络类示例
----------

.. code-block:: c

   // === XDP ===
   SEC("xdp")
   int xdp_handler(struct xdp_md *ctx) {}

   // === TC ===
   SEC("tcx/ingress")
   int tc_handler(struct __sk_buff *skb) {}

   // === sk_msg ===
   SEC("sk_msg")
   int skmsg_handler(struct sk_msg_md *msg) {}

Cgroup 类示例
-------------

.. code-block:: c

   // === cgroup/connect ===
   SEC("cgroup/connect4")
   int connect_handler(struct bpf_sock_addr *ctx) {}

   // === cgroup_skb ===
   SEC("cgroup_skb/ingress")
   int ingress_handler(struct __sk_buff *skb) {}

LSM 类示例
----------

.. code-block:: c

   SEC("lsm/file_open")
   int lsm_handler(struct bpf_lsm_file_open *ctx) {}

其他示例
--------

.. code-block:: c

   // === iter ===
   SEC("iter/task")
   int iter_handler(struct bpf_iter_task *ctx) {}

   // === syscall ===
   SEC("syscall")
   int syscall_handler(void *ctx) {}


