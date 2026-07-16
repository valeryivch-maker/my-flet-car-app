# ci_fix.py
import os

print("[CI-FIX] Ювелирная очистка синтаксиса проекта...")

# 1. Принудительное вырезание BOM из app.py на любой строке
if os.path.exists("app.py"):
    with open("app.py", "r", encoding="utf-8-sig") as f:
        text = f.read()
    with open("app.py", "w", encoding="utf-8") as f:
        f.write(text)
    print("[CI-FIX] BOM из app.py успешно удален.")

# 2. Восстановление разорванных строк во views.py
if os.path.exists("views.py"):
    with open("views.py", "r", encoding="utf-8") as f:
        code = f.read()
        
    # Склеиваем разорванную строку "Быстрый сброс"
    code = code.replace('"Быстрый\\nсброс"', '"Быстрый сброс"')
    code = code.replace('"Быстрый\\n сброс"', '"Быстрый сброс"')
    
    # Склеиваем первый тултип (кнопка История ТО)
    old_broken_tooltip1 = 'tooltip="Просмотр и\\nудаление истории записей",'
    new_fixed_tooltip1 = 'tooltip="Просмотр и удаление истории записей",'
    code = code.replace(old_broken_tooltip1, new_fixed_tooltip1)
    
    # Склеиваем второй тултип (кнопка Внести запись)
    old_broken_tooltip2 = 'tooltip="Внести запись в историю\\nвручную (кастомная дата/пробег)",'
    new_fixed_tooltip2 = 'tooltip="Внести запись в историю вручную (кастомная дата/пробег)",'
    code = code.replace(old_broken_tooltip2, new_fixed_tooltip2)
    
    with open("views.py", "w", encoding="utf-8") as f:
        f.write(code)
    print("[CI-FIX] Все разорванные строки во views.py успешно склеены!")
