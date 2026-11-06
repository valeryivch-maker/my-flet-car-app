import sys
import os
import time
import warnings
import traceback
from datetime import datetime

# === ПЕРЕХВАТ ОШИБОК В ФАЙЛ ===
def log_error_to_file(error_msg):
    try:
        # Пытаемся сохранить в папку приложения
        log_dir = os.environ.get("FLET_APP_STORAGE_DATA", os.getcwd())
        log_path = os.path.join(log_dir, "error_log.txt")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n{error_msg}\n")
    except Exception as e:
        print(f"Не удалось записать лог: {e}")

# === БЕЗОПАСНЫЙ СТАРТ ===
try:
    if "ANDROID_BOOTLOGO" in os.environ or os.name != "nt":
        sandbox_dir = os.environ.get("FLET_APP_STORAGE_DATA", "/data/data/com.flet.carjournal/files")
        if sandbox_dir in ["/", "/data", ""]:
            sandbox_dir = os.path.dirname(os.path.abspath(__file__))
    else:
        sandbox_dir = os.getcwd()

    config_dir = os.path.join(sandbox_dir, "server_config")
    os.makedirs(config_dir, exist_ok=True)
        
    config_file = os.path.join(config_dir, "ru_ru.json")
    if not os.path.exists(config_file):
        with open(config_file, "w", encoding="utf-8") as f_loc:
            f_loc.write('{"status": "fallback", "locale": "ru_RU"}')
            
except Exception as loc_err:
    log_error_to_file(f"Ошибка локализации: {loc_err}")

warnings.filterwarnings('ignore', category=DeprecationWarning)

base_dir = os.path.abspath(os.path.dirname(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

cwd_dir = os.getcwd()
if cwd_dir not in sys.path:
    try:
        sys.path.insert(0, cwd_dir)
    except:
        pass

# === ИМПОРТ FLET И МОДУЛЕЙ ===
try:
    import flet as ft
    import engine
    import views
    import network
except Exception as import_err:
    log_error_to_file(f"Критическая ошибка импорта: {import_err}")
    # Если импорт упал, мы не можем запустить Flet, выбрасываем ошибку дальше
    raise

_current_page_ref = None

def show_message(text: str):
    global _current_page_ref
    if _current_page_ref:
        try:
            _current_page_ref.snack_bar = ft.SnackBar(ft.Text(text), open=True)
            _current_page_ref.update()
        except:
            pass

def run_local_telegram_sync():
    if os.name != "nt":
        return False
    import shutil
    import glob
    
    user_profile = os.environ.get("USERPROFILE")
    if not user_profile:
        import getpass
        current_user = getpass.getuser()
        user_profile = f"C:\\Users\\{current_user}"
        
    possible_paths = [
        os.path.join(user_profile, "Downloads", "Telegram Desktop"),
        os.path.join(user_profile, "Загрузки", "Telegram Desktop")
    ]
    
    tg_downloads_path = None
    for p in possible_paths:
        if os.path.exists(p):
            tg_downloads_path = p
            break
            
    if not tg_downloads_path:
        return False
        
    search_pattern = os.path.join(tg_downloads_path, "*.json")
    found_files = glob.glob(search_pattern)
    if not found_files:
        return False
        
    try:
        found_files.sort(key=os.path.getmtime, reverse=True)
        shutil.copy2(found_files[0], engine.DB_FILE)
        return True
    except Exception as ex:
        log_error_to_file(f"Ошибка локального импорта: {ex}")
        return False


def main(page: ft.Page):
    global _current_page_ref
    _current_page_ref = page
    
    try:
        page.title = "Журнал ТО"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.bgcolor = ft.Colors.SURFACE_CONTAINER_LOW
        page.theme = ft.Theme(color_scheme_seed=ft.Colors.AMBER)
        page.scroll = ft.ScrollMode.AUTO
    except Exception as e:
        log_error_to_file(f"Ошибка настройки Page: {e}")

    orig_update = page.update
    state_holder = {'last_time': 0.0}

    def throttled_update(*args, **kwargs):
        if os.name == 'nt':
            orig_update(*args, **kwargs)
            return
        now = time.time()
        if now - state_holder['last_time'] < 0.25:
            return
        state_holder.update({'last_time': now})
        try:
            orig_update(*args, **kwargs)
        except Exception as e:
            log_error_to_file(f"Ошибка обновления UI: {e}")

    page.update = throttled_update

    def refresh_ui():
        try:
            page.controls.clear()
            page.update()
            rebuild_ui()
        except Exception as e:
            log_error_to_file(f"Ошибка refresh_ui: {e}")

    page.data = {"refresh_ui": refresh_ui}

    def rebuild_ui():
        try:
            page.clean()
            render_main_layout()
        except Exception as e:
            log_error_to_file(f"Ошибка rebuild_ui: {e}")

    async def async_mobile_import(e=None):
        show_message(" Запрос файла из Telegram...")
        import asyncio
        loop = asyncio.get_running_loop()
        try:
            success = await loop.run_in_executor(None, lambda: network.auto_import_last_file())
            if success or os.name != "nt":
                page.data.pop("db_data", None)
                refresh_ui()
                show_message("[V] База данных успешно обновлена!")
            else:
                show_message("[X] Не удалось получить новый файл")
        except Exception as err:
            log_error_to_file(f"Ошибка async_mobile_import: {err}")
            show_message(f"[X] Ошибка импорта: {str(err)}")

    async def async_pc_import(e=None):
        show_message(" Сканирование локальных загрузок...")
        import asyncio
        loop = asyncio.get_running_loop()
        try:
            success = await loop.run_in_executor(None, run_local_telegram_sync)
            if success:
                page.data.pop("db_data", None)
                refresh_ui()
                show_message("[V] База данных успешно импортирована!")
            else:
                show_message("[X] Файлы импорта не найдены.")
        except Exception as db_err:
            log_error_to_file(f"Ошибка async_pc_import: {db_err}")

    def render_main_layout():
        try:
            current_db = engine.load_data()
        except Exception as db_err:
            log_error_to_file(f"Критическая ошибка engine.load_data: {db_err}")
            current_db = {'cars': {}}

        cars_dict = current_db.get('cars', {})
        car_names = list(cars_dict.keys())

        if not cars_dict or not car_names:
            try:
                page.add(ft.Container(
                    content=ft.Text('База данных пуста. Пожалуйста, импортируйте базу.', size=16, weight=ft.FontWeight.BOLD),
                    alignment=ft.alignment.center, padding=50
                ))
                page.update()
            except Exception as e:
                log_error_to_file(f"Ошибка отрисовки пустой базы: {e}")
            return

        selected_car = engine.app_state.get('selected_car', car_names[0] if car_names else None)
        
        if isinstance(selected_car, list) and selected_car:
            selected_car = selected_car[0]
            
        if selected_car:
            match = [c for c in car_names if str(c).lower().strip() == str(selected_car).lower().strip()]
            if match:
                selected_car = match[0]
                engine.app_state['selected_car'] = selected_car

        if not selected_car or selected_car not in cars_dict:
            selected_car = car_names[0] if car_names else None
            engine.app_state['selected_car'] = selected_car

        car_buttons_row = ft.Row(spacing=10, scroll=ft.ScrollMode.AUTO)
        for name in car_names:
            is_selected = (name == selected_car)
            def make_click_handler(car_name_to_select=name):
                return lambda _: [engine.app_state.update({"selected_car": car_name_to_select}), rebuild_ui()]
            
            btn = ft.Container(
                content=ft.Text(str(name), color=ft.Colors.WHITE if is_selected else ft.Colors.BLACK,
                                weight=ft.FontWeight.BOLD if is_selected else ft.FontWeight.NORMAL, size=14),
                bgcolor=ft.Colors.AMBER_700 if is_selected else ft.Colors.GREY_200, 
                padding=ft.Padding(16, 8, 16, 8), border_radius=8, on_click=make_click_handler()
            )
            car_buttons_row.controls.append(btn)

        car_profile = cars_dict[selected_car]
        odo_dict = car_profile.get("odometer") or {}
        current_odo_input = ft.TextField(
            label=f"Пробег (км) [от {odo_dict.get('date', '-')} ]",
            value=str(odo_dict.get("value", "0")), keyboard_type=ft.KeyboardType.NUMBER, expand=True,
            border=ft.InputBorder.NONE, filled=True, border_radius=ft.BorderRadius(8, 8, 8, 8)
        )
        daily_input = ft.TextField(
            label="Пробег в день (км)", value=str(car_profile.get("daily_mileage", "0")),
            keyboard_type=ft.KeyboardType.NUMBER, expand=True, border=ft.InputBorder.NONE,
            filled=True, border_radius=ft.BorderRadius(8, 8, 8, 8)
        )

        def update_forecast_click(e):
            try:
                if not current_odo_input.value or not daily_input.value:
                    page.snack_bar = ft.SnackBar(ft.Text("Поля не могут быть пустыми!"), open=True)
                    page.update()
                    return
                val = int(str(current_odo_input.value).strip())
                daily_val = int(str(daily_input.value).strip())
                
                car_profile["odometer"] = {"value": val, "date": datetime.now().strftime("%d.%m.%Y")}
                car_profile["daily_mileage"] = max(1, daily_val)
                
                if "odometer_history" not in car_profile: 
                    car_profile["odometer_history"] = []
                if not any(h.get("value") == val for h in car_profile["odometer_history"]):
                    car_profile["odometer_history"].append({"value": val, "date": datetime.now().strftime("%d.%m.%Y")})
                
                car_profile['predictions'] = engine.get_maintenance_predictions(car_profile)
                engine.save_data(current_db)
                page.snack_bar = ft.SnackBar(ft.Text("Данные успешно обновлены в JSON!"), open=True)
                page.update()
                refresh_ui()

                try:
                    import threading
                    current_car_name = selected_car[0] if isinstance(selected_car, list) else selected_car
                    if hasattr(network, 'LAST_SENT_ALERTS') and current_car_name in network.LAST_SENT_ALERTS:
                        network.LAST_SENT_ALERTS[current_car_name] = None
                    def trigger_alerts_worker():
                        if hasattr(network, 'check_and_send_alerts'):
                            network.check_and_send_alerts(car_profile, car_name=current_car_name)
                    threading.Thread(target=trigger_alerts_worker, daemon=True).start()
                except Exception as t_err:
                    log_error_to_file(f"Ошибка алертов: {t_err}")
            except Exception as ex:
                log_error_to_file(f"Ошибка update_forecast_click: {ex}")
                page.snack_bar = ft.SnackBar(ft.Text(f"Ошибка СУБД: {str(ex)}"), open=True)
                page.update()

        def toggle_analytics_click(e):
            engine.app_state['view_mode'] = 'analytics' if engine.app_state.get('view_mode', 'list') != 'analytics' else 'list'
            rebuild_ui()

        action_panel = views.build_action_panel(
            page, current_db, selected_car, async_mobile_import, async_pc_import,
            toggle_analytics_click, network, show_message, refresh_ui
        )

        odo_hist = car_profile.get("odometer_history", [])
        hist_text = "История пробега: " + " ".join([f"{h['value']} км ({h['date']})" for h in odo_hist[-2:]]) if odo_hist else "История пробега пуста"

        def send_full_report(e):
            try:
                report_text = engine.generate_report_full(car_profile, selected_car)
                network.send_telegram_alert_message(report_text)
                page.snack_bar = ft.SnackBar(ft.Text("Полный отчет отправлен в Telegram!"), open=True)
                page.update()
            except Exception as ex:
                log_error_to_file(f"Ошибка send_full_report: {ex}")
                page.snack_bar = ft.SnackBar(ft.Text(f"Ошибка отправки: {ex}"), open=True)
                page.update()

        header_card = ft.Card(
            content=ft.Container(
                padding=12,
                content=ft.Column([
                    action_panel, ft.Divider(height=5),
                    ft.Text("Обновление данных пробега", size=16, weight=ft.FontWeight.BOLD),
                    ft.Column([current_odo_input, daily_input], expand=False, spacing=8),
                    ft.Text(hist_text, size=11, color=ft.Colors.GREY_600, italic=True),
                    ft.Column([
                        ft.ElevatedButton("Обновить пробег и прогноз", on_click=update_forecast_click, height=45, bgcolor=ft.Colors.AMBER_700, color=ft.Colors.WHITE),
                        ft.ElevatedButton("История пробега", on_click=lambda _: views.show_car_odometer_history_dialog(page, current_db, car_profile, rebuild_ui, show_message), height=45)
                    ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=10),
                    
                    ft.Text("Учет расходов на топливо", size=14, weight=ft.FontWeight.BOLD),
                    ft.Row([
                        ft.ElevatedButton("Заправить авто", icon=ft.Icons.LOCAL_GAS_STATION, bgcolor=ft.Colors.AMBER_700, color=ft.Colors.WHITE, on_click=lambda _: views.show_add_fuel_dialog(page, current_db, car_profile, rebuild_ui, show_message), expand=True, height=40),
                        ft.ElevatedButton("Журнал заправок", icon=ft.Icons.LIST_ALT, on_click=lambda _: views.show_fuel_history_dialog(page, current_db, car_profile, rebuild_ui, show_message), expand=True, height=40)
                    ], spacing=10),
                    
                    ft.ElevatedButton("Журнал ремонтов", icon=ft.Icons.BUILD_CIRCLE, color=ft.Colors.WHITE, bgcolor=ft.Colors.BLUE_GREY_700, on_click=lambda _: views.show_repair_history_dialog(page, current_db, car_profile, rebuild_ui, show_message), expand=True, height=40),
                    
                    ft.ElevatedButton("📊 Отправить полный отчет в TG", icon=ft.Icons.SEND, color=ft.Colors.WHITE, bgcolor=ft.Colors.GREEN_700, on_click=send_full_report, expand=True, height=45),
                ], spacing=12)
            )
        )

        if engine.app_state.get("view_mode") == "analytics":
            analytics_container = ft.Column(expand=False, scroll=ft.ScrollMode.AUTO)
            analytics_container.controls.append(header_card)
            analytics_container.controls.append(views.generate_analytics_view(page, car_profile))
            main_layout = analytics_container
        else:
            main_layout = views.build_maintenance_list(page, current_db, selected_car, car_profile, header_card, rebuild_ui, show_message)

        page.add(ft.SafeArea(content=ft.Column(expand=False, controls=[ft.Container(content=car_buttons_row, padding=ft.Padding(5, 5, 0, 15)), main_layout])))

    # === СТАРТ С ОТЛОВОМ ОШИБОК ===
    try:
        rebuild_ui()
    except Exception as e:
        log_error_to_file(f"Критическая ошибка при старте: {e}")
        try:
            page.add(ft.Text(f"Ошибка запуска: {str(e)}", color=ft.Colors.RED))
            page.update()
        except:
            pass

    try:
        import threading
        def trigger_start_alerts_worker():
            time.sleep(2) 
            try:
                current_db_data = engine.load_data()
                sel_car = engine.app_state.get('selected_car', 'Chevrolet lacetti')
                if isinstance(sel_car, list) and sel_car:
                    sel_car = sel_car[0]
                if current_db_data and "cars" in current_db_data and sel_car in current_db_data["cars"]:
                    car_prof = current_db_data["cars"][sel_car]
                    network.check_and_send_alerts(car_prof, car_name=sel_car)
            except Exception as e:
                log_error_to_file(f"Ошибка фоновых алертов: {e}")
                
        threading.Thread(target=trigger_start_alerts_worker, daemon=True).start()
    except Exception as start_err:
        log_error_to_file(f"Ошибка запуска потока алертов: {start_err}")

if __name__ == "__main__":
    ft.app(target=main)