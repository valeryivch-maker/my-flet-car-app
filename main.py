import sys
import os
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)

base_dir = os.path.abspath(os.path.dirname(__file__))
if base_dir not in sys.path: sys.path.insert(0, base_dir)
cwd_dir = os.getcwd()
if cwd_dir not in sys.path: sys.path.insert(0, cwd_dir)

if os.name != "nt":
    sandbox_dir = os.environ.get("FLET_APP_DIR", os.path.expanduser("~"))
    if sandbox_dir in ["/", "/data", ""]:
        try:
            from plyer import storagepath
            sandbox_dir = storagepath.get_application_dir()
        except:
            sandbox_dir = os.path.dirname(os.path.abspath(__file__))
    if "app_flutter" not in sandbox_dir:
        sandbox_dir = os.path.join(os.path.expanduser("~"), "files")
    if sandbox_dir.startswith("/data/data/") and len(sandbox_dir.split("/")) <= 3:
        sandbox_dir = os.path.dirname(os.path.abspath(__file__))
    try: os.makedirs(sandbox_dir, exist_ok=True)
    except: sandbox_dir = "." 
    target_db = os.path.join(sandbox_dir, "database.txt")

def check_and_link_downloaded_db(show_message_callback=None):
    import os, shutil
    if os.name != "nt":
        sandbox_dir = os.environ.get("FLET_APP_DIR", os.path.expanduser("~"))
        if sandbox_dir in ["/", "/data", ""]:
            try:
                from plyer import storagepath
                sandbox_dir = storagepath.get_application_dir()
            except: sandbox_dir = os.path.dirname(os.path.abspath(__file__))
            if "app_flutter" not in sandbox_dir: sandbox_dir = os.path.join(os.path.expanduser("~"), "files")
            else: sandbox_dir = "."
    else: sandbox_dir = "."
    target_db_path = os.path.join(sandbox_dir, "database.txt")
    if os.name == "nt": download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    else: download_dir = "/storage/emulated/0/Download"
    external_backup = os.path.join(download_dir, "database.txt")
    if os.path.exists(external_backup) and os.path.getsize(external_backup) > 0:
        try:
            shutil.copy2(external_backup, target_db_path)
            os.remove(external_backup)
            if show_message_callback: show_message_callback("Синхронизация: Облачная база импортирована!")
            return True
        except: return False
    return False

try:
    import network
except ImportError:
    class NetworkStub:
        def __getattr__(self, name):
            def stub_func(*args, **kwargs): return False, "Сетевой шлюз недоступен."
            return stub_func
    network = NetworkStub()
    sys.modules['network'] = network

import flet as ft
from datetime import datetime
import engine
import views

_current_page_ref = None
def show_message(text: str):
    if _current_page_ref:
        _current_page_ref.snack_bar = ft.SnackBar(ft.Text(text), open=True)
        _current_page_ref.update()

def main(page: ft.Page):
    global _current_page_ref
    _current_page_ref = page
    try: check_and_link_downloaded_db(show_message)
    except: pass

    orig_update = page.update
    import time
    state_holder = {'last_time': 0.0}
    def throttled_update(*args, **kwargs):
        import os
        if os.name == 'nt': orig_update(*args, **kwargs); return
        now = time.time()
        if now - state_holder['last_time'] < 0.25: time.sleep(0.1); return
        state_holder.update({'last_time': now})
        orig_update(*args, **kwargs)
    
    page.update = throttled_update
    page.data = {'refresh_ui': lambda: rebuild_ui()}
    page.title = "Бортовой Журнал"
    page.scroll = ft.ScrollMode.ADAPTIVE
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = ft.Colors.SURFACE_CONTAINER_LOW
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.AMBER)
    if os.name == "nt": page.window_width, page.window_height = 1200, 800
    else: page.window_width, page.window_height, page.window_resizable = None, None, False

    def rebuild_ui():
        page.clean()
        try: current_db = engine.load_data()
        except: current_db = {"cars": {"Мой Автомобиль": engine.get_default_car_data()}}
        cars_dict = current_db.get("cars", {})
        if not cars_dict: page.add(ft.Text("В базе данных нет автомобилей.", size=16)); page.update(); return
        car_names = list(cars_dict.keys())
        selected_car = engine.app_state.get("selected_car")
        if not selected_car or selected_car not in cars_dict:
            selected_car = car_names[0] if car_names else "Мой Автомобиль"
            engine.app_state["selected_car"] = selected_car
        car_profile = cars_dict[selected_car]
        
        car_buttons_row = ft.Row(spacing=10, scroll=ft.ScrollMode.AUTO)
        for name in car_names:
            is_selected = (name == selected_car)
            def make_click_handler(car_name_to_select=name):
                return lambda _: [engine.app_state.update({"selected_car": car_name_to_select}), rebuild_ui()]
            btn = ft.Container(
                content=ft.Text(str(name), color=ft.Colors.WHITE if is_selected else ft.Colors.BLACK, weight=ft.FontWeight.BOLD if is_selected else ft.FontWeight.NORMAL, size=14),
                bgcolor=ft.Colors.AMBER_700 if is_selected else ft.Colors.GREY_200, padding=ft.Padding(16, 8, 16, 8), border_radius=8, on_click=make_click_handler()
            )
            car_buttons_row.controls.append(btn)

        odo_dict = car_profile.get("odometer") or {}
        current_odo_input = ft.TextField(label=f"Пробег (км) [от {odo_dict.get('date', '-')} ]", value=str(odo_dict.get("value", "0")), keyboard_type=ft.KeyboardType.NUMBER, expand=True, border=ft.InputBorder.NONE, filled=True, border_radius=ft.BorderRadius(8,8,8,8))
        daily_input = ft.TextField(label="Пробег в день (км)", value=str(car_profile.get("daily_mileage", "0")), keyboard_type=ft.KeyboardType.NUMBER, expand=True, border=ft.InputBorder.NONE, filled=True, border_radius=ft.BorderRadius(8,8,8,8))

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
            except ValueError: show_message("Ошибка поля пробега")

        def add_car_click(e):
            car_name_input = ft.TextField(label="Марка / Модель")
            def save_new_car(_):
                name = car_name_input.value.strip()
                if not name or name in current_db["cars"]: return
                current_db["cars"][name] = {"odometer": {"value": 0, "date": datetime.now().strftime("%d.%m.%Y")}, "daily_mileage": 0, "odometer_history": [], "maintenance_data": {}, "history": []}
                engine.save_data(current_db)
                engine.app_state["selected_car"] = name
                dialog.open = False
                page.update()
                rebuild_ui()
            dialog = ft.AlertDialog(title=ft.Text("Добавить автомобиль"), content=ft.Column([car_name_input], tight=True), actions=[ft.TextButton("Добавить", on_click=save_new_car)])
            page.overlay.append(dialog)
            dialog.open = True
            page.update()

        def edit_car_name_click(e):
            edit_name_input = ft.TextField(label="Новое имя профиля", value=selected_car)
            def save_name_change(_):
                new_name = edit_name_input.value.strip()
                success_rename, rename_msg = engine.rename_car_profile(current_db, selected_car, new_name)
                if not success_rename: show_message(rename_msg); return
                engine.app_state["selected_car"] = new_name
                dialog.open = False
                page.update()
                rebuild_ui()
            dialog = ft.AlertDialog(title=ft.Text("Редактировать имя"), content=ft.Column([edit_name_input], tight=True), actions=[ft.TextButton("Сохранить", on_click=save_name_change)])
            page.overlay.append(dialog)
            dialog.open = True
            page.update()

        def delete_car_click(e):
            if len(current_db["cars"]) <= 1: return
            def confirm_delete(_):
                current_db["cars"].pop(selected_car)
                engine.save_data(current_db)
                engine.app_state["selected_car"] = list(current_db["cars"].keys())
                dialog.open = False
                page.update()
                rebuild_ui()
            dialog = ft.AlertDialog(title=ft.Text("Удаление профиля"), content=ft.Text(f"Удалить '{selected_car}'?"), actions=[ft.TextButton("Удалить", on_click=confirm_delete, style=ft.ButtonStyle(color=ft.Colors.RED_600))])
            page.overlay.append(dialog)
            dialog.open = True
            page.update()

        action_panel = ft.Column(spacing=5, horizontal_alignment=ft.CrossAxisAlignment.START, controls=[
            ft.Text("База и управление профилями:", size=12, weight=ft.FontWeight.W_500, color=ft.Colors.BLUE_GREY_700),
            ft.Row(scroll=ft.ScrollMode.AUTO, spacing=5, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                ft.IconButton(icon=ft.Icons.CLOUD_UPLOAD, tooltip="Экспорт базы в Telegram", on_click=android_safe_export_thread),
                ft.IconButton(icon=ft.Icons.CLOUD_DOWNLOAD, tooltip="Импорт базы данных", on_click=android_safe_import_thread),
                ft.IconButton(icon=ft.Icons.BAR_CHART_ROUNDED, tooltip="Аналитика", on_click=lambda _: [engine.app_state.update({'view_mode': 'analytics' if engine.app_state.get('view_mode') != 'analytics' else 'list'}), rebuild_ui()]),
                ft.VerticalDivider(width=10, color=ft.Colors.BLACK_12),
                ft.IconButton(ft.Icons.ADD_CIRCLE, tooltip="Добавить авто", on_click=add_car_click),
                ft.IconButton(icon=ft.Icons.EDIT, tooltip="Переименовать авто", on_click=edit_car_name_click),
                ft.IconButton(ft.Icons.DELETE_FOREVER, tooltip="Удалить авто", on_click=delete_car_click, icon_color=ft.Colors.RED_500),
            ])
        ])

        odo_hist = car_profile.get("odometer_history", [])
        hist_text = "История пробега: " + " ".join([f"{h['value']} км ({h['date']})" for h in odo_hist[-2:]]) if odo_hist else "История пробега пуста"
        
        header_card = ft.Card(content=ft.Container(content=ft.Column([
            action_panel, ft.Divider(height=5, color=ft.Colors.BLACK_12),
            ft.Text("Обновление данных пробега", size=16, weight=ft.FontWeight.BOLD),
            ft.Column([current_odo_input, daily_input], expand=False, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=8),
            ft.Text(hist_text, size=11, color=ft.Colors.GREY_600, italic=True),
            ft.Column([
                ft.Button("Обновить пробег и прогноз", on_click=update_forecast_click, height=45),
                ft.Button("История пробега", on_click=lambda _: views.show_car_odometer_history_dialog(page, current_db, car_profile, rebuild_ui, show_message), height=45)
            ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=10),
            ft.Text("Учет расходов на топливо", size=14, weight=ft.FontWeight.BOLD),
            ft.Row([
                ft.Button("Заправить авто", icon=ft.Icons.LOCAL_GAS_STATION, bgcolor=ft.Colors.AMBER_700, color=ft.Colors.WHITE, on_click=lambda _: views.show_add_fuel_dialog(page, current_db, car_profile, rebuild_ui, show_message), expand=True, height=40),
                ft.Button("Журнал заправок", icon=ft.Icons.LIST_ALT, on_click=lambda _: views.show_fuel_history_dialog(page, current_db, car_profile, rebuild_ui, show_message), expand=True, height=40)
            ], spacing=10, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Button("Журнал ремонтов", icon=ft.Icons.BUILD_CIRCLE, bgcolor=ft.Colors.BLUE_GREY_700, color=ft.Colors.WHITE, on_click=lambda _: views.show_repair_history_dialog(page, current_db, car_profile, rebuild_ui, show_message), expand=True, height=40),
        ], spacing=12), padding=12))

        if engine.app_state.get("view_mode") == "analytics":
            main_layout = ft.Column([header_card, views.generate_analytics_view(page, car_profile)], scroll=ft.ScrollMode.ADAPTIVE)
        else:
            main_layout = views.build_maintenance_list(page, current_db, selected_car, car_profile, header_card, rebuild_ui, show_message)
        
        page.add(ft.SafeArea(content=ft.Column(expand=False, controls=[ft.Container(content=car_buttons_row, padding=ft.Padding(5, 5, 0, 15)), main_layout])))
        page.update()

    rebuild_ui()

def android_safe_import_thread(e: ft.ControlEvent):
    page = e.page
    import threading
    def worker_logic():
        import os, httpx, time
        async def ui_log_coro(text: str):
            page.snack_bar = ft.SnackBar(ft.Text(text), open=True)
            page.update()
        async def ui_refresh_coro():
            if 'refresh_ui' in page.data: page.data['refresh_ui']()
        try:
            time.sleep(0.3)
            page.run_task(ui_log_coro, "Синхронизация: Поиск бэкапа...")
            success = check_and_link_downloaded_db(show_message)
            if success:
                time.sleep(0.5)
                page.run_task(ui_log_coro, "Синхронизация: База успешно импортирована!")
                time.sleep(0.3)
                page.run_task(ui_refresh_coro)
            else: page.run_task(ui_log_coro, "Файл бэкапа не найден в Загрузках.")
        except Exception as ex: print(ex)
    threading.Thread(target=worker_logic, daemon=True).start()

def android_safe_export_thread(e: ft.ControlEvent):
    page = e.page
    import threading
    def worker_logic():
        import time
        async def ui_log_coro(text: str):
            page.snack_bar = ft.SnackBar(ft.Text(text), open=True)
            page.update()
        try:
            time.sleep(0.5)
            page.run_task(ui_log_coro, "Запуск экспорта базы данных...")
            import sys
            net_mod = sys.modules.get('network', __import__('network'))
            success, msg = net_mod.auto_export_file_to_telegram(page, None)
            time.sleep(0.3)
            page.run_task(ui_log_coro, msg)
        except Exception as ex: print(ex)
    threading.Thread(target=worker_logic, daemon=True).start()

if __name__ == "__main__":
    ft.app(target=main)
