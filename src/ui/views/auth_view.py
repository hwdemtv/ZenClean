import flet as ft
import re
from datetime import datetime


class AuthView(ft.Column):
    def __init__(self, app):
        self.app = app

        self._code_input = ft.TextField(
            label='激活码（格式：ZEN-VIP-YYYYMMDD，可在微信公众号发送"获取激活码"领取）',
            width=500,
            password=True,
            can_reveal_password=True,
            border_color="#00D4AA",
        )
        self._error_text = ft.Text(color=ft.colors.RED_400, visible=False)

        submit_btn = ft.ElevatedButton(
            "立即激活",
            width=500,
            height=50,
            bgcolor="#00D4AA",
            color="white",
            on_click=self._on_submit,
        )

        if self.app.is_activated:
            # 动态计算是否显示离线提醒
            expiry_infos = [
                ft.Row([
                    ft.Text("总订阅到期日：", color="#AAAAAA", size=14),
                    ft.Text(f"{self.app.total_expiry_date or '永久'}", color="#00D4AA", weight=ft.FontWeight.BOLD),
                ], alignment=ft.MainAxisAlignment.CENTER)
            ]
            
            if self.app.lease_expiry_date:
                try:
                    lease_dt = datetime.strptime(self.app.lease_expiry_date, "%Y-%m-%d %H:%M")
                    days_left = (lease_dt - datetime.now()).days
                    if days_left < 3:
                        expiry_infos.extend([
                            ft.Row([
                                ft.Text("离线许可至：", color="#AAAAAA", size=14),
                                ft.Text(f"{self.app.lease_expiry_date}", color="#FFA500"),
                            ], alignment=ft.MainAxisAlignment.CENTER),
                            ft.Text("(离线期满前联网运行一次即可自动续期)", color="#666666", size=12, italic=True)
                        ])
                except Exception:
                    pass

            content_col = ft.Column([
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.icons.VERIFIED_USER, size=60, color="#00D4AA"),
                        ft.Text("尊贵的VIP状态已激活", size=24, weight=ft.FontWeight.BOLD, color="#00D4AA"),
                        
                        ft.Container(
                            content=ft.Column(expiry_infos, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                            padding=15,
                        ),

                        ft.Text("您已解锁全天候本地 AI 深层扫查与强力清除功能。", color="#AAAAAA"),
                        ft.Container(height=20),
                        ft.ElevatedButton(
                            "开始体验纯净系统",
                            bgcolor="#00D4AA",
                            color="white",
                            width=300,
                            height=45,
                            on_click=lambda _: self.app.navigate_to("/scan")
                        )
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.alignment.center,
                    padding=40,
                    border=ft.border.all(1, "#00D4AA"),
                    border_radius=10,
                    bgcolor="#0A1A14"
                )
            ], alignment=ft.MainAxisAlignment.CENTER)
        else:
            content_col = ft.Column([
                self._code_input,
                self._error_text,
                ft.Container(height=10),
                submit_btn,
            ])

        super().__init__(
            controls=[
                ft.Column([
                    ft.Text("激活 ZenClean VIP 特权", size=24, weight=ft.FontWeight.BOLD),
                    ft.Text("输入激活码以解锁本地 AI 高级扫描与一键清除能力。", color="#AAAAAA"),
                ]),
                ft.Container(height=50),
                content_col,
            ],
            expand=True,
        )

    def _on_submit(self, e):
        code = self._code_input.value.strip()
        if not code:
            self._error_text.value = "请输入激活码"
            self._error_text.visible = True
            self.update()
            return
            
        self._error_text.visible = False
        
        # 禁用输入并显示 loading
        self._code_input.disabled = True
        e.control.disabled = True
        e.control.text = "正在联网效验..."
        self.update()
        
        from core.auth import verify_license_online
        success, msg = verify_license_online(code)
        
        # 恢复 UI 状态
        self._code_input.disabled = False
        e.control.disabled = False
        e.control.text = "立即激活"
        
        if success:
            # 重新加载本地状态以获取最新的 JWT Payload
            from core.auth import check_local_auth_status
            is_val, payload = check_local_auth_status()
            lease_str = None
            sub_str = None
            if is_val and payload:
                exp_ts = payload.get("exp")
                lease_str = datetime.fromtimestamp(exp_ts).strftime("%Y-%m-%d %H:%M")
                backend_exp = payload.get("_backend_expires_at")
                if backend_exp:
                    try:
                        dt = datetime.fromisoformat(backend_exp.replace("Z", "+00:00"))
                        sub_str = dt.astimezone().strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        sub_str = backend_exp[:16].replace("T", " ")
                else:
                    sub_str = lease_str
            self.app.set_activated(True, lease_str, sub_str)
        else:
            self._error_text.value = msg
            self._error_text.visible = True
        self.update()
