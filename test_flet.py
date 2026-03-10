
import flet as ft
def main(page: ft.Page):
    tile = ft.Container(
        content=ft.Column([
            ft.Icon(ft.icons.MEMORY, color="#E67E22", size=24),
            ft.Text("虚拟内存", size=13, weight=ft.FontWeight.BOLD),
            ft.Text("转移或缩减", size=11, color="#E67E22")
        ]),
        padding=15, bgcolor=ft.colors.with_opacity(0.03, "onSurface"), border_radius=10,
        border=ft.border.all(1, ft.colors.with_opacity(0.2, "tertiary")), ink=True,
        tooltip="说明文本...",
        animate=ft.animation.Animation(300, "decelerate")
    )
    page.add(tile)
    print("Success rendering tile")
ft.app(target=main)
