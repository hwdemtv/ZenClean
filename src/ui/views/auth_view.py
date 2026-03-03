import os
import flet as ft
import re
from datetime import datetime
from config.settings import (
    COLOR_ZEN_PRIMARY, COLOR_ZEN_BG, COLOR_ZEN_GOLD, 
    COLOR_ZEN_TEXT_MAIN, COLOR_ZEN_TEXT_DIM
)
from config.version import __version__ as APP_VERSION

class AuthView(ft.Column):
    def __init__(self, app):
        self.app = app
        self._quota_text = ft.Text("正在获取云端 AI 额度...", color=COLOR_ZEN_PRIMARY, size=14, italic=True)

        self._code_input = ft.TextField(
            label='激活码（格式：ZEN-，可在微信公众号(互为螺旋工具箱)发送"获取激活码"领取）',
            width=500,
            password=True,
            can_reveal_password=True,
            border_color=COLOR_ZEN_PRIMARY,
            label_style=ft.TextStyle(color=COLOR_ZEN_TEXT_DIM),
            color=COLOR_ZEN_TEXT_MAIN,
        )
        
        # 这里为了做富文本点击，将原生的简易 Checkbox 拆分为纯勾选框 + 后跟的 Row
        self._agree_checkbox = ft.Checkbox(
            value=False,
            fill_color=COLOR_ZEN_PRIMARY,
        )
        
        self._agree_checkbox = ft.Checkbox(
            value=False,
            fill_color=COLOR_ZEN_PRIMARY,
        )

        def _toggle_checkbox(e):
            self._agree_checkbox.value = not self._agree_checkbox.value
            self.update()
        
        # 构造协议行
        self._terms_row = ft.Row([
            self._agree_checkbox,
            ft.Container(
                content=ft.Text("我已阅读并完全同意", color=COLOR_ZEN_TEXT_DIM, size=13),
                on_click=_toggle_checkbox,
                ink=True
            ),
            ft.Container(
                content=ft.Text("《软件许可协议》", color=ft.colors.BLUE_400, size=13),
                on_click=self._show_license,
                ink=True
            ),
            ft.Text("与", color=COLOR_ZEN_TEXT_DIM, size=13),
            ft.Container(
                content=ft.Text("《隐私政策》", color=ft.colors.BLUE_400, size=13),
                on_click=self._show_privacy,
                ink=True
            ),
            ft.Container(
                content=ft.Text("，知晓并自担清理数据丢失风险。", color=COLOR_ZEN_TEXT_DIM, size=13),
                on_click=_toggle_checkbox,
                ink=True
            )
        ], spacing=0, wrap=True)

        self._error_text = ft.Text(color=ft.colors.RED_400, visible=False)

        submit_btn = ft.ElevatedButton(
            "立即激活",
            width=500,
            height=50,
            bgcolor=COLOR_ZEN_PRIMARY,
            color="white",
            on_click=self._on_submit,
        )

        if self.app.is_activated:
            # 动态计算是否显示离线提醒
            expiry_infos = [
                ft.Row([
                    ft.Text("总订阅到期日：", color=COLOR_ZEN_TEXT_DIM, size=14),
                    ft.Text(f"{self.app.total_expiry_date or '永久'}", color=COLOR_ZEN_GOLD, weight=ft.FontWeight.BOLD),
                ], alignment=ft.MainAxisAlignment.CENTER)
            ]
            
            if self.app.lease_expiry_date:
                try:
                    lease_dt = datetime.strptime(self.app.lease_expiry_date, "%Y-%m-%d %H:%M")
                    days_left = (lease_dt - datetime.now()).days
                    if days_left < 3:
                        expiry_infos.extend([
                            ft.Row([
                                ft.Text("离线许可至：", color=COLOR_ZEN_TEXT_DIM, size=14),
                                ft.Text(f"{self.app.lease_expiry_date}", color=COLOR_ZEN_GOLD),
                            ], alignment=ft.MainAxisAlignment.CENTER),
                            ft.Text("(离线期满前联网运行一次即可自动续期)", color=COLOR_ZEN_TEXT_DIM, size=12, italic=True)
                        ])
                except Exception:
                    pass

            content_col = ft.Column([
                ft.Container(
                    content=ft.Column([
                        ft.Container(
                            content=ft.Image(
                                src=os.path.join(self.app.page.client_storage.get("assets_dir") or "", "icon.png"), 
                                width=80, height=80, fit=ft.ImageFit.CONTAIN
                            ),
                            width=110, height=110,
                            border_radius=55,
                            bgcolor="#2A2F3A",  # 微亮底座，让黑色六边形浮出
                            alignment=ft.alignment.center,
                            margin=ft.margin.only(bottom=10),
                        ),
                        ft.Text("尊贵的 VIP 状态已激活", size=24, weight=ft.FontWeight.BOLD, color=COLOR_ZEN_GOLD),
                        
                        ft.Container(
                            content=ft.Column(expiry_infos, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                            padding=15,
                        ),

                        ft.Text("您已解锁全天候本地 AI 深层扫查与强力清除功能。", color=COLOR_ZEN_TEXT_DIM),
                        
                        # AI 额度展示区
                        ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.icons.BOLT, color=COLOR_ZEN_PRIMARY, size=20),
                                self._quota_text,
                            ], alignment=ft.MainAxisAlignment.CENTER),
                            margin=ft.margin.only(top=10, bottom=10),
                        ),

                        ft.Container(height=10),
                        ft.Container(
                            content=ft.Text("开始体验纯净系统", color="white", weight=ft.FontWeight.BOLD, size=16),
                            alignment=ft.alignment.center,
                            width=300,
                            height=45,
                            border_radius=25,
                            gradient=ft.LinearGradient(
                                begin=ft.alignment.top_left,
                                end=ft.alignment.bottom_right,
                                colors=["#1DD1A1", "#00C2FF"],
                            ),
                            shadow=ft.BoxShadow(spread_radius=1, blur_radius=15, color="#401DD1A1"),
                            ink=True,
                            on_click=lambda _: self.app.navigate_to("/scan")
                        ),
                        ft.Text(f"当前版本: v{APP_VERSION} Beta", size=14, color=COLOR_ZEN_TEXT_DIM),
                        ft.Container(height=10),
                        ft.ElevatedButton(
                            text="检查更新",
                            icon=ft.icons.SYSTEM_UPDATE_ALT,
                            on_click=self._on_check_update_click,
                            style=ft.ButtonStyle(
                                color=COLOR_ZEN_GOLD,
                                bgcolor=ft.colors.TRANSPARENT,
                                side=ft.BorderSide(1, COLOR_ZEN_GOLD),
                                shape=ft.RoundedRectangleBorder(radius=8),
                            )
                        )
                    ], spacing=5, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=40,
                    border=ft.border.all(1, COLOR_ZEN_GOLD),
                    border_radius=10,
                    bgcolor="#252525"
                )
            ], alignment=ft.MainAxisAlignment.CENTER)
        else:
            content_col = ft.Column([
                self._code_input,
                self._terms_row,
                self._error_text,
                ft.Container(height=10),
                submit_btn,
            ])

        super().__init__(
            controls=[
                ft.Column([
                    ft.Text("激活 ZenClean VIP 特权", size=24, weight=ft.FontWeight.BOLD, color=COLOR_ZEN_TEXT_MAIN),
                    ft.Text("输入激活码以解锁本地 AI 高级扫描与一键清除能力。", color=COLOR_ZEN_TEXT_DIM),
                ]),
                ft.Container(height=50),
                content_col,
            ],
            expand=True,
        )

    def _show_license(self, e):
        """显示软件许可协议简要版"""
        dlg = ft.AlertDialog(
            title=ft.Text("ZenClean 软件许可协议"),
            content=ft.Column([
                ft.Text("1. 本软件按“原样”提供，您将自行承担清理操作带来的数据丢失风险。"),
                ft.Text("2. 禁止对本软件进行逆向工程、破解或分发。"),
                ft.Text("3. AI 扫描引擎的判定结果仅供参考，不保证绝对的安全与正确。"),
                ft.Text("4. 您的激活码将与硬件设备绑定，换机需解除旧有关联。"),
            ], tight=True, spacing=10, scroll=ft.ScrollMode.AUTO),
            actions=[ft.TextButton("我已知晓并同意", on_click=lambda _: self._close_dlg(dlg))],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _show_privacy(self, e):
        """显示隐私政策简要版"""
        dlg = ft.AlertDialog(
            title=ft.Text("ZenClean 隐私政策"),
            content=ft.Column([
                ft.Text("1. 我们【不会】收集、上传您的任何私人文件内容至服务器。"),
                ft.Text("2. 云端 AI 引擎仅接受脱敏后的只读目录层级路径，用于风险等级评估。"),
                ft.Text("3. 您的设备生成的机器码（Machine ID）仅用于激活码的硬件绑定校验。"),
                ft.Text("4. 清理日志与识别库变更始终由于您的本地电脑存储和控制。"),
            ], tight=True, spacing=10, scroll=ft.ScrollMode.AUTO),
            actions=[ft.TextButton("我已知晓并同意", on_click=lambda _: self._close_dlg(dlg))],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _close_dlg(self, dlg: ft.AlertDialog):
        dlg.open = False
        self.page.update()

    def _on_submit(self, e):
        code = self._code_input.value.strip()
        
        if not self._agree_checkbox.value:
            self._error_text.value = "请先勾选同意免责声明与隐私协议"
            self._error_text.visible = True
            self.page.update()
            self.update()
            return
            
        if not code:
            self._error_text.value = "请输入激活码"
            self._error_text.visible = True
            self.update()
            return
            
        self._error_text.visible = False
        
        import traceback
        from core.logger import logger
        try:
            # 禁用输入并显示 loading
            self._code_input.disabled = True
            e.control.disabled = True
            e.control.text = "正在联网效验..."
            self.update()
            
            logger.info(f"Starting online verification for code: {code}")
            from core.auth import verify_license_online
            success, msg = verify_license_online(code)
            logger.info(f"Online verification result: success={success}, msg={msg}")
            
            # 恢复 UI 状态
            self._code_input.disabled = False
            e.control.disabled = False
            e.control.text = "立即激活"
        except Exception as ex:
            logger.error(f"Error during verification: {ex}")
            traceback.print_exc()
            self._error_text.value = f"程序出错: {ex}"
            self._error_text.visible = True
            self._code_input.disabled = False
            e.control.disabled = False
            e.control.text = "立即激活"
            self.update()
            return
        
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
            self.app.navigate_to("/auth")
            return
        else:
            self._error_text.value = msg
            self._error_text.visible = True
            
        self.update()

    def did_mount(self):
        """视图挂载后异步加载 AI 额度"""
        if self.app.is_activated:
            import threading
            def _load():
                from ai import cloud_engine
                quota = cloud_engine.get_quota()
                if quota and hasattr(self, "_quota_text"):
                    used = quota.get('used_today', 0)
                    limit = quota.get('daily_limit', 0)
                    self._quota_text.value = f"今日版图测绘算力：已消耗 {used} / 共 {limit} 次"
                    self._quota_text.italic = False
                    if self.page:
                        self.update()
            threading.Thread(target=_load, daemon=True).start()
