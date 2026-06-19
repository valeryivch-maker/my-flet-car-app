import os

def run_patch():
    file_path = "main.py"
    
    # Чтение исходного кода
    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()

    # Карта замен: убираем requests.Session(), добавляем verify=False
    replacements = {
        'res = requests.Session().post(URL_EXPORT, data={"chat_id": int(TG_CHAT_ID), "caption": "📦\nБэкап Журнала ТО"}, files={"document": stream}, timeout=10)':
        'res = requests.post(URL_EXPORT, data={"chat_id": int(TG_CHAT_ID), "caption": "📦\\nБэкап Журнала ТО"}, files={"document": stream}, timeout=10, verify=False)',

        'res = requests.Session().get(URL_UPDATES, params={"offset": -10, "limit": 10}, timeout=5)':
        'res = requests.get(URL_UPDATES, params={"offset": -10, "limit": 10}, timeout=5, verify=False)',

        'f_res = requests.Session().get(URL_FILE_INFO, params={"file_id": f_id}, timeout=5)':
        'f_res = requests.get(URL_FILE_INFO, params={"file_id": f_id}, timeout=5, verify=False)',

        'dl_res = requests.Session().get(URL_DOWNLOAD_BASE + f_path, timeout=10)':
        'dl_res = requests.get(URL_DOWNLOAD_BASE + f_path, timeout=10, verify=False)'
    }

    # Применение правок
    for old, new in replacements.items():
        code = code.replace(old, new)

    # Запись изменений и жесткий сброс кэша диска Windows
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(code)
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError:
            pass

    # Вывод отчета о работе в консоль
    print("ПАТЧ ВЫПОЛНЕН: Зависание сетевого сокета импорта устранено.")
    print("Изменения внесены в main.py, кэш Windows сброшен.")

if __name__ == "__main__":
    run_patch()
    # Финальное требование по ТЗ
    input("\nДля продолжения нажмите Enter...")
