import os

def main():
    target_file = "network.py"
    
    if not os.path.exists(target_file):
        print(f"Ошибка: Файл {target_file} не найден!")
        return

    with open(target_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Точечная и гарантированная замена доменов
    if "https://telegram.org" in content:
        content = content.replace("https://telegram.org", "https://telegram.org")
        # Корректируем базовый URL скачивания файлов (у него другой формат в API)
        content = content.replace("api.telegram.org/bot{TG_TOKEN}/\"", "api.telegram.org/file/bot{TG_TOKEN}/\"")
        
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        print("\n[УСПЕХ] Файл network.py успешно обновлен!")
    else:
        print("\n[ИНФО] Похоже, домен telegram.org в файле не найден или уже заменен.")

if __name__ == "__main__":
    main()
    input("\nДля продолжения нажмите Enter...")
