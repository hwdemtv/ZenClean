
import flet as ft

# ── ZenClean 核心色彩定义 ──────────────────────────────────────────────
COLOR_ZEN_BG = "#0F1115"
COLOR_ZEN_SURFACE = "#171A21"
COLOR_ZEN_PRIMARY = "#009688"
COLOR_ZEN_GOLD = "#D4AF37"
COLOR_ZEN_DANGER = "#E74C3C"
COLOR_ZEN_DIVIDER = "#11FFFFFF"
COLOR_ZEN_TEXT_MAIN = "#E6EAF0"
COLOR_ZEN_TEXT_DIM = "#8B93A6"

def zen_capsule_style(color=COLOR_ZEN_PRIMARY, side="left"):
    """
    HUD 翼板样式生成器 (左右护法模式)
    """
    sides = {
        "left": {
            "border": ft.border.only(left=ft.BorderSide(2, color)),
            "radius": ft.border_radius.only(top_left=15, bottom_left=15, top_right=5, bottom_right=5)
        },
        "right": {
            "border": ft.border.only(right=ft.BorderSide(2, color)),
            "radius": ft.border_radius.only(top_right=15, bottom_right=15, top_left=5, bottom_left=5)
        }
    }
    s = sides.get(side, sides["left"])
    return {
        "bgcolor": ft.colors.with_opacity(0.05, color),
        "border": s["border"],
        "border_radius": s["radius"],
        "padding": ft.padding.symmetric(vertical=12),
        "width": 100,
        "height": 85
    }

def zen_card_style():
    """
    标准功能磁贴样式
    """
    return {
        "bgcolor": "#15181E",
        "border": ft.border.all(1, "#2C3440"),
        "border_radius": 16,
        "padding": 15
    }

# 使用示例
if __name__ == "__main__":
    def main(page: ft.Page):
        page.bgcolor = COLOR_ZEN_BG
        
        # 左右护法示例
        left_wing = ft.Container(
            content=ft.Column([
                ft.Icon(ft.icons.SHIELD, color=COLOR_ZEN_PRIMARY),
                ft.Text("100%", color=COLOR_ZEN_PRIMARY, font_family="Consolas"),
                ft.Text("系统健康", color=COLOR_ZEN_TEXT_DIM, size=9)
            ], horizontal_alignment="center", spacing=0),
            **zen_capsule_style(side="left")
        )
        
        page.add(ft.Row([left_wing], alignment="center"))
        page.update()

    ft.app(target=main)
