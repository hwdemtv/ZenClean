import flet as ft
def main(page: ft.Page):
    page.add(ft.Text("Hello World"))
if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8558)
