import os

def apply_clean_import_patch():
    target_path = "main.py"
    
    if not os.path.exists(target_path):
        print(f"[ОШИБКА] Файл {target_path} не найден в этой папке.")
        input("\nНажмите Enter...")
        return

    with open(target_path, "r", encoding="utf-8") as f:
        code = f.read()

    # Точные маркеры границ всей старой функции менеджера файлов
    start_keyword = "def show_custom_file_manager_dialog("
    end_keyword = "def generate_car_view("

    start_idx = code.find(start_keyword)
    end_idx = code.find(end_keyword)

    if start_idx == -1 or end_idx == -1:
        print("[ОШИБКА] Не удалось найти блок диалога бэкапов в main.py.")
        input("\nНажмите Enter...")
        return

    # Новый, абсолютно чистый и проверенный блок функции
    new_dialog_block = """def show_custom_file_manager_dialog(page, mode, on_file_selected, show_msg):
    URL_EXPORT = f"https://telegram.org{TG_TOKEN}/sendDocument"
    URL_UPDATES = f"https://telegram.org{TG_TOKEN}/getUpdates"
    URL_FILE_INFO = f"https://telegram.org{TG_TOKEN}/getFile"
    URL_DOWNLOAD_BASE = f"https://telegram.org{TG_TOKEN}/"

    if mode == "export":
        def async_export():
            try:
                curr = engine.load_data()
                js_t = json.dumps(curr, ensure_ascii=False, indent=4)
                stream = io.BytesIO(js_t.encode("utf-8"))
                stream.name = "CarJournal_database.json"
                res = requests.Session().post(URL_EXPORT, data={"chat_id": int(TG_CHAT_ID), "caption": "📦 Бэкап Журнала ТО"}, files={"document": stream}, timeout=10)
                show_msg("Бэкап успешно отправлен!" if res.status_code == 200 else f"Ошибка: {res.status_code}")
            except Exception as ex: show_msg(f"Сбой сети: {ex}")
        network_executor.submit(async_export)
    elif mode == "import":
        ring = ft.ProgressRing(width=30, height=30, stroke_width=3)
        lbl = ft.Text("Поиск бэкапа в Telegram...", size=14)
        
        def async_import():
            try:
                # Жесткий таймаут 5 секунд, запрашиваем только последние сообщения
                res = requests.Session().get(URL_UPDATES, params={"offset": -10, "limit": 10}, timeout=5)
                if res.status_code != 200:
                    lbl.value = f"Ошибка сервера: {res.status_code}"
                    page.update()
                    return
                
                updates = res.json().get("result", [])
                if not updates:
                    lbl.value = "Чат пуст! Отправьте файл боту."
                    page.update()
                    return
                
                f_id = None
                for upd in reversed(updates):
                    msg_obj = upd.get("message") or upd.get("edited_message") or {}
                    doc = msg_obj.get("document", {})
                    if doc and "json" in doc.get("file_name", "").lower():
                        f_id = doc.get("file_id")
                        break
                
                if not f_id:
                    lbl.value = "Файл бэкапа .json не найден!"
                    page.update()
                    return
                
                lbl.value = "Скачивание бэкапа..."
                page.update()
                
                f_res = requests.Session().get(URL_FILE_INFO, params={"file_id": f_id}, timeout=5)
                f_path = f_res.json().get("result", {}).get("file_path")
                
                dl_res = requests.Session().get(URL_DOWNLOAD_BASE + f_path, timeout=10)
                imported = json.loads(dl_res.text)
                
                if "cars" in imported:
                    engine.save_data(imported)
                    if 'db_data' in globals():
                        global db_data
                        db_data.clear()
                        db_data.update(engine.load_data())
                    lbl.value = "Успешно импортировано!"
                    page.update()
                    show_msg("База данных восстановлена!")
                    if page.data and "refresh_ui" in page.data:
                        page.data["refresh_ui"]()
                    dlg.open = False
                    page.update()
                else:
                    lbl.value = "Неверная структура файла."
                    page.update()
            except requests.exceptions.Timeout:
                lbl.value = "Время ожидания сети истекло."
                page.update()
            except Exception as ex:
                lbl.value = f"Сбой: {str(ex)[:20]}"
                page.update()

        ac = ft.Container(content=ft.FilledButton("Начать импорт", on_click=lambda _: [setattr(ac, "content", ring), page.update(), network_executor.submit(async_import)], style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.BLUE)))
        dlg = ft.AlertDialog(title=ft.Text("Облачный Импорт"), content=ft.Column([lbl, ft.Container(height=10), ac], tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER), actions=[ft.TextButton("Отмена", on_click=lambda _: [setattr(dlg, "open", False), page.update()])])
        page.overlay.append(dlg); dlg.open = True; page.update()

"""

    # Собираем файл обратно
    code = code[:start_idx] + new_dialog_block + code[end_idx:]

    with open(target_path, "w", encoding="utf-8") as f:
        f.write(code)
        f.flush()
        os.fsync(f.fileno())

    print("\n==============================================================")
    print("[ПАТЧ ВЫПОЛНЕН] Блок импорта полностью обновлен!")
    print("-> Код очищен от старых зависающих дубликатов.")
    print("-> Добавлены жесткие мобильные ограничения на сетевые сокеты.")
    print("==============================================================")
    input("\nДля продолжения нажмите Enter...")

if __name__ == "__main__":
    apply_clean_import_patch()
