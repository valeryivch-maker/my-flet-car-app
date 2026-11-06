import os
import json
from datetime import datetime, timedelta

# === АДАПТАЦИЯ ПУТЕЙ ДЛЯ ANDROID ===
def get_db_path():
    # Пытаемся взять путь из переменных окружения Flet (для Android)
    storage_dir = os.environ.get("FLET_APP_STORAGE_DATA")
    if storage_dir:
        return os.path.join(storage_dir, "Carjournal_database.json")
    # Для десктопа берем текущую директорию
    return os.path.join(os.getcwd(), "Carjournal_database.json")

def get_config_path():
    storage_dir = os.environ.get("FLET_APP_STORAGE_DATA")
    if storage_dir:
        return os.path.join(storage_dir, "app_config.txt")
    return os.path.join(os.getcwd(), "app_config.txt")

DB_FILE = get_db_path()
CONFIG_FILE = get_config_path()

def save_config_to_disk(file_id):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_file_id": file_id}, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"[DEBUG CONFIG] Ошибка записи конфига: {e}")

def load_config_from_disk():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config_data = json.load(f)
                if isinstance(config_data, dict):
                    return config_data.get("last_file_id")
        except Exception as e:
            print(f"[DEBUG CONFIG] Ошибка чтения конфига: {e}")
    return None

class SmartAppState(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
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

saved_id = load_config_from_disk()
app_state = SmartAppState({
    "active_tab": 0,
    "newly_added_cars": [],
    "view_mode": "list",
    "selected_car": "Chevrolet lacetti",
    "last_file_id": saved_id
})

def get_default_car_data():
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
    try:
        return datetime.strptime(item["date"], "%d.%m.%Y")
    except:
        return datetime.min

def recalculate_auto_daily_mileage(car_profile):
    history = car_profile.get("odometer_history", [])
    if len(history) < 2:
        try:
            return int(car_profile.get("daily_mileage", 45))
        except Exception:
            return 45

    try:
        sorted_hist = sorted(
            history, 
            key=lambda x: datetime.strptime(x.get("date", "01.01.2000"), "%d.%m.%Y") if x.get("date") else datetime.min
        )
        rates = []
        for i in range(1, len(sorted_hist)):
            prev_entry = sorted_hist[i-1]
            curr_entry = sorted_hist[i]
            
            if not prev_entry.get("date") or not curr_entry.get("date"):
                continue
                
            d1 = datetime.strptime(prev_entry["date"], "%d.%m.%Y")
            d2 = datetime.strptime(curr_entry["date"], "%d.%m.%Y")
            days = (d2 - d1).days
            km = int(curr_entry["value"]) - int(prev_entry["value"])
            
            if days == 0 and km > 0:
                days = 1
                
            if days > 0 and km > 0:
                rates.append(km / days)
                
        if rates:
            recent_rates = rates[-4:]
            calculated_rate = int(sum(recent_rates) / len(recent_rates))
            if calculated_rate > 1000:
                return int(car_profile.get("daily_mileage", 45))
            return max(1, calculated_rate)
    except Exception:
        pass
    return int(car_profile.get("daily_mileage", 45))

def calculate_task_status(task_info, current_odometer, daily_mileage):
    last_service = task_info.get("last_service", current_odometer)
    interval = task_info.get("interval", 10000)
    rem_km = (last_service + interval) - current_odometer
    if daily_mileage > 0:
        rem_days = int(rem_km / daily_mileage)
    else:
        rem_days = 9999
    return {"rem_km": rem_km, "rem_days": rem_days, "is_overdue": rem_km <= 0}

def get_maintenance_predictions(car_profile):
    current_odometer = car_profile.get("odometer", {}).get("value", 0)
    daily_mileage = car_profile.get("daily_mileage", 45)
    maintenance_data = car_profile.get("maintenance_data", {})
    predictions = {}
    for task_name, task_info in maintenance_data.items():
        predictions[task_name] = calculate_task_status(task_info, current_odometer, daily_mileage)
    return predictions

def load_data():
    if not os.path.exists(DB_FILE):
        try:
            initial_data = {"cars": {"Chevrolet lacetti": get_default_car_data()}, "shops": [], "guides": []}
            initial_data["cars"]["Chevrolet lacetti"]["predictions"] = get_maintenance_predictions(
                initial_data["cars"]["Chevrolet lacetti"]
            )
            save_data(initial_data)
            return initial_data
        except Exception:
            return {"cars": {"Chevrolet lacetti": {}}, "shops": [], "guides": []}
            
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        if not data or "cars" not in data or not data["cars"]:
            data = {"cars": {"Chevrolet lacetti": get_default_car_data()}, "shops": [], "guides": []}
            
        if "shops" not in data:
            data["shops"] = []
        if "guides" not in data:
            data["guides"] = []

        for car_name, car_profile in list(data["cars"].items()):
            try:
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
                    
                try:
                    car_profile["daily_mileage"] = recalculate_auto_daily_mileage(car_profile)
                except Exception:
                    car_profile["daily_mileage"] = 45
                    
                for task_name, task_info in car_profile.get("maintenance_data", {}).items():
                    if "last_service" not in task_info:
                        task_info["last_service"] = car_profile["odometer"]["value"]
                    if "interval" not in task_info:
                        task_info["interval"] = 10000
                    if "date" not in task_info:
                        task_info["date"] = datetime.now().strftime("%d.%m.%Y")
                        
                car_profile["predictions"] = get_maintenance_predictions(car_profile)
            except Exception:
                pass
        return data
    except Exception:
        return {"cars": {"Chevrolet lacetti": get_default_car_data()}, "shops": [], "guides": []}

def save_data(data):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Ошибка записи на диск: {e}")

def rename_car_profile(data, old_name, new_name):
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
    if "fuel_history" not in car_profile:
        car_profile["fuel_history"] = []
        
    liters = float(liters)
    cost = float(total_cost)
    odometer = int(odometer)
    
    price = round(cost / liters, 2) if liters > 0 else 0.0
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

def calculate_cost_per_km_brsm(car_profile):
    fuel_history = car_profile.get("fuel_history", [])
    if not fuel_history:
        return 0.0
        
    gas_logs = sorted([log for log in fuel_history if log.get("type") == "Газ"], key=lambda x: x.get("odometer", 0))
    petrol_logs = sorted([log for log in fuel_history if log.get("type") == "Бензин"], key=lambda x: x.get("odometer", 0))
    
    gas_cost_per_km = 0.0
    petrol_cost_per_km = 0.0
    
    if gas_logs:
        last_gas = gas_logs[-1]
        consumption = last_gas.get("consumption", 0.0)
        price = last_gas.get("price", 0.0)
        if consumption > 0:
            gas_cost_per_km = (consumption / 100.0) * price
            
    if petrol_logs:
        last_petrol = petrol_logs[-1]
        consumption = last_petrol.get("consumption", 0.0)
        price = last_petrol.get("price", 0.0)
        if consumption > 0:
            petrol_cost_per_km = (consumption / 100.0) * price
            
    if gas_cost_per_km > 0:
        return round(gas_cost_per_km, 2)
    return round(petrol_cost_per_km, 2)

def calculate_fuel_stats(car_profile, days=30):
    now = datetime.now()
    cutoff_date = now - timedelta(days=days)
    fuel_spent = 0.0
    maintenance_spent = 0.0
    
    fuel_history = car_profile.get("fuel_history", [])
    for record in fuel_history:
        try:
            r_date = datetime.strptime(record.get("date", ""), "%d.%m.%Y")
            if r_date >= cutoff_date:
                fuel_spent += float(record.get("cost", 0.0))
        except:
            continue
            
    history = car_profile.get("history", [])
    for record in history:
        try:
            r_date = datetime.strptime(record.get("date", ""), "%d.%m.%Y")
            if r_date >= cutoff_date:
                maintenance_spent += float(record.get("cost", 0.0))
        except:
            continue
            
    return {
        "fuel_spent": round(fuel_spent, 2),
        "maintenance_spent": round(maintenance_spent, 2),
        "total_spent": round(fuel_spent + maintenance_spent, 2)
    }

def calculate_gbo_economy_points(car_profile):
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

    total_gas_km = 0
    if len(gas_logs) >= 2:
        total_gas_km = gas_logs[-1]["odometer"] - gas_logs[0]["odometer"]

    total_gas_cost = sum([log["cost"] for log in gas_logs])

    recent_petrol_prices = [log["price"] for log in petrol_logs[-3:]]
    base_petrol_price = sum(recent_petrol_prices) / len(recent_petrol_prices) if recent_petrol_prices else 75.0
    
    valid_petrol_cons = [log["consumption"] for log in petrol_logs if log["consumption"] > 5.0]
    
    if valid_petrol_cons:
        base_petrol_consumption = sum(valid_petrol_cons) / len(valid_petrol_cons)
    else:
        valid_gas_cons = [log["consumption"] for log in gas_logs if log["consumption"] > 0]
        if valid_gas_cons:
            base_petrol_consumption = (sum(valid_gas_cons) / len(valid_gas_cons)) * 0.85
        else:
            base_petrol_consumption = 8.5 

    alt_petrol_liters = (total_gas_km / 100.0) * base_petrol_consumption
    alt_petrol_cost = alt_petrol_liters * base_petrol_price

    economy = alt_petrol_cost - total_gas_cost

    return [{
        "km": total_gas_km,
        "economy": round(economy, 2),
        "gas_cost": round(total_gas_cost, 2)
    }]

# =========================================================
# МОДУЛЬ ОТЧЕТОВ ДЛЯ TELEGRAM
# =========================================================

def generate_report_expenses(car_profile, car_name, days=None):
    now = datetime.now()
    fuel_cost = 0.0
    repair_cost = 0.0
    fuel_liters = 0.0
    
    for record in car_profile.get("fuel_history", []):
        try:
            r_date = datetime.strptime(record.get("date", ""), "%d.%m.%Y")
            if days is None or r_date >= (now - timedelta(days=days)):
                fuel_cost += float(record.get("cost", 0.0))
                fuel_liters += float(record.get("liters", 0.0))
        except:
            continue
            
    for record in car_profile.get("history", []):
        try:
            r_date = datetime.strptime(record.get("date", ""), "%d.%m.%Y")
            if days is None or r_date >= (now - timedelta(days=days)):
                repair_cost += float(record.get("cost", 0.0))
        except:
            continue
            
    for record in car_profile.get("repair_history", []):
        try:
            r_date = datetime.strptime(record.get("date", ""), "%d.%m.%Y")
            if days is None or r_date >= (now - timedelta(days=days)):
                repair_cost += float(record.get("cost", 0.0))
        except:
            continue

    total_cost = fuel_cost + repair_cost
    period_text = f"за последние {days} дней" if days else "за всё время"

    report = f"📊 <b>Финансовый отчет</b>\n"
    report += f"🚗 Автомобиль: <b>{car_name}</b>\n"
    report += f"📅 Период: <b>{period_text}</b>\n"
    report += f"━━━━━━━━━━━━━━━━━━━━\n"
    report += f"⛽ <b>Топливо:</b>\n"
    report += f"   Залито: <code>{round(fuel_liters, 2)} л</code>\n"
    report += f"   Потрачено: <b>{round(fuel_cost, 2)} грн</b>\n\n"
    report += f"🛠 <b>Ремонт и ТО:</b>\n"
    report += f"   Потрачено: <b>{round(repair_cost, 2)} грн</b>\n"
    report += f"━━━━━━━━━━━━━━━━━━━━\n"
    report += f"💰 <b>ИТОГО ЗАТРАТ: {round(total_cost, 2)} грн</b>\n"
    
    return report

def generate_report_maintenance(car_profile, car_name):
    current_km = car_profile.get("odometer", {}).get("value", 0)
    tasks = car_profile.get("maintenance_data", {})
    daily = car_profile.get("daily_mileage", 45)
    
    report = f"🛠 <b>Статус регламентов ТО</b>\n"
    report += f"🚗 Автомобиль: <b>{car_name}</b>\n"
    report += f"📍 Текущий пробег: <b>{current_km} км</b>\n"
    report += f"━━━━━━━━━━━━━━━━━━━━\n"
    
    if not tasks:
        report += "Нет активных регламентов.\n"
        return report

    overdue = []
    warning = []
    ok = []

    for t_name, t_data in tasks.items():
        remains = (t_data.get("last_service", 0) + t_data.get("interval", 0)) - current_km
        if remains <= 0:
            overdue.append(f"🔴 <b>{t_name}</b>: ПРОСРОЧЕНО на {-remains} км!")
        elif remains <= 500:
            warning.append(f"🟡 <b>{t_name}</b>: осталось {remains} км")
        else:
            f_str = (datetime.now() + timedelta(days=remains/daily)).strftime("%d.%m.%Y") if daily > 0 else "-"
            ok.append(f"🟢 <b>{t_name}</b>: {remains} км (до {f_str})")

    if overdue:
        report += "⚠️ <b>СРОЧНО ЗАМЕНИТЬ:</b>\n" + "\n".join(overdue) + "\n\n"
    if warning:
        report += "⏳ <b>СКОРО ЗАМЕНА:</b>\n" + "\n".join(warning) + "\n\n"
    if ok:
        report += "✅ <b>В НОРМЕ:</b>\n" + "\n".join(ok) + "\n"
        
    return report

def generate_report_full(car_profile, car_name):
    current_km = car_profile.get("odometer", {}).get("value", 0)
    odo_date = car_profile.get("odometer", {}).get("date", "-")
    
    exp_all = generate_report_expenses(car_profile, car_name, days=None)
    cost_per_km = calculate_cost_per_km_brsm(car_profile)
    gbo_points = calculate_gbo_economy_points(car_profile)
    gbo_econ = gbo_points[0]["economy"] if gbo_points else 0.0
    
    report = f"🚘 <b>Полный отчет по автомобилю</b>\n"
    report += f"Название: <b>{car_name}</b>\n"
    report += f"Пробег: <b>{current_km} км</b> (от {odo_date})\n"
    report += f"Стоимость 1 км: <b>{cost_per_km} грн</b>\n"
    report += f"━━━━━━━━━━━━━━━━━━━━\n"
    
    if gbo_econ > 0:
        report += f"🌿 <b>Экономия на ГБО:</b> +{gbo_econ} грн\n"
        report += f"━━━━━━━━━━━━━━━━━━━━\n"
        
    report += exp_all + "\n"
    return report

# =========================================================
# СПРАВОЧНИКИ (МАГАЗИНЫ И ИНСТРУКЦИИ)
# =========================================================

def generate_shops_report(data):
    shops = data.get("shops", [])
    if not shops:
        return "🏪 <b>Справочник магазинов пуст.</b>"
        
    report = f"🏪 <b>Мои магазины и артикулы</b>\n"
    report += f"━━━━━━━━━━━━━━━━━━━━\n"
    
    for shop in shops:
        report += f"🏬 <b>{shop.get('name')}</b>\n"
        if shop.get('phone'): report += f"📞 {shop.get('phone')}\n"
        if shop.get('address'): report += f"📍 {shop.get('address')}\n"
        if shop.get('parts'): report += f"🔧 Запчасти: <i>{shop.get('parts')}</i>\n"
        report += "\n"
        
    return report

def generate_guides_report(data):
    guides = data.get("guides", [])
    if not guides:
        return "📚 <b>Справочник технологий пуст.</b>"
        
    report = f"📚 <b>Мои технологии ремонта</b>\n"
    report += f"━━━━━━━━━━━━━━━━━━━━\n"
    
    for guide in guides:
        report += f"🔹 <b>{guide.get('title')}</b>\n"
        if guide.get('car_model'): report += f"🚗 Модель: <i>{guide.get('car_model')}</i>\n"
        report += f"{guide.get('text')}\n\n"
        
    return report