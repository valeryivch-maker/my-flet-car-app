import flet as ft
from datetime import datetime, timedelta
import json
import os

# Имя файла для хранения данных на диске
DB_FILE = "database.txt"

# --- ФУНКЦИИ РАБОТЫ С БАЗОЙ ДАННЫХ (ФАЙЛ) ---
def load_data():
    """Загружает данные из файла. Если файла нет, возвращает дефолтные значения."""
    default_data = {
        "odometer": 125000,
        "daily_mileage": 45,
        "maintenance_data": {
            "oil": {"current": 120000, "interval": 10000, "name": "Замена масла"},
            "grm": {"current": 90000, "interval": 60000, "name": "Замена ГРМ"},
            "antifreeze": {"current": 100000, "interval": 40000, "name": "Замена тосола"},
            "brake": {"current": 110000, "interval": 30000, "name": "Тормозная жидкость"}
        }
    }
    if not os.path.exists(DB_FILE):
        return default_data
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default_data

def save_all_data(odo, daily, maint_data):
    """Сохраняет все текущие показатели в текстовый файл json-строкой."""
    data_to_save = {
        "odometer": odo,
        "daily_mileage": daily,
        "maintenance_data": maint_data
    }
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, ensure_ascii=False, indent=4)


def main(page: ft.Page):
    # Настройки окна (Имитируем экран смартфона)
    page.title = "Авто-Трекер ТО"
    page.window_width = 450
    page.window_height = 750
    page.scroll = "adaptive"
    page.theme_mode = ft.ThemeMode.LIGHT

    # Загружаем сохраненное состояние из файла
    app_data = load_data()
    maintenance_data = app_data["maintenance_data"]

    # --- КОМПОНЕНТЫ ИНТЕРФЕЙСА (Поля ввода) ---
    odo_input = ft.TextField(
        label="Текущий километраж (км)", 
        value=str(app_data["odometer"]), 
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True
    )
    daily_input = ft.TextField(
        label="Пробег в день (км)", 
        value=str(app_data["daily_mileage"]), 
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True
    )

    # Контейнер, куда мы будем динамически выводить карточки регламента
    cards_container = ft.Column(spacing=15)

    # --- ФУНКЦИЯ ДЛЯ СБРОСА ТО (КНОПКА «ВЫПОЛНЕНО») ---
    def reset_maintenance_item(key):
        try:
            current_odo = int(odo_input.value or 0)
            daily_km = int(daily_input.value or 1)
        except ValueError:
            current_odo = app_data["odometer"]
            daily_km = app_data["daily_mileage"]
            
        # Приравниваем пробег последней замены к текущему одометру
        maintenance_data[key]["current"] = current_odo
        
        # Записываем изменения в файл базы данных
        save_all_data(current_odo, daily_km, maintenance_data)
        
        # Пересчитываем и обновляем экран
        update_dashboard()
        
        page.snack_bar = ft.SnackBar(ft.Text(f"Статус {maintenance_data[key]['name']} успешно обновлен!"), open=True)
        page.update()

    # --- ЛОГИКА РАСЧЕТА И ЦВЕТОВЫХ ПРЕДУПРЕЖДЕНИЙ ---
    def update_dashboard():
        cards_container.controls.clear()
        
        try:
            current_odo = int(odo_input.value or 0)
            daily_km = int(daily_input.value or 1)
        except ValueError:
            current_odo = app_data["odometer"]
            daily_km = app_data["daily_mileage"]

        if daily_km <= 0:
            daily_km = 1  # Защита от деления на ноль

        for key, item in maintenance_data.items():
            # Расчет пробега, когда нужно сделать ТО
            target_odo = item["current"] + item["interval"]
            # Сколько километров осталось до критической точки
            km_left = target_odo - current_odo
            # Прогноз дней до ТО
            days_left = km_left / daily_km
            predicted_date = datetime.now() + timedelta(days=days_left)
            date_str = predicted_date.strftime("%d.%m.%Y")

            # Логика алертов
            if km_left <= 0:
                status_text = f"[ СРОЧНО ] Просрочено на {abs(km_left)} км!"
                status_color = "red700"
                bg_color = "red50"
            elif days_left <= 14:
                status_text = f"[ ! ] ВНИМАНИЕ: осталось {km_left} км ({int(days_left)} дн.)"
                status_color = "orange700"
                bg_color = "orange50"
            else:
                status_text = f"В норме. Осталось: {km_left} км (~{date_str})"
                status_color = "green700"
                bg_color = "green50"

            # Лямбда-функция для изоляции ключа запчасти в обработчике клика
            def make_click_handler(k=key):
                return lambda e: reset_maintenance_item(k)

            # Создаем красивую карточку для каждого типа работы
            card = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(item["name"], size=18, weight=ft.FontWeight.BOLD, expand=True),
                        # Используем новый универсальный ft.Button с явным указанием цвета текста
                        ft.Button(
                            "СБРОС ТО",
                            color=status_color,
                            on_click=make_click_handler()
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Text(f"Последняя замена: {item['current']} км | Интервал: {item['interval']} км", size=12, color="grey700"),
                    ft.Container(height=5),
                    ft.Text(status_text, color=status_color, weight=ft.FontWeight.W_600)
                ]),
                padding=12,
                border_radius=10,
                bgcolor=bg_color,
                border=ft.Border(
                    top=ft.BorderSide(1, status_color),
                    bottom=ft.BorderSide(1, status_color),
                    left=ft.BorderSide(1, status_color),
                    right=ft.BorderSide(1, status_color)
                )
            )
            cards_container.controls.append(card)
        
        page.update()

    # --- ОБРАБОТЧИК НАЖАТИЯ ГЛАВНОЙ КНОПКИ ---
    def on_save_click(e):
        try:
            c_odo = int(odo_input.value or 0)
            c_daily = int(daily_input.value or 1)
        except ValueError:
            return

        # ЗАПИСЫВАЕМ ДАННЫЕ В ФАЙЛ НА ДИСК
        save_all_data(c_odo, c_daily, maintenance_data)

        update_dashboard()
        page.snack_bar = ft.SnackBar(ft.Text("Все изменения сохранены в файл!"), open=True)
        page.update()

    # Базовая кнопка ft.Button без специфических флагов скругления
    save_button = ft.Button(
        "Рассчитать прогноз ТО", 
        on_click=on_save_click
    )

    # --- СБОРКА ГЛАВНОГО ЭКРАНА ---
    page.add(
        ft.AppBar(
            title=ft.Text("Бортовой журнал ТО", color="white"),
            bgcolor="blue600",
            center_title=True
        ),
        ft.Container(
            content=ft.Column([
                ft.Text("Обновление данных", size=16, weight=ft.FontWeight.W_600),
                ft.Row([odo_input, daily_input], spacing=10),
                ft.Row([save_button], alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(height=30),
                ft.Text("Статус регламентных работ", size=16, weight=ft.FontWeight.W_600),
                cards_container
            ]),
            padding=15
        )
    )

    # Первичный расчет при запуске
    update_dashboard()

# Официальный метод запуска современных версий Flet
ft.run(main)
