# ci_fix.py
import os
import re

print("[CI-FIX] Запуск серверного исправления синтаксиса...")

# Исправление BOM в app.py
if os.path.exists("app.py"):
    with open("app.py", "r", encoding="utf-8-sig") as f:
        text = f.read()
    with open("app.py", "w", encoding="utf-8") as f:
        f.write(text)
    print("[CI-FIX] BOM из app.py успешно удален.")

# Исправление функции make_copy во views.py
if os.path.exists("views.py"):
    with open("views.py", "r", encoding="utf-8") as f:
        code = f.read()
    
    perfect_copy = '''def make_copy(code_to_copy=rec.get('part_code', '')):
        def do_copy(_):
            import os
            if os.name == "nt":
                try:
                    import subprocess
                    subprocess.run(f"echo {str(code_to_copy).strip()} | clip", shell=True, check=True)
                    show_msg(f"📋 Артикул {code_to_copy} скопирован!")
                except:
                    pass
            else:
                try:
                    page.set_clipboard(str(code_to_copy))
                    show_msg(f"📋 Артикул {code_to_copy} скопирован!")
                except:
                    try:
                        page.clipboard = str(code_to_copy)
                        show_msg(f"📋 Артикул {code_to_copy} скопирован!")
                    except:
                        show_msg("Ошибка копирования!")
        return do_copy'''
        
    pattern = r"def make_copy\(.*?\):.*?return do_copy"
    if re.search(pattern, code, re.DOTALL):
        code = re.sub(pattern, perfect_copy, code, flags=re.DOTALL)
    else:
        code = code.replace("def make_copy(code_to_copy=rec.get('part_code', '')):", perfect_copy)
        
    with open("views.py", "w", encoding="utf-8") as f:
        f.write(code)
    print("[CI-FIX] Функция make_copy во views.py успешно пересобрана.")
