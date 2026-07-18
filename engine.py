import json
import os
from datetime import datetime, timedelta

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
            import network
            if network and hasattr(network, 'check_and_send_alerts'): network.check_and_send_alerts(car_profile, car_name=car_name)
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
    from datetime import datetime, timedelta
    
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
