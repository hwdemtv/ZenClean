import flet as ft
from collections import defaultdict


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

        self.lbl_total_size = ft.Text(
            "待清理: 0.00 GB",
            size=20,
            color=ft.colors.RED_400,
            weight=ft.FontWeight.BOLD,
        )

        header = ft.Row(
            [
                ft.Row([
                    ft.IconButton(
                        ft.icons.ARROW_BACK,
                        on_click=lambda _: self.app.navigate_to("/scan"),
                    ),
                    ft.Text("扫描结果揭晓", size=24, weight=ft.FontWeight.BOLD),
                ]),
                self.lbl_total_size,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        self.btn_reset = ft.TextButton(
            "取消/重置",
            icon=ft.icons.REFRESH,
            visible=False,
            on_click=self._reset_selection,
        )

        self.btn_clean = ft.ElevatedButton(
            "智能体检一键清理" if app.is_activated else "🔑 VIP专享: 一键智能清除",
            icon=ft.icons.BACKSPACE_ROUNDED,
            color="white",
            bgcolor=ft.colors.GREEN_700 if app.is_activated else ft.colors.GREY_800,
            disabled=not app.is_activated,
            height=50,
            expand=True,
            on_click=self._on_main_button_click,
        )

        # 分组面板容器
        self.groups_col = ft.ListView(expand=True, spacing=8)

        self.controls = [header, self.groups_col, ft.Row([self.btn_reset, self.btn_clean])]
        self._build_data()  # 初始构建（不调用 update）

    # ── 数据处理与 UI 渲染 ──────────────────────────────────────────────────

    def _build_data(self):
        """构建分组数据 UI（不调用 self.update，适用于 __init__ 期间）"""
        nodes = getattr(self.app, "scan_nodes", [])
        self.groups_col.controls.clear()
        self._total_size_bytes = 0

        if not nodes:
            self.groups_col.controls.append(
                ft.Container(
                    content=ft.Text("未发现任何可清理项", color=ft.colors.GREEN_400),
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
                    ft.Icon(cat_icon, color="#00D4AA", size=20),
                    ft.Text(f"{cat_label}", weight=ft.FontWeight.BOLD, size=14),
                ], expand=True), # 左侧：图标 + 文字（占据所有剩余空间并把右侧推挤）
                ft.Row([
                    # 右侧：全选框 + 统计信息
                    ft.Checkbox(
                        value=group_check_state,
                        tristate=True,
                        tooltip="全选/取消本组",
                        on_change=lambda e, ns=cat_nodes: self._select_all(ns, e.control.value),
                    ),
                    ft.VerticalDivider(width=1),
                    # 统计信息：文件数（已选/总计）
                    ft.Container(
                        content=ft.Text(f"{len(checked_in_cat)}/{len(cat_nodes)} 项", size=12, color=ft.colors.GREY_400),
                        width=90, # 固定宽度以保证左侧复选框对齐
                        alignment=ft.alignment.center_right,
                    ),
                    # 统计信息：大小（已选/总计）
                    ft.Container(
                        content=ft.Text(
                            f"{_fmt_size(checked_size)} / {_fmt_size(total_size)}",
                            size=13, weight=ft.FontWeight.W_600, color=ft.colors.ORANGE_400,
                        ),
                        width=140, # 给予固定宽度，让数值即使长度跳动，整体布局也保持对齐
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
                        bgcolor="#252525",
                        border_radius=5,
                    ))

                risk_color = ft.colors.GREEN_400
                if node["risk_level"] == "MEDIUM": risk_color = ft.colors.YELLOW_400
                elif node["risk_level"] == "HIGH": risk_color = ft.colors.RED_400

                # 行内复选框同步
                def _on_row_check(e, n=node):
                    n["is_checked"] = e.control.value
                    self._update_ui_stats()

                file_controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Checkbox(value=node["is_checked"], on_change=_on_row_check),
                            ft.Icon(ft.icons.CIRCLE, color=risk_color, size=10),
                            ft.Text(node["path"][-70:] if len(node["path"]) > 75 else node["path"],
                                    size=12, expand=True, font_family="Consolas"),
                            ft.Text(_fmt_size(node.get("size_bytes", 0)), size=12, color=ft.colors.GREY_500),
                        ]),
                        padding=ft.padding.only(left=10, right=10),
                        tooltip=node["ai_advice"],
                    )
                )

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

            self.groups_col.controls.append(
                ft.ExpansionTile(
                    title=title_row,
                    controls=file_controls,
                    initially_expanded=False,
                    bgcolor="#1A1A1A",
                    collapsed_bgcolor="#141414",
                    shape=ft.RoundedRectangleBorder(radius=8),
                )
            )
            # 增加分组间的间距
            self.groups_col.controls.append(ft.Container(height=4))

        self._update_btn_and_total_label()

    def _load_data(self):
        """刷新分组数据并更新 UI（仅在已挂载后使用）"""
        self._build_data()
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
            self.btn_clean.text = "智能体检一键清理"
            self.btn_clean.bgcolor = ft.colors.GREEN_700
            self.btn_clean.icon = ft.icons.AUTO_FIX_HIGH
            self.btn_reset.visible = False
        else:
            checked_count = sum(1 for n in self.app.scan_nodes if n.get("is_checked", False))
            self.btn_clean.text = f"确认清理 {checked_count} 项 ({_fmt_size(self._total_size_bytes)})"
            self.btn_clean.bgcolor = ft.colors.RED_700
            self.btn_clean.icon = ft.icons.DELETE_FOREVER
            self.btn_reset.visible = True

    # ── 交互逻辑 ────────────────────────────────────────────────────────────

    def _on_main_button_click(self, e):
        """主按钮点：第一阶段切换确认模式并预选；第二阶段执行清理。"""
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

        dlg = ft.AlertDialog(
            title=ft.Text("⚠️ 确认开始清理？"),
            content=ft.Text(f"系统即将清理 {len(nodes)} 个项，共计 {_fmt_size(self._total_size_bytes)}。\n\n当前为【模拟模式】，不会真正改动磁盘。"),
            actions=[
                ft.TextButton("我再想想", on_click=lambda _: self._close_dlg(dlg)),
                ft.ElevatedButton("开始清理", bgcolor=ft.colors.RED, color="white", on_click=lambda _: self._run_clean(dlg, len(nodes))),
            ]
        )
        self.app.page.overlay.append(dlg)
        dlg.open = True
        self.app.page.update()

    def _close_dlg(self, dlg):
        dlg.open = False
        self.app.page.update()

    def _run_clean(self, dlg, count):
        dlg.open = False
        self.btn_clean.disabled = True
        self.btn_clean.text = "正在处理中..."
        self.update()

        self.update()

        # 模拟清理成功
        # 未来：这里将调用 `from core.cleaner import clean` 并获取 trashed 数量
        has_trashed = True  # 模拟存在移入回收站的 MEDIUM/HIGH 文件

        self.app.page.snack_bar = ft.SnackBar(
            ft.Text(f"常规清理完毕！预计释放 {_fmt_size(self._total_size_bytes)} 空间。"), 
            bgcolor=ft.colors.GREEN_800
        )
        self.app.page.snack_bar.open = True
        self.app.scan_nodes = [] # 清空扫描数据
        self.app.page.update()

        if has_trashed:
            self._prompt_empty_recycle_bin()
        else:
            self.app.navigate_to("/scan")

    def _prompt_empty_recycle_bin(self):
        def _on_confirm(e):
            dlg.open = False
            self.app.page.update()
            
            from core.cleaner import empty_recycle_bin
            success = empty_recycle_bin()
            
            msg = "回收站已彻底清空！" if success else "清空回收站失败或已为空，请查看日志。"
            color = ft.colors.GREEN_800 if success else ft.colors.ORANGE_800
            
            self.app.page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=color)
            self.app.page.snack_bar.open = True
            
            self.app.navigate_to("/scan")

        def _on_cancel(e):
            dlg.open = False
            self.app.page.update()
            self.app.navigate_to("/scan")

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([ft.Icon(ft.icons.WARNING_AMBER_ROUNDED, color=ft.colors.RED_400), ft.Text("高能预警：清空回收站")]),
            content=ft.Text("部分争议文件（MEDIUM/HIGH级别）已移入系统回收站作为您的最后防线。\n\n是否立即【彻底清空系统回收站】斩草除根？\n警告：此操作不可逆转！"),
            actions=[
                ft.TextButton("先保留在回收站", on_click=_on_cancel),
                ft.ElevatedButton("彻底清空 (免责)", bgcolor=ft.colors.RED_700, color="white", on_click=_on_confirm),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.app.page.overlay.append(dlg)
        dlg.open = True
        self.app.page.update()

    # (保留最后的空白便于以后修改)

