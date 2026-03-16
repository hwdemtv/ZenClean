import threading
import flet as ft

from core.migration import get_shell_folders, SHELL_FOLDER_KEYS, _dir_size, restore_folder
from config.settings import COLOR_ZEN_PRIMARY, COLOR_ZEN_SURFACE


# 注册表键名 → 图标映射
_KEY_TO_ICON = {
    "Desktop":                                    ft.icons.DESKTOP_WINDOWS,
    "{374DE290-123F-4565-9164-39C4925E467B}":     ft.icons.DOWNLOAD,
    "Personal":                                   ft.icons.FOLDER_SPECIAL,
    "My Pictures":                                ft.icons.IMAGE,
    "My Video":                                   ft.icons.VIDEO_FILE,
    "My Music":                                   ft.icons.MUSIC_NOTE,
}


def _fmt_size(size_bytes: int) -> str:
    """将字节数格式化为人类可读字符串。"""
    if size_bytes >= 1024 ** 3:
        return f"{size_bytes / 1024 ** 3:.1f} GB"
    if size_bytes >= 1024 ** 2:
        return f"{size_bytes / 1024 ** 2:.1f} MB"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} B"


class MigrationView(ft.Column):
    def __init__(self, app):
        self.app = app

        # 加载状态提示（数据读取期间显示）
        self._loading = ft.Row(
            [
                ft.ProgressRing(width=18, height=18, stroke_width=2, color="primary"),
                ft.Text("正在读取系统文件夹信息...", color="onSurfaceVariant", size=13),
            ],
            spacing=10,
        )

        # 卡片列表容器（数据加载完成后填充）
        self._cards_col = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=0,
        )

        super().__init__(
            controls=[
                ft.Column([
                    ft.Text("系统文件夹无损搬家", size=24, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        "将桌面、下载等核心默认目录物理移动至其他盘符，根治 C 盘红线。",
                        color="onSurfaceVariant",
                    ),
                ]),
                ft.Divider(color="outlineVariant"),
                self._loading,
                self._cards_col,
            ],
            expand=True,
        )

        # 初始化 FilePicker，后续在 did_mount 挂载到 page
        self._current_migrate_key = None
        self._picker = ft.FilePicker(on_result=self._on_picker_result)

        # 在后台线程中计算目录大小（可能较慢），避免阻塞 UI
        threading.Thread(target=self._load_data, daemon=True).start()

    def did_mount(self):
        self.app.page.overlay.append(self._picker)
        self.app.page.update()

    def will_unmount(self):
        if self._picker in self.app.page.overlay:
            self.app.page.overlay.remove(self._picker)
            self.app.page.update()

    # ── 数据加载 ──────────────────────────────────────────────────────────────

    def _load_data(self) -> None:
        """后台线程：读注册表 + 计算各目录大小，完成后更新 UI。"""
        try:
            folders = get_shell_folders()   # 读注册表
        except Exception:
            folders = {}

        cards = []
        for key, label in SHELL_FOLDER_KEYS.items():
            path = folders.get(key)
            if path is None:
                continue

            # 计算目录大小（可能耗时，但在后台线程中执行）
            size_bytes = _dir_size(path) if path.exists() else 0
            icon = _KEY_TO_ICON.get(key, ft.icons.FOLDER)
            on_c = path.drive.upper() == "C:"

            cards.append(
                self._make_card(label, str(path), size_bytes, icon, on_c, key)
            )

        # 切回主线程更新控件
        try:
            self._loading.visible = False
            self._cards_col.controls = cards
            self.update()
        except Exception:
            pass   # 视图已被销毁（用户切换到其他页面），静默忽略

    # ── 卡片组件 ──────────────────────────────────────────────────────────────

    def _make_card(
        self,
        label: str,
        path: str,
        size_bytes: int,
        icon: str,
        on_c: bool,
        reg_key: str,
    ) -> ft.Container:
        """构建单个文件夹的迁移卡片。"""
        size_str = _fmt_size(size_bytes)

        # 设置核心数据展示色 (动态适配)
        path_color = "onSurfaceVariant"
        size_color = "onSurface" if on_c else "onSurfaceVariant"

        if on_c:
            action_btn = ft.Container(
                content=ft.Text("迁移至其他盘", color="white", weight=ft.FontWeight.W_600, size=13),
                padding=ft.padding.symmetric(horizontal=15, vertical=6),
                border_radius=4,
                gradient=ft.LinearGradient(
                    begin=ft.alignment.top_left,
                    end=ft.alignment.bottom_right,
                    colors=["#00B894", "#00C2FF"],
                ),
                border=ft.border.all(1, ft.colors.with_opacity(0.12, "onSurface")),
                shadow=ft.BoxShadow(spread_radius=1, blur_radius=10, color=ft.colors.with_opacity(0.15, "#00B894")),
                ink=True,
                on_click=lambda e, k=reg_key, p=path: self._on_migrate(e, k, p),
            )
        else:
            action_btn = ft.OutlinedButton(
                "还原回 C 盘",
                icon=ft.icons.UNDO,
                style=ft.ButtonStyle(
                    color={"hovered": "onPrimaryContainer", "": "onSurfaceVariant"},
                    side={"": ft.BorderSide(1, "outlineVariant")},
                    bgcolor={"hovered": "surfaceVariant", "": ft.colors.TRANSPARENT},
                ),
                on_click=lambda e, k=reg_key: self._on_restore(e, k),
            )

        def _on_hover(e):
            e.control.bgcolor = ft.colors.with_opacity(0.08, "onSurface") if e.data == "true" else "surface"
            e.control.update()

        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(icon, color="primary" if on_c else "onSurfaceVariant", size=28),
                    ft.Column(
                        [
                            ft.Text(label, weight=ft.FontWeight.BOLD),
                            ft.Text(path, size=12, color=path_color, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                        ],
                        expand=True,
                        spacing=2,
                    ),
                    ft.Row(
                        [
                            ft.Text(size_str, size=13, color=size_color, font_family="Consolas", weight=ft.FontWeight.BOLD if on_c else ft.FontWeight.NORMAL),
                            action_btn,
                        ],
                        alignment=ft.MainAxisAlignment.END,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=15,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=15,
            bgcolor="surface",
            border=ft.border.all(1, "outlineVariant"),
            border_radius=8,
            margin=ft.margin.only(bottom=10),
            on_hover=_on_hover,
        )

    # ── 迁移触发 ──────────────────────────────────────────────────────────────

    def _on_migrate(self, e, reg_key: str, current_path: str) -> None:
        """
        点击"迁移"按钮后弹出目录选择器，用户确认目标盘后执行迁移。
        """
        from core.logger import logger
        logger.info(f"迁移按钮被点击: key={reg_key}, path={current_path}")
        self._current_migrate_key = reg_key
        try:
            self._picker.get_directory_path(dialog_title="选择目标目录（请选择非 C 盘）")
        except Exception as exc:
            logger.error(f"FilePicker 启动失败: {exc}", exc_info=True)
            self.app.page.snack_bar = ft.SnackBar(
                ft.Text(f"无法打开目录选择器：{exc}"),
                bgcolor=ft.colors.RED_900,
            )
            self.app.page.snack_bar.open = True
            self.app.page.update()

    def _on_picker_result(self, ev: ft.FilePickerResultEvent):
        from core.logger import logger
        if not ev.path:
            logger.info("用户取消了目录选择")
            self._current_migrate_key = None
            return

        if not getattr(self, "_current_migrate_key", None):
            return

        reg_key = self._current_migrate_key
        self._current_migrate_key = None

        import threading
        from pathlib import Path
        from core.migration import MigrationPlan, SHELL_FOLDER_KEYS

        dst_base = Path(ev.path)
        label = SHELL_FOLDER_KEYS.get(reg_key, reg_key)
        logger.info(f"用户选择目标目录: {dst_base}")

        # 立即显示进度提示
        self.app.page.snack_bar = ft.SnackBar(
            ft.Row([
                ft.ProgressRing(width=16, height=16, stroke_width=2, color="white"),
                ft.Text(f"正在迁移「{label}」...", color="white"),
            ], spacing=10),
            bgcolor=ft.colors.BLUE_700,
            duration=60000,
        )
        self.app.page.snack_bar.open = True
        self.app.page.update()

        def _run():
            try:
                plan = MigrationPlan([reg_key], dst_base)
                report = plan.preflight()
                if not report.ok:
                    logger.warning(f"前置检查未通过: {report.issues}")
                    self.app.page.snack_bar = ft.SnackBar(
                        ft.Text("前置检查未通过：" + "；".join(report.issues)),
                        bgcolor=ft.colors.RED_900,
                    )
                    self.app.page.snack_bar.open = True
                    self.app.page.update()
                    return
                logger.info(f"前置检查通过，开始迁移 ({report.total_size_gb:.2f} GB)")
                plan.execute()
                logger.info(f"迁移完成: {label}")
                self.app.page.snack_bar = ft.SnackBar(
                    ft.Text(f"搬家完成！已释放约 {_fmt_size(report.total_size_bytes)}"),
                    bgcolor=ft.colors.GREEN_800,
                )
                self.app.page.snack_bar.open = True
                self.app.page.update()
                # 刷新本视图数据
                self._cards_col.controls = []
                self._loading.visible = True
                self.app.page.update()
                threading.Thread(target=self._load_data, daemon=True).start()
            except Exception as exc:
                logger.error(f"迁移出错: {exc}", exc_info=True)
                self.app.page.snack_bar = ft.SnackBar(
                    ft.Text(f"迁移出错：{exc}"),
                    bgcolor=ft.colors.RED_900,
                )
                self.app.page.snack_bar.open = True
                self.app.page.update()

        threading.Thread(target=_run, daemon=True).start()

    # ── 还原触发 ──────────────────────────────────────────────────────────────

    def _on_restore(self, e, reg_key: str) -> None:
        """点击"还原回 C 盘"按钮后弹出确认弹窗，确认后执行还原。"""
        from core.migration import SHELL_FOLDER_KEYS, get_default_c_path

        label = SHELL_FOLDER_KEYS.get(reg_key, reg_key)
        try:
            default_path = get_default_c_path(reg_key)
        except ValueError:
            default_path = "C 盘默认位置"

        def _do_restore(_):
            dlg.open = False
            self.app.page.update()

            # 立即显示正在还原的状态
            self.app.page.snack_bar = ft.SnackBar(
                ft.Row([
                    ft.ProgressRing(width=16, height=16, stroke_width=2, color="white"),
                    ft.Text(f"正在还原「{label}」到 C 盘...", color="white"),
                ], spacing=10),
                bgcolor=ft.colors.BLUE_700,
                duration=30000,  # 长时显示
            )
            self.app.page.snack_bar.open = True
            self.app.page.update()

            def _run():
                from core.logger import logger
                try:
                    logger.info(f"开始还原 [{label}] (key={reg_key})")
                    msg = restore_folder(reg_key)
                    logger.info(f"还原结果: {msg}")
                    self.app.page.snack_bar = ft.SnackBar(
                        ft.Text(msg), bgcolor=ft.colors.GREEN_800,
                    )
                    self.app.page.snack_bar.open = True
                    self.app.page.update()
                    # 刷新视图
                    self._cards_col.controls = []
                    self._loading.visible = True
                    self.update()
                    threading.Thread(target=self._load_data, daemon=True).start()
                except Exception as exc:
                    logger.error(f"还原失败 [{label}]: {exc}", exc_info=True)
                    self.app.page.snack_bar = ft.SnackBar(
                        ft.Text(f"还原失败：{exc}"), bgcolor=ft.colors.RED_900,
                    )
                    self.app.page.snack_bar.open = True
                    self.app.page.update()

            threading.Thread(target=_run, daemon=True).start()

        def _cancel(_):
            dlg.open = False
            self.app.page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"确认还原「{label}」？"),
            content=ft.Text(
                f"将把「{label}」文件夹从当前位置移动回：\n"
                f"{default_path}\n\n"
                f"请确保 C 盘有足够的可用空间。"
            ),
            actions=[
                ft.TextButton("取消", on_click=_cancel),
                ft.ElevatedButton(
                    "确认还原",
                    bgcolor=ft.colors.BLUE_700,
                    color="white",
                    on_click=_do_restore,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.app.page.overlay.append(dlg)
        dlg.open = True
        self.app.page.update()

