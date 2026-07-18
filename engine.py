# -*- coding: utf-8 -*-
import sys
import os
import json
from datetime import datetime, timedelta

if 'ANDROID_BOOTLOGO' in os.environ or os.name != 'nt':
    base_data_dir = os.environ.get('HOME', os.path.expanduser('~'))
    DB_FILE = os.path.join(base_data_dir, 'database.txt')
    CONFIG_FILE = os.path.join(base_data_dir, 'app_config.txt')
    os.makedirs(base_data_dir, exist_ok=True)
else:
    DB_FILE = "database.txt"
    CONFIG_FILE = "app_config.txt"
DB_PATH = DB_FILE

def save_config_to_disk(file_id):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_file_id": file_id}, f, ensure_ascii=False, indent=4)
    except: pass

def load_config_from_disk():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config_data = json.load(f)
                if isinstance(config_data, dict):
                    return config_data.get("last_file_id", "")
    except: pass
    return ""

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
            if not val:
                val = load_config_from_disk()
                if val: super().__setitem__("last_file_id", val)
            return val if val else ""
        return super().get(key, default)

saved_id = load_config_from_disk()

app_state = SmartAppState({
    "active_tab": 0,
    "newly_added_cars": [],
    "view_mode": "list",
    "selected_car": "Мой Автомобиль",
    "last_file_id": saved_id if saved_id else ""
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
        "history": [], "fuel_history": [], "repair_history": []
    }

def recalculate_auto_daily_mileage(car_profile):
    history = car_profile.get("odometer_history", [])
    if len(history) < 2: return int(car_profile.get("daily_mileage", 45))
    try:
        sorted_hist = sorted(history, key=lambda x: datetime.strptime(x["date"], "%d.%m.%Y"))
        rates = []
        for i in range(1, len(sorted_hist)):
            d1 = datetime.strptime(sorted_hist[i-1]["date"], "%d.%m.%Y")
            d2 = datetime.strptime(sorted_hist[i]["date"], "%d.%m.%Y")
            days = (d2 - d1).days
            km = int(sorted_hist[i]["value"]) - int(sorted_hist[i-1]["value"])
            if days == 0 and km > 0: days = 1
            if days > 0 and km > 0: rates.append(km / days)
        if rates:
            recent = rates[-4:]
            calc = int(sum(recent) / len(recent))
            if calc > 1000: return int(car_profile.get("daily_mileage", 45))
            return max(1, calc)
    except: pass
    return int(car_profile.get("daily_mileage", 45))

def calculate_task_status(task_info, current_odometer, daily_mileage):
    last_service = task_info.get("last_service", current_odometer)
    interval = task_info.get("interval", 10000)
    rem_km = (last_service + interval) - current_odometer
    rem_days = int(rem_km / daily_mileage) if daily_mileage > 0 else 9999
    return {"rem_km": rem_km, "rem_days": rem_days, "is_overdue": rem_km <= 0}

def get_maintenance_predictions(car_profile):
    current_odometer = car_profile.get("odometer", {}).get("value", 0)
    daily_mileage = car_profile.get("daily_mileage", 45)
    maintenance_data = car_profile.get("maintenance_data", {})
    return {k: calculate_task_status(v, current_odometer, daily_mileage) for k, v in maintenance_data.items()}

def load_data():
    if not os.path.exists(DB_FILE):
        init_data = {"cars": {"Мой Автомобиль": get_default_car_data()}}
        save_data(init_data)
        return init_data
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "cars" not in data or not data["cars"]:
            data = {"cars": {"Мой Автомобиль": get_default_car_data()}}
        for car_name, car_profile in data["cars"].items():
            for k in ["odometer_history", "history", "fuel_history", "repair_history"]:
                if k not in car_profile: car_profile[k] = []
            if "odometer" not in car_profile: car_profile["odometer"] = {"value": 125000, "date": datetime.now().strftime("%d.%m.%Y")}
            car_profile["daily_mileage"] = recalculate_auto_daily_mileage(car_profile)
            car_profile["predictions"] = get_maintenance_predictions(car_profile)
        if "network" in sys.modules or "network" in globals():
            try:
                import network
                if hasattr(network, "check_and_send_alerts"): network.check_and_send_alerts(car_profile, car_name=car_name)
            except: pass
        return data
    except: return {"cars": {"Мой Автомобиль": get_default_car_data()}}

def save_data(data):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except: pass

def rename_car_profile(data, old_name, new_name):
    if "cars" not in data or old_name not in data["cars"]: return False, "Автомобиль не найден."
    if new_name in data["cars"]: return False, "Такое имя уже есть."
    if not new_name.strip(): return False, "Имя не может быть пустым."
    data["cars"][new_name] = data["cars"].pop(old_name)
    save_data(data)
    return True, "Успешно переименован."

def add_fuel_record(car_profile, f_type, liters, total_cost, odometer, date_str, comment=""):
    if "fuel_history" not in car_profile: car_profile["fuel_history"] = []
    liters, cost, odometer = float(liters), float(total_cost), int(odometer)
    price = round(cost / liters, 2) if liters > 0 else 0.0
    consumption = 0.0
    logs = sorted([l for l in car_profile["fuel_history"] if l.get("type") == f_type], key=lambda x: x.get("odometer", 0))
    if logs and odometer - logs[-1].get("odometer", 0) > 0:
        consumption = round((liters / (odometer - logs[-1]["odometer"])) * 100, 2)
    rec = {"date": date_str, "type": f_type, "liters": liters, "price": price, "cost": cost, "odometer": odometer, "consumption": consumption, "comment": comment}
    car_profile["fuel_history"].append(rec)
    return rec

def calculate_fuel_stats(car_profile, days=30):
    cutoff = datetime.now() - timedelta(days=days)
    f_spent = sum([float(r.get("cost", 0)) for r in car_profile.get("fuel_history", []) if datetime.strptime(r.get("date", ""), "%d.%m.%Y") >= cutoff])
    m_spent = sum([float(r.get("cost", 0)) for r in car_profile.get("history", []) if datetime.strptime(r.get("date", ""), "%d.%m.%Y") >= cutoff])
    return {"fuel_spent": round(f_spent, 2), "maintenance_spent": round(m_spent, 2), "total_spent": round(f_spent + m_spent, 2)}

def calculate_cost_per_km_brsm(car_profile):
    logs = car_profile.get("fuel_history", [])
    if not logs: return 0.0
    g = sorted([l for l in logs if l.get("type") == "Газ"], key=lambda x: x.get("odometer", 0))
    p = sorted([l for l in logs if l.get("type") == "Бензин"], key=lambda x: x.get("odometer", 0))
    if g and g[-1].get("consumption", 0) > 0: return round((g[-1]["consumption"] / 100.0) * g[-1]["price"], 2)
    if p and p[-1].get("consumption", 0) > 0: return round((p[-1]["consumption"] / 100.0) * p[-1]["price"], 2)
    return 0.0

def calculate_gbo_economy_points(car_profile):
    logs = car_profile.get("fuel_history", [])
    g = sorted([l for l in logs if l.get("type") == "Газ"], key=lambda x: x.get("odometer", 0))
    p = sorted([l for l in logs if l.get("type") == "Бензин"], key=lambda x: x.get("odometer", 0))
    if not g: return []
    p_price = p[-1]["price"] if p else 54.0
    p_cons = sum([l["consumption"] for l in p if l["consumption"] > 0]) / len([l for l in p if l["consumption"] > 0]) if [l for l in p if l["consumption"] > 0] else 8.5
    pts, acc_g, s_odo = [], 0.0, int(g[0].get("odometer", 0))
    for l in g:
        dk = int(l["odometer"]) - s_odo
        acc_g += float(l["cost"])
        acc_alt = (dk / 100.0) * p_cons * p_price if dk > 0 else acc_g
        pts.append({"km": dk, "economy": round(acc_alt - acc_g, 2), "gas_cost": round(acc_g, 2)})
    return pts
