import flet as ft
import os
import threading
import ctypes
from pathlib import Path
from datetime import datetime
from core.app_migrator import AppMigrator, APP_TARGETS
from core.system_migrator import SystemMigrator
from core.patch_analyzer import PatchCacheAnalyzer
from config.settings import COLOR_ZEN_PRIMARY, COLOR_ZEN_TEXT_MAIN, COLOR_ZEN_TEXT_DIM

class AppMigrationView(ft.Column):
    def __init__(self, app):
        super().__init__(expand=True, scroll=ft.ScrollMode.AUTO)
        self.app = app
        self.migrator = AppMigrator()
        self.sys_migrator = SystemMigrator()
        self.patch_analyzer = PatchCacheAnalyzer()
        
        self.picker_context = None
        self._picker_added = False  # 防止重复添加 FilePicker
        self.file_picker = ft.FilePicker(on_result=self._on_file_picker_result)
        
        # ── 1. 顶部标题 ──
        self.header = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.IconButton(ft.icons.ARROW_BACK_IOS_NEW, on_click=lambda _: self.app.navigate_to("/scan")),
                    ft.Icon(ft.icons.DRIVE_FILE_MOVE, size=28, color=COLOR_ZEN_PRIMARY),
                    ft.Text("大厂应用无损搬家", size=24, weight=ft.FontWeight.W_800, color=COLOR_ZEN_TEXT_MAIN),
                ], spacing=10),
                ft.Text("将微信、Docker 等“空间杀手”的数据安全迁移至非系统盘，底层透明映射，不影响软件运行。", 
                        size=13, color=COLOR_ZEN_TEXT_DIM),
            ], spacing=2),
            padding=ft.padding.only(bottom=15)
        )
        
        # ── 2. 核心网格容器 ──
        self.grid = ft.ResponsiveRow(spacing=20, run_spacing=20)
        
        # ── 3. 历史记录容器 ──
        self.history_list = ft.Column(spacing=10)
        self.history_section = ft.Column([
            ft.Divider(height=40, color=ft.colors.with_opacity(0.1, ft.colors.ON_SURFACE)),
            ft.Row([
                ft.Icon(ft.icons.HISTORY, size=20, color=COLOR_ZEN_TEXT_DIM),
                ft.Text("已搬家的应用记录", size=16, weight=ft.FontWeight.W_600, color=COLOR_ZEN_TEXT_MAIN),
            ], spacing=8),
            self.history_list
        ], visible=False)

        self.controls = [
            self.header,
            self.grid,
            self.history_section
        ]
        
        # 挂载后启动后台数据加载
        self.did_mount = self.load_data

    def load_data(self):
        """加载应用体积和历史记录"""
        # 只添加一次 FilePicker 到 overlay
        if not self._picker_added:
            self.app.page.overlay.append(self.file_picker)
            self._picker_added = True
            self.app.page.update()

        self.grid.controls = [ft.Container(content=ft.ProgressRing(), alignment=ft.alignment.center, height=200, col=12)]
        self.update()

        def _task():
            history = self.migrator.get_history()
            sys_history = self.sys_migrator.get_history()

            cards = []

            # --- 中断迁移恢复提醒 (最高优先级) ---
            interrupted = self.migrator.check_interrupted_migrations()
            if interrupted:
                for item in interrupted:
                    cards.append(self._build_interrupted_alert_card(item))

            # --- 增量增长提醒卡片 (次优先级) ---
            growth_items = self.migrator.check_incremental_growth()
            if growth_items:
                for item in growth_items:
                    cards.append(self._build_growth_alert_card(item))

            # --- 系统级特权高危项 (置顶) ---
            is_sys_migrated = any(h["target_id"] == "win_installer_patch_cache" for h in sys_history)
            if not is_sys_migrated:
                sys_card = self._build_sys_card()
                if sys_card:
                    cards.append(sys_card)

            # --- 常规应用项 ---
            for target in APP_TARGETS:
                # 检查是否已搬家
                is_migrated = any(h["target_id"] == target.id for h in history)
                if not is_migrated:
                    cards.append(self._build_app_card(target))

            # 更新历史列表
            history_items = []
            if is_sys_migrated:
                history_items.append(self._build_sys_history_item(sys_history[0]))

            for h in history:
                history_items.append(self._build_history_item(h))

            async def _gui_update():
                self.grid.controls = cards if cards else [ft.Text("所有支持的应用均已搬家或未安装。", color=COLOR_ZEN_TEXT_DIM, col=12)]
                self.history_list.controls = history_items
                self.history_section.visible = len(history_items) > 0
                if self.page:
                    self.update()

            self.app.page.run_task(_gui_update)

        threading.Thread(target=_task, daemon=True).start()

    def _build_interrupted_alert_card(self, item: dict):
        """构建中断迁移恢复提醒卡片"""
        phase_names = {
            "preflight": "预检阶段",
            "copying": "复制文件阶段",
            "verifying": "验证阶段",
            "creating_junction": "创建链接阶段",
        }
        phase_name = phase_names.get(item.get("phase"), item.get("phase", "未知"))
        moved_count = len(item.get("moved_items", []))
        start_time = item.get("start_time", "未知时间")

        # 根据是否可恢复决定按钮
        if item.get("can_recover"):
            actions = ft.Row([
                ft.TextButton(
                    "放弃并回滚",
                    on_click=lambda _, tid=item['target_id']: self._on_rollback_interrupted(tid),
                    style=ft.ButtonStyle(color=ft.colors.RED_400)
                ),
                ft.ElevatedButton(
                    "恢复迁移",
                    icon=ft.icons.RESTORE,
                    on_click=lambda _, tid=item['target_id']: self._on_recover_interrupted(tid),
                    style=ft.ButtonStyle(color="white", bgcolor=ft.colors.RED_600),
                ),
            ], spacing=10)
        else:
            actions = ft.Row([
                ft.TextButton(
                    "清除状态",
                    on_click=lambda _, tid=item['target_id']: self._on_clear_interrupted_state(tid),
                    style=ft.ButtonStyle(color=COLOR_ZEN_TEXT_DIM)
                ),
            ], spacing=10)

        return ft.Container(
            col=12,
            padding=20,
            border_radius=15,
            bgcolor=ft.colors.with_opacity(0.15, ft.colors.RED_800),
            border=ft.border.all(2, ft.colors.RED_600),
            content=ft.Row([
                ft.Icon(ft.icons.ERROR_OUTLINE, color=ft.colors.RED_400, size=32),
                ft.Column([
                    ft.Row([
                        ft.Text("⚠️ 发现中断的迁移任务", size=16, weight=ft.FontWeight.W_800, color=ft.colors.RED_300),
                        ft.Container(
                            content=ft.Text("需要处理", size=10, color="white"),
                            bgcolor=ft.colors.RED_600,
                            border_radius=4,
                            padding=ft.padding.only(left=6, right=6, top=2, bottom=2),
                        ),
                    ], spacing=8),
                    ft.Text(f"{item['target_name']} - {phase_name}", size=13, color=COLOR_ZEN_TEXT_MAIN),
                    ft.Text(f"已迁移 {moved_count} 个项目 · 开始于 {start_time[:19] if len(start_time) > 19 else start_time}", size=11, color=COLOR_ZEN_TEXT_DIM),
                    ft.Text(item.get("recovery_hint", ""), size=11, color=ft.colors.AMBER_300, italic=True),
                ], expand=True, spacing=2),
                actions,
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        )

    def _on_recover_interrupted(self, target_id: str):
        """恢复中断的迁移"""
        def _do_recover(e):
            self.app.page.dialog.open = False
            self.app.page.update()

            self.pb = ft.ProgressBar(width=400, color=ft.colors.RED_400, bgcolor="#EEEEEE")
            self.pb_text = ft.Text("正在恢复迁移...", size=12, color=COLOR_ZEN_TEXT_DIM)

            self.app.page.dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("恢复迁移中"),
                content=ft.Column([self.pb, self.pb_text], tight=True, spacing=10),
            )
            self.app.page.dialog.open = True
            self.app.page.update()

            def _task():
                def _progress_cb(moved, total, item_name):
                    pct = moved / total if total > 0 else 0
                    async def _update_ui():
                        self.pb.value = pct
                        self.pb_text.value = f"正在处理: {item_name} ({pct*100:.1f}%)"
                        self.app.page.update()
                    self.app.page.run_task(_update_ui)

                ok, msg = self.migrator.recover_interrupted_migration(target_id, on_progress=_progress_cb)

                async def _finish():
                    self.app.page.dialog.open = False
                    self.app.show_snack_bar(msg, is_error=not ok)
                    self.load_data()
                self.app.page.run_task(_finish)

            threading.Thread(target=_task, daemon=True).start()

        self.app.page.dialog = ft.AlertDialog(
            title=ft.Text("确认恢复迁移？"),
            content=ft.Text("将从上次中断的位置继续迁移操作。"),
            actions=[
                ft.TextButton("取消", on_click=lambda _: [setattr(self.app.page.dialog, 'open', False), self.app.page.update()]),
                ft.ElevatedButton("开始恢复", on_click=_do_recover, bgcolor=ft.colors.RED_600, color="white"),
            ]
        )
        self.app.page.dialog.open = True
        self.app.page.update()

    def _on_rollback_interrupted(self, target_id: str):
        """回滚中断的迁移"""
        def _do_rollback(e):
            self.app.page.dialog.open = False
            self.app.page.update()

            ok, msg = self.migrator.rollback_interrupted_migration(target_id)
            self.app.show_snack_bar(msg, is_error=not ok)
            self.load_data()

        self.app.page.dialog = ft.AlertDialog(
            title=ft.Row([ft.Icon(ft.icons.WARNING, color=ft.colors.RED_400), ft.Text("确认回滚？")]),
            content=ft.Text("这将把已迁移到目标盘的数据移回原位置，并清除中断状态。"),
            actions=[
                ft.TextButton("取消", on_click=lambda _: [setattr(self.app.page.dialog, 'open', False), self.app.page.update()]),
                ft.ElevatedButton("确认回滚", on_click=_do_rollback, bgcolor=ft.colors.RED_600, color="white"),
            ]
        )
        self.app.page.dialog.open = True
        self.app.page.update()

    def _on_clear_interrupted_state(self, target_id: str):
        """清除中断状态（不可恢复时）"""
        self.migrator._clear_state(target_id)
        self.app.show_snack_bar("已清除中断状态")
        self.load_data()

    def _build_growth_alert_card(self, growth_item: dict):
        """构建增量增长提醒卡片"""
        return ft.Container(
            col=12,
            padding=20,
            border_radius=15,
            bgcolor=ft.colors.with_opacity(0.1, ft.colors.AMBER_700),
            border=ft.border.all(1, ft.colors.AMBER_600),
            content=ft.Row([
                ft.Icon(ft.icons.TRENDING_UP, color=ft.colors.AMBER_400, size=30),
                ft.Column([
                    ft.Text(f"⚠️ {growth_item['target_name']} 数据增长提醒", size=15, weight=ft.FontWeight.W_700, color=ft.colors.AMBER_300),
                    ft.Text(f"自上次搬家以来增长了 {growth_item['growth_gb']} GB，当前总大小 {growth_item['current_size_gb']:.2f} GB", size=12, color=COLOR_ZEN_TEXT_DIM),
                ], expand=True, spacing=2),
                ft.Row([
                    ft.TextButton(
                        "已知晓",
                        on_click=lambda _, tid=growth_item['target_id']: self._on_growth_acknowledge(tid),
                        style=ft.ButtonStyle(color=COLOR_ZEN_TEXT_DIM)
                    ),
                    ft.ElevatedButton(
                        "再次迁移",
                        icon=ft.icons.MOVE_DOWN,
                        on_click=lambda _, tid=growth_item['target_id']: self._on_re_migrate_click(tid),
                        style=ft.ButtonStyle(color="white", bgcolor=ft.colors.AMBER_600),
                    ),
                ], spacing=5)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        )

    def _on_growth_acknowledge(self, target_id: str):
        """用户确认已知晓增量增长"""
        self.migrator.update_last_check_size(target_id)
        self.app.show_snack_bar("已记录，下次将重新计算增量")
        self.load_data()

    def _on_re_migrate_click(self, target_id: str):
        """点击再次迁移按钮"""
        target = next((t for t in APP_TARGETS if t.id == target_id), None)
        if target:
            self._on_migrate_click(target)

    def _on_file_picker_result(self, e: ft.FilePickerResultEvent):
        if self.picker_context == "sys":
            self._on_sys_directory_picked(e)
        elif self.picker_context:
            self._on_directory_picked(e, self.picker_context)
        self.picker_context = None

    def _get_dir_size(self, path_template):
        """计算目录体积"""
        path = Path(os.path.expandvars(path_template))
        if not path.exists():
            return 0
        total = 0
        try:
            for entry in os.scandir(path):
                if entry.is_file():
                    total += entry.stat().st_size
                elif entry.is_dir():
                    total += self._get_dir_size_recursive(entry.path)
        except:
            pass
        return total

    def _get_dir_size_recursive(self, path):
        total = 0
        try:
            for entry in os.scandir(path):
                if entry.is_file():
                    total += entry.stat().st_size
                elif entry.is_dir():
                    total += self._get_dir_size_recursive(entry.path)
        except:
            pass
        return total

    def _fmt_size(self, size_bytes):
        if size_bytes == 0: return "未检测到数据"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} PB"

    def _build_app_card(self, target):
        """构建待搬家应用的卡片 - 采用宽行布局（单列）"""
        size = self._get_dir_size(target.path_template)
        size_str = self._fmt_size(size)
        
        return ft.Container(
            col=12,
            padding=20,
            border_radius=15,
            bgcolor=ft.colors.with_opacity(0.03, ft.colors.ON_SURFACE),
            border=ft.border.all(1, ft.colors.with_opacity(0.1, ft.colors.ON_SURFACE)),
            content=ft.Row([
                # 左侧：图标与名称
                ft.Row([
                    ft.Container(
                        content=ft.Icon(getattr(ft.icons, target.icon, ft.icons.APPS), color=COLOR_ZEN_PRIMARY, size=30),
                        padding=10,
                        bgcolor=ft.colors.with_opacity(0.1, COLOR_ZEN_PRIMARY),
                        border_radius=10
                    ),
                    ft.Column([
                        ft.Text(target.name, size=16, weight=ft.FontWeight.BOLD, color=COLOR_ZEN_TEXT_MAIN),
                        ft.Text(size_str, size=14, color=COLOR_ZEN_PRIMARY if size > 0 else COLOR_ZEN_TEXT_DIM),
                    ], spacing=0, width=200)
                ], spacing=15),
                
                # 中间：描述（弹性空间）
                ft.Container(
                    content=ft.Text(target.description, size=12, color=COLOR_ZEN_TEXT_DIM),
                    expand=True,
                    padding=ft.padding.only(left=20, right=20)
                ),
                
                # 右侧：动作按钮
                ft.ElevatedButton(
                    "开始搬家",
                    icon=ft.icons.MOVE_DOWN,
                    style=ft.ButtonStyle(
                        color="white",
                        bgcolor=COLOR_ZEN_PRIMARY if size > 0 else ft.colors.GREY_400,
                        shape=ft.RoundedRectangleBorder(radius=8)
                    ),
                    disabled=size == 0,
                    on_click=lambda _: self._on_migrate_click(target)
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        )

    # =============== 系统级特权 UI 构建 ===============

    def _build_sys_card(self):
        checks = self.sys_migrator.preflight_check("C:") # drive 暂时无所谓，只是拿 size 和状态
        if checks.get("is_junction"):
            return None # 已经被映射过的理论上不应该到这，被外层过滤了
            
        size_bytes = checks.get("size_bytes", 0)
        size_str = self._fmt_size(size_bytes)
        can_click_admin = checks.get("is_admin", False) and checks.get("path_exists", False)
        
        # 极度危险的暗红警告卡片
        return ft.Container(
            col=12,
            padding=20,
            border_radius=15,
            bgcolor=ft.colors.with_opacity(0.1, ft.colors.RED_800),
            border=ft.border.all(1, ft.colors.RED_700),
            content=ft.Row([
                # 左侧
                ft.Row([
                    ft.Container(
                        content=ft.Icon(ft.icons.WARNING_AMBER_ROUNDED, color=ft.colors.RED_400, size=30),
                        padding=10,
                        bgcolor=ft.colors.with_opacity(0.1, ft.colors.RED_400),
                        border_radius=10
                    ),
                    ft.Column([
                        ft.Text("Windows 补丁档案存根", size=16, weight=ft.FontWeight.W_900, color=ft.colors.RED_400),
                        ft.Text(size_str, size=15, weight=ft.FontWeight.BOLD, color=ft.colors.RED_300 if size_bytes > 0 else COLOR_ZEN_TEXT_DIM),
                    ], spacing=0, width=200)
                ], spacing=15),
                
                # 中间警告文本
                ft.Container(
                    content=ft.Text(
                        "$PatchCache$ 是系统回退卸载旧网卡/显卡/补丁的命根子。\n强制迁移将冻结提权机制并暂停 Windows Installer 服务！", 
                        size=12, color=ft.colors.RED_300, weight=ft.FontWeight.W_500
                    ),
                    expand=True,
                    padding=ft.padding.only(left=20, right=20)
                ),

                # 右侧动作按钮组
                ft.Row([
                    ft.OutlinedButton(
                        "分析详情",
                        icon=ft.icons.ANALYTICS,
                        style=ft.ButtonStyle(
                            color=ft.colors.AMBER_400,
                            side={"": ft.BorderSide(1, ft.colors.AMBER_400)},
                        ),
                        on_click=self._on_sys_analyze_click
                    ),
                    ft.ElevatedButton(
                        "高危强迁" if can_click_admin else "需管理员权限",
                        icon=ft.icons.BOLT,
                        style=ft.ButtonStyle(
                            color="white",
                            bgcolor=ft.colors.RED_800 if can_click_admin else ft.colors.GREY_700,
                            shape=ft.RoundedRectangleBorder(radius=8)
                        ),
                        disabled=not can_click_admin,
                        on_click=self._on_sys_migrate_click
                    ),
                ], spacing=10)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        )

    def _build_sys_history_item(self, record):
        return ft.Container(
            padding=15,
            border_radius=10,
            bgcolor=ft.colors.with_opacity(0.05, ft.colors.AMBER_900),
            border=ft.border.all(1, ft.colors.AMBER_700),
            content=ft.Row([
                ft.Icon(ft.icons.GPP_BAD, color=ft.colors.AMBER_400, size=20),
                ft.Column([
                    ft.Text("Windows 补丁档案存根 ($PatchCache$)", size=14, weight=ft.FontWeight.W_900, color=ft.colors.AMBER_400),
                    ft.Row([
                        ft.Text(f"原路径: {record['original_path']}", size=11, color=COLOR_ZEN_TEXT_DIM),
                        ft.Icon(ft.icons.ARROW_FORWARD, size=12, color=COLOR_ZEN_TEXT_DIM),
                        ft.Text(f"异地军火库: {record['dest_path']}", size=11, color=ft.colors.AMBER_200),
                    ], spacing=5)
                ], expand=True, spacing=2),
                ft.OutlinedButton(
                    "执行撤离还盘",
                    icon=ft.icons.KEYBOARD_RETURN,
                    style=ft.ButtonStyle(color=ft.colors.AMBER_400),
                    on_click=lambda _: self._on_sys_restore_click(record)
                )
            ], spacing=15)
        )

    # =============== 系统级特权 UI 构建 END ===============


    def _build_history_item(self, record):
        """构建已搬家记录项"""
        return ft.Container(
            padding=15,
            border_radius=10,
            bgcolor=ft.colors.with_opacity(0.02, ft.colors.ON_SURFACE),
            border=ft.border.all(1, ft.colors.with_opacity(0.05, ft.colors.ON_SURFACE)),
            content=ft.Row([
                ft.Icon(ft.icons.CHECK_CIRCLE, color=ft.colors.GREEN_400, size=20),
                ft.Column([
                    ft.Text(record["target_name"], size=14, weight=ft.FontWeight.W_600, color=COLOR_ZEN_TEXT_MAIN),
                    ft.Row([
                        ft.Text(f"原路径: {record['original_path']}", size=11, color=COLOR_ZEN_TEXT_DIM),
                        ft.Icon(ft.icons.ARROW_FORWARD, size=12, color=COLOR_ZEN_TEXT_DIM),
                        ft.Text(f"现位置: {record['dest_path']}", size=11, color=COLOR_ZEN_PRIMARY),
                    ], spacing=5)
                ], expand=True, spacing=2),
                ft.OutlinedButton(
                    "还原",
                    icon=ft.icons.RESTORE,
                    style=ft.ButtonStyle(color=COLOR_ZEN_TEXT_DIM),
                    on_click=lambda _: self._on_restore_click(record)
                )
            ], spacing=15)
        )

    def _on_migrate_click(self, target):
        # 1. 检查进程
        alive_procs = self.migrator.check_process_alive(target.id)
        if alive_procs:
            self._show_process_kill_dialog(target, alive_procs)
            return

        # 2. 选择目标盘
        self._pick_destination_and_run(target)

    def _show_process_kill_dialog(self, target, alive_procs):
        """显示进程关闭对话框 - 使用优雅关闭"""
        def _do_graceful_kill(e):
            """优雅关闭"""
            self.app.page.dialog.open = False
            self.app.page.update()
            self.app.show_snack_bar("正在尝试优雅关闭相关进程...")
            ok, msg = self.migrator.kill_target_processes_gracefully(target.id)
            if ok:
                self._pick_destination_and_run(target)
            else:
                self.app.show_snack_bar(msg, is_error=True)

        def _do_force_kill(e):
            """强制关闭"""
            self.app.page.dialog.open = False
            self.app.page.update()
            ok, msg = self.migrator.kill_target_processes(target.id)
            if ok:
                self._pick_destination_and_run(target)
            else:
                self.app.show_snack_bar(msg, is_error=True)

        # 根据目标类别决定警告级别
        is_browser = target.category == "browser_cache"
        warning_text = "浏览器可能正在进行下载或填写表单" if is_browser else "可能有未保存的工作"

        self.app.page.dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.icons.WARNING_AMBER_ROUNDED, color=ft.colors.AMBER_400),
                ft.Text("检测到应用正在运行", color=COLOR_ZEN_TEXT_MAIN)
            ]),
            content=ft.Column([
                ft.Text(f"以下进程正在运行：{', '.join(alive_procs)}", size=13),
                ft.Text(f"⚠️ {warning_text}，强制关闭可能导致数据丢失", size=12, color=ft.colors.AMBER_400),
                ft.Divider(height=10, color="transparent"),
                ft.Text("建议选择「优雅关闭」等待程序自行退出", size=12, color=COLOR_ZEN_TEXT_DIM),
            ], tight=True, spacing=5),
            actions=[
                ft.TextButton("手动关闭", on_click=lambda _: [setattr(self.app.page.dialog, 'open', False), self.app.page.update()]),
                ft.OutlinedButton("强制关闭", on_click=_do_force_kill, style=ft.ButtonStyle(color=ft.colors.RED_400)),
                ft.ElevatedButton("优雅关闭", on_click=_do_graceful_kill, bgcolor=COLOR_ZEN_PRIMARY, color="white"),
            ]
        )
        self.app.page.dialog.open = True
        self.app.page.update()

    def _pick_destination_and_run(self, target):
        self.picker_context = target
        self.file_picker.get_directory_path(dialog_title=f"选择 [{target.name}] 的落脚点（如 D:\\）")

    def _on_directory_picked(self, e: ft.FilePickerResultEvent, target):
        if not e.path:
            return
            
        dest_drive = Path(e.path).drive
        if not dest_drive:
            self.app.show_snack_bar("无效的路径，请选择一个驱动器根目录或子目录。", is_error=True)
            return

        # 开启进度弹窗
        self._show_progress_dialog(target)
        
        def _task():
            def _progress_cb(cur, total, item_name):
                pct = cur / total if total > 0 else 0
                async def _update_ui():
                    self.pb.value = pct
                    self.pb_text.value = f"正在搬运: {item_name} ({pct*100:.1f}%)"
                    self.app.page.update()
                self.app.page.run_task(_update_ui)

            ok, msg = self.migrator.execute_migration(target.id, dest_drive, on_progress=_progress_cb)

            async def _finish():
                self.app.page.dialog.open = False
                self.app.show_snack_bar(msg, is_error=not ok)
                self.load_data()
            self.app.page.run_task(_finish)

        threading.Thread(target=_task, daemon=True).start()

    def _show_progress_dialog(self, target):
        self.pb = ft.ProgressBar(width=400, color=COLOR_ZEN_PRIMARY, bgcolor="#EEEEEE")
        self.pb_text = ft.Text("准备工作中...", size=12, color=COLOR_ZEN_TEXT_DIM)
        
        self.app.page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"正在搬家: {target.name}"),
            content=ft.Column([
                self.pb,
                self.pb_text,
                ft.Text("请不要关闭程序或断开磁盘连接...", size=11, italic=True, color=ft.colors.AMBER_400)
            ], tight=True, spacing=10),
        )
        self.app.page.dialog.open = True
        self.app.page.update()

    def _on_restore_click(self, record):
        def _do_restore(e):
            self.app.page.dialog.open = False
            self.app.page.update()
            
            # 显示还原进度
            self.app.show_snack_bar(f"正在尝试将 {record['target_name']} 移回 C 盘...")
            
            def _task():
                ok, msg = self.migrator.restore_migration(record["target_id"])
                async def _finish():
                    self.app.show_snack_bar(msg, is_error=not ok)
                    self.load_data()
                self.app.page.run_task(_finish)
            
            threading.Thread(target=_task, daemon=True).start()

        self.app.page.dialog = ft.AlertDialog(
            title=ft.Text("确认还原？"),
            content=ft.Text(f"这将把 {record['target_name']} 的真实数据从 {record['dest_path']} 重新迁回 C 盘并拆除软链接。确保 C 盘有足够空间！"),
            actions=[
                ft.TextButton("取消", on_click=lambda _: [setattr(self.app.page.dialog, 'open', False), self.app.page.update()]),
                ft.ElevatedButton("确认还原", on_click=_do_restore, bgcolor=ft.colors.RED_400, color="white")
            ]
        )
        self.app.page.dialog.open = True
        self.app.page.update()

    # =============== 系统专属控制流 ===============
    
    def _on_sys_migrate_click(self, e):
        # 抛出双重免责声明
        def _proceed(e):
            self.app.page.dialog.open = False
            self.app.page.update()
            self.picker_context = "sys"
            self.file_picker.get_directory_path(dialog_title="选择系统核心存根的落脚点（强烈建议放到固态硬盘!!）")

        self.app.page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([ft.Icon(ft.icons.REPORT_PROBLEM, color="red"), ft.Text("系统特权行动警告", color="red")]),
            content=ft.Text(
                "请再三确认您的意图：\n\n"
                "1. 此操作将挂起系统的 Windows Installer (msiserver) 兵权守护进程。\n"
                "2. 这是一个极其底层的骇客行为。如有突然的断电断网，可能导致系统无法验证安装包签名。\n"
                "3. 请确保目标驻地是一块 高速固态硬盘(SSD)。 若放在机械硬盘，未来系统打补丁期间，I/O阻塞会把机器拖进卡顿地狱！\n\n"
                "一旦确认，即代表您自愿承担系统崩溃之风险。",
                color=COLOR_ZEN_TEXT_MAIN, size=13
            ),
            actions=[
                ft.TextButton("临危勒马", on_click=lambda _: [setattr(self.app.page.dialog, 'open', False), self.app.page.update()]),
                ft.ElevatedButton("后果自负，立即夺权起飞", on_click=_proceed, bgcolor="red", color="white")
            ]
        )
        self.app.page.dialog.open = True
        self.app.page.update()

    def _on_sys_directory_picked(self, e: ft.FilePickerResultEvent):
        if not e.path: return
        dest_drive = Path(e.path).drive
        if not dest_drive:
            self.app.show_snack_bar("目标选址无效。必须在本地卷驱动器内获取锚点。", is_error=True)
            return

        self.pb = ft.ProgressBar(width=400, color="red", bgcolor="#EEEEEE")
        self.pb_text = ft.Text("正在接管 msiserver 权限...", size=12, color="red")
        
        self.app.page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("核威慑级：深空转移"),
            content=ft.Column([
                self.pb, self.pb_text,
                ft.Text("系统已进入脱机重构保护态...绝对不要强制断电！", size=11, color="red")
            ], tight=True, spacing=10),
        )
        self.app.page.dialog.open = True
        self.app.page.update()

        def _task():
            def _progress_cb(pct):
                async def _update_ui():
                    self.pb.value = pct
                    self.pb_text.value = f"正在迁移核心组件 ({pct*100:.1f}%)"
                    self.app.page.update()
                if self.app.page: self.app.page.run_task(_update_ui)

            ok, msg = self.sys_migrator.migrate(dest_drive, on_progress=_progress_cb)
            
            async def _finish():
                self.app.page.dialog.open = False
                self.app.show_snack_bar(msg, is_error=not ok)
                self.load_data()
            if self.app.page: self.app.page.run_task(_finish)
            
        threading.Thread(target=_task, daemon=True).start()

    def _on_sys_restore_click(self, record):
        def _do_restore(e):
            self.app.page.dialog.open = False
            self.app.page.update()
            
            self.pb = ft.ProgressBar(width=400, color="amber", bgcolor="#EEEEEE")
            self.pb_text = ft.Text("回收兵权...", size=12, color="amber")
            self.app.page.dialog = ft.AlertDialog(
                modal=True, title=ft.Text("收回复盘"),
                content=ft.Column([self.pb, self.pb_text], tight=True, spacing=10)
            )
            self.app.page.dialog.open = True
            self.app.page.update()

            def _task():
                def _progress_cb(pct):
                    async def _update_ui():
                        self.pb.value = pct
                        self.pb_text.value = f"回切组件流 ({pct*100:.1f}%)"
                        self.app.page.update()
                    if self.app.page: self.app.page.run_task(_update_ui)
                    
                ok, msg = self.sys_migrator.restore(on_progress=_progress_cb)
                
                async def _finish():
                    self.app.page.dialog.open = False
                    self.app.show_snack_bar(msg, is_error=not ok)
                    self.load_data()
                if self.app.page: self.app.page.run_task(_finish)
            
            threading.Thread(target=_task, daemon=True).start()

        self.app.page.dialog = ft.AlertDialog(
            title=ft.Row([ft.Icon(ft.icons.WARNING, color="amber"), ft.Text("退防 C 盘", color="amber")]),
            content=ft.Text("确保 C 盘有足够的留存空间，回退过程中依然会夺取 Windows Installer 守护进程控制权。"),
            actions=[
                ft.TextButton("终止退防", on_click=lambda _: [setattr(self.app.page.dialog, 'open', False), self.app.page.update()]),
                ft.ElevatedButton("立即还盘", on_click=_do_restore, bgcolor="amber", color="black")
            ]
        )
        self.app.page.dialog.open = True
        self.app.page.update()

    # =============== 补丁分析功能 ===============

    def _is_admin(self):
        """检查是否以管理员权限运行"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    def _on_sys_analyze_click(self, e):
        """点击分析详情按钮"""
        # 先检查管理员权限
        if not self._is_admin():
            self.app.page.dialog = ft.AlertDialog(
                title=ft.Row([ft.Icon(ft.icons.WARNING, color="amber"), ft.Text("需要管理员权限")]),
                content=ft.Text("分析补丁缓存需要管理员权限。请右键选择“以管理员身份运行”启动本程序。"),
                actions=[ft.TextButton("确定", on_click=lambda _: setattr(self.app.page.dialog, 'open', False) or self.app.page.update())]
            )
            self.app.page.dialog.open = True
            self.app.page.update()
            return

        # 先显示加载中
        self.pb = ft.ProgressRing(width=40, height=40)
        self.pb_text = ft.Text("正在扫描补丁档案...", size=13)

        self.app.page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("补丁档案分析中"),
            content=ft.Column([self.pb, self.pb_text], tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        )
        self.app.page.dialog.open = True
        self.app.page.update()

        def _task():
            # 后台分析
            analysis = self.patch_analyzer.analyze()
            recommendations = self.patch_analyzer.get_cleanup_recommendations()

            async def _show_result():
                self.app.page.dialog.open = False
                self.app.page.update()

                # 构建展示内容
                if not analysis["available"]:
                    content = ft.Column([
                        ft.Icon(ft.icons.INFO, size=40, color=ft.colors.BLUE_400),
                        ft.Text("补丁缓存目录不存在", size=14, weight=ft.FontWeight.BOLD),
                        ft.Text("该目录可能已被清理或不存在", size=12, color=COLOR_ZEN_TEXT_DIM),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                elif analysis.get("is_migrated"):
                    content = ft.Column([
                        ft.Icon(ft.icons.CHECK_CIRCLE, size=40, color=ft.colors.GREEN_400),
                        ft.Text("已迁移到其他盘", size=14, weight=ft.FontWeight.BOLD),
                        ft.Text("补丁缓存已通过搬家功能转移到其他盘符", size=12, color=COLOR_ZEN_TEXT_DIM),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                else:
                    # 构建补丁列表
                    all_patches = analysis.get("patches", [])
                    patches = all_patches[:20]  # 最多显示20个
                    patch_rows = []

                    for p in patches:
                        age_days = (datetime.now() - p.modified_time).days
                        age_str = f"{age_days}天前"

                        # 颜色根据时间
                        if age_days > 365:
                            color = ft.colors.RED_400
                        elif age_days > 180:
                            color = ft.colors.ORANGE_400
                        else:
                            color = ft.colors.GREEN_400

                        patch_rows.append(
                            ft.Container(
                                content=ft.Row([
                                    ft.Text(p.patch_id or p.name[:25], size=11, weight=ft.FontWeight.W_500, expand=1),
                                    ft.Text(age_str, size=10, color=color),
                                    ft.Text(self._fmt_size(p.size_bytes), size=10, color=COLOR_ZEN_TEXT_DIM),
                                ]),
                                padding=5,
                                border=ft.border.only(bottom=1, color=ft.colors.with_opacity(0.1, "onSurface"))
                            )
                        )

                    # 统计信息
                    total_size = analysis.get("total_size", 0)
                    total_count = analysis.get("total_count", 0)
                    safe_size = recommendations.get("recommendations", {}).get("safe", {}).get("size", 0)
                    safe_count = recommendations.get("recommendations", {}).get("safe", {}).get("count", 0)

                    content = ft.Container(
                        width=500,
                        content=ft.Column([
                            # 统计卡片
                            ft.Container(
                                content=ft.Row([
                                    ft.Container(
                                        content=ft.Column([
                                            ft.Text("总大小", size=11, color=COLOR_ZEN_TEXT_DIM),
                                            ft.Text(self._fmt_size(total_size), size=16, weight=ft.FontWeight.BOLD, color=COLOR_ZEN_PRIMARY),
                                        ], tight=True),
                                        expand=1, alignment=ft.alignment.center
                                    ),
                                    ft.Container(
                                        content=ft.Column([
                                            ft.Text("补丁数", size=11, color=COLOR_ZEN_TEXT_DIM),
                                            ft.Text(str(total_count), size=16, weight=ft.FontWeight.BOLD, color=COLOR_ZEN_PRIMARY),
                                        ], tight=True),
                                        expand=1, alignment=ft.alignment.center
                                    ),
                                    ft.Container(
                                        content=ft.Column([
                                            ft.Text("可清理", size=11, color=COLOR_ZEN_TEXT_DIM),
                                            ft.Text(f"{self._fmt_size(safe_size)}\n({safe_count}个)", size=14, weight=ft.FontWeight.BOLD, color=ft.colors.RED_400),
                                        ], tight=True),
                                        expand=1, alignment=ft.alignment.center
                                    ),
                                ], spacing=10),
                                padding=15,
                                bgcolor=ft.colors.with_opacity(0.05, "surface"),
                                border_radius=8
                            ),

                            ft.Divider(height=20),

                            # 补丁列表标题
                            ft.Text("补丁详情 (按大小排序)", size=12, weight=ft.FontWeight.W_600, color=COLOR_ZEN_TEXT_DIM),
                            ft.Text("超过365天的补丁可安全清理", size=10, color=COLOR_ZEN_TEXT_DIM),

                            # 列表头
                            ft.Container(
                                content=ft.Row([
                                    ft.Text("补丁名称/KB号", size=10, weight=ft.FontWeight.BOLD, expand=1),
                                    ft.Text("修改时间", size=10, weight=ft.FontWeight.BOLD, width=70),
                                    ft.Text("大小", size=10, weight=ft.FontWeight.BOLD, width=70),
                                ]),
                                padding=ft.padding.only(bottom=5),
                                border=ft.border.only(bottom=2, color=ft.colors.with_opacity(0.3, "primary"))
                            ),

                            # 补丁列表
                            ft.Container(
                                content=ft.Column(patch_rows, spacing=0),
                                height=200,
                                scroll=ft.ScrollMode.AUTO
                            ),

                            # 修复语法与逻辑 Bug：使用三元表达式，并基于 all_patches 判断总数
                            ft.Text(f"... 还有 {len(all_patches) - 20} 个补丁", size=10, color=COLOR_ZEN_TEXT_DIM, italic=True) if len(all_patches) > 20 else ft.Container()

                        ], tight=True, spacing=5)
                    )

                self.app.page.dialog = ft.AlertDialog(
                    modal=True,
                    title=ft.Row([
                        ft.Icon(ft.icons.INVENTORY_2, color=COLOR_ZEN_PRIMARY),
                        ft.Text("Windows 补丁档案分析")
                    ]),
                    content=content,
                    actions=[
                        ft.TextButton("关闭", on_click=lambda _: [setattr(self.app.page.dialog, 'open', False), self.app.page.update()]),
                    ]
                )
                self.app.page.dialog.open = True
                self.app.page.update()

            if self.app.page:
                self.app.page.run_task(_show_result)

        threading.Thread(target=_task, daemon=True).start()
