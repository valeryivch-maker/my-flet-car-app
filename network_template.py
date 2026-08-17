
import os
import engine
import asyncio
import flet as ft
import json
import io
import time
import traceback
import requests
import urllib3

# Глобальный хак SSL-контекста для обхода сетевой изоляции песочницы Android
try:
    import certifi
    os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
    os.environ["SSL_CERT_FILE"] = certifi.where()
    
    import ssl
    def create_default_context(purpose=ssl.Purpose.SERVER_AUTH, *, cafile=None, capath=None, cadata=None):
        return ssl.create_default_context(purpose=purpose, cafile=certifi.where(), capath=capath, cadata=cadata)
    ssl._create_default_https_context = create_default_context
    print("[SSL FIXED] Корневые сертификаты certifi успешно вшиты в рантайм Android.")
except Exception as ssl_err:
    print(f"[SSL WARNING] Не удалось переопределить контекст: {ssl_err}")

# Отключаем предупреждения о проверке SSL-сертификатов на уровне ядра библиотеки
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Берем точное имя файла базы данных, которое использует само приложение
DB_REAL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), getattr(engine, "DB_FILE", "database.txt"))
LAST_SENT_ALERTS = {}

BOT_TOKEN = "СЮДА_GITHUB_ACTIONS_ПОДСТАВИТ_ТОКЕН"
TELEGRAM_IP = "149.154.167.220"
BASE_URL = f"https://{TELEGRAM_IP}/bot{BOT_TOKEN}"
BASE_FILE_URL = f"https://{TELEGRAM_IP}/file/bot{BOT_TOKEN}"
URL_EXPORT = f"{BASE_URL}/sendDocument"
URL_UPDATES = f"{BASE_URL}/getUpdates"
URL_FILE_INFO = f"{BASE_URL}/getFile"

CUSTOM_HEADERS = {
    "Host": "api.telegram.org",
    "User-Agent": "Flet-CarJournal-Client/1.0"
}

def auto_import_last_file():
    """Синхронная чистая функция импорта, устойчивая к SSL-ограничениям мобильной песочницы."""
    target_file_id = engine.app_state.get("last_file_id")
    
    if not target_file_id:
        try:
            url_updates = f"{URL_UPDATES}?offset=-1&limit=10"
            response = requests.get(url_updates, headers=CUSTOM_HEADERS, verify=False, timeout=10)
            if response.status_code == 200:
                res_data = response.json()
                for result in reversed(res_data.get("result", [])):
                    message = result.get("message", result.get("edited_message", {}))
                    document = message.get("document", {})
                    filename = str(document.get("file_name", "")).lower()
                    # Регистронезависимая проверка имени файла бэкапа
                    if document and filename == "carjournal_database.json":
                        target_file_id = document.get("file_id")
                        break
        except Exception as e:
            print(f"[DEBUG NETWORK] Ошибка получения обновлений Telegram: {e}")
            pass
    
    if not target_file_id:
        return False
    
    try:
        url_file_info = f"{URL_FILE_INFO}?file_id={target_file_id}"
        file_info_resp = requests.get(url_file_info, headers=CUSTOM_HEADERS, verify=False, timeout=10).json()
        if file_info_resp.get("ok"):
            file_path = file_info_resp["result"]["file_path"]
            url_download = f"{BASE_FILE_URL}/{file_path}"
            db_resp = requests.get(url_download, headers=CUSTOM_HEADERS, verify=False, timeout=12)
            if db_resp.status_code == 200:
                with open(DB_REAL_PATH, "w", encoding="utf-8") as f:
                    f.write(db_resp.text)
                engine.load_data()
                return True
    except Exception as e:
        print(f"[DEBUG NETWORK] Ошибка скачивания файла базы данных: {e}")
        pass
    return False

def show_custom_file_manager_dialog(page: ft.Page, mode: str, db_data_ref: dict, show_message_callback):
    if mode == "export":
        def async_export_worker():
            try:
                print("\n[DEBUG] Воркер экспорта запущен!")
                current_db_data = engine.load_data()
                if not current_db_data or "cars" not in current_db_data:
                    current_db_data = {"cars": {}, "history": []}
                
                json_text = json.dumps(current_db_data, ensure_ascii=False, indent=4)
                
                file_stream = io.BytesIO(json_text.encode("utf-8"))
                file_stream.name = "Carjournal_database.json"
                
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
                    page.run_task(lambda: show_message_callback("Бэкап успешно отправлен в Telegram!"))
                else:
                    page.run_task(lambda: show_message_callback(f"Ошибка облака: Код {response.status_code}"))
            except Exception as ex:
                page.run_task(lambda: show_message_callback(f"Сбой сети: {str(ex)}"))
        
        import threading
        threading.Thread(target=async_export_worker, daemon=True).start()

    elif mode == "import":
        progress_ring = ft.ProgressRing(width=30, height=30, stroke_width=3)
        status_text = ft.Text("Поиск последнего бэкапа in Telegram...", size=14)
        
        def close_dialog(e):
            dialog.open = False
            page.update()
        
        def async_import_worker():
            def safe_update_ui(text, close_win=False):
                status_text.value = text
                if close_win:
                    dialog.open = False
                page.update()

            try:
                print("\n[DEBUG] Изолированный воркер импорта запущен!")
                
                if os.name == 'nt':
                    safe_update_ui("Сканирование локальных загрузок Telegram на ПК...")
                    import main
                    success = main.run_local_telegram_sync()
                else:
                    safe_update_ui("Подключение к Telegram и скачивание бэкапа...")
                    success = auto_import_last_file()
                
                if success:
                    db_data_ref.clear()
                    db_data_ref.update(engine.load_data())
                    
                    # Финальное 12-пробельное выравнивание для сборщика CI/CD
                    async def finalize_success():
                        dialog.open = False
                        status_text.value = "Синхронизация успешна!"
                        page.update()
                        await asyncio.sleep(0.35)
                        if page.data and "refresh_ui" in page.data:
                            page.data["refresh_ui"]()
                        show_message_callback("База успешно восстановлена!")

                    page.run_task(finalize_success)
                else:
                    safe_update_ui("Ошибка: Свежий бэкап не найден.")
            except Exception as ex:
                print("[КРИТИЧЕСКИЙ СБОЙ В ПОТОКЕ ИМПОРТА]")
                safe_update_ui(f"Ошибка рантайма: {str(ex)}")
        
        confirm_btn = ft.FilledButton(
            "Начать импорт",
            style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.BLUE)
        )
        
        def on_confirm_click(e):
            confirm_btn.visible = False
            action_container.content = progress_ring
            page.update()
            
            import threading
            threading.Thread(target=async_import_worker, daemon=True).start()

        confirm_btn.on_click = on_confirm_click
        
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
    global LAST_SENT_ALERTS
    predictions = car_profile.get("predictions", {})
    alerts_to_send = []
    
    if not car_name:
        car_name = engine.app_state.get("selected_car", "Мой Автомобиль")
    
    for task_name, pred in predictions.items():
        rem_km = pred.get("rem_km", 9999)
        if rem_km <= 500:
            status = f"<b>ПРОСРОЧЕНО</b> на {-rem_km} км!" if rem_km < 0 else f"осталось всего {rem_km} км."
            alerts_to_send.append(f" <b>{task_name}</b>: {status}")
    
    if alerts_to_send:
        full_message_body = "\n".join(alerts_to_send)
        if LAST_SENT_ALERTS.get(car_name) == full_message_body:
            return
        
        LAST_SENT_ALERTS[car_name] = full_message_body
        msg_header = f" <b>Внимание! Критический износ ТО</b>\nАвтомобиль: <b>{car_name}</b>\n\n"
        full_message = msg_header + full_message_body
        
        import threading
        threading.Thread(target=send_telegram_alert_message, args=(full_message,), daemon=True).start()
