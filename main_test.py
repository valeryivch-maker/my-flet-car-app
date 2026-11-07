import flet as ft


def main(page: ft.Page):
    page.title = "Test"
    page.bgcolor = ft.Colors.WHITE
    page.add(
        ft.Column(
            [
                ft.Text("Python OK", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN),
                ft.Text("Flet works!", size=20),
                ft.Text("Если видишь этот текст — Python и Flet живы.", size=14),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
    )


ft.app(target=main)