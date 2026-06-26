import flet as ft
import json
import io
import requests
import urllib3
from concurrent.futures import ThreadPoolExecutor
import engine

# Отключение предупреждений SSL для корректной работы сетевого контейнера на Android
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Сетевые константы Telegram Bot API
TG_TOKEN = "8859678783:AAHA9MbUhnS17bmf7w-vINLkwYPil-gOVuU"
TG_CHAT_ID = "1036911003"
network_executor = ThreadPoolExecutor(max_workers=2)

def show_custom_file_manager_dialog(page: ft.Page, mode: str, db_data_ref: dict, show_message_callback):
    URL_EXPORT = f"https://telegram.org{TG_TOKEN}/sendDocument"
    URL_UPDATES = f"https://telegram.org{TG_TOKEN}/getUpdates"
    URL_FILE_INFO = f"https://telegram.org{TG_TOKEN}/getFile"
    URL_DOWNLOAD_BASE = f"https://telegram.org{TG_TOKEN}/"

    if mode == "export":
        def async_export_worker():
            try:
                current_db_data = engine.load_data()
                if not current_db_data or "cars" not in current_db_data:
                    current_db_data = {"cars": {}, "history": []}

                json_text = json.dumps(current_db_data, ensure_ascii=False, indent=4)
                file_stream = io.BytesIO(json_text.encode("utf-8"))
                file_stream.name = "CarJournal_database.json"

                payload_data = {
                    "chat_id": int(TG_CHAT_ID),
                    "caption": "🤖 Резервная копия базы Журнала ТО"
                }
                payload_files = {"document": file_stream}

                response = requests.post(
                    URL_EXPORT, data=payload_data, files=payload_files, timeout=15, verify=False
                )
                if response.status_code == 200:
                    show_message_callback("Бэкап успешно отправлен в Telegram!")
                else:
                    show_message_callback(f"Ошибка облака: Код {response.status_code}")
            except Exception as ex:
                show_message_callback(f"Сбой сети: {str(ex)}")

        network_executor.submit(async_export_worker)

    elif mode == "import":
        progress_ring = ft.ProgressRing(width=30, height=30, stroke_width=3)
        status_text = ft.Text("Поиск последнего бэкапа в Telegram...", size=14)

        def close_dialog(e):
            dialog.open = False
            page.update()

        def async_import_worker():
            try:
                response = requests.get(URL_UPDATES, timeout=15, verify=False)
                if response.status_code != 200:
                    status_text.value = f"Ошибка сети: Код {response.status_code}"
                    page.update()
                    return

                updates = response.json().get("result", [])
                backup_file_id = None

                for update in reversed(updates):
                    message = update.get("message", {})
                    document = message.get("document", {})
                    if document and "json" in document.get("file_name", "").lower():
                        backup_file_id = document.get("file_id")
                        break

                if not backup_file_id:
                    status_text.value = "Бэкап в облаке не найден!"
                    page.update()
                    return

                status_text.value = "Скачивание файла..."
                page.update()

                file_info_res = requests.get(URL_FILE_INFO, params={"file_id": backup_file_id}, timeout=15, verify=False)
                file_path = file_info_res.json().get("result", {}).get("file_path")

                download_res = requests.get(URL_DOWNLOAD_BASE + file_path, timeout=15, verify=False)
                imported_json = json.loads(download_res.text)

                if "cars" in imported_json:
                    engine.save_data(imported_json)

                    # Сброс ОЗУ кэша переданного словаря по ссылке
                    db_data_ref.clear()
                    db_data_ref.update(engine.load_data())

                    status_text.value = "Синхронизация успешна!"
                    page.update()
                    show_message_callback("База успешно восстановлена!")

                    if page.data and "refresh_ui" in page.data:
                        page.data["refresh_ui"]()

                    dialog.open = False
                    page.update()
                else:
                    status_text.value = "Файл поврежден."
                    page.update()
            except Exception as ex:
                status_text.value = f"Ошибка: {str(ex)}"
                page.update()

            def start_sync_import(e):
                confirm_btn.visible = False
                action_container.content = progress_ring
                page.update()
                network_executor.submit(async_import_worker)

        confirm_btn = ft.FilledButton(
            "Начать импорт",
            on_click=lambda e: [setattr(confirm_btn, "visible", False), 
                               setattr(action_container, "content", progress_ring), 
                               page.update(), 
                               network_executor.submit(async_import_worker)],
            style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.BLUE)
        )
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
