# -*- coding: utf-8 -*-
import sys, os, warnings, time, threading
try:
 if not os.path.exists("server_config"): os.makedirs("server_config", exist_ok=True)
 if not os.path.exists("server_config/ru_ru.json"):
  with open("server_config/ru_ru.json", "w", encoding="utf-8") as f: f.write('{"status": "fallback", "locale": "ru_RU"}')
except: pass
warnings.filterwarnings('ignore', category=DeprecationWarning)
for d in [os.path.abspath(os.path.dirname(__file__)), os.getcwd()]:
 if d not in sys.path: sys.path.insert(0, d)
try: import network
except ImportError:
 class NetworkStub:
  def __getattr__(self, name): return lambda *a, **kw: False
 network = NetworkStub(); sys.modules['network'] = network
import flet as ft
from datetime import datetime
import engine, views
_current_page_ref = None
def show_message(text: str):
 global _current_page_ref
 if _current_page_ref:
  _current_page_ref.snack_bar = ft.SnackBar(ft.Text(text), open=True)
  try: _current_page_ref.update()
  except: pass
def run_local_telegram_sync():
 import shutil, glob
 paths = [os.path.join(os.environ.get("USERPROFILE", "C:\\Users\\User"), "Downloads", "Telegram Desktop"), os.path.join(os.environ.get("USERPROFILE", "C:\\Users\\User"), "Загрузки", "Telegram Desktop"), r"C:\Users\User\Загрузки\Telegram Desktop"]
 tg_path = next((p for p in paths if os.path.exists(p)), None)
 if not tg_path: return False
 files = glob.glob(os.path.join(tg_path, "*.json"))
 if not files: return False
 try: files.sort(key=os.path.getmtime, reverse=True); shutil.copy2(files[0], "Carjournal_database.json"); return True
 except: return False
def main(page: ft.Page):
 global _current_page_ref
 _current_page_ref = page; orig_update = page.update; state_holder = {'last_time': 0.0}
 def throttled_update(*args, **kwargs):
  if os.name == 'nt': orig_update(*args, **kwargs); return
  now = time.time()
  if now - state_holder['last_time'] < 0.25: time.sleep(0.1); return
  state_holder.update({'last_time': now}); orig_update(*args, **kwargs)
 page.update = throttled_update; page.scroll = ft.ScrollMode.AUTO; page.theme_mode = ft.ThemeMode.LIGHT; page.bgcolor = ft.Colors.SURFACE_CONTAINER_LOW
 page.theme = ft.Theme(color_scheme_seed=ft.Colors.AMBER, scrollbar_theme=ft.ScrollbarTheme(track_visibility=True, thumb_visibility=True, thickness=10, radius=4, thumb_color=ft.Colors.AMBER_700))
 page.title = "Журнал ТО"; page.window_width = 1200; page.window_height = 800
 def refresh_ui_sync(): page.controls.clear(); rebuild_ui(); page.update()
 def on_pubsub_refresh_message(message):
  if message == "trigger_refresh_ui": refresh_ui_sync()
 page.pubsub.on_message = on_pubsub_refresh_message
 page.data = {"refresh_ui": lambda: page.pubsub.send_all("trigger_refresh_ui")}
 def async_mobile_import(e=None):
  show_message(" Запрос файла из Telegram...")
  try:
   page.data.pop("db_data", None)
   if os.name != "nt":
    import sys; engine_mod = sys.modules.get("engine", __import__("engine")); engine_mod.app_state.clear()
    if os.path.exists("Carjournal_database.json"):
     try: os.rename("Carjournal_database.json", "Carjournal_database.json.bak")
     except: pass
   if network.auto_import_last_file(): page.data["refresh_ui"](); page.update(); show_message("[V] База данных успешно обновлена!")
   else: show_message("[X] Не удалось получить новый файл")
  except Exception as err: show_message(f"[X] Ошибка импорта: {str(err)}")
 def async_pc_import(e=None):
  show_message(" Сканирование локальных загрузок...")
  try:
   if run_local_telegram_sync(): page.data.pop("db_data", None); page.data["refresh_ui"](); page.update(); show_message("[V] База данных успешно импортирована!")
   else: show_message("[X] Файлы импорта не найдены.")
  except Exception as err: show_message(f"[X] Ошибка импорта: {str(err)}")
 def rebuild_ui():
  page.clean()
  try: current_db = engine.load_data()
  except Exception as db_err: print(f"[CRITICAL] Сбой СУБД: {db_err}"); current_db = {"cars": {}}
  cars_dict = current_db.get("cars", {}); car_names = list(cars_dict.keys())
  if not cars_dict or not car_names:
   page.add(ft.Container(content=ft.Text("База данных пуста. Пожалуйста, импортируйте базу.", size=16, weight=ft.FontWeight.BOLD), alignment=ft.alignment.center, padding=50)); page.update(); return
  selected_car = engine.app_state.get("selected_car")
  if selected_car:
   match = [c for c in car_names if str(c).lower().strip() == str(selected_car).lower().strip()]
   if match: selected_car = match[0]; engine.app_state["selected_car"] = selected_car
  if not selected_car or selected_car not in cars_dict:
   selected_car = car_names if car_names else None; engine.app_state["selected_car"] = selected_car
  car_buttons_row = ft.Row(spacing=10, scroll=ft.ScrollMode.AUTO)
  for name in car_names:
   is_selected = (name == selected_car)
   def make_click_handler(car_name_to_select=name): return lambda _: [engine.app_state.update({"selected_car": car_name_to_select}), rebuild_ui()]
   car_buttons_row.controls.append(ft.Container(content=ft.Text(str(name), color=ft.Colors.WHITE if is_selected else ft.Colors.BLACK, weight=ft.FontWeight.BOLD if is_selected else ft.FontWeight.NORMAL, size=14), bgcolor=ft.Colors.AMBER_700 if is_selected else ft.Colors.GREY_200, padding=ft.Padding(16, 8, 16, 8), border_radius=8, on_click=make_click_handler()))
  car_profile = cars_dict[selected_car]; odo_dict = car_profile.get("odometer") or {}
  current_odo_input = ft.TextField(label=f"Пробег (км) [от {odo_dict.get('date', '-')} ]", value=str(odo_dict.get("value", "0")), keyboard_type=ft.KeyboardType.NUMBER, expand=True, border=ft.InputBorder.NONE, filled=True, border_radius=ft.BorderRadius(8, 8, 8, 8))
  daily_input = ft.TextField(label="Пробег в день (км)", value=str(car_profile.get("daily_mileage", "0")), keyboard_type=ft.KeyboardType.NUMBER, expand=True, border=ft.InputBorder.NONE, filled=True, border_radius=ft.BorderRadius(8, 8, 8, 8))
  def update_forecast_click(e):
   try:
    if not current_odo_input.value or not daily_input.value: page.snack_bar = ft.SnackBar(ft.Text(" Поля не могут быть пустыми!"), open=True); page.update(); return
    val = int(str(current_odo_input.value).strip()); daily_val = int(str(daily_input.value).strip())
    car_profile["odometer"] = {"value": val, "date": datetime.now().strftime("%d.%m.%Y")}; car_profile["daily_mileage"] = max(1, daily_val)
    if "odometer_history" not in car_profile: car_profile["odometer_history"] = []
    if not any(h.get("value") == val for h in car_profile["odometer_history"]): car_profile["odometer_history"].append({"value": val, "date": datetime.now().strftime("%d.%m.%Y")})
    car_profile["predictions"] = engine.get_maintenance_predictions(car_profile); engine.save_data(current_db)
    page.snack_bar = ft.SnackBar(ft.Text(" Данные успешно обновлены в JSON!"), open=True); page.update(); page.data["refresh_ui"]()
    try:
     if hasattr(network, "LAST_SENT_ALERTS") and selected_car in network.LAST_SENT_ALERTS: network.LAST_SENT_ALERTS[selected_car] = None
     threading.Thread(target=lambda: network.check_and_send_alerts(car_profile, car_name=selected_car) if hasattr(network, "check_and_send_alerts") else None, daemon=True).start()
    except Exception as t_err: print(f"[ALERT ERROR]: {t_err}")
   except Exception as ex: page.snack_bar = ft.SnackBar(ft.Text(f" Ошибка СУБД: {str(ex)}"), open=True); page.update()
  action_panel = views.build_action_panel(page, current_db, selected_car, async_mobile_import, async_pc_import, lambda e: [engine.app_state.update({"view_mode": "analytics" if engine.app_state.get("view_mode", "list") != "analytics" else "list"}), rebuild_ui()], network, show_message, lambda: page.data["refresh_ui"]())
  hist_text = "История пробега: " + " ".join([f"{h['value']} км ({h['date']})" for h in car_profile.get("odometer_history", [])[-2:]]) if car_profile.get("odometer_history") else "История пробега пуста"
  header_card = ft.Card(content=ft.Container(content=ft.Column([action_panel, ft.Divider(height=5), ft.Text("Обновление данных пробега", size=16, weight=ft.FontWeight.BOLD), ft.Column([current_odo_input, daily_input], expand=False, spacing=8), ft.Text(hist_text, size=11, color=ft.Colors.GREY_600, italic=True), ft.Column([ft.ElevatedButton("Обновить пробег и прогноз", on_click=update_forecast_click, height=45, bgcolor=ft.Colors.AMBER_700, color=ft.Colors.WHITE), ft.ElevatedButton("История пробега", on_click=lambda _: views.show_car_odometer_history_dialog(page, current_db, car_profile, rebuild_ui, show_message), height=45)], horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=10), ft.Text("Учет расходов на топливо", size=14, weight=ft.FontWeight.BOLD), ft.Row([ft.ElevatedButton("Заправить авто", icon=ft.Icons.LOCAL_GAS_STATION, bgcolor=ft.Colors.AMBER_700, color=ft.Colors.WHITE, on_click=lambda _: views.show_add_fuel_dialog(page, current_db, car_profile, lambda: page.data["refresh_ui"](), show_message), expand=True, height=40), ft.ElevatedButton("Журнал заправок", icon=ft.Icons.LIST_ALT, on_click=lambda _: views.show_fuel_history_dialog(page, current_db, car_profile, lambda: page.data["refresh_ui"](), show_message), expand=True, height=40)], spacing=10), ft.ElevatedButton("Журнал ремонтов", icon=ft.Icons.BUILD_CIRCLE, bgcolor=ft.Colors.BLUE_GREY_700, color=ft.Colors.WHITE, on_click=lambda _: views.show_repair_history_dialog(page, current_db, car_profile, lambda: page.data["refresh_ui"](), show_message), expand=True, height=40)], spacing=12), padding=12))
  if engine.app_state.get("view_mode") == "analytics":
   main_layout = ft.Column([header_card, views.generate_analytics_view(page, car_profile)], expand=False, scroll=ft.ScrollMode.AUTO)
  else: main_layout = views.build_maintenance_list(page, current_db, selected_car, car_profile, header_card, rebuild_ui, show_message)
  page.add(ft.SafeArea(content=ft.Column(expand=False, controls=[ft.Container(content=car_buttons_row, padding=ft.Padding(5, 5, 0, 15)), main_layout])))
 rebuild_ui()
 try:
  def start_worker():
   c_data = engine.load_data()
   sc = engine.app_state.get("selected_car", "Chevrolet lacetti")
   if c_data and "cars" in c_data and sc in c_data["cars"]:
    net_mod = sys.modules.get("network", __import__("network"))
    if hasattr(net_mod, "check_and_send_alerts"):
     net_mod.check_and_send_alerts(c_data["cars"][sc], car_name=sc)
  threading.Thread(target=start_worker, daemon=True).start()
 except Exception as e:
  print(f"Ошибка запуска алертов: {e}")

if __name__ == "__main__":
 ft.app(target=main)

