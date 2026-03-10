import flet as ft
from config.settings import COLOR_ZEN_DANGER, COLOR_ZEN_TEXT_DIM

def show_confirm_clean_dialog(page: ft.Page, size_str: str, node_count: int, on_confirm, on_cancel=None):
    """最终清理的确认对话框"""
    def _close(_):
        dlg.open = False
        page.update()
        if on_cancel:
            on_cancel()

    def _confirm(_):
        dlg.open = False
        page.update()
        on_confirm()

    dlg = ft.AlertDialog(
        title=ft.Row([ft.Icon(ft.icons.WARNING_AMBER_ROUNDED, color=COLOR_ZEN_DANGER), ft.Text("确认开始深度清理？")]),
        content=ft.Text(f"系统即将正式处理 {node_count} 个勾选项，共计约 {size_str}。\n\n提示：100% 确认无害的低风险临时项将被直接释放，中/高风险项将移入时光机沙箱（保留72小时反悔期）。"),
        actions=[
            ft.TextButton("我再想想", on_click=_close, style=ft.ButtonStyle(color=COLOR_ZEN_TEXT_DIM)),
            ft.ElevatedButton("开始清理", bgcolor=COLOR_ZEN_DANGER, color="white", on_click=_confirm),
        ]
    )
    page.overlay.append(dlg)
    dlg.open = True
    page.update()

def show_empty_recycle_bin_dialog(page: ft.Page, on_confirm, on_cancel):
    """清空回收站提示对话框"""
    def _close(_):
        dlg.open = False
        page.update()
        on_cancel()

    def _confirm(_):
        dlg.open = False
        page.update()
        on_confirm()

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Row([ft.Icon(ft.icons.WARNING_AMBER_ROUNDED, color=COLOR_ZEN_DANGER), ft.Text("清理完成：是否直达时光机？")]),
        content=ft.Text("所选文件已处理完毕。\n\n部分重要文件已被移入左侧导航栏的【时光机】隔离舱，以防止您误删。您可以去那里彻底粉碎它们，或者随时原路恢复。"),
        actions=[
            ft.TextButton("知道了", on_click=_close, style=ft.ButtonStyle(color=COLOR_ZEN_TEXT_DIM)),
            ft.ElevatedButton("前往时光机", bgcolor=COLOR_ZEN_DANGER, color="white", on_click=_confirm),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.overlay.append(dlg)
    dlg.open = True
    page.update()

def show_confirm_dialog(
    page: ft.Page,
    title: str,
    content: ft.Control,
    on_result: callable,
    confirm_text: str = "确定",
    cancel_text: str = "取消",
    is_danger: bool = False
):
    """
    通用的确认对话框 (Yes/No)
    on_result 接受一个 bool 参数，True 为确认，False 为取消。
    """
    def _close(e):
        dlg.open = False
        page.update()
        on_result(False)

    def _confirm(e):
        dlg.open = False
        page.update()
        on_result(True)

    confirm_color = COLOR_ZEN_DANGER if is_danger else ft.colors.BLUE_600

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Row([
            ft.Icon(ft.icons.WARNING_AMBER_ROUNDED if is_danger else ft.icons.INFO_OUTLINE, color=confirm_color),
            ft.Text(title)
        ]),
        content=content,
        actions=[
            ft.TextButton(cancel_text, on_click=_close, style=ft.ButtonStyle(color=COLOR_ZEN_TEXT_DIM)),
            ft.ElevatedButton(confirm_text, bgcolor=confirm_color, color="white", on_click=_confirm),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.overlay.append(dlg)
    dlg.open = True
    page.update()


def show_eula_dialog(page: ft.Page, on_accepted: callable):
    """
    首次启动时的强制免责声明弹窗 (EULA)。
    用户必须主动勾选"已阅读并同意"后才能解锁"进入"按钮。
    确认后将状态持久化到 client_storage，后续启动不再弹出。
    """

    _EULA_TEXT = (
        "《禅清 (ZenClean) 最终用户许可协议》\n\n"
        "版本：1.0 ｜ 生效日期：2026年3月\n\n"
        "—————————————————\n\n"
        "一、服务性质声明\n"
        "ZenClean 是一款按现状（\"AS-IS\"）提供的 Windows 系统效率优化工具。"
        "开发者已尽最大努力确保清理逻辑的安全性，但无法对所有潜在的边界情况做出绝对保证。\n\n"
        "二、风险告知\n"
        "1. 低风险项（如系统临时文件）将被直接释放。\n"
        "2. 中/高风险项将被移入【时光机】隔离沙箱，保留 72 小时的恢复窗口期。\n"
        "3. 用户主动选择【彻底粉碎】沙箱内容后，数据将不可恢复。\n\n"
        "三、责任限度\n"
        "因使用本软件进行的任何清理、搬家操作而造成的数据损失，"
        "开发者的最大赔偿责任不超过用户购买本软件所实际支付的金额。\n\n"
        "四、知识产权保护\n"
        "任何试图脱壳、反编译、抓包篡改心跳数据的行为，"
        "均视为侵犯商业秘密，开发者保留法律追诉权利。\n\n"
        "五、隐私保护\n"
        "本软件不会上传任何个人文件内容。"
        "仅在鉴权时上报匿名设备指纹（Machine ID）用于防滥用。\n\n"
        "—————————————————\n\n"
        "继续使用本软件即表示您已充分理解并自愿接受以上条款。"
    )

    # 勾选框控件
    agree_checkbox = ft.Checkbox(label="我已阅读并同意以上条款", value=False)
    # 进入按钮（初始禁用）
    enter_btn = ft.ElevatedButton(
        "进入 ZenClean",
        bgcolor=ft.colors.GREY_800,
        color=ft.colors.GREY_500,
        disabled=True,
        width=200,
    )

    def _on_agree_change(e):
        checked = agree_checkbox.value
        enter_btn.disabled = not checked
        enter_btn.bgcolor = "#009688" if checked else ft.colors.GREY_800
        enter_btn.color = "white" if checked else ft.colors.GREY_500
        page.update()

    def _on_enter(e):
        dlg.open = False
        page.update()
        # 持久化确认状态
        page.client_storage.set("zen_eula_accepted", True)
        on_accepted()

    agree_checkbox.on_change = _on_agree_change
    enter_btn.on_click = _on_enter

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Row([
            ft.Icon(ft.icons.GAVEL_ROUNDED, color="#009688"),
            ft.Text("使用条款与免责声明", weight=ft.FontWeight.BOLD),
        ]),
        content=ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Text(_EULA_TEXT, size=13, selectable=True),
                    height=320,
                    border=ft.border.all(1, ft.colors.OUTLINE),
                    border_radius=8,
                    padding=15,
                ),
                ft.Container(height=10),
                agree_checkbox,
            ], tight=True),
            width=500,
        ),
        actions=[enter_btn],
        actions_alignment=ft.MainAxisAlignment.CENTER,
    )
    page.overlay.append(dlg)
    dlg.open = True
    page.update()
