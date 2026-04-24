# ZenClean (禅清) - 互为螺旋

![ZenClean Hero](docs/images/hero.png)

现代 Windows C 盘深度清理与极致优化工具 —— 融合 AI 智能分诊与极客底层爆破，让您的系统回归“禅”意般的纯净。

[![Status](https://img.shields.io/badge/Status-Beta-orange?style=flat-square)](https://github.com/hwdemtv/ZenClean/releases)
[![Python](https://img.shields.io/badge/Python-3.11+-1DD1A1?style=flat-square)](https://www.python.org/)
[![UI](https://img.shields.io/badge/UI-Flet-white?style=flat-square)](https://flet.dev/)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

## ✨ 核心特性 (Core Features)

### 🤖 AI 智能深度清理与异步扫描 2.0
- **异步隔离引擎 (Scanner 2.0)**: 彻底剥离 UI 线程，采用独立后台 Worker + 异步消息队列。扫描几万项文件时界面依然丝滑，UI 响应与物理扫盘物理隔离。
- **靶向云端研判**: 接入云端大语言模型，精准评估系统冗余、应用残留与无效日志的风险等级，杜绝误报误删。
- **时光机双核隔离舱**: 提供“72 小时反悔期”。误删文件支持一键原路恢复；过期隔离项目由后台守护线程自动静默粉碎。

### 🚀 v0.1.6 Beta 更新日志
- **[算法] 异步批处理 2.0**: 接入全新 `BatchProcessor` 分发层，将 AI 风险研判从“单点阻塞”升级为“高并发流水线”，分析效率提升 300%。
- **[系统] 强效退出守护**: 重构托盘 (Tray) 退出链路，增加 watchdog 哨兵线程，彻底根治 Windows 进程残留与僵尸句柄问题。

### 🚀 近期更新日志
- **[扫描] 靶点史诗级扩容**：`SCAN_TARGETS` 从 20+ 精准路径通过白皮书对齐增加至 **150+ 项**，实现对微信、QQ、抖音、飞书、各厂浏览器及开发环境缓存的全方位覆盖。
- **[安全] 分级保护策略**：正式引入 `CRISIS` 风险等级，对聊天记录、浏览器 User Data 等核心资产实施“物理级硬阻断”，杜绝一切误删可能。
- **[搬家] 路径探测器 2.0**：补全 `resolve_target_path` 函数，支持通过**注册表**及多候选路径自动定位微信等软件的真实数据目录。
- **[修复] 初始化崩溃项**：修复了搬家引擎架构升级导致的 `TypeError` 实例化异常，确保启动流稳定。

### 🚀 v0.1.4 Beta 更新日志
- **[底层] 重构调度引擎**：全面剥离耗时的底层清理任务至独立的 Worker 线程，彻底根治清理过程中的 UI 假死与句柄泄露及容量显示错乱（KB/MB/GB）问题。
- **[修复] 弹窗阻塞 Bug**：修复了在执行高阶权限扫描与底层清理时的前端句柄丢失问题。
- **[算法] 增强清洗规则**：补充优化 Windows Update 残留、陈年补丁及系统更新卸载残留的深层提取算法，精准拦截高风险系统文件。

### 🚀 v0.1.3 Beta 更新日志
- **[底层] 全新搬家引擎**：以 Windows 原生 Shell API 为核心，结合底层重解析点（Junction）兜底的全新搬家双引擎，完全对齐系统原生“位置转移”行为，彻底解决 C 盘应用数据“幽灵反写”难题。
- **[功能] AI 授权状态**：优化了在线检测和失败回调机制（服务端吊销自动无感拦截）。

### 🚚 大厂应用无损极客搬家
- **底层透明映射**: 针对微信、QQ、Docker、VSCode 扩展等“C 盘杀手”，采用 Windows NTFS Junction 技术进行底层物理搬运。
- **零感知运行**: 搬移至 D 盘后，C 盘原有路径将生成透明软连接。应用软件**无需重装、无需修改任何配置**即可照常运行。
- **进程级防线**: 搬家前自动侦测并挂起活跃进程，严格的容量预检与全量校验，支持随时一键无损退防。

### ⚡ 深空级系统补丁粉碎 (高危)
- **Windows 更新缓存清剿**: 自动化调用 `dism /StartComponentCleanup` 接口清剿失效的 Component Store。
- **$PatchCache 物理强剪**: 深入系统禁区，强接管 `msiserver` (Windows Installer) 服务，对陈年补丁进行寿命鉴定（365天安全隔离），一键释放海量空间。

### 🛡️ 系统级深度整合与安全加固
- **安全审计 (HMAC-SHA256)**: 全线 API 接入时间戳哈希校验与 Nonce 随机数，杜绝模拟发包与非法刷写。
- **多实例 IPC 联动**: 基于 TCP 端口映射的单实例守护。如果从右键菜单重复启动，将自动唤醒已运行的主界面。
- **系统托盘与预警**: 接入托盘 (Tray) 驻留，并在 C 盘爆仓时投递原生 Toast 通知。

## 💡 为什么选择 ZenClean? (Philosophy)

我们摒弃传统清理软件动辄扫出数十 GB “假面垃圾”（如浏览器 Cookies、必要的预编译库）的做法。我们的核心理念是：**性能优先、零感知干扰、极客级深度**。
1. **不碰敏感核心**：我们绝不为了好看的数字去清理您的登录态、表单历史或预编译文件。
2. **仪表盘美学**：针对多分类数据采用 `Wrap` 网格排列布局，彻底解决图例重叠，打造极致的 Windows 运维美学。

---

## 🚀 极速上手 (For Users)

1. 前往 [Release](https://github.com/hwdemtv/ZenClean/releases) 页面下载最新的绿色免安装版压缩包。
2. 解压至任意目录，**双击运行 `ZenClean.exe`**。
3. _（可选）_ 如果系统提示，请赋予管理员权限以解锁深层清理能力。

---

## 👨‍💻 开发者指南 (For Developers)

### 1. 环境准备
```bash
git clone https://github.com/hwdemtv/ZenClean.git
cd ZenClean
pip install -r requirements.txt
```

### 2. 本地调试
该项目使用 `.env` 管理敏感配置，请参考 `.env.example` 进行配置。
```bash
python src/main.py
```

### 3. 构建发布
我们提供了自动化的构建流水线：
```bash
# 自动清理并生成全量免安装目录
python scripts/build_release.py

# (可选) 调用 Inno Setup 编译安装向导
python scripts/build_installer.py
```

## 📜 免责声明
本软件涉及 Windows 底层核心操作。开发者不对任何意外导致的系统崩溃、数据丢失承担连带法律责任。**请在知晓风险的情况下使用**。

---

<div align="center">
    <b>互为螺旋 · 禅意清扫</b><br>
    <i>Crafted with ❤️ for Windows Geeks.</i>
</div>
