# 阶段一 (MVP首发版) 深化实施方案 v2.0

本阶段聚焦于构建 ZenClean 最核心的扫描、鉴权与清理闭环，不依赖云端 API，完全通过本地引擎和 Flet UI 打造最小可用且体验惊艳的产品。

---

## 1. 目录结构与职责划分

`D:\软件开发\ZenClean\src\` 目录下完整骨架：

```text
src/
├── main.py                     # Flet 主入口，启动 UI 线程并管理鉴权状态
├── core/
│   ├── scanner.py              # 核心扫描引擎 (独立子进程 multiprocessing，IPC via Queue)
│   ├── cleaner.py              # 双重分诊清理执行器 (LOW→unlink, MEDIUM+→send2trash)
│   ├── auth.py                 # 鉴权模块 (对接 hw-license-center + NTP防回退)
│   └── whitelist.py            # 硬编码绝对白名单 (独立模块，防误删核心屏障)
├── ai/
│   ├── local_engine.py         # 本地规则引擎，解析 file_kb.json，输出风险等级与建议
│   └── cloud_mock.py           # 大模型占位符 (第一阶段强制返回 UNKNOWN，UI置灰)
├── ui/
│   ├── app.py                  # Flet 根视图管理器 (路由 + 深色主题初始化)
│   ├── components/
│   │   ├── file_list_item.py   # 单条文件行组件 (复选框+风险色标+路径+大小)
│   │   ├── risk_badge.py       # 风险等级徽章 (LOW绿/MEDIUM黄/HIGH红/CRISIS灰锁)
│   │   └── dialogs.py          # 弹窗集合 (免责弹窗、激活弹窗、确认清理弹窗)
│   └── views/
│       ├── splash.py           # 启动闪屏页 (缓解 PyInstaller 解压等待焦虑)
│       ├── auth_view.py        # 鉴权/激活页面
│       ├── scan_view.py        # 主扫描操作页 (大按钮 + 进度条 + 实时计数)
│       └── result_view.py      # 结果列表页 (虚拟化 ListView + 分类折叠树)
└── config/
    ├── file_kb.json            # 核心正则与路径知识库 (LOW/MEDIUM/HIGH/CRISIS 裁决)
    └── settings.py             # 全局配置读取 (白名单路径、日志级别、版本号等)
```

**变更说明（v2.0 新增）**：
- `core/whitelist.py` 从 `settings.py` 中**独立剥离**，白名单作为最高优先级守卫单独维护，杜绝被误配置覆盖。
- `ui/components/` 细化为三个可复用组件，避免后续 UI 代码膨胀混乱。
- 新增 `ui/views/splash.py`，对应 `deep_analysis.md` 中指出的启动速度痛点。

---

## 2. 核心数据结构与兼容性 (Forward Compatibility)

扫描引擎与 UI 通信的载体规定为标准 `dict`（通过 `multiprocessing.Queue` 传递）：

```python
# NodeDict 格式规范 v2.0
{
    "path": "C:\\Users\\Admin\\AppData\\Local\\Temp\\junk.tmp",
    "size_bytes": 1048576,
    "risk_level": "LOW",         # LOW | MEDIUM | HIGH | CRISIS | UNKNOWN
    "category": "system_temp",   # 用于 UI 分组折叠树的分类键
    "is_checked": True,          # UI 智能预勾选状态 (LOW→True, HIGH→False)
    "ai_advice": "系统临时文件，安全且无害。",  # 第一阶段由 file_kb.json 提供
    "is_whitelisted": False,     # 白名单命中标志，True 时 UI 直接锁定禁止勾选
    "scan_ts": 1700000000.0      # 扫描时间戳，用于结果缓存有效期校验
}
```

**v2.0 新增字段**：
- `is_whitelisted`：在 `scanner.py` 层即打标，UI 层无需再做二次判断，防止逻辑分散。
- `scan_ts`：为后续第二阶段"结果缓存复用"预留扩展点，第一阶段仅写入不使用。

---

## 3. 核心模块详细规格

### 3.1 `config/whitelist.py` — 绝对白名单（最高优先级）

白名单分两层：**路径前缀精确匹配** 和 **正则模式匹配**。

```python
# 绝对禁止访问的路径前缀 (大小写不敏感，normalized)
ABSOLUTE_PROTECTED_PREFIXES = [
    r"C:\Windows\System32",
    r"C:\Windows\SysWOW64",
    r"C:\Windows\WinSxS",
    r"C:\Windows\Boot",
    r"C:\Program Files\Windows Defender",
    r"C:\Program Files (x86)\Windows Defender",
    r"C:\Users\All Users\Microsoft\Windows Defender",
    r"C:\ProgramData\Microsoft\Windows Defender",
    # 注册表软链 / Junction 保护区
    r"C:\Documents and Settings",
]

# 关键文件名正则黑洞（哪怕 AI 说可清理也直接丢弃）
PROTECTED_FILENAME_PATTERNS = [
    r".*\.sys$",         # 驱动文件
    r".*\.dll$",         # 系统动态库
    r"ntldr",
    r"bootmgr",
    r"pagefile\.sys",
    r"hiberfil\.sys",
]
```

**验收标准**：单元测试覆盖以下用例全部返回 `CRISIS`/被拦截：
- `C:\Windows\System32\kernel32.dll`
- `C:\Windows\SysWOW64\` 下任意子路径
- `C:\pagefile.sys`

### 3.2 `config/file_kb.json` — 本地 AI 知识库结构

```json
{
  "version": "1.0.0",
  "rules": [
    {
      "id": "sys_temp_001",
      "pattern": "^C:\\\\(Users\\\\[^\\\\]+\\\\AppData\\\\Local\\\\Temp|Windows\\\\Temp)\\\\",
      "risk_level": "LOW",
      "category": "system_temp",
      "ai_advice": "Windows 系统临时文件，程序运行后的残余，安全可清理。",
      "is_checked_default": true
    },
    {
      "id": "browser_cache_001",
      "pattern": "^C:\\\\Users\\\\[^\\\\]+\\\\AppData\\\\(Local|Roaming)\\\\(Google\\\\Chrome|Microsoft\\\\Edge|Mozilla\\\\Firefox)\\\\(User Data\\\\[^\\\\]+\\\\Cache|cache2)\\\\",
      "risk_level": "LOW",
      "category": "browser_cache",
      "ai_advice": "浏览器缓存，删除后首次访问网页略慢，无数据损失风险。",
      "is_checked_default": true
    },
    {
      "id": "wechat_cache_001",
      "pattern": "^C:\\\\Users\\\\[^\\\\]+\\\\Documents\\\\WeChat Files\\\\[^\\\\]+\\\\FileStorage\\\\Cache\\\\",
      "risk_level": "LOW",
      "category": "social_cache",
      "ai_advice": "微信图片/文件加载缓存，仅限 Cache 子目录，不含聊天记录。",
      "is_checked_default": true
    },
    {
      "id": "wechat_media_001",
      "pattern": "^C:\\\\Users\\\\[^\\\\]+\\\\Documents\\\\WeChat Files\\\\[^\\\\]+\\\\FileStorage\\\\(Image|Video|File)\\\\",
      "risk_level": "HIGH",
      "category": "social_media",
      "ai_advice": "⚠️ 此目录包含微信接收的图片/视频/文件，误删将导致不可逆丢失！",
      "is_checked_default": false
    },
    {
      "id": "win_update_001",
      "pattern": "^C:\\\\Windows\\\\SoftwareDistribution\\\\Download\\\\",
      "risk_level": "MEDIUM",
      "category": "windows_update",
      "ai_advice": "Windows Update 下载缓存，清理后重新触发更新时需重新下载。",
      "is_checked_default": false
    },
    {
      "id": "recycle_bin_001",
      "pattern": "^C:\\\\\\$Recycle\\.Bin\\\\",
      "risk_level": "MEDIUM",
      "category": "recycle_bin",
      "ai_advice": "回收站文件，如无需恢复可清理。建议用户自行确认后删除。",
      "is_checked_default": false
    }
  ]
}
```

### 3.3 `core/scanner.py` — IPC 并发扫描引擎

**关键实现要点**：

1. **Junction/Symlink 防死锁**：遍历前检测 `os.path.islink(path)` 与 `os.stat(path).st_reparse_tag`，跳过所有重解析点，彻底杜绝无限递归。

2. **隐藏/系统文件过滤**：通过 `os.stat()` 的 `st_file_attributes` 跳过 `FILE_ATTRIBUTE_SYSTEM (0x4)` 与 `FILE_ATTRIBUTE_HIDDEN (0x2)` 文件（Windows 专属），避免扫描到无权访问的系统文件触发异常风暴。

3. **分批推送节奏控制**：每积攒 **50 条** NodeDict 打包一次推入 `Queue`，而非逐条推送。防止主进程 UI 线程的事件循环被淹没。

4. **哨兵信号**：扫描完毕推入 `{"type": "done", "total": N}` 作为结束标志，主进程据此关闭进度条。

```python
# scanner.py 核心流程伪代码
class ScanWorker(multiprocessing.Process):
    def run(self):
        batch = []
        for root, dirs, files in os.walk(TARGET_ROOT, followlinks=False):
            # 1. 过滤白名单目录（就地修改 dirs 列表，阻止 os.walk 递归进入）
            dirs[:] = [d for d in dirs
                       if not whitelist.is_protected(os.path.join(root, d))]
            # 2. 过滤 Junction/Symlink 目录
            dirs[:] = [d for d in dirs
                       if not os.path.islink(os.path.join(root, d))]

            for fname in files:
                fpath = os.path.join(root, fname)
                if whitelist.is_protected(fpath):
                    continue
                node = local_engine.analyze(fpath)
                batch.append(node)
                if len(batch) >= 50:
                    self.queue.put(batch)
                    batch = []

        if batch:
            self.queue.put(batch)
        self.queue.put({"type": "done"})
```

### 3.4 `core/cleaner.py` — 双重分诊清理引擎

**执行逻辑**：

| 风险等级 | 清理策略 | 理由 |
|---|---|---|
| `LOW` | `pathlib.Path.unlink()` 物理删除 | 毫无争议的垃圾，最大化即时 C 盘释放量 |
| `MEDIUM` | `send2trash.send2trash()` 移入回收站 | 保留后悔药，用户可自行确认清空 |
| `HIGH` | 仅在用户**手动勾选且二次确认**后，调用 `send2trash` | 不自动处理，风险责任转移给用户 |
| `CRISIS` | **程序级硬拒绝，不执行任何操作** | 白名单命中，无论如何不执行 |
| `UNKNOWN` | 第一阶段：跳过（UI 置灰） | 待第三阶段云端 AI 接入后启用 |

**清理后收尾**：
- 统计实际释放字节数，更新 UI"已释放空间"计数器动画。
- **收尾动作**：清理完毕触发释放动效。在主界面弹出大红按钮：**【彻底清空回收站争议项（免责/危）】**。


### 3.5 `core/auth.py` — 鉴权模块

**第一阶段鉴权流程**：

```
用户输入卡密
    ↓
本地格式校验 (正则: ZEN-VIP\+VX-\w+)
    ↓
提取机器码 (py-machineid.get_id())
    ↓
POST hw-license-center /api/v1/verify
    Body: { "license_key": "...", "machine_id": "...", "product": "zenclean" }
    ↓
服务端响应: { "valid": true, "expire_ts": null, "tier": "beta" }
    ↓
本地缓存 JWT Token（写入 %AppData%\ZenClean\auth.dat，AES-128 加密存储）
    ↓
解锁"一键清理"按钮
```

**NTP 防回退**（第一阶段简化版）：
- 应用启动时，对比本机时间与 `pool.ntp.org` 时间差。
- 若偏差超过 **300 秒**，弹出警告并禁止离线 JWT 校验，强制联网验证。

---

## 4. UI 关键页面规格

### 4.1 启动闪屏 (`splash.py`)
- 纯黑背景 + ZenClean Logo（SVG矢量）+ 品牌口号"让 C 盘重获新生"
- 加载动画：三个小圆点循环渐变
- 等待主窗口初始化完毕后自动跳转，**无需用户操作**

### 4.2 主扫描页 (`scan_view.py`)
- 顶部：磁盘空间仪表盘（已用/可用/总量，环形进度条）
- 中部：大号"开始扫描"按钮（扫描中变为"正在扫描… X 个文件"进度状态）
- 底部状态栏：实时"已发现 XX GB 可释放空间"滚动计数

### 4.3 结果列表页 (`result_view.py`)
- 按 `category` 分组折叠展示（每组显示总大小）
- 每行：`[复选框] [风险徽章] 路径文字（截断省略号） [大小] [AI建议tooltip]`
- 底部固定操作栏：全选/反选 + **"清理已选项"**按钮
- **虚拟化渲染**：使用 Flet `ListView` 的 `item_extent` 固定行高策略，配合分批渲染，保证 5 万条数据下 UI 不卡帧

### 4.4 鉴权弹窗 (`dialogs.py`)
- 未激活用户点击"一键清理"时弹出
- 内容：卡密输入框 + "去关注公众号获取免费激活码"引流按钮 + 激活按钮
- 激活成功：显示绿色"✓ 已激活 ZenClean Beta"并关闭弹窗

---

## 5. 日志系统规格（补充自 `deep_analysis.md`）

- **日志路径**：`%AppData%\ZenClean\logs\zenclean_YYYY-MM-DD.log`
- **默认级别**：`INFO`，设置中可切换 `DEBUG`
- **自动滚动**：保留最近 **7 天**，超期自动删除
- **关键记录事件**：
  - 每次扫描的启动/结束时间与文件总数
  - 每次清理操作（路径、大小、策略）
  - 鉴权成功/失败事件
  - 白名单命中拦截事件（级别 WARNING）
  - 任何 `Exception` 全量堆栈（级别 ERROR）

---

## 6. 版本更新检查（补充自 `deep_analysis.md`）

应用启动时（非阻塞异步线程）：
1. 请求 `https://api.github.com/repos/{owner}/zenclean/releases/latest`
2. 对比本地 `settings.py` 中的 `APP_VERSION` 与 `tag_name`
3. 若有新版本，在主界面顶部展示非侵入式提示条："发现新版本 vX.X.X，点击下载"
4. 点击跳转 GitHub Release 页面，用户手动下载（第一阶段不做自动更新）

---

## 7. 分步开发工序 (Task Sequence)

### 步骤 1.1: 基建与安全底座
**实现内容**：
- 编写 `config/settings.py`（版本号、日志配置、扫描根目录）
- 编写 `core/whitelist.py`，录入绝对白名单前缀与文件名正则
- 编写并填充 `config/file_kb.json`，覆盖 10 类以上常见垃圾路径规则

**验收标准**：单元测试 15 个用例：
- `C:\Windows\System32\*` → `CRISIS`（被 whitelist 拦截）
- `C:\Windows\Temp\*.tmp` → `LOW`
- `C:\Users\*\AppData\Local\Temp\*` → `LOW`
- `C:\Users\*\Documents\WeChat Files\*\FileStorage\Cache\*` → `LOW`
- `C:\Users\*\Documents\WeChat Files\*\FileStorage\Image\*` → `HIGH`
- `C:\Windows\SoftwareDistribution\Download\*` → `MEDIUM`

### 步骤 1.2: 本地 AI 规则引擎
**实现内容**：
- 编写 `ai/local_engine.py`：读取 `file_kb.json`，输入路径字符串，按规则优先级依次匹配正则，返回 `(risk_level, category, ai_advice, is_checked_default)`
- 编写 `ai/cloud_mock.py`：统一返回 `{"risk_level": "UNKNOWN", "ai_advice": "云端分析功能将在 VIP 版本开放"}`

**验收标准**：同步运行步骤 1.1 的测试用例，100% 通过率。

### 步骤 1.3: IPC 并发扫描引擎
**实现内容**：
- 在 `core/scanner.py` 内实现 `ScanWorker(multiprocessing.Process)` 子进程类
- 实现 Junction 检测、系统/隐藏文件过滤、50条批量推送
- 主进程侧实现 `QueueConsumer` 线程，持续消费 Queue 并触发 Flet UI 更新回调

**验收标准**：
- C 盘 10 万文件扫描：主进程 UI 响应延迟 < 100ms，总扫描时间 < 15 秒
- 扫描含 Junction Point 的目录（如 `C:\Documents and Settings`）不死循环

### 步骤 1.4: Flet UI 框架搭建
**实现内容**：
- `ui/app.py`：路由管理，深色主题（背景色 `#0D0D0D`，强调色 `#00D4AA`）
- `ui/views/splash.py`：闪屏页
- `ui/views/scan_view.py`：主扫描操作页
- `ui/views/result_view.py`：虚拟化列表结果页
- `ui/views/migration_view.py`：系统大文件夹无损搬家专页
- `ui/views/auth_view.py`：鉴权/激活页
- `ui/components/`：三个可复用组件

**验收标准**：
- 深色主题渲染正确，无白色闪烁
- 5 万条 NodeDict 加载到 ListView，滚动帧率 ≥ 30fps

### 步骤 1.5: 鉴权模块与商业闭环
**实现内容**：
- 编写 `core/auth.py`，实现 hw-license-center 联调与 JWT 本地缓存
- 实现 NTP 时间防回退检测（简化版）
- 编写 `ui/views/auth_view.py` 与 `ui/components/dialogs.py` 的激活弹窗

**验收标准**：
- 输入当天（或未来时间）的动态公码如 `ZEN-VIP-20991231` → 激活成功，解锁"一键清理"
- 输入过期卡密（如昨天的）→ 提示过期，要求回公众号获取
- 断网状态下由于仅依赖本地时间 -> 正常工作

### 步骤 1.6: 双重清理引擎（终极爽感）
**实现内容**：
- 编写 `core/cleaner.py`，实现双重分诊策略
- 接入 `structlog` 记录每条清理操作
- 清理完毕触发 UI 空间释放数字滚动动画
- 展示"彻底清空回收站"红色按钮与免责弹窗

**验收标准**：
- 清理 100 个 LOW 级文件：全部物理删除，C 盘空间即时变化
- 清理 10 个 MEDIUM 级文件：全部出现在回收站
- CRISIS 级文件（白名单命中）：拒绝执行，写入 WARNING 日志

### 步骤 1.7: 系统大文件夹无损搬家 (User Shell Folders Migration)
- **实现内容**：在 `core/` 下新增 `migration.py`，处理截图中的“桌面、下载、图片、视频、文档”等默认库的转移。
- **执行逻辑**：
    - 读取 Windows 注册表 `HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders` 判定当前绝对路径。
    - 将旧路径内的所有海量数据安全 `shutil.move` 至用户选择的非 C 盘目录。
    - 修改注册表键值，并调用 Win32 API `SHChangeNotify` 发信号刷新系统缓存。
- **验收标准**：一键点击后，原本在 C 盘的下载和桌面等文件被平滑移动至 D 盘，图标不花退，空间立刻获得十 GB 级物理释放。

---

## 8. 第一阶段上线准则

1. **绝对安全红线**：
   - 绝不触碰 `System32`、`SysWOW64`、`Windows Defender` 等系统命门
   - 微信仅清理 `FileStorage/Cache`，**绝不进入** `Image/Video/File`

2. **商业闭环验收**：
   - 激活界面成功挡下无效卡密
   - "一键清理"按钮仅授权用户可点击
   - 未授权用户的每次清理需手动逐项勾选（完成引流摩擦设计）

3. **爽感验收**：
   - 清理结果**必须**让 C 盘至少释放 2-5 GB 物理空间（真实测试机验证）
   - 释放数字滚动动画流畅，无卡顿

4. **稳定性验收**：
   - 连续扫描 3 次不崩溃
   - 日志文件正确生成且可读

---

## 9. 已知风险与对策

| 风险 | 概率 | 对策 |
|---|:---:|---|
| Flet 版本 API 变动导致 UI 破坏 | 中 | 锁定 `flet==0.21.x`，写入 `requirements.txt` |
| PyInstaller 打包后体积 > 100MB | 高 | 第一阶段接受，第二阶段评估 `--onedir` + NSIS |
| `multiprocessing` 在 `--onefile` 模式下 spawn 失败 | 中 | 主入口添加 `multiprocessing.freeze_support()` |
| hw-license-center 服务宕机 | 低 | 缓存 JWT 保证 24 小时离线可用，到期后降级提示 |
| 杀毒软件误报（因涉及系统目录操作） | 高 | 第一阶段准备 360/火绒白名单申请文档，暂不签 EV 证书 |
