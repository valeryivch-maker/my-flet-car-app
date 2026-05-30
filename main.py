import flet as ft
import json
import os
from datetime import datetime, timedelta

# Название файла локальной базы данных
DB_FILE = "database.txt"

def load_data():
    """Загрузка данных из JSON. Если файла нет, создаем структуру по умолчанию."""
    default_data = {
        "odometer": 125000,
        "prev_odometer": 125000,
        "daily_mileage": 45,
        "maintenance_data": {
            "Замена масла": {"last_service": 120000, "interval": 10000, "date": "15.01.2026"},
            "Замена ГРМ": {"last_service": 90000, "interval": 60000, "date": "10.05.2024"},
            "Фильтр салона": {"last_service": 120000, "interval": 15000, "date": "15.01.2026"},
            "Тормозная жидкость": {"last_service": 100000, "interval": 40000, "date": "20.09.2024"}
        },
        "history": []
    }
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(default_data, f, ensure_ascii=False, indent=4)
        return default_data
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default_data

def save_data(data):
    """Сохранение текущего состояния в файл."""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def calculate_forecast(target_km, current_km, daily_run):
    """Расчет ориентировочной даты наступления события."""
    if target_km <= current_km:
        return "Срочно ТО!"
    if daily_run <= 0:
        return "Укажите пробег в день"
    days_left = (target_km - current_km) / daily_run
    future_date = datetime.now() + timedelta(days=int(days_left))
    return future_date.strftime("%d.%m.%Y")
def main(page: ft.Page):
    page.title = "Журнал ТО автомобиля"
    page.scroll = ft.ScrollMode.AUTO
    page.theme_mode = ft.ThemeMode.LIGHT
    
    # Загружаем сохраненные данные
    data = load_data()

    # Поля ввода верхнего блока
    prev_odo_input = ft.TextField(
        label="Предыдущий километраж (км)", 
        value=str(data.get("prev_odometer", 125000)), 
        disabled=True, 
        expand=True
    )
    current_odo_input = ft.TextField(
        label="Текущий километраж (км)", 
        value=str(data["odometer"]), 
        keyboard_type=ft.KeyboardType.NUMBER, 
        expand=True
    )
    daily_input = ft.TextField(
        label="Пробег в день (км)", 
        value=str(data["daily_mileage"]), 
        keyboard_type=ft.KeyboardType.NUMBER, 
        expand=True
    )

    # Контейнер для списка регламентных работ
    maintenance_list = ft.Column(spacing=15)

    def show_message(text):
        """Универсальная функция вывода уведомлений под стандарты Flet 1.0"""
        snack = ft.SnackBar(ft.Text(text))
        page.overlay.append(snack)
        snack.open = True
        page.update()

    def rebuild_maintenance_list():
        """Пересборка списка ТО с исправленной адаптивной версткой под экран телефона."""
        maintenance_list.controls.clear()
        
        current_km = int(current_odo_input.value or 0)
        daily_run = int(daily_input.value or 0)

        for task, info in data["maintenance_data"].items():
            target_km = info["last_service"] + info["interval"]
            remaining_km = target_km - current_km
            
            # Расчет прогноза даты и выбор цветов
            if remaining_km <= 0:
                status_text = "Просрочено! Срочно на ТО!"
                status_color = ft.Colors.RED_700
                bg_color = ft.Colors.RED_50
                border_color = ft.Colors.RED_400
            else:
                forecast_date = calculate_forecast(target_km, current_km, daily_run)
                status_text = f"В норме. Осталось: {remaining_km} км (~{forecast_date})"
                status_color = ft.Colors.GREEN_700
                bg_color = ft.Colors.GREEN_50
                border_color = ft.Colors.GREEN_400

            # Замыкания для обработчиков кнопок
            def make_reset_handler(t_name=task):
                return lambda e: reset_task(t_name)

            def make_show_history_handler(t_name=task):
                return lambda e: show_history(t_name)

            def make_add_history_handler(t_name=task):
                return lambda e: show_add_history_dialog(t_name)

            # Карточка регламента: Текст строго сверху, кнопки строго снизу
            card = ft.Container(
                content=ft.Column([
                    # Название работы теперь на всю ширину экрана и не сжимается
                    ft.Text(task, size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_900),
                    ft.Divider(height=1, color=ft.Colors.BLACK_12),
                    
                    # Строка кнопок с автоматическим переносом строк (wrap=True)
                    ft.Row([
                        ft.IconButton(icon=ft.Icons.MENU_BOOK, tooltip="Просмотр журнала", on_click=make_show_history_handler()),
                        ft.Button("Ввод истории", on_click=make_add_history_handler()),
                        ft.OutlinedButton("Сброс ТО", on_click=make_reset_handler(), style=ft.ButtonStyle(color=ft.Colors.RED_600)),
                    ], wrap=True, alignment=ft.MainAxisAlignment.START, spacing=10),
                    
                    # Информационный блок под кнопками
                    ft.Text(
                        f"Последнее ТО: {info['last_service']} км ({info['date']}) | Регламент: {info['interval']} км", 
                        size=12, 
                        color=ft.Colors.GREY_700
                    ),
                    ft.Text(status_text, size=14, weight=ft.FontWeight.W_500, color=status_color),
                ], spacing=8),
                padding=15,
                border=ft.Border.all(1, border_color),
                border_radius=10,
                bgcolor=bg_color
            )
            maintenance_list.controls.append(card)
        page.update()

    def update_forecast_click(e):
        """Обработка клика по кнопке рассчитать прогноз."""
        try:
            data["prev_odometer"] = data["odometer"]
            data["odometer"] = int(current_odo_input.value)
            data["daily_mileage"] = int(daily_input.value)
            save_data(data)
            prev_odo_input.value = str(data["prev_odometer"])
            rebuild_maintenance_list()
            show_message("Данные успешно сохранены и пересчитаны!")
        except ValueError:
            show_message("Ошибка: Введите корректные числовые значения!")

    def reset_task(task_name):
        """Быстрый сброс пробега на текущий километраж."""
        current_km = int(current_odo_input.value or 0)
        today_str = datetime.now().strftime("%d.%m.%Y")
        
        data["maintenance_data"][task_name]["last_service"] = current_km
        data["maintenance_data"][task_name]["date"] = today_str
        
        data["history"].append({
            "task": task_name,
            "odometer": current_km,
            "date": today_str
        })
        save_data(data)
        rebuild_maintenance_list()
        show_message(f"Сервис '{task_name}' сброшен на текущий пробег!")

    def show_add_history_dialog(task_name):
        """Окно Ввода истории (ячейки для ручного добавления прошлых ТО)."""
        history_odo = ft.TextField(label="Пробег на момент ТО (км)", keyboard_type=ft.KeyboardType.NUMBER)
        history_date = ft.TextField(label="Дата (ДД.ММ.ГГГГ)", value=datetime.now().strftime("%d.%m.%Y"))

        def close_dialog(e):
            dialog.open = False
            page.update()

        def save_history_entry(e):
            try:
                km = int(history_odo.value)
                date_str = history_date.value
                
                # Добавляем запись в общую историю обслуживания автомобиля
                data["history"].append({
                    "task": task_name,
                    "odometer": km,
                    "date": date_str
                })
                
                # Если эта запись новее последнего сохраненного ТО, обновляем карточку
                if km > data["maintenance_data"][task_name]["last_service"]:
                    data["maintenance_data"][task_name]["last_service"] = km
                    data["maintenance_data"][task_name]["date"] = date_str

                save_data(data)
                dialog.open = False
                rebuild_maintenance_list()
                show_message("Историческая запись успешно добавлена!")
            except ValueError:
                show_message("Заполните пробег корректным числом!")

        dialog = ft.AlertDialog(
            title=ft.Text(f"Добавить прошлые ТО: {task_name}"),
            content=ft.Column([
                ft.Text("Введите данные обслуживания до установки программы:"),
                history_odo,
                history_date
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton("Отмена", on_click=close_dialog),
                ft.Button("Сохранить", on_click=save_history_entry)
            ]
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def show_history(task_name):
        """Окно просмотра журнала обслуживания."""
        task_history = [h for h in data.get("history", []) if h["task"] == task_name]
        
        history_lines = []
        if not task_history:
            history_lines.append(ft.Text("История обслуживания пуста."))
        else:
            # Сортируем записи по убыванию пробега
            sorted_history = sorted(task_history, key=lambda x: x["odometer"], reverse=True)
            for item in sorted_history:
                history_lines.append(ft.Text(f"• {item['date']} — Пробег: {item['odometer']} км"))

        def close_dialog(e):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            title=ft.Text(f"Журнал: {task_name}"),
            content=ft.Column(controls=history_lines, tight=True, scroll=ft.ScrollMode.AUTO),
            actions=[ft.TextButton("Закрыть", on_click=close_dialog)]
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    # Сборка интерфейса верхнего блока
    header_card = ft.Card(
        content=ft.Container(
            content=ft.Column([
                ft.Text("Обновление данных пробега", size=18, weight=ft.FontWeight.BOLD),
                ft.Row([prev_odo_input, current_odo_input]),
                ft.Row([
                    daily_input,
                    ft.Button("Рассчитать прогноз ТО", on_click=update_forecast_click, height=50)
                ]),
            ], spacing=12),
            padding=15
        )
    )

    # Добавление элементов на экран
    page.add(
        header_card,
        ft.Container(height=10),
        ft.Text("Статус регламентных работ", size=20, weight=ft.FontWeight.BOLD),
        maintenance_list
    )

    # Первичный рендеринг списка
    rebuild_maintenance_list()

if __name__ == "__main__":
    ft.run(main)
