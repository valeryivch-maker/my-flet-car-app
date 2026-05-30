import flet as ft
from datetime import datetime, timedelta
import json
import os

DB_FILE = "database.txt"

# --- СТРУКТУРА БАЗЫ ДАННЫХ ---
def load_data():
    """Загружает данные автомобильного журнала ТО из файла JSON."""
    default_data = {
        "odometer": 125000,
        "daily_mileage": 45,
        "maintenance_data": {
            "oil": {
                "history": [[120000, "15.01.2026"]], 
                "interval": 10000, 
                "name": "Замена масла"
            },
            "grm": {
                "history": [[90000, "10.08.2025"]], 
                "interval": 60000, 
                "name": "Замена ГРМ"
            },
            "antifreeze": {
                "history": [[100000, "20.11.2025"]], 
                "interval": 40000, 
                "name": "Замена тосола"
            },
            "brake": {
                "history": [[110000, "05.12.2025"]], 
                "interval": 30000, 
                "name": "Тормозная жидкость"
            }
        }
    }
    if not os.path.exists(DB_FILE):
        return default_data
    
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key, item in data["maintenance_data"].items():
            if "history" not in item or not item["history"]:
                item["history"] = [[120000, datetime.now().strftime("%d.%m.%Y")]]
        return data
    except Exception:
        return default_data

def save_all_data(odo, daily, maint_data):
    """Сохраняет параметры в файл базы данных."""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump({"odometer": odo, "daily_mileage": daily, "maintenance_data": maint_data}, f, ensure_ascii=False, indent=4)

def main(page: ft.Page):
    page.title = "Бортовой журнал ТО"
    page.window_width = 480
    page.window_height = 800
    page.scroll = "adaptive"
    page.theme_mode = ft.ThemeMode.LIGHT

    app_data = load_data()
    maintenance_data = app_data["maintenance_data"]

    # Хранилища состояний видимости блоков для каждой детали
    opened_journals = {key: False for key in maintenance_data.keys()}
    opened_history_inputs = {key: False for key in maintenance_data.keys()}

    # --- ЭЛЕМЕНТЫ ВВОДА И ОТОБРАЖЕНИЯ ПРОБЕГА ---
    prev_odo_view = ft.TextField(
        label="Предыдущий километраж (км)", 
        value=str(app_data["odometer"]), 
        read_only=True, 
        disabled=True,
        expand=True
    )
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
    cards_container = ft.Column(spacing=15)

    # --- ФУНКЦИЯ: ДОБАВЛЕНИЕ НОВОЙ ЗАПИСИ (СБРОС ТО) ---
    def reset_maintenance_item(key):
        try:
            current_odo = int(odo_input.value or 0)
            daily_km = int(daily_input.value or 1)
        except ValueError:
            return

        today_str = datetime.now().strftime("%d.%m.%Y")
        maintenance_data[key]["history"].insert(0, [current_odo, today_str])
        
        prev_odo_view.value = str(current_odo)
        
        save_all_data(current_odo, daily_km, maintenance_data)
        update_dashboard()
        
        page.snack_bar = ft.SnackBar(ft.Text(f"Запись добавлена в историю: {maintenance_data[key]['name']}"), open=True)
        page.update()

    # --- ФУНКЦИЯ: РУЧНОЙ ВВОД СТАРЫХ ЗАПИСЕЙ В ИСТОРИЮ ---
    def add_custom_history_record(key, odo_val, date_val):
        try:
            past_odo = int(odo_val or 0)
        except ValueError:
            return
        
        if not date_val:
            date_val = datetime.now().strftime("%d.%m.%Y")
            
        maintenance_data[key]["history"].append([past_odo, date_val])
        maintenance_data[key]["history"].sort(key=lambda x: x[0], reverse=True)
        
        try:
            current_odo = int(odo_input.value or 0)
            daily_km = int(daily_input.value or 1)
        except ValueError:
            current_odo, daily_km = app_data["odometer"], app_data["daily_mileage"]
            
        save_all_data(current_odo, daily_km, maintenance_data)
        opened_history_inputs[key] = False  
        update_dashboard()
        
        page.snack_bar = ft.SnackBar(ft.Text("Прошлая запись успешно внесена в журнал!"), open=True)
        page.update()

    def toggle_journal(key):
        opened_journals[key] = not opened_journals[key]
        update_dashboard()

    def toggle_history_input(key):
        opened_history_inputs[key] = not opened_history_inputs[key]
        update_dashboard()

    def delete_history_record(key, index):
        maintenance_data[key]["history"].pop(index)
        try:
            current_odo = int(odo_input.value or 0)
            daily_km = int(daily_input.value or 1)
        except ValueError:
            current_odo, daily_km = app_data["odometer"], app_data["daily_mileage"]
        save_all_data(current_odo, daily_km, maintenance_data)
        update_dashboard()
    # --- ОТРИСОВКА ЭКРАНА И РАСЧЕТ АЛЕРТОВ ---
    def update_dashboard():
        cards_container.controls.clear()
        try:
            current_odo = int(odo_input.value or 0)
            daily_km = int(daily_input.value or 1)
        except ValueError:
            current_odo = app_data["odometer"]
            daily_km = app_data["daily_mileage"]

        if daily_km <= 0:
            daily_km = 1

        for key, item in maintenance_data.items():
            if item["history"] and len(item["history"]) > 0:
                last_replacement = item["history"][0][0]
                last_date_str = item["history"][0][1]
            else:
                last_replacement = current_odo
                last_date_str = "Нет записей"
            
            target_odo = last_replacement + item["interval"]
            km_left = target_odo - current_odo
            days_left = km_left / daily_km
            predicted_date = datetime.now() + timedelta(days=max(days_left, -365))
            date_str = predicted_date.strftime("%d.%m.%Y")

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

            # --- БЛОК 1: Просмотр списка истории ТО ---
            history_rows = ft.Column(spacing=5, visible=opened_journals[key])
            if opened_journals[key]:
                history_rows.controls.append(ft.Divider())
                history_rows.controls.append(ft.Text("Хронология замен:", weight=ft.FontWeight.BOLD, size=12))
                if not item["history"]:
                    history_rows.controls.append(ft.Text("История пуста", italic=True, size=12, color="grey600"))
                else:
                    for idx, record in enumerate(item["history"]):
                        def make_delete_click(k=key, i=idx):
                            return lambda e: delete_history_record(k, i)
                        
                        rec_odo = record[0]
                        rec_date = record[1]
                        
                        history_rows.controls.append(
                            ft.Row([
                                ft.Text(f"• {rec_odo} км ({rec_date})", size=13, expand=True),
                                ft.Button("Удалить", color="red700", height=30, on_click=make_delete_click())
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                        )

            # --- БЛОК 2: Поля ввода для добавления ручной старой записи ---
            history_input_block = ft.Column(spacing=5, visible=opened_history_inputs[key])
            if opened_history_inputs[key]:
                history_input_block.controls.append(ft.Divider())
                history_input_block.controls.append(ft.Text("Ввод архивной записи обслуживания:", weight=ft.FontWeight.BOLD, size=12))
                
                past_odo_field = ft.TextField(label="Пробег замены (км)", keyboard_type=ft.KeyboardType.NUMBER, height=40, text_size=13, expand=True)
                past_date_field = ft.TextField(label="Дата (ДД.ММ.ГГГГ)", value=datetime.now().strftime("%d.%m.%Y"), height=40, text_size=13, expand=True)
                
                def make_add_past_handler(k=key, o_f=past_odo_field, d_f=past_date_field):
                    return lambda e: add_custom_history_record(k, o_f.value, d_f.value)

                history_input_block.controls.append(ft.Row([past_odo_field, past_date_field], spacing=10))
                history_input_block.controls.append(ft.Row([ft.Button("Добавить запись", on_click=make_add_past_handler())], alignment=ft.MainAxisAlignment.CENTER))

            card = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(item["name"], size=16, weight=ft.FontWeight.BOLD, expand=True),
                        ft.Row([
                            ft.Button("ЖУРНАЛ", on_click=lambda e, k=key: toggle_journal(k)),
                            ft.Button("ВВОД ИСТОРИИ", on_click=lambda e, k=key: toggle_history_input(k)),
                            ft.Button("СБРОС ТО", color=status_color, on_click=lambda e, k=key: reset_maintenance_item(k))
                        ], spacing=3)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Text(f"Последнее ТО: {last_replacement} км ({last_date_str}) | Регламент: {item['interval']} км", size=11, color="grey700"),
                    ft.Container(height=3),
                    ft.Text(status_text, color=status_color, weight=ft.FontWeight.W_600, size=13),
                    history_rows,          
                    history_input_block    
                ]),
                padding=12, border_radius=10, bgcolor=bg_color,
                border=ft.Border(top=ft.BorderSide(1, status_color), bottom=ft.BorderSide(1, status_color), left=ft.BorderSide(1, status_color), right=ft.BorderSide(1, status_color))
            )
            cards_container.controls.append(card)
        page.update()

    def on_save_click(e):
        try:
            c_odo = int(odo_input.value or 0)
            c_daily = int(daily_input.value or 1)
        except ValueError:
            return
        prev_odo_view.value = str(c_odo)
        save_all_data(c_odo, c_daily, maintenance_data)
        update_dashboard()
        page.snack_bar = ft.SnackBar(ft.Text("Текущий пробег сохранен!"), open=True)
        page.update()

    save_button = ft.Button("Рассчитать прогноз ТО", on_click=on_save_click)
    
    page.add(
        ft.AppBar(title=ft.Text("Бортовой журнал ТО", color="white"), bgcolor="blue600", center_title=True),
        ft.Container(
            content=ft.Column([
                ft.Text("Обновление данных", size=16, weight=ft.FontWeight.W_600),
                ft.Row([prev_odo_view, odo_input], spacing=10),
                ft.Row([daily_input, save_button], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                ft.Divider(height=30),
                ft.Text("Статус регламентных работ", size=16, weight=ft.FontWeight.W_600),
                cards_container
            ]),
            padding=15
        )
    )
    update_dashboard()

ft.run(main)
