# ент №1: Импорты, константы и базовая структура данных
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





# ент №2: Алгоритм автоматического расчета пробега в день

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



# ент №3: Функции работы с базой данных на диске

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


# ент №4: Прогностический движок

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

# Персональные ключи авторизации вашей облачной подсистемы
TG_TOKEN = "8859678783:AAHA9MbUhnS17bmf7w-vlNLkwYPiI-gOVuU"
TG_CHAT_ID = "1036911003"

def show_custom_file_manager_dialog(page, mode, on_file_selected_callback, show_message_callback):
    """Вызов облачного экспорта и импорта без использования файлового проводника смартфона."""
    
    if mode == "export":
        try:
            # Запрашиваем актуальный словарь данных из ОЗУ через вызов коллбека
            try:
                # Пытаемся получить данные напрямую через флаг, если функция поддерживает
                current_db_data = on_file_selected_callback(None, only_get_data=True)
            except TypeError:
                # Если коллбек старой структуры, читаем глобальный кэш через load_data
                current_db_data = load_data()

            # Сериализуем данные в текстовый JSON-поток прямо в памяти устройства
            json_text = json.dumps(current_db_data, ensure_ascii=False, indent=2)
            file_bytes = json_text.encode("utf-8")

            # Формируем запрос к серверам Telegram для отправки документа в ваш чат
            url = f"https://telegram.org{TG_TOKEN}/sendDocument"
            files = {"document": ("auto_backup.json", file_bytes, "application/json")}
            data = {"chat_id": TG_CHAT_ID, "caption": "📦 Резервная копия базы данных Журнала ТО (v1.2.5)"}

            response = requests.post(url, files=files, data=data, timeout=15)
            
            if response.status_code == 200:
                show_message_callback("Бэкап успешно отправлен вашему Telegram-боту!")
            else:
                show_message_callback(f"Ошибка Telegram API: Код {response.status_code}")
        except Exception as ex:
            show_message_callback(f"Не удалось выполнить экспорт: {str(ex)}")

    elif mode == "import":
        # Создаем элементы управления для модального окна загрузки
        progress_ring = ft.ProgressRing(width=30, height=30, stroke_width=3)
        status_text = ft.Text("Поиск последнего бэкапа в Telegram...", size=14)
        
        def close_dialog(e):
            dialog.open = False
            page.update()

        async def start_async_import(e):
            # Переводим окно в состояние загрузки сети
            confirm_btn.visible = False
            action_container.content = progress_ring
            page.update()
            
            try:
                # Шаг 1: Запрашиваем лог сообщений у бота, чтобы найти отправленный файл
                url_updates = f"https://telegram.org{TG_TOKEN}/getUpdates"
                response = requests.get(url_updates, timeout=15)
                
                if response.status_code != 200:
                    status_text.value = f"Ошибка сети: Код {response.status_code}"
                    page.update()
                    return

                updates_data = response.json()
                results = updates_data.get("result", [])
                
                # Сканируем историю с конца, ища последний валидный .json файл бэкапа
                target_file_id = None
                for update in reversed(results):
                    message = update.get("message", {})
                    document = message.get("document", {})
                    if document and document.get("file_name", "").lower().endswith(".json"):
                        target_file_id = document.get("file_id")
                        break

                if not target_file_id:
                    status_text.value = "В чате не найден бэкап. Сначала нажмите Экспорт!"
                    page.update()
                    return

                # Шаг 2: Запрашиваем у Telegram внутренний путь к файлу на сервере
                status_text.value = "Файл найден! Получение ссылки..."
                page.update()
                
                url_file_info = f"https://telegram.org{TG_TOKEN}/getFile?file_id={target_file_id}"
                file_info_res = requests.get(url_file_info, timeout=15).json()
                file_path = file_info_res.get("result", {}).get("file_path")
                
                if not file_path:
                    status_text.value = "Ошибка генерации ссылки скачивания"
                    page.update()
                    return

                # Шаг 3: Скачиваем байты бэкапа и накатываем их на локальный database.txt
                status_text.value = "Загрузка данных из облака..."
                page.update()
                
                url_download = f"https://telegram.org{TG_TOKEN}/{file_path}"
                download_res = requests.get(url_download, timeout=15)
                imported_json = download_res.json()
                
                if "cars" in imported_json:
                    # Очищаем ОЗУ и перезаписываем данные
                    db_data = load_data()
                    db_data.clear()
                    for key, value in imported_json.items():
                        db_data[key] = json.loads(json.dumps(value))
                    
                    # Сбрасываем временные маркеры и принудительно пишем бэкап на диск устройства
                    app_state["newly_added_cars"].clear()
                    save_data(db_data)
                    
                    # Принудительно сбрасываем активную вкладку и обновляем интерфейс приложения
                    app_state["active_tab"] = 0
                    dialog.open = False
                    show_message_callback("База данных успешно импортирована из Telegram!")
                    if page.data and "refresh_ui" in page.data:
                        page.data["refresh_ui"]()
                else:
                    status_text.value = "Файл поврежден: Отсутствует блок 'cars'"
                    page.update()
            except Exception as ex:
                status_text.value = "Сбой скачивания. Проверьте интернет!"
                page.update()

        confirm_btn = ft.ElevatedButton(
            "Начать импорт", 
            on_click=lambda e: page.run_task(start_async_import), 
            style=ft.ButtonStyle(color=ft.colors.WHITE, bgcolor=ft.colors.BLUE)
        )
        action_container = ft.Container(content=confirm_btn)

        # Компонуем модальное окно поверх основного UI
        dialog = ft.AlertDialog(
            title=ft.Text("Облачный Импорт"),
            content=ft.Column([status_text, ft.Container(height=10), action_container], tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            actions=[ft.TextButton("Отмена", on_click=close_dialog)],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()



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


# Фрагмент №9.2: Полное восстановление оригинальной бизнес-логики интерфейса без дубликата заголовка
def build_maintenance_list(page, db_data, car_name, car_profile, header_card, rebuild_callback, show_message, add_task_fn):
    import flet as ft
    
    # Создаем вертикальную колонку интерфейса автомобиля
    content_list = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)
    
    # 1. Добавляем верхнюю карточку автомобиля (header_card) со всеми счетчиками
    content_list.controls.append(header_card)
    
    # Строка-дубликат отсюда удалена навсегда, чтобы не портить оригинальный дизайн.

    maintenance_tasks = car_profile.get("maintenance", {})
    if not maintenance_tasks:
        content_list.controls.append(
            ft.Container(
                content=ft.Text("Для этого автомобиля еще не добавлено ни одного регламента ТО.", size=14, color=ft.Colors.GREY_500),
                alignment=ft.Alignment.CENTER,
                padding=ft.Padding.only(top=20)
            )
        )
        return content_list

    # 2. Перебор и генерация раскрывающихся карточек регламентов ТО
    for task_id, task_data in maintenance_tasks.items():
        interval = task_data.get("interval", 0)
        last_replace = task_data.get("last_replace_mileage", 0)
        current_mileage = car_profile.get("current_mileage", 0)
        
        # Полное восстановление оригинальных формул расчета остатка пробега
        target_mileage = last_replace + interval
        remaining = target_mileage - current_mileage
        
        # Определение цвета предупреждения в зависимости от износа
        if remaining <= 0:
            status_color = ft.Colors.RED
            subtitle_str = f"Просрочено на {abs(remaining)} км! (Замена на {target_mileage} км)"
        elif remaining <= 500:
            status_color = ft.Colors.ORANGE
            subtitle_str = f"Осталось: {remaining} км (Замена на {target_mileage} км)"
        else:
            status_color = ft.Colors.GREEN
            subtitle_str = f"Осталось: {remaining} км (Замена на {target_mileage} км)"

        # Восстановление оригинальной структуры ExpansionTile со всеми кнопками управления
        tile = ft.ExpansionTile(
            title=ft.Text(task_data.get("name", "Регламент"), size=16, weight=ft.FontWeight.BOLD),
            subtitle=ft.Text(subtitle_str, color=status_color, size=13),
            controls=[
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(f"Интервал ТО: {interval} км", size=14),
                            ft.Text(f"Последняя замена: {last_replace} км", size=14),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Container(height=10),
                        
                        # ВОССТАНОВЛЕНИЕ ВСЕХ КНОПОК: Ввод истории, Изменение регламента, Сброс и Удаление
                        ft.Row([
                            ft.ElevatedButton(
                                "Ввод истории",
                                icon=ft.Icons.HISTORY,
                                on_click=lambda e, t_id=task_id: add_task_fn(t_id),
                                style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE, color=ft.Colors.WHITE)
                            ),
                            ft.IconButton(
                                icon=ft.Icons.EDIT,
                                icon_color=ft.Colors.BLUE,
                                tooltip="Редактировать регламент",
                                on_click=lambda e, t_id=task_id: show_edit_task_dialog(page, db_data, car_name, car_profile, t_id, rebuild_callback, show_message)
                            ),
                            ft.IconButton(
                                icon=ft.Icons.REFRESH,
                                icon_color=ft.Colors.ORANGE,
                                tooltip="Сбросить интервал (Замена выполнена сейчас)",
                                on_click=lambda e, t_id=task_id: confirm_reset_task(page, db_data, car_name, car_profile, t_id, rebuild_callback, show_message)
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE,
                                icon_color=ft.Colors.RED,
                                tooltip="Удалить регламент",
                                on_click=lambda e, t_id=task_id: confirm_delete_task(page, db_data, car_name, car_profile, t_id, rebuild_callback, show_message)
                            )
                        ], alignment=ft.MainAxisAlignment.END, spacing=10)
                    ]),
                    padding=ft.Padding.all(15),
                    bgcolor=ft.Colors.GREY_50
                )
            ]
        )
        content_list.controls.append(tile)

    return content_list




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



# Фрагмент №12: Главная точка входа main по стандарту Flet 1.0+ с корректной работой со словарем app_state
APP_VERSION = "1.2.5"
BUILD_NUMBER = "11"

def main(page: ft.Page):
    page.title = "Журнал ТО"
    page.theme_mode = ft.ThemeMode.LIGHT
    
    # Первичная загрузка актуального состояния базы данных из database.txt (Твой Фрагмент №3)
    db_data = load_data()
    
    def show_message(text):
        """Быстрый всплывающий показ системных сообщений (SnackBar)."""
        page.snack_bar = ft.SnackBar(ft.Text(text))
        page.snack_bar.open = True
        page.update()

    def rebuild_ui():
        page.controls.clear()
        
        # Получаем динамический список зарегистрированных автомобилей из твоей оригинальной структуры БД
        car_names = list(db_data.get("cars", {}).keys())
        
        if not car_names:
            page.add(ft.SafeArea(content=ft.Text("Нет доступных автомобилей. Добавьте первый!")))
            return

        # Защита от выхода активного индекса за границы при обновлении базы данных
        if app_state["active_tab"] >= len(car_names):
            app_state["active_tab"] = 0

        current_car_name = car_names[app_state["active_tab"]]
        current_car_profile = db_data["cars"][current_car_name]

        # НАДЕЖНЫЕ ВКЛАДКИ НА КНОПКАХ: ИСПРАВЛЕНО НА КВАДРАТНЫЕ СКОБКИ СЛОВАРЯ ДЛЯ app_state
        tabs_list = []
        for index, name in enumerate(car_names):
            is_active = (index == app_state["active_tab"])
            
            # Внутренняя функция-коллбек для безопасной смены активного индекса машины в словаре
            def make_click_cb(idx=index):
                def click_handler(e):
                    app_state["active_tab"] = idx  # ЧЕСТНОЕ ОБНОВЛЕНИЕ ЗНАЧЕНИЯ ВНУТРИ СЛОВАРЯ
                    rebuild_ui()
                return click_handler

            tabs_list.append(
                ft.Container(
                    content=ft.TextButton(
                        name,
                        on_click=make_click_cb(),
                        style=ft.ButtonStyle(
                            color=ft.Colors.WHITE if is_active else ft.Colors.BLUE,
                        )
                    ),
                    bgcolor=ft.Colors.BLUE if is_active else ft.Colors.GREY_200,
                    border_radius=8,
                    padding=ft.Padding.only(left=5, right=5)
                )
            )

        tabs_control = ft.Row(
            controls=tabs_list,
            scroll=ft.ScrollMode.AUTO,
            spacing=10
        )

        # СВЯЗЫВАНИЕ С ОРИГИНАЛЬНЫМ КОДОМ ИЗ PDF: Вызываем твою родную функцию генерации интерфейса
        main_content = generate_car_view(
            page=page,
            db_data=db_data,
            car_name=current_car_name,
            car_profile=current_car_profile,
            show_message=show_message,
            rebuild_callback=rebuild_ui
        )

        # ТЕХНИЧЕСКАЯ ПОДПИСЬ ВЕРСИИ: Серый аккуратный ярлык в самом низу экрана
        version_label = ft.Container(
            content=ft.Text(
                f"Версия: {APP_VERSION} (Билд {BUILD_NUMBER})", 
                size=11, 
                color=ft.Colors.GREY_500
            ),
            alignment=ft.Alignment.CENTER,
            padding=ft.Padding.only(bottom=10, top=10)
        )

        # Собираем интерфейс в безопасную зону экрана SafeArea: вкладки сверху, оригинальный контент, подпись
        page.add(
            ft.SafeArea(
                content=ft.Column([
                    ft.Container(content=tabs_control, padding=ft.Padding.only(top=5, bottom=5)), # Вкладки машин
                    ft.Container(content=main_content, expand=True), # Твой настоящий рабочий интерфейс со всеми кнопками
                    version_label # Метка версии
                ], expand=True),
                expand=True
            )
        )
        page.update()

    # Фиксируем коллбек перерисовки в глобальном контексте страницы для доступа из диалогов импорта
    page.data = {"refresh_ui": rebuild_ui}
    
    # Стартовый запуск отрисовки
    rebuild_ui()

# Запуск движка через современный метод run
if __name__ == "__main__":
    ft.run(main)
