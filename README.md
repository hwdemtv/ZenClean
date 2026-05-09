# ZenClean (禅清) - 互为螺旋

![ZenClean Hero](docs/images/hero.png)

现代 Windows C 盘深度清理与极致优化工具 —— 融合 AI 智能分诊与极客底层爆破，让您的系统回归"禅"意般的纯净。

[![Status](https://img.shields.io/badge/Status-V0.1.7--beta-orange?style=flat-square)](https://github.com/hwdemtv/ZenClean/releases)
[![Python](https://img.shields.io/badge/Python-3.11+-1DD1A1?style=flat-square)](https://www.python.org/)
[![UI](https://img.shields.io/badge/UI-Flet-white?style=flat-square)](https://flet.dev/)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

---

## 核心特性 (Core Features)

### AI 智能深度清理与异步扫描 2.0
- **异步隔离引擎 (Scanner 2.0)**: 独立后台 Worker + 异步消息队列，扫描数万项文件时界面依然丝滑，UI 响应与物理扫盘完全隔离。
- **靶向云端研判**: 接入云端大语言模型 (GLM-4-flash)，精准评估系统冗余、应用残留与无效日志的风险等级，杜绝误报误删。
- **批处理聚合引擎**: 单文件查询自动聚合成批量请求 (8 文件/批)，客户端滑动窗口限流 (100 req/60s)，大幅降低 API 调用成本。
- **三级分类策略**: 本地规则引擎 -> 云端 AI 分析 -> 降级 UNKNOWN 处理，链路完整且具备容错能力。
- **时光机双核隔离舱**: 提供"72 小时反悔期"。误删文件支持一键原路恢复；过期隔离项目由后台守护线程自动静默粉碎。

### 大厂应用无损极客搬家
- **底层透明映射**: 针对微信、QQ、Docker、VSCode 扩展等"C 盘杀手"，采用 Windows NTFS Junction 技术进行底层物理搬运。
- **零感知运行**: 搬移至 D 盘后，C 盘原有路径将生成透明软连接。应用软件**无需重装、无需修改任何配置**即可照常运行。
- **进程级防线**: 搬家前自动侦测并挂起活跃进程，严格的容量预检与全量校验，支持随时一键无损退防。
- **断点恢复**: 5 阶状态机全程追踪（预检->复制->校验->挂载->完成），中断后重启可继续迁移或一键回滚。

### 深空级系统补丁粉碎 (高危)
- **Windows 更新缓存清剿**: 自动化调用 `dism /StartComponentCleanup` 接口清剿失效的 Component Store。
- **$PatchCache 物理强剪**: 深入系统禁区，强接管 `msiserver` (Windows Installer) 服务，对陈年补丁进行寿命鉴定（365天安全隔离），一键释放海量空间。

### 系统级深度整合与安全加固
- **安全审计 (HMAC-SHA256)**: 全线 API 接入时间戳哈希校验与 Nonce 随机数，杜绝模拟发包与非法刷写。
- **多实例 IPC 联动**: 基于 TCP 端口映射的单实例守护。如果从右键菜单重复启动，将自动唤醒已运行的主界面。
- **系统托盘与预警**: 接入托盘 (Tray) 驻留，并在 C 盘爆仓时投递原生 Toast 通知。
- **商业授权体系**: 动态通配码 (`ZEN-VIP-YYYYMMDD`)、机器码绑定、NTP 时间防篡改、在线/离线双模式校验。

---

## 更新日志 (Changelog)

### V0.1.7-beta (2026-03-28)
- **[修复] AI 鉴权 403**: 移除自定义 Header 以绕过 Cloudflare WAF 拦截，并增强了鉴权失败的诊断日志。
- **[稳定] 异步超时策略**: 提升超时至 60s 并优化批处理分片，彻底解决大规模路径扫描时的分析超时问题。
- **[修复] UI 数据回显**: 修复了异步结果返回时的 Flet 协程调用异常，确保 AI 研判建议实时刷新。
- **[修复] 授权返回值崩溃**: `verify_license_online` 所有错误路径统一返回 3-tuple，消除调用方 ValueError。
- **[修复] 缓存键对齐**: AI 降级结果与批量分析结果统一按父目录缓存，与 `query()` 查询键一致，避免重复请求。
- **[修复] 缓存写盘丢数据**: 引入脏标记机制，写盘被跳过时自动补写，防止进程崩溃时丢失 AI 分析结果。
- **[安全] .env 不再打包**: 生产环境配置不再内嵌到可执行文件中，改为运行时从 exe 同级目录或系统环境变量读取。
- **[修复] SnackBar 方法缺失**: `ZenCleanApp` 新增 `show_snack_bar()` 方法，修复应用迁移页面操作反馈崩溃。
- **[清理] 代码质量**: 移除硬编码像素偏移、重复导入、过时注释。

### V0.1.6-beta
- 实现云端 AI 批处理异步合并机制。
- 消除 FAQ 区域背景色缓存冲突。

### V0.1.4-beta
- **[底层] 重构调度引擎**: 全面剥离耗时的底层清理任务至独立 Worker 线程，根治 UI 假死与句柄泄露。
- **[修复] 弹窗阻塞 Bug**: 修复高阶权限扫描与底层清理时的前端句柄丢失问题。
- **[算法] 增强清洗规则**: 补充优化 Windows Update 残留、陈年补丁及系统更新卸载残留的深层提取算法。

### V0.1.3-beta
- **[底层] 全新搬家引擎**: Windows 原生 Shell API + Junction 兜底的双引擎架构，解决 C 盘应用数据"幽灵反写"难题。
- **[原生] 断点恢复与防断电保护**: 5 阶状态机全程追踪，重启即弹出状态卡片支持"继续迁移"或"一键无损回滚"。
- **[核心] 浏览器目标外科手术式拆分**: 支持 Chrome/Edge 缓存子目录迁移，不影响登录状态。

---

## 为什么选择 ZenClean? (Philosophy)

我们摒弃传统清理软件动辄扫出数十 GB "假面垃圾"（如浏览器 Cookies、必要的预编译库）的做法。核心理念：**性能优先、零感知干扰、极客级深度**。

1. **不碰敏感核心**: 绝不为了好看的数字去清理您的登录态、表单历史或预编译文件。
2. **仪表盘美学**: 针对多分类数据采用 Wrap 网格排列布局，打造极致的 Windows 运维美学。
3. **安全第一**: 沙箱隔离 + 白名单硬阻断 + 风险分级 (SAFE/WARNING/CRISIS)，杜绝一切误删可能。

---

## 极速上手 (For Users)

1. 前往 [Release](https://github.com/hwdemtv/ZenClean/releases) 页面下载最新的绿色免安装版压缩包。
2. 解压至任意目录，**双击运行 `ZenClean.exe`**。
3. _（可选）_ 如果系统提示，请赋予管理员权限以解锁深层清理能力。
4. _（可选）_ 将 `.env` 文件放置在 `ZenClean.exe` 同级目录以配置服务器地址（参考 `.env.example`）。

---

## 开发者指南 (For Developers)

### 环境准备

```bash
git clone https://github.com/hwdemtv/ZenClean.git
cd ZenClean
pip install -r requirements.txt
```

### 项目结构

```
src/
├── main.py              # 入口点，UAC 提权，IPC 监听，托盘启动
├── config/
│   ├── settings.py      # 全局配置，150+ 扫描目标路径
│   └── file_kb.json     # AI 分类知识库
├── core/                # 业务逻辑层
│   ├── scanner.py       # 异步文件扫描器 (消息队列)
│   ├── cleaner.py       # 文件删除 + 沙箱隔离
│   ├── app_migrator.py  # NTFS Junction 应用迁移
│   ├── migration.py     # Windows Shell API + Junction 双引擎
│   ├── patch_analyzer.py# Windows Update 补丁清理
│   ├── quarantine.py    # 72 小时隔离 + 自动过期清理
│   ├── auth.py          # 授权校验 (HMAC-SHA256 + JWT)
│   └── safety_manager.py# 风险分级 (SAFE/WARNING/CRISIS)
├── ai/
│   ├── cloud_engine.py  # 云端 AI 分析 (GLM-4-flash)
│   ├── local_engine.py  # 本地规则引擎 (降级兜底)
│   └── batch_processor.py # 批处理聚合 (单文件->批量)
└── ui/
    ├── app.py           # 根视图管理，导航，主题切换
    ├── tray_manager.py  # 系统托盘集成
    ├── views/           # 页面级组件
    └── components/      # 可复用 UI 组件
```

### 本地调试

该项目使用 `.env` 管理敏感配置，请参考 `.env.example` 进行配置。

```bash
python src/main.py
```

### 构建发布

```bash
# 自动清理并生成全量免安装目录
python scripts/build_release.py

# (可选) 调用 Inno Setup 编译安装向导
python scripts/build_installer.py
```

### 运行测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行回归测试
python -m pytest tests/test_fixes.py -v
```

---

## 免责声明

本软件涉及 Windows 底层核心操作。开发者不对任何意外导致的系统崩溃、数据丢失承担连带法律责任。**请在知晓风险的情况下使用**。

---

<div align="center">
    <b>互为螺旋 · 禅意清扫</b><br>
    <i>Crafted with ❤️ for Windows Geeks.</i>
</div>
