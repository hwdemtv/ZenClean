import flet as ft
from collections import defaultdict
from config.settings import (
    COLOR_ZEN_PRIMARY, COLOR_ZEN_GOLD, 
    COLOR_ZEN_DANGER, COLOR_ZEN_TEXT_MAIN, COLOR_ZEN_TEXT_DIM, COLOR_ZEN_DIVIDER
)
from ui.components.file_list_item import FileListItem
from ui.components.dialogs import show_confirm_clean_dialog, show_empty_recycle_bin_dialog

# 分类ID → 中文标签 + 图标
_CATEGORY_META: dict[str, tuple[str, str]] = {
    "system_temp":      ("系统临时文件",   ft.icons.DELETE_SWEEP),
    "browser_cache":    ("浏览器缓存",     ft.icons.LANGUAGE),
    "app_cache":        ("应用缓存",       ft.icons.APPS),
    "dev_cache":        ("开发工具缓存",   ft.icons.CODE),
    "dev_build_cache":  ("构建产物缓存",   ft.icons.BUILD),
    "social_cache":     ("社交软件缓存",   ft.icons.CHAT),
    "social_media":     ("社交媒体文件",   ft.icons.PERM_MEDIA),
    "recycle_bin":      ("回收站",         ft.icons.RESTORE_FROM_TRASH),
    "windows_update":   ("Windows 更新缓存", ft.icons.SYSTEM_UPDATE),
    "system_logs":      ("系统日志",       ft.icons.RECEIPT_LONG),
    "downloads":        ("系统下载文件夹", ft.icons.DOWNLOAD),
    "protected":        ("系统保护文件",   ft.icons.SHIELD),
    "unknown":          ("其他文件",       ft.icons.HELP_OUTLINE),
}

MAX_ITEMS_PER_GROUP = 10  # 每个分组默认展示的文件条目数

# 分类配色方案
_CHART_COLORS = [
    "#E74C3C", "#3498DB", "#2ECC71", "#F39C12", "#9B59B6",
    "#1ABC9C", "#E67E22", "#34495E", "#16A085", "#C0392B"
]

def _build_category_chart(groups: dict[str, list[dict]]) -> ft.Container:
    """构建分类分布饼图及图示图例"""
    if not groups:
        return ft.Container()

    # 计算每个分类的大小
    cat_sizes = []
    for cat, cat_nodes in groups.items():
        size = sum(n.get("size_bytes", 0) for n in cat_nodes)
        if size > 0:
            label, _ = _CATEGORY_META.get(cat, (cat, ft.icons.FOLDER))
            cat_sizes.append((cat, label, size))

    if not cat_sizes:
        return ft.Container()

    # 按大小排序
    cat_sizes.sort(key=lambda x: x[2], reverse=True)

    # 只取前6个，其余合并为"其他"
    main_cats = cat_sizes[:6]
    other_size = sum(x[2] for x in cat_sizes[6:]) if len(cat_sizes) > 6 else 0

    total_size = sum(x[2] for x in cat_sizes)

    # 构建饼图sections与图例行
    sections = []
    legend_items = []
    
    for i, (cat, label, size) in enumerate(main_cats):
        value_gb = size / (1024 ** 3)
        color = _CHART_COLORS[i % len(_CHART_COLORS)]
        
        # 移除 title，防止在饼图上重叠，只靠 Hover
        sections.append(
            ft.PieChartSection(
                value=max(value_gb, 0.05),
                color=color,
                radius=14,
                title=" ", # 必须传字符串，传空串
            )
        )
        # 添加定宽图例，方便在 wrap 时形成网格
        legend_items.append(
            ft.Container(
                content=ft.Row([
                    ft.Container(bgcolor=color, width=10, height=10, border_radius=2),
                    ft.Text(f"{label} ({_fmt_size(size)})", size=11, color=COLOR_ZEN_TEXT_DIM, selectable=True)
                ], spacing=6),
                width=140
            )
        )

    if other_size > 0:
        other_gb = other_size / (1024 ** 3)
        color = "#95A5A6"
        sections.append(
            ft.PieChartSection(
                value=max(other_gb, 0.05),
                color=color,
                radius=14,
                title=" "
            )
        )
        legend_items.append(
            ft.Container(
                content=ft.Row([
                    ft.Container(bgcolor=color, width=10, height=10, border_radius=2),
                    ft.Text(f"其他文件 ({_fmt_size(other_size)})", size=11, color=COLOR_ZEN_TEXT_DIM, selectable=True)
                ], spacing=6),
                width=140
            )
        )

    # 构建饼图组件 (适当缩小避居占位过大)
    chart = ft.PieChart(
        sections=sections,
        sections_space=3,
        center_space_radius=40,
    )

    # 统计摘要 (标题)
    summary_title = ft.Column([
        ft.Text("清理项分布", size=15, weight=ft.FontWeight.BOLD, color=COLOR_ZEN_TEXT_MAIN),
        ft.Text(f"共发现 {sum(len(v) for v in groups.values())} 项 • 总体积 {_fmt_size(total_size)}", size=12, color=COLOR_ZEN_TEXT_DIM),
    ], spacing=2)

    # 紧凑型：左侧小饼图 + 右侧紧凑图例
    return ft.Container(
        content=ft.Row([
            # 左侧紧凑饼图
            ft.Container(content=chart, alignment=ft.alignment.center, width=100, height=100),
            # 右侧紧凑图例 (更小的wrap布局)
            ft.Container(
                content=ft.Column(
                    [
                        summary_title,
                        ft.Container(height=4),
                        ft.Row(legend_items, wrap=True, spacing=6, run_spacing=4)
                    ],
                    spacing=0,
                    alignment=ft.MainAxisAlignment.START
                ),
                padding=ft.padding.only(left=15),
                expand=True
            ),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=10,
        border_radius=8,
        bgcolor=ft.colors.with_opacity(0.02, ft.colors.SURFACE_VARIANT),
        margin=ft.margin.only(bottom=6)
    )

def _fmt_size(size_bytes: int) -> str:
    """将字节数格式化为人类可读字符串。"""
    if size_bytes >= 1024 ** 3:
        return f"{size_bytes / 1024 ** 3:.2f} GB"
    if size_bytes >= 1024 ** 2:
        return f"{size_bytes / 1024 ** 2:.1f} MB"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.0f} KB"
    return f"{size_bytes} B"

class ResultView(ft.Column):
    def __init__(self, app):
        super().__init__(expand=True)
        self.app = app
        self._total_size_bytes = 0
        self.is_confirm_mode = False  # 是否处于“确认清理阶段”
        self._expanded_cats: dict[str, int] = {}  # 分组 category → 当前显示条数上限
        self._expanded_tile_keys: set[str] = set()  # 记录当前展开的分组 ID
        self._chart_container = ft.Container(visible=False)  # 饼图容器
        self._file_items = {}  # 路径 -> FileListItem 实例，用于异步刷新

        self.lbl_total_size = ft.Text(
            "待清理: 0.00 GB",
            size=20,
            color=COLOR_ZEN_DANGER,
            weight=ft.FontWeight.BOLD,
        )

        header = ft.Row(
            [
                ft.Row([
                    ft.IconButton(
                        ft.icons.ARROW_BACK,
                        on_click=lambda _: self.app.navigate_to("/scan"),
                    ),
                    ft.Text("扫描结果揭晓", size=24, weight=ft.FontWeight.BOLD, color=COLOR_ZEN_TEXT_MAIN),
                ]),
                self.lbl_total_size,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        self.btn_reset = ft.TextButton(
            "取消/重置",
            icon=ft.icons.REFRESH,
            visible=False,
            style=ft.ButtonStyle(color=COLOR_ZEN_TEXT_DIM),
            on_click=self._reset_selection,
        )

        # ── 极光增强型一键清理按钮 ──
        self._btn_clean_icon = ft.Icon(ft.icons.BACKSPACE_ROUNDED, color="white")
        self._btn_clean_text = ft.Text(
            "智能体检一键清理" if app.is_activated else "🔑 VIP专享: 一键智能清除",
            color="white", weight=ft.FontWeight.BOLD
        )

        self.btn_clean = ft.Container(
            content=ft.Row([self._btn_clean_icon, self._btn_clean_text], alignment=ft.MainAxisAlignment.CENTER),
            height=50,
            expand=True,
            border_radius=10,
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=["#00B894", "#00C2FF"] if app.is_activated else ["#454545", "#333333"]
            ),
            border=ft.border.all(1, ft.colors.with_opacity(0.1, "onSurface")),
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=15, color=ft.colors.with_opacity(0.2, "#00B894") if app.is_activated else ft.colors.TRANSPARENT),
            ink=True if app.is_activated else False,
            on_click=self._on_main_button_click if app.is_activated else None,
            opacity=1.0 if app.is_activated else 0.6
        )

        # 分组面板容器 (从 ListView 改为带滚动条的 Column，解决 ExpansionTile 与虚拟化滚动条的高度计算冲突，告别底部切边/遮挡)
        # 此处使用 expand=True，它会尽可能霸占父级(ResultView也是一个expand=True的Column)剩下的所有高度空间
        self.groups_col = ft.Column(expand=True, spacing=4, scroll=ft.ScrollMode.AUTO)
        
        # 进度反馈条 (清理过程专属)
        self.clean_progress = ft.ProgressBar(width=None, value=0, color=COLOR_ZEN_PRIMARY, visible=False)

        # 底部操作栏（不再放置在一整个可滚动的长页面底部，而是作为页脚固定在 ResultView 的最后)
        self.bottom_bar = ft.Row([self.btn_reset, self.btn_clean])

        self.controls = [header, self._chart_container, self.groups_col, self.clean_progress, self.bottom_bar]
        self._build_data()  # 初始构建

    # ── 数据处理与 UI 渲染 ──────────────────────────────────────────────────

    def _update_category_chart(self, groups: dict[str, list[dict]]):
        """更新分类分布饼图"""
        if not groups:
            self._chart_container.visible = False
            return

        # 计算总节点数
        total_nodes = sum(len(v) for v in groups.values())
        if total_nodes < 3:  # 数据太少不显示图表
            self._chart_container.visible = False
            return

        self._chart_container.content = _build_category_chart(groups)
        self._chart_container.visible = True

    def _build_data(self):
        nodes = getattr(self.app, "scan_nodes", [])
        self.groups_col.controls.clear()
        self._file_items.clear()  # 清除旧的实例追踪
        self._total_size_bytes = 0

        # 计算分类统计数据用于图表
        groups: dict[str, list[dict]] = defaultdict(list)
        for node in nodes:
            cat = node.get("category", "unknown")
            groups[cat].append(node)

        # 如果有数据，显示分类分布饼图
        if nodes:
            self._update_category_chart(groups)

        if not nodes:
            self.groups_col.controls.append(
                ft.Container(
                    content=ft.Text("未发现任何可清理项", color=COLOR_ZEN_PRIMARY),
                    alignment=ft.alignment.center,
                    padding=20,
                )
            )
            self.lbl_total_size.value = "待清理: 0.00 GB"
            return

        # 获取当前勾选的总统计
        checked_nodes = [n for n in nodes if n.get("is_checked", False)]
        self._total_size_bytes = sum(n.get("size_bytes", 0) for n in checked_nodes)

        # 按 category 分组
        groups: dict[str, list[dict]] = defaultdict(list)
        for node in nodes:
            cat = node.get("category", "unknown")
            groups[cat].append(node)

        # 按组内总大小降序排列
        sorted_cats = sorted(
            groups.keys(),
            key=lambda c: sum(n.get("size_bytes", 0) for n in groups[c]),
            reverse=True,
        )

        for cat in sorted_cats:
            cat_nodes = groups[cat]
            cat_label, cat_icon = _CATEGORY_META.get(cat, (cat, ft.icons.FOLDER))
            
            # 分组统计
            total_size = sum(n.get("size_bytes", 0) for n in cat_nodes)
            checked_in_cat = [n for n in cat_nodes if n.get("is_checked", False)]
            checked_size = sum(n.get("size_bytes", 0) for n in checked_in_cat)

            # 确定分组级的 checkbox 状态 (三态)
            cat_valid_nodes = [n for n in cat_nodes if not n.get("is_whitelisted")]
            if len(cat_valid_nodes) == 0:
                group_check_state = False
            elif checked_size == total_size and total_size > 0:
                group_check_state = True
            elif checked_size == 0:
                group_check_state = False
            else:
                group_check_state = None  # 部分选中 (tristate)

            # 更新 UI 中的分组标题
            title_row = ft.Row([
                ft.Row([
                    ft.Icon(cat_icon, color=COLOR_ZEN_PRIMARY, size=20),
                    ft.Text(f"{cat_label}", weight=ft.FontWeight.BOLD, size=14, color=COLOR_ZEN_TEXT_MAIN),
                ], expand=True),
                ft.Row([
                    ft.Checkbox(
                        value=group_check_state,
                        tristate=True,
                        tooltip="全选/取消本组",
                        fill_color=COLOR_ZEN_PRIMARY,
                        on_change=lambda e, ns=cat_nodes: self._select_all(ns, e.control.value),
                    ),
                    ft.VerticalDivider(width=1, color=COLOR_ZEN_DIVIDER),
                    ft.Container(
                        content=ft.Text(f"{len(checked_in_cat)}/{len(cat_nodes)} 项", size=12, color=COLOR_ZEN_TEXT_DIM),
                        width=90,
                        alignment=ft.alignment.center_right,
                    ),
                    ft.Container(
                        content=ft.Text(
                            f"{_fmt_size(checked_size)} / {_fmt_size(total_size)}",
                            size=13, weight=ft.FontWeight.W_600, color=COLOR_ZEN_GOLD,
                        ),
                        width=140,
                        alignment=ft.alignment.center_right,
                    ),
                ], alignment=ft.MainAxisAlignment.END, spacing=10),
            ])

            # 按文件大小大到小排序，确保最大的文件显示在前面
            cat_nodes.sort(key=lambda n: n.get("size_bytes", 0), reverse=True)

            # 构建组内小列表
            show_limit = self._expanded_cats.get(cat, MAX_ITEMS_PER_GROUP)
            total_in_cat = len(cat_nodes)
            file_controls = []

            for i, node in enumerate(cat_nodes):
                # 到达当前上限，停止渲染
                if i >= show_limit:
                    break

                # 分批加载模式下，在原默认截断位置插入中途收起按钮
                if i == MAX_ITEMS_PER_GROUP and show_limit > MAX_ITEMS_PER_GROUP:
                    file_controls.append(ft.Container(
                        content=ft.TextButton(
                            f"🔼 收起本组（仅显示前 {MAX_ITEMS_PER_GROUP} 个）",
                            on_click=lambda _, c=cat: self._collapse_group(c),
                        ),
                        padding=ft.padding.only(left=30, top=5, bottom=5),
                        bgcolor="surfaceVariant",
                        border_radius=5,
                    ))

                # 行内复选框同步
                def _on_row_check(e, current_node):
                    current_node["is_checked"] = e.control.value
                    self._update_ui_stats()

                size_str = _fmt_size(node.get("size_bytes", 0))
                item = FileListItem(node, _on_row_check, size_str)
                file_controls.append(item)
                
                # 记录实例，以便后续异步刷新 (这里的 key 使用 sanitized_path 对应的真实 path)
                self._file_items[node["path"]] = item

            # ── 底部操作栏（合并“加载更多”与“收起”为一行） ──────────────
            remaining = total_in_cat - show_limit
            bottom_btns = []

            if remaining > 0:
                # 还有未显示的文件 -> 添加“加载更多”
                if remaining <= MAX_ITEMS_PER_GROUP:
                    load_text = f"📂 显示剩余 {remaining} 个文件"
                else:
                    load_text = f"📂 加载更多（还有 {remaining} 个）"
                bottom_btns.append(
                    ft.TextButton(load_text, on_click=lambda _, c=cat: self._expand_group(c))
                )

            if show_limit > MAX_ITEMS_PER_GROUP:
                # 已经加载过更多 -> 添加“收起”
                bottom_btns.append(
                    ft.TextButton(
                        f"🔼 收起（仅前 {MAX_ITEMS_PER_GROUP} 个）",
                        on_click=lambda _, c=cat: self._collapse_group(c),
                    )
                )

            if bottom_btns:
                file_controls.append(ft.Container(
                    content=ft.Row(bottom_btns, alignment=ft.MainAxisAlignment.CENTER, spacing=20),
                    padding=ft.padding.only(top=5, bottom=5),
                ))

            def _on_tile_change(e, k=cat):
                if e.data == "true":
                    self._expanded_tile_keys.add(k)
                else:
                    self._expanded_tile_keys.discard(k)

            self.groups_col.controls.append(
                ft.ExpansionTile(
                    title=title_row,
                    controls=file_controls,
                    initially_expanded=cat in self._expanded_tile_keys,
                    on_change=_on_tile_change,
                    bgcolor="surface",
                    collapsed_bgcolor="surfaceVariant",
                    shape=ft.RoundedRectangleBorder(radius=8),
                )
            )
            # 增加分组间的间距
            self.groups_col.controls.append(ft.Container(height=2))

        # (已移除底部的 80px 隐形垫片，因为现在按钮区脱离了列表本身，成了绝对锁定的页脚)
        self._update_btn_and_total_label()

    def _load_data(self):
        """刷新分组数据并更新 UI（仅在已挂载后使用）"""
        self._build_data()
        self.update()

    def on_ai_batch_done(self, results_map: dict):
        """AI 异步结果返回时的局部刷新处理器"""
        # results_map: { path: { risk_level, ai_advice, ... } }
        updated_any = False
        for path, result in results_map.items():
            if path in self._file_items:
                self._file_items[path].update_ai_result(result)
                updated_any = True
        
        # 如果有任何更新，可能影响到统计（如风险等级改变导致“一键清理”逻辑变化）
        if updated_any:
            # 这里不调用 _load_data (太重)，只更新统计数值
            self._update_btn_and_total_label()
            self.update()

    def _update_ui_stats(self):
        """局部或全量刷新，更新统计标签和按钮文案"""
        nodes = getattr(self.app, "scan_nodes", [])
        checked_nodes = [n for n in nodes if n.get("is_checked", False)]
        self._total_size_bytes = sum(n.get("size_bytes", 0) for n in checked_nodes)
        
        # 为了让分组标题中的 (x/y) 实时变动，目前最简单且保证 UI 一致性的方法是触发部分或全部重绘
        # 考虑到性能，我们可以改为只通过 refs 更新标题 Text，但为了逻辑清晰先全量刷新
        self._load_data()

    def _update_btn_and_total_label(self):
        """更新底部按钮状态和总大小标签"""
        self.lbl_total_size.value = f"待清理: {_fmt_size(self._total_size_bytes)}"
        
        if not self.is_confirm_mode:
            self._btn_clean_text.value = "智能体检一键清理"
            self.btn_clean.gradient = ft.LinearGradient(
                begin=ft.alignment.top_left, end=ft.alignment.bottom_right,
                colors=["#00B894", "#00C2FF"]
            )
            self._btn_clean_icon.name = ft.icons.AUTO_FIX_HIGH
            self.btn_reset.visible = False
        else:
            checked_count = sum(1 for n in self.app.scan_nodes if n.get("is_checked", False))
            self._btn_clean_text.value = f"确认清理 {checked_count} 项 ({_fmt_size(self._total_size_bytes)})"
            self.btn_clean.gradient = ft.LinearGradient(
                begin=ft.alignment.top_left, end=ft.alignment.bottom_right,
                colors=["#EB4D4B", "#C0392B"]
            )
            self._btn_clean_icon.name = ft.icons.DELETE_FOREVER
            self.btn_reset.visible = True

    # ── 交互逻辑 ────────────────────────────────────────────────────────────

    def _on_main_button_click(self, e):
        """主按钮点击：第一阶段切换确认模式并预选；第二阶段执行清理。"""
        if not self.is_confirm_mode:
            # 模式 1 -> 模式 2：AI 预选
            for node in self.app.scan_nodes:
                if node.get("risk_level") == "LOW" and not node.get("is_whitelisted"):
                    node["is_checked"] = True
            self.is_confirm_mode = True
            self._load_data()
        else:
            # 模式 2 -> 执行：弹窗二次确认
            self._confirm_final_clean()

    def _reset_selection(self, e):
        """重置勾选并退回浏览模式"""
        for node in self.app.scan_nodes:
            node["is_checked"] = False
        self.is_confirm_mode = False
        self._expanded_cats.clear()
        self._load_data()

    def _select_all(self, nodes_subset: list[dict], value: bool):
        """分类级别的全选/反选"""
        for n in nodes_subset:
            if not n.get("is_whitelisted"):
                n["is_checked"] = value
        self._load_data()

    def _expand_group(self, category: str):
        """分批加载更多文件（每次 +15）"""
        current = self._expanded_cats.get(category, MAX_ITEMS_PER_GROUP)
        self._expanded_cats[category] = current + MAX_ITEMS_PER_GROUP
        self._load_data()

    def _collapse_group(self, category: str):
        """收起指定分组，恢复为默认显示数量"""
        self._expanded_cats.pop(category, None)
        self._load_data()

    def _confirm_final_clean(self):
        """最终清理的确认对话框"""
        nodes = [n for n in self.app.scan_nodes if n.get("is_checked", False)]
        if not nodes: return

        size_str = _fmt_size(self._total_size_bytes)
        def _on_confirm():
            self._trigger_clean(nodes)
            
        show_confirm_clean_dialog(self.app.page, size_str, len(nodes), _on_confirm)

    def _trigger_clean(self, nodes_to_clean):
        """点击确认清理按钮后，立即更新 UI 并派发异步任务"""
        # 禁用操作，防止二次点击
        self.btn_clean.disabled = True
        self.btn_reset.disabled = True
        
        # 切换按钮外观为加载态
        if getattr(self.btn_clean.content, "controls", None):
            self.btn_clean.content.controls[0].name = ft.icons.HOURGLASS_EMPTY
            self.btn_clean.content.controls[1].value = "正在初始化粉碎环境..."
            
        self.clean_progress.visible = True
        self.clean_progress.value = 0
        self.app.page.update()
        
        # 抛出异步清理任务
        self.app.page.run_task(self._async_run_clean, nodes_to_clean)

    async def _async_run_clean(self, nodes_to_clean):
        """在独立线程池中执行耗时的物理清理，并实时驱动 UI 动效"""
        import asyncio
        import time
        from core.cleaner import clean

        total_nodes = len(nodes_to_clean)
        processed_count = 0
        last_update_ts = 0

        try:
            def _on_progress(path, action, total_freed):
                nonlocal processed_count, last_update_ts
                processed_count += 1
                
                # 目标值：总大小 - 已释放大小 (total_freed 是累加字节数)
                target_size = max(0, float(self._total_size_bytes - total_freed))
                
                # 节流更新 UI
                now = time.time()
                if now - last_update_ts > 0.03 or processed_count == total_nodes:
                    if self.app.page:
                        # 进度条
                        self.clean_progress.value = processed_count / total_nodes
                        # 按钮文案
                        if getattr(self.btn_clean.content, "controls", None):
                            self.btn_clean.content.controls[1].value = f"正在物理粉碎: {processed_count} / {total_nodes}"
                        # 数字倒吸
                        self.lbl_total_size.value = f"待清理: {_fmt_size(int(target_size))}"
                        self.app.page.update()
                    last_update_ts = now

            # 执行核心清理
            result = await asyncio.to_thread(clean, nodes_to_clean, on_progress=_on_progress, force_high=True)

            # ── 清理完成后显示圆满状态 ──────────────────────────────────────
            if self.app.page:
                self.lbl_total_size.value = "待清理: 0 B"
                if getattr(self.btn_clean.content, "controls", None):
                    self.btn_clean.content.controls[0].name = ft.icons.CHECK_CIRCLE
                    self.btn_clean.content.controls[1].value = "清理圆满完成"
                
                self.btn_clean.gradient = ft.LinearGradient(
                    begin=ft.alignment.top_left, end=ft.alignment.bottom_right,
                    colors=["#27AE60", "#2ECC71"]
                )
                self.clean_progress.visible = False
                
                # 汇总通知
                msg = f"清理完毕！成功释放 {result.deleted} 项，隔离 {result.trashed} 项。"
                if result.freed_bytes > 0:
                    msg += f" 共腾出空间 {_fmt_size(result.freed_bytes)}。"
                
                self.app.page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=ft.colors.GREEN_800, duration=3000)
                self.app.page.snack_bar.open = True
                
                # 数据重置
                self.app.scan_nodes = []
                
                # 状态落定
                self.app.page.update()

                # 延迟跳转或弹窗，让用户能看清结果
                await asyncio.sleep(0.8)

                if result.trashed > 0:
                    self._prompt_empty_recycle_bin()
                else:
                    self.app.navigate_to("/scan")
                
                self.app.page.update()

        except Exception as e:
            from core.logger import logger
            logger.error(f"UI_CLEAN_TASK_ERROR: {e}", exc_info=True)
            if self.app.page:
                self.btn_clean.disabled = False
                self.btn_reset.disabled = False
                self.app.page.snack_bar = ft.SnackBar(ft.Text(f"清理过程出现中断: {e}"), bgcolor="error", open=True)
                self.app.page.update()

    def _prompt_empty_recycle_bin(self):
        def _on_confirm():
            self.app.navigate_to("/quarantine")

        def _on_cancel():
            self.app.navigate_to("/scan")

        show_empty_recycle_bin_dialog(self.app.page, _on_confirm, _on_cancel)

    # (保留最后的空白便于以后修改)

    # (保留最后的空白便于以后修改)

