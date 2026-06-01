import flet as ft
import json
import os
from datetime import datetime, timedelta

# Название файла локальной базы данных
DB_FILE = "database.txt"

def get_default_car_data():
    """Шаблон структуры данных с новыми профессиональными пунктами регламента ТО."""
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
            "Замена масла + фильтры (масляный, воздушный, салонный)": {"last_service": 120000, "interval": 10000, "date": current_date},
            "Замена ГРМ (ремень, помпа, натяжной ролик)": {"last_service": 90000, "interval": 60000, "date": current_date},
            "Замена охлаждающей жидкости (Тосол/Антифриз)": {"last_service": 100000, "interval": 50000, "date": current_date},
            "Тормозная жидкость": {"last_service": 100000, "interval": 40000, "date": current_date},
            "Обслуживание кондиционера": {"last_service": 110000, "interval": 30000, "date": current_date},
            "Жидкость гидроусилителя руля (ГУР)": {"last_service": 100000, "interval": 40000, "date": current_date},
            "Промывка форсунок": {"last_service": 110000, "interval": 30000, "date": current_date}
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
    """Загрузка данных с принудительной автоматической миграцией на новую сетку регламентов ТО."""
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
            
        # Интеллектуальное обновление регламентов для уже созданных машин у пользователя
        fresh_blueprint = get_default_car_data()["maintenance_data"]
        db_updated = False
        
        for car_name, car_profile in data.get("cars", {}).items():
            if "daily_mileage" not in car_profile:
                car_profile["daily_mileage"] = recalculate_auto_daily_mileage(car_profile)
                db_updated = True
                
            # Проверяем старые пункты и заменяем их на новые расширенные
            old_data = car_profile.get("maintenance_data", {})
            new_data = {}
            
            # Переносим историю старого масла на объединенный пункт
            oil_src = old_data.get("Замена масла", old_data.get("Замена масла + фильтры (масляный, воздушный, салонный)", fresh_blueprint["Замена масла + фильтры (масляный, воздушный, салонный)"]))
            new_data["Замена масла + фильтры (масляный, воздушный, салонный)"] = oil_src
            
            # Переносим ГРМ
            grm_src = old_data.get("Замена ГРМ", old_data.get("Замена ГРМ (ремень, помпа, натяжной ролик)", fresh_blueprint["Замена ГРМ (ремень, помпа, натяжной ролик)"]))
            new_data["Замена ГРМ (ремень, помпа, натяжной ролик)"] = grm_src
            
            # Наполняем остальные новые разделы, если их еще не было в базе пользователя
            for key, blueprint_val in fresh_blueprint.items():
                if key not in new_data:
                    new_data[key] = old_data.get(key, blueprint_val)
            
            car_profile["maintenance_data"] = new_data
            db_updated = True
            
        if db_updated:
            save_data(data)
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
            tab_buttons.append(ft.Tab(label=car_name, icon=ft.Icons.DIRECTIONS_CAR))
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
    
    current_odo_input = ft.TextField(
        label=f"Пробег (км) [от {current_odo_data.get('date', '—')}]", 
        value=str(current_odo_data.get("value", 125000)), 
        keyboard_type=ft.KeyboardType.NUMBER, expand=True
    )
    daily_input = ft.TextField(
        label="Пробег в день (км)", 
        value=str(car_profile.get("daily_mileage", 45)), 
        keyboard_type=ft.KeyboardType.NUMBER, expand=True
    )

    def update_forecast_click(e):
        try:
            val = int(current_odo_input.value)
            now_date_str = datetime.now().strftime("%d.%m.%Y")
            car_profile["odometer"] = {"value": val, "date": now_date_str}
            car_profile["daily_mileage"] = int(daily_input.value)
            
            if not any(h["value"] == val for h in car_profile["odometer_history"]):
                car_profile["odometer_history"].append({"value": val, "date": now_date_str})
            
            save_data(db_data)
            rebuild_callback()
            show_message(f"Данные успешно обновлены!")
        except ValueError:
            show_message("Ошибка: Введите числовые значения пробега!")

    def add_car_click(e):
        car_name_input = ft.TextField(label="Марка / Модель / Госномер")
        def save_new_car(_):
            name = car_name_input.value.strip()
            if not name or name in db_data["cars"]: return
            db_data["cars"][name] = get_default_car_data()
            save_data(db_data); dialog.open = False; page.update(); rebuild_callback()
        dialog = ft.AlertDialog(title=ft.Text("Добавить автомобиль"), content=ft.Column([car_name_input], tight=True), actions=[ft.TextButton("Добавить", on_click=save_new_car)])
        page.overlay.append(dialog); dialog.open = True; page.update()

    def edit_car_name_click(e):
        edit_name_input = ft.TextField(label="Новое имя профиля", value=car_name)
        def save_name_change(_):
            new_name = edit_name_input.value.strip()
            if not new_name or new_name == car_name: return
            if new_name in db_data["cars"]: return
            db_data["cars"][new_name] = db_data["cars"].pop(car_name)
            save_data(db_data); dialog.open = False; page.update(); rebuild_callback()
        dialog = ft.AlertDialog(title=ft.Text("Редактировать имя"), content=ft.Column([edit_name_input], tight=True), actions=[ft.TextButton("Сохранить", on_click=save_name_change)])
        page.overlay.append(dialog); dialog.open = True; page.update()

    def delete_car_click(e):
        if len(db_data["cars"]) <= 1: return
        def confirm_delete(_):
            db_data["cars"].pop(car_name)
            save_data(db_data); dialog.open = False; page.update(); rebuild_callback()
        dialog = ft.AlertDialog(title=ft.Text("Удаление профиля"), content=ft.Text(f"Удалить '{car_name}'?"), actions=[ft.TextButton("Удалить", on_click=confirm_delete, style=ft.ButtonStyle(color=ft.Colors.RED_600))])
        page.overlay.append(dialog); dialog.open = True; page.update()

    action_panel = ft.Row([
        ft.Text(f"Управление профилем:", size=14, weight=ft.FontWeight.W_500),
        ft.Row([
            ft.IconButton(icon=ft.Icons.ADD_CIRCLE, tooltip="Добавить авто", on_click=add_car_click),
            ft.IconButton(icon=ft.Icons.EDIT, tooltip="Переименовать", on_click=edit_car_name_click),
            ft.IconButton(icon=ft.Icons.DELETE_FOREVER, on_click=delete_car_click, icon_color=ft.Colors.RED_500),
        ], spacing=5)
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    header_card = ft.Card(
        content=ft.Container(
            content=ft.Column([
                action_panel, ft.Divider(height=5, color=ft.Colors.BLACK_12),
                ft.Text("Обновление данных пробега", size=16, weight=ft.FontWeight.BOLD),
                ft.Row([current_odo_input, daily_input, ft.IconButton(icon=ft.Icons.MENU_BOOK, on_click=lambda _: show_odometer_history_click(page, db_data, car_profile, rebuild_callback, show_message))], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                ft.Row([ft.Button("Обновить пробег и прогноз", on_click=update_forecast_click, height=45)], alignment=ft.MainAxisAlignment.CENTER)
            ], spacing=12), padding=12
        )
    )
    return build_maintenance_list(page, db_data, car_name, car_profile, header_card, rebuild_callback, show_message)
def show_odometer_history_click(page, db_data, car_profile, rebuild_callback, show_message):
    def get_sort_key(item):
        try: return datetime.strptime(item["date"], "%d.%m.%Y")
        except ValueError: return datetime.min
    def refresh_and_recalc():
        if car_profile["odometer_history"]:
            car_profile["odometer"] = sorted(car_profile["odometer_history"], key=get_sort_key)[-1]
        car_profile["daily_mileage"] = recalculate_auto_daily_mileage(car_profile)
    def delete_odo_entry(entry):
        car_profile["odometer_history"].remove(entry); refresh_and_recalc(); save_data(db_data); dialog.open = False; page.update(); rebuild_callback()
    def edit_odo_entry_dialog(entry):
        val_in = ft.TextField(label="Пробег", value=str(entry["value"]), keyboard_type=ft.KeyboardType.NUMBER)
        date_in = ft.TextField(label="Дата", value=str(entry["date"]))
        def save_edit(_):
            try:
                entry["value"], entry["date"] = int(val_in.value), date_in.value.strip()
                datetime.strptime(entry["date"], "%d.%m.%Y")
                refresh_and_recalc(); save_data(db_data); sub.open = False; dialog.open = False; page.update(); rebuild_callback()
            except ValueError: pass
        sub = ft.AlertDialog(title=ft.Text("Правка"), content=ft.Column([val_in, date_in], tight=True), actions=[ft.TextButton("ОК", on_click=save_edit)])
        page.overlay.append(sub); sub.open = True; page.update()
    def add_hist_entry(_):
        v_in = ft.TextField(label="Пробег", keyboard_type=ft.KeyboardType.NUMBER)
        d_in = ft.TextField(label="Дата", value=datetime.now().strftime("%d.%m.%Y"))
        def save_new(_):
            try:
                car_profile["odometer_history"].append({"value": int(v_in.value), "date": d_in.value.strip()})
                datetime.strptime(d_in.value.strip(), "%d.%m.%Y")
                refresh_and_recalc(); save_data(db_data); add_d.open = False; dialog.open = False; page.update(); rebuild_callback()
            except ValueError: pass
        add_d = ft.AlertDialog(title=ft.Text("Добавить"), content=ft.Column([v_in, d_in], tight=True), actions=[ft.TextButton("ОК", on_click=save_new)])
        page.overlay.append(add_d); add_d.open = True; page.update()

    sorted_history = sorted(car_profile.get("odometer_history", []), key=get_sort_key, reverse=True)
    rows = [ft.Row([ft.Text(f"• {i['date']} — {i['value']} км", expand=True), ft.IconButton(ft.Icons.EDIT, on_click=lambda _, x=i: edit_odo_entry_dialog(x)), ft.IconButton(ft.Icons.DELETE, on_click=lambda _, x=i: delete_odo_entry(x))], alignment=ft.MainAxisAlignment.SPACE_BETWEEN) for i in sorted_history]
    dialog = ft.AlertDialog(title=ft.Text("История"), content=ft.Column(controls=rows if rows else [ft.Text("Пусто")], tight=True, scroll=ft.ScrollMode.AUTO, height=250), actions=[ft.TextButton("Добавить", on_click=add_hist_entry), ft.TextButton("Закрыть", on_click=lambda _: [setattr(dialog, "open", False), page.update()])])
    page.overlay.append(dialog); dialog.open = True; page.update()

def build_maintenance_list(page, db_data, car_name, car_profile, header_card, rebuild_callback, show_message):
    maintenance_list = ft.ListView(expand=True, spacing=10, height=400)
    current_km = int(car_profile["odometer"].get("value", 0))
    daily_run = int(car_profile.get("daily_mileage", 45))

    for task, info in car_profile["maintenance_data"].items():
        target_km = info["last_service"] + info["interval"]
        remaining_km = target_km - current_km
        status_text, status_color, bg_color = ("Просрочено! Срочно на ТО!", ft.Colors.RED_700, ft.Colors.RED_50) if remaining_km <= 0 else (f"В норме. Осталось: {remaining_km} км (~{calculate_forecast(target_km, current_km, daily_run)})", ft.Colors.GREEN_700, ft.Colors.GREEN_50)
        has_h = any(h["task"] == task for h in car_profile.get("history", []))
        last_text = f"Последнее ТО: {info['last_service']} км ({info['date']})" if has_h else "Последнее ТО: данных нет"

        def make_reset(t=task, p=car_profile):
            return lambda _: [p["maintenance_data"][t].update({"last_service": current_km, "date": datetime.now().strftime("%d.%m.%Y")}), p["history"].append({"task": t, "odometer": current_km, "date": datetime.now().strftime("%d.%m.%Y")}), save_data(db_data), rebuild_callback()]
        def make_history(t=task, p=car_profile):
            return lambda _: [show_task_history_dialog(page, t, p)]
        def make_add(t=task, p=car_profile):
            return lambda _: [show_add_task_history_dialog(page, db_data, t, p, rebuild_callback, show_message)]
        def make_change(t=task, p=car_profile, cv=info["interval"]):
            return lambda _: [show_change_interval_dialog(page, db_data, t, p, cv, rebuild_callback, show_message)]

        expansion_tile = ft.ExpansionTile(
            title=ft.Text(task, size=15, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_900),
            subtitle=ft.Text(status_text, size=12, color=status_color),
            bgcolor=bg_color, collapsed_bgcolor=bg_color,
            shape=ft.RoundedRectangleBorder(radius=10), collapsed_shape=ft.RoundedRectangleBorder(radius=10),
            controls=[ft.Container(content=ft.Column([ft.Divider(height=1, color=ft.Colors.BLACK_12), ft.Row([ft.IconButton(ft.Icons.MENU_BOOK, on_click=make_history()), ft.Button("Ввод истории", on_click=make_add()), ft.Button("Регламент", on_click=make_change(), icon=ft.Icons.EDIT), ft.OutlinedButton("Сброс ТО", on_click=make_reset(), style=ft.ButtonStyle(color=ft.Colors.RED_600))], wrap=True, spacing=10), ft.Text(f"{last_text} | Регламент: {info['interval']} км", size=12, color=ft.Colors.GREY_700)], spacing=10), padding=ft.Padding(left=15, right=15, top=0, bottom=15))]
        )
        maintenance_list.controls.append(expansion_tile)

    return ft.Column([header_card, ft.Container(height=5), ft.Text("Статус регламентных работ", size=18, weight=ft.FontWeight.BOLD), maintenance_list], scroll=ft.ScrollMode.AUTO, expand=True)

def show_task_history_dialog(page, t_name, p_profile):
    task_history = [h for h in p_profile.get("history", []) if h["task"] == t_name]
    def get_sort_key(item):
        try: return datetime.strptime(item["date"], "%d.%m.%Y")
        except ValueError: return datetime.min
    lines = [ft.Text("История обслуживания пуста.")] if not task_history else [ft.Text(f"• {i['date']} — {i['odometer']} км") for i in sorted(task_history, key=get_sort_key, reverse=True)]
    dialog = ft.AlertDialog(title=ft.Text(f"Журнал: {t_name}"), content=ft.Column(controls=lines, tight=True, scroll=ft.ScrollMode.AUTO), actions=[ft.TextButton("Закрыть", on_click=lambda _: [setattr(dialog, "open", False), page.update()])])
    page.overlay.append(dialog); dialog.open = True; page.update()

def show_add_task_history_dialog(page, db_data, t_name, p_profile, rebuild_callback, show_message):
    h_odo = ft.TextField(label="Пробег (км)", keyboard_type=ft.KeyboardType.NUMBER)
    h_date = ft.TextField(label="Дата (ДД.ММ.ГГГГ)", value=datetime.now().strftime("%d.%m.%Y"))
    def save_entry(_):
        try:
            km, date_str = int(h_odo.value), h_date.value.strip()
            datetime.strptime(date_str, "%d.%m.%Y")
            p_profile["history"].append({"task": t_name, "odometer": km, "date": date_str})
            if km > p_profile["maintenance_data"][t_name]["last_service"]:
                p_profile["maintenance_data"][t_name].update({"last_service": km, "date": date_str})
            save_data(db_data); dialog.open = False; page.update(); rebuild_callback(); show_message("Добавлено!")
        except ValueError: pass
    dialog = ft.AlertDialog(title=ft.Text("Ввод истории"), content=ft.Column([h_odo, h_date], tight=True, spacing=10), actions=[ft.TextButton("Сохранить", on_click=save_entry)])
    page.overlay.append(dialog); dialog.open = True; page.update()

def show_change_interval_dialog(page, db_data, t_name, p_profile, current_val, rebuild_callback, show_message):
    int_input = ft.TextField(label="Новый интервал (км)", value=str(current_val), keyboard_type=ft.KeyboardType.NUMBER)
    def save_int(_):
        try:
            new_val = int(int_input.value)
            if new_val <= 0: return
            p_profile["maintenance_data"][t_name]["interval"] = new_val
            save_data(db_data); dialog.open = False; page.update(); rebuild_callback(); show_message("Изменено!")
        except ValueError: pass
    dialog = ft.AlertDialog(title=ft.Text("Регламент"), content=ft.Column([int_input], tight=True), actions=[ft.TextButton("Сохранить", on_click=save_int)])
    page.overlay.append(dialog); dialog.open = True; page.update()

if __name__ == "__main__":
    ft.run(main)
