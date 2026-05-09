import flet as ft
import time
import threading

def main(page: ft.Page):
    page.title = "Flet Progress Timer Test"
    
    elapsed_text = ft.Text("Estimated time: 1.8s (Static)", size=14, color=ft.colors.GREY_500)
    progress = ft.ProgressBar(width=400, color="blue", visible=False)
    
    def start_scan(e):
        e.control.disabled = True
        progress.visible = True
        page.update()
        
        start_time = time.perf_counter()
        
        # 模拟扫描循环
        def run_timer():
            for i in range(50): # 模拟 5 秒
                if not progress.visible: break
                now = time.perf_counter()
                elapsed = now - start_time
                elapsed_text.value = f"Elapsed time: {elapsed:.1f}s · Scanning deep folders..."
                elapsed_text.color = ft.colors.BLUE_700
                page.update()
                time.sleep(0.1)
            
            elapsed_text.value = f"Scan completed in {time.perf_counter()-start_time:.2f}s"
            elapsed_text.color = ft.colors.GREEN_700
            progress.visible = False
            e.control.disabled = False
            page.update()

        threading.Thread(target=run_timer, daemon=True).start()

    scan_btn = ft.ElevatedButton("Start Scan", on_click=start_scan)
    
    page.add(
        ft.Column([
            ft.Text("ZenClean Dashboard Concept", size=20, weight="bold"),
            scan_btn,
            ft.Container(height=20),
            progress,
            elapsed_text
        ], horizontal_alignment="center", alignment="center", expand=True)
    )

ft.app(target=main)
