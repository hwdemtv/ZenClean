# ZenClean (禅清) - 互为螺旋

![ZenClean Hero](docs/images/hero.png)

现代 Windows C 盘深度清理与极致优化工具 —— 融合 AI 智能分诊与极客底层爆破，让您的系统回归“禅”意般的纯净。

[![Status](https://img.shields.io/badge/Status-v0.1.3--Beta-orange?style=flat-square)](https://github.com/hwdemtv/ZenClean/releases/tag/v0.1.3-beta)
[![Python](https://img.shields.io/badge/Python-3.11+-1DD1A1?style=flat-square)](https://www.python.org/)
[![UI](https://img.shields.io/badge/UI-Flet-white?style=flat-square)](https://flet.dev/)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

## ✨ 核心特性 (Core Features)

### 🤖 AI 智能深度清理与异步扫描 2.0
- **异步隔离引擎 (Scanner 2.0)**: 彻底剥离 UI 线程，采用独立后台 Worker + 异步消息队列。扫描几万项文件时界面依然丝滑，UI 响应与物理扫盘物理隔离。
- **靶向云端研判**: 接入云端大语言模型，精准评估系统冗余、应用残留与无效日志的风险等级，杜绝误报误删。
- **时光机双核隔离舱**: 提供“72 小时反悔期”。误删文件支持一键原路恢复；过期隔离项目由后台守护线程自动静默粉碎。

### � v0.1.3 Beta 更新日志
- **[核心] 浏览器目标外科手术式拆分**：支持 Chrome/Edge 缓存子目录迁移，不影响登录状态，风险降至 SAFE。
- **[智能] 增量监控提醒**：自动检测已搬家目录的增长，超过 1GB 时琥珀色 UI 提醒，支持“一键再迁”。
- **[稳健] 进程优雅关闭**：引入阶梯式关闭逻辑（尝试退出 -> 超时强杀），保护搬家时的数据一致性。
- **[系统] 右键菜单全域覆盖**：除文件夹外，新增对磁盘根目录（Drive Context）的直接挂载支持。
- **[视觉] 网格流 UI 升级**：应用搬家页面采用更紧凑、直观的单列表 ResponsiveRow 布局。

### �🚚 大厂应用无损极客搬家
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

1. 前往 [Release](https://github.com/hwdemtv/ZenClean/releases) 页面下载最新的 `ZenClean_v0.1.3_Beta_Green_Portable.zip`。
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
