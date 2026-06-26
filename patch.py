import os

def main():
    target_file = "network.py"
    
    if not os.path.exists(target_file):
        print(f"Ошибка: Файл {target_file} не найден!")
        return

    with open(target_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    modified = False
    for i, line in enumerate(lines):
        # Ищем строки объявления констант и жестко их перезаписываем
        if "URL_EXPORT =" in line and "telegram.org" in line:
            lines[i] = '    URL_EXPORT = f"https://telegram.org{TG_TOKEN}/sendDocument"\n'
            modified = True
        elif "URL_UPDATES =" in line and "telegram.org" in line:
            lines[i] = '    URL_UPDATES = f"https://telegram.org{TG_TOKEN}/getUpdates"\n'
            modified = True
        elif "URL_FILE_INFO =" in line and "telegram.org" in line:
            lines[i] = '    URL_FILE_INFO = f"https://telegram.org{TG_TOKEN}/getFile"\n'
            modified = True
        elif "URL_DOWNLOAD_BASE =" in line and "telegram.org" in line:
            lines[i] = '    URL_DOWNLOAD_BASE = f"https://telegram.org{TG_TOKEN}/"\n'
            modified = True

    if modified:
        with open(target_file, "w", encoding="utf-8") as f:
            f.writelines(lines)
            f.flush()
            os.fsync(f.fileno())
        print("\n[УСПЕХ] network.py принудительно обновлен по маске констант!")
    else:
        print("\n[ВНИМАНИЕ] Совпадений не найдено. Проверь, что вывело в консоль.")

if __name__ == "__main__":
    main()
    input("\nДля продолжения нажмите Enter...")
