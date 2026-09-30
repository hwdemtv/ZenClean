import flet as ft
def main(page: ft.Page):
    def on_window_event(e):
        print(f"window_event: {e.data}")
    page.on_window_event = on_window_event
    page.add(ft.Text("Drag and drop file here"))

ft.app(target=main)
