import sys
import os
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)

# Гарантируем корректный поиск локальных модулей на Android до их импорта
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
        
        try:
            os.makedirs(sandbox_dir, exist_ok=True)
        except:
            sandbox_dir = "." 
        target_db = os.path.join(sandbox_dir, "database.txt")
def check_and_link_downloaded_db(show_message_callback=None):
    """Подсистема Auto-Storage Linker: автономно вычисляет пути и безопасно перемещает бэкап."""
    import os
    import shutil
    
    # Автономное вычисление пути к песочнице приложения для обхода NameError
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
    else:
        sandbox_dir = "."
        
    target_db_path = os.path.join(sandbox_dir, "database.txt")
    
    if os.name == "nt":
        download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    else:
        download_dir = "/storage/emulated/0/Download"
        
    external_backup = os.path.join(download_dir, "database.txt")
    
    if os.path.exists(external_backup) and os.path.getsize(external_backup) > 0:
        try:
            print(f"[LINKER] Обнаружен свежий бэкап: {external_backup}")
            shutil.copy2(external_backup, target_db_path)
            os.remove(external_backup)
            print(f"[LINKER] База успешно перемещена в песочницу: {target_db_path}")
            if show_message_callback:
                show_message_callback("Синхронизация: Облачная база успешно импортирована!")
            return True
        except Exception as e:
            print(f"[LINKER_ERROR] Не удалось переместить файл базы данных: {e}")
    return False


try:
    import network
except ImportError:
    class NetworkStub:
        def __getattr__(self, name):
            def stub_func(*args, **kwargs): 
                return False, "Сетевой шлюз недоступен (ошибка импорта)."
            return stub_func
        def auto_export_file_to_telegram(self, *args, **kwargs): 
            return False, "Экспорт недоступен."
        def auto_import_last_file(self, *args, **kwargs): 
            return False, "Импорт недоступен."
    network = NetworkStub()
    sys.modules['network'] = network

import flet as ft
from datetime import datetime
import engine
import views

def main(page: ft.Page):
    # Автономный перенос бэкапа из папки загрузок при холодном старте
    try:
        if check_and_link_downloaded_db(None):
            if hasattr(engine, 'app_state') and engine.app_state:
                engine.app_state.clear()
            print('[CACHE] Внутренние буферы СУБД сброшены под импортированную базу.')
    except Exception as le:
        print(f'[LINKER_START_ERROR] Сбой холодного автолинкера: {le}')

    # Защитный демпфер графического конвейера HyperOS
    # Защитный демпфер графического конвейера HyperOS
    orig_update = page.update
    import time
    last_update_time = [0.0]

    def throttled_update(*args, **kwargs):
        import os
        if os.name == 'nt':
            # На Windows отключаем демпфер полностью во избежание пустых окон
            orig_update(*args, **kwargs)
            return
            
        now = time.time()
        if now - last_update_time[0] < 0.06:
            time.sleep(0.04)
        last_update_time[0] = time.time()
        orig_update(*args, **kwargs)
        
    page.update = throttled_update

    # Перенесено в асинхронный воркер кнопки импорта во избежание дедлока

    page.data = {'refresh_ui': lambda: rebuild_ui()}
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
                ft.IconButton(
                    icon=ft.Icons.CLOUD_UPLOAD, 
                    tooltip="Экспорт базы в Telegram",
                    on_click=android_safe_export_thread
                ),
                # Кнопка импорта теперь одиночная и вызывает run_thread
                ft.IconButton(
                    icon=ft.Icons.CLOUD_DOWNLOAD, 
                    tooltip="Импорт базы данных",
                 on_click=android_safe_import_thread
                ),
                ft.IconButton(
                    icon=ft.Icons.BAR_CHART_ROUNDED, 
                    tooltip="Аналитика", 
                    on_click=lambda _: [engine.app_state.update({'view_mode': 'analytics' if engine.app_state.get('view_mode') != 'analytics' else 'list'}), rebuild_ui()]
                ),
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



# Безопасный системный поток импорта для полного предотвращения дедлоков рендеринга на Android

def android_safe_import_thread(e: ft.ControlEvent):
    page = e.page
    import threading

    def worker_logic():
        import httpx
        import time
        BOT_TOKEN = "7367807270:AAEg_O18Zg0iYgW_X7YF_8f_qG_K9M"

        sub = "api"
        dom = "telegram.org"
        clean_host = f"https://{sub}.{dom}"

        async def ui_log_coro(text: str):
            page.snack_bar = ft.SnackBar(ft.Text(text), open=True)
            page.update()

        async def ui_refresh_coro():
            page.data['refresh_ui']()

        def send_log(msg: str):
            page.run_task(ui_log_coro, msg)

        try:
            time.sleep(0.3) # Демпфер перед инициализацией сетевого клиента
            send_log("Поиск последнего бэкапа в облаке...")

            with httpx.Client(timeout=5.0) as client:
                base_host = httpx.URL(clean_host)
                updates_url = base_host.join(f"/bot{BOT_TOKEN}/getUpdates")
                updates_res = client.get(updates_url, params={"offset": -1, "limit": 100})
                updates_data = updates_res.json()

            results = updates_data.get("result", [])
            file_id = None
            for update in reversed(results):
                msg = update.get("message", {})
                doc = msg.get("document", {})
                if doc and doc.get("file_name") == "database.txt":
                    file_id = doc.get("file_id")
                    break

            if not file_id:
                send_log("Ошибка: Бэкап database.txt не найден в чате!")
                return

            file_info_url = base_host.join(f"/bot{BOT_TOKEN}/getFile")
            with httpx.Client(timeout=5.0) as client:
                file_info_res = client.get(file_info_url, params={"file_id": file_id})
                file_path = file_info_res.json().get("result", {}).get("file_path")

            if not file_path:
                send_log("Ошибка получения пути к файлу бэкапа!")
                return

            final_download_url = f"{clean_host}/file/bot{BOT_TOKEN}/{file_path}"
            send_log("Загрузка файла бэкапа напрямую...")

            if os.name == "nt":
                download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
            else:
                download_dir = "/storage/emulated/0/Download"

            local_target = os.path.join(download_dir, "database.txt")

            with httpx.Client(timeout=15.0) as client:
                response = client.get(final_download_url)
                if response.status_code == 200:
                    with open(local_target, "wb") as f_out:
                        f_out.write(response.content)
                else:
                    send_log(f"Ошибка скачивания: HTTP {response.status_code}")
                    return

            send_log("Файл успешно скачан! Запуск линкера...")
            time.sleep(1.0)

            success = check_and_link_downloaded_db(None)
            if success:
                time.sleep(0.5) # Демпфер для стабилизации UI перед тяжелым рендером
                send_log("Синхронизация: База успешно импортирована!")
                time.sleep(0.3) # Пауза перед обновлением интерфейса
                page.run_task(ui_refresh_coro)
            else:
                send_log("Ошибка линкера: файл не перемещен.")

        except Exception as ex:
            print(f"[FLET_THREAD_ERROR] Критическая ошибка шлюза: {ex}")
            try:
                send_log(f"Сетевая ошибка: {str(ex)}")
            except:
                pass

    threading.Thread(target=worker_logic, daemon=True).start()

# Безопасный системный поток экспорта для полного предотвращения дедлоков рендеринга
def android_safe_export_thread(e: ft.ControlEvent):
    page = e.page
    import threading

    def worker_logic():
        import time
        async def ui_log_coro(text: str):
            page.snack_bar = ft.SnackBar(ft.Text(text), open=True)
            page.update()

        try:
            time.sleep(0.5) # Локальный демпфер потока экспорта
            page.run_task(ui_log_coro, "Запуск экспорта базы данных...")
            import sys
            net_mod = sys.modules.get('network', __import__('network'))

            success, msg = net_mod.auto_export_file_to_telegram(page, None)
            time.sleep(0.3) # Предотвращение ANR перед финализацией UI
            page.run_task(ui_log_coro, msg)
        except Exception as ex:
            print(f"[FLET_EXPORT_ERROR] Ошибка шлюза экспорта: {ex}")

    threading.Thread(target=worker_logic, daemon=True).start()

if __name__ == "__main__":
    ft.app(target=main)
