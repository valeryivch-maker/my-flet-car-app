import flet as ft

def main(page: ft.Page):
    page.title = "Тест"
    page.bgcolor = ft.Colors.WHITE
    page.add(
        ft.Text("ПРИВЕТ! ЭТО ТЕСТ", size=30, color=ft.Colors.BLACK),
        ft.Text("Если вы это видите — Flutter работает.", size=16, color=ft.Colors.GREEN)
    )

if __name__ == "__main__":
    ft.app(target=main)