# 修复系统级特殊目录搬运崩溃 (WinError 5)

## 问题分析
用户在迁移 `文档` (Documents) 文件夹时遇到了 `[WinError 5] 拒绝访问。: 'C:\Users\...\Documents\My Music'`。
这是因为 Windows 中的特殊系统目录（如 My Music）可能会由于权限问题拒绝访问。
虽然在 `migration.py` 中的子目录遍历 `list(os.scandir(src))` 和 `shutil.move` 都受 `try...except OSError` 保护，但仍有两个明显漏洞导致异常逃逸进而引发崩溃：

1. **`is_dir` 与 `is_reparse` 属性判定的疏漏**：
   在 `_merge_move` 函数中，直接且未受保护地调用了 `if entry.is_dir(follow_symlinks=False):`。如果 `entry` 代表一个无权访问的系统节点，且系统没能缓存它的元信息，`is_dir()` 会触发底层的 `stat` 调用并直接引发 `[WinError 5]` 导致程序崩溃。
   另外，属性读取代码 `attrs = entry.stat(...).st_file_attributes` 虽然被捕获，但它在发生异常后直接 `pass` 并将 `is_reparse` 设为 `False`，导致后续逻辑将该受限目录视作普通目录/文件进行操作（这本身就是高风险动作）。

2. **跨盘文件移动中潜在的反向影响**：
   在 `app_migrator.py` 的迁移逻辑中，`os.listdir(src_path)` 和对 `s.is_dir()` 以及 `s.stat()` 的调用也缺乏粒度更细的异常捕获。如果列表内有系统级隐藏大文件（如页面文件、特定被锁缓存），该报错会导致当次整体目标迁移判定为了报错失败。

## 迁移目标调研列表 (待选)

以下是调研到的高价值迁移目标，建议用户选择后加入 [APP_TARGETS](file:///D:/软件开发/ZenClean/src/core/app_migrator.py)：

## 优先实装清单 (国内高性价比 + AI 大户)

基于用户反馈，我们将以下目标列为优先实装：

### 1. 办公社交类 (国内优先)
*   **钉钉 (DingTalk)**、**飞书 (Feishu)**、**百度网盘**。

### 2. AI 助手类 (空间杀手)
*   **Ollama**: 本地模型目录 `%USERPROFILE%\.ollama` (5GB-100GB+)。
*   **ChatGPT / Claude / Cursor**: 官方桌面应用缓存与索引库。
*   **.gemini**: 助手运行轨迹产物。

### 3. 应用工具类
*   **Chrome / Edge**: 浏览器用户全量数据（缓存、插件、配置）。

## 高占用文件夹处理策略 (基于用户截图)

针对扫描出的具体“大户”，我们的处理原则是：**能搬家的不清理，能清理的不强删。**

| 文件夹 | 占用 | 建议操作 | ZenClean 处理路径 |
| :--- | :--- | :--- | :--- |
| **Users / AppData** | **~114 GB** | **高危/不可删除** | 这是最核心的区域。我们通过“应用搬家”将其中具体的微信、QQ、浏览器等目录搬走，而不动系统配置。 |
| **LarkShell** | **7.9 GB** | **搬家 (首选)** | 这是**飞书 (Feishu)** 的数据目录。已实装“大厂应用搬家”，可直接将其迁至 D 盘。 |
| **.gemini** | **8.9 GB** | **清理 (Purge)** | 这是 AI 助手的运行时历史日志与录制视频。如不需要回溯历史，可安全一键清理。 |
| **ProgramData** | **13.4 GB** | **安全清理** | 主要通过“陈年补丁粉碎”功能，删除其中的 `$PatchCache$` 和 `Package Cache` 存根。 |

## 补丁粉碎方案 (`$PatchCache$` & DISM)

针对系统冗余补丁，我们将采取“物理粉碎 + 官方压缩”的双轨方案：

### 1. `$PatchCache$` 物理粉碎
*   **目标**: `C:\Windows\Installer\$PatchCache$`
*   **逻辑**: 该目录仅为软件修复存根。我们将实现一个静默粉碎接口，在清理前进行 UI 强提示。

### 2. DISM 系统更新压缩
*   **命令**: `Dism.exe /online /Cleanup-Image /StartComponentCleanup`
*   **价值**: 安全删除已被替代的旧版更新组件，是官方推荐的 `WinSxS` 回血手段。
*   **注意**: 执行时间可能较长（3-10分钟），需在 UI 增加“深度扫描中”的滚动条提示。

## Proposed Changes

### [MODIFY] src/core/migration.py
- **全方位包裹文件属性访问**：在 `_merge_move` 内迭代条目时，若 `entry.stat()` 由于权限问题引发异常，直接视为受保护文件而 `continue` 跳过，不让它有进入后续 `is_dir()` 测试以及 `shutil.move()` 触发 `PermissionError` 的机会。
- **保护 `is_dir` 判断**：将 `entry.is_dir(...)` 放入 `try...except OSError` 中，遇到异常判定为不可读目标直接跳过。
- **防范边界行为**：确保 `mkdir` 与空目录删除环节中的 `rmdir` 报错完全闭环。

### [MODIFY] src/core/app_migrator.py
- 对 `for item in os.listdir(src_path):` 的内部单文件判定操作进行安全强化。将 `s.is_dir()` 和 `s.stat()` 以及 `shutil.move` 封装在细粒度的 `try...except` 块中。单文件遭遇 WinError 时，只输出警告日记而避免中断 `app_migrator` 后续所有文件的备份。保证最大限度的“尽力迁移（Best-effort migration）”。

## Verification Plan

### Automated Tests
1. 运行预先编写的 `try_except_simulation.py` 或类似的探测脚本，确保我们对 Python `entry.is_dir()` 抛出 `OSError` 时的判断逻辑成立。
2. `python -c "import traceback; ... "` 触发一次异常，检查程序不再崩溃并成功绕过。

### Manual Verification
1. 引导用户重试迁移，观察 `Documents`（文档）移动行为，确保能够跨越 `My Music` 等系统限制目录并不爆出红框异常。
2. 检查 `ZenClean_Migration` 日志输出，验证无权限项目确实被成功跳过了。
