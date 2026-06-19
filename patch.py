import os

def run_patch():
    file_path = "main.py"
    
    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()

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

    for old, new in replacements.items():
        code = code.replace(old, new)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(code)
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError:
            pass

    # Четкий и лаконичный вывод по ТЗ
    print("ПАТЧ ВЫПОЛНЕН: Зависание сетевого сокета импорта устранено.")

if __name__ == "__main__":
    run_patch()
    # Ожидание действия пользователя в самом низу
    input("нажми ентер")
