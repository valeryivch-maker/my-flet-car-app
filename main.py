import sys
import os
import time
import warnings
import traceback
from datetime import datetime

# === ПЕРЕХВАТ ОШИБОК ДЛЯ ВЫВОДА НА ЭКРАН ===
STARTUP_ERROR = None

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
    STARTUP_ERROR = f"Ошибка локализации: {loc_err}"

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

# === БЕЗОПАСНЫЙ ИМПОРТ ===
try:
    import flet as ft
    import engine
    import views
    import network
except Exception as import_err:
    # Если импорт упал, запоминаем ошибку, Flet попробует запуститься и показать её
    STARTUP_ERROR = f"Критическая ошибка импорта: {import_err}\n\n{traceback.format_exc()}"
    try:
        import flet as ft
    except:
        pass

def main(page: ft.Page):
    global STARTUP_ERROR
    
    page.title = "Журнал ТО"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = ft.Colors.WHITE

    # Если была ошибка при импорте, показываем её и останавливаемся
    if STARTUP_ERROR:
        page.add(
            ft.Container(
                content=ft.Column([
                    ft.Text("ОШИБКА ЗАПУСКА", color=ft.Colors.RED, size=24, weight=ft.FontWeight.BOLD),
                    ft.Text(STARTUP_ERROR, color=ft.Colors.BLACK, selectable=True)
                ], scroll=ft.ScrollMode.AUTO),
                padding=20
            )
        )
        page.update()
        return

    # Если импорт прошел, но ошибка всё равно вылезет, мы ее поймаем тут
    try:
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
            orig_update(*args, **kwargs)

        page.update = throttled_update
        page.scroll = ft.ScrollMode.AUTO
        page.window_width = 1200
        page.window_height = 800

        def refresh_ui():
            page.controls.clear()
            page.update()
            rebuild_ui()

        page.data = {"refresh_ui": refresh_ui}

        def rebuild_ui():
            page.clean()
            render_main_layout()

        async def async_mobile_import(e=None):
            page.snack_bar = ft.SnackBar(ft.Text("Запрос файла..."), open=True)
            page.update()
            import asyncio
            loop = asyncio.get_running_loop()
            try:
                success = await loop.run_in_executor(None, lambda: network.auto_import_last_file())
                if success:
                    page.data.pop("db_data", None)
                    refresh_ui()
                    page.snack_bar = ft.SnackBar(ft.Text("[V] База обновлена!"), open=True)
                    page.update()
            except Exception as err:
                page.snack_bar = ft.SnackBar(ft.Text(f"Ошибка: {err}"), open=True)
                page.update()

        async def async_pc_import(e=None):
            page.snack_bar = ft.SnackBar(ft.Text("Поиск локально..."), open=True)
            page.update()
            import asyncio
            loop = asyncio.get_running_loop()
            try:
                from main import run_local_telegram_sync
                success = await loop.run_in_executor(None, run_local_telegram_sync)
                if success:
                    page.data.pop("db_data", None)
                    refresh_ui()
                    page.snack_bar = ft.SnackBar(ft.Text("[V] База обновлена!"), open=True)
                    page.update()
            except Exception as err:
                pass

        def render_main_layout():
            current_db = engine.load_data()
            cars_dict = current_db.get('cars', {})
            car_names = list(cars_dict.keys())

            if not cars_dict or not car_names:
                page.add(ft.Text('База пуста.', size=16))
                page.update()
                return

            selected_car = engine.app_state.get('selected_car', car_names[0])
            if isinstance(selected_car, list) and selected_car:
                selected_car = selected_car[0]
            
            if selected_car not in cars_dict:
                selected_car = car_names[0]
                engine.app_state['selected_car'] = selected_car

            car_buttons_row = ft.Row(spacing=10, scroll=ft.ScrollMode.AUTO)
            for name in car_names:
                is_selected = (name == selected_car)
                def make_click_handler(car_name_to_select=name):
                    return lambda _: [engine.app_state.update({"selected_car": car_name_to_select}), rebuild_ui()]
                
                btn = ft.Container(
                    content=ft.Text(str(name), color=ft.Colors.WHITE if is_selected else ft.Colors.BLACK, size=14),
                    bgcolor=ft.Colors.AMBER_700 if is_selected else ft.Colors.GREY_200, 
                    padding=ft.Padding(16, 8, 16, 8), border_radius=8, on_click=make_click_handler()
                )
                car_buttons_row.controls.append(btn)

            car_profile = cars_dict[selected_car]
            odo_dict = car_profile.get("odometer") or {}
            current_odo_input = ft.TextField(label="Пробег", value=str(odo_dict.get("value", "0")), expand=True)
            daily_input = ft.TextField(label="Пробег в день", value=str(car_profile.get("daily_mileage", "0")), expand=True)

            def update_forecast_click(e):
                try:
                    val = int(current_odo_input.value)
                    daily_val = int(daily_input.value)
                    car_profile["odometer"] = {"value": val, "date": datetime.now().strftime("%d.%m.%Y")}
                    car_profile["daily_mileage"] = max(1, daily_val)
                    engine.save_data(current_db)
                    refresh_ui()
                    page.snack_bar = ft.SnackBar(ft.Text("Обновлено!"), open=True)
                    page.update()
                except Exception as ex:
                    page.snack_bar = ft.SnackBar(ft.Text(f"Ошибка: {ex}"), open=True)
                    page.update()

            def toggle_analytics_click(e):
                engine.app_state['view_mode'] = 'analytics' if engine.app_state.get('view_mode', 'list') != 'analytics' else 'list'
                rebuild_ui()

            action_panel = views.build_action_panel(
                page, current_db, selected_car, async_mobile_import, async_pc_import,
                toggle_analytics_click, network, lambda t: None, refresh_ui
            )

            def send_full_report(e):
                try:
                    report_text = engine.generate_report_full(car_profile, selected_car)
                    network.send_telegram_alert_message(report_text)
                    page.snack_bar = ft.SnackBar(ft.Text("Отчет отправлен!"), open=True)
                    page.update()
                except Exception as ex:
                    page.snack_bar = ft.SnackBar(ft.Text(f"Ошибка: {ex}"), open=True)
                    page.update()

            header_card = ft.Card(
                content=ft.Container(
                    padding=12,
                    content=ft.Column([
                        action_panel, ft.Divider(),
                        ft.Text("Пробег", size=16, weight=ft.FontWeight.BOLD),
                        ft.Column([current_odo_input, daily_input], spacing=8),
                        ft.ElevatedButton("Обновить", on_click=update_forecast_click, bgcolor=ft.Colors.AMBER_700, color=ft.Colors.WHITE),
                        ft.Text("Топливо", size=14, weight=ft.FontWeight.BOLD),
                        ft.Row([
                            ft.ElevatedButton("Заправить", on_click=lambda _: views.show_add_fuel_dialog(page, current_db, car_profile, rebuild_ui, lambda t: None), expand=True),
                            ft.ElevatedButton("Журнал", on_click=lambda _: views.show_fuel_history_dialog(page, current_db, car_profile, rebuild_ui, lambda t: None), expand=True)
                        ]),
                        ft.ElevatedButton("Ремонты", on_click=lambda _: views.show_repair_history_dialog(page, current_db, car_profile, rebuild_ui, lambda t: None)),
                        ft.ElevatedButton("📊 Отчет в TG", on_click=send_full_report, bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE),
                    ], spacing=12)
                )
            )

            if engine.app_state.get("view_mode") == "analytics":
                analytics_container = ft.Column(expand=False, scroll=ft.ScrollMode.AUTO)
                analytics_container.controls.append(header_card)
                analytics_container.controls.append(views.generate_analytics_view(page, car_profile))
                main_layout = analytics_container
            else:
                main_layout = views.build_maintenance_list(page, current_db, selected_car, car_profile, header_card, rebuild_ui, lambda t: None)

            page.add(ft.Column(controls=[car_buttons_row, main_layout]))

        # Запуск отрисовки
        rebuild_ui()
        
        import threading
        def start_alerts():
            time.sleep(2)
            try:
                network.check_and_send_alerts(car_profile, car_name=selected_car)
            except: pass
        threading.Thread(target=start_alerts, daemon=True).start()

    except Exception as render_err:
        # Если упало уже после импорта
        page.clean()
        page.add(
            ft.Container(
                content=ft.Column([
                    ft.Text("ОШИБКА ОТРИСОВКИ UI", color=ft.Colors.RED, size=20, weight=ft.FontWeight.BOLD),
                    ft.Text(f"{render_err}\n\n{traceback.format_exc()}", color=ft.Colors.BLACK, selectable=True)
                ], scroll=ft.ScrollMode.AUTO),
                padding=20
            )
        )
        page.update()

if __name__ == "__main__":
    ft.app(target=main)