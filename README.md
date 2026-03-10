# ZenClean (禅清)

![ZenClean Hero](docs/images/hero.png)

现代 Windows C 盘深度清理与极致优化工具 —— 让您的系统回归“禅”意般的纯净。

[![Status](https://img.shields.io/badge/Status-v0.1.1--Beta-00C2FF?style=flat-square)](https://github.com/hwdemtv/ZenClean)
[![Python](https://img.shields.io/badge/Python-3.11+-1DD1A1?style=flat-square)](https://www.python.org/)
[![UI](https://img.shields.io/badge/UI-Flet-white?style=flat-square)](https://flet.dev/)

## ✨ 核心功能 (Core Features)

- 🧼 **AI 智能深度清理**: 接入真实云端 AI 引擎，精准识别系统冗余、应用残留与无效日志，杜绝误报误删。
- 📦 **开发环境专项优化**: 针对极客用户，一键扫描 npm/pip/VSCode 等开发链下的巨量隐藏 `.cache` 缓存。
- ⏳ **时光机隔离沙箱**: 提供 72 小时“反悔期”，支持误删文件的一键原路恢复，过期项目后台静默物理粉碎。
- 🔄 **多实例 IPC 联动**: 支持 Windows 右键菜单深度集成，多开实例自动唤醒已运行的主程序并同步扫描路径。
- 🛡️ **安全第一架构**: UAC 全自动提权、回收站全量容灾、Windows 内核级路径免杀白名单三重保障。

## 💡 为什么选择 ZenClean? (Philosophy)

如果您习惯了传统清理软件动辄扫出数十 GB 垃圾的“数字震撼”，您可能觉得 ZenClean 过于保守。这并非缺陷，而是我们建立在**性能优先与零感知干扰**之上的核心理念：

1. **克制的解析策略**：我们不清理 `Cookies`、`History` 等敏感数据。清理不应导致重新登录或丢失表单。
2. **不碰底层预编译缓存**：避免删除 `.NET` 或系统组件缓存，防止下次打开专业软件时产生额外的冷启动耗时。
3. **拒绝地毯式扫描**：依靠精确的“垃圾热区”靶向打击（`SCAN_TARGETS`），实现秒级体检响应。

## 🛠️ 近期优化成果 (Recent Improvements)

- 🏗️ **底层组件化重构**: 成功抽取 `FileListItem` 与全局 `Dialog` 体系，渲染性能提升 60%+。
- 📐 **视觉对齐大修**: 精确对齐跨容器 UI 标题中轴线，彻底解决高 Dpi 缩放下的不对齐“强迫症”。
- 📡 **通信机制升级**: 弃用 Windows 命名管道，全面切换至 **TCP 回环 (127.0.0.1:19528)**，彻底解决管理员权限下的 IPC 通信屏障。
- 🚀 **时光机双核驱动**: 实装了全量原路恢复引擎与后台定时静默粉碎守护线程。
- ⚡ **性能调优**: 针对文件扫描与 UI 渲染进行了深度优化，响应速度显著提升。
- 🧹 **代码规范化**: 遵循 PEP8 规范，提升代码可读性与可维护性。

---

## 🏗️ 技术架构 (Tech Stack)

- **UI Framework**: [Flet](https://flet.dev/) (基于 Flutter 实现的 Python 声明式 UI 框架)
- **AI Engine**: 集成智谱清言大模型，真实云端分析，支持智能风险研判。
- **IPC Engine**: 基于 **TCP Loopback** 的单实例唤醒机制，支持跨权限边界的路径传递。
- **Auth System**: 支持离线离机鉴权 + 后台 JWT 静默校验（基于 `py-machineid`）。

## � 开发路线图 (Roadmap)

我们正按计划向 `v1.0` 迈进：

- [x] **阶段一 (核心闭环)**: 性能调优、代码规范化、多实例 IPC 唤醒、时光机隔离舱、后台静默清理。
- [ ] **阶段二 (深度优化)**: 系统托盘驻留 (Tray)、开机自启管理、日志自动审计。
- [ ] **阶段三 (搬家中心)**: 第三方大型应用无损迁移（基于 Junction 点）、磁盘大文件可视化看板。
- [ ] **发布增强**: Inno Setup 自动安装向导、商用数字签名证书。

## 🚀 开发者快速开始

1. **配置环境变量文件（重要）**:
   - 本仓库不会提交真实的 `.env`，请先将根目录下的 `.env.example` 复制为 `.env`，并按自己的环境修改里面的 `LICENSE_SERVER_URLS` / `AI_GATEWAY_BASE_URL` 等变量。
   - 若你只是本地体验官方云端服务，可直接使用示例中的默认值。

2. **环境准备**:
   ```bash
   pip install -r requirements.txt
   ```
3. **启动程序**:
   ```bash
   python src/main.py
   ```
4. **分发打包**:
   ```bash
   pyinstaller zenclean.spec --clean
   ```


---
## 🚀 极速上手
1. 下载并解压 `ZenClean_0.x.x_Beta.zip`。
2. **双击运行 `ZenClean.exe`**。
3. 若提示“缺少运行库”，按引导完成 Visual C++ 安装。

> 💡 更多详情请查阅 [docs/ROADMAP.md](docs/ROADMAP.md) 或 [CHANGELOG.md](CHANGELOG.md)。
