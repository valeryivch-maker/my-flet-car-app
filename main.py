import sys
import os
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)

if os.name != "nt":
    sandbox_dir = os.environ.get("FLET_APP_DIR", os.path.expanduser("~"))
    if sandbox_dir in ["/", "/data", ""]:
        # Автоматически определяем реальный системный путь запущенного приложения, исключая любые жесткие имена пакетов
        try:
            from plyer import storagepath
            sandbox_dir = storagepath.get_application_dir()
        except:
            # Аварийный универсальный путь относительно исполняемого файла внутри песочницы Android
            sandbox_dir = os.path.dirname(os.path.abspath(__file__))
            if "app_flutter" not in sandbox_dir:
                sandbox_dir = os.path.join(os.path.expanduser("~"), "files")
    
    # Делаем проверку: если путь все еще пытается создать папки в корне /data, изолируем его в текущую директорию скрипта
    if sandbox_dir.startswith("/data/data/") and len(sandbox_dir.split("/")) <= 3:
        sandbox_dir = os.path.dirname(os.path.abspath(__file__))
        
    try:
        os.makedirs(sandbox_dir, exist_ok=True)
    except:
        # Если Android совсем запретил создавать папки выше, работаем строго в локальной папке запуска скрипта
        sandbox_dir = "." 
    target_db = os.path.join(sandbox_dir, "database.txt")
    try:
        import json
        pass # Блок инжекции полностью отключен; backup_disabled_data
        backup_disabled_data = {
            "cars": {
                "Мой Автомобиль": {
                    "mileage": 125000,
                    "daily_mileage": 50,
                    "odometer": {"value": 125000, "date": "20.07.2026"},
                    "odometer_history": [{"value": 120000, "date": "01.01.2026"}, {"value": 125000, "date": "20.07.2026"}],
                    "components": {
                        "Масло в двигателе": {"last_change_mileage": 120000, "interval_mileage": 10000, "last_change_date": "20.07.2026", "interval_months": 12},
                        "Фильтр воздушный": {"last_change_mileage": 120000, "interval_mileage": 10000, "last_change_date": "20.07.2026", "interval_months": 12},
                        "Кондиционер": {"last_change_mileage": 100000, "interval_mileage": 15000, "last_change_date": "01.01.2024", "interval_months": 6}
                    },
                    "maintenance_data": {}, "history": []
                }
            },
            "selected_car": "Мой Автомобиль"
        }
        with open(target_db, "w", encoding="utf-8") as f_db:
            json.dump(backup_data, f_db, ensure_ascii=False, indent=4)
    except:
        pass
    if not os.path.exists(target_db) or os.path.getsize(target_db) == 0:
        try:
            import json
            default_data = {
                "cars": {
                    "Мой Автомобиль": {
                        "mileage": 125000,
                        "components": {
                            "Масло в двигателе": {"last_change_mileage": 120000, "interval_mileage": 10000, "last_change_date": "20.07.2026", "interval_months": 12},
                            "Кондиционер": {"last_change_mileage": 100000, "interval_mileage": 15000, "last_change_date": "01.01.2024", "interval_months": 6}
                        }
                    }
                },
                "selected_car": "Мой Автомобиль"
            }
            with open(target_db, "w", encoding="utf-8") as f:
                json.dump(default_data, f, ensure_ascii=False, indent=4)
        except:
            pass

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

import flet as ft
from datetime import datetime
import engine
import views

APP_VERSION = "1.2.6"
BUILD_NUMBER = "13"
db_data = {}

def run_local_telegram_sync():
    import shutil
    import glob
    if os.name != 'nt': return False
    tg_downloads_path = r"C:\\Users\\User\\Загрузки\\Telegram Desktop"
    if not os.path.exists(tg_downloads_path):
        user_profile = os.environ.get("USERPROFILE", "C:\\\\Users\\\\User")
        tg_downloads_path = os.path.join(user_profile, "Downloads", "Telegram Desktop")
    if not os.path.exists(tg_downloads_path):
        tg_downloads_path = os.path.join(user_profile, "Загрузки", "Telegram Desktop")
    if not os.path.exists(tg_downloads_path):
        return False
    search_pattern = os.path.join(tg_downloads_path, "*atabase*.json")
    found_files = glob.glob(search_pattern)
    if not found_files: return False
    try:
        found_files.sort(key=os.path.getmtime, reverse=True)
        shutil.copy2(found_files[0], "database.txt")
        return True
    except:
        return False


# Изолированный асинхронный обработчик импорта для Android-смартфонов
async def mobile_import_click_handler(e):
    try:
        import network
        # Передаем управление сетевому шлюзу импорта
        network.auto_import_last_file(e.page, lambda msg: print(f"[FLET_UI] {msg}"))
    except Exception as ex:
        print(f"[FLET_ERROR] Ошибка вызова мобильного импорта: {ex}")


# Неблокирующий асинхронный воркер импорта для предотвращения графического дедлока на Android

# Безопасный системный поток импорта для полного предотвращения дедлоков рендеринга на Android
def android_safe_import_thread(page, show_message_callback):
    try:
        import network
        import engine
        # Запускаем чистую загрузку в изолированном системном потоке ОС
        success, message = network.auto_import_last_file(page)
        
        # Передаем управление в Main UI Thread для легальной отрисовки слоев Android
        async def safe_ui_refresh_task():
            if success:
                try:
                    # Принудительно обновляем глобальное состояние памяти из нового database.txt
                    fresh_db = engine.load_data()
                    if page.data:
                        page.data["db_data"] = fresh_db
                    
                    # Прямой вызов перерисовки интерфейса в главном потоке
                    # Находим и вызываем rebuild_ui через замыкание или рефреш
                    if "refresh_ui" in page.data:
                        page.data["refresh_ui"]()
                    else:
                        # Если коллбэк пуст, принудительно вызываем снэкбар
                        pass
                except Exception as ex_eng:
                    print(f"[ПАТЧ_КРИТ] Ошибка синхронизации engine: {ex_eng}")
            
            # Легально выводим плашку успешного или ошибочного завершения
            show_message_callback(message)
            page.update()

        page.run_task(safe_ui_refresh_task)
        
    except Exception as ex:
        print(f"[FLET_THREAD_FIX] Ошибка фонового потока: {ex}")
def main(page: ft.Page):
    # Запрос нативных разрешений Android на чтение/запись файлов песочницы
    def on_perm_result(e):
        print(f"[ПРАВА] Результат запроса разрешений: {e.granted}")
    
    if os.name != "nt":
        try:
            page.permission.request_permission()
        except Exception as e:
            print(f"[ПРАВА] Ошибка инициализации плагина разрешений: {e}")

    page.title = "Бортовой Журнал"
    page.scroll = ft.ScrollMode.ADAPTIVE
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

    def rebuild_ui():
        page.clean()
        
        def run_delayed_alerts():
            import time
            try:
                time.sleep(2.0)
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
        except:
            current_db = {"cars": {"Мой Автомобиль": engine.get_default_car_data()}}

        cars_dict = current_db.get("cars", {})
        if not cars_dict:
            page.add(ft.Text("В базе данных нет автомобилей.", size=16))
            page.update()
            return

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
                bgcolor=ft.Colors.AMBER_700 if is_selected else ft.Colors.GREY_200,
                padding=ft.Padding(16, 8, 16, 8), border_radius=8, on_click=make_click_handler(), animate=200
            )
            car_buttons_row.controls.append(btn)

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
        ft.IconButton(ft.Icons.CLOUD_DOWNLOAD, tooltip="Импорт базы данных", on_click=lambda e: e.page.run_thread(android_safe_import_thread, e.page, show_message)),
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
            main_layout = ft.Column([header_card, views.generate_analytics_view(page, car_profile)], scroll=ft.ScrollMode.ADAPTIVE)
        else:
            main_layout = views.build_maintenance_list(page, current_db, selected_car, car_profile, header_card, rebuild_ui, show_message)

        page.add(ft.SafeArea(content=ft.Column(expand=False, controls=[ft.Container(content=car_buttons_row, padding=ft.Padding(5, 5, 0, 15)), main_layout])))
        page.update()

    def show_message(text: str):
        page.snack_bar = ft.SnackBar(ft.Text(text), open=True)
        page.update()

    rebuild_ui()

if __name__ == "__main__":
    ft.app(target=main)


# CACHE_FLUSH_MARKER: 20.07.2026 21:10:44