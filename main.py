# Фрагмент №1: Импорты, константы и базовая структура данных
import flet as ft
import json
import os
from datetime import datetime, timedelta

# СИНХРОНИЗАЦИЯ: Связываем оба имени с одним физическим файлом
DB_FILE = "database.txt"
DB_PATH = DB_FILE

# Глобальный словарь состояния приложения
app_state = {
    "active_tab": 0,
    "newly_added_cars": []  # Список имен машин, которые должны оставаться чистыми
}

def get_default_car_data():
    """Генерирует демонстрационный шаблон данных для самого первого запуска программы."""
    current_date = datetime.now().strftime("%d.%m.%Y")
    past_date = (datetime.now() - timedelta(days=30)).strftime("%d.%m.%Y")
    return {
        "odometer": {
            "value": 125000,
            "date": current_date,
        },
        "daily_mileage": 45,
        "odometer_history": [
            {"value": 123650, "date": past_date},
            {"value": 125000, "date": current_date},
        ],
        "maintenance_data": {
            "Замена масла + фильтры": {
                "last_service": 120000,
                "interval": 10000,
                "date": current_date,
            },
            "Замена ГРМ (ремень, помпа)": {
                "last_service": 90000,
                "interval": 60000,
                "date": current_date,
            },
            "Замена антифриза": {
                "last_service": 100000,
                "interval": 50000,
                "date": current_date,
            },
            "Тормозная жидкость": {
                "last_service": 100000,
                "interval": 40000,
                "date": current_date,
            },
            "Обслуживание кондиционера": {
                "last_service": 110000,
                "interval": 30000,
                "date": current_date,
            },
        },
        "history": [],
    }

def get_clean_car_data():
    """Генерирует абсолютно чистый профиль для нового добавляемого автомобиля."""
    current_date = datetime.now().strftime("%d.%m.%Y")
    return {
        "odometer": {
            "value": 0,
            "date": current_date,
        },
        "daily_mileage": 0,
        "odometer_history": [],
        "maintenance_data": {},
        "history": []
    }

# НАДЕЖНЫЙ ИНТЕРФЕЙС ИСТОРИИ БЕЗ ИСПОЛЬЗОВАНИЯ ЦИКЛИЧЕСКИХ ИНДЕКСОВ ПИTOНА
def show_task_history_dialog(page, db_data, task_name, car_profile, rebuild_callback, show_message):
    """Окно просмотра истории ТО с рабочим CRUD-функционалом на базе объектов."""
    history_column = ft.Column(scroll=ft.ScrollMode.AUTO, height=220, spacing=8)

    def refresh_history_view():
        history_column.controls.clear()
        task_history = [h for h in car_profile.get("history", []) if h.get("task") == task_name]
        
        if not task_history:
            history_column.controls.append(
                ft.Text("История по этой работе пуста", color=ft.Colors.GREY_500, italic=True)
            )
        else:
            for record in reversed(task_history):
                def delete_action(e, target_record=record):
                    if target_record in car_profile["history"]:
                        car_profile["history"].remove(target_record)
                        try:
                            with open(DB_FILE, "w", encoding="utf-8") as f:
                                json.dump(db_data, f, ensure_ascii=False, indent=4)
                        except Exception:
                            pass
                        refresh_history_view()
                        rebuild_callback()
                        show_message("Запись из истории удалена")

                def edit_action(e, target_record=record):
                    date_input = ft.TextField(label="Дата выполнения", value=target_record.get("date", ""))
                    odo_input = ft.TextField(label="Пробег (км)", value=str(target_record.get("odometer", 0)), keyboard_type=ft.KeyboardType.NUMBER)
                    comment_input = ft.TextField(label="Комментарий", value=target_record.get("comment", ""))
                    
                    def save_edit(_):
                        try:
                            target_record["date"] = date_input.value.strip()
                            target_record["odometer"] = int(odo_input.value)
                            target_record["comment"] = comment_input.value.strip()
                            
                            with open(DB_FILE, "w", encoding="utf-8") as f:
                                json.dump(db_data, f, ensure_ascii=False, indent=4)
                                
                            edit_dialog.open = False
                            page.update()
                            refresh_history_view()
                            rebuild_callback()
                            show_message("Запись успешно изменена")
                        except ValueError:
                            show_message("Ошибка: Проверьте числовое поле пробега")

                    edit_dialog = ft.AlertDialog(
                        title=ft.Text("Редактировать запись"),
                        content=ft.Column([date_input, odo_input, comment_input], tight=True, spacing=10),
                        actions=[
                            ft.TextButton("Отмена", on_click=lambda _: setattr(edit_dialog, "open", False) or page.update()),
                            ft.TextButton("Сохранить", on_click=save_edit)
                        ]
                    )
                    page.overlay.append(edit_dialog)
                    edit_dialog.open = True
                    page.update()

                history_column.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Column([
                                ft.Row([
                                    ft.Text(f"📅 {record.get('date', '—')}", size=13, weight=ft.FontWeight.BOLD),
                                    ft.Text(f"📍 {record.get('odometer', 0)} км", size=13, color=ft.Colors.BLUE_700, weight=ft.FontWeight.W_500)
                                ], spacing=15),
                                ft.Text(f"💬 {record.get('comment', 'Выполнено ТО')}", size=12, color=ft.Colors.GREY_700)
                            ], spacing=2, expand=True),
                            ft.Row([
                                ft.IconButton(ft.Icons.EDIT, icon_size=16, icon_color=ft.Colors.BLUE_600, on_click=edit_action),
                                ft.IconButton(ft.Icons.DELETE, icon_size=16, icon_color=ft.Colors.RED_400, on_click=delete_action),
                            ], spacing=0)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=6,
                        bgcolor=ft.Colors.GREY_50,
                        border_radius=4
                    )
                )
        page.update()

    dialog = ft.AlertDialog(
        title=ft.Text(f"История: {task_name}"),
        content=ft.Container(content=history_column, width=420),
        actions=[ft.TextButton("Закрыть", on_click=lambda _: setattr(dialog, "open", False) or page.update())]
    )
    page.overlay.append(dialog)
    dialog.open = True
    refresh_history_view()





# Фрагмент №2: Алгоритм автоматического расчета пробега в день

def recalculate_auto_daily_mileage(car_profile):
    """Счет реального пробега в сутки по истории."""
    history = car_profile.get("odometer_history", [])
    if len(history) < 2:
        return int(car_profile.get("daily_mileage", 45))

    sorted_hist = sorted(history, key=parse_h_date)
    first_point = sorted_hist[0]
    last_point = sorted_hist[-1]

    delta_km = int(last_point["value"]) - int(
        first_point["value"]
    )
    delta_days = (
        parse_h_date(last_point) - parse_h_date(first_point)
    ).days

    if delta_days <= 0 or delta_km <= 0:
        return int(car_profile.get("daily_mileage", 45))

    auto_run = round(delta_km / delta_days)
    if auto_run > 0:
        return auto_run
    return 45


def parse_h_date(item):
    """Глобальная функция парсинга дат для сортировки истории."""
    try:
        return datetime.strptime(
            item["date"], "%d.%m.%Y"
        )
    except:
        return datetime.min



# Фрагмент №3: Функции работы с базой данных на диске

def load_data():
    """Загружает базу из файла и адаптирует под обновления."""
    default_structure = {
        "cars": {
            "Автомобиль 1": get_default_car_data(),
            "Автомобиль 2": get_default_car_data(),
        }
    }
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(
                default_structure,
                f,
                ensure_ascii=False,
                indent=4,
            )
        return default_structure
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        db_updated = False
        for car_name, car_profile in data.get(
            "cars", {}
        ).items():
            if "daily_mileage" not in car_profile:
                car_profile[
                    "daily_mileage"
                ] = recalculate_auto_daily_mileage(
                    car_profile
                )
                db_updated = True
            if (
                "maintenance_data" not in car_profile
                or not car_profile["maintenance_data"]
            ):
                car_profile[
                    "maintenance_data"
                ] = get_default_car_data()[
                    "maintenance_data"
                ]
                db_updated = True
        if db_updated:
            save_data(data)
        return data
    except Exception:
        return default_structure


def save_data(data):
    """Преобразует словарь данных в JSON и пишет на диск."""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(
            data, f, ensure_ascii=False, indent=4
        )


# Фрагмент №4: Прогностический движок

def calculate_forecast(
    target_km, current_km, daily_run
):
    """Высчитывает примерную дату, когда наступит регламент ТО."""
    if target_km <= current_km:
        return "Срочно ТО!"
    if daily_run <= 0:
        return "Укажите пробег в день"
    days_left = (target_km - current_km) / daily_run
    future_date = datetime.now() + timedelta(
        days=int(days_left)
    )
    return future_date.strftime("%d.%m.%Y")


# Фрагмент №5.1: Панель управления автомобилем (Верхняя часть: Кнопки и Счётчики)
def generate_car_view(page, db_data, car_name, car_profile, show_message, rebuild_callback):
    if car_name in app_state["newly_added_cars"]:
        current_value, current_date, daily_mileage_val = "0", datetime.now().strftime("%d.%m.%Y"), "0"
        car_profile.update({"odometer": {"value": 0, "date": current_date}, "daily_mileage": 0, "maintenance_data": {}, "odometer_history": [], "history": []})
    else:
        odo_dict = car_profile.get("odometer") or {}
        val_from_db = odo_dict.get("value")
        current_value = str(val_from_db) if val_from_db is not None else "0"
        current_date = odo_dict.get("date", "—")
        daily_mileage_val = str(car_profile.get("daily_mileage", 0))

    current_odo_input = ft.TextField(label=f"Пробег (км) [от {current_date}]", value=current_value, keyboard_type=ft.KeyboardType.NUMBER, expand=True)
    daily_input = ft.TextField(label="Пробег в день (км)", value=daily_mileage_val, keyboard_type=ft.KeyboardType.NUMBER, expand=True)

    def execute_custom_export(full_path):
        try:
            with open(full_path, "w", encoding="utf-8") as f: json.dump(db_data, f, ensure_ascii=False, indent=4)
            show_message("Экспорт завершен успешно!")
        except Exception as ex: show_message(f"Ошибка экспорта: {ex}")

    def execute_custom_import(full_path):
        try:
            with open(full_path, "r", encoding="utf-8") as f: imported_json = json.load(f)
            if "cars" in imported_json:
                db_data.clear()
                for key, value in imported_json.items(): db_data[key] = json.loads(json.dumps(value))
                app_state["newly_added_cars"].clear()
                try:
                    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(db_data, f, ensure_ascii=False, indent=4)
                except Exception: pass
                rebuild_callback(); show_message("База успешно импортирована!")
            else: show_message("Неверный формат резервного файла")
        except Exception as ex: show_message(f"Ошибка импорта: {ex}")

    def update_forecast_click(e):
        try:
            val = int(current_odo_input.value)
            now_date_str = datetime.now().strftime("%d.%m.%Y")
            car_profile["odometer"] = {"value": val, "date": now_date_str}
            car_profile["daily_mileage"] = int(daily_input.value)
            if car_name in app_state["newly_added_cars"]: app_state["newly_added_cars"].remove(car_name)
            if "odometer_history" not in car_profile: car_profile["odometer_history"] = []
            if not any(h["value"] == val for h in car_profile["odometer_history"]): car_profile["odometer_history"].append({"value": val, "date": now_date_str})
            try:
                with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(db_data, f, ensure_ascii=False, indent=4)
            except Exception: pass
            rebuild_callback(); show_message("Данные успешно обновлены!")
        except ValueError: show_message("Ошибка: Проверьте числовые поля пробега")

    def add_car_click(e):
        car_name_input = ft.TextField(label="Марка / Модель")
        def save_new_car(_):
            name = car_name_input.value.strip()
            if not name or name in db_data["cars"]: return
            if name not in app_state["newly_added_cars"]: app_state["newly_added_cars"].append(name)
            db_data["cars"][name] = {"odometer": {"value": 0, "date": datetime.now().strftime("%d.%m.%Y")}, "daily_mileage": 0, "odometer_history": [], "maintenance_data": {}, "history": []}
            try:
                with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(db_data, f, ensure_ascii=False, indent=4)
            except Exception: pass
            app_state["active_tab"] = len(db_data["cars"]) - 1
            dialog.open = False; page.update(); rebuild_callback()
        dialog = ft.AlertDialog(title=ft.Text("Добавить автомобиль"), content=ft.Column([car_name_input], tight=True), actions=[ft.TextButton("Добавить", on_click=save_new_car)])
        page.overlay.append(dialog); dialog.open = True; page.update()

    def edit_car_name_click(e):
        edit_name_input = ft.TextField(label="Новое имя профиля", value=car_name)
        def save_name_change(_):
            new_name = edit_name_input.value.strip()
            if not new_name or new_name == car_name or new_name in db_data["cars"]: return
            db_data["cars"][new_name] = db_data["cars"].pop(car_name)
            if car_name in app_state["newly_added_cars"]:
                app_state["newly_added_cars"].remove(car_name); app_state["newly_added_cars"].append(new_name)
            try:
                with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(db_data, f, ensure_ascii=False, indent=4)
            except Exception: pass
            dialog.open = False; page.update(); rebuild_callback()
        dialog = ft.AlertDialog(title=ft.Text("Редактировать имя"), content=ft.Column([edit_name_input], tight=True), actions=[ft.TextButton("Сохранить", on_click=save_name_change)])
        page.overlay.append(dialog); dialog.open = True; page.update()

    def delete_car_click(e):
        if len(db_data["cars"]) <= 1: return
        def confirm_delete(_):
            db_data["cars"].pop(car_name)
            if car_name in app_state["newly_added_cars"]: app_state["newly_added_cars"].remove(car_name)
            try:
                with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(db_data, f, ensure_ascii=False, indent=4)
            except Exception: pass
            app_state["active_tab"] = 0
            dialog.open = False; page.update(); rebuild_callback()
        dialog = ft.AlertDialog(title=ft.Text("Удаление профиля"), content=ft.Text(f"Удалить '{car_name}'?"), actions=[ft.TextButton("Удалить", on_click=confirm_delete, style=ft.ButtonStyle(color=ft.Colors.RED_600))])
        page.overlay.append(dialog); dialog.open = True; page.update()

    def add_custom_task_click(e):
        task_title = ft.TextField(label="Название работы")
        task_interval = ft.TextField(label="Интервал (км)", value="10000")
        def save_custom_task(_):
            title = task_title.value.strip()
            if not title or title in car_profile["maintenance_data"]: return
            try:
                car_profile["maintenance_data"][title] = {"last_service": int(current_odo_input.value), "interval": int(task_interval.value), "date": datetime.now().strftime("%d.%m.%Y"), "history": []}
                try:
                    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(db_data, f, ensure_ascii=False, indent=4)
                except Exception: pass
                dialog.open = False; page.update(); rebuild_callback()
            except ValueError: pass
        dialog = ft.AlertDialog(title=ft.Text("Добавить свою работу"), content=ft.Column([task_title, task_interval], tight=True), actions=[ft.TextButton("Сохранить", on_click=save_custom_task)])
        page.overlay.append(dialog); dialog.open = True; page.update()

    action_panel = ft.Row([
        ft.Row([
            ft.Text("База:", size=14, weight=ft.FontWeight.W_500),
            ft.IconButton(ft.Icons.CLOUD_UPLOAD, tooltip="Экспорт", icon_color=ft.Colors.BLUE_600, on_click=lambda _: show_custom_file_manager_dialog(page, "export", execute_custom_export, show_message)),
            ft.IconButton(ft.Icons.CLOUD_DOWNLOAD, tooltip="Импорт", icon_color=ft.Colors.GREEN_600, on_click=lambda _: show_custom_file_manager_dialog(page, "import", execute_custom_import, show_message)),
        ], spacing=2),
        ft.Row([
            ft.IconButton(ft.Icons.ADD_CIRCLE, tooltip="Добавить авто", on_click=add_car_click),
            ft.IconButton(icon=ft.Icons.EDIT, tooltip="Переименовать", on_click=edit_car_name_click),
            ft.IconButton(ft.Icons.DELETE_FOREVER, tooltip="Удалить авто", on_click=delete_car_click, icon_color=ft.Colors.RED_500),
            ft.Container(width=40)
        ], spacing=2)
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    odo_hist = car_profile.get("odometer_history", [])
    hist_text = "История пробега: " + " ➡️ ".join([f"{h['value']} км ({h['date']})" for h in odo_hist[-2:]]) if odo_hist else "История изменений пробега пуста"

    header_card = ft.Card(
        content=ft.Container(
            content=ft.Column([
                action_panel, ft.Divider(height=5, color=ft.Colors.BLACK_12), ft.Text("Обновление данных пробега", size=16, weight=ft.FontWeight.BOLD), 
                ft.Row([current_odo_input, daily_input], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                ft.Text(hist_text, size=11, color=ft.Colors.GREY_600, italic=True),
                ft.Row([
                    ft.Button("Обновить пробег и прогноз", on_click=update_forecast_click, height=45), 
                    ft.Button("➕ Добавить работу", on_click=add_custom_task_click, height=45, style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_50, color=ft.Colors.BLUE_700))
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=15)
            ], spacing=12), padding=12
        )
    )

    return build_maintenance_list_cards(page, db_data, car_profile, header_card, rebuild_callback, show_message)


# Фрагмент №5.3: Панель управления автомобилем (Нижняя часть: Отрисовка интерактивных карточек регламентов)
def build_maintenance_list_cards(page, db_data, car_profile, header_card, rebuild_callback, show_message):
    """Отрисовка карточек регламента автомобиля и обработка кликов истории."""
    maintenance_cards = []
    current_km = car_profile.get("odometer", {}).get("value", 0)
    daily_run = car_profile.get("daily_mileage", 45)
    tasks = car_profile.get("maintenance_data", {})
    
    if tasks:
        maintenance_cards.append(ft.Container(content=ft.Text("Текущий статус регламентных работ по автомобилю:", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_800), padding=ft.Padding(left=0, top=10, right=0, bottom=5)))

    for task, info in tasks.items():
        last_service, interval = info.get("last_service", 0), info.get("interval", 10000)
        target_km = last_service + interval
        remains = target_km - current_km
        
        if remains > 0 and daily_run > 0:
            days_left = remains / daily_run
            future_date = datetime.now() + timedelta(days=days_left)
            forecast_str = future_date.strftime("%d.%m.%Y")
        else: forecast_str = "Срочно ТО!"
            
        if remains <= 0: status_color, status_text = ft.Colors.RED_600, f"Просрочено на {-remains} км"
        elif remains <= 500: status_color, status_text = ft.Colors.ORANGE_700, f"Осталось: {remains} км (Скоро ТО)"
        else: status_color, status_text = ft.Colors.GREEN_700, f"Осталось: {remains} км"

        def delete_task_click_inner(p, db, profile, task_name):
            def confirm_delete(_):
                profile["maintenance_data"].pop(task_name); save_data(db)
                p.pop_dialog(); rebuild_callback()
            dialog = ft.AlertDialog(title=ft.Text("Удаление регламента"), content=ft.Text(f"Удалить работу '{task_name}'?"), actions=[ft.TextButton("Удалить", on_click=confirm_delete, style=ft.ButtonStyle(color=ft.Colors.RED_600))])
            p.show_dialog(dialog)

        card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([ft.Text(task, size=16, weight=ft.FontWeight.BOLD, expand=True), ft.Text(forecast_str, size=14, color=ft.Colors.BLUE_GREY_700, weight=ft.FontWeight.W_500)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Text(status_text, color=status_color, size=13, weight=ft.FontWeight.W_500),
                    ft.Text(f"Последний сервис: {last_service} км | Интервал: {interval} км", size=12, color=ft.Colors.GREY_600),
                    ft.Divider(height=5, color=ft.Colors.TRANSPARENT),
                    ft.Row([
                        ft.IconButton(ft.Icons.MENU_BOOK, tooltip="История", icon_color=ft.Colors.BLUE_600, on_click=lambda _, t=task: show_task_history_dialog(page, db_data, t, car_profile, rebuild_callback, show_message)),
                        ft.IconButton(ft.Icons.CHECK_CIRCLE, tooltip="Отметить выполнение", icon_color=ft.Colors.GREEN_600, on_click=lambda _, t=task: show_complete_task_dialog(page, db_data, t, car_profile, current_km, rebuild_callback, show_message)),
                        ft.IconButton(ft.Icons.DELETE, tooltip="Удалить регламент", icon_color=ft.Colors.RED_400, on_click=lambda _, t=task: delete_task_click_inner(page, db_data, car_profile, t))
                    ], alignment=ft.MainAxisAlignment.END, spacing=0)
                ], spacing=4), padding=10
            )
        )
        maintenance_cards.append(card)

    return ft.Column(controls=[header_card] + maintenance_cards, scroll=ft.ScrollMode.AUTO, expand=True)


# Фрагмент №5.2: Кроссплатформенный надежный менеджер диалогов импорта и экспорта
def show_custom_file_manager_dialog(page, mode, on_file_selected_callback, 
show_message_callback):
    """Вызов нативных диалогов ОС с явным указанием типов данных для Android SAF."""
    import os
    import sys
    import flet as ft

    # ОПРЕДЕЛЕНИЕ ПЛАТФОРМЫ: Проверяем, запущены ли мы на Windows или Android
    is_windows = sys.platform.startswith("win")

    # ==================== ЛОГИКА ДЛЯ WINDOWS (Через Tkinter) ====================
    if is_windows:
        try:
            import tkinter as tk
            from tkinter import filedialog
            
            # Скрываем корневое графическое окно самого Tkinter
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True) # Помещаем окно выбора поверх Flet приложения
            
            if mode == "import":
                # Классическое белое окно Windows "Открыть файл"
                file_path = filedialog.askopenfilename(
                    title="Выберите файл импорта базы данных (.json)",
                    filetypes=[("Файлы JSON", "*.json")]
                )
                if file_path:
                    # Передаем точный путь в синхронную функцию импорта JSON
                    on_file_selected_callback(file_path)
                    show_message_callback("База данных успешно импортирована!")
                    if page.data and "refresh_ui" in page.data:
                        page.data["refresh_ui"]()
                else:
                    show_message_callback("Импорт отменен пользователем")
                    
            elif mode == "export":
                # Классическое окно Windows "Сохранить как..."
                file_path = filedialog.asksaveasfilename(
                    title="Выберите место для сохранения резервной копии",
                    initialfile="auto_backup.json",
                    defaultextension=".json",
                    filetypes=[("Файлы JSON", "*.json")]
                )
                if file_path:
                    # Передаем путь в функцию записи JSON
                    on_file_selected_callback(file_path)
                    show_message_callback("Резервная копия успешно создана!")
                    page.update()
                else:
                    show_message_callback("Экспорт отменен пользователем")
            
            root.destroy() # Выгружаем Tkinter из оперативной памяти
        except Exception as ex:
            show_message_callback(f"Ошибка проводника Windows: {str(ex)}")

    # ==================== ЛОГИКА ДЛЯ ANDROID (Через FilePicker) ====================
    else:
        async def launch_android_picker():
            try:
                if mode == "import":
                    # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Переводим тип в TEXT, чтобы Android показал немедийные файлы
                    result = await ft.FilePicker().pick_files(
                        type=ft.FilePickerFileType.TEXT,
                        allow_multiple=False,
                        with_data=True
                    )
                    if result and result.files and len(result.files) > 0:
                        # Извлекаем первый элемент списка файлов
                        target_file = result.files[0]
                        
                        # Внутренняя валидация расширения файла на стороне Python
                        if not target_file.name.lower().endswith(".json"):
                            show_message_callback("Ошибка: Можно импортировать только файлы .json")
                            return
                            
                        if getattr(target_file, "bytes", None) is not None:
                            import json
                            json_text = target_file.bytes.decode("utf-8")
                            raw_data = json.loads(json_text)
                            
                            # Передаем данные в функцию сохранения (запись в локальный storage приложения)
                            on_file_selected_callback(raw_data) 
                            show_message_callback("База данных успешно импортирована!")
                            
                            if page.data and "refresh_ui" in page.data:
                                page.data["refresh_ui"]()
                    else:
                        show_message_callback("Импорт отменен пользователем")
                        
                elif mode == "export":
                    # Для экспорта на Android используем явный тип TEXT
                    export_path = await ft.FilePicker().save_file(
                        dialog_title="Выберите место для сохранения резервной копии",
                        file_name="auto_backup.json",
                        type=ft.FilePickerFileType.TEXT
                    )
                    if export_path:
                        on_file_selected_callback(export_path)
                        show_message_callback("Резервная копия успешно создана!")
                        page.update()
                    else:
                        show_message_callback("Экспорт отменен пользователем")
            except Exception as ex:
                show_message_callback(f"Ошибка проводника Android: {str(ex)}")
                
        page.run_task(launch_android_picker)


# Фрагмент №6: Окно добавления записи в журнал ТО

def show_add_task_history_dialog(
    page,
    db_data,
    t_name,
    p_profile,
    rebuild_callback,
    show_message,
):
    """Ручной ввод выполненного регламента ТО."""
    h_odo = ft.TextField(
        label="Пробег (км)",
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    h_date = ft.TextField(
        label="Дата (ДД.ММ.ГГГГ)",
        value=datetime.now().strftime("%d.%m.%Y"),
    )

    def save_entry(_):
        try:
            km = int(h_odo.value)
            date_str = h_date.value.strip()
            datetime.strptime(date_str, "%d.%m.%Y")
            p_profile["history"].append(
                {
                    "task": t_name,
                    "odometer": km,
                    "date": date_str,
                }
            )
            m_data = p_profile["maintenance_data"][
                t_name
            ]
            if km > m_data["last_service"]:
                m_data.update(
                    {"last_service": km, "date": date_str}
                )
            save_data(db_data)
            dialog.open = False
            page.update()
            rebuild_callback()
            show_message("Добавлено!")
        except ValueError:
            show_message(
                "Ошибка: Проверьте формат данных!"
            )

    def close_dlg(_):
        dialog.open = False
        page.update()

    dialog = ft.AlertDialog(
        title=ft.Text("Ввод истории"),
        content=ft.Column(
            [h_odo, h_date], tight=True, spacing=10
        ),
        actions=[
            ft.TextButton(
                "Сохранить", on_click=save_entry
            ),
            ft.TextButton(
                "Отмена", on_click=close_dlg
            ),
        ],
    )
    page.overlay.append(dialog)
    dialog.open = True
    page.update()


# Фрагмент №7: Окно истории общего пробега автомобиля — Логика списка (CRUD)

def show_car_odometer_history_dialog(
    page,
    db_data,
    car_profile,
    rebuild_callback,
    show_message,
):
    """Окно истории пробега с кнопками управления."""
    history_container = ft.Column(
        spacing=10,
        scroll=ft.ScrollMode.AUTO,
    )

    def render_history_list():
        history_container.controls.clear()
        hist_data = car_profile.get(
            "odometer_history", []
        )
        sorted_hist = sorted(
            hist_data, key=parse_h_date, reverse=True
        )

        if not sorted_hist:
            history_container.controls.append(
                ft.Text(
                    "История пробега пуста.",
                    color=ft.Colors.GREY_600,
                )
            )
            page.update()
            return

        for item in sorted_hist:

            def make_del(target=item):
                return lambda _: confirm_delete_entry(
                    target
                )

            def make_edit(target=item):
                return lambda _: open_edit_entry_dialog(
                    target
                )

            val_txt = f"{item['value']} км"
            date_txt = f"Дата: {item['date']}"
            
            history_container.controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(
                                        val_txt,
                                        weight=ft.FontWeight.BOLD,
                                        size=14,
                                    ),
                                    ft.Text(
                                        date_txt,
                                        size=12,
                                        color=ft.Colors.GREY_500,
                                    ),
                                ],
                                spacing=2,
                            ),
                            ft.Row(
                                [
                                    ft.IconButton(
                                        ft.Icons.EDIT,
                                        icon_size=18,
                                        icon_color=ft.Colors.BLUE_600,
                                        on_click=make_edit(),
                                    ),
                                    ft.IconButton(
                                        ft.Icons.DELETE_OUTLINE,
                                        icon_size=18,
                                        icon_color=ft.Colors.RED_500,
                                        on_click=make_del(),
                                    ),
                                ],
                                spacing=0,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    padding=5,
                    border=ft.Border.all(
                        1, ft.Colors.BLACK_12
                    ),
                    border_radius=5,
                )
            )
        page.update()



# Фрагмент №8: Окно истории общего пробега — Функции Добавления / Изменения / Удаления

    def open_add_entry_dialog(_):
        add_km = ft.TextField(
            label="Пробег",
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        add_date = ft.TextField(
            label="Дата",
            value=datetime.now().strftime("%d.%m.%Y"),
        )

        def save_new_entry(_):
            try:
                val = int(add_km.value)
                d_str = add_date.value.strip()
                datetime.strptime(d_str, "%d.%m.%Y")
                car_profile["odometer_history"].append(
                    {"value": val, "date": d_str}
                )

                if val >= car_profile["odometer"].get(
                    "value", 0
                ):
                    car_profile["odometer"] = {
                        "value": val,
                        "date": d_str,
                    }

                car_profile[
                    "daily_mileage"
                ] = recalculate_auto_daily_mileage(
                    car_profile
                )
                save_data(db_data)
                add_dialog.open = False
                render_history_list()
                rebuild_callback()
                show_message("Запись успешно добавлена!")
            except ValueError:
                show_message(
                    "Ошибка: Неверный формат!"
                )

        def close_add(_):
            add_dialog.open = False
            page.update()

        add_dialog = ft.AlertDialog(
            title=ft.Text("Добавить пробег"),
            content=ft.Column(
                [add_km, add_date],
                tight=True,
                spacing=10,
            ),
            actions=[
                ft.TextButton(
                    "Сохранить", on_click=save_new_entry
                ),
                ft.TextButton(
                    "Отмена", on_click=close_add
                ),
            ],
        )
        page.overlay.append(add_dialog)
        add_dialog.open = True
        page.update()

    def open_edit_entry_dialog(item_to_edit):
        edit_km = ft.TextField(
            label="Пробег",
            value=str(item_to_edit["value"]),
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        edit_date = ft.TextField(
            label="Дата", value=item_to_edit["date"]
        )

        def save_edited_entry(_):
            try:
                val = int(edit_km.value)
                new_date_str = edit_date.value.strip()
                datetime.strptime(
                    new_date_str, "%d.%m.%Y"
                )

                item_to_edit["value"] = val
                item_to_edit["date"] = new_date_str

                hist_data = car_profile.get(
                    "odometer_history", []
                )
                if hist_data:
                    latest = max(
                        hist_data, key=parse_h_date
                    )
                    car_profile["odometer"] = {
                        "value": latest["value"],
                        "date": latest["date"],
                    }

                car_profile[
                    "daily_mileage"
                ] = recalculate_auto_daily_mileage(
                    car_profile
                )
                save_data(db_data)
                edit_dialog.open = False
                render_history_list()
                rebuild_callback()
                show_message("Запись изменена")
            except ValueError:
                show_message(
                    "Ошибка: Неверный формат!"
                )

        def close_edit(_):
            edit_dialog.open = False
            page.update()

        edit_dialog = ft.AlertDialog(
            title=ft.Text("Редактировать запись"),
            content=ft.Column(
                [edit_km, edit_date],
                tight=True,
                spacing=10,
            ),
            actions=[
                ft.TextButton(
                    "Сохранить",
                    on_click=save_edited_entry,
                ),
                ft.TextButton(
                    "Отмена", on_click=close_edit
                ),
            ],
        )
        page.overlay.append(edit_dialog)
        edit_dialog.open = True
        page.update()

    def confirm_delete_entry(item_to_delete):
        def delete_confirmed(_):
            h_list = car_profile["odometer_history"]
            if item_to_delete in h_list:
                h_list.remove(item_to_delete)

                if h_list:
                    latest = max(
                        h_list, key=parse_h_date
                    )
                    car_profile["odometer"] = {
                        "value": latest["value"],
                        "date": latest["date"],
                    }
                else:
                    car_profile["odometer"] = {
                        "value": 0,
                        "date": "—",
                    }

                car_profile[
                    "daily_mileage"
                ] = recalculate_auto_daily_mileage(
                    car_profile
                )
                save_data(db_data)
                del_dialog.open = False
                render_history_list()
                rebuild_callback()
                show_message("Запись удалена")

        def close_del(_):
            del_dialog.open = False
            page.update()

        del_txt = (
            f"Удалить запись: {item_to_delete['value']} км "
            f"за {item_to_delete['date']}?"
        )
        del_dialog = ft.AlertDialog(
            title=ft.Text("Удаление записи"),
            content=ft.Text(del_txt),
            actions=[
                ft.TextButton(
                    "Удалить",
                    on_click=delete_confirmed,
                    style=ft.ButtonStyle(
                        color=ft.Colors.RED_600
                    ),
                ),
                ft.TextButton(
                    "Отмена", on_click=close_del
                ),
            ],
        )
        page.overlay.append(del_dialog)
        del_dialog.open = True
        page.update()

    def close_main(_):
        main_dialog.open = False
        page.update()

    main_dialog = ft.AlertDialog(
        title=ft.Text("История общего пробега"),
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Button(
                        "➕ Добавить новую запись",
                        icon=ft.Icons.ADD,
                        on_click=open_add_entry_dialog,
                    ),
                    ft.Divider(
                        height=10,
                        color=ft.Colors.BLACK_12,
                    ),
                    history_container,
                ],
                tight=True,
                spacing=10,
            ),
            width=400,
        ),
        actions=[
            ft.TextButton(
                "Закрыть", on_click=close_main
            )
        ],
    )
    page.overlay.append(main_dialog)
    main_dialog.open = True
    render_history_list()


# Фрагмент №9.1: Функции действий внутри плитки ТО

def create_task_actions(
    page, db_data, p, t, current_km, rebuild, show_msg
):
    """Генерирует замыкания для кнопок плитки ТО."""
    
    def reset_click(_):
        now_str = datetime.now().strftime("%d.%m.%Y")
        p["maintenance_data"][t].update({
            "last_service": current_km,
            "date": now_str
        })
        p["history"].append({
            "task": t,
            "odometer": current_km,
            "date": now_str
        })
        save_data(db_data)
        rebuild()

    def change_click(_):
        name_in = ft.TextField(label="Название", value=t)
        int_in = ft.TextField(
            label="Интервал (км)",
            value=str(p["maintenance_data"][t]["interval"]),
            keyboard_type=ft.KeyboardType.NUMBER
        )

        def save_changes(_):
            new_name = name_in.value.strip()
            try:
                new_int = int(int_in.value)
                if new_int <= 0 or not new_name:
                    raise ValueError
                old_info = p["maintenance_data"].pop(t)
                old_info["interval"] = new_int
                p["maintenance_data"][new_name] = old_info
                if new_name != t:
                    for h in p.get("history", []):
                        if h["task"] == t:
                            h["task"] = new_name
                save_data(db_data)
                dlg.open = False
                page.update()
                rebuild()
                show_msg("Регламент изменен")
            except ValueError:
                show_msg("Ошибка: Проверьте поля")

        dlg = ft.AlertDialog(
            title=ft.Text("Редактировать"),
            content=ft.Column([name_in, int_in], tight=True),
            actions=[ft.TextButton("Сохранить", on_click=save_changes)]
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def delete_click(_):
        def confirm_delete(_):
            p["maintenance_data"].pop(t)
            p["history"] = [
                h for h in p.get("history", []) if h["task"] != t
            ]
            save_data(db_data)
            dlg.open = False
            page.update()
            rebuild()
            show_msg(f"Работа '{t}' удалена")

        dlg = ft.AlertDialog(
            title=ft.Text("Удаление"),
            content=ft.Text(f"Удалить пункт '{t}'?"),
            actions=[
                ft.TextButton(
                    "Удалить",
                    on_click=confirm_delete,
                    style=ft.ButtonStyle(color=ft.Colors.RED_600)
                )
            ]
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    return reset_click, change_click, delete_click


# Фрагмент №9.2: Интерфейс заголовка и списка регламентов ТО

def build_maintenance_list(
    page,
    db_data,
    car_name,
    car_profile,
    header_card,
    rebuild_callback,
    show_message,
    add_task_fn,
):
    """Сборка визуального списка регламентных работ."""
    m_list = ft.ListView(expand=True, spacing=10, height=400)
    current_km = int(car_profile["odometer"].get("value", 0))
    daily_run = int(car_profile.get("daily_mileage", 45))

    for task, info in list(car_profile["maintenance_data"].items()):
        target_km = info["last_service"] + info["interval"]
        remaining_km = target_km - current_km

        if remaining_km <= 0:
            status_text = "Просрочено! Срочно на ТО!"
            status_color = ft.Colors.RED_700
            bg_color = ft.Colors.RED_50
        else:
            fc = calculate_forecast(target_km, current_km, daily_run)
            status_text = f"В норме. Осталось: {remaining_km} км (~{fc})"
            status_color = ft.Colors.GREEN_700
            bg_color = ft.Colors.GREEN_50

        has_h = any(h["task"] == task for h in car_profile.get("history", []))
        last_text = (
            f"Последнее ТО: {info['last_service']} км ({info['date']})"
            if has_h else "Последнее ТО: данных нет"
        )

        fn_reset, fn_change, fn_delete = create_task_actions(
            page, db_data, car_profile, task,
            current_km, rebuild_callback, show_message
        )

        sub_info = f"{last_text} | Регламент: {info['interval']} км"
        
        tile = ft.ExpansionTile(
            title=ft.Text(
                task, size=15, weight=ft.FontWeight.BOLD,
                color=ft.Colors.BLUE_GREY_900
            ),
            subtitle=ft.Text(status_text, size=12, color=status_color),
            bgcolor=bg_color, collapsed_bgcolor=bg_color,
            shape=ft.RoundedRectangleBorder(radius=10),
            collapsed_shape=ft.RoundedRectangleBorder(radius=10),
            controls=[
                ft.Container(
                    content=ft.Column([
                        ft.Divider(height=1, color=ft.Colors.BLACK_12),
                        ft.Row([
                            ft.IconButton(
                                ft.Icons.MENU_BOOK,
                                # СИНХРОНИЗИРОВАНО: передаем новые аргументы в Фрагмент №5
                                on_click=lambda _, t=task: show_task_history_dialog(
                                    page, db_data, t, car_profile, rebuild_callback, show_message
                                ),
                                tooltip="История"
                            ),
                            ft.Button(
                                "Ввод истории",
                                on_click=lambda _, t=task: show_add_task_history_dialog(
                                    page, db_data, t, car_profile, rebuild_callback, show_message
                                )
                            ),
                            ft.Button("Правка", on_click=fn_change, icon=ft.Icons.EDIT),
                            ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=ft.Colors.RED_500, on_click=fn_delete, tooltip="Удалить"),
                            ft.OutlinedButton("Сброс ТО", on_click=fn_reset, style=ft.ButtonStyle(color=ft.Colors.RED_600))
                        ], wrap=True, spacing=10),
                        ft.Text(sub_info, size=12, color=ft.Colors.GREY_700)
                    ], spacing=10),
                    padding=ft.Padding(left=15, right=15, top=0, bottom=15)
                )
            ]
        )
        m_list.controls.append(tile)

    title_row = ft.Row(
        [
            ft.Text("Статус регламентных работ", size=18, weight=ft.FontWeight.BOLD),
            ft.IconButton(
                ft.Icons.ADD_CIRCLE_OUTLINE, icon_color=ft.Colors.BLUE_700,
                tooltip="Добавить новую работу", on_click=add_task_fn
            )
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
    )

    return ft.Column(
        [header_card, ft.Container(height=5), title_row, m_list],
        scroll=ft.ScrollMode.AUTO, expand=True
    )



# Фрагмент №10: Кастомный файловый менеджер (Устаревшая заглушка отключена)
# Данный блок намеренно оставлен пустым для бесконфликтной работы Фрагмента №5.2
pass






# Фрагмент №11: Подсистема загрузки, сохранения и автоматической миграции структуры БД
def load_data():
    """Загрузка локальной базы данных из database.txt с сохранением оригинальной миграции."""
    if not os.path.exists(DB_FILE):
        initial_data = {"cars": {"Мой Автомобиль": get_default_car_data()}}
        save_data(initial_data)
        return initial_data
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "cars" not in data:
                data = {"cars": {}}
            
            # ОРИГИНАЛЬНАЯ ЛОГИКА МИГРАЦИИ И ВАЛИДАЦИИ СТРУКТУРЫ КАЖДОГО АВТОМОБИЛЯ
            for car_name, car_profile in data["cars"].items():
                # ЗАЩИТНЫЙ КЛАПАН: Если машина новая и должна быть чистой, не навязываем ей 125000 и 45
                if car_name in app_state["newly_added_cars"] and car_profile.get("odometer", {}).get("value") == 0:
                    if "odometer" not in car_profile:
                        car_profile["odometer"] = {"value": 0, "date": datetime.now().strftime("%d.%m.%Y")}
                    if "daily_mileage" not in car_profile:
                        car_profile["daily_mileage"] = 0
                    if "odometer_history" not in car_profile:
                        car_profile["odometer_history"] = []
                    if "maintenance_data" not in car_profile:
                        car_profile["maintenance_data"] = {}
                    if "history" not in car_profile:
                        car_profile["history"] = []
                    continue # Пропускаем демо-заполнение для этой машины

                # Стандартная миграция для старых и уже заполненных профилей
                if "odometer" not in car_profile:
                    car_profile["odometer"] = {"value": 125000, "date": datetime.now().strftime("%d.%m.%Y")}
                if "daily_mileage" not in car_profile:
                    car_profile["daily_mileage"] = 45
                if "odometer_history" not in car_profile:
                    car_profile["odometer_history"] = []
                if "maintenance_data" not in car_profile:
                    car_profile["maintenance_data"] = {}
                if "history" not in car_profile:
                    car_profile["history"] = []

                # Автоматический перерасчет среднесуточного пробега по истории
                odo_hist = car_profile.get("odometer_history", [])
                if len(odo_hist) >= 2:
                    try:
                        sorted_hist = sorted(odo_hist, key=lambda x: datetime.strptime(x["date"], "%d.%m.%Y"))
                        first, last = sorted_hist[0], sorted_hist[-1]
                        d1 = datetime.strptime(first["date"], "%d.%m.%Y")
                        d2 = datetime.strptime(last["date"], "%d.%m.%Y")
                        days = (d2 - d1).days
                        km = last["value"] - first["value"]
                        if days > 0 and km > 0:
                            car_profile["daily_mileage"] = max(1, int(km / days))
                    except Exception:
                        pass

                # Проверка внутренней структуры регламентных работ
                for task_name, task_info in car_profile["maintenance_data"].items():
                    if "last_service" not in task_info:
                        task_info["last_service"] = car_profile["odometer"]["value"]
                    if "interval" not in task_info:
                        task_info["interval"] = 10000
                    if "date" not in task_info:
                        task_info["date"] = datetime.now().strftime("%d.%m.%Y")

            return data
    except Exception:
        return {"cars": {}}

def save_data(data):
    """Преобразует словарь данных в JSON и пишет на диск."""
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Ошибка записи на диск: {e}")


# Фрагмент №11.2: Системный конфигуратор действий профиля автомобиля
def setup_car_profile_actions(page, db_data, car_name, show_message, rebuild_callback):
    """Генерирует обработчики для кнопок добавления, правки и удаления вкладок машин."""
    
    def add_car_fn(e):
        car_name_input = ft.TextField(label="Марка / Модель")
        
        def save_new_car(_):
            name = car_name_input.value.strip()
            if not name or name in db_data["cars"]: 
                return
            
            # Регистрируем имя машины в списке чистых, чтобы мигратор не навязал ей 125000 км
            if name not in app_state["newly_added_cars"]:
                app_state["newly_added_cars"].append(name)
            
            # Записываем строго пустую структуру данных
            db_data["cars"][name] = {
                "odometer": {"value": 0, "date": datetime.now().strftime("%d.%m.%Y")},
                "daily_mileage": 0,
                "odometer_history": [],
                "maintenance_data": {},
                "history": []
            }
            save_data(db_data)
            
            # Автоматически вычисляем индекс новой вкладки (она будет последней в списке)
            app_state["active_tab"] = len(db_data["cars"]) - 1
            
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

    def edit_car_fn(e):
        edit_name_input = ft.TextField(label="Новое имя профиля", value=car_name)
        
        def save_name_change(_):
            new_name = edit_name_input.value.strip()
            if not new_name or new_name == car_name or new_name in db_data["cars"]: 
                return
            
            db_data["cars"][new_name] = db_data["cars"].pop(car_name)
            
            if car_name in app_state["newly_added_cars"]:
                app_state["newly_added_cars"].remove(car_name)
                app_state["newly_added_cars"].append(new_name)
                
            save_data(db_data)
            dialog.open = False
            page.update()
            rebuild_callback()

        dialog = ft.AlertDialog(
            title=ft.Text("Редактировать имя"),
            content=ft.Column([edit_name_input], tight=True),
            actions=[ft.TextButton("Сохранить", on_click=save_name_change)]
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def del_car_fn(e):
        if len(db_data["cars"]) <= 1: 
            return
            
        def confirm_delete(_):
            db_data["cars"].pop(car_name)
            if car_name in app_state["newly_added_cars"]:
                app_state["newly_added_cars"].remove(car_name)
                
            save_data(db_data)
            app_state["active_tab"] = 0 # Сбрасываем фокус на первую вкладку
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

    return add_car_fn, edit_car_fn, del_car_fn





# Фрагмент №12: Панель пробега автомобиля и создание карточки вида
def generate_car_view(page, db_data, car_name, car_profile, show_message, rebuild_callback):
    """Генерация основного экрана автомобиля."""
    # Извлекаем данные пробега. Если машина в списке чистых — строго выводим 0
    if car_name in app_state["newly_added_cars"]:
        current_value, current_date, daily_mileage_val = "0", datetime.now().strftime("%d.%m.%Y"), "0"
    else:
        odo_data = car_profile.get("odometer", {"value": 125000, "date": "—"})
        current_value = str(odo_data.get("value", 125000))
        current_date = odo_data.get("date", "—")
        daily_mileage_val = str(car_profile.get("daily_mileage", 45))

    current_odo_input = ft.TextField(label=f"Пробег (км) [от {current_date}]", value=current_value, keyboard_type=ft.KeyboardType.NUMBER, expand=True)
    daily_input = ft.TextField(label="Пробег в день (км)", value=daily_mileage_val, keyboard_type=ft.KeyboardType.NUMBER, expand=True)

    def execute_custom_export(full_path):
        try:
            fresh_db_data = load_data()
            with open(full_path, "w", encoding="utf-8") as f: json.dump(fresh_db_data, f, ensure_ascii=False, indent=4)
            show_message("Экспорт завершен!")
        except Exception as ex: show_message(f"Ошибка экспорта: {ex}")

    def execute_custom_import(full_path):
        try:
            with open(full_path, "r", encoding="utf-8") as f: imported_json = json.load(f)
            if "cars" in imported_json:
                save_data(imported_json)
                app_state["newly_added_cars"].clear()
                rebuild_callback()
                show_message("База импортирована!")
            else: show_message("Неверный формат!")
        except Exception as ex: show_message(f"Ошибка импорта: {ex}")

    def update_forecast_click(e):
        try:
            val = int(current_odo_input.value)
            now_str = datetime.now().strftime("%d.%m.%Y")
            car_profile["odometer"] = {"value": val, "date": now_str}
            car_profile["daily_mileage"] = int(daily_input.value)
            if car_name in app_state["newly_added_cars"]: app_state["newly_added_cars"].remove(car_name)
            h_list = car_profile["odometer_history"]
            if not any(h["value"] == val for h in h_list): h_list.append({"value": val, "date": now_str})
            car_profile["daily_mileage"] = recalculate_auto_daily_mileage(car_profile)
            save_data(db_data)
            rebuild_callback()
            show_message("Данные обновлены!")
        except ValueError: show_message("Ошибка: Проверьте поля!")

    def add_custom_task_click(e):
        t_title, t_int = ft.TextField(label="Название"), ft.TextField(label="Интервал", value="10000")
        def save_custom_task(_):
            title = t_title.value.strip()
            m_data = car_profile["maintenance_data"]
            if not title or title in m_data: return
            try:
                km = int(current_odo_input.value)
                now_date = datetime.now().strftime("%d.%m.%Y")
                m_data[title] = {"last_service": km, "interval": int(t_int.value), "date": now_date}
                car_profile["history"].append({"task": title, "odometer": km, "date": now_date})
                save_data(db_data)
                dlg.open = False; page.update(); rebuild_callback()
            except ValueError: pass
        dlg = ft.AlertDialog(title=ft.Text("Добавить свою работу"), content=ft.Column([t_title, t_int], tight=True), actions=[ft.TextButton("Сохранить", on_click=save_custom_task)])
        # ИСПРАВЛЕНО: Теперь имена переменных строго совпадают (везде dlg)
        page.overlay.append(dlg); dlg.open = True; page.update()

    act_fns = setup_car_profile_actions(page, db_data, car_name, show_message, rebuild_callback)
    add_car_fn, edit_car_fn, del_car_fn = act_fns

    def open_export(_): show_custom_file_manager_dialog(page, "export", execute_custom_export, show_message)
    def open_import(_): show_custom_file_manager_dialog(page, "import", execute_custom_import, show_message)
    def open_odo_hist(_): show_car_odometer_history_dialog(page, db_data, car_profile, rebuild_callback, show_message)

    action_panel = ft.Row([
        ft.Row([
            ft.Text("База:", size=14, weight=ft.FontWeight.W_500),
            ft.IconButton(ft.Icons.CLOUD_UPLOAD, icon_color=ft.Colors.BLUE_600, on_click=open_export),
            ft.IconButton(ft.Icons.CLOUD_DOWNLOAD, icon_color=ft.Colors.GREEN_600, on_click=open_import),
        ], spacing=2),
        ft.Row([
            ft.IconButton(ft.Icons.ADD_CIRCLE, on_click=add_car_fn),
            ft.IconButton(icon=ft.Icons.EDIT, on_click=edit_car_fn),
            ft.IconButton(ft.Icons.DELETE_FOREVER, icon_color=ft.Colors.RED_500, on_click=del_car_fn),
            ft.Container(width=40),
        ], spacing=2),
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    header_card = ft.Card(content=ft.Container(content=ft.Column([
        action_panel, ft.Divider(height=5, color=ft.Colors.BLACK_12), ft.Text("Обновление данных пробега", size=16, weight=ft.FontWeight.BOLD),
        ft.Row([current_odo_input, daily_input], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
        ft.Row([
            ft.Button("Обновить", on_click=update_forecast_click, height=45),
            ft.OutlinedButton("📖 История пробега", icon=ft.Icons.HISTORY, height=45, on_click=open_odo_hist),
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
    ], spacing=12), padding=12))

    return build_maintenance_list(page, db_data, car_name, car_profile, header_card, rebuild_callback, show_message, add_custom_task_click)




# Фрагмент №13: Главная точка входа приложения по спецификации Flet 1.0+
def main(page: ft.Page):
    page.title = "Журнал ТО"
    page.theme_mode = ft.ThemeMode.LIGHT

    def show_message(message_text):
        """Универсальное всплывающее уведомление (SnackBar)."""
        page.overlay.append(ft.SnackBar(ft.Text(message_text), open=True))
        page.update()

    def build_tabs_ui():
        """Полная пересборка интерфейса вкладок с сохранением фокуса на новой машине."""
        page.controls.clear()
        
        # Загрузка базы данных
        db_data = load_data()
        
        # Инициализация первого авто при пустом файле
        if not db_data.get("cars"):
            db_data["cars"] = {"Мой Автомобиль": get_default_car_data()}
            save_data(db_data)

        tab_headers = []
        tab_contents = []
        
        # Строим списки вкладок
        for car_name, car_profile in db_data["cars"].items():
            car_view_container = generate_car_view(
                page, db_data, car_name, car_profile, show_message, build_tabs_ui
            )
            tab_headers.append(ft.Tab(label=car_name, icon=ft.Icons.DIRECTIONS_CAR))
            tab_contents.append(car_view_container)

        # Синхронизируем состояние индекса при ручном переключении вкладок пользователем
        def on_tab_change(e):
            app_state["active_tab"] = e.control.selected_index

        # Собираем контейнер Tabs, подставляя актуальный индекс из app_state
        tabs_control = ft.Tabs(
            length=len(tab_headers),
            selected_index=min(app_state["active_tab"], len(tab_headers) - 1),
            animation_duration=200,
            expand=True,
            on_change=on_tab_change,
            content=ft.Column(
                expand=True,
                controls=[
                    ft.TabBar(tabs=tab_headers),
                    ft.TabBarView(expand=True, controls=tab_contents)
                ]
            )
        )
        
        page.add(tabs_control)
        page.update()

    # Сохраняем ссылку на функцию обновления, чтобы Фрагмент №5.2 мог её вызвать
    page.data = {"refresh_ui": build_tabs_ui}

    # Запускаем построение интерфейса при старте
    build_tabs_ui()

if __name__ == "__main__":
    ft.run(main)


