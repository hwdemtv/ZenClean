import flet as ft
import time
import threading

def main(page: ft.Page):
    page.title = "Flet Dynamic Update Test"
    
    # 一个列表，存储 UI 控件以便后续更新
    controls_map = {}
    
    list_col = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
    
    for i in range(10):
        # 模拟 FileListItem
        row_content = ft.Row([
            ft.Icon(ft.icons.FILE_PRESENT),
            ft.Text(f"File_{i}.dat", expand=True),
            ft.Text("Analyzing...", key=f"status_{i}", color=ft.colors.GREY_500)
        ])
        
        container = ft.Container(
            content=row_content,
            padding=10,
            border=ft.border.all(1, ft.colors.OUTLINE_VARIANT),
            border_radius=5,
            tooltip=f"Initial tooltip for {i}"
        )
        
        controls_map[i] = container
        list_col.controls.append(container)
        
    page.add(
        ft.Text("Scanning simulation...", size=20, weight=ft.FontWeight.BOLD),
        list_col
    )
    
    def background_work():
        time.sleep(2)
        # 模拟 AI 批量返回结果
        results = {
            2: ("SAFE", "This is a log file."),
            5: ("RISK", "Potentially dangerous cache."),
            8: ("UNKNOWN", "Rate limited, retry later.")
        }
        
        for idx, (status, advice) in results.items():
            if idx in controls_map:
                container = controls_map[idx]
                # 查找并更新内部的状态文本
                # 在 Flet 中，我们可以通过遍历 content.controls 或者使用 ref
                # 这里通过 list index 演示简单查找
                status_text = container.content.controls[2]
                status_text.value = status
                status_text.color = ft.colors.GREEN if status == "SAFE" else ft.colors.RED
                
                # 更新 Tooltip
                container.tooltip = advice
                
                print(f"Updated item {idx}")
        
        # 统一刷新页面
        page.update()

    threading.Thread(target=background_work, daemon=True).start()

ft.app(target=main)
