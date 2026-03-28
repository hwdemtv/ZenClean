import flet as ft
from config.settings import COLOR_ZEN_PRIMARY

class FileListItem(ft.Container):
    """
    文件列表项组件。
    支持在扫描过程中先以“分析中”状态占位，待 AI 结果返回后局部刷新。
    """
    def __init__(self, node: dict, on_check_change, size_str: str):
        super().__init__()
        self.node = node
        self.on_check_change = on_check_change
        self.size_str = size_str
        
        # 定义内部需要动态刷新的控件
        self._risk_icon = ft.Icon(name=ft.icons.CIRCLE, size=10)
        self._path_text = ft.Text(
            self._truncate_path(node["path"]),
            size=12, expand=True, font_family="Consolas"
        )
        self._size_text = ft.Text(size_str, size=12, color=ft.colors.GREY_500)
        self._status_text = ft.Text("", size=10, color=ft.colors.GREY_400, italic=True)
        
        # 初始化显示
        self._apply_node_data(node)
        
        self.content = ft.Row([
            ft.Checkbox(
                value=node.get("is_checked", False), 
                on_change=lambda e: self.on_check_change(e, self.node)
            ),
            self._risk_icon,
            ft.Column([
                self._path_text,
                self._status_text
            ], spacing=0, expand=True, alignment=ft.MainAxisAlignment.CENTER),
            self._size_text,
            ft.IconButton(
                icon=ft.icons.FOLDER_OPEN_ROUNDED,
                icon_size=16,
                icon_color=COLOR_ZEN_PRIMARY,
                tooltip="打开文件所在目录 (手动清理)",
                on_click=self._open_location
            ),
        ], spacing=5)
        
        self.padding = ft.padding.only(left=10, right=5, top=2, bottom=2)
        self.tooltip = node.get("ai_advice", "")

    def _truncate_path(self, path: str) -> str:
        return path[-70:] if len(path) > 75 else path

    def _apply_node_data(self, node):
        """根据节点数据更新内部控件状态"""
        risk = node.get("risk_level", "UNKNOWN")
        
        # 风险颜色映射
        risk_colors = {
            "SAFE": ft.colors.GREEN_400,
            "LOW": ft.colors.GREEN_400,
            "MEDIUM": ft.colors.YELLOW_400,
            "HIGH": ft.colors.RED_400,
            "CRISIS": ft.colors.RED_700,
            "ANALYZING": ft.colors.BLUE_200,
            "UNKNOWN": ft.colors.GREY_400
        }
        self._risk_icon.color = risk_colors.get(risk, ft.colors.GREY_400)
        
        # 如果是正在分析状态，显示提示
        if risk == "ANALYZING":
            self._status_text.value = "AI 研判中..."
            self._status_text.visible = True
        else:
            self._status_text.visible = False
            
        self.tooltip = node.get("ai_advice", "")

    def update_ai_result(self, result_node: dict):
        """外部调用：异步更新 AI 结果"""
        self.node.update(result_node)
        self._apply_node_data(self.node)
        if self.page:
            self.update()

    def _open_location(self, e):
        import os
        target_dir = os.path.dirname(self.node["path"])
        if os.path.exists(target_dir):
            os.startfile(target_dir)
