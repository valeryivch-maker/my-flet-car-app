import json
import os
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BOT_TOKEN = os.environ.get("SECRET_BOT_TOKEN", "8859678783:AAFDa97SuNwBorffMeG59Ad9zYb7u7VqnPw")
TELEGRAM_IP = "149.154.167.220"

CUSTOM_HEADERS = {
    "Host": "api.telegram.org",
    "User-Agent": "Flet-CarJournal-Client/1.0"
}

def main():
    print("[DIAGNOSTIC] Запуск поиска file_id базы данных...")
    try:
        url_updates = f"https://{TELEGRAM_IP}/bot{BOT_TOKEN}/getUpdates?offset=-1&limit=10"
        response = requests.get(url_updates, headers=CUSTOM_HEADERS, proxies={"http": None, "https": None}, verify=False, timeout=15)
        
        if response.status_code == 200:
            res_data = response.json()
            results = res_data.get("result", [])
            print(f"[DIAGNOSTIC] Найдено событий в очереди: {len(results)}")
            
            for index, result in enumerate(reversed(results)):
                message = result.get("message", result.get("edited_message", {}))
                document = message.get("document", {})
                
                if document:
                    print(f"\n--- НАЙДЕН ФАЙЛ №{index+1} ---")
                    print(f"Имя файла: {document.get('file_name')}")
                    print(f"РАБОЧИЙ FILE_ID: {document.get('file_id')}")
                    print("-" * 30)
            
            if not any(r.get("message", r.get("edited_message", {})).get("document") for r in results):
                print("[DIAGNOSTIC] Документы в очереди не найдены. Очередь пуста или очищена.")
        else:
            print(f"[DIAGNOSTIC] Ошибка шлюза Telegram: Код {response.status_code}")
    except Exception as e:
        print(f"[DIAGNOSTIC] Сбой выполнения: {e}")

if __name__ == "__main__":
    main()
