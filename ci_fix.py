# ci_fix.py
import os

print("[CI-FIX] Глубокая очистка синтаксиса проекта перед сборкой...")

# Исправление BOM в app.py на любой строке
if os.path.exists("app.py"):
    with open("app.py", "r", encoding="utf-8-sig") as f:
        text = f.read()
    with open("app.py", "w", encoding="utf-8") as f:
        f.write(text)
    print("[CI-FIX] BOM из app.py успешно удален.")

# Ювелирное склеивание разорванных строк во views.py
if os.path.exists("views.py"):
    with open("views.py", "r", encoding="utf-8") as f:
        code = f.read()
        
    # Склеиваем разорванную f-строку "Быстрый сброс"
    code = code.replace('"Быстрый\nсброс"', '"Быстрый сброс"')
    code = code.replace('"Быстрый\n сброс"', '"Быстрый сброс"')
    
    # Склеиваем разорванный тултип кнопки История ТО, сохраняя структуру элементов
    old_broken_tooltip = '''tooltip="Просмотр и
удаление истории записей",'''
    
    new_fixed_tooltip = 'tooltip="Просмотр и удаление истории записей",'
    
    code = code.replace(old_broken_tooltip, new_fixed_tooltip)
    
    with open("views.py", "w", encoding="utf-8") as f:
        f.write(code)
    print("[CI-FIX] Все разорванные строки во views.py успешно восстановлены.")
