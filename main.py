import sys
import os
# Принудительно ставим текущую папку проекта на первое место в путях поиска
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import flet as ft
from datetime import datetime
import engine
import views
import network  # Импортируем вынесенный сетевой модуль

APP_VERSION = "1.2.5"
BUILD_NUMBER = "11"
db_data = {}

def main(page: ft.Page):
    global db_data

    # Настройка темы и базовых параметров окна
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = ft.Colors.SURFACE_CONTAINER_LOW
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.AMBER)
    page.title = "Журнал ТО"
    page.window_width = 1200
    page.window_height = 800

    # Стартовая загрузка локальной БД
    db_data = engine.load_data()

    def show_message(text: str):
        page.snack_bar = ft.SnackBar(ft.Text(text), open=True)
        page.update()

    def refresh_ui():
        rebuild_ui()

    # Хук обновления интерфейса для обратного вызова из network.py
    page.data = {"refresh_ui": refresh_ui}

    def rebuild_ui():
        page.clean()
        current_db = engine.load_data()
        cars_dict = current_db.get("cars", {})

        if not cars_dict:
            page.add(ft.Text("В базе данных нет автомобилей. Добавьте первый автомобиль.", size=16))
            page.update()
            return

        car_names = list(cars_dict.keys())
        selected_car = engine.app_state.get("selected_car")
        
        if not selected_car or selected_car not in cars_dict:
            selected_car = car_names[0]
            engine.app_state["selected_car"] = selected_car

        # Верхняя панель переключения активных машин car_buttons_row
        car_buttons_row = ft.Row(spacing=10, scroll=ft.ScrollMode.AUTO)
        for name in car_names:
            is_selected = (name == selected_car)
            def make_click_handler(car_name_to_select=name):
                return lambda _: [engine.app_state.update({"selected_car": car_name_to_select}), rebuild_ui()]

            btn = ft.Container(
                content=ft.Text(str(name), color=ft.Colors.WHITE if is_selected else ft.Colors.BLACK, weight=ft.FontWeight.BOLD if is_selected else ft.FontWeight.NORMAL, size=14),
                bgcolor=ft.Colors.AMBER_700 if is_selected else ft.Colors.GREY_200,
                padding=ft.Padding(16, 8, 16, 8), border_radius=8, on_click=make_click_handler(), animate=200
            )
            car_buttons_row.controls.append(btn)

        car_profile = cars_dict[selected_car]

        # Текстовые поля ввода пробега
        odo_dict = car_profile.get("odometer") or {}
        current_odo_input = ft.TextField(label=f"Пробег (км) [от {odo_dict.get('date', '-')} ]", value=str(odo_dict.get("value", "0")), keyboard_type=ft.KeyboardType.NUMBER, expand=True)
        daily_input = ft.TextField(label="Пробег в день (км)", value=str(car_profile.get("daily_mileage", "0")), keyboard_type=ft.KeyboardType.NUMBER, expand=True)

        def update_forecast_click(e):
            try:
                val = int(current_odo_input.value)
                now_date_str = datetime.now().strftime("%d.%m.%Y")
                car_profile["odometer"] = {"value": val, "date": now_date_str}
                car_profile["daily_mileage"] = int(daily_input.value)
                
                if "odometer_history" not in car_profile: car_profile["odometer_history"] = []
                if not any(h["value"] == val for h in car_profile["odometer_history"]):
                    car_profile["odometer_history"].append({"value": val, "date": now_date_str})
                    
                engine.save_data(current_db)
                rebuild_ui()
                show_message("Данные успешно обновлены!")
            except ValueError:
                show_message("Ошибка: Проверьте числовое поле пробега")
        # Вложенные обработчики добавления, изменения и удаления машин (кнопки добавления)
        def add_car_click(e):
            car_name_input = ft.TextField(label="Марка / Модель")
            def save_new_car(_):
                name = car_name_input.value.strip()
                if not name or name in current_db["cars"]: return
                if name not in engine.app_state["newly_added_cars"]: engine.app_state["newly_added_cars"].append(name)
                
                current_db["cars"][name] = {"odometer": {"value": 0, "date": datetime.now().strftime("%d.%m.%Y")}, "daily_mileage": 0, "odometer_history": [], "maintenance_data": {}, "history": []}
                engine.save_data(current_db)
                engine.app_state["selected_car"] = name
                dialog.open = False; page.update(); rebuild_ui()

            dialog = ft.AlertDialog(title=ft.Text("Добавить автомобиль"), content=ft.Column([car_name_input], tight=True), actions=[ft.TextButton("Добавить", on_click=save_new_car)])
            page.overlay.append(dialog); dialog.open = True; page.update()

        def edit_car_name_click(e):
            edit_name_input = ft.TextField(label="Новое имя профиля", value=selected_car)
            def save_name_change(_):
                new_name = edit_name_input.value.strip()
                if not new_name or new_name == selected_car or new_name in current_db["cars"]: return
                current_db["cars"][new_name] = current_db["cars"].pop(selected_car)
                if selected_car in engine.app_state["newly_added_cars"]:
                    engine.app_state["newly_added_cars"].remove(selected_car)
                    engine.app_state["newly_added_cars"].append(new_name)
                engine.save_data(current_db); engine.app_state["selected_car"] = new_name
                dialog.open = False; page.update(); rebuild_ui()

            dialog = ft.AlertDialog(title=ft.Text("Редактировать имя"), content=ft.Column([edit_name_input], tight=True), actions=[ft.TextButton("Сохранить", on_click=save_name_change)])
            page.overlay.append(dialog); dialog.open = True; page.update()

        def delete_car_click(e):
            if len(current_db["cars"]) <= 1: return
            def confirm_delete(_):
                current_db["cars"].pop(selected_car)
                if selected_car in engine.app_state["newly_added_cars"]: engine.app_state["newly_added_cars"].remove(selected_car)
                engine.save_data(current_db); engine.app_state["selected_car"] = list(current_db["cars"].keys())[0]
                dialog.open = False; page.update(); rebuild_ui()

            dialog = ft.AlertDialog(title=ft.Text("Удаление профиля"), content=ft.Text(f"Удалить '{selected_car}'?"), actions=[ft.TextButton("Удалить", on_click=confirm_delete, style=ft.ButtonStyle(color=ft.Colors.RED_600))])
            page.overlay.append(dialog); dialog.open = True; page.update()

        # Верхняя панель управления с перенаправлением вызовов в network.py
        action_panel = ft.Row([
            ft.Row([
                ft.Text("База:", size=14, weight=ft.FontWeight.W_500),
                ft.IconButton(ft.Icons.CLOUD_UPLOAD, tooltip="Экспорт в Telegram", icon_color=ft.Colors.BLUE_600, on_click=lambda _: network.show_custom_file_manager_dialog(page, "export", db_data, show_message)),
                ft.IconButton(ft.Icons.CLOUD_DOWNLOAD, tooltip="Импорт из Telegram", icon_color=ft.Colors.GREEN_600, on_click=lambda _: network.show_custom_file_manager_dialog(page, "import", db_data, show_message)),
                ft.IconButton(ft.Icons.BAR_CHART_ROUNDED, tooltip='Переключить Графики / Список ТО', icon_color=ft.Colors.ORANGE_800, 
                              on_click=lambda _: [engine.app_state.update({'view_mode': 'analytics' if engine.app_state.get('view_mode') != 'analytics' else 'list'}), rebuild_ui()]),
            ], spacing=2),
            ft.Row([
                ft.IconButton(ft.Icons.ADD_CIRCLE, tooltip="Добавить авто", on_click=add_car_click),
                ft.IconButton(icon=ft.Icons.EDIT, tooltip="Переименовать", on_click=edit_car_name_click),
                ft.IconButton(ft.Icons.DELETE_FOREVER, tooltip="Удалить авто", on_click=delete_car_click, icon_color=ft.Colors.RED_500),
                ft.Container(width=40)
            ], spacing=2)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        odo_hist = car_profile.get("odometer_history", [])
        hist_text = "История пробега: " + " ".join([f"{h['value']} км ({h['date']})" for h in odo_hist[-2:]]) if odo_hist else "История изменений пробега пуста"

        # Сборка Header Card панели управления
        header_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    action_panel, ft.Divider(height=5, color=ft.Colors.BLACK_12),
                    ft.Text("Обновление данных пробега", size=16, weight=ft.FontWeight.BOLD),
                    ft.Row([current_odo_input, daily_input], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                    ft.Text(hist_text, size=11, color=ft.Colors.GREY_600, italic=True),
                    ft.Row([
                        ft.Button("Обновить пробег и прогноз", on_click=update_forecast_click, height=45),
                        ft.Button("История пробега", on_click=lambda _: views.show_car_odometer_history_dialog(page, current_db, car_profile, rebuild_ui, show_message), height=45)
                    ], alignment=ft.MainAxisAlignment.CENTER, spacing=15)
                ], spacing=12), padding=12
            )
        )

        # Выбор результирующего макета отображения
        if engine.app_state.get("view_mode") == "analytics":
            analytics_container = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)
            analytics_container.controls.append(header_card)
            analytics_container.controls.append(views.generate_analytics_view(page, car_profile))
            main_layout = analytics_container
        else:
            main_layout = views.build_maintenance_list(page, current_db, selected_car, car_profile, header_card, rebuild_ui, show_message)

        page.add(ft.Column(expand=True, controls=[ft.Container(content=car_buttons_row, padding=ft.Padding(5, 5, 0, 15)), main_layout]))
        page.update()

    rebuild_ui()

if __name__ == "__main__":
    ft.run(main)
