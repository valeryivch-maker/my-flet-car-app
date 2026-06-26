import os

def main():
    target_file = "network.py"
    
    if not os.path.exists(target_file):
        print(f"Ошибка: Файл {target_file} не найден в текущей директории!")
        return

    print(f"Читаем {target_file}...")
    with open(target_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Точные маркеры для замены дефектных URL-адресов
    old_block = (
        '    URL_EXPORT = f"https://telegram.org{TG_TOKEN}/sendDocument"\n'
        '    URL_UPDATES = f"https://telegram.org{TG_TOKEN}/getUpdates"\n'
        '    URL_FILE_INFO = f"https://telegram.org{TG_TOKEN}/getFile"\n'
        '    URL_DOWNLOAD_BASE = f"https://telegram.org{TG_TOKEN}/"'
    )

    new_block = (
        '    URL_EXPORT = f"https://telegram.org{TG_TOKEN}/sendDocument"\n'
        '    URL_UPDATES = f"https://telegram.org{TG_TOKEN}/getUpdates"\n'
        '    URL_FILE_INFO = f"https://telegram.org{TG_TOKEN}/getFile"\n'
        '    URL_DOWNLOAD_BASE = f"https://telegram.org{TG_TOKEN}/"'
    )

    if old_block in content:
        updated_content = content.replace(old_block, new_block)
        
        # Запись изменений с гарантированным сбросом буферов на диск
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(updated_content)
            f.flush()
            os.fsync(f.fileno())
            
        print("\n[УСПЕХ] Патч успешно применен!")
        print("Заменены базовые адреса Telegram Bot API на корректные.")
        print("Обход SSL (verify=False) и таймауты уже были корректно внедрены в network.py.")
    else:
        print("\n[ПРЕДУПРЕЖДЕНИЕ] Целевой блок кода не найден. Возможно, патч уже был применен ранее.")

if __name__ == "__main__":
    main()
    # Инструментальное требование интерфейса: удержание окна терминала открытым
    input("\nДля продолжения нажмите Enter...")
