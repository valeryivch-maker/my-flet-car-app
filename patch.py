import os

def fix_indent_final():
    target_path = "main.py"
    
    if not os.path.exists(target_path):
        print(f"[ОШИБКА] Файл {target_path} не найден.")
        input("\nНажмите Enter для выхода...")
        return

    with open(target_path, "r", encoding="utf-8") as f:
        code = f.read()

    # Ищем ошибочный блок с кривым отступом, который сгенерировал прошлый патч
    bad_block = """            except requests.exceptions.Timeout:
                lbl.value = "Превышено время ожидания сети."
                    page.update()"""

    # Заменяем его на блок с идеальным выравниванием по стандарту PEP 8
    good_block = """            except requests.exceptions.Timeout:
                lbl.value = "Превышено время ожидания сети."
                page.update()"""

    if bad_block in code:
        code = code.replace(bad_block, good_block)
        
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(code)
            f.flush()
            os.fsync(f.fileno())
            
        print("\n==============================================================")
        print("[ПАТЧ ВЫПОЛНЕН] Ошибка отступа на строке 82 успешно устранена!")
        print("-> Убран лишний сдвиг перед page.update() в блоке таймаута.")
        print("==============================================================")
    else:
        # Если блок не найден точным совпадением, пересобираем всю функцию начисто
        with open(target_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        new_lines = []
        inside_import = False
        inserted = False
        
        for line in lines:
            if "def async_import" in line:
                inside_import = True
                continue
            if inside_import and 'ac = ft.Container(content=ft.FilledButton("Начать импорт"' in line:
                inside_import = False
                new_lines.append("        def async_import():\n")
                new_lines.append("            try:\n")
                new_lines.append('                res = requests.Session().get(URL_UPDATES, params={"offset": -20, "limit": 20}, timeout=5)\n')
                new_lines.append("                if res.status_code != 200: \n")
                new_lines.append('                    lbl.value = f"Ошибка сервера: {res.status_code}"\n')
                new_lines.append("                    page.update()\n")
                new_lines.append("                    return\n")
                new_lines.append('                updates = res.json().get("result", [])\n')
                new_lines.append("                if not updates:\n")
                new_lines.append('                    lbl.value = "Чат пуст! Отправьте файл в бот."\n')
                new_lines.append("                    page.update()\n")
                new_lines.append("                    return\n")
                new_lines.append("                f_id = None\n")
                new_lines.append("                for upd in reversed(updates):\n")
                new_lines.append('                    msg_obj = upd.get("message") or upd.get("edited_message") or {}\n')
                new_lines.append('                    doc = msg_obj.get("document", {})\n')
                new_lines.append('                    if doc and "json" in doc.get("file_name", "").lower(): \n')
                new_lines.append('                        f_id = doc.get("file_id")\n')
                new_lines.append("                        break\n")
                new_lines.append("                if not f_id: \n")
                new_lines.append('                    lbl.value = "Бэкап .json не найден в чате!"\n')
                new_lines.append("                    page.update()\n")
                new_lines.append("                    return\n")
                new_lines.append('                lbl.value = "Скачивание бэкапа..."\n')
                new_lines.append("                page.update()\n")
                new_lines.append('                f_res = requests.Session().get(URL_FILE_INFO, params={"file_id": f_id}, timeout=5)\n')
                new_lines.append('                f_path = f_res.json().get("result", {}).get("file_path")\n')
                new_lines.append('                dl_res = requests.Session().get(URL_DOWNLOAD_BASE + f_path, timeout=10)\n')
                new_lines.append("                imported = json.loads(dl_res.text)\n")
                new_lines.append('if "cars" in imported:\n')
                new_lines.append("                    engine.save_data(imported)\n")
                new_lines.append("                    if 'db_data' in globals(): \n")
                new_lines.append("                        global db_data\n")
                new_lines.append("                        db_data.clear()\n")
                new_lines.append("                        db_data.update(engine.load_data())\n")
                new_lines.append('                    lbl.value = "Успешно импортировано!"\n')
                new_lines.append("                    page.update()\n")
                new_lines.append('                    show_msg("База данных восстановлена!")\n')
                new_lines.append('                    if page.data and "refresh_ui" in page.data: \n')
                new_lines.append('                        page.data["refresh_ui"]()\n')
                new_lines.append("                    dlg.open = False\n")
                new_lines.append("                    page.update()\n")
                new_lines.append("                else: \n")
                new_lines.append('                    lbl.value = "Неверная структура файла."\n')
                new_lines.append("                    page.update()\n")
                new_lines.append("            except requests.exceptions.Timeout:\n")
                new_lines.append('                lbl.value = "Превышено время ожидания сети."\n')
                new_lines.append("                page.update()\n")
                new_lines.append("            except Exception as ex: \n")
                new_lines.append('                lbl.value = f"Сбой: {str(ex)[:25]}"\n')
                new_lines.append("                page.update()\n\n")
                inserted = True
            if not inside_import:
                new_lines.append(line)
                
        with open(target_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
            f.flush()
            os.fsync(f.fileno())
        print("\n==============================================================")
        print("[ПАТЧ ВЫПОЛНЕН] Функция полностью пересобрана с ровными отступами.")
        print("==============================================================")

    input("\nДля продолжения нажмите Enter...")

if __name__ == "__main__":
    fix_indent_final()
