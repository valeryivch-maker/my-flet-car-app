import json
import requests
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BOT_TOKEN = "8859678783:AAFKgP9dc7hk5YsRkh02kfcIoT4M_liFVbs"
TELEGRAM_IP = "149.154.167.220"
CHAT_ID = 1036911003

HEADERS = {
    "Host": "api.telegram.org",
    "User-Agent": "GitHub-Actions-Cron-Watcher/1.0"
}

def get_latest_database():
    """Сканирует getUpdates чата и забирает самый свежий бэкап базы данных."""
    url = f"https://{TELEGRAM_IP}/bot{BOT_TOKEN}/getUpdates?offset=-1&limit=10"
    try:
        res = requests.get(url, headers=HEADERS, verify=False, timeout=15).json()
        if not res.get("ok"): return None
        
        target_file_id = None
        for result in reversed(res.get("result", [])):
            message = result.get("message", result.get("edited_message", {}))
            document = message.get("document", {})
            if document and "json" in str(document.get("file_name", "")).lower():
                target_file_id = document.get("file_id")
                break
                
        if not target_file_id: return None
        
        # Получаем file_path и скачиваем файл
        url_file = f"https://{TELEGRAM_IP}/bot{BOT_TOKEN}/getFile?file_id={target_file_id}"
        file_info = requests.get(url_file, headers=HEADERS, verify=False, timeout=15).json()
        if not file_info.get("ok"): return None
        
        file_path = file_info["result"]["file_path"]
        url_download = f"https://{TELEGRAM_IP}/file/bot{BOT_TOKEN}/{file_path}"
        db_res = requests.get(url_download, headers=HEADERS, verify=False, timeout=15)
        
        return db_res.json() if db_res.status_code == 200 else None
    except Exception as e:
        print(f"[ERROR] Не удалось загрузить бэкап: {e}")
        return None

def send_message(text):
    """Отправляет инициативное сообщение в ваш чат."""
    url = f"https://{TELEGRAM_IP}/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload, headers=HEADERS, verify=False, timeout=10)
    except Exception as e:
        print(f"[ERROR] Ошибка отправки сообщения: {e}")

def main():
    print("[CRON] Запуск автономной проверки дат пробега...")
    db_data = get_latest_database()
    
    if not db_data or "cars" not in db_data:
        print("[CRON] Свежая база данных в чате бота не обнаружена.")
        return

    for car_name, car_profile in db_data["cars"].items():
        odo_hist = car_profile.get("odometer_history", [])
        if not odo_hist:
            continue
            
        try:
            # Сортируем историю и берем последнюю запись
            last_entry = sorted(odo_hist, key=lambda x: datetime.strptime(x["date"], "%d.%m.%Y"))[-1]
            last_date = datetime.strptime(last_entry["date"], "%d.%m.%Y")
            days_passed = (datetime.now() - last_date).days
            
            print(f"[CRON] Автомобиль: {car_name}. Прошло дней: {days_passed}")
            
            # Если пробег не обновлялся 7 или более дней — отправляем пуш
            if days_passed >= 7:
                msg = (
                    f"📅 <b>Автономное напоминание!</b>\n"
                    f"Для автомобиля <b>{car_name}</b> пробег не обновлялся уже <b>{days_passed} дн.</b>\n"
                    f"Последние данные: {last_entry['value']} км от {last_entry['date']}.\n\n"
                    f"Пожалуйста, запустите приложение и внесите актуальный километраж!"
                )
                send_message(msg)
                print(f"[CRON] Напоминание для {car_name} успешно улетело в Telegram.")
        except Exception as ex:
            print(f"[CRON] Ошибка обработки авто {car_name}: {ex}")

if __name__ == "__main__":
    main()
