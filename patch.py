# final_safe_fix.py
import os

def apply_final_fix():
    file_path = "main.py"
    if not os.path.exists(file_path):
        print(f"[ОШИБКА] Файл {file_path} не найден!")
        return

    print("[СТАРТ] Чтение исходного main.py...")
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Находим блок action_panel
    start_idx = -1
    for idx, line in enumerate(lines):
        if "action_panel =" in line:
            start_idx = idx
            break

    if start_idx == -1:
        print("[ОШИБКА] Блок action_panel не обнаружен.")
        return

    end_idx = -1
    for idx in range(start_idx, len(lines)):
        if "odo_hist =" in lines[idx]:
            end_idx = idx
            break

    if end_idx == -1:
        print("[ОШИБКА] Конец блока не найден.")
        return

    # Динамически определяем отступ
    base_indent = " " * 4
    for line in lines:
        if "cars_dict =" in line:
            base_indent = line[:len(line) - len(line.lstrip())]
            break

    # Переписываем панель через нативный ft.Row(wrap=True) без f-строк (экранируем вручную)
    bi = base_indent
    new_panel = [
        bi + "action_panel = ft.Row([\n",
        bi + "    ft.Row([\n",
        bi + "        ft.Text(\"База:\", size=14, weight=ft.FontWeight.W_500),\n",
        bi + "        ft.IconButton(ft.Icons.CLOUD_UPLOAD, on_click=lambda _: network.auto_export_file_to_telegram(page, show_message)),\n",
        bi + "        ft.IconButton(ft.Icons.CLOUD_DOWNLOAD, on_click=lambda _: network.auto_import_last_file(page, show_message) or refresh_ui()),\n",
        bi + "        ft.IconButton(ft.Icons.BAR_CHART_ROUNDED, on_click=lambda _: [engine.app_state.update({'view_mode': 'analytics' if engine.app_state.get('view_mode') != 'analytics' else 'list'}), rebuild_ui()]),\n",
        bi + "    ], spacing=2, tight=True),\n",
        bi + "    ft.Row([ \n",
        bi + "        ft.IconButton(ft.Icons.ADD_CIRCLE, on_click=add_car_click),\n",
        bi + "        ft.IconButton(icon=ft.Icons.EDIT, on_click=edit_car_name_click),\n",
        bi + "        ft.IconButton(ft.Icons.DELETE_FOREVER, on_click=delete_car_click, icon_color=ft.Colors.RED_500),\n",
        bi + "    ], spacing=2, tight=True)\n",
        bi + "], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True)\n"
    ]

    # Сборка файла
    final_lines = lines[:start_idx] + new_panel + lines[end_idx:]

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(final_lines)

    print("[УСПЕХ] Панель переведена на стабильный ft.Row(wrap=True). Ошибки форматирования устранены!")

if __name__ == "__main__":
    apply_final_fix()
    input("\nНажмите Enter для завершения...")
