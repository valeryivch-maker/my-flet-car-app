# Фрагмент №1: Импорты, константы и базовая структура данных
import flet as ft
import json
import os
from datetime import datetime, timedelta

# СИНХРОНИЗАЦИЯ: Связываем оба имени с одним физическим файлом
DB_FILE = "database.txt"

def generate_analytics_view(page, car_profile):
    import flet as ft
    
    view_column = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=15)
    current_km = car_profile.get("odometer", {}).get("value", 0)
    maintenance_tasks = car_profile.get("maintenance_data", {})
    
    view_column.controls.append(
        ft.Text("Аналитика износа расходников", size=20, weight=ft.FontWeight.BOLD)
    )
    
    if not maintenance_tasks:
        view_column.controls.append(
            ft.Text("Нет данных для анализа. Добавьте регламентные работы.", 
                    color=ft.Colors.GREY_500, italic=True)
        )
        return view_column
        
    for task_name, task_data in maintenance_tasks.items():
        interval = task_data.get("interval", 1) # Защита от деления на 0
        last_service = task_data.get("last_service", 0)
        
        target_km = last_service + interval
        remains = target_km - current_km
        
        # Считаем остаток ресурса (от 0.0 до 1.0)
        passed = current_km - last_service
        if passed < 0: passed = 0
        
        resource_left = 1.0 - (passed / interval)
        # Ограничиваем рамками 0.0 - 1.0
        resource_left = max(0.0, min(1.0, resource_left))
        
        # Динамически выбираем цвет полосы и статус
        if remains <= 0:
            bar_color = ft.Colors.RED_600
            status_text = "Срочно заменить!"
        elif remains <= 500:
            bar_color = ft.Colors.ORANGE_700
            status_text = f"Скоро замена (осталось {remains} км)"
        else:
            bar_color = ft.Colors.GREEN_700
            status_text = f"Ресурс в норме (осталось {remains} км)"
            
        # Красивая карточка с прогресс-баром
        task_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(task_name, size=15, weight=ft.FontWeight.BOLD, expand=True),
                        ft.Text(f"{int(resource_left * 100)}%", size=14, weight=ft.FontWeight.W_500, color=bar_color)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Container(height=4),
                    ft.ProgressBar(value=resource_left, color=bar_color, bgcolor=ft.Colors.GREY_200, height=8),
                    ft.Container(height=2),
                    ft.Text(status_text, size=12, color=ft.Colors.GREY_600, italic=True)
                ], spacing=4),
                padding=12
            )
        )
        view_column.controls.append(task_card)
        
    return view_column


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
    import flet as ft
    from datetime import datetime

    if car_name in app_state["newly_added_cars"]:
        current_value, current_date, daily_mileage_val = "0", datetime.now().strftime("%d.%m.%Y"), "0"
        car_profile.update({"odometer": {"value": 0, "date": current_date}, "daily_mileage": 0, 
        "maintenance_data": {}, "odometer_history": [], "history": []})
    else:
        odo_dict = car_profile.get("odometer") or {}
        val_from_db = odo_dict.get("value")
        current_value = str(val_from_db) if val_from_db is not None else "0"
        current_date = odo_dict.get("date", "—")
        daily_mileage_val = str(car_profile.get("daily_mileage", 0))

    current_odo_input = ft.TextField(
        label=f"Пробег (км) [от {current_date}]", 
        value=current_value, 
        keyboard_type=ft.KeyboardType.NUMBER, 
        expand=True
    )
    daily_input = ft.TextField(
        label="Пробег в день (км)", 
        value=daily_mileage_val, 
        keyboard_type=ft.KeyboardType.NUMBER, 
        expand=True
    )

    def update_forecast_click(e):
        try:
            val = int(current_odo_input.value)
            now_date_str = datetime.now().strftime("%d.%m.%Y")
            car_profile["odometer"] = {"value": val, "date": now_date_str}
            car_profile["daily_mileage"] = int(daily_input.value)
            if car_name in app_state["newly_added_cars"]: 
                app_state["newly_added_cars"].remove(car_name)
            if "odometer_history" not in car_profile: 
                car_profile["odometer_history"] = []
            if not any(h["value"] == val for h in car_profile["odometer_history"]): 
                car_profile["odometer_history"].append({"value": val, "date": now_date_str})
            save_data(db_data)
            rebuild_callback()
            show_message("Данные успешно обновлены!")
        except ValueError: 
            show_message("Ошибка: Проверьте числовые поля пробега")

    def add_car_click(e):
        car_name_input = ft.TextField(label="Марка / Модель")
        def save_new_car(_):
            name = car_name_input.value.strip()
            if not name or name in db_data["cars"]: return
            if name not in app_state["newly_added_cars"]: app_state["newly_added_cars"].append(name)
            db_data["cars"][name] = {"odometer": {"value": 0, "date": datetime.now().strftime("%d.%m.%Y")}, "daily_mileage": 0, "odometer_history": [], "maintenance_data": {}, "history": []}
            save_data(db_data)
            app_state["active_tab"] = len(db_data["cars"]) - 1
            dialog.open = False
            page.update()
            rebuild_callback()
        dialog = ft.AlertDialog(title=ft.Text("Добавить автомобиль"), content=ft.Column([car_name_input], tight=True), actions=[ft.TextButton("Добавить", on_click=save_new_car)])
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def edit_car_name_click(e):
        edit_name_input = ft.TextField(label="Новое имя профиля", value=car_name)
        def save_name_change(_):
            new_name = edit_name_input.value.strip()
            if not new_name or new_name == car_name or new_name in db_data["cars"]: return
            db_data["cars"][new_name] = db_data["cars"].pop(car_name)
            if car_name in app_state["newly_added_cars"]:
                app_state["newly_added_cars"].remove(car_name)
                app_state["newly_added_cars"].append(new_name)
            save_data(db_data)
            dialog.open = False
            page.update()
            rebuild_callback()
        dialog = ft.AlertDialog(title=ft.Text("Редактировать имя"), content=ft.Column([edit_name_input], tight=True), actions=[ft.TextButton("Сохранить", on_click=save_name_change)])
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def delete_car_click(e):
        if len(db_data["cars"]) <= 1: return
        def confirm_delete(_):
            db_data["cars"].pop(car_name)
            if car_name in app_state["newly_added_cars"]: app_state["newly_added_cars"].remove(car_name)
            save_data(db_data)
            app_state["active_tab"] = 0
            dialog.open = False
            page.update()
            rebuild_callback()
        dialog = ft.AlertDialog(title=ft.Text("Удаление профиля"), content=ft.Text(f"Удалить '{car_name}'?"), actions=[ft.TextButton("Удалить", on_click=confirm_delete, style=ft.ButtonStyle(color=ft.Colors.RED_600))])
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    # ОРИГИНАЛЬНАЯ ПАНЕЛЬ БАЗЫ И УПРАВЛЕНИЯ МАШИНАМИ (Из твоего PDF)
    action_panel = ft.Row([
        ft.Row([
            ft.Text("База:", size=14, weight=ft.FontWeight.W_500),
            ft.IconButton(ft.Icons.CLOUD_UPLOAD, tooltip="Экспорт в Telegram", icon_color=ft.Colors.BLUE_600, on_click=lambda _: show_custom_file_manager_dialog(page, "export", None, show_message)),
            ft.IconButton(ft.Icons.CLOUD_DOWNLOAD, tooltip="Импорт из Telegram", icon_color=ft.Colors.GREEN_600, on_click=lambda _: show_custom_file_manager_dialog(page, "import", None, show_message)),
            ft.IconButton(ft.Icons.BAR_CHART_ROUNDED, tooltip='Переключить Графики / Список ТО', 
            icon_color=ft.Colors.ORANGE_800, 
            on_click=lambda _: [app_state.update({'view_mode': 'analytics' if app_state.get('view_mode') != 'analytics' else 'list'}), rebuild_callback()]),
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
                action_panel, 
                ft.Divider(height=5, color=ft.Colors.BLACK_12), 
                ft.Text("Обновление данных пробега", size=16, weight=ft.FontWeight.BOLD), 
                ft.Row([current_odo_input, daily_input], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                ft.Text(hist_text, size=11, color=ft.Colors.GREY_600, italic=True),
                ft.Row([
                    # СТАНДАРТ FLET 1.0+: Используем чистый ft.Button вместо устаревшего ElevatedButton
                    ft.Button("Обновить пробег и прогноз", on_click=update_forecast_click, height=45), 
                    # ВОССТАНОВЛЕНИЕ: Кнопка "История пробега" встала рядом с кнопкой обновления пробега
                    ft.Button("⏱️ История пробега", on_click=lambda _: show_car_odometer_history_dialog(page, db_data, car_profile, rebuild_callback, show_message), height=45)
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=15)
            ], spacing=12), padding=12
        )
    )
    
        # Проверка режима отображения (Списки или Аналитика с прогресс-барами)
    if app_state.get("view_mode") == "analytics":
        # Создаем контейнер, наверх кидаем header_card, снизу — прогресс-бары
        analytics_container = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)
        analytics_container.controls.append(header_card)
        analytics_container.controls.append(generate_analytics_view(page, car_profile))
        return analytics_container
        
    return build_maintenance_list_cards(page, db_data, car_profile, header_card, rebuild_callback, show_message)




# Фрагмент №5.3: Отрисовка раскрывающихся карточек регламента автомобиля по стандарту Flet 1.0+
def build_maintenance_list_cards(page, db_data, car_profile, header_card, rebuild_callback, show_message):
    import flet as ft
    from datetime import datetime, timedelta

    current_km = car_profile.get("odometer", {}).get("value", 0)
    daily_run = car_profile.get("daily_mileage", 45)
    tasks = car_profile.get("maintenance_data", {})
    
    content_list = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)
    content_list.controls.append(header_card)
    
    def add_custom_task_click_inner(e):
        # Логика открытия окна добавления новой работы (из твоего Фрагмента №5.1)
        task_title = ft.TextField(label="Название работы")
        task_interval = ft.TextField(label="Интервал (км)", value="10000")
        def save_custom_task(_):
            title = task_title.value.strip()
            if not title or title in car_profile.get("maintenance_data", {}): return
            try:
                if "maintenance_data" not in car_profile: car_profile["maintenance_data"] = {}
                car_profile["maintenance_data"][title] = {"last_service": current_km, "interval": int(task_interval.value), "date": datetime.now().strftime("%d.%m.%Y"), "history": []}
                save_data(db_data)
                dialog.open = False
                page.update()
                rebuild_callback()
            except ValueError: pass
        dialog = ft.AlertDialog(title=ft.Text("Добавить свою работу"), content=ft.Column([task_title, task_interval], tight=True), actions=[ft.TextButton("Сохранить", on_click=save_custom_task)])
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    if not tasks:
        # Даже если работ нет, выводим строчку заголовка ТО с кнопкой Плюс
        status_header = ft.Row([
            ft.Text("Статус регламентных работ:", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_800),
            ft.IconButton(ft.Icons.ADD_CIRCLE, tooltip="Добавить работу", icon_color=ft.Colors.BLUE_600, on_click=add_custom_task_click_inner)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        content_list.controls.append(ft.Container(content=status_header, padding=ft.Padding.only(top=10, bottom=5)))
        
        content_list.controls.append(
            ft.Container(
                content=ft.Text("Для этого автомобиля еще не добавлено ни одного регламента ТО.", size=14, color=ft.Colors.GREY_500),
                alignment=ft.Alignment.CENTER,
                padding=ft.Padding.only(top=20)
            )
        )
        return content_list

    # ИСПРАВЛЕНО: Кнопка добавить работу (Плюс в кружочке) сидит прямо в строчке заголовка статуса регламентов!
    status_header = ft.Row([
        ft.Text("Статус регламентных работ по автомобилю:", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_800),
        ft.IconButton(ft.Icons.ADD_CIRCLE, tooltip="Добавить работу", icon_color=ft.Colors.BLUE_600, on_click=add_custom_task_click_inner)
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    
    content_list.controls.append(ft.Container(content=status_header, padding=ft.Padding.only(left=0, top=10, right=0, bottom=5)))

    for task_name, info in tasks.items():
        last_service = info.get("last_service", 0)
        interval = info.get("interval", 10000)
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

        reset_fn, change_fn, delete_fn = create_task_actions(
            page, db_data, car_profile, task_name, current_km, rebuild_callback, show_message
        )

        tile = ft.ExpansionTile(
            title=ft.Text(task_name, size=16, weight=ft.FontWeight.BOLD),
            subtitle=ft.Text(f"{status_text} | Прогноз: {forecast_str}", color=status_color, size=13),
            controls=[
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(f"Интервал ТО: {interval} км", size=14),
                            ft.Text(f"Последний сервис: {last_service} км", size=14),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Container(height=10),
                        ft.Row([
                            ft.Button(
                                "Ввод истории",
                                icon=ft.Icons.HISTORY,
                                on_click=lambda e, t=task_name: show_add_task_history_dialog(page, db_data, t, car_profile, rebuild_callback, show_message),
                                style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE, color=ft.Colors.WHITE)
                            ),
                            ft.IconButton(ft.Icons.EDIT, icon_color=ft.Colors.BLUE_600, tooltip="Редактировать регламент", on_click=change_fn),
                            ft.IconButton(ft.Icons.CHECK_CIRCLE, icon_color=ft.Colors.GREEN_600, tooltip="Отметить выполнение", on_click=reset_fn),
                            ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED_400, tooltip="Удалить регламент", on_click=delete_fn)
                        ], alignment=ft.MainAxisAlignment.END, spacing=10)
                    ]),
                    padding=ft.Padding.all(15),
                    bgcolor=ft.Colors.GREY_50
                )
            ]
        )
        content_list.controls.append(tile)

    return content_list



# Фрагмент №5.2: Кроссплатформенный менеджер бэкапов через скрытые сетевые запросы к Telegram Bot API
import requests
import json
import io
from concurrent.futures import ThreadPoolExecutor

TG_TOKEN = "8859678783:AAHA9MbUhnS17bmf7w-vlNLkwYPiI-gOVuU"
TG_CHAT_ID = "1036911003"

network_executor = ThreadPoolExecutor(max_workers=2)

def show_custom_file_manager_dialog(page, mode, on_file_selected_callback, show_message_callback):
    import flet as ft
    import requests, json, io
    from concurrent.futures import ThreadPoolExecutor

    TG_TOKEN = "8859678783:AAHA9MbUhnS17bmf7w-vlNLkwYPiI-gOVuU"
    TG_CHAT_ID = "1036911003"
    
    network_executor = ThreadPoolExecutor(max_workers=2)
    
    URL_EXPORT = f"https://api.telegram.org/bot{TG_TOKEN}/sendDocument"
    URL_UPDATES = f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates"
    URL_FILE_INFO = f"https://api.telegram.org/bot{TG_TOKEN}/getFile"
    URL_DOWNLOAD_BASE = f"https://telegram.org{TG_TOKEN}/"
    
    if mode == "export":
        def async_export_worker():
            try:
                print("[LOG] Старт асинхронного экспорта базы...")
                current_db_data = None
                
                try: current_db_data = load_data()
                except: pass
                
                # Если база данных на телефоне еще пустая, создаем валидный стартовый каркас
                if not current_db_data or "cars" not in current_db_data:
                    current_db_data = {"cars": {}, "history": []}
                    
                json_text = json.dumps(current_db_data, ensure_ascii=False, indent=4)
                file_stream = io.BytesIO(json_text.encode("utf-8"))
                file_stream.name = "CarJournal_database.json"
                
                payload_data = {"chat_id": int(TG_CHAT_ID), "caption": "📦 Резервная копия базы Журнала ТО"}
                payload_files = {"document": file_stream}
                
                session = requests.Session()
                session.trust_env = False
                
                response = session.post(URL_EXPORT, data=payload_data, files=payload_files, timeout=15)
                
                if response.status_code == 200:
                    show_message_callback("Бэкап успешно отправлен в Telegram!")
                else:
                    show_message_callback(f"Ошибка облака: Код {response.status_code}")
            except Exception as ex:
                show_message_callback(f"Сбой сети: {str(ex)}")
                
        network_executor.submit(async_export_worker)
        
    elif mode == "import":
        progress_ring = ft.ProgressRing(width=30, height=30, stroke_width=3)
        status_text = ft.Text("Поиск последнего бэкапа в Telegram...", size=14)
        
        def close_dialog(e):
            dialog.open = False
            page.update()
            
        def async_import_worker():
            try:
                session = requests.Session()
                session.trust_env = False
                
                response = session.get(URL_UPDATES, timeout=15)
                if response.status_code != 200:
                    status_text.value = f"Ошибка сети: Код {response.status_code}"
                    page.update()
                    return
                    
                updates = response.json().get("result", [])
                backup_file_id = None
                
                for update in reversed(updates):
                    message = update.get("message", {})
                    document = message.get("document", {})
                    if document and "json" in document.get("file_name", "").lower():
                        backup_file_id = document.get("file_id")
                        break
                        
                if not backup_file_id:
                    status_text.value = "Бэкап в облаке не найден!"
                    page.update()
                    return
                    
                status_text.value = "Скачивание файла..."
                page.update()
                
                file_info_res = session.get(URL_FILE_INFO, params={"file_id": backup_file_id})
                file_path = file_info_res.json().get("result", {}).get("file_path")
                
                download_res = session.get(URL_DOWNLOAD_BASE + file_path, timeout=15)
                imported_json = json.loads(download_res.text)
                
                if "cars" in imported_json:
                    try: save_data(imported_json)
                    except Exception as e: print(f"Ошибка сохранения: {e}")
                        
                    # ХАК ДЛЯ ОЖИВЛЕНИЯ UI: Сброс кэша оперативной памяти
                    if 'db_data' in globals():
                        global db_data
                        db_data.clear()
                        db_data.update(load_data())
                    elif 'db' in globals():
                        global db
                        db.clear()
                        db.update(load_data())
                    status_text.value = "Синхронизация успешна!"
                    page.update()
                    show_message_callback("База успешно восстановлена!")
                    
                    if page.data and "refresh_ui" in page.data:
                        page.data["refresh_ui"]()
                    dialog.open = False
                    page.update()
                else:
                    status_text.value = "Файл поврежден."
                    page.update()
            except Exception as ex:
                status_text.value = f"Ошибка: {str(ex)}"
                page.update()

        def start_sync_import(e):
            confirm_btn.visible = False
            action_container.content = progress_ring
            page.update()
            network_executor.submit(async_import_worker)
            
        confirm_btn = ft.FilledButton(
            "Начать импорт", 
            on_click=start_sync_import, 
            style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.BLUE)
        )
        action_container = ft.Container(content=confirm_btn)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Облачный Импорт"),
            content=ft.Column([status_text, ft.Container(height=10), action_container], tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            actions=[ft.TextButton("Отмена", on_click=close_dialog)],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

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


# Фрагмент №9.2: Полное восстановление оригинальной бизнес-логики интерфейса без дубликата заголовка
def build_maintenance_list(page, db_data, car_name, car_profile, header_card, rebuild_callback, show_message, add_task_fn=None):
    import flet as ft
    from datetime import datetime, timedelta
    
    content_list = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)
    content_list.controls.append(header_card)
    
    current_km = car_profile.get("odometer", {}).get("value", 0)
    daily_run = car_profile.get("daily_mileage", 45)
    maintenance_tasks = car_profile.get("maintenance_data", {})
    
    if not maintenance_tasks:
        content_list.controls.append(
            ft.Container(
                content=ft.Text("Для этого автомобиля еще не добавлено ни одного регламента ТО.", 
                                size=14, color=ft.Colors.GREY_500),
                alignment=ft.Alignment.CENTER,
                padding=ft.Padding.only(top=20)
            )
        )
        return content_list
        
    for task_name, task_data in maintenance_tasks.items():
        interval = task_data.get("interval", 0)
        last_service = task_data.get("last_service", 0)
        
        target_mileage = last_service + interval
        remaining = target_mileage - current_km
        
        # Расчет прогнозной даты ТО
        if remaining > 0 and daily_run > 0:
            days_left = remaining / daily_run
            future_date = datetime.now() + timedelta(days=days_left)
            forecast_str = future_date.strftime("%d.%m.%Y")
        else:
            forecast_str = "Срочно ТО!"
            
        # Определение цвета и статуса износа
        if remaining <= 0:
            status_color = ft.Colors.RED_600
            subtitle_str = f"Просрочено на {abs(remaining)} км! | Прогноз: {forecast_str}"
        elif remaining <= 500:
            status_color = ft.Colors.ORANGE_700
            subtitle_str = f"Осталось: {remaining} км (Скоро ТО) | Прогноз: {forecast_str}"
        else:
            status_color = ft.Colors.GREEN_700
            subtitle_str = f"Осталось: {remaining} км | Прогноз: {forecast_str}"
            
        # Генерация замыканий для кнопок управления
        reset_fn, change_fn, delete_fn = create_task_actions(
            page, db_data, car_profile, task_name, current_km, rebuild_callback, show_message
        )
        
        tile = ft.ExpansionTile(
            title=ft.Text(task_name, size=16, weight=ft.FontWeight.BOLD),
            subtitle=ft.Text(subtitle_str, color=status_color, size=13),
            controls=[
                ft.Container(
                    content=ft.Column([
                        # Добавлено название работы внутрь карточки
                        ft.Text(f"🛠️ Выполняемая работа: {task_name}", size=14, weight=ft.FontWeight.W_500),
                        ft.Container(height=5),
                        ft.Row([
                            ft.Text(f"Интервал ТО: {interval} км", size=14),
                            ft.Text(f"Последний сервис: {last_service} км", size=14),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Container(height=10),
                        ft.Row([
                            ft.Button(
                                "Ввод истории",
                                icon=ft.Icons.HISTORY,
                                on_click=lambda e, t=task_name: show_add_task_history_dialog(
                                    page, db_data, t, car_profile, rebuild_callback, show_message
                                ),
                                style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE, color=ft.Colors.WHITE)
                            ),
                            ft.IconButton(ft.Icons.EDIT, icon_color=ft.Colors.BLUE_600, tooltip="Редактировать", on_click=change_fn),
                            ft.IconButton(ft.Icons.CHECK_CIRCLE, icon_color=ft.Colors.GREEN_600, tooltip="Выполнено", on_click=reset_fn),
                            ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED_400, tooltip="Удалить", on_click=delete_fn)
                        ], alignment=ft.MainAxisAlignment.END, spacing=10)
                    ]),
                    padding=ft.Padding.all(15),
                    bgcolor=ft.Colors.GREY_50
                )
            ]
        )
        content_list.controls.append(tile)
        
    return content_list


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



# Фрагмент №12: Главная точка входа main по стандарту Flet 1.0+ с корректной работой со словарем app_state
APP_VERSION = "1.2.5"
BUILD_NUMBER = "11"

def main(page: ft.Page):
    import flet as ft
    
    # 1. Настройка светлой темы и параметров окна
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = ft.Colors.SURFACE_CONTAINER_LOW
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.AMBER)
    page.title = "Журнал ТО"
    page.window_width = 1200
    page.window_height = 800
    
    global app_state, db_data
    if 'app_state' not in globals():
        app_state = {"view_mode": "list", "active_tab": 0, "newly_added_cars": []}
        
    db_data = load_data()
    
    # 2. Главный обработчик отрисовки
    def rebuild_ui():
        page.clean()
        
        cars_dict = db_data.get("cars", {})
        if not cars_dict:
            page.add(ft.Text("В базе данных нет автомобилей. Добавьте первый автомобиль.", size=16))
            page.update()
            return
            
        car_names = list(cars_dict.keys())
        
        selected_car = app_state.get("selected_car")
        if not selected_car or selected_car not in cars_dict:
            selected_car = car_names[0]
            app_state["selected_car"] = selected_car
            
        # Панель переключения машин на чистых кнопках ft.Row
        car_buttons_row = ft.Row(spacing=10, scroll=ft.ScrollMode.AUTO)
        
        for name in car_names:
            is_selected = (name == selected_car)
            
            def make_click_handler(car_name_to_select):
                return lambda _: [app_state.update({"selected_car": car_name_to_select}), rebuild_ui()]
            
            btn = ft.Container(
                content=ft.Text(
                    str(name), 
                    color=ft.Colors.WHITE if is_selected else ft.Colors.BLACK,
                    weight=ft.FontWeight.BOLD if is_selected else ft.FontWeight.NORMAL,
                    size=14
                ),
                bgcolor=ft.Colors.AMBER_700 if is_selected else ft.Colors.GREY_200,
                # ИСПРАВЛЕНО ПО СТАНДАРТУ FLET 1.0+ (лево, верх, право, низ)
                padding=ft.Padding(16, 8, 16, 8),
                border_radius=8,
                on_click=make_click_handler(name),
                animate=200
            )
            car_buttons_row.controls.append(btn)
                
        car_profile = cars_dict[selected_car]
        
        if 'generate_car_view' in globals():
            main_layout = generate_car_view(
                page=page,
                db_data=db_data,
                car_name=selected_car,
                car_profile=car_profile,
                rebuild_callback=rebuild_ui,
                show_message=lambda msg: page.show_snack_bar(ft.SnackBar(ft.Text(msg)))
            )
            
            # Собираем интерфейс: сверху кнопки машин, ниже — весь контент автомобиля
            final_layout = ft.Column(
                expand=True,
                controls=[
                    # ИСПРАВЛЕНО ПО СТАНДАРТУ FLET 1.0+
                    ft.Container(content=car_buttons_row, padding=ft.Padding(5, 5, 0, 15)),
                    main_layout
                ]
            )
            page.add(final_layout)
        else:
            page.add(ft.Text("Ошибка: Функция generate_car_view не найдена.", color=ft.Colors.RED))
            
        page.update()
        
    page.data = {"refresh_ui": rebuild_ui}
    rebuild_ui()

if __name__ == "__main__":
    import flet as ft
    ft.run(main)
