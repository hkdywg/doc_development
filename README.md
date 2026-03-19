# 嵌入式开发技术文档

<div align="center">

[![Sphinx](https://img.shields.io/badge/Sphinx-Documentation-orange)](https://www.sphinx-doc.org/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**一站式嵌入式Linux开发学习笔记，涵盖从底层硬件到上层应用的全栈技术栈**

</div>

---

## 项目简介

`doc_development` 是一套基于 [Sphinx](https://www.sphinx-doc.org/) 构建的技术文档系统，汇集了嵌入式Linux开发领域的核心知识点。文档以 RST (reStructuredText) 格式编写，支持导出为 HTML、PDF、EPUB 等多种格式。

### 核心特性

- **全栈覆盖**：从ARM64架构到Linux内核，从驱动开发到应用编程
- **源码解读**：深入分析U-Boot、Linux内核、FreeRTOS等开源项目核心代码
- **实战导向**：包含大量实际项目中的调试技巧和问题解决方案
- **图表辅助**：配套Draw.io架构图，直观展示系统内部机制

---

## 文档目录

```
doc_development/
├── kernel/          Linux内核开发
├── driver/          Linux驱动开发
├── u-boot/          U-Boot引导程序
├── embedded/        嵌入式系统构建
├── optee/           TEE可信执行环境
├── arm64/           ARM64架构基础
├── rtos/            实时操作系统
├── fs/              文件系统
├── net/             网络协议栈
├── android/         Android系统
├── fpga/            FPGA开发
├── user/            应用程序开发
├── misc/            开发工具与技巧
├── drawio/          架构图汇
├── docs/            GitHub Pages部署
└── Tutorials/       教程资源
```

### 详细内容

#### 1. Linux内核开发 (`kernel/`)

深入剖析Linux内核核心子系统：

| 模块 | 内容 |
|------|------|
| `kernel_start/` | 内核启动流程，从 bootloader 到第一个进程 |
| `mm/` | 内存管理，物理内存分配、虚拟内存映射、SLAB/SLUB分配器 |
| `process/` | 进程调度，CFS调度器、实时调度、负载均衡 |
| `kernel_function/` | 核心内核函数分析 |
| `system_call/` | 系统调用接口 |
| `dts/` | 设备树(Device Tree)语法与使用 |
| `debug/` | 内核调试技术，printk、Ftrace、KGDB |
| `concurrenty_contrl/` | 并发控制，spinlock、mutex、RCU |
| `kernel_map/` | 内核内存布局 |
| `performance_optimzation/` | 性能调优方法论 |

#### 2. Linux驱动开发 (`driver/`)

驱动开发实战指南：

| 模块 | 内容 |
|------|------|
| `platform_bus/` | 平台总线与设备驱动模型 |
| `mmc/` | MMC/SD卡驱动架构 |
| `i2c/` | I2C/SPI总线驱动 |
| `irq/` | 中断处理子系统 |
| `gpio/` | GPIO子系统 |
| `device_module/` | 字符设备、块设备、网络设备 |
| `kobj/` | sysfs与内核对象 |
| `Async_notify/` | 异步通知机制 |
| `mmap/` | 内存映射与DMA |
| `net/` | 网络设备驱动 |
| `timer/` | 内核定时器与高精度定时器 |
| `input/` | 输入子系统 |
| `framebuffer/` | Framebuffer显示驱动 |
| `drm/` | DRM/KMS显示框架 |
| `v4l2/` | V4L2视频采集框架 |
| `rpmsg/` | RPMsg处理器间通信 |

#### 3. U-Boot引导程序 (`u-boot/`)

| 文档 | 内容 |
|------|------|
| `compile.rst` | U-Boot编译配置 |
| `source_analysis/` | 启动流程源码分析 |
| `bootm.rst` | bootm启动命令实现 |
| `legacy-fit_img.rst` | FIT镜像格式详解 |
| `parsing_uimage.rst` | UImage解析 |
| `transfer_param.rst` | 内核参数传递 |
| `multi_core_startup.rst` | 多核启动机制 |
| `uboot_memory.rst` | 内存布局管理 |

#### 4. 嵌入式系统构建 (`embedded/`)

| 模块 | 内容 |
|------|------|
| `buildroot/` | Buildroot构建系统 |
| `yocto/` | Yocto/OpenEmbedded |
| `ota/` | OTA空中升级方案 |
| `safeboot/` | 安全启动链 |
| `systemd/` | Systemd服务管理 |
| `hotplug/` | 热插拔机制 |
| `bus/` | 总线协议(I2C/SPI/UART) |
| `fs/` | 嵌入式文件系统 |
| `video/` | 视频编解码 |
| `udev/` | 动态设备管理 |
| `debug/` | 嵌入式调试技术 |
| `gpt/` | GPT分区表 |
| `hardware/` | 硬件接口 |

#### 5. TEE可信执行环境 (`optee/`)

| 模块 | 内容 |
|------|------|
| `atf/` | ARM Trusted Firmware |
| `optee/` | OP-TEE客户端API与TA开发 |

#### 6. ARM64架构 (`arm64/`)

| 模块 | 内容 |
|------|------|
| `register/` | ARM64寄存器 |
| `assembly/` | ARM64汇编语言 |
| `stack/` | 栈帧结构与调用约定 |
| `exception/` | 异常处理机制 |

#### 7. 实时操作系统 (`rtos/`)

| 模块 | 内容 |
|------|------|
| `free_rtos/` | FreeRTOS任务调度、队列、信号量 |

#### 8. 网络协议栈 (`net/`)

| 模块 | 内容 |
|------|------|
| `overview/` | 网络架构概览 |
| `tcp_ip/` | TCP/IP协议栈分析 |
| `AVB/` | Audio Video Bridging |
| `tc8/` | TC8车载以太网测试 |

#### 9. 应用程序开发 (`user/`)

| 模块 | 内容 |
|------|------|
| `c++/` | C++高级特性 |
| `communication/` | 进程间通信(IPC) |
| `socket/` | Socket网络编程 |
| `video/` | 音视频应用开发 |
| `verhicle_app/` | 汽车电子应用 |
| `linux_system/` | Linux系统编程 |
| `Cstand_lib/` | C标准库 |
| `security/` | 应用安全 |
| `config/` | 配置文件解析 |
| `soft_package_list/` | 软件包清单 |

#### 10. 开发工具 (`misc/`)

| 模块 | 内容 |
|------|------|
| `git/` | Git版本控制 |
| `shell/` | Shell脚本编程 |
| `cmake/` | CMake构建系统 |
| `makefile/` | Makefile编写 |
| `program_debug/` | GDB/LLDB调试 |
| `datastruct_algo/` | 数据结构与算法 |
| `markdown/` | Markdown技巧 |
| `linux_commond/` | Linux常用命令 |
| `vim/` | Vim编辑器配置 |
| `ld_scripts/` | 链接脚本 |
| `reference/` | 参考资料 |

---

## 快速开始

### 环境要求

- Python 3.8+
- Sphinx 4.0+

### 安装依赖

```bash
# Debian/Ubuntu
sudo apt install python3-pip
pip3 install sphinx sphinx_rtd_theme

# 如果遇到 externally-managed-environment 错误 (Ubuntu 24.04+)
pip3 install --break-system-packages sphinx sphinx_rtd_theme
```

### 本地预览

```bash
# 编译HTML文档
make html

# 启动本地服务器
cd build/html
python3 -m http.server 8000
```

访问 `http://localhost:8000` 即可预览文档。

### 输出格式

```bash
# HTML文档
make html

# PDF (需要安装 LaTeX)
make latexpdf

# 单页HTML
make singlehtml

# EPub电子书
make epub
```

---

## 在线预览

文档已部署至 GitHub Pages：[查看在线文档](https://hkdywg.github.io/doc_development/)

或者访问个人网站：[个人网站](https://www.pedestrian.com.cn/)

---

## 配套资源

### 架构图汇 (`drawio/`)

提供以下 Draw.io 图表下载：

- `fs/fs.drawio` - 文件系统架构图
- `io/mmap.drawio` - IO内存映射图
- `mm/memory_management.drawio` - 内存管理架构图

### 参考链接

- [Linux Kernel Documentation](https://www.kernel.org/doc/html/latest/)
- [Linux Driver Development](https://www.kernel.org/doc/html/latest/driver-api/)
- [ARM Architecture Reference Manual](https://developer.arm.com/documentation/ddi0487/ka/)
- [Sphinx Documentation](https://www.sphinx-doc.org/)

---

## 许可证

本项目基于 MIT 许可证开源，详见 [LICENSE](LICENSE) 文件。

---

<div align="center">

**如果文档对您有帮助，欢迎 Star ⭐**

</div>
