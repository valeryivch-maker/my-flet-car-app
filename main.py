import flet as ft
import json
import os
from datetime import datetime, timedelta

# Название файла локальной базы данных
DB_FILE = "database.txt"

def get_default_car_data():
    """Шаблон структуры данных для каждого нового автомобиля в гараже."""
    return {
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

def load_data():
    """Загрузка данных. Поддерживает структуру изолированных профилей машин."""
    default_structure = {
        "current_car": "Мой Автомобиль 1",
        "cars": {
            "Мой Автомобиль 1": get_default_car_data()
        }
    }
    
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(default_structure, f, ensure_ascii=False, indent=4)
        return default_structure
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            if "cars" not in loaded:
                return default_structure
            return loaded
    except Exception:
        return default_structure

def save_data(data):
    """Сохранение текущего состояния мультигаража в файл."""
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
    
    # Загружаем мульти-автомобильные данные
    global_data = load_data()

    # Ссылка на текущий активный профиль машины
    def get_current_car_profile():
        current_car_name = global_data["current_car"]
        return global_data["cars"][current_car_name]

    # Поля ввода верхнего блока
    prev_odo_input = ft.TextField(label="Предыдущий километраж (км)", disabled=True, expand=True)
    current_odo_input = ft.TextField(label="Текущий километраж (км)", keyboard_type=ft.KeyboardType.NUMBER, expand=True)
    daily_input = ft.TextField(label="Пробег в день (км)", keyboard_type=ft.KeyboardType.NUMBER, expand=True)

    # Компоненты выбора автомобиля
    car_dropdown = ft.Dropdown(label="Выбранный автомобиль", expand=True)
    maintenance_list = ft.Column(spacing=10)

    def show_message(text):
        snack = ft.SnackBar(ft.Text(text))
        page.overlay.append(snack)
        snack.open = True
        page.update()

    def load_car_inputs():
        """Заполнение полей ввода данными выбранной машины."""
        car_profile = get_current_car_profile()
        prev_odo_input.value = str(car_profile.get("prev_odometer", 125000))
        current_odo_input.value = str(car_profile["odometer"])
        daily_input.value = str(car_profile["daily_mileage"])
        page.update()

    def update_car_dropdown_options():
        """Обновление списка автомобилей в Dropdown."""
        car_dropdown.options = [ft.dropdown.Option(name) for name in global_data["cars"].keys()]
        car_dropdown.value = global_data["current_car"]
        page.update()

    def on_car_changed(e):
        """Переключение на другой автомобиль."""
        global_data["current_car"] = car_dropdown.value
        save_data(global_data)
        load_car_inputs()
        rebuild_maintenance_list()

    car_dropdown.on_change = on_car_changed

    def rebuild_maintenance_list():
        """Пересборка списка ТО для выбранного автомобиля."""
        maintenance_list.controls.clear()
        car_profile = get_current_car_profile()
        
        current_km = int(current_odo_input.value or 0)
        daily_run = int(daily_input.value or 0)

        for task, info in car_profile["maintenance_data"].items():
            target_km = info["last_service"] + info["interval"]
            remaining_km = target_km - current_km
            
            if remaining_km <= 0:
                status_text = "Просрочено! Срочно на ТО!"
                status_color = ft.Colors.RED_700
                bg_color = ft.Colors.RED_50
            else:
                forecast_date = calculate_forecast(target_km, current_km, daily_run)
                status_text = f"В норме. Осталось: {remaining_km} км (~{forecast_date})"
                status_color = ft.Colors.GREEN_700
                bg_color = ft.Colors.GREEN_50

            def make_reset_handler(t_name=task):
                return lambda e: reset_task(t_name)

            def make_show_history_handler(t_name=task):
                return lambda e: show_history(t_name)

            def make_add_history_handler(t_name=task):
                return lambda e: show_add_history_dialog(t_name)

            def make_change_interval_handler(t_name=task, current_val=info["interval"]):
                return lambda e: show_change_interval_dialog(t_name, current_val)

            # Проверка истории обслуживания для скрытия демо-данных
            has_history = any(h["task"] == task for h in car_profile.get("history", []))
            if has_history:
                last_service_text = f"Последнее ТО: {info['last_service']} км ({info['date']})"
            else:
                last_service_text = "Последнее ТО: данных нет"

            expansion_tile = ft.ExpansionTile(
                title=ft.Text(task, size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_900),
                subtitle=ft.Text(status_text, size=12, color=status_color, weight=ft.FontWeight.W_500),
                bgcolor=bg_color,
                collapsed_bgcolor=bg_color,
                shape=ft.RoundedRectangleBorder(radius=10),
                collapsed_shape=ft.RoundedRectangleBorder(radius=10),
                controls=[
                    ft.Container(
                        content=ft.Column([
                            ft.Divider(height=1, color=ft.Colors.BLACK_12),
                            
                            # Адаптивная строка кнопок управления
                            ft.Row([
                                ft.IconButton(icon=ft.Icons.MENU_BOOK, tooltip="Просмотр журнала", on_click=make_show_history_handler()),
                                ft.Button("Ввод истории", on_click=make_add_history_handler()),
                                ft.Button("Регламент", on_click=make_change_interval_handler(), icon=ft.Icons.EDIT),
                                ft.OutlinedButton("Сброс ТО", on_click=make_reset_handler(), style=ft.ButtonStyle(color=ft.Colors.RED_600)),
                            ], wrap=True, alignment=ft.MainAxisAlignment.START, spacing=10),
                            
                            ft.Text(
                                f"{last_service_text} | Регламент: {info['interval']} км", 
                                size=12, color=ft.Colors.GREY_700
                            ),
                        ], spacing=10),
                        padding=ft.Padding(left=15, right=15, top=0, bottom=15)
                    )
                ]
            )
            maintenance_list.controls.append(expansion_tile)
        page.update()



    def show_change_interval_dialog(task_name, current_interval):
        """Всплывающее окно для ручного изменения регламентного интервала детали."""
        interval_input = ft.TextField(
            label="Новый интервал обслуживания (км)", 
            value=str(current_interval),
            keyboard_type=ft.KeyboardType.NUMBER
        )

        def close_dialog(e):
            dialog.open = False
            page.update()

        def save_new_interval(e):
            try:
                new_val = int(interval_input.value)
                if new_val <= 0:
                    show_message("Интервал должен быть больше нуля!")
                    return
                
                car_profile = get_current_car_profile()
                car_profile["maintenance_data"][task_name]["interval"] = new_val
                save_data(global_data)
                
                dialog.open = False
                rebuild_maintenance_list()
                show_message(f"Интервал для '{task_name}' успешно изменен на {new_val} км!")
            except ValueError:
                show_message("Введите корректное число!")

        dialog = ft.AlertDialog(
            title=ft.Text(f"Настройка регламента: {task_name}"),
            content=ft.Column([interval_input], tight=True),
            actions=[
                ft.TextButton("Отмена", on_click=close_dialog),
                ft.Button("Сохранить", on_click=save_new_interval)
            ]
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def update_forecast_click(e):
        try:
            car_profile = get_current_car_profile()
            car_profile["prev_odometer"] = car_profile["odometer"]
            car_profile["odometer"] = int(current_odo_input.value)
            car_profile["daily_mileage"] = int(daily_input.value)
            save_data(global_data)
            prev_odo_input.value = str(car_profile["prev_odometer"])
            rebuild_maintenance_list()
            show_message("Данные успешно сохранены и пересчитаны!")
        except ValueError:
            show_message("Ошибка: Введите корректные числовые значения!")

    def reset_task(task_name):
        car_profile = get_current_car_profile()
        current_km = int(current_odo_input.value or 0)
        today_str = datetime.now().strftime("%d.%m.%Y")
        
        car_profile["maintenance_data"][task_name]["last_service"] = current_km
        car_profile["maintenance_data"][task_name]["date"] = today_str
        car_profile["history"].append({"task": task_name, "odometer": current_km, "date": today_str})
        
        save_data(global_data)
        rebuild_maintenance_list()
        show_message(f"Сервис '{task_name}' сброшен!")

    def show_add_history_dialog(task_name):
        history_odo = ft.TextField(label="Пробег на момент ТО (км)", keyboard_type=ft.KeyboardType.NUMBER)
        history_date = ft.TextField(label="Дата (ДД.ММ.ГГГГ)", value=datetime.now().strftime("%d.%m.%Y"))

        def close_dialog(e):
            dialog.open = False
            page.update()

        def save_history_entry(e):
            try:
                car_profile = get_current_car_profile()
                km = int(history_odo.value)
                date_str = history_date.value
                
                car_profile["history"].append({"task": task_name, "odometer": km, "date": date_str})
                if km > car_profile["maintenance_data"][task_name]["last_service"]:
                    car_profile["maintenance_data"][task_name]["last_service"] = km
                    car_profile["maintenance_data"][task_name]["date"] = date_str

                save_data(global_data)
                dialog.open = False
                rebuild_maintenance_list()
                show_message("Историческая запись успешно добавлена!")
            except ValueError:
                show_message("Заполните пробег корректным числом!")

        dialog = ft.AlertDialog(
            title=ft.Text(f"Добавить прошлые ТО: {task_name}"),
            content=ft.Column([history_odo, history_date], tight=True, spacing=10),
            actions=[ft.TextButton("Отмена", on_click=close_dialog), ft.Button("Сохранить", on_click=save_history_entry)]
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def show_history(task_name):
        car_profile = get_current_car_profile()
        task_history = [h for h in car_profile.get("history", []) if h["task"] == task_name]
        
        history_lines = []
        if not task_history:
            history_lines.append(ft.Text("История обслуживания пуста."))
        else:
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

    def show_add_car_dialog(e):
        car_name_input = ft.TextField(label="Марка / Модель автомобиля / Госномер")

        def close_dialog(e):
            dialog.open = False
            page.update()

        def save_new_car(e):
            name = car_name_input.value.strip()
            if not name:
                show_message("Имя автомобиля не может быть пустым!")
                return
            if name in global_data["cars"]:
                show_message("Такой автомобиль уже добавлен!")
                return
            
            global_data["cars"][name] = get_default_car_data()
            global_data["current_car"] = name
            save_data(global_data)
            
            dialog.open = False
            update_car_dropdown_options()
            load_car_inputs()
            rebuild_maintenance_list()
            show_message(f"Автомобиль '{name}' успешно добавлен!")

        dialog = ft.AlertDialog(
            title=ft.Text("Добавить автомобиль"),
            content=ft.Column([car_name_input], tight=True),
            actions=[ft.TextButton("Отмена", on_click=close_dialog), ft.Button("Добавить", on_click=save_new_car)]
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    # Панель гаража (Dropdown + кнопка плюс)
    garage_panel = ft.Row([
        car_dropdown,
        ft.IconButton(icon=ft.Icons.ADD_CIRCLE, tooltip="Добавить автомобиль", on_click=show_add_car_dialog, icon_size=36)
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    # Сборка интерфейса верхнего блока
    header_card = ft.Card(
        content=ft.Container(
            content=ft.Column([
                ft.Text("Гараж", size=18, weight=ft.FontWeight.BOLD),
                garage_panel,
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                ft.Text("Обновление данных пробега", size=16, weight=ft.FontWeight.BOLD),
                ft.Row([prev_odo_input, current_odo_input]),
                ft.Row([
                    daily_input,
                    ft.Button("Рассчитать прогноз ТО", on_click=update_forecast_click, height=50)
                ]),
            ], spacing=12),
            padding=15
        )
    )

    # Добавление на экран
    page.add(
        header_card,
        ft.Container(height=10),
        ft.Text("Статус регламентных работ", size=20, weight=ft.FontWeight.BOLD),
        maintenance_list
    )

    # Инициализация интерфейса
    update_car_dropdown_options()
    load_car_inputs()
    rebuild_maintenance_list()

if __name__ == "__main__":
    ft.run(main)
