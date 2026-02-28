# 项目核心上下文：ZenClean (禅清)

## 项目概述
ZenClean 是一个现代化的 Windows C 盘深度清理与优化工具。它旨在解决用户 C 盘空间不足的痛点，同时提供安全、智能且极具美感的交互体验。

## 核心路线
1. **启发源**：参考了 `One-click-cleaning-of-C-drive` 的广泛扫描逻辑。
2. **技术栈**：Python 3.10 + Flet (Flutter GUI)。
3. **亮点功能**：
    - **AI 混合分析**：本地知识库 + 云端 LLM 辅助决策。
    - **三层安全找回**：模拟预览、回收站中转、自动备份一键恢复。
    - **EXE 独立分发**：支持打包为单个可执行文件，自动请求 UAC 管理员权限。

## 当前进度
- [x] 完成项目详细设计方案 ([implementation_plan.md](./implementation_plan.md))
- [x] 初始化项目结构
- [/] 核心扫描与清理引擎开发中

## 关键路径
- `D:\软件开发\ZenClean\src\core`：核心逻辑
- `D:\软件开发\ZenClean\src\ai`：AI 分析模块
- `D:\软件开发\ZenClean\src\ui`：Flet 界面
