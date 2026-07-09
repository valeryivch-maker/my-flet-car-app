# restore_odometer_history.py
import os

def restore_function():
    file_path = "views.py"
    if not os.path.exists(file_path):
        print(f"[ОШИБКА] Файл {file_path} не найден!")
        return

    print("[СТАРТ] Анализ файла views.py на наличие функции истории пробега...")
    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()

    if "show_car_odometer_history_dialog" in code:
        print("[ИНФО] Функция уже присутствует в коде. Повторное восстановление не требуется.")
        return

    # Оригинальный код функции со страницы 6-7, адаптированный под мобильные экраны
    odometer_dialog_code = """

def show_car_odometer_history_dialog(page, db_data, car_profile, rebuild, show_msg):
    h_cont = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
    
    def render():
        h_cont.controls.clear()
        for item in sorted(car_profile.get("odometer_history", []), key=engine.parse_h_date, reverse=True):
            def make_del(i=item): 
                return lambda _: [car_profile["odometer_history"].remove(i), engine.save_data(db_data), render(), rebuild(), show_msg("Удалено")]
            h_cont.controls.append(ft.Container(
                content=ft.Row([
                    ft.Column([ft.Text(f"{item['value']} км", weight=ft.FontWeight.BOLD), ft.Text(item['date'])]),
                    ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED_400, on_click=make_del())
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), 
                padding=5, 
                border=ft.Border.all(1, ft.Colors.BLACK_12),
                border_radius=6
            ))
        page.update()
        
    def add_click(_):
        a_km = ft.TextField(label="Пробег")
        a_dt = ft.TextField(label="Дата", value=datetime.now().strftime("%d.%m.%Y"))
        
        def save(_):
            try:
                v = int(a_km.value); d = a_dt.value.strip(); datetime.strptime(d, "%d.%m.%Y")
                if "odometer_history" not in car_profile:
                    car_profile["odometer_history"] = []
                car_profile["odometer_history"].append({"value": v, "date": d})
                if v >= car_profile["odometer"].get("value", 0): 
                    car_profile["odometer"] = {"value": v, "date": d}
                car_profile["daily_mileage"] = engine.recalculate_auto_daily_mileage(car_profile)
                engine.save_data(db_data); adlg.open = False; render(); rebuild(); show_msg("Добавлено!")
            except: 
                show_msg("Ошибка формата!")
                
        adlg = ft.AlertDialog(title=ft.Text("Добавить пробег"), content=ft.Column([a_km, a_dt], tight=True), actions=[ft.TextButton("OK", on_click=save)])
        page.overlay.append(adlg); adlg.open = True; page.update()
        
    dlg = ft.AlertDialog(
        title=ft.Text("История общего пробега"), 
        content=ft.Container(content=ft.Column([ft.Button("+ Добавить запись", icon=ft.Icons.ADD, on_click=add_click), h_cont], tight=True), adaptive=True)
    )
    page.overlay.append(dlg); dlg.open = True; render()
"""

    print("[ЗАПИСЬ] Интеграция функции в конец модуля views.py...")
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(odometer_dialog_code)

    print("[УСПЕХ] Функция show_car_odometer_history_dialog полностью восстановлена и адаптирована!")

if __name__ == "__main__":
    restore_function()
    input("\nНажмите Enter для завершения...")
