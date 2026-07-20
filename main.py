import sys
import os
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)

# Сквозной перехват путей до инициализации расчетного ядра engine
if os.name != "nt":
    # Используем внутреннюю защищенную директорию Flet-рантайма на Android
    sandbox_dir = os.environ.get("FLET_APP_DIR", os.path.expanduser("~"))
    if sandbox_dir == "/" or sandbox_dir == "/data":
        # Аварийный редирект в легальную локальную песочницу данных приложения
        sandbox_dir = "/data/data/com.flet.carjournal/files"
        
    os.makedirs(sandbox_dir, exist_ok=True)
    target_db = os.path.join(sandbox_dir, "database.txt")
    if not os.path.exists(target_db):
        try:
            with open(target_db, "w", encoding="utf-8") as f:
                f.write("")
        except:
            # Если и там закрыто, уходим в глубокий кэш ассетов Flutter
            sandbox_dir = os.path.dirname(sys.executable) if hasattr(sys, 'executable') else "."
            target_db = os.path.join(sandbox_dir, "database.txt")
            with open(target_db, "w", encoding="utf-8") as f: f.write("")

# -*- coding: utf-8 -*-
import sys
import os
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)

try:
    import network
except ImportError:
    class NetworkStub:
        def __getattr__(self, name):
            def stub_func(*args, **kwargs): pass
            return stub_func
        def auto_export_file_to_telegram(self, *args, **kwargs): pass
        def auto_import_last_file(self, *args, **kwargs): pass
    network = NetworkStub()
    sys.modules['network'] = network

base_dir = os.path.abspath(os.path.dirname(__file__))
if base_dir not in sys.path: sys.path.insert(0, base_dir)
cwd_dir = os.getcwd()
if cwd_dir not in sys.path: sys.path.insert(0, cwd_dir)
if "" not in sys.path: sys.path.insert(0, "")

import flet as ft
from datetime import datetime
import engine
import views

APP_VERSION = "1.2.6"
BUILD_NUMBER = "12"
db_data = {}

def run_local_telegram_sync():
    import shutil
    if os.name == 'nt': pass
    import glob
    tg_downloads_path = r"C:\Users\User\Загрузки\Telegram Desktop"
    if not os.path.exists(tg_downloads_path):
        user_profile = os.environ.get("USERPROFILE", "C:\\Users\\User")
        tg_downloads_path = os.path.join(user_profile, "Downloads", "Telegram Desktop")
    if not os.path.exists(tg_downloads_path):
        tg_downloads_path = os.path.join(user_profile, "Загрузки", "Telegram Desktop")
    if not os.path.exists(tg_downloads_path):
        return False
    search_pattern = os.path.join(tg_downloads_path, "*atabase*.json")
    found_files = glob.glob(search_pattern)
    if not found_files:
        return False
    try:
        found_files.sort(key=os.path.getmtime, reverse=True)
        shutil.copy2(found_files[0], "database.txt")
        return True
    except Exception:
        return False

def main(page: ft.Page):
    page.title = "Бортовой Журнал"
    page.scroll = ft.ScrollMode.ADAPTIVE # Отключаем скролл страницы, скроллиться будут только списки
    global db_data
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = ft.Colors.SURFACE_CONTAINER_LOW
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.AMBER)
    
    if os.name == "nt":
        page.window_width = 1200
        page.window_height = 800
    else:
        page.window_width = None
        page.window_height = None
        page.window_resizable = False

    import shutil
    if os.name == 'nt': pass
    if os.name != "nt" or "ANDROID_BOOTLOGO" in os.environ:
        sandbox_dir = os.environ.get("HOME", os.path.expanduser("~"))
        target_db = os.path.join(sandbox_dir, "database.txt")
        target_cfg = os.path.join(sandbox_dir, "app_config.txt")
        os.makedirs(sandbox_dir, exist_ok=True)
        if not os.path.exists(target_db) and os.name == "nt":
            try:
                if os.name == "nt": shutil.copy2("database.txt", target_db)
            except: pass
        if not os.path.exists(target_cfg) and os.path.exists("app_config.txt"):
            try:
                if os.name == "nt": shutil.copy2("app_config.txt", target_cfg)
            except: pass

    try:
        db_data = engine.load_data()
    except Exception:
        db_data = {"cars": {"Мой Автомобиль": {"odometer": {"value": 0, "date": "19.07.2026"}, "daily_mileage": 0, "odometer_history": [], "maintenance_data": {}, "history": []}}}
        db_data = engine.load_data()
    except Exception:
        db_data = {"cars": {"Мой Автомобиль": {"odometer": {"value": 0, "date": "19.07.2026"}, "daily_mileage": 0, "odometer_history": [], "maintenance_data": {}, "history": []}}}
    except Exception:
        db_data = {"cars": {"Мой Автомобиль": {"odometer": {"value": 0, "date": "19.07.2026"}, "daily_mileage": 0, "odometer_history": [], "maintenance_data": {}, "history": []}}}
    except Exception:
        # Аварийный обход Scoped Storage: генерируем чистую структуру прямо в оперативной памяти
        db_data = {"cars": {"Мой Автомобиль": engine.get_default_car_data()}}

    def run_delayed_alerts(profile_data, name_str):
        import time
        try:
            time.sleep(2.0)
            import sys
            net_mod = sys.modules.get('network', __import__('network'))
            if hasattr(net_mod, 'check_and_send_alerts'):
                net_mod.check_and_send_alerts(profile_data, car_name=name_str)
        except:
            pass

    def show_message(text: str):
        page.snack_bar = ft.SnackBar(ft.Text(text), open=True)
        page.update()

    def refresh_ui():
        page.controls.clear()
        page.update()
        rebuild_ui()

    page.data = {"refresh_ui": refresh_ui}

    def rebuild_ui():
        page.clean()
        
        def run_delayed_alerts():
            import time
            try:
                time.sleep(1.5)
                import sys
                net_mod = sys.modules.get('network', __import__('network'))
                if hasattr(net_mod, 'check_and_send_alerts'):
                    net_mod.check_and_send_alerts(car_profile, car_name=selected_car)
            except:
                pass
                
        import threading
        threading.Thread(target=run_delayed_alerts, daemon=True).start()
        try:
            current_db = engine.load_data()
        except Exception:
            current_db = page.data.get("db_data", {"cars": {"Мой Автомобиль": engine.get_default_car_data()}})
        if page.data and "db_data" in page.data:
            current_db = page.data["db_data"]
        else:
            if page.data is None: page.data = {}
            page.data["db_data"] = current_db

        cars_dict = current_db.get("cars", {})
        if not cars_dict:
            page.add(ft.Text("В базе данных нет автомобилей.", size=16))
            page.update()
            return

        car_names = list(cars_dict.keys())
        # Железная защита от KeyError: None в песочнице Android
        selected_car = engine.app_state.get("selected_car")
        if not selected_car or selected_car == "None" or selected_car not in cars_dict:
            if car_names:
                selected_car = car_names[0]
            else:
                selected_car = "Мой Автомобиль"
            engine.app_state["selected_car"] = selected_car
            
        if selected_car not in cars_dict:
            selected_car = car_names[0]
            engine.app_state["selected_car"] = selected_car
            
        car_profile = cars_dict[selected_car]
        
        # Безопасный вызов алертов ТО после инициализации профиля
        def run_delayed_alerts():
            import time
            try:
                time.sleep(1.5) # Даем графическому движку Android 1.5 секунды на полную отрисовку
                import sys
                net_mod = sys.modules.get('network', __import__('network'))
                if hasattr(net_mod, 'check_and_send_alerts'):
                    net_mod.check_and_send_alerts(profile_data, car_name=name_str)
            except:
                pass
        
        # Запускаем сетевой скрининг в изолированном фоновом потоке, не мешающем UI
        # Фоновый скрининг перенесен на этап после полной отрисовки canvas
        pass

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
        odo_dict = car_profile.get("odometer") or {}
        current_odo_input = ft.TextField(label=f"Пробег (км) [от {odo_dict.get('date', '-')} ]", value=str(odo_dict.get("value", "0")), keyboard_type=ft.KeyboardType.NUMBER, expand=True, border=ft.InputBorder.NONE, filled=True, border_radius=ft.BorderRadius(8, 8, 8, 8))
        daily_input = ft.TextField(label="Пробег в день (км)", value=str(car_profile.get("daily_mileage", "0")), keyboard_type=ft.KeyboardType.NUMBER, expand=True, border=ft.InputBorder.NONE, filled=True, border_radius=ft.BorderRadius(8, 8, 8, 8))

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
                show_message("Ошибка поля пробега")

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
                if not success_rename:
                    show_message(rename_msg)
                    return
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

        action_panel = ft.Column(
            spacing=5, horizontal_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Text("База и управление профилями:", size=12, weight=ft.FontWeight.W_500, color=ft.Colors.BLUE_GREY_700),
                ft.Row(
                    scroll=ft.ScrollMode.AUTO, spacing=5, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.IconButton(ft.Icons.CLOUD_UPLOAD, tooltip="Экспорт базы в Telegram", on_click=lambda _: network.auto_export_file_to_telegram(page, show_message) if os.name == 'nt' or 'network' in sys.modules else None),
                        ft.IconButton(ft.Icons.CLOUD_DOWNLOAD, tooltip="Импорт базы данных", on_click=lambda _: [run_local_telegram_sync(), page.data.update({"db_data": engine.load_data()}), refresh_ui(), show_message("✅ База импортирована!")] if os.name == "nt" else [network.auto_import_last_file(page, show_message) if os.name == 'nt' or 'network' in sys.modules else None]),
                        ft.IconButton(ft.Icons.BAR_CHART_ROUNDED, tooltip="Аналитика", on_click=lambda _: [engine.app_state.update({'view_mode': 'analytics' if engine.app_state.get('view_mode') != 'analytics' else 'list'}), rebuild_ui()]),
                        ft.VerticalDivider(width=10, color=ft.Colors.BLACK_12),
                        ft.IconButton(ft.Icons.ADD_CIRCLE, tooltip="Добавить авто", on_click=add_car_click),
                        ft.IconButton(icon=ft.Icons.EDIT, tooltip="Переименовать авто", on_click=edit_car_name_click),
                        ft.IconButton(ft.Icons.DELETE_FOREVER, tooltip="Удалить авто", on_click=delete_car_click, icon_color=ft.Colors.RED_500),
                    ]
                )
            ]
        )
        odo_hist = car_profile.get("odometer_history", [])
        hist_text = "История пробега: " + " ".join([f"{h['value']} км ({h['date']})" for h in odo_hist[-2:]]) if odo_hist else "История пробега пуста"

        header_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    action_panel, ft.Divider(height=5, color=ft.Colors.BLACK_12),
                    ft.Text("Обновление данных пробега", size=16, weight=ft.FontWeight.BOLD),
                    ft.Column([current_odo_input, daily_input], expand=False, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=8),
                    ft.Text(hist_text, size=11, color=ft.Colors.GREY_600, italic=True),
                    ft.Column([
                        ft.Button("Обновить пробег и прогноз", on_click=update_forecast_click, height=45),
                        ft.Button("История пробега", on_click=lambda _: views.show_car_odometer_history_dialog(page, current_db, car_profile, rebuild_ui, show_message), height=45)
                    ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=10),
                    ft.Text("Учёт расходов на топливо", size=14, weight=ft.FontWeight.BOLD),
                    ft.Row([
                        ft.Button("Заправить авто", icon=ft.Icons.LOCAL_GAS_STATION, bgcolor=ft.Colors.AMBER_700, color=ft.Colors.WHITE, on_click=lambda _: views.show_add_fuel_dialog(page, current_db, car_profile, rebuild_ui, show_message), expand=True, height=40),
                        ft.Button("Журнал заправок", icon=ft.Icons.LIST_ALT, on_click=lambda _: views.show_fuel_history_dialog(page, current_db, car_profile, rebuild_ui, show_message), expand=True, height=40)
                    ], spacing=10, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Button("Журнал ремонтов", icon=ft.Icons.BUILD_CIRCLE, bgcolor=ft.Colors.BLUE_GREY_700, color=ft.Colors.WHITE, on_click=lambda _: views.show_repair_history_dialog(page, current_db, car_profile, rebuild_ui, show_message), expand=True, height=40),
                ], spacing=12), padding=12
            )
        )

        if engine.app_state.get("view_mode") == "analytics":
            analytics_container = ft.Column(expand=False, scroll=ft.ScrollMode.AUTO)
            analytics_container.controls.append(header_card)
            analytics_container.controls.append(views.generate_analytics_view(page, car_profile))
            main_layout = analytics_container
        else:
            main_layout = ft.Column([header_card], scroll=ft.ScrollMode.ADAPTIVE) # Временный безопасный контейнер

        page.add(ft.SafeArea(content=ft.Column(expand=False, controls=[ft.Container(content=car_buttons_row, padding=ft.Padding(5, 5, 0, 15)), main_layout])))
        page.update()
        import threading
        threading.Thread(target=run_delayed_alerts, daemon=True).start()

    rebuild_ui()

if __name__ == "__main__":
    ft.app(target=main)
