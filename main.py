import flet as ft
import json
import os
from datetime import datetime, timedelta

# Название файла локальной базы данных
DB_FILE = "database.txt"

def get_default_car_data():
    """Шаблон структуры данных. На старте даем базовую историю для возможности прогноза."""
    current_date = datetime.now().strftime("%d.%m.%Y")
    past_date = (datetime.now() - timedelta(days=30)).strftime("%d.%m.%Y")
    return {
        "odometer": {"value": 125000, "date": current_date},
        "daily_mileage": 45,
        "odometer_history": [
            {"value": 123650, "date": past_date},  
            {"value": 125000, "date": current_date} 
        ], 
        "maintenance_data": {
            "Замена масла": {"last_service": 120000, "interval": 10000, "date": "15.01.2026"},
            "Замена ГРМ": {"last_service": 90000, "interval": 60000, "date": "10.05.2024"},
            "Фильтр салона": {"last_service": 120000, "interval": 15000, "date": "15.01.2026"},
            "Тормозная жидкость": {"last_service": 100000, "interval": 40000, "date": "20.09.2024"}
        },
        "history": []
    }

def recalculate_auto_daily_mileage(car_profile):
    """Автоматический расчет пробега в день на основе истории."""
    history = car_profile.get("odometer_history", [])
    if len(history) < 2:
        return int(car_profile.get("daily_mileage", 45))

    def parse_date(item):
        try: return datetime.strptime(item["date"], "%d.%m.%Y")
        except ValueError: return datetime.min

    sorted_hist = sorted(history, key=parse_date)
    first_point = sorted_hist[0]
    last_point = sorted_hist[-1]

    delta_km = int(last_point["value"]) - int(first_point["value"])
    delta_days = (parse_date(last_point) - parse_date(first_point)).days

    if delta_days <= 0 or delta_km <= 0:
        return int(car_profile.get("daily_mileage", 45))

    auto_run = round(delta_km / delta_days)
    return auto_run if auto_run > 0 else 45

def load_data():
    """Загрузка данных с автоматическим пересчетом суточного пробега."""
    default_structure = {
        "cars": {
            "Автомобиль 1": get_default_car_data(),
            "Автомобиль 2": get_default_car_data()
        }
    }
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(default_structure, f, ensure_ascii=False, indent=4)
        return default_structure
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for car_name, car_profile in data.get("cars", {}).items():
            car_profile["daily_mileage"] = recalculate_auto_daily_mileage(car_profile)
        return data
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
    page.theme_mode = ft.ThemeMode.LIGHT
    # Включаем автоматический скролл для всей страницы, чтобы контент не резался на маленьких экранах
    page.scroll = ft.ScrollMode.AUTO 

    def show_message(text):
        """Вывод всплывающего уведомления SnackBar."""
        snack = ft.SnackBar(ft.Text(text))
        page.overlay.append(snack)
        snack.open = True
        page.update()

    def build_tabs_ui():
        """ФУНКЦИЯ ТАБ-ОРИЕНТИРОВАННОГО ИНТЕРФЕЙСА. Перестраивает экран на основе структуры БД."""
        page.controls.clear()
        
        db_data = load_data()
        cars_dict = db_data.get("cars", {})
        
        if not cars_dict:
            db_data = load_data()
            cars_dict = db_data["cars"]

        tab_buttons = []
        tab_contents = []

        for car_name, car_profile in cars_dict.items():
            car_view_content = generate_car_view(
                page, db_data, car_name, car_profile, show_message, build_tabs_ui
            )
            
            tab_buttons.append(
                ft.Tab(
                    label=car_name,
                    icon=ft.Icons.DIRECTIONS_CAR
                )
            )
            tab_contents.append(car_view_content)

        tabs_layout = ft.Column(
            controls=[
                ft.TabBar(tabs=tab_buttons),
                ft.TabBarView(controls=tab_contents, expand=True)
            ],
            expand=True
        )

        tabs_container = ft.Tabs(
            length=len(tab_buttons),
            selected_index=0,
            animation_duration=300,
            content=tabs_layout,
            expand=True
        )
        
        page.add(tabs_container)
        page.update()

    build_tabs_ui()
def generate_car_view(page, db_data, car_name, car_profile, show_message, rebuild_callback):
    """Создает независимое визуальное содержимое для конкретной вкладки автомобиля."""
    
    current_odo_data = car_profile.get("odometer", {"value": 125000, "date": "—"})
    
    # ИСПРАВЛЕНО: Короткие labels и убран параметр expand=True для корректного отображения в Column
    current_odo_input = ft.TextField(
        label=f"Новый пробег (км) [Текущий: {current_odo_data.get('value', 125000)} от {current_odo_data.get('date', '—')}]", 
        value=str(current_odo_data.get("value", 125000)), 
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True
    )
    
    daily_input = ft.TextField(
        label="Пробег в день (Авторасчет, км)", 
        value=str(car_profile.get("daily_mileage", 45)), 
        disabled=True
    )

    def update_forecast_click(e):
        try:
            val = int(current_odo_input.value)
            now_date_str = datetime.now().strftime("%d.%m.%Y")
            
            car_profile["odometer"] = {"value": val, "date": now_date_str}
            
            if not any(h["value"] == val for h in car_profile["odometer_history"]):
                car_profile["odometer_history"].append({"value": val, "date": now_date_str})
            
            car_profile["daily_mileage"] = recalculate_auto_daily_mileage(car_profile)
            
            save_data(db_data)
            rebuild_callback()
            show_message(f"Новый пробег учтен. Прогноз обновлен!")
        except ValueError:
            show_message("Ошибка: Введите числовое значение пробега!")

    def show_odometer_history_click(e):
        def get_sort_key(item):
            try: return datetime.strptime(item["date"], "%d.%m.%Y")
            except ValueError: return datetime.min

        def refresh_and_recalc():
            if car_profile["odometer_history"]:
                last_entry = sorted(car_profile["odometer_history"], key=get_sort_key)[-1]
                car_profile["odometer"] = last_entry
            car_profile["daily_mileage"] = recalculate_auto_daily_mileage(car_profile)

        def delete_odo_entry(item_to_remove):
            car_profile["odometer_history"].remove(item_to_remove)
            refresh_and_recalc()
            save_data(db_data)
            dialog.open = False
            page.update()
            rebuild_callback()
            show_message("Запись удалена!")

        def edit_odo_entry_dialog(item_to_edit):
            val_input = ft.TextField(label="Пробег (км)", value=str(item_to_edit["value"]), keyboard_type=ft.KeyboardType.NUMBER)
            date_input = ft.TextField(label="Дата (ДД.ММ.ГГГГ)", value=str(item_to_edit["date"]))
            
            def save_row_edit(_):
                try:
                    new_val = int(val_input.value)
                    new_date = date_input.value.strip()
                    datetime.strptime(new_date, "%d.%m.%Y")
                    
                    item_to_edit["value"] = new_val
                    item_to_edit["date"] = new_date
                    
                    refresh_and_recalc()
                    save_data(db_data)
                    sub_dialog.open = False
                    dialog.open = False
                    page.update()
                    rebuild_callback()
                    show_message("История изменена!")
                except ValueError:
                    show_message("Ошибка ввода данных!")

            sub_dialog = ft.AlertDialog(
                title=ft.Text("Редактировать запись"),
                content=ft.Column([val_input, date_input], tight=True, spacing=10),
                actions=[ft.TextButton("Сохранить", on_click=save_row_edit)]
            )
            page.overlay.append(sub_dialog)
            sub_dialog.open = True
            page.update()

        sorted_history = sorted(car_profile.get("odometer_history", []), key=get_sort_key, reverse=True)
        
        history_rows = []
        for item in sorted_history:
            history_rows.append(
                ft.Row([
                    ft.Text(f"• {item['date']} — {item['value']} км", expand=True),
                    ft.Row([
                        ft.IconButton(icon=ft.Icons.EDIT_OUTLINED, icon_color=ft.Colors.BLUE_400, on_click=lambda _, idx=item: edit_odo_entry_dialog(idx)),
                        ft.IconButton(icon=ft.Icons.DELETE_OUTLINED, icon_color=ft.Colors.RED_400, on_click=lambda _, idx=item: delete_odo_entry(idx))
                    ], spacing=0)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            )

        if not history_rows:
            history_rows.append(ft.Text("История пробегов пуста."))

        dialog = ft.AlertDialog(
            title=ft.Text("История пробега"),
            content=ft.Column(controls=history_rows, tight=True, scroll=ft.ScrollMode.AUTO, height=300),
            actions=[ft.TextButton("Закрыть", on_click=lambda _: [setattr(dialog, "open", False), page.update()])]
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def add_car_click(e):
        car_name_input = ft.TextField(label="Марка / Модель / Госномер")
        def save_new_car(_):
            name = car_name_input.value.strip()
            if not name or name in db_data["cars"]: return
            db_data["cars"][name] = get_default_car_data()
            save_data(db_data)
            dialog.open = False
            page.update()
            rebuild_callback()
            
        dialog = ft.AlertDialog(
            title=ft.Text("Добавить автомобиль"),
            content=ft.Column([car_name_input], tight=True),
            actions=[ft.TextButton("Добавить", on_click=save_new_car)]
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def edit_car_name_click(e):
        edit_name_input = ft.TextField(label="Новое имя профиля", value=car_name)
        def save_name_change(_):
            new_name = edit_name_input.value.strip()
            if not new_name or new_name == car_name: return
            if new_name in db_data["cars"]:
                show_message("Автомобиль с таким именем уже существует!")
                return
            db_data["cars"][new_name] = db_data["cars"].pop(car_name)
            save_data(db_data)
            dialog.open = False
            page.update()
            rebuild_callback()
            show_message(f"Профиль переименован!")
            
        dialog = ft.AlertDialog(
            title=ft.Text("Редактировать имя"),
            content=ft.Column([edit_name_input], tight=True),
            actions=[ft.TextButton("Сохранить", on_click=save_name_change)]
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def delete_car_click(e):
        if len(db_data["cars"]) <= 1:
            show_message("Нельзя удалить единственный автомобиль!")
            return
        def confirm_delete(_):
            db_data["cars"].pop(car_name)
            save_data(db_data)
            dialog.open = False
            page.update()
            rebuild_callback()
            
        dialog = ft.AlertDialog(
            title=ft.Text("Удаление профиля"),
            content=ft.Text(f"Удалить '{car_name}'?"),
            actions=[ft.TextButton("Удалить", on_click=confirm_delete, style=ft.ButtonStyle(color=ft.Colors.RED_600))]
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    action_panel = ft.Row([
        ft.Text(f"Управление профилем:", size=14, weight=ft.FontWeight.W_500),
        ft.Row([
            ft.IconButton(icon=ft.Icons.ADD_CIRCLE, tooltip="Добавить авто", on_click=add_car_click),
            ft.IconButton(icon=ft.Icons.EDIT, tooltip="Переименовать этот авто", on_click=edit_car_name_click),
            ft.IconButton(icon=ft.Icons.DELETE_FOREVER, tooltip="Удалить это авто", on_click=delete_car_click, icon_color=ft.Colors.RED_500),
        ], spacing=5)
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    # ИСПРАВЛЕНО: Элементы ввода перестроены вертикально (ft.Column вместо ft.Row), чтобы избежать наложения на мобильных экранах
    header_card = ft.Card(
        content=ft.Container(
            content=ft.Column([
                action_panel,
                ft.Divider(height=5, color=ft.Colors.BLACK_12),
                ft.Text("Обновление данных пробега", size=16, weight=ft.FontWeight.BOLD),
                ft.Column([
                    ft.Row([
                        current_odo_input, 
                        ft.IconButton(icon=ft.Icons.MENU_BOOK, tooltip="История изменений пробега", on_click=show_odometer_history_click),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    daily_input,
                ], spacing=10),
                ft.Button("Обновить пробег и прогноз", on_click=update_forecast_click, height=50, width=400),
            ], spacing=12), padding=15
        )
    )

    return build_maintenance_list(page, db_data, car_name, car_profile, header_card, rebuild_callback, show_message)
def build_maintenance_list(page, db_data, car_name, car_profile, header_card, rebuild_callback, show_message):
    """Генерирует список ExpansionTile для регламентных работ и возвращает полную колонку интерфейса."""
    maintenance_list = ft.ListView(expand=True, spacing=10, height=400)
    
    odo_data = car_profile.get("odometer", {"value": 0, "date": ""})
    current_km = int(odo_data.get("value", 0)) if isinstance(odo_data, dict) else int(odo_data)
    daily_run = int(car_profile.get("daily_mileage", 45))

    for task, info in car_profile["maintenance_data"].items():
        target_km = info["last_service"] + info["interval"]
        remaining_km = target_km - current_km
        
        if remaining_km <= 0:
            status_text, status_color, bg_color = "Просрочено! Срочно на ТО!", ft.Colors.RED_700, ft.Colors.RED_50
        else:
            forecast_date = calculate_forecast(target_km, current_km, daily_run)
            status_text, status_color, bg_color = f"В норме. Осталось: {remaining_km} км (~{forecast_date})", ft.Colors.GREEN_700, ft.Colors.GREEN_50
            
        has_history = any(h["task"] == task for h in car_profile.get("history", []))
        last_service_text = f"Последнее ТО: {info['last_service']} км ({info['date']})" if has_history else "Последнее ТО: данных нет"

        # Локальные замыкания (Handlers)
        def make_reset_handler(t_name=task, p_profile=car_profile):
            return lambda _: [
                p_profile["maintenance_data"][t_name].update({"last_service": current_km, "date": datetime.now().strftime("%d.%m.%Y")}),
                p_profile["history"].append({"task": t_name, "odometer": current_km, "date": datetime.now().strftime("%d.%m.%Y")}),
                save_data(db_data), rebuild_callback(), show_message(f"Сервис '{t_name}' успешно сброшен!")
            ]

        def make_history_handler(t_name=task, p_profile=car_profile):
            def show_history(_):
                task_history = [h for h in p_profile.get("history", []) if h["task"] == t_name]
                
                def get_sort_key(item):
                    try: return datetime.strptime(item["date"], "%d.%m.%Y")
                    except ValueError: return datetime.min

                sorted_history = sorted(task_history, key=get_sort_key, reverse=True)
                lines = [ft.Text("История обслуживания пуста.")] if not task_history else [
                    ft.Text(f"• {item['date']} — Пробег: {item['odometer']} км") for item in sorted_history
                ]
                
                def close_dialog(_):
                    dialog.open = False
                    page.update()
                    
                dialog = ft.AlertDialog(
                    title=ft.Text(f"Журнал: {t_name}"),
                    content=ft.Column(controls=lines, tight=True, scroll=ft.ScrollMode.AUTO),
                    actions=[ft.TextButton("Закрыть", on_click=close_dialog)]
                )
                page.overlay.append(dialog)
                dialog.open = True
                page.update()
            return show_history

        def make_add_history_handler(t_name=task, p_profile=car_profile):
            def show_add_dialog(_):
                h_odo = ft.TextField(label="Пробег на момент ТО (км)", keyboard_type=ft.KeyboardType.NUMBER)
                h_date = ft.TextField(label="Дата (ДД.ММ.ГГГГ)", value=datetime.now().strftime("%d.%m.%Y"))
                
                def save_entry(_):
                    try:
                        km = int(h_odo.value)
                        date_str = h_date.value.strip()
                        datetime.strptime(date_str, "%d.%m.%Y")
                        p_profile["history"].append({"task": t_name, "odometer": km, "date": date_str})
                        
                        if km > p_profile["maintenance_data"][t_name]["last_service"]:
                            p_profile["maintenance_data"][t_name].update({"last_service": km, "date": date_str})
                            
                        save_data(db_data)
                        dialog.open = False
                        page.update()
                        rebuild_callback()
                        show_message("Запись добавлена!")
                    except ValueError: 
                        show_message("Ошибка: Проверьте пробег или формат даты (ДД.ММ.ГГГГ)!")
                        
                dialog = ft.AlertDialog(
                    title=ft.Text("Ввод истории"), 
                    content=ft.Column([h_odo, h_date], tight=True, spacing=10), 
                    actions=[ft.TextButton("Сохранить", on_click=save_entry)]
                )
                page.overlay.append(dialog)
                dialog.open = True
                page.update()
            return show_add_dialog

        def make_change_interval_handler(t_name=task, p_profile=car_profile, current_val=info["interval"]):
            def show_int_dialog(_):
                int_input = ft.TextField(label="Новый интервал (км)", value=str(current_val), keyboard_type=ft.KeyboardType.NUMBER)
                
                def save_int(_):
                    try:
                        new_val = int(int_input.value)
                        if new_val <= 0: return
                        p_profile["maintenance_data"][t_name]["interval"] = new_val
                        save_data(db_data)
                        dialog.open = False
                        page.update()
                        rebuild_callback()
                        show_message("Интервал изменен!")
                    except ValueError: 
                        show_message("Введите число!")
                        
                dialog = ft.AlertDialog(
                    title=ft.Text("Регламент"), 
                    content=ft.Column([int_input], tight=True), 
                    actions=[ft.TextButton("Сохранить", on_click=save_int)]
                )
                page.overlay.append(dialog)
                dialog.open = True
                page.update()
            return show_int_dialog

        expansion_tile = ft.ExpansionTile(
            title=ft.Text(task, size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_900),
            subtitle=ft.Text(status_text, size=12, color=status_color, weight=ft.FontWeight.W_500),
            bgcolor=bg_color, collapsed_bgcolor=bg_color,
            shape=ft.RoundedRectangleBorder(radius=10), collapsed_shape=ft.RoundedRectangleBorder(radius=10),
            controls=[
                ft.Container(
                    content=ft.Column([
                        ft.Divider(height=1, color=ft.Colors.BLACK_12),
                        ft.Row([
                            ft.IconButton(icon=ft.Icons.MENU_BOOK, on_click=make_history_handler()),
                            ft.Button("Ввод истории", on_click=make_add_history_handler()),
                            ft.Button("Регламент", on_click=make_change_interval_handler(), icon=ft.Icons.EDIT),
                            ft.OutlinedButton("Сброс ТО", on_click=make_reset_handler(), style=ft.ButtonStyle(color=ft.Colors.RED_600)),
                        ], wrap=True, alignment=ft.MainAxisAlignment.START, spacing=10),
                        ft.Text(f"{last_service_text} | Регламент: {info['interval']} км", size=12, color=ft.Colors.GREY_700),
                    ], spacing=10), padding=ft.Padding(left=15, right=15, top=0, bottom=15)
                )
            ]
        )
        maintenance_list.controls.append(expansion_tile)

    return ft.Column([
        header_card,
        ft.Container(height=5),
        ft.Text("Статус регламентных работ", size=18, weight=ft.FontWeight.BOLD),
        maintenance_list
    ], scroll=ft.ScrollMode.AUTO, expand=True)

if __name__ == "__main__":
    ft.run(main)
