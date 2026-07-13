# smart_cloud_sync.py
import requests
import json
import os

def fetch_latest_telegram_db():
    print("[СТАРТ] Сканирование чата нового бота на предмет свежего экспорта...")
    
    # Константы строго по техпаспорту (Страница 2)
    TOKEN = "8859678783:AAFDa97SuNwBorffMeG59Ad9zYb7u7VqnPw"
    TELEGRAM_IP = "149.154.167.220"
    
    headers = {"Host": "api.telegram.org"}
    
    # Шаг 1: Запрашиваем историю обновлений чата (getUpdates)
    url_updates = f"http://{TELEGRAM_IP}/bot{TOKEN}/getUpdates?limit=50&allowed_updates=[\"message\"]"
    
    try:
        response = requests.get(url_updates, headers=headers, verify=False, proxies={"http": None, "https": None}, timeout=10)
        res_json = response.json()
        
        if not res_json.get("ok"):
            print(f"[ОШИБКА API] Ошибка получения истории: {res_json}")
            return
            
        updates = res_json.get("result", [])
        if not updates:
            print("[ИНФО] История чата бота пуста. Экспортируйте базу с телефона ещё раз прямо сейчас!")
            return
            
        # Ищем самый последний документ с именем database.txt
        target_file_id = None
        for update in reversed(updates):
            message = update.get("message", {})
            document = message.get("document", {})
            
            if document and (document.get("file_name") == "database.txt" or "database" in document.get("file_name", "")):
                target_file_id = document.get("file_id")
                print(f"[НАЙДЕНО] Обнаружен свежий файл базы данных от {message.get('date')}!")
                break
                
        if not target_file_id:
            print("[ВНИМАНИЕ] В истории чата нет файлов документов. Пожалуйста, зайдите в приложение на телефоне и нажмите кнопку 'ЭКСПОРТ' (Облако со стрелкой вверх), затем запустите этот скрипт снова.")
            return
            
        # Шаг 2: Получаем актуальный временный путь файла по найденному file_id
        print(f"[СЕТЬ] Запрос пути для file_id: {target_file_id[:15]}...")
        url_file = f"http://{TELEGRAM_IP}/bot{TOKEN}/getFile?file_id={target_file_id}"
        file_path_res = requests.get(url_file, headers=headers, verify=False, proxies={"http": None, "https": None}, timeout=10).json()
        
        file_path = file_path_res.get("result", {}).get("file_path")
        if not file_path:
            print("[ОШИБКА] Не удалось сгенерировать путь скачивания:", file_path_res)
            return
            
        # Шаг 3: Скачиваем физический JSON
        print("[СЕТЬ] Загрузка физического JSON из облака...")
        url_download = f"http://{TELEGRAM_IP}/file/bot{TOKEN}/{file_path}"
        db_content = requests.get(url_download, headers=headers, verify=False, proxies={"http": None, "https": None}, timeout=15).json()
        
        # Шаг 4: Пишем на диск ноутбука
        with open("database.txt", "w", encoding="utf-8") as f:
            json.dump(db_content, f, ensure_ascii=False, indent=4)
            
        print("[СИНХРОНИЗАЦИЯ УСПЕШНА] Ноутбук полностью перенял актуальную историю с телефона!")
        
    except Exception as e:
        print(f"[КРИТИЧЕСКАЯ ОШИБКА КОНТУРА]: {e}")

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    fetch_latest_telegram_db()
    input("\nНажмите Enter для завершения...")
