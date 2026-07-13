# local_folder_sync.py
import os
import shutil
import glob
import re

def sync_from_telegram_downloads():
    print("[СТАРТ] Сканирование локальной папки загрузок Telegram Desktop...")
    
    # Стандартный путь к папке загрузок Telegram Desktop на вашем ноутбуке
    tg_downloads_path = r"C:\Users\User\Загрузки\Telegram Desktop"
    
    if not os.path.exists(tg_downloads_path):
        # Резервный вариант, если папка Users называется по-другому
        user_profile = os.environ.get("USERPROFILE", "C:\\Users\\User")
        tg_downloads_path = os.path.join(user_profile, "Downloads", "Telegram Desktop")
        if not os.path.exists(tg_downloads_path):
            tg_downloads_path = os.path.join(user_profile, "Загрузки", "Telegram Desktop")

    if not os.path.exists(tg_downloads_path):
        print(f"[ОШИБКА] Не удалось найти папку по пути: {tg_downloads_path}")
        return False

    # Ищем все файлы, имя которых начинается на Carjournal_database
    search_pattern = os.path.join(tg_downloads_path, "Carjournal_database*.json")
    found_files = glob.glob(search_pattern)

    if not found_files:
        print(f"[ВНИМАНИЕ] В папке {tg_downloads_path} не найдено файлов бэкапа!")
        return False

    # Функция для извлечения номера в скобках, чтобы найти самый последний файл
    def get_file_number(filepath):
        filename = os.path.basename(filepath)
        # Ищем число внутри круглых скобок, например (26)
        match = re.search(r"\((\d+)\)", filename)
        if match:
            return int(match.group(1))
        # Если файл без скобок (самый первый), даем ему номер 0
        return 0

    # Сортируем файлы по номеру в скобках (от большего к меньшему)
    found_files.sort(key=get_file_number, reverse=True)
    
    # Самый свежий файл на основе вашей фотографии
    latest_source_file = found_files[0]
    print(f"[НАЙДЕНО] Обнаружен самый свежий бэкап телефона: {os.path.basename(latest_source_file)}")

    # Путь назначения в корне нашего Flet-приложения
    target_file = "database.txt"

    try:
        # Копируем файл из загрузок Telegram в корень проекта, переименовывая в database.txt
        shutil.copy2(latest_source_file, target_file)
        print(f"[УСПЕХ] Файл скопирован и сохранен как {target_file} в корне проекта!")
        print(f"Размер перенесенной базы: {os.path.getsize(target_file)} байт.")
        return True
    except Exception as e:
        print(f"[КРИТИЧЕСКАЯ ОШИБКА КОПИРОВАНИЯ]: {e}")
        return False

if __name__ == "__main__":
    sync_from_telegram_downloads()
    print("\nСинхронизация завершена.")
    input("Нажмите Enter для завершения...")
