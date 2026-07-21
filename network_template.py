import os
import engine
# Берем точное имя файла базы данных, которое использует само приложение
DB_REAL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), getattr(engine, "DB_FILE", "database.txt"))
LAST_SENT_ALERTS = {}
import flet as ft
import json
import io
import time
import traceback
import requests
import urllib3
from concurrent.futures import ThreadPoolExecutor
import engine

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
network_executor = ThreadPoolExecutor(max_workers=2)

BOT_TOKEN = "СЮДА_GITHUB_ACTIONS_ПОДСТАВИТ_ТОКЕН"

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
                import engine
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
                page.update() # Безопасный синхронный апдейт вместо run_task

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
                        db_data_ref.update(engine.load_data())
                        
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
            import engine
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
    """Импорт базы из кэша сессии или из входящих файлов чата."""
    import requests
    import engine
    
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

    target_file_id = engine.app_state.get("last_file_id")

    if not target_file_id:
        try:
            url_updates = f"https://{TELEGRAM_IP}/bot{BOT_TOKEN}/getUpdates?offset=-1&limit=10"
            response = requests.get(url_updates, headers=CUSTOM_HEADERS, verify=False, timeout=10)
            if response.status_code == 200:
                res_data = response.json()
                for result in reversed(res_data.get("result", [])):
                    message = result.get("message", result.get("edited_message", {}))
                    document = message.get("document", {})
                    if document and str(document.get("file_name")) == "Carjournal_database.json":
                        target_file_id = document.get("file_id")
                        break
        except Exception:
            pass

    if not target_file_id:
        show_alert("Файл бэкапа не найден в кэше сессии. Перешлите файл Carjournal_database.json в чат бота вручную и повторите импорт.")
        return

    try:
        url_file_info = f"https://{TELEGRAM_IP}/bot{BOT_TOKEN}/getFile?file_id={target_file_id}"
        file_info_resp = requests.get(url_file_info, headers=CUSTOM_HEADERS, verify=False, timeout=10).json()
        
        if file_info_resp.get("ok"):
            file_path = file_info_resp["result"]["file_path"]
            url_download = f"https://{TELEGRAM_IP}/file/bot{BOT_TOKEN}/{file_path}"
            db_resp = requests.get(url_download, headers=CUSTOM_HEADERS, verify=False, timeout=10)
            
            if db_resp.status_code == 200:
                with open(DB_REAL_PATH, "w", encoding="utf-8") as f:
                    f.write(db_resp.text)
                show_alert("✅ База данных успешно импортирована!")
                import engine
                engine.load_data()
            else:
                show_alert("Не удалось загрузить файл бэкапа.")
        else:
            show_alert("Срок действия ссылки на файл в Telegram истек.")
    except Exception as ex:
        show_alert(f"Ошибка импорта: {str(ex)}")
