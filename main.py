import flet as ft
import sys
import os

def main(page: ft.Page):
    page.title = "Тест лога"
    page.bgcolor = ft.Colors.WHITE
    
    # Пытаемся прочитать лог
    try:
        # Путь к логу в песочнице Android
        log_path = os.environ.get("FLET_APP_CONSOLE", "out.log")
        with open(log_path, "r") as f:
            log_content = f.read()
    except Exception as e:
        log_content = f"Не удалось прочитать лог: {e}"
    
    page.add(
        ft.Text("ЛОГ ПРИЛОЖЕНИЯ:", size=20, weight=ft.FontWeight.BOLD),
        ft.Text(log_content, selectable=True, size=12)
    )

if __name__ == "__main__":
    ft.app(target=main)