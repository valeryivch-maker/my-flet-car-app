import json
import os
import requests
import urllib3
from datetime import datetime

# Отключаем SSL-валидацию, как в рабочем network.py
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BOT_TOKEN = "8859678783:AAFKgP9dc7hk5YsRkh02kfcIoT4M_liFVbs"
TELEGRAM_IP = "149.154.167.220"
CHAT_ID = 1036911003

# Строгие отлаженные заголовки из вашего сетевого контура
CUSTOM_HEADERS = {
    "Host": "api.telegram.org",
    "User-Agent": "Flet-CarJournal-Client/1.0"
}

def get_latest_database_blueprint():
    """Полная копия вашей отлаженной логики поиска и скачивания базы из network.py"""
    target_file_id = None
    try:
        # Берем limit=10, как на Page 14 вашего network.py
        url_updates = f"https://{TELEGRAM_IP}/bot{BOT_TOKEN}/getUpdates?offset=-1&limit=10"
        response = requests.get(url_updates, headers=CUSTOM_HEADERS, proxies={"http": None, "https": None}, verify=False, timeout=10)
        
        if response.status_code == 200:
            res_data = response.json()
            # Сканируем историю с конца, обрабатывая message и edited_message
            for result in reversed(res_data.get("result", [])):
                message = result.get("message", result.get("edited_message", {}))
                document = message.get("document", {})
                # Строгое соответствие имени файла из вашей системы
                if document and str(document.get("file_name")) == "Carjournal_database.json":
                    target_file_id = document.get("file_id")
                    break
    except Exception as e:
        print(f"[CRON DEBUG] Ошибка запроса обновлений: {e}")
        return None

    if not target_file_id:
        print("[CRON DEBUG] Файл бэкапа не найден в истории чата.")
        return None

    try:
        # Точное воссоздание логики getFile и url_download со страниц 14-15
        url_file_info = f"https://{TELEGRAM_IP}/bot{BOT_TOKEN}/getFile?file_id={target_file_id}"
        file_info_resp = requests.get(url_file_info, headers=CUSTOM_HEADERS, verify=False, timeout=10).json()
        
        if file_info_resp.get("ok"):
            file_path = file_info_resp["result"]["file_path"]
            url_download = f"https://{TELEGRAM_IP}/file/bot{BOT_TOKEN}/{file_path}"
            
            db_resp = requests.get(url_download, headers=CUSTOM_HEADERS, verify=False, timeout=10)
            if db_resp.status_code == 200:
                return json.loads(db_resp.text)
    except Exception as e:
        print(f"[CRON DEBUG] Ошибка скачивания/парсинга файла: {e}")
        
    return None

def send_telegram_cron_alert(text_msg):
    """Точная копия метода send_telegram_alert_message со Страницы 13"""
    url = f"https://{TELEGRAM_IP}/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text_msg,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, data=payload, headers=CUSTOM_HEADERS, proxies={"http": None, "https": None}, timeout=10, verify=False)
        print("[CRON] Сообщение успешно отправлено шлюзом!")
    except Exception as e:
        print(f"[CRON DEBUG] Сбой отправки sendMessage: {e}")

def main():
    print("[CRON] Старт автономной проверки по отлаженной схеме...")
    db_data = get_latest_database_blueprint()
    
    if not db_data or "cars" not in db_data:
        print("[CRON] Не удалось получить валидную структуру базы данных.")
        return

    for car_name, car_profile in db_data["cars"].items():
        odo_hist = car_profile.get("odometer_history", [])
        if not odo_hist:
            continue
            
        try:
            # Парсинг и сортировка дат
            # Используем встроенный лямбда-парсинг во избежание импорта engine
            sorted_hist = sorted(odo_hist, key=lambda x: datetime.strptime(x["date"], "%d.%m.%Y"))
            last_entry = sorted_hist[-1]
            last_date = datetime.strptime(last_entry["date"], "%d.%m.%Y")
            days_passed = (datetime.now() - last_date).days
            
            print(f"[CRON] Машина: {car_name} | Прошло дней: {days_passed}")
            
            # ВРЕМЕННО: ставлю >= 0 для мгновенного теста связи!
            if days_passed >= 0:
                msg = (
                    f"📅 <b>Автономное напоминание!</b>\n"
                    f"Для автомобиля <b>{car_name}</b> пробег не обновлялся уже <b>{days_passed} дн.</b>\n"
                    f"Последние данные: {last_entry['value']} км ({last_entry['date']}).\n\n"
                    f"Пожалуйста, внесите актуальный километраж в приложение!"
                )
                send_telegram_cron_alert(msg)
        except Exception as ex:
            print(f"[CRON] Ошибка обработки данных автомобиля {car_name}: {ex}")

if __name__ == "__main__":
    main()
