import json
import os
import requests
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BOT_TOKEN = os.environ.get("SECRET_BOT_TOKEN", "8859678783:AAFDa97SuNwBorffMeG59Ad9zYb7u7VqnPw")
TARGET_FILE_ID = os.environ.get("SECRET_FILE_ID", "")

TELEGRAM_IP = "149.154.167.220"
CHAT_ID = 1036911003

CUSTOM_HEADERS = {
    "Host": "api.telegram.org",
    "User-Agent": "Flet-CarJournal-Client/1.0"
}

def get_database_directly():
    if not TARGET_FILE_ID:
        print("[CRON] Ошибка: SECRET_FILE_ID не передан из настроек GitHub!")
        return None
    try:
        url_file_info = f"https://{TELEGRAM_IP}/bot{BOT_TOKEN}/getFile?file_id={TARGET_FILE_ID}"
        file_info_resp = requests.get(url_file_info, headers=CUSTOM_HEADERS, verify=False, timeout=10).json()
        
        if file_info_resp.get("ok"):
            file_path = file_info_resp["result"]["file_path"]
            url_download = f"https://{TELEGRAM_IP}/file/bot{BOT_TOKEN}/{file_path}"
            db_resp = requests.get(url_download, headers=CUSTOM_HEADERS, verify=False, timeout=10)
            if db_resp.status_code == 200:
                return json.loads(db_resp.text)
    except Exception as e:
        print(f"[CRON] Ошибка прямого скачивания файла: {e}")
    return None

def send_telegram_cron_alert(text_msg):
    url = f"https://{TELEGRAM_IP}/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text_msg, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload, headers=CUSTOM_HEADERS, proxies={"http": None, "https": None}, timeout=10, verify=False)
        print("[CRON] Уведомление успешно доставлено в Telegram!")
    except Exception as e:
        print(f"[CRON] Сбой sendMessage: {e}")

def main():
    print("[CRON] Запуск боевого автономного сканирования по ID...")
    db_data = get_database_directly()
    
    if not db_data or "cars" not in db_data:
        print("[CRON] Завершено: Не удалось прочитать базу данных.")
        return

    for car_name, car_profile in db_data["cars"].items():
        odo_hist = car_profile.get("odometer_history", [])
        if not odo_hist: continue
        try:
            sorted_hist = sorted(odo_hist, key=lambda x: datetime.strptime(x["date"], "%d.%m.%Y"))
            last_entry = sorted_hist[-1]
            last_date = datetime.strptime(last_entry["date"], "%d.%m.%Y")
            days_passed = (datetime.now() - last_date).days
            print(f"[CRON] Машина: {car_name} | Прошло дней с обновления: {days_passed}")
            
            # БОЕВОЙ РЕЖИМ: Бот напишет сам, только если вы не вводили данные 7 или более дней
            if days_passed >= 7:
                msg = (
                    f"📅 <b>Автономное напоминание!</b>\n"
                    f"Для автомобиля <b>{car_name}</b> пробег не обновлялся уже <b>{days_passed} дн.</b>\n"
                    f"Последние данные: {last_entry['value']} км ({last_entry['date']}).\n\n"
                    f"Пожалуйста, запустите приложение и обновите текущий километраж!"
                )
                send_telegram_cron_alert(msg)
            else:
                print(f"[CRON] Напоминание не требуется. С момента последнего ввода прошло всего {days_passed} дн.")
        except Exception as ex:
            print(f"[CRON] Ошибка обработки авто {car_name}: {ex}")

if __name__ == "__main__":
    main()
