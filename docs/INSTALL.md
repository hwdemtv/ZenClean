# ZenClean 用户安装与运行指南

感谢您使用 **禅清 (ZenClean)** —— 基于 AI 的 Windows C 盘极速清理大师。

本文档将指导您如何成功运行本程序。

## 1. 系统要求
* **操作系统**：Windows 10 / Windows 11 (64位)
* **磁盘空间**：至少 150MB 可用空间（用于存放解压后的程序主体及运行日志）。
* **网络环境**：建议保持联网（用于激活校验与获取最新的 AI 云端清扫规则）。

## 2. 运行流程

1. 前往 [Release](https://github.com/hwdemtv/ZenClean/releases) 页面下载最新的绿色免安装版压缩包。
2. **解压**：将 ZIP 文件解压至非系统核心目录（如 `D:\Tools`）。
3. **运行**：双击 `ZenClean.exe`。
4. **授权**：如果是首次运行且拥有激活码，请在左侧"VIP 激活"处输入开启离线保护。
5. **依赖**：若提示"缺少运行库"，请参考下方常见问题安装 VC++ 运行时。

## 3. 环境变量配置 (可选)

`.env` 文件不再打包进可执行文件。如需自定义服务器地址，请将 `.env` 文件放置在 `ZenClean.exe` 同级目录。

参考 `.env.example` 配置项：
- `LICENSE_SERVER_URLS` - 授权服务器地址（逗号分隔多节点）
- `LICENSE_PRODUCT_ID` - 产品 ID
- `AI_GATEWAY_BASE_URL` - AI 网关地址

---

## 4. 管理员权限说明 (UAC)

ZenClean 旨在进行**系统级**的深度扫描（例如 `C:\Windows\Temp` 等隐藏锁死区）。
为了保证清理引擎的威力和数据完整性，**程序必须以 Administrator (系统管理员) 身份运行**。

* **运行表现**：当您双击 `ZenClean.exe` 时，屏幕可能会变暗，并弹出 UAC 询问窗口。
* **您的操作**：请务必点击 **"是"**。程序将会被系统赋予最高权限。

---

## 5. 常见启动报错与解决方案

### 报错："找不到 MSVCP140.dll" 或 "VC++ 组件缺失"
* **原因**：UI 渲染引擎 (Flet) 依赖于微软的 C++ 基础运行库。非常纯净的 Windows 新系统可能缺漏此组件。
* **解决办法**：请前往微软官方下载并安装 [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) (64位版本)。安装完成后无需重启，再次运行 `ZenClean.exe` 即可。

### 界面只显示一个无响应的黑窗口或持续闪退
* **建议**：这可能与您电脑的显卡驱动（OpenGL 渲染支持）有关。请检查您的显卡驱动是否已经正常安装。
* **应急排查**：查看 `C:\Users\您的用户名\AppData\Roaming\ZenClean\logs\` 目录下的最新 `.log` 文件，或将其截图发给技术支持。

---

*ZenClean 承诺绝不在未提示的情况下收集您的私人文件。详见我们的[隐私协议](PRIVACY_POLICY.md)。*
