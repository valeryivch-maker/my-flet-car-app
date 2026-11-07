import os
import sys
import time
import warnings
import traceback
from datetime import datetime

warnings.filterwarnings('ignore', category=DeprecationWarning)

base_dir = os.path.abspath(os.path.dirname(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

try:
    import flet as ft
    import engine
    import views
    import network
except Exception as import_err:
    print(f"Критическая ошибка импорта: {import_err}")
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

def main(page: ft.Page):
    global _current_page_ref
    _current_page_ref = page
    
    page.title = "Журнал ТО"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = ft.Colors.WHITE
    page.scroll = ft.ScrollMode.AUTO

    def refresh_ui():
        page.controls.clear()
        page.update()
        rebuild_ui()

    page.data = {"refresh_ui": refresh_ui}

    def rebuild_ui():
        try:
            page.clean()
            render_main_layout()
        except Exception as e:
            page.clean()
            page.add(ft.Text(f"Ошибка UI: {e}", color=ft.Colors.RED))
            page.update()

    async def async_mobile_import(e=None):
        show_message("Запрос файла из Telegram...")
        import asyncio
        loop = asyncio.get_running_loop()
        try:
            success = await loop.run_in_executor(None, lambda: network.auto_import_last_file())
            if success or os.name != "nt":
                page.data.pop("db_data", None)
                refresh_ui()
                show_message("[V] База данных обновлена!")
            else:
                show_message("[X] Не удалось получить новый файл")
        except Exception as err:
            show_message(f"[X] Ошибка импорта: {str(err)}")

    async def async_pc_import(e=None):
        show_message("Сканирование локальных загрузок...")
        import asyncio
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, lambda: None)
            show_message("[X] Функция доступна только на ПК")
        except Exception as db_err:
            print(f'[CRITICAL] Сбой СУБД: {db_err}')

    def render_main_layout():
        current_db = engine.load_data()
        cars_dict = current_db.get('cars', {})
        car_names = list(cars_dict.keys())

        if not cars_dict or not car_names:
            page.add(ft.Container(
                content=ft.Text('База данных пуста.', size=16, weight=ft.FontWeight.BOLD),
                alignment=ft.Alignment.CENTER, padding=50
            ))
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
        
        current_odo_input = ft.TextField(
            label=f"Пробег (км) [от {odo_dict.get('date', '-')}]",
            value=str(odo_dict.get("value", "0")), expand=True
        )
        daily_input = ft.TextField(
            label="Пробег в день (км)", value=str(car_profile.get("daily_mileage", "0")), expand=True
        )

        def update_forecast_click(e):
            try:
                val = int(current_odo_input.value)
                daily_val = int(daily_input.value)
                car_profile["odometer"] = {"value": val, "date": datetime.now().strftime("%d.%m.%Y")}
                car_profile["daily_mileage"] = max(1, daily_val)
                
                if "odometer_history" not in car_profile: 
                    car_profile["odometer_history"] = []
                if not any(h.get("value") == val for h in car_profile["odometer_history"]):
                    car_profile["odometer_history"].append({"value": val, "date": datetime.now().strftime("%d.%m.%Y")})
                
                car_profile['predictions'] = engine.get_maintenance_predictions(car_profile)
                engine.save_data(current_db)
                refresh_ui()
                page.snack_bar = ft.SnackBar(ft.Text("Данные обновлены!"), open=True)
                page.update()
            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"Ошибка: {str(ex)}"), open=True)
                page.update()

        def toggle_analytics_click(e):
            engine.app_state['view_mode'] = 'analytics' if engine.app_state.get('view_mode', 'list') != 'analytics' else 'list'
            rebuild_ui()

        action_panel = views.build_action_panel(
            page, current_db, selected_car, async_mobile_import, async_pc_import,
            toggle_analytics_click, network, show_message, refresh_ui
        )

        header_card = ft.Card(
            content=ft.Container(
                padding=12,
                content=ft.Column([
                    action_panel, ft.Divider(),
                    ft.Text("Обновление данных пробега", size=16, weight=ft.FontWeight.BOLD),
                    ft.Column([current_odo_input, daily_input], spacing=8),
                    ft.ElevatedButton("Обновить пробег и прогноз", on_click=update_forecast_click, bgcolor=ft.Colors.AMBER_700, color=ft.Colors.WHITE),
                    
                    ft.Text("Учет расходов на топливо", size=14, weight=ft.FontWeight.BOLD),
                    ft.Row([
                        ft.ElevatedButton("Заправить авто", on_click=lambda _: views.show_add_fuel_dialog(page, current_db, car_profile, rebuild_ui, show_message), expand=True),
                        ft.ElevatedButton("Журнал заправок", on_click=lambda _: views.show_fuel_history_dialog(page, current_db, car_profile, rebuild_ui, show_message), expand=True)
                    ]),
                    ft.ElevatedButton("Журнал ремонтов", on_click=lambda _: views.show_repair_history_dialog(page, current_db, car_profile, rebuild_ui, show_message)),
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

    rebuild_ui()

    try:
        import threading
        def trigger_start_alerts_worker():
            time.sleep(5)
            try:
                current_db_data = engine.load_data()
                sel_car = engine.app_state.get('selected_car', 'Chevrolet lacetti')
                if isinstance(sel_car, list) and sel_car:
                    sel_car = sel_car[0]
                if current_db_data and "cars" in current_db_data and sel_car in current_db_data["cars"]:
                    car_prof = current_db_data["cars"][sel_car]
                    network.check_and_send_alerts(car_prof, car_name=sel_car)
            except Exception as e:
                print(f"[DEBUG START ALERTS WORKER ERROR]: {e}")
        threading.Thread(target=trigger_start_alerts_worker, daemon=True).start()
    except Exception as start_err:
        print(f"[START ALERT TRIGGER ERROR]: {start_err}")

if __name__ == "__main__":
    ft.app(target=main)