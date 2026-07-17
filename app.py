# ==================================================
# БЕЗОПАСНЫЙ АВТОМАТИЧЕСКИЙ СЛЕПОК ДЛЯ GITHUB ACTIONS
# ==================================================
import sys
import os
import json
import io
import time
import traceback
import requests
import urllib3
import glob
import shutil
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import flet as ft

# [ЯДРО] ENGINE
import json
import os
# Заменено монолитом: from datetime import datetime, timedelta

DB_FILE = "database.txt"
DB_PATH = DB_FILE
CONFIG_FILE = "app_config.txt"

def save_config_to_disk(file_id):
    """Принудительно записывает file_id на диск."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_file_id": file_id}, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"[DEBUG CONFIG] Ошибка записи конфига: {e}")

def load_config_from_disk():
    """Читает file_id с диска."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config_data = json.load(f)
                if isinstance(config_data, dict):
                    return config_data.get("last_file_id")
        except Exception as e:
            print(f"[DEBUG CONFIG] Ошибка чтения конфига: {e}")
    return None

# Умный класс-обертка для app_state, перехватывающий запись ключей
class SmartAppState(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        # Если network.py записывает новый last_file_id, мгновенно сохраняем его на диск
        if key == "last_file_id" and value is not None:
            save_config_to_disk(value)
            
    def get(self, key, default=None):
        if key == "last_file_id":
            val = super().get(key, default)
            if val is None:
                val = load_config_from_disk()
                if val is not None:
                    super().__setitem__("last_file_id", val)
            return val
        return super().get(key, default)

# Инициализируем состояние приложения как умный словарь
# Сразу же при загрузке модуля подтягиваем сохраненный file_id с диска, если он существует
saved_id = load_config_from_disk()

app_state = SmartAppState({
    "active_tab": 0,
    "newly_added_cars": [],
    "view_mode": "list",
    "selected_car": None,
    "last_file_id": saved_id  # Теперь ID готов к выдаче сразу после перезапуска приложения
})

def get_default_car_data():
    """Генерирует демонстрационный шаблон данных для первого запуска."""
    current_date = datetime.now().strftime("%d.%m.%Y")
    past_date = (datetime.now() - timedelta(days=30)).strftime("%d.%m.%Y")
    return {
        "odometer": {"value": 125000, "date": current_date},
        "daily_mileage": 45,
        "odometer_history": [
            {"value": 123650, "date": past_date},
            {"value": 125000, "date": current_date}
        ],
        "maintenance_data": {
            "Замена масла + фильтры": {"last_service": 120000, "interval": 10000, "date": current_date},
            "Замена ГРМ (ремень, помпа)": {"last_service": 90000, "interval": 60000, "date": current_date},
            "Замена антифриза": {"last_service": 100000, "interval": 50000, "date": current_date},
            "Тормозная жидкость": {"last_service": 100000, "interval": 40000, "date": current_date},
            "Обслуживание кондиционера": {"last_service": 110000, "interval": 30000, "date": current_date}
        },
        "history": []
    }

def parse_h_date(item):
    """Глобальная функция парсинга дат для сортировки истории."""
    try:
        return datetime.strptime(item["date"], "%d.%m.%Y")
    except:
        return datetime.min

def recalculate_auto_daily_mileage(car_profile):
    """Вычисляет реальный пробег в сутки на основе скользящего среднего между соседними записями."""
    history = car_profile.get("odometer_history", [])
    if len(history) < 2:
        return int(car_profile.get("daily_mileage", 45))
        
    try:
        # Сортируем историю строго по хронологии дат
        sorted_hist = sorted(history, key=lambda x: datetime.strptime(x["date"], "%d.%m.%Y"))
        
        rates = []
        # Проходим по парам соседних (последовательных) записей пробега
        for i in range(1, len(sorted_hist)):
            prev_entry = sorted_hist[i-1]
            curr_entry = sorted_hist[i]
            
            d1 = datetime.strptime(prev_entry["date"], "%d.%m.%Y")
            d2 = datetime.strptime(curr_entry["date"], "%d.%m.%Y")
            
            days = (d2 - d1).days
            km = int(curr_entry["value"]) - int(prev_entry["value"])
            
            # Если записи сделаны в один день, считаем как за 1 день, чтобы избежать деления на ноль
            if days == 0 and km > 0:
                days = 1
                
            if days > 0 and km > 0:
                rates.append(km / days)
                
        # Если удалось посчитать отрезки, берём среднее по последним 4 периодам (свежая статистика)
        if rates:
            recent_rates = rates[-4:]  # Берём только актуальный плавающий интервал поездок
            calculated_rate = int(sum(recent_rates) / len(recent_rates))
            
            # Защита от опечаток и случайных лишних нулей при вводе км (ограничение 1000 км/день)
            if calculated_rate > 1000:
                return int(car_profile.get("daily_mileage", 45))
                
            return max(1, calculated_rate)
            
    except Exception:
        pass
        
    return int(car_profile.get("daily_mileage", 45))

def calculate_task_status(task_info, current_odometer, daily_mileage):
    """Вычисляет остаток ресурса до ТО в километрах и днях."""
    last_service = task_info.get("last_service", current_odometer)
    interval = task_info.get("interval", 10000)
    rem_km = (last_service + interval) - current_odometer
    if daily_mileage > 0:
        rem_days = int(rem_km / daily_mileage)
    else:
        rem_days = 9999
    return {"rem_km": rem_km, "rem_days": rem_days, "is_overdue": rem_km <= 0}

def get_maintenance_predictions(car_profile):
    """Генерация пакета прогнозов по всем компонентам ТО."""
    current_odometer = car_profile.get("odometer", {}).get("value", 0)
    daily_mileage = car_profile.get("daily_mileage", 45)
    maintenance_data = car_profile.get("maintenance_data", {})
    predictions = {}
    for task_name, task_info in maintenance_data.items():
        predictions[task_name] = calculate_task_status(task_info, current_odometer, daily_mileage)
    return predictions

def load_data():
    """Загружает базу из файла и адаптирует под обновления."""
    if not os.path.exists(DB_FILE):
        initial_data = {"cars": {"Мой Автомобиль": get_default_car_data()}}
        save_data(initial_data)
        return initial_data
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "cars" not in data:
            data = {"cars": {}}
        for car_name, car_profile in data["cars"].items():
            if "odometer" not in car_profile:
                car_profile["odometer"] = {"value": 125000, "date": datetime.now().strftime("%d.%m.%Y")}
            if "daily_mileage" not in car_profile:
                car_profile["daily_mileage"] = 45
            if "odometer_history" not in car_profile:
                car_profile["odometer_history"] = []
            if "maintenance_data" not in car_profile:
                car_profile["maintenance_data"] = {}
            if "history" not in car_profile:
                car_profile["history"] = []
            if "fuel_history" not in car_profile:
                car_profile["fuel_history"] = []
            car_profile["daily_mileage"] = recalculate_auto_daily_mileage(car_profile)
            for task_name, task_info in car_profile["maintenance_data"].items():
                if "last_service" not in task_info:
                    task_info["last_service"] = car_profile["odometer"]["value"]
                if "interval" not in task_info:
                    task_info["interval"] = 10000
                if "date" not in task_info:
                    task_info["date"] = datetime.now().strftime("%d.%m.%Y")
            car_profile["predictions"] = get_maintenance_predictions(car_profile)
            # Заменено монолитом: import network
            network.check_and_send_alerts(car_profile, car_name=car_name)
        return data
    except Exception:
        return {"cars": {}}

def save_data(data):
    """Преобразует словарь данных в JSON и пишет на диск."""
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Ошибка записи на диск: {e}")

def rename_car_profile(data, old_name, new_name):
    """Безопасно переименовывает автомобиль в кэше и пишет на диск."""
    if "cars" not in data or old_name not in data["cars"]:
        return False, "Автомобиль со старым именем не найден."
    if new_name in data["cars"]:
        return False, "Автомобиль с таким именем уже существует."
    if not new_name.strip():
        return False, "Имя автомобиля не может быть пустым."
    data["cars"][new_name] = data["cars"].pop(old_name)
    save_data(data)
    return True, "Автомобиль успешно переименован."

def add_fuel_record(car_profile, f_type, liters, total_cost, odometer, date_str, comment=""):
    """Добавляет запись о заправке на основе литров и общей суммы."""
    if "fuel_history" not in car_profile:
        car_profile["fuel_history"] = []
        
    liters = float(liters)
    cost = float(total_cost)
    odometer = int(odometer)
    
    # Расчётная цена за 1 литр
    price = round(cost / liters, 2) if liters > 0 else 0.0
    
    # Расчёт расхода топлива по сравнению с прошлыми заправками того же типа
    consumption = 0.0
    same_type_logs = [log for log in car_profile["fuel_history"] if log.get("type") == f_type]
    
    if same_type_logs:
        same_type_logs.sort(key=lambda x: x.get("odometer", 0))
        prev_log = same_type_logs[-1]
        
        delta_km = odometer - prev_log.get("odometer", 0)
        if delta_km > 0:
            consumption = round((liters / delta_km) * 100, 2)

    new_record = {
        "date": date_str,
        "type": f_type,
        "liters": liters,
        "price": price,
        "cost": cost,
        "odometer": odometer,
        "consumption": consumption,
        "comment": comment
    }
    
    car_profile["fuel_history"].append(new_record)
    return new_record


def calculate_fuel_stats(car_profile, days=30):
    """Вычисляет общие расходы (ТО + Топливо) в грн за выбранный период дней."""
    # Заменено монолитом: from datetime import datetime, timedelta
    
    now = datetime.now()
    cutoff_date = now - timedelta(days=days)
    
    fuel_spent = 0.0
    maintenance_spent = 0.0
    
    # Считаем заправки за период
    fuel_history = car_profile.get("fuel_history", [])
    for record in fuel_history:
        try:
            r_date = datetime.strptime(record.get("date", ""), "%d.%m.%Y")
            if r_date >= cutoff_date:
                fuel_spent += float(record.get("cost", 0.0))
        except:
            continue
            
    # Считаем расходы на ТО из общей истории за период
    # Примечание: ожидается, что в общей истории ремонтов "history" есть поле "cost"
    history = car_profile.get("history", [])
    for record in history:
        try:
            r_date = datetime.strptime(record.get("date", ""), "%d.%m.%Y")
            if r_date >= cutoff_date:
                maintenance_spent += float(record.get("cost", 0.0))
        except:
            continue
            
    total_spent = fuel_spent + maintenance_spent
    return {
        "fuel_spent": round(fuel_spent, 2),
        "maintenance_spent": round(maintenance_spent, 2),
        "total_spent": round(total_spent, 2)
    }

def calculate_cost_per_km_brsm(car_profile):
    """Вычисляет стоимость 1 км пути на основе крайних заправок БРСМ (Газ/Бензин)."""
    fuel_history = car_profile.get("fuel_history", [])
    if not fuel_history:
        return 0.0
        
    # Разделяем по типам и сортируем по одометру (свежие в конце)
    gas_logs = sorted([log for log in fuel_history if log.get("type") == "Газ"], key=lambda x: x.get("odometer", 0))
    petrol_logs = sorted([log for log in fuel_history if log.get("type") == "Бензин"], key=lambda x: x.get("odometer", 0))
    
    gas_cost_per_km = 0.0
    petrol_cost_per_km = 0.0
    
    # Если есть ГБО, считаем стоимость км на Газу по последней записи расхода
    if gas_logs:
        last_gas = gas_logs[-1]
        consumption = last_gas.get("consumption", 0.0)
        price = last_gas.get("price", 0.0)
        if consumption > 0:
            # Стоимость км = (расход на 100 км / 100) * цена за литр
            gas_cost_per_km = (consumption / 100.0) * price
            
    # Аналогично для бензина
    if petrol_logs:
        last_petrol = petrol_logs[-1]
        consumption = last_petrol.get("consumption", 0.0)
        price = last_petrol.get("price", 0.0)
        if consumption > 0:
            petrol_cost_per_km = (consumption / 100.0) * price
            
    # Если машина на чистом газу, но бензин используется для прогрева (или наоборот)
    # Возвращаем стоимость км основного используемого топлива (по приоритету Газ, затем Бензин)
    if gas_cost_per_km > 0:
        return round(gas_cost_per_km, 2)
    return round(petrol_cost_per_km, 2)


def calculate_gbo_economy_points(car_profile):
    """Корректный расчет окупаемости ГБО с защитой от одиночных бензиновых чеков."""
    fuel_history = car_profile.get("fuel_history", [])
    if not fuel_history:
        return []
        
    gas_logs = []
    petrol_logs = []
    
    for log in fuel_history:
        f_type = log.get("type")
        odo_val = int(log.get("odometer", 0))
        cost_val = float(log.get("cost", 0.0))
        cons_val = float(log.get("consumption", 0.0))
        price_val = float(log.get("price", 0.0))
        
        item = {"odometer": odo_val, "cost": cost_val, "consumption": cons_val, "price": price_val}
        if f_type == "Газ":
            gas_logs.append(item)
        elif f_type == "Бензин":
            petrol_logs.append(item)
            
    gas_logs.sort(key=lambda x: x["odometer"])
    petrol_logs.sort(key=lambda x: x["odometer"])
    
    if not gas_logs:
        return []
        
    # Вычисляем базовую цену бензина по чекам
    base_petrol_price = petrol_logs[-1]["price"] if petrol_logs else 54.0
    
    # Вычисляем расход бензина: если есть парные чеки - берем их, если нет - берем газовый расход и снижаем на 15%
    base_petrol_consumption = 8.5
    valid_petrol_cons = [log["consumption"] for log in petrol_logs if log["consumption"] > 0]
    
    if valid_petrol_cons:
        base_petrol_consumption = sum(valid_petrol_cons) / len(valid_petrol_cons)
    else:
        valid_gas_cons = [log["consumption"] for log in gas_logs if log["consumption"] > 0]
        if valid_gas_cons:
            # Бензина обычно расходуется на 15% меньше, чем газа
            base_petrol_consumption = (sum(valid_gas_cons) / len(valid_gas_cons)) * 0.85
            
    points = []
    accumulated_gas_cost = 0.0
    start_odo = gas_logs[0]["odometer"]
    
    for log in gas_logs:
        current_odo = log["odometer"]
        delta_km = current_odo - start_odo
        accumulated_gas_cost += log["cost"]
        
        if delta_km > 0:
            accumulated_alternative_cost = (delta_km / 100.0) * base_petrol_consumption * base_petrol_price
        else:
            accumulated_alternative_cost = accumulated_gas_cost
            
        economy = accumulated_alternative_cost - accumulated_gas_cost
        
        points.append({
            "km": delta_km,
            "economy": round(economy, 2),
            "gas_cost": round(accumulated_gas_cost, 2)
        })
        
    return points


# [ЯДРО] NETWORK
import os
# Заменено монолитом: import engine
# Берем точное имя файла базы данных, которое использует само приложение
DB_REAL_PATH = os.path.join(os.getcwd(), "database.txt")
LAST_SENT_ALERTS = {}
# Заменено монолитом: import flet as ft
import json
import io
import time
import traceback
import requests
import urllib3
from concurrent.futures import ThreadPoolExecutor
# Заменено монолитом: import engine

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
network_executor = ThreadPoolExecutor(max_workers=2)

BOT_TOKEN = "8859678783:AAFDa97SuNwBorffMeG59Ad9zYb7u7VqnPw"

TELEGRAM_IP = "149.154.167.220"
BASE_URL = f"https://{TELEGRAM_IP}/bot{BOT_TOKEN}"
BASE_FILE_URL = f"https://{TELEGRAM_IP}/file/bot{BOT_TOKEN}"

URL_EXPORT = f"{BASE_URL}/sendDocument"
URL_UPDATES = f"{BASE_URL}/getUpdates"
URL_FILE_INFO = f"{BASE_URL}/getFile"
URL_DOWNLOAD_BASE = f"{BASE_FILE_URL}/"

CUSTOM_HEADERS = {
    "Host": "api.telegram.org",
    "User-Agent": "Flet-CarJournal-Client/1.0"
}

def show_custom_file_manager_dialog(page: ft.Page, mode: str, db_data_ref: dict, show_message_callback):
    if mode == "export":
        def async_export_worker():
            try:
                print("\n[DEBUG] Воркер экспорта запущен!")
                # Заменено монолитом: import engine
                current_db_data = engine.load_data()
                
                
                if not current_db_data or "cars" not in current_db_data:
                    current_db_data = {"cars": {}, "history": []}
                
                json_text = json.dumps(current_db_data, ensure_ascii=False, indent=4)
                file_stream = io.BytesIO(json_text.encode("utf-8"))
                file_stream.name = "CarJournal_database.json"
                
                payload_data = {
                    "chat_id": 1036911003,
                    "caption": "Резервная копия базы Журнала ТО"
                }
                payload_files = {"document": file_stream}
                
                response = requests.post(
                    URL_EXPORT, 
                    data=payload_data, 
                    files=payload_files, 
                    headers=CUSTOM_HEADERS,
                    proxies={"http": None, "https": None},
                    timeout=15, 
                    verify=False
                )
                
                if response.status_code == 200:
                    async def success_msg_task():
                        show_message_callback("Бэкап успешно отправлен в Telegram!")
                    page.run_task(success_msg_task)
                else:
                    async def error_msg_task():
                        show_message_callback(f"Ошибка облака: Код {response.status_code}")
                    page.run_task(error_msg_task)
            except Exception as ex:
                async def fail_msg_task():
                    show_message_callback(f"Сбой сети: {str(ex)}")
                page.run_task(fail_msg_task)
                
        network_executor.submit(async_export_worker)
        
    elif mode == "import":
        progress_ring = ft.ProgressRing(width=30, height=30, stroke_width=3)
        status_text = ft.Text("Поиск последнего бэкапа in Telegram...", size=14)
        
        def close_dialog(e):
            dialog.open = False
            page.update()
            
        def async_import_worker():
            # Исправлено: ui_task объявлена как async def для жесткого соответствия требованиям run_task()
            def safe_update_ui(text, close_win=False):
                async def ui_task():
                    status_text.value = text
                    if close_win:
                        dialog.open = False
                    page.update()
                page.run_task(ui_task)

            try:
                print("\n[DEBUG] Воркер импорта запущен!")
                
                try:
                    requests.post(f"{BASE_URL}/deleteWebhook", headers=CUSTOM_HEADERS, proxies={"http": None, "https": None}, timeout=5, verify=False)
                    time.sleep(0.5)
                except:
                    pass
                
                print("[DEBUG] Запрашиваем getUpdates...")
                response = requests.get(
                    URL_UPDATES, 
                    headers=CUSTOM_HEADERS,
                    proxies={"http": None, "https": None},
                    timeout=12, 
                    verify=False
                )
                print(f"[DEBUG] Импорт Updates: Код {response.status_code}")
                
                if response.status_code != 200:
                    safe_update_ui(f"Ошибка сети: Код {response.status_code}")
                    return
                    
                updates = response.json().get("result", [])
                backup_file_id = None
                
                for update in reversed(updates):
                    try:
                        message = update.get("message", {})
                        if not message:
                            continue
                        document = message.get("document", {})
                        if document and "json" in str(document.get("file_name", "")).lower():
                            backup_file_id = document.get("file_id")
                            break
                    except:
                        continue
                        
                if not backup_file_id:
                    safe_update_ui("Бэкап в облаке не найден!")
                    return
                    
                safe_update_ui("Скачивание файла...")
                
                file_info_res = requests.get(
                    URL_FILE_INFO, 
                    params={"file_id": backup_file_id}, 
                    headers=CUSTOM_HEADERS,
                    proxies={"http": None, "https": None},
                    timeout=12, 
                    verify=False
                )
                file_path = file_info_res.json().get("result", {}).get("file_path")
                
                download_res = requests.get(
                    URL_DOWNLOAD_BASE + file_path, 
                    headers=CUSTOM_HEADERS,
                    proxies={"http": None, "https": None},
                    timeout=12, 
                    verify=False
                )
                
                print(f"[DEBUG] Скачано байт: {len(download_res.text)}")
                
                try:
                    imported_json = json.loads(download_res.text)
                    if "cars" in imported_json:
                        engine.save_data(imported_json)
                        db_data_ref.clear()
                        db_data_ref.update(engine.load_data()
                
                )
                        
                        # Исправлено: корутина для безопасного коллбэка
                        async def finalize_success():
                            show_message_callback("База успешно восстановлена!")
                            if page.data and "refresh_ui" in page.data:
                                page.data["refresh_ui"]()
                        
                        page.run_task(finalize_success)
                        safe_update_ui("Синхронизация успешна!", close_win=True)
                    else:
                        safe_update_ui("Файл поврежден.")
                except Exception as json_ex:
                    print("[КРИТИЧЕСКИЙ СБОЙ ПАРСИНГА JSON]:")
                    traceback.print_exc()
                    safe_update_ui("Ошибка чтения JSON-структуры")
                    
            except Exception as ex:
                print("[КРИТИЧЕСКИЙ СБОЙ В ПОТОКЕ ИМПОРТА]")
                traceback.print_exc()
                safe_update_ui(f"Ошибка: {str(ex)}")

        confirm_btn = ft.FilledButton(
            "Начать импорт",
            style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.BLUE)
        )
        confirm_btn.on_click = lambda e: [
            setattr(confirm_btn, "visible", False),
            setattr(action_container, "content", progress_ring),
            page.update(),
            network_executor.submit(async_import_worker)
        ]
        
        action_container = ft.Container(content=confirm_btn)
        dialog = ft.AlertDialog(
            title=ft.Text("Облачный Импорт"),
            content=ft.Column(
                [status_text, ft.Container(height=10), action_container],
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            actions=[ft.TextButton("Отмена", on_click=close_dialog)],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()


def send_telegram_alert_message(text_msg):
    """Внутренний фоновый воркер отправки критических уведомлений."""
    url = f"https://{TELEGRAM_IP}/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": 1036911003,
        "text": text_msg,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, data=payload, headers=CUSTOM_HEADERS, proxies={"http": None, "https": None}, timeout=10, verify=False)
    except Exception:
        pass

def check_and_send_alerts(car_profile, car_name=None):
    """Сканирует прогнозы, исправляет имя None и защищает от дублирования алертов."""
    global LAST_SENT_ALERTS
    predictions = car_profile.get("predictions", {})
    alerts_to_send = []
    
    # Исправление бага None: берем переданное имя или ищем в app_state
    if not car_name:
        car_name = engine.app_state.get("selected_car", "Мой Автомобиль")
        
    for task_name, pred in predictions.items():
        rem_km = pred.get("rem_km", 9999)
        if rem_km <= 500:
            status = f"<b>ПРОСРОЧЕНО</b> на {-rem_km} км!" if rem_km < 0 else f"осталось всего {rem_km} км."
            alerts_to_send.append(f"• ⚠️ <b>{task_name}</b>: {status}")
            
    if alerts_to_send:
        full_message_body = "\n".join(alerts_to_send)
        
        # Флуд-контроль: если для этой машины алерты не изменились, игнорируем повторную отправку
        if LAST_SENT_ALERTS.get(car_name) == full_message_body:
            return
            
        LAST_SENT_ALERTS[car_name] = full_message_body
        
        msg_header = f"🚨 <b>Внимание! Критический износ ТО</b>\nАвтомобиль: <b>{car_name}</b>\n\n"
        full_message = msg_header + full_message_body
        
        network_executor.submit(send_telegram_alert_message, full_message)

def auto_import_last_file(show_message_callback):
    """Сканирует историю чата бота, находит последний JSON-бэкап и импортирует его."""
    url_updates = f"https://{TELEGRAM_IP}/bot{BOT_TOKEN}/getUpdates?offset=-1&limit=1"
    try:
        response = requests.get(url_updates, headers=CUSTOM_HEADERS, verify=False, timeout=10)
        if response.status_code != 200:
            show_message_callback("Ошибка подключения к Telegram API")
            return
            
        res_data = response.json()
        if not res_data.get("ok"):
            show_message_callback("Не удалось получить обновления чата")
            return
            
        # Ищем самый свежий файл базы данных в истории сообщений (сканируем с конца)
        target_file_id = None
        for result in reversed(res_data.get("result", [])):
            message = result.get("message", {})
            document = message.get("document", {})
            if document and document.get("file_name") == "Carjournal_database.json":
                target_file_id = document.get("file_id")
                break
                
        if not target_file_id:
            show_message_callback("Файл бэкапа не найден в последних сообщениях чата")
            return
            
        # Получаем прямую ссылку на скачивание файла
        url_file_info = f"https://{TELEGRAM_IP}/bot{BOT_TOKEN}/getFile?file_id={target_file_id}"
        file_info_resp = requests.get(url_file_info, headers=CUSTOM_HEADERS, verify=False, timeout=10).json()
        
        if not file_info_resp.get("ok"):
            show_message_callback("Ошибка получения ссылки на файл")
            return
            
        file_path = file_info_resp["result"]["file_path"]
        url_download = f"https://{TELEGRAM_IP}/file/bot{BOT_TOKEN}/{file_path}"
        
        # Скачиваем файл и перезаписываем локальную базу данных
        db_resp = requests.get(url_download, headers=CUSTOM_HEADERS, verify=False, timeout=10)
        if db_resp.status_code == 200:
            with open(DB_REAL_PATH, "w", encoding="utf-8") as f:
                f.write(db_resp.text)
            show_message_callback("✅ База данных успешно импортирована из чата!")
            # Триггерим обновление интерфейса приложения
            # Заменено монолитом: import engine
            engine.load_data()
                
                
        else:
            show_message_callback("Не удалось скачать файл бэкапа")
            
    except Exception as ex:
        show_message_callback(f"Ошибка импорта: {str(ex)}")


def auto_export_file_to_telegram(page, show_message_callback):
    """Прямой экспорт базы данных в Telegram с кэшированием ID файла."""
    import requests
    url = f"https://{TELEGRAM_IP}/bot{BOT_TOKEN}/sendDocument"
    
    def show_alert(msg_text):
        def close_dialog(_):
            dialog.open = False
            page.update()
        dialog = ft.AlertDialog(
            title=ft.Text("Синхронизация базы"),
            content=ft.Text(msg_text),
            actions=[ft.TextButton("ОК", on_click=close_dialog)]
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()
    
    if not os.path.exists(DB_REAL_PATH):
        show_alert("Ошибка: Файл базы данных не найден.")
        return
        
    try:
        with open(DB_REAL_PATH, "rb") as file_data:
            files = {"document": ("Carjournal_database.json", file_data)}
            payload = {"chat_id": 1036911003, "caption": "📦 Резервная копия базы"}
            resp = requests.post(url, data=payload, files=files, headers=CUSTOM_HEADERS, verify=False, timeout=10)
            
            if resp.status_code == 200:
                resp_json = resp.json()
                if resp_json.get("ok"):
                    doc_info = resp_json["result"].get("document", {})
                    engine.app_state["last_file_id"] = doc_info.get("file_id")
                show_alert("✅ База данных успешно экспортирована в Telegram!")
            else:
                show_alert(f"Ошибка сервера: {resp.status_code}")
    except Exception as e:
        show_alert(f"Ошибка сети: {str(e)}")

def auto_import_last_file(page, show_message_callback):
    """Импорт базы данных на основе проверенной логики скрипта smart_cloud_sync."""
    import requests
    # Заменено монолитом: import engine
    # Заменено монолитом: import flet as ft
    import json
    
    def show_alert(msg_text):
        def close_dialog(_):
            dialog.open = False
            page.update()
        dialog = ft.AlertDialog(
            title=ft.Text("Синхронизация базы"),
            content=ft.Text(msg_text),
            actions=[ft.TextButton("ОК", on_click=close_dialog)]
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    print("[СЕТЬ] Сканирование чата по методу smart_cloud_sync...")
    target_file_id = None
    CHAT_ID = 1036911003
    
    try:
        # Запрашиваем глубокий кэш обновлений (100 пунктов), как в рабочем скрипте
        url_updates = f"https://{TELEGRAM_IP}/bot{BOT_TOKEN}/getUpdates?offset=-1&limit=100"
        response = requests.get(url_updates, headers=CUSTOM_HEADERS, verify=False, timeout=10)
        
        if response.status_code == 200:
            res_data = response.json()
            # Сканируем массив строго с конца
            for result in reversed(res_data.get("result", [])):
                message = result.get("message", result.get("edited_message", {}))
                
                # Фильтруем отправителя: ищем файлы только от вашего chat_id (телефона)
                if message.get("chat", {}).get("id") == CHAT_ID or message.get("from", {}).get("id") == CHAT_ID:
                    document = message.get("document", {})
                    if document:
                        fname = str(document.get("file_name", ""))
                        # Проверяем имя файла без жесткой привязки к регистру
                        if "carjournal_database" in fname.lower():
                            target_file_id = document.get("file_id")
                            print(f"[УСПЕХ] Найден файл от телефона по методу smart_sync: {target_file_id[:15]}...")
                            break
    except Exception as ex:
        print(f"[ОШИБКА СЕТИ]: {ex}")

    if not target_file_id:
        show_alert("Файл базы от телефона не найден в кэше обновлений. Нажмите 'ЭКСПОРТ' на телефоне и повторите попытку.")
        return

    try:
        # Прямое скачивание
        url_file_info = f"https://{TELEGRAM_IP}/bot{BOT_TOKEN}/getFile?file_id={target_file_id}"
        file_info_resp = requests.get(url_file_info, headers=CUSTOM_HEADERS, verify=False, timeout=10).json()
        
        if file_info_resp.get("ok"):
            file_path = file_info_resp["result"]["file_path"]
            url_download = f"https://{TELEGRAM_IP}/file/bot{BOT_TOKEN}/{file_path}"
            db_resp = requests.get(url_download, headers=CUSTOM_HEADERS, verify=False, timeout=10)
            
            if db_resp.status_code == 200:
                # Перезаписываем корень приложения
                with open(DB_REAL_PATH, "w", encoding="utf-8") as f:
                    f.write(db_resp.text)
                
                # Синхронизируем состояние памяти
                engine.app_state["last_file_id"] = target_file_id
                fresh_db = engine.load_data()
                
                if page.data:
                    page.data["db_data"] = fresh_db
                    
                show_alert("✅ База данных успешно импортирована с вашего телефона!")
                
                # Принудительно заставляем main.py перерисовать экран новыми данными
                if page.data and "refresh_ui" in page.data:
                    page.data["refresh_ui"]()
            else:
                show_alert("Не удалось загрузить файл из облака Telegram.")
        else:
            show_alert("Срок ссылки файла в Telegram истек. Сделайте новый экспорт на телефоне.")
    except Exception as ex:
        show_alert(f"Ошибка шлюза импорта: {str(ex)}")


# [ЯДРО] VIEWS
# Заменено монолитом: import flet as ft
# Заменено монолитом: from datetime import datetime, timedelta
# Заменено монолитом: import engine

def generate_analytics_view(page, car_profile):
    view_column = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=15)
    current_km = car_profile.get("odometer", {}).get("value", 0)
    tasks = car_profile.get("maintenance_data", {})
    
    # --- БЛОК 1: ФИНАНСОВАЯ СТАТИСТИКА И СТОИМОСТЬ КИЛОМЕТРА ---
    stats_30 = engine.calculate_fuel_stats(car_profile, days=30)
    cost_per_km = engine.calculate_cost_per_km_brsm(car_profile)
    
    fin_card = ft.Card(
        content=ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.MONETIZATION_ON, color=ft.Colors.GREEN_700, size=24),
                    ft.Text("Финансовая аналитика (30 дн.)", size=16, weight=ft.FontWeight.BOLD)
                ], alignment=ft.MainAxisAlignment.START, spacing=8),
                ft.Divider(height=1, color=ft.Colors.BLACK_12),
                ft.Row([
                    ft.Text("⛽ Топливо:", size=13),
                    ft.Text(f"{stats_30['fuel_spent']} грн", size=13, weight=ft.FontWeight.W_600)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([
                    ft.Text("🛠️ Ремонт и ТО:", size=13),
                    ft.Text(f"{stats_30['maintenance_spent']} грн", size=13, weight=ft.FontWeight.W_600)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([
                    ft.Text("💰 Всего затрат:", size=14, weight=ft.FontWeight.BOLD),
                    ft.Text(f"{stats_30['total_spent']} грн", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(height=1, color=ft.Colors.BLACK_12),
                ft.Row([
                    ft.Text("📍 Стоимость 1 км пути:", size=13, weight=ft.FontWeight.W_500),
                    ft.Container(
                        content=ft.Text(f"{cost_per_km} грн/км", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        bgcolor=ft.Colors.GREEN_700,
                        padding=ft.Padding(6, 2, 6, 2),
                        border_radius=4
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ], spacing=8),
            padding=14
        ),
        bgcolor=ft.Colors.SURFACE_CONTAINER_LOW
    )
    view_column.controls.append(fin_card)
    
    # --- БЛОК 2: ТЕКСТОВЫЙ БАЛАНС ОКУПАЕМОСТИ ГБО ---
    gbo_points = engine.calculate_gbo_economy_points(car_profile)
    last_econ = gbo_points[-1]["economy"] if gbo_points else 0.0
    gas_cost = gbo_points[-1]["gas_cost"] if gbo_points else 0.0
    
    # Расчет условного прогресса окупаемости оборудования (например, до 15 000 грн за установку)
    gbo_target = 15000.0
    progress_val = max(0.0, min(1.0, last_econ / gbo_target)) if last_econ > 0 else 0.0
    
    gbo_card = ft.Card(
        content=ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.ENERGY_SAVINGS_LEAF, color=ft.Colors.GREEN_700, size=22),
                    ft.Text("Эффективность и окупаемость ГБО", size=14, weight=ft.FontWeight.BOLD)
                ]),
                ft.Divider(height=1, color=ft.Colors.BLACK_12),
                ft.Row([
                    ft.Text("🔥 Реальный расход на Газ:", size=13),
                    ft.Text(f"{gas_cost} грн", size=13, weight=ft.FontWeight.W_500, color=ft.Colors.ORANGE_900)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([
                    ft.Text("📈 Чистая экономия бюджета:", size=13),
                    ft.Text(f"{last_econ} грн" if last_econ < 0 else f"+{last_econ} грн", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700 if last_econ >= 0 else ft.Colors.RED_600)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Column([
                    ft.Row([
                        ft.Text("Прогресс окупаемости оборудования:", size=11, color=ft.Colors.GREY_600),
                        ft.Text(f"{int(progress_val * 100)}%", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.ProgressBar(value=progress_val, color=ft.Colors.GREEN_700, bgcolor=ft.Colors.GREY_200, height=6)
                ], spacing=4)
            ], spacing=8),
            padding=14
        )
    )
    view_column.controls.append(gbo_card)
    
    # --- БЛОК 3: АНАЛИТИКА ИЗНОСА РЕГЛАМЕНТОВ ТО ---
    view_column.controls.append(ft.Text("Аналитика износа регламентов", size=18, weight=ft.FontWeight.BOLD))
    
    if not tasks:
        view_column.controls.append(ft.Text("Нет данных по регламентам", color=ft.Colors.GREY_500, italic=True))
        return view_column
        
    for t_name, t_data in tasks.items():
        interval = t_data.get("interval", 1)
        remains = (t_data.get("last_service", 0) + interval) - current_km
        passed = max(0, current_km - t_data.get("last_service", 0))
        res = max(0.0, min(1.0, 1.0 - (passed / interval)))
        b_color = ft.Colors.RED_600 if remains <= 0 else (ft.Colors.ORANGE_700 if remains <= 500 else ft.Colors.GREEN_700)
        st_text = "Срочно заменить!" if remains <= 0 else f"Осталось {remains} км"
        
        view_column.controls.append(ft.Card(content=ft.Container(content=ft.Column([
            ft.Row([ft.Text(t_name, size=14, weight=ft.FontWeight.BOLD, expand=True), ft.Text(f"{int(res * 100)}%", size=13, color=b_color)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.ProgressBar(value=res, color=b_color, bgcolor=ft.Colors.GREY_200, height=8),
            ft.Text(st_text, size=12, color=ft.Colors.GREY_600, italic=True)
        ], spacing=4), padding=12)))
        
    return view_column

def show_task_history_dialog(page, db_data, task_name, car_profile, rebuild, show_msg): 
    h_col = ft.Column(scroll=ft.ScrollMode.AUTO, height=220, spacing=8) 
 
    def refresh(): 
        h_col.controls.clear() 
        if "history" not in car_profile: 
            car_profile["history"] = [] 
        t_hist = [h for h in car_profile.get("history", []) if h.get("task") == task_name] 
 
        if not t_hist: 
            h_col.controls.append(ft.Text("Пусто", italic=True)) 
        else: 
            for rec in sorted(t_hist, key=lambda x: int(x.get('odometer', 0)), reverse=True): 
                # Функция-замыкание для удаления 
                def make_del(r=rec): 
                    return lambda _: [car_profile["history"].remove(r), engine.save_data(db_data), refresh(), rebuild(), show_msg("Удалено")] 
 
                # Функция-замыкание для вызова окна редактирования записи 
                def make_edit(r=rec): 
                    def open_edit_dialog(_): 
                        edit_odo = ft.TextField(label="Пробег", value=str(r.get("odometer", ""))) 
                        edit_date = ft.TextField(label="Дата", value=str(r.get("date", ""))) 
                        edit_comm = ft.TextField(label="Комментарий", value=str(r.get("comment", ""))) 
 
                        def save_edited_rec(_): 
                            try: 
                                km = int(edit_odo.value) 
                                dt_str = edit_date.value.strip() 
                                datetime.strptime(dt_str, "%d.%m.%Y") 
 
                                # Обновляем данные в оригинальной записи внутри списка 
                                r["odometer"] = km 
                                r["date"] = dt_str 
                                r["comment"] = edit_comm.value.strip() 
 
                                engine.save_data(db_data) 
                                edit_dlg.open = False 
                                page.update() 
                                refresh() 
                                rebuild() 
                                show_msg("Запись изменена!") 
                            except: 
                                show_msg("Ошибка формата!") 
 
                        edit_dlg = ft.AlertDialog( 
                            title=ft.Text("Правка записи ТО"), 
                            content=ft.Column([edit_odo, edit_date, edit_comm], tight=True), 
                            actions=[ft.TextButton("Сохранить", on_click=save_edited_rec)] 
                        ) 
                        page.overlay.append(edit_dlg) 
                        edit_dlg.open = True 
                        page.update() 
                    return open_edit_dialog  # ТУТ ИСПРАВЛЕНО: возвращаем правильное имя!
 
                # Отрисовка строки истории с двумя кнопками: Редактировать и Удалить 
                h_col.controls.append(ft.Container( 
                    content=ft.Row([ 
                        ft.Column([ 
                            ft.Row([ft.Text(f"📅 {rec.get('date')}"), ft.Text(f"📍 {rec.get('odometer')} км")]), 
                            ft.Text(rec.get('comment', ""), size=12, color=ft.Colors.GREY_600, italic=True) 
                        ]), 
                        ft.Row([ 
                            ft.IconButton(ft.Icons.EDIT, icon_color=ft.Colors.BLUE_600, icon_size=18, on_click=make_edit()), 
                            ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED_400, icon_size=18, on_click=make_del()) 
                        ], spacing=0) 
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), 
                    padding=6, bgcolor=ft.Colors.GREY_50, border_radius=6 
                )) 
        page.update() 
 
    dlg = ft.AlertDialog( 
        title=ft.Text(f"История: {task_name}"), 
        content=ft.Container(content=h_col, adaptive=True), 
        actions=[ft.TextButton("Закрыть", on_click=lambda _: [setattr(dlg, "open", False), page.update()])]
    ) 
    page.overlay.append(dlg) 
    dlg.open = True 
    refresh() 
 
def show_add_task_history_dialog(page, db_data, t_name, p_profile, rebuild, show_msg):
    h_odo = ft.TextField(label="Пробег")
    h_date = ft.TextField(label="Дата", value=datetime.now().strftime("%d.%m.%Y"))
    
    def save(_):
        try:
            km = int(h_odo.value)
            dt_str = h_date.value.strip()
            datetime.strptime(dt_str, "%d.%m.%Y")
            
            # Наша главная броня от багов сохранения:
            if "history" not in p_profile:
                p_profile["history"] = []
                
            p_profile["history"].append({"task": t_name, "odometer": km, "date": dt_str})
            
            if km > p_profile["maintenance_data"][t_name].get("last_service", 0):
                p_profile["maintenance_data"][t_name].update({"last_service": km, "date": dt_str})
                
            engine.save_data(db_data)
            dlg.open = False
            page.update()
            rebuild()
            show_msg("Добавлено!")
        except Exception as ex:
            show_msg("Ошибка формата!")
            
    dlg = ft.AlertDialog(title=ft.Text("Ввод истории"), content=ft.Column([h_odo, h_date], tight=True), 
                         actions=[ft.TextButton("Сохранить", on_click=save)])
    page.overlay.append(dlg)
    dlg.open = True
    page.update()

def create_task_actions(page, db_data, p, t, current_km, rebuild, show_msg):
    def reset_click(_):
        now = datetime.now().strftime("%d.%m.%Y")
        p["maintenance_data"][t].update({"last_service": current_km, "date": now})
        if "history" not in p: p["history"] = []
        p["history"].append({"task": t, "odometer": current_km, "date": now, "comment": "Быстрый сброс"})
        engine.save_data(db_data); rebuild(); show_msg("ТО отмечено как выполненное!")
        
    def change_click(_):
        n_in = ft.TextField(label="Имя регламента", value=t)
        i_in = ft.TextField(label="Интервал (км)", value=str(p["maintenance_data"][t]["interval"]))
        def save(_):
            try:
                nn = n_in.value.strip(); ni = int(i_in.value)
                if ni <= 0 or not nn: raise ValueError
                old = p["maintenance_data"].pop(t); old["interval"] = ni; p["maintenance_data"][nn] = old
                if nn != t:
                    if "history" not in p: p["history"] = []
                    for h in p.get("history", []):
                        if h["task"] == t: h["task"] = nn
                engine.save_data(db_data); dlg.open = False; page.update(); rebuild(); show_msg("Регламент изменен")
            except: show_msg("Ошибка заполнения")
        dlg = ft.AlertDialog(title=ft.Text("Правка регламента"), content=ft.Column([n_in, i_in], tight=True), actions=[ft.TextButton("OK", on_click=save)])
        page.overlay.append(dlg); dlg.open = True; page.update()
        
    def delete_click(_):
        p["maintenance_data"].pop(t)
        if "history" in p:
            p["history"] = [h for h in p.get("history", []) if h["task"] != t]
        engine.save_data(db_data); rebuild(); show_msg("Регламент полностью удален")
        
    return reset_click, change_click, delete_click

def build_maintenance_list(page, db_data, car_name, car_profile, header_card, rebuild, show_msg, add_task_fn=None):
    c_list = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=10)
    c_list.controls.append(header_card)
    
    status_header = ft.Row([
        ft.Text("Статус регламентных работ:", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_800),
        ft.IconButton(ft.Icons.ADD_CIRCLE, tooltip="Создать новый регламент ТО", icon_color=ft.Colors.BLUE_600, on_click=add_task_fn)
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    c_list.controls.append(ft.Container(content=status_header, padding=ft.Padding.only(left=0, top=10, right=0, bottom=5)))
    
    current_km = car_profile.get("odometer", {}).get("value", 0)
    daily = car_profile.get("daily_mileage", 45)
    tasks = car_profile.get("maintenance_data", {})
    
    if not tasks:
        c_list.controls.append(ft.Container(content=ft.Text("Нет регламентов ТО.", color=ft.Colors.GREY_500), alignment=ft.Alignment.CENTER, padding=20))
        return c_list
        
    for t_name, t_data in tasks.items():
        remains = (t_data.get("last_service", 0) + t_data.get("interval", 0)) - current_km
        f_str = (datetime.now() + timedelta(days=remains/daily)).strftime("%d.%m.%Y") if remains > 0 and daily > 0 else "Срочно ТО!"
        color = ft.Colors.RED_600 if remains <= 0 else (ft.Colors.ORANGE_700 if remains <= 500 else ft.Colors.GREEN_700)
        sub = f"Осталось: {remains} км | Срок: {f_str}"
        
        r_fn, c_fn, d_fn = create_task_actions(page, db_data, car_profile, t_name, current_km, rebuild, show_msg)
        card_bgcolor = "#FFF0F0" if remains <= 0 else ("#FFF9F2" if remains <= 500 else ft.Colors.SURFACE)
        
        item_card = ft.Container(
            bgcolor=card_bgcolor,
            margin=ft.Margin(4, 0, 4, 2),
            padding=ft.Padding(4, 0, 4, 0),
            border_radius=ft.BorderRadius(12, 12, 12, 12),
            shadow=ft.BoxShadow(blur_radius=6, color=ft.Colors.with_opacity(0.04, ft.Colors.BLACK), offset=ft.Offset(0, 2)),
            content=ft.ExpansionTile(
                title=ft.Text(t_name, weight=ft.FontWeight.BOLD, size=14),
                subtitle=ft.Text(sub, color=color, size=12),
                controls=[
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(f"Интервал: {t_data.get('interval')} км", size=13), 
                                ft.Text(f"Прошлый: {t_data.get('last_service')} км", size=13)
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Row([
                                ft.Button("История ТО", icon=ft.Icons.HISTORY, tooltip="Просмотр и удаление истории записей", on_click=lambda e, tn=t_name: show_task_history_dialog(page, db_data, tn, car_profile, rebuild, show_msg)),
                                ft.IconButton(ft.Icons.POST_ADD, tooltip="Внести запись в историю вручную (кастомная дата/пробег)", icon_color=ft.Colors.GREEN_700, on_click=lambda e, tn=t_name: show_add_task_history_dialog(page, db_data, tn, car_profile, rebuild, show_msg)),
                                ft.IconButton(ft.Icons.CHECK_CIRCLE, tooltip="Выполнено сейчас (Быстрый сброс на текущий пробег)", icon_color=ft.Colors.BLUE_600, on_click=r_fn),
                                ft.IconButton(ft.Icons.SETTINGS, tooltip="Настройки (Изменить имя регламента или интервал)", icon_color=ft.Colors.BLUE_GREY_600, on_click=c_fn),
                                ft.IconButton(ft.Icons.DELETE_FOREVER, tooltip="Полностью удалить этот регламент", icon_color=ft.Colors.RED_400, on_click=d_fn)
                            ], alignment=ft.MainAxisAlignment.END)
                        ]), padding=12, bgcolor=ft.Colors.with_opacity(0.4, ft.Colors.SURFACE_CONTAINER_LOW)
                    )
                ]
            )
        )
        c_list.controls.append(item_card)
    return c_list


def show_car_odometer_history_dialog(page, db_data, car_profile, rebuild, show_msg):
    h_cont = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, height=240)
    dlg = None
 
    def render():
        h_cont.controls.clear()
        for item in sorted(car_profile.get("odometer_history", []), key=lambda x: int(x.get("value", 0)), reverse=True):
            def make_del(i=item):
                return lambda _: [car_profile["odometer_history"].remove(i), engine.save_data(db_data), render(), rebuild(), show_msg("Удалено")]
            h_cont.controls.append(ft.Container(
                content=ft.Row([
                    ft.Column([ft.Text(f"{item['value']} км", weight=ft.FontWeight.BOLD), ft.Text(item['date'])]),
                    ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED_400, on_click=make_del())
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=5,
                border=ft.Border.all(1, ft.Colors.BLACK_12),
                border_radius=6
            ))
        if dlg: dlg.update()
        else: page.update()
 
    def add_click(_):
        a_km = ft.TextField(label="Пробег")
        a_dt = ft.TextField(label="Дата", value=datetime.now().strftime("%d.%m.%Y"))
 
        def save(_):
            try:
                v = int(a_km.value); d = a_dt.value.strip(); datetime.strptime(d, '%d.%m.%Y')
                if "odometer_history" not in car_profile:
                    car_profile["odometer_history"] = []
                car_profile["odometer_history"].append({"value": v, "date": d})
                if v >= car_profile["odometer"].get("value", 0):
                    car_profile["odometer"] = {"value": v, "date": d}
                car_profile["daily_mileage"] = engine.recalculate_auto_daily_mileage(car_profile)
                engine.save_data(db_data); adlg.open = False; render(); rebuild(); show_msg("Добавлено!")
            except:
                show_msg("Ошибка формата!")
 
        adlg = ft.AlertDialog(title=ft.Text("Добавить пробег"), content=ft.Column([a_km, a_dt], tight=True), actions=[ft.TextButton("OK", on_click=save)])
        page.overlay.append(adlg); adlg.open = True; page.update()
 
    total_count = len(car_profile.get("odometer_history", []))
    dlg = ft.AlertDialog(
        bgcolor=ft.Colors.WHITE,
        title=ft.Text(f"История пробега (записей: {total_count})"),
        content=ft.Column([
            ft.Button("Добавить запись", icon=ft.Icons.ADD, on_click=add_click),
            ft.Divider(height=1, color=ft.Colors.BLACK_12),
            h_cont
        ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=10, tight=True, width=360),
        actions=[ft.TextButton("Закрыть", on_click=lambda _: [setattr(dlg, "open", False), page.update()])]
    )
    page.overlay.append(dlg); dlg.open = True; page.update(); render()


def show_fuel_history_dialog(page, db_data, car_profile, rebuild, show_msg):
    h_col = ft.Column(scroll=ft.ScrollMode.AUTO, height=240, spacing=8)
    dlg = None
 
    def refresh():
        h_col.controls.clear()
        f_hist = car_profile.get("fuel_history", [])
 
        if not f_hist:
            h_col.controls.append(ft.Text("История заправок пуста", italic=True))
        else:
            for rec in sorted(f_hist, key=lambda x: int(x.get("odometer", 0)), reverse=True):
                def make_del(r=rec):
                    return lambda _: [car_profile["fuel_history"].remove(r), engine.save_data(db_data), refresh(), rebuild(), show_msg("Запись удалена")]
 
                def make_edit(r=rec):
                    def open_edit_fuel_dialog(_):
                        e_liters = ft.TextField(label="Количество литров", value=str(r.get("liters", "")))
                        e_cost = ft.TextField(label="Общая сумма (грн)", value=str(r.get("cost", "")))
                        e_odo = ft.TextField(label="Пробег (км)", value=str(r.get("odometer", "")))
                        e_date = ft.TextField(label="Дата", value=str(r.get("date", "")))
                        e_comm = ft.TextField(label="Комментарий", value=str(r.get("comment", "")))
 
                        def save_edited_fuel(_):
                            try:
                                liters = float(e_liters.value)
                                cost = float(e_cost.value)
                                odo = int(e_odo.value)
                                dt_str = e_date.value.strip()
                                datetime.strptime(dt_str, '%d.%m.%Y')
                                if liters <= 0 or cost <= 0 or odo <= 0: raise ValueError
 
                                r["liters"] = liters
                                r["cost"] = cost
                                r["odometer"] = odo
                                r["date"] = dt_str
                                r["comment"] = e_comm.value.strip()
                                r["price"] = round(cost / liters, 2)
 
                                same_type_logs = [log for log in car_profile["fuel_history"] if log.get("type") == r.get("type")]
                                same_type_logs.sort(key=lambda x: int(x.get("odometer", 0)))
 
                                for idx, log in enumerate(same_type_logs):
                                    if idx == 0:
                                        log["consumption"] = 0.0
                                    else:
                                        delta = int(log["odometer"]) - int(same_type_logs[idx-1]["odometer"])
                                        log["consumption"] = round((float(log["liters"]) / delta) * 100, 2) if delta > 0 else 0.0
 
                                engine.save_data(db_data); edit_fuel_dlg.open = False; page.update(); refresh(); rebuild(); show_msg("Заправка успешно изменена!")
                            except:
                                show_msg("Ошибка формата!")
 
                        edit_fuel_dlg = ft.AlertDialog(title=ft.Text("Правка записи заправки"), content=ft.Column([e_liters, e_cost, e_odo, e_date, e_comm], tight=True, spacing=10), actions=[ft.TextButton("Сохранить", on_click=save_edited_fuel)])
                        page.overlay.append(edit_fuel_dlg); edit_fuel_dlg.open = True; page.update()
                    return open_edit_fuel_dialog
 
                cons_text = f" | Расход: {rec.get('consumption')} л/100км" if rec.get("consumption", 0) > 0 else ""
                info_line = f"⛽ {rec.get('type')} | {rec.get('liters')} л | {rec.get('price')} грн/л"
                cost_line = f"💰 Сумма: {rec.get('cost')} грн{cons_text}"
 
                h_col.controls.append(ft.Container(
                    content=ft.Row([
                        ft.Column([
                            ft.Row([ft.Text(f"📅 {rec.get('date')}"), ft.Text(f"📍 {rec.get('odometer')} км", weight=ft.FontWeight.BOLD)]),
                            ft.Text(info_line, size=13),
                            ft.Text(cost_line, size=13, color=ft.Colors.BLUE_GREY_700, weight=ft.FontWeight.W_500),
                            ft.Text(rec.get('comment', ""), size=11, color=ft.Colors.GREY_500, italic=True) if rec.get('comment') else ft.Container()
                        ], spacing=2, expand=True),
                        ft.Row([
                            ft.IconButton(ft.Icons.EDIT, icon_color=ft.Colors.BLUE_600, icon_size=18, on_click=make_edit()),
                            ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED_400, icon_size=18, on_click=make_del())
                        ], spacing=0)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=8, bgcolor=ft.Colors.GREY_50, border_radius=6, border=ft.Border.all(1, ft.Colors.BLACK_12)
                ))
        if dlg: dlg.update()
        else: page.update()
 
    total_count = len(car_profile.get("fuel_history", []))
    dlg = ft.AlertDialog(
        bgcolor=ft.Colors.WHITE,
        title=ft.Text(f"Журнал заправок (чеков: {total_count})"),
        content=ft.Column([
            ft.Divider(height=1, color=ft.Colors.BLACK_12),
            h_col
        ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=10, tight=True, width=380),
        actions=[ft.TextButton("Закрыть", on_click=lambda _: [setattr(dlg, "open", False), page.update()])]
    )
    page.overlay.append(dlg); dlg.open = True; page.update(); refresh()


def show_add_fuel_dialog(page, db_data, car_profile, rebuild, show_msg):
    f_type = ft.RadioGroup(content=ft.Row([
        ft.Radio(value="Бензин", label="Бензин"),
        ft.Radio(value="Газ", label="Газ")
    ], alignment=ft.MainAxisAlignment.SPACE_AROUND), value="Бензин")
    
    in_liters = ft.TextField(label="Количество литров", keyboard_type=ft.KeyboardType.NUMBER)
    in_cost = ft.TextField(label="Общая сумма (грн)", keyboard_type=ft.KeyboardType.NUMBER)
    in_odo = ft.TextField(label="Текущий пробег (км)", keyboard_type=ft.KeyboardType.NUMBER, value=str(car_profile.get("odometer", {}).get("value", "")))
    in_date = ft.TextField(label="Дата заправки", value=datetime.now().strftime("%d.%m.%Y"))
    in_comm = ft.TextField(label="Комментарий (АЗС, марка)", value="БРСМ")

    def save_click(_):
        try:
            liters = float(in_liters.value)
            cost = float(in_cost.value)
            odo = int(in_odo.value)
            dt_str = in_date.value.strip()
            datetime.strptime(dt_str, "%d.%m.%Y")
            
            if liters <= 0 or cost <= 0 or odo <= 0:
                raise ValueError
                
            # Передаем cost вместо price в обновленный метод
            engine.add_fuel_record(car_profile, f_type.value, liters, cost, odo, dt_str, in_comm.value.strip())
            
            if odo >= car_profile["odometer"].get("value", 0):
                car_profile["odometer"] = {"value": odo, "date": dt_str}
                car_profile["daily_mileage"] = engine.recalculate_auto_daily_mileage(car_profile)
                
            engine.save_data(db_data)
            dlg.open = False
            page.update()
            rebuild()
            show_msg("Заправка успешно учтена!")
        except:
            show_msg("Ошибка! Проверьте формат полей.")

    dlg = ft.AlertDialog(
        title=ft.Text("Учёт заправки (до полного)"),
        content=ft.Column([
            ft.Text("Тип топлива:", size=12, color=ft.Colors.GREY_600),
            f_type, in_liters, in_cost, in_odo, in_date, in_comm
        ], tight=True, spacing=10),
        actions=[
            ft.TextButton("Отмена", on_click=lambda _: [setattr(dlg, "open", False), page.update()]),
            ft.ElevatedButton("Сохранить", bgcolor=ft.Colors.AMBER_700, color=ft.Colors.WHITE, on_click=save_click)
        ]
    )
    page.overlay.append(dlg)
    dlg.open = True
    page.update()

# [ЯДРО] MAIN
import sys
import os
# Принудительное связывание путей для среды Android
base_dir = os.path.abspath(os.path.dirname(__file__))
if base_dir not in sys.path: sys.path.insert(0, base_dir)
cwd_dir = os.getcwd()
if cwd_dir not in sys.path: sys.path.insert(0, cwd_dir)
if "" not in sys.path: sys.path.insert(0, "")
# Заменено монолитом: import flet as ft
from datetime import datetime
# Заменено монолитом: import engine
# Заменено монолитом: import views
# Заменено монолитом: import network

APP_VERSION = "1.2.5"
BUILD_NUMBER = "11"
db_data = {}

def run_local_telegram_sync():
    import shutil
    import glob
    tg_downloads_path = r"C:\Users\User\Загрузки\Telegram Desktop"
    import os
    if not os.path.exists(tg_downloads_path):
        import os
        user_profile = os.environ.get("USERPROFILE", "C:\\Users\\User")
        tg_downloads_path = os.path.join(user_profile, "Downloads", "Telegram Desktop")
        import os
    if not os.path.exists(tg_downloads_path):
            tg_downloads_path = os.path.join(user_profile, "Загрузки", "Telegram Desktop")
    import os
    if not os.path.exists(tg_downloads_path): return False
    search_pattern = os.path.join(tg_downloads_path, "*atabase*.json")
    found_files = glob.glob(search_pattern)
    if not found_files: return False
    try:
        found_files.sort(key=os.path.getmtime, reverse=True)
        shutil.copy2(found_files[0], "database.txt")
        return True
    except:
        return False

def main(page: ft.Page):
    page.scroll = ft.ScrollMode.AUTO
    global db_data
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = ft.Colors.SURFACE_CONTAINER_LOW
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.AMBER)
    page.title = "Журнал ТО"
    page.window_width = 1200
    page.window_height = 800
    db_data = engine.load_data()
    
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
        current_db = engine.load_data()
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
        selected_car = engine.app_state.get("selected_car")
        if not selected_car or selected_car not in cars_dict:
            selected_car = car_names[0]
            engine.app_state["selected_car"] = selected_car
            
        car_buttons_row = ft.Row(spacing=10, scroll=ft.ScrollMode.AUTO)
        for name in car_names:
            is_selected = (name == selected_car)
            def make_click_handler(car_name_to_select=name):
                return lambda _: [engine.app_state.update({"selected_car": car_name_to_select}), rebuild_ui()]
            btn = ft.Container(
                content=ft.Text(str(name), color=ft.Colors.WHITE if is_selected else ft.Colors.BLACK, weight=ft.FontWeight.BOLD if is_selected else ft.FontWeight.NORMAL, size=14),
                bgcolor=ft.Colors.AMBER_700 if is_selected else ft.Colors.GREY_200, padding=ft.Padding(16, 8, 16, 8), border_radius=8, on_click=make_click_handler(), animate=200
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
            except ValueError: show_message("Ошибка поля пробега")
            
        def add_car_click(e):
            car_name_input = ft.TextField(label="Марка / Модель")
            def save_new_car(_):
                name = car_name_input.value.strip()
                if not name or name in current_db["cars"]: return
                current_db["cars"][name] = {"odometer": {"value": 0, "date": datetime.now().strftime("%d.%m.%Y")}, "daily_mileage": 0, "odometer_history": [], "maintenance_data": {}, "history": []}
                engine.save_data(current_db); engine.app_state["selected_car"] = name
                dialog.open = False; page.update(); rebuild_ui()
            dialog = ft.AlertDialog(title=ft.Text("Добавить автомобиль"), content=ft.Column([car_name_input], tight=True), actions=[ft.TextButton("Добавить", on_click=save_new_car)])
            page.overlay.append(dialog); dialog.open = True; page.update()
            
        def edit_car_name_click(e):
            edit_name_input = ft.TextField(label="Новое имя профиля", value=selected_car)
            def save_name_change(_):
                new_name = edit_name_input.value.strip()
                success_rename, rename_msg = engine.rename_car_profile(current_db, selected_car, new_name)
                if not success_rename: show_message(rename_msg); return
                engine.app_state["selected_car"] = new_name
                dialog.open = False; page.update(); rebuild_ui()
            dialog = ft.AlertDialog(title=ft.Text("Редактировать имя"), content=ft.Column([edit_name_input], tight=True), actions=[ft.TextButton("Сохранить", on_click=save_name_change)])
            page.overlay.append(dialog); dialog.open = True; page.update()
            
        def delete_car_click(e):
            if len(current_db["cars"]) <= 1: return
            def confirm_delete(_):
                current_db["cars"].pop(selected_car)
                engine.save_data(current_db); engine.app_state["selected_car"] = list(current_db["cars"].keys())[0]
                dialog.open = False; page.update(); rebuild_ui()
            dialog = ft.AlertDialog(title=ft.Text("Удаление профиля"), content=ft.Text(f"Удалить '{selected_car}'?"), actions=[ft.TextButton("Удалить", on_click=confirm_delete, style=ft.ButtonStyle(color=ft.Colors.RED_600))])
            page.overlay.append(dialog); dialog.open = True; page.update()
            
        action_panel = ft.Column(
            spacing=5,
            horizontal_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Text("База и управление профилями:", size=12, weight=ft.FontWeight.W_500, color=ft.Colors.BLUE_GREY_700),
                ft.Row(
                    scroll=ft.ScrollMode.AUTO,
                    spacing=5,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.IconButton(ft.Icons.CLOUD_UPLOAD, tooltip="Экспорт базы в Telegram", on_click=lambda _: network.auto_export_file_to_telegram(page, show_message)),
                        ft.IconButton(
                            ft.Icons.CLOUD_DOWNLOAD, 
                            tooltip="Импорт базы данных", 
                            on_click=lambda _: [
                                network.auto_import_last_file(page, show_message)
                            ] if os.name != "nt" else [
                                run_local_telegram_sync(), 
                                page.data.update({"db_data": engine.load_data()}), 
                                refresh_ui(), 
                                show_message("✅ База данных успешно импортирована локально из Telegram Desktop!")
                            ]
                        ),
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
                ], spacing=12), padding=12
            )
        )
        
        if engine.app_state.get("view_mode") == "analytics":
            analytics_container = ft.Column(expand=False, scroll=ft.ScrollMode.AUTO)
            analytics_container.controls.append(header_card); analytics_container.controls.append(views.generate_analytics_view(page, car_profile))
            main_layout = analytics_container
        else:
            main_layout = views.build_maintenance_list(page, current_db, selected_car, car_profile, header_card, rebuild_ui, show_message)
        page.add(ft.SafeArea(content=ft.Column(expand=False, controls=[ft.Container(content=car_buttons_row, padding=ft.Padding(5, 5, 0, 15)), main_layout])))
        page.update()
        
    rebuild_ui()

if __name__ == "__main__":
    ft.run(main)

