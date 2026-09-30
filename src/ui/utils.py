"""UI 层共享工具与常量。

收口此前散落在多个视图中的重复实现（字节数格式化、品牌渐变），
统一行为口径，避免同一数值在不同页面显示不一致。
"""
import flet as ft

# 品牌主渐变色对（统一收口，替换散落各视图的硬编码色值）
BRAND_GRADIENT_COLORS = ["#00B894", "#00C2FF"]


def brand_gradient() -> ft.LinearGradient:
    """品牌渐变对象工厂（各视图按钮/磁贴统一调用）"""
    return ft.LinearGradient(
        begin=ft.alignment.top_left,
        end=ft.alignment.bottom_right,
        colors=BRAND_GRADIENT_COLORS,
    )


def fmt_size(size_bytes) -> str:
    """全应用统一的字节数格式化（KB 起保留一位小数，支持 TB/PB）。

    注意：0 值的"未检测到数据"等业务化文案由调用方特判，
    本函数只负责纯格式化。
    """
    try:
        n = float(size_bytes or 0)
    except (TypeError, ValueError):
        n = 0.0
    if n < 0:
        n = 0.0
    for unit, bound in (("PB", 1024 ** 5), ("TB", 1024 ** 4), ("GB", 1024 ** 3), ("MB", 1024 ** 2), ("KB", 1024)):
        if n >= bound:
            return f"{n / bound:.1f} {unit}"
    return f"{int(n)} B"
