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

BOT_TOKEN = "8859678783:AAFKgP9dc7hk5YsRkh02kfcIoT4M_liFVbs"

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
