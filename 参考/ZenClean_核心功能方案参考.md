# ZenClean 核心功能逻辑参考手册 (v0.2.0)

本手册提取自 ZenClean 项目，记录了 **VIP 激活体系** 与 **云端广播系统** 的技术实现方案。

---

## 🔐 1. VIP 激活体系 (软硬件双重绑定)

方案特点：**启动即所得、離线可用、后台探活、硬件指纹安全**。

### A. 核心资产 (JWT + MachineID)
*   **硬件指纹**：使用 `py-machineid` 获取 `device_id`。
*   **授权载荷 (JWT)**：服务器颁发不透明 Token，关键字段包含：`device_id`, `product_id`, `exp` (过期时间)。

### B. 三级跳鉴权流程
1.  **启动态 (Fast Startup)**：仅读取本地 `auth.dat`，使用 `jwt.decode(verify_signature=False)` 快速比对 `device_id` 与 `exp`。此步**跳过网络**，优先保证 0.2s 极速启动。
2.  **静默探活 (Silent Ping)**：启动 2 秒后开启后台线程，每 30 分钟向服务器发起极简 POST 请求。
3.  **强制降级 (Auto Downgrade)**：若服务端返回 `[REVOKED]` 标记或 4xx 状态，UI 立即触发 `set_activated(False)`，清理本地缓存并弹出 SnackBar 提示。

### C. 开发者复用建议
*   **文件夹下钻**：在业务逻辑中，通过 `if app.is_activated:` 判定功能权限。
*   **防篡改**：周期性执行 `_check_time_drift()`，防止用户修改系统时间来骗取 VIP 周期。

---

## 📢 2. 云端广播系统 (去重通知逻辑)

方案特点：**强弱提醒分离、内容指纹去重、支持实时下发**。

### A. 通知载荷 (Payload Structure)
后端返回的 JSON 结构：
```json
{
  "id": "notice_2024_001",
  "title": "版本更新公告",
  "content": "发现新版本 v1.5...",
  "is_force": true,
  "action_url": "https://..."
}
```

### B. 去重机制 (Fingerprint)
*   **原理**：`fingerprint = f"{note_id}_{hash(content)}"`。
*   **策略**：客户端使用 `client_storage` 记录最后点击/查看的指纹。若指纹一致，则不再重复弹窗干扰用户。支持“同 ID 但内容更新后重新提醒”。

### C. 视觉呈现 (Visual Classes)
1.  **强提醒 (Force)**：使用 `ft.AlertDialog`。强制模态，带有“查看详情”和“我知道了”按钮，用于重大停服或更新通知。
2.  **弱提醒 (Standard)**：使用 `ft.SnackBar`。采用 `FLOATING` 行为，背景使用 `COLOR_ZEN_BG` 的提亮版（如 `#2D323E`），悬浮在底部中央，支持 10s 自动消失。

---

## 🛠️ 后端对接参考示例 (Python)

```python
# process_server_notification 简化逻辑库
def process_notice(app, note):
    notice_id = note.get("id")
    # 1. 检查去重
    if app.storage.get("read_ids") == notice_id: return
    
    # 2. 依据 is_force 决定用弹窗还是气泡
    if note.get("is_force"):
        show_alert_dialog(note)
    else:
        show_snack_bar(note)
        
    # 3. 标记已读
    app.storage.set("read_ids", notice_id)
```
