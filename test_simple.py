import flet as ft
def main(page: ft.Page):
    page.title = "Basic Test"
    page.add(ft.Text("Hello ZenClean UI!", size=50, color="blue"))
    page.update()
if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8551)
