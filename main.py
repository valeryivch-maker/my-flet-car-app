# Фрагмент №1: Импорты, константы и базовая структура данных

import flet as ft
import json
import os
from datetime import datetime, timedelta

DB_FILE = "database.txt"


def get_default_car_data():
    """Генерирует чистый шаблон данных для новой машины."""
    current_date = datetime.now().strftime("%d.%m.%Y")
    past_date = (
        datetime.now() - timedelta(days=30)
    ).strftime("%d.%m.%Y")

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


# Фрагмент №5.1: Логика действий внутри журнала ремонтов ТО

def create_task_history_ops(
    page, db_data, p, t, target_item, render_fn, rebuild, show_msg, get_sort_key
):
    """Генерирует замыкания для изменения и удаления строк в журнале ТО."""
    
    def delete_confirmed(_):
        h_list = p["history"]
        if target_item in h_list:
            h_list.remove(target_item)
            rem_h = [h for h in h_list if h["task"] == t]
            m_data = p["maintenance_data"][t]
            
            if rem_h:
                latest = max(rem_h, key=get_sort_key)
                m_data.update({
                    "last_service": latest["odometer"],
                    "date": latest["date"]
                })
            else:
                m_data.update({"last_service": 0, "date": "—"})
            
            save_data(db_data)
            del_dlg.open = False
            page.update()
            render_fn()
            rebuild()
            show_msg("Запись из журнала удалена")

    def open_delete_dialog(_):
        nonlocal del_dlg
        del_dlg = ft.AlertDialog(
            title=ft.Text("Удалить запись?"),
            content=ft.Text(
                f"Удалить ТО на пробеге {target_item['odometer']} км "
                f"от {target_item['date']}?"
            ),
            actions=[
                ft.TextButton("Удалить", on_click=delete_confirmed, style=ft.ButtonStyle(color=ft.Colors.RED_600)),
                ft.TextButton("Отмена", on_click=lambda _: [setattr(del_dlg, "open", False), page.update()])
            ]
        )
        page.overlay.append(del_dlg)
        del_dlg.open = True
        page.update()

    def save_changes(_):
        try:
            n_km = int(edit_km.value)
            n_date = edit_date.value.strip()
            datetime.strptime(n_date, "%d.%m.%Y")
            
            target_item["odometer"] = n_km
            target_item["date"] = n_date
            
            h_list = p["history"]
            rem_h = [h for h in h_list if h["task"] == t]
            m_data = p["maintenance_data"][t]
            
            latest = max(rem_h, key=get_sort_key)
            m_data.update({
                "last_service": latest["odometer"],
                "date": latest["date"]
            })
            
            save_data(db_data)
            edit_dlg.open = False
            page.update()
            render_fn()
            rebuild()
            show_msg("Запись изменена")
        except ValueError:
            show_msg("Ошибка: Неверный формат!")

    def open_edit_dialog(_):
        nonlocal edit_dlg, edit_km, edit_date
        edit_km = ft.TextField(
            label="Пробег (км)", value=str(target_item["odometer"]),
            keyboard_type=ft.KeyboardType.NUMBER
        )
        edit_date = ft.TextField(label="Дата", value=target_item["date"])
        
        edit_dlg = ft.AlertDialog(
            title=ft.Text("Редактировать запись"),
            content=ft.Column([edit_km, edit_date], tight=True, spacing=10),
            actions=[
                ft.TextButton("Сохранить", on_click=save_changes),
                ft.TextButton("Отмена", on_click=lambda _: [setattr(edit_dlg, "open", False), page.update()])
            ]
        )
        page.overlay.append(edit_dlg)
        edit_dlg.open = True
        page.update()

    del_dlg = None
    edit_dlg = None
    edit_km = None
    edit_date = None
    
    return open_edit_dialog, open_delete_dialog


# Фрагмент №5.2: Собственный безопасный UI-проводник и дисковый навигатор
def show_custom_file_manager_dialog(page, mode, on_file_selected_callback, show_message_callback):
    """Внутренний изолированный проводник папок на чистом Python (Вариант 6)."""
    import platform
    
    # Определение стартовой папки в зависимости от платформы
    if platform.system() == "Java" or hasattr(sys, "getandroidapkname"):  # Проверка на Android среду
        try:
            # Стандартный путь к папке Загрузки на большинстве устройств Android
            current_path = "/storage/emulated/0/Download"
            # Если папка по какой-то причине недоступна, откатываемся на корень внешнего хранилища
            if not os.path.exists(current_path):
                current_path = "/storage/emulated/0"
        except Exception:
            current_path = os.getcwd()
    else:
        # Для Windows/Linux/macOS оставляем текущую рабочую директорию
        current_path = os.getcwd()
    
    file_list_column = ft.Column(scroll=ft.ScrollMode.AUTO, height=280)
    path_text = ft.Text(value=current_path, size=12, color=ft.Colors.GREY_700, weight=ft.FontWeight.BOLD)
    
    dialog_controls = [
        path_text, 
        ft.Divider(height=10), 
        file_list_column, 
        ft.Divider(height=10)
    ]
    
    if mode == "export":
        file_name_input = ft.TextField(label="Имя файла сохранения", value="auto_backup.json")
        dialog_controls.append(file_name_input)

    def refresh_folder_contents():
        nonlocal current_path
        file_list_column.controls.clear()
        path_text.value = current_path
        try:
            items = os.listdir(current_path)
            file_list_column.controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.ARROW_UPWARD, color=ft.Colors.BLUE_700), 
                    title=ft.Text(".. [На уровень вверх]"), 
                    on_click=lambda _: go_up_folder()
                )
            )
            for item in sorted(items):
                full_path = os.path.join(current_path, item)
                if os.path.isdir(full_path):
                    file_list_column.controls.append(
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.FOLDER, color=ft.Colors.AMBER_700), 
                            title=ft.Text(item), 
                            on_click=lambda _, p=full_path: navigate_into_folder(p)
                        )
                    )
                elif item.endswith(".json") or item.endswith(".txt"):
                    file_list_column.controls.append(
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.INSERT_DRIVE_FILE, color=ft.Colors.BLUE_GREY_500), 
                            title=ft.Text(item), 
                            on_click=lambda _, p=full_path: select_target_file(p)
                        )
                    )
        except Exception:
            file_list_column.controls.append(
                ft.Text("Доступ ограничен. Проверьте разрешения приложения!", color=ft.Colors.RED_500)
            )
        page.update()

    def navigate_into_folder(new_path):
        nonlocal current_path
        current_path = new_path
        refresh_folder_contents()

    def go_up_folder():
        nonlocal current_path
        current_path = os.path.dirname(current_path)
        refresh_folder_contents()

    def select_target_file(file_path):
        if mode == "import":
            on_file_selected_callback(file_path)
            page.close(dialog)

    def handle_export_confirmation(_):
        if mode == "export":
            name = file_name_input.value.strip()
            if not name: 
                return
            if not name.endswith(".json"): 
                name += ".json"
            on_file_selected_callback(os.path.join(current_path, name))
            page.close(dialog)
 
    dialog_action_btn = ft.TextButton("Экспортировать сюда", on_click=handle_export_confirmation) if mode == "export" else ft.TextButton("Закрыть", on_click=lambda _: page.close(dialog))
 
    dialog = ft.AlertDialog(
        title=ft.Text("Экспорт данных" if mode == "export" else "Выберите файл импорта"),
        content=ft.Container(content=ft.Column(dialog_controls, tight=True, spacing=5), width=450),
        actions=[dialog_action_btn]
    )
 
    page.open(dialog)
    refresh_folder_contents()





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



# Фрагмент №10: Кастомный файловый менеджер

def show_custom_file_manager_dialog(
    page, mode, on_file_selected, show_message
):
    """Прямой автоматический экспорт/импорт без сканирования папок ОС."""
    # Задаем жесткий, легальный путь к документам Android устройства
    backup_path = "/storage/emulated/0/Documents/auto_backup.json"
    
    # Если это ПК или старый телефон, берем стандартный путь документов
    if not os.path.exists("/storage/emulated/0/"):
        base_dir = os.path.expanduser("~")
        backup_path = os.path.join(base_dir, "Documents", "auto_backup.json")

    def handle_action(_):
        try:
            on_file_selected(backup_path)
            dialog.open = False
            page.update()
        except Exception as ex:
            show_message(f"Ошибка операции: {ex}")

    def close_dlg(_):
        dialog.open = False
        page.update()

    if mode == "export":
        title_text = "Экспорт базы данных"
        body_text = f"Файл будет сохранен в папку Документы под именем 'auto_backup.json'.\n\nПолный путь: {backup_path}"
        btn_text = "Экспортировать"
    else:
        title_text = "Импорт базы данных"
        body_text = f"Приложение попытается загрузить файл 'auto_backup.json' из вашей папки Документы.\n\nУбедитесь, что файл находится там."
        btn_text = "Импортировать"

    dialog = ft.AlertDialog(
        title=ft.Text(title_text),
        content=ft.Container(
            content=ft.Text(body_text, size=14),
            width=400,
            padding=5
        ),
        actions=[
            ft.TextButton(btn_text, on_click=handle_action),
            ft.TextButton("Отмена", on_click=close_dlg)
        ]
    )
    page.overlay.append(dialog)
    dialog.open = True
    page.update()





# Фрагмент №11: Методы управления профилями машин

def setup_car_profile_actions(
    page, db_data, car_name, show_message, rebuild
):
    """Методы для управления карточками машин."""

    def add_car_click(e):
        name_in = ft.TextField(label="Модель")

        def save_new(_):
            n = name_in.value.strip()
            if not n or n in db_data["cars"]:
                return
            db_data["cars"][n] = get_default_car_data()
            save_data(db_data)
            dlg.open = False
            page.update()
            rebuild()

        dlg = ft.AlertDialog(
            title=ft.Text("Добавить авто"),
            content=ft.Column([name_in], tight=True),
            actions=[
                ft.TextButton(
                    "Добавить", on_click=save_new
                )
            ],
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def edit_name_click(e):
        name_in = ft.TextField(
            label="Имя", value=car_name
        )

        def save_edit(_):
            n = name_in.value.strip()
            if (
                not n
                or n == car_name
                or n in db_data["cars"]
            ):
                return
            db_data["cars"][n] = db_data["cars"].pop(
                car_name
            )
            save_data(db_data)
            dlg.open = False
            page.update()
            rebuild()

        dlg = ft.AlertDialog(
            title=ft.Text("Редактировать имя"),
            content=ft.Column([name_in], tight=True),
            actions=[
                ft.TextButton(
                    "Сохранить", on_click=save_edit
                )
            ],
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def delete_car_click(e):
        if len(db_data["cars"]) <= 1:
            return

        def confirm_del(_):
            db_data["cars"].pop(car_name)
            save_data(db_data)
            dlg.open = False
            page.update()
            rebuild()

        dlg = ft.AlertDialog(
            title=ft.Text("Удаление профиля"),
            content=ft.Text(f"Удалить '{car_name}'?"),
            actions=[
                ft.TextButton(
                    "Удалить",
                    on_click=confirm_del,
                    style=ft.ButtonStyle(
                        color=ft.Colors.RED_600
                    ),
                )
            ],
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    return (
        add_car_click,
        edit_name_click,
        delete_car_click,
    )


# Фрагмент №12: Панель пробега автомобиля и создание карточки вида

def generate_car_view(
    page,
    db_data,
    car_name,
    car_profile,
    show_message,
    rebuild_callback,
):
    """Генерация основного экрана автомобиля."""
    odo_data = car_profile.get(
        "odometer", {"value": 125000, "date": "—"}
    )
    lbl_odo = (
        f"Пробег (км) [от {odo_data.get('date', '—')}]"
    )

    current_odo_input = ft.TextField(
        label=lbl_odo,
        value=str(odo_data.get("value", 125000)),
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
    )
    daily_input = ft.TextField(
        label="Пробег в день (км)",
        value=str(car_profile.get("daily_mileage", 45)),
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
    )

    def execute_custom_export(full_path):
        try:
            # ИСПРАВЛЕНО: Перед экспортом принудительно перечитываем структуру с диска,
            # чтобы подтянулись все новые и измененные имена машин
            fresh_db_data = load_data()
            with open(
                full_path, "w", encoding="utf-8"
            ) as f:
                json.dump(
                    fresh_db_data,
                    f,
                    ensure_ascii=False,
                    indent=4,
                )
            show_message("Экспорт завершен!")
        except Exception as ex:
            show_message(f"Ошибка экспорта: {ex}")

    def execute_custom_import(full_path):
        try:
            with open(
                full_path, "r", encoding="utf-8"
            ) as f:
                imported_json = json.load(f)
                if "cars" in imported_json:
                    save_data(imported_json)
                    rebuild_callback()
                    show_message("База импортирована!")
                else:
                    show_message("Неверный формат!")
        except Exception as ex:
            show_message(f"Ошибка импорта: {ex}")

    def update_forecast_click(e):
        try:
            val = int(current_odo_input.value)
            now_str = datetime.now().strftime(
                "%d.%m.%Y"
            )
            car_profile["odometer"] = {
                "value": val,
                "date": now_str,
            }
            car_profile["daily_mileage"] = int(
                daily_input.value
            )
            h_list = car_profile["odometer_history"]

            if not any(
                h["value"] == val for h in h_list
            ):
                h_list.append(
                    {"value": val, "date": now_str}
                )

            car_profile[
                "daily_mileage"
            ] = recalculate_auto_daily_mileage(
                car_profile
            )
            save_data(db_data)
            rebuild_callback()
            show_message("Данные обновлены!")
        except ValueError:
            show_message("Ошибка: Проверьте поля!")

    def add_custom_task_click(e):
        t_title = ft.TextField(label="Название")
        t_int = ft.TextField(
            label="Интервал", value="10000"
        )

        def save_custom_task(_):
            title = t_title.value.strip()
            m_data = car_profile["maintenance_data"]
            if not title or title in m_data:
                return
            try:
                km = int(current_odo_input.value)
                now_date = datetime.now().strftime(
                    "%d.%m.%Y"
                )
                
                m_data[title] = {
                    "last_service": km,
                    "interval": int(t_int.value),
                    "date": now_date,
                }
                
                car_profile["history"].append(
                    {
                        "task": title,
                        "odometer": km,
                        "date": now_date
                    }
                )
                
                save_data(db_data)
                dlg.open = False
                page.update()
                rebuild_callback()
            except ValueError:
                pass

        dlg = ft.AlertDialog(
            title=ft.Text("Добавить свою работу"),
            content=ft.Column(
                [t_title, t_int], tight=True
            ),
            actions=[
                ft.TextButton(
                    "Сохранить",
                    on_click=save_custom_task,
                )
            ],
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    act_fns = setup_car_profile_actions(
        page,
        db_data,
        car_name,
        show_message,
        rebuild_callback,
    )
    add_car_fn, edit_car_fn, del_car_fn = act_fns

    def open_export(_):
        show_custom_file_manager_dialog(
            page,
            "export",
            execute_custom_export,
            show_message,
        )

    def open_import(_):
        show_custom_file_manager_dialog(
            page,
            "import",
            execute_custom_import,
            show_message,
        )

    def open_odo_hist(_):
        show_car_odometer_history_dialog(
            page,
            db_data,
            car_profile,
            rebuild_callback,
            show_message,
        )

    action_panel = ft.Row(
        [
            ft.Row(
                [
                    ft.Text(
                        "База:",
                        size=14,
                        weight=ft.FontWeight.W_500,
                    ),
                    ft.IconButton(
                        ft.Icons.CLOUD_UPLOAD,
                        icon_color=ft.Colors.BLUE_600,
                        on_click=open_export,
                    ),
                    ft.IconButton(
                        ft.Icons.CLOUD_DOWNLOAD,
                        icon_color=ft.Colors.GREEN_600,
                        on_click=open_import,
                    ),
                ],
                spacing=2,
            ),
            ft.Row(
                [
                    ft.IconButton(
                        ft.Icons.ADD_CIRCLE,
                        on_click=add_car_fn,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.EDIT,
                        on_click=edit_car_fn,
                    ),
                    ft.IconButton(
                        ft.Icons.DELETE_FOREVER,
                        icon_color=ft.Colors.RED_500,
                        on_click=del_car_fn,
                    ),
                    ft.Container(width=40),
                ],
                spacing=2,
            ),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    header_card = ft.Card(
        content=ft.Container(
            content=ft.Column(
                [
                    action_panel,
                    ft.Divider(
                        height=5,
                        color=ft.Colors.BLACK_12,
                    ),
                    ft.Text(
                        "Обновление данных пробега",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Row(
                        [
                            current_odo_input,
                            daily_input,
                        ],
                        vertical_alignment=(
                            ft.CrossAxisAlignment.CENTER
                        ),
                        spacing=8,
                    ),
                    ft.Row(
                        [
                            ft.Button(
                                "Обновить",
                                on_click=(
                                    update_forecast_click
                                ),
                                height=45,
                            ),
                            ft.OutlinedButton(
                                "📖 История пробега",
                                icon=ft.Icons.HISTORY,
                                height=45,
                                on_click=open_odo_hist,
                            ),
                        ],
                        alignment=(
                            ft.MainAxisAlignment.CENTER
                        ),
                        spacing=10,
                    ),
                ],
                spacing=12,
            ),
            padding=12,
        )
    )

    return build_maintenance_list(
        page,
        db_data,
        car_name,
        car_profile,
        header_card,
        rebuild_callback,
        show_message,
        add_custom_task_click,
    )



# Фрагмент №13: Точка входа приложения (Main)

def main(page: ft.Page):
    """Главная функция интерфейса."""
    page.title = "Журнал ТО автомобиля"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = ft.ScrollMode.AUTO

    def show_message(text):
        snack = ft.SnackBar(ft.Text(text))
        page.overlay.append(snack)
        snack.open = True
        page.update()

    def build_tabs_ui():
        page.controls.clear()
        db_data = load_data()
        cars_dict = db_data.get("cars", {})
        tab_buttons = []
        tab_contents = []

        for car_name, car_profile in cars_dict.items():
            car_view_content = generate_car_view(
                page,
                db_data,
                car_name,
                car_profile,
                show_message,
                build_tabs_ui,
            )
            tab_buttons.append(
                ft.Tab(
                    label=car_name,
                    icon=ft.Icons.DIRECTIONS_CAR,
                )
            )
            tab_contents.append(car_view_content)

        tabs_layout = ft.Column(
            controls=[
                ft.TabBar(tabs=tab_buttons),
                ft.TabBarView(
                    controls=tab_contents,
                    expand=True,
                ),
            ],
            expand=True,
        )

        tabs_container = ft.Tabs(
            length=len(tab_buttons),
            selected_index=0,
            animation_duration=300,
            content=tabs_layout,
            expand=True,
        )
        page.add(tabs_container)
        page.update()

    build_tabs_ui()


if __name__ == "__main__":
    ft.run(main)
