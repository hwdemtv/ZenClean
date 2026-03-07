# ZenClean (禅清)

![ZenClean Hero](docs/images/hero.png)

现代 Windows C 盘深度清理与极致优化工具 —— 让您的系统回归“禅”意般的纯净。

[![Status](https://img.shields.io/badge/Status-v0.1.0--Beta-00C2FF?style=flat-square)](https://github.com/hwdemtv/ZenClean)
[![Python](https://img.shields.io/badge/Python-3.11+-1DD1A1?style=flat-square)](https://www.python.org/)
[![UI](https://img.shields.io/badge/UI-Flet-white?style=flat-square)](https://flet.dev/)

## ✨ 核心功能 (Core Features)

- 🧼 **AI 智能深度清理**: 接入真实云端 AI 引擎，精准识别系统冗余、应用残留与无效日志，杜绝误报误删。
- 📦 **开发环境专项优化**: 针对极客用户，一键扫描 npm/pip/VSCode 等开发链下的巨量隐藏 `.cache` 缓存。
- � **无损空间搬家**: 核心文件夹（桌面/下载/文档等）自动重定向，支持三方应用数据基于 Junction Link 的物理迁移。
- 🛡️ **安全第一架构**: UAC 全自动提权、回收站全量容灾、Windows 内核级路径免杀白名单三重保障。

## 💡 为什么选择 ZenClean? (Philosophy)

如果您习惯了传统清理软件动辄扫出数十 GB 垃圾的“数字震撼”，您可能觉得 ZenClean 过于保守。这并非缺陷，而是我们建立在**性能优先与零感知干扰**之上的核心理念：

1. **克制的解析策略**：我们不清理 `Cookies`、`History` 等敏感数据。清理不应导致重新登录或丢失表单。
2. **不碰底层预编译缓存**：避免删除 `.NET` 或系统组件缓存，防止下次打开专业软件时产生额外的冷启动耗时。
3. **拒绝地毯式扫描**：依靠精确的“垃圾热区”靶向打击（`SCAN_TARGETS`），实现秒级体检响应。

## 🛠️ 近期优化成果 (Recent Improvements)

- 🏗️ **底层组件化重构**: 成功抽取 `FileListItem` 与全局 `Dialog` 体系，渲染性能提升 60%+。
- 📐 **视觉对齐大修**: 精确对齐跨容器 UI 标题中轴线，彻底解决高 Dpi 缩放下的不对齐“强迫症”。
- � **代码洁净度治理**: 利用 `flake8` 完成了全局无用包引用 (Unused Imports) 的“零容忍”清理。

---

## 🏗️ 技术架构 (Tech Stack)

- **UI Framework**: [Flet](https://flet.dev/) (基于 Flutter 实现的 Python 声明式 UI 框架)
- **AI Engine**: 集成智谱 GLM-4 真实云端分析，支持智能风险研判。
- **IPC Engine**: 基于 `multiprocessing` 的独立扫描子进程，绕过 GIL 限制。
- **Auth System**: 支持离线离机鉴权 + 后台 JWT 静默校验（基于 `py-machineid`）。

## � 开发路线图 (Roadmap)

我们正按计划向 `v1.0` 迈进：

- [ ] **阶段一 (收尾项目)**: 性能调优、代码规范化、多环境打包验证。
- [ ] **阶段二 (深度瘦身)**: 休眠文件管理、虚拟内存引导、僵尸 `node_modules` 扫描。
- [ ] **阶段三 (搬家中心)**: 第三方大型应用无损迁移（基于 Junction 点）、磁盘大文件可视化看板。
- [ ] **发布增强**: Inno Setup 自动安装向导、商用数字签名证书。

## 🚀 开发者快速开始

1. **环境准备**:
   ```bash
   pip install -r requirements.txt
   ```
2. **启动程序**:
   ```bash
   python src/main.py
   ```
3. **分发打包**:
   ```bash
   pyinstaller zenclean.spec --clean
   ```

---
## 🚀 极速上手
1. 下载并解压 `ZenClean_0.1.0_Beta.zip`。
2. **双击运行 `ZenClean.exe`**。
3. 若提示“缺少运行库”，按引导完成 Visual C++ 安装。

> 💡 更多详情请查阅 [docs/ROADMAP.md](docs/ROADMAP.md) 或 [CHANGELOG.md](CHANGELOG.md)。
