import flet as ft
from datetime import datetime, timedelta
import engine

def generate_analytics_view(page, car_profile):
    view_column = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=15)
    current_km = car_profile.get("odometer", {}).get("value", 0)
    tasks = car_profile.get("maintenance_data", {})
    
    # --- БЛОК 1: ФИНАНСОВАЯ СТАТИСТИКА И СТОИМОСТЬ КИЛОМЕТРА ---
    stats_30 = engine.calculate_fuel_stats(car_profile, days=30)
    cost_per_km = engine.calculate_cost_per_km_brsm(car_profile)
    
    fin_card = ft.Card(
        content=ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.MONETIZATION_ON, color=ft.Colors.GREEN_700, size=24),
                    ft.Text("Финансовая аналитика (30 дн.)", size=16, weight=ft.FontWeight.BOLD)
                ], alignment=ft.MainAxisAlignment.START, spacing=8),
                ft.Divider(height=1, color=ft.Colors.BLACK_12),
                ft.Row([
                    ft.Text("⛽ Топливо:", size=13),
                    ft.Text(f"{stats_30['fuel_spent']} грн", size=13, weight=ft.FontWeight.W_600)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([
                    ft.Text("🛠️ Ремонт и ТО:", size=13),
                    ft.Text(f"{stats_30['maintenance_spent']} грн", size=13, weight=ft.FontWeight.W_600)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([
                    ft.Text("💰 Всего затрат:", size=14, weight=ft.FontWeight.BOLD),
                    ft.Text(f"{stats_30['total_spent']} грн", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(height=1, color=ft.Colors.BLACK_12),
                ft.Row([
                    ft.Text("📍 Стоимость 1 км пути:", size=13, weight=ft.FontWeight.W_500),
                    ft.Container(
                        content=ft.Text(f"{cost_per_km} грн/км", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        bgcolor=ft.Colors.GREEN_700,
                        padding=ft.Padding(6, 2, 6, 2),
                        border_radius=4
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ], spacing=8),
            padding=14
        ),
        bgcolor=ft.Colors.SURFACE_CONTAINER_LOW
    )
    view_column.controls.append(fin_card)
    
    # --- БЛОК 2: АНАЛИТИКА ИЗНОСА РЕГЛАМЕНТОВ ТО ---
    view_column.controls.append(ft.Text("Аналитика износа регламентов", size=18, weight=ft.FontWeight.BOLD))
    
    if not tasks:
        view_column.controls.append(ft.Text("Нет данных по регламентам", color=ft.Colors.GREY_500, italic=True))
        return view_column
        
    for t_name, t_data in tasks.items():
        interval = t_data.get("interval", 1)
        remains = (t_data.get("last_service", 0) + interval) - current_km
        passed = max(0, current_km - t_data.get("last_service", 0))
        res = max(0.0, min(1.0, 1.0 - (passed / interval)))
        b_color = ft.Colors.RED_600 if remains <= 0 else (ft.Colors.ORANGE_700 if remains <= 500 else ft.Colors.GREEN_700)
        st_text = "Срочно заменить!" if remains <= 0 else f"Осталось {remains} км"
        
        view_column.controls.append(ft.Card(content=ft.Container(content=ft.Column([
            ft.Row([ft.Text(t_name, size=14, weight=ft.FontWeight.BOLD, expand=True), ft.Text(f"{int(res * 100)}%", size=13, color=b_color)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.ProgressBar(value=res, color=b_color, bgcolor=ft.Colors.GREY_200, height=8),
            ft.Text(st_text, size=12, color=ft.Colors.GREY_600, italic=True)
        ], spacing=4), padding=12)))
        
    return view_column

def show_task_history_dialog(page, db_data, task_name, car_profile, rebuild, show_msg): 
    h_col = ft.Column(scroll=ft.ScrollMode.AUTO, height=220, spacing=8) 
 
    def refresh(): 
        h_col.controls.clear() 
        if "history" not in car_profile: 
            car_profile["history"] = [] 
        t_hist = [h for h in car_profile.get("history", []) if h.get("task") == task_name] 
 
        if not t_hist: 
            h_col.controls.append(ft.Text("Пусто", italic=True)) 
        else: 
            for rec in sorted(t_hist, key=lambda x: int(x.get('odometer', 0)), reverse=True): 
                # Функция-замыкание для удаления 
                def make_del(r=rec): 
                    return lambda _: [car_profile["history"].remove(r), engine.save_data(db_data), refresh(), rebuild(), show_msg("Удалено")] 
 
                # Функция-замыкание для вызова окна редактирования записи 
                def make_edit(r=rec): 
                    def open_edit_dialog(_): 
                        edit_odo = ft.TextField(label="Пробег", value=str(r.get("odometer", ""))) 
                        edit_date = ft.TextField(label="Дата", value=str(r.get("date", ""))) 
                        edit_comm = ft.TextField(label="Комментарий", value=str(r.get("comment", ""))) 
 
                        def save_edited_rec(_): 
                            try: 
                                km = int(edit_odo.value) 
                                dt_str = edit_date.value.strip() 
                                datetime.strptime(dt_str, "%d.%m.%Y") 
 
                                # Обновляем данные в оригинальной записи внутри списка 
                                r["odometer"] = km 
                                r["date"] = dt_str 
                                r["comment"] = edit_comm.value.strip() 
 
                                engine.save_data(db_data) 
                                edit_dlg.open = False 
                                page.update() 
                                refresh() 
                                rebuild() 
                                show_msg("Запись изменена!") 
                            except: 
                                show_msg("Ошибка формата!") 
 
                        edit_dlg = ft.AlertDialog( 
                            title=ft.Text("Правка записи ТО"), 
                            content=ft.Column([edit_odo, edit_date, edit_comm], tight=True), 
                            actions=[ft.TextButton("Сохранить", on_click=save_edited_rec)] 
                        ) 
                        page.overlay.append(edit_dlg) 
                        edit_dlg.open = True 
                        page.update() 
                    return open_edit_dialog  # ТУТ ИСПРАВЛЕНО: возвращаем правильное имя!
 
                # Отрисовка строки истории с двумя кнопками: Редактировать и Удалить 
                h_col.controls.append(ft.Container( 
                    content=ft.Row([ 
                        ft.Column([ 
                            ft.Row([ft.Text(f"📅 {rec.get('date')}"), ft.Text(f"📍 {rec.get('odometer')} км")]), 
                            ft.Text(rec.get('comment', ""), size=12, color=ft.Colors.GREY_600, italic=True) 
                        ]), 
                        ft.Row([ 
                            ft.IconButton(ft.Icons.EDIT, icon_color=ft.Colors.BLUE_600, icon_size=18, on_click=make_edit()), 
                            ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED_400, icon_size=18, on_click=make_del()) 
                        ], spacing=0) 
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), 
                    padding=6, bgcolor=ft.Colors.GREY_50, border_radius=6 
                )) 
        page.update() 
 
    dlg = ft.AlertDialog( 
        title=ft.Text(f"История: {task_name}"), 
        content=ft.Container(content=h_col, adaptive=True), 
        actions=[ft.TextButton("Закрыть", on_click=lambda _: [setattr(dlg, "open", False), page.update()])]
    ) 
    page.overlay.append(dlg) 
    dlg.open = True 
    refresh() 
 
def show_add_task_history_dialog(page, db_data, t_name, p_profile, rebuild, show_msg):
    h_odo = ft.TextField(label="Пробег")
    h_date = ft.TextField(label="Дата", value=datetime.now().strftime("%d.%m.%Y"))
    
    def save(_):
        try:
            km = int(h_odo.value)
            dt_str = h_date.value.strip()
            datetime.strptime(dt_str, "%d.%m.%Y")
            
            # Наша главная броня от багов сохранения:
            if "history" not in p_profile:
                p_profile["history"] = []
                
            p_profile["history"].append({"task": t_name, "odometer": km, "date": dt_str})
            
            if km > p_profile["maintenance_data"][t_name].get("last_service", 0):
                p_profile["maintenance_data"][t_name].update({"last_service": km, "date": dt_str})
                
            engine.save_data(db_data)
            dlg.open = False
            page.update()
            rebuild()
            show_msg("Добавлено!")
        except Exception as ex:
            show_msg("Ошибка формата!")
            
    dlg = ft.AlertDialog(title=ft.Text("Ввод истории"), content=ft.Column([h_odo, h_date], tight=True), 
                         actions=[ft.TextButton("Сохранить", on_click=save)])
    page.overlay.append(dlg)
    dlg.open = True
    page.update()

def create_task_actions(page, db_data, p, t, current_km, rebuild, show_msg):
    def reset_click(_):
        now = datetime.now().strftime("%d.%m.%Y")
        p["maintenance_data"][t].update({"last_service": current_km, "date": now})
        if "history" not in p: p["history"] = []
        p["history"].append({"task": t, "odometer": current_km, "date": now, "comment": "Быстрый сброс"})
        engine.save_data(db_data); rebuild(); show_msg("ТО отмечено как выполненное!")
        
    def change_click(_):
        n_in = ft.TextField(label="Имя регламента", value=t)
        i_in = ft.TextField(label="Интервал (км)", value=str(p["maintenance_data"][t]["interval"]))
        def save(_):
            try:
                nn = n_in.value.strip(); ni = int(i_in.value)
                if ni <= 0 or not nn: raise ValueError
                old = p["maintenance_data"].pop(t); old["interval"] = ni; p["maintenance_data"][nn] = old
                if nn != t:
                    if "history" not in p: p["history"] = []
                    for h in p.get("history", []):
                        if h["task"] == t: h["task"] = nn
                engine.save_data(db_data); dlg.open = False; page.update(); rebuild(); show_msg("Регламент изменен")
            except: show_msg("Ошибка заполнения")
        dlg = ft.AlertDialog(title=ft.Text("Правка регламента"), content=ft.Column([n_in, i_in], tight=True), actions=[ft.TextButton("OK", on_click=save)])
        page.overlay.append(dlg); dlg.open = True; page.update()
        
    def delete_click(_):
        p["maintenance_data"].pop(t)
        if "history" in p:
            p["history"] = [h for h in p.get("history", []) if h["task"] != t]
        engine.save_data(db_data); rebuild(); show_msg("Регламент полностью удален")
        
    return reset_click, change_click, delete_click

def build_maintenance_list(page, db_data, car_name, car_profile, header_card, rebuild, show_msg, add_task_fn=None):
    c_list = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=10)
    c_list.controls.append(header_card)
    
    status_header = ft.Row([
        ft.Text("Статус регламентных работ:", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_800),
        ft.IconButton(ft.Icons.ADD_CIRCLE, tooltip="Создать новый регламент ТО", icon_color=ft.Colors.BLUE_600, on_click=add_task_fn)
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    c_list.controls.append(ft.Container(content=status_header, padding=ft.Padding.only(left=0, top=10, right=0, bottom=5)))
    
    current_km = car_profile.get("odometer", {}).get("value", 0)
    daily = car_profile.get("daily_mileage", 45)
    tasks = car_profile.get("maintenance_data", {})
    
    if not tasks:
        c_list.controls.append(ft.Container(content=ft.Text("Нет регламентов ТО.", color=ft.Colors.GREY_500), alignment=ft.Alignment.CENTER, padding=20))
        return c_list
        
    for t_name, t_data in tasks.items():
        remains = (t_data.get("last_service", 0) + t_data.get("interval", 0)) - current_km
        f_str = (datetime.now() + timedelta(days=remains/daily)).strftime("%d.%m.%Y") if remains > 0 and daily > 0 else "Срочно ТО!"
        color = ft.Colors.RED_600 if remains <= 0 else (ft.Colors.ORANGE_700 if remains <= 500 else ft.Colors.GREEN_700)
        sub = f"Осталось: {remains} км | Срок: {f_str}"
        
        r_fn, c_fn, d_fn = create_task_actions(page, db_data, car_profile, t_name, current_km, rebuild, show_msg)
        card_bgcolor = "#FFF0F0" if remains <= 0 else ("#FFF9F2" if remains <= 500 else ft.Colors.SURFACE)
        
        item_card = ft.Container(
            bgcolor=card_bgcolor,
            margin=ft.Margin(4, 0, 4, 2),
            padding=ft.Padding(4, 0, 4, 0),
            border_radius=ft.BorderRadius(12, 12, 12, 12),
            shadow=ft.BoxShadow(blur_radius=6, color=ft.Colors.with_opacity(0.04, ft.Colors.BLACK), offset=ft.Offset(0, 2)),
            content=ft.ExpansionTile(
                title=ft.Text(t_name, weight=ft.FontWeight.BOLD, size=14),
                subtitle=ft.Text(sub, color=color, size=12),
                controls=[
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(f"Интервал: {t_data.get('interval')} км", size=13), 
                                ft.Text(f"Прошлый: {t_data.get('last_service')} км", size=13)
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Row([
                                ft.Button("История ТО", icon=ft.Icons.HISTORY, tooltip="Просмотр и удаление истории записей", on_click=lambda e, tn=t_name: show_task_history_dialog(page, db_data, tn, car_profile, rebuild, show_msg)),
                                ft.IconButton(ft.Icons.POST_ADD, tooltip="Внести запись в историю вручную (кастомная дата/пробег)", icon_color=ft.Colors.GREEN_700, on_click=lambda e, tn=t_name: show_add_task_history_dialog(page, db_data, tn, car_profile, rebuild, show_msg)),
                                ft.IconButton(ft.Icons.CHECK_CIRCLE, tooltip="Выполнено сейчас (Быстрый сброс на текущий пробег)", icon_color=ft.Colors.BLUE_600, on_click=r_fn),
                                ft.IconButton(ft.Icons.SETTINGS, tooltip="Настройки (Изменить имя регламента или интервал)", icon_color=ft.Colors.BLUE_GREY_600, on_click=c_fn),
                                ft.IconButton(ft.Icons.DELETE_FOREVER, tooltip="Полностью удалить этот регламент", icon_color=ft.Colors.RED_400, on_click=d_fn)
                            ], alignment=ft.MainAxisAlignment.END)
                        ]), padding=12, bgcolor=ft.Colors.with_opacity(0.4, ft.Colors.SURFACE_CONTAINER_LOW)
                    )
                ]
            )
        )
        c_list.controls.append(item_card)
    return c_list


def show_car_odometer_history_dialog(page, db_data, car_profile, rebuild, show_msg):
    h_cont = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, height=240)
    dlg = None
 
    def render():
        h_cont.controls.clear()
        for item in sorted(car_profile.get("odometer_history", []), key=lambda x: int(x.get("value", 0)), reverse=True):
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
        if dlg: dlg.update()
        else: page.update()
 
    def add_click(_):
        a_km = ft.TextField(label="Пробег")
        a_dt = ft.TextField(label="Дата", value=datetime.now().strftime("%d.%m.%Y"))
 
        def save(_):
            try:
                v = int(a_km.value); d = a_dt.value.strip(); datetime.strptime(d, '%d.%m.%Y')
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
 
    total_count = len(car_profile.get("odometer_history", []))
    dlg = ft.AlertDialog(
        bgcolor=ft.Colors.WHITE,
        title=ft.Text(f"История пробега (записей: {total_count})"),
        content=ft.Column([
            ft.Button("Добавить запись", icon=ft.Icons.ADD, on_click=add_click),
            ft.Divider(height=1, color=ft.Colors.BLACK_12),
            h_cont
        ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=10, tight=True, width=360),
        actions=[ft.TextButton("Закрыть", on_click=lambda _: [setattr(dlg, "open", False), page.update()])]
    )
    page.overlay.append(dlg); dlg.open = True; page.update(); render()


def show_fuel_history_dialog(page, db_data, car_profile, rebuild, show_msg):
    h_col = ft.Column(scroll=ft.ScrollMode.AUTO, height=240, spacing=8)
    dlg = None
 
    def refresh():
        h_col.controls.clear()
        f_hist = car_profile.get("fuel_history", [])
 
        if not f_hist:
            h_col.controls.append(ft.Text("История заправок пуста", italic=True))
        else:
            for rec in sorted(f_hist, key=lambda x: int(x.get("odometer", 0)), reverse=True):
                def make_del(r=rec):
                    return lambda _: [car_profile["fuel_history"].remove(r), engine.save_data(db_data), refresh(), rebuild(), show_msg("Запись удалена")]
 
                def make_edit(r=rec):
                    def open_edit_fuel_dialog(_):
                        e_liters = ft.TextField(label="Количество литров", value=str(r.get("liters", "")))
                        e_cost = ft.TextField(label="Общая сумма (грн)", value=str(r.get("cost", "")))
                        e_odo = ft.TextField(label="Пробег (км)", value=str(r.get("odometer", "")))
                        e_date = ft.TextField(label="Дата", value=str(r.get("date", "")))
                        e_comm = ft.TextField(label="Комментарий", value=str(r.get("comment", "")))
 
                        def save_edited_fuel(_):
                            try:
                                liters = float(e_liters.value)
                                cost = float(e_cost.value)
                                odo = int(e_odo.value)
                                dt_str = e_date.value.strip()
                                datetime.strptime(dt_str, '%d.%m.%Y')
                                if liters <= 0 or cost <= 0 or odo <= 0: raise ValueError
 
                                r["liters"] = liters
                                r["cost"] = cost
                                r["odometer"] = odo
                                r["date"] = dt_str
                                r["comment"] = e_comm.value.strip()
                                r["price"] = round(cost / liters, 2)
 
                                same_type_logs = [log for log in car_profile["fuel_history"] if log.get("type") == r.get("type")]
                                same_type_logs.sort(key=lambda x: int(x.get("odometer", 0)))
 
                                for idx, log in enumerate(same_type_logs):
                                    if idx == 0:
                                        log["consumption"] = 0.0
                                    else:
                                        delta = int(log["odometer"]) - int(same_type_logs[idx-1]["odometer"])
                                        log["consumption"] = round((float(log["liters"]) / delta) * 100, 2) if delta > 0 else 0.0
 
                                engine.save_data(db_data); edit_fuel_dlg.open = False; page.update(); refresh(); rebuild(); show_msg("Заправка успешно изменена!")
                            except:
                                show_msg("Ошибка формата!")
 
                        edit_fuel_dlg = ft.AlertDialog(title=ft.Text("Правка записи заправки"), content=ft.Column([e_liters, e_cost, e_odo, e_date, e_comm], tight=True, spacing=10), actions=[ft.TextButton("Сохранить", on_click=save_edited_fuel)])
                        page.overlay.append(edit_fuel_dlg); edit_fuel_dlg.open = True; page.update()
                    return open_edit_fuel_dialog
 
                cons_text = f" | Расход: {rec.get('consumption')} л/100км" if rec.get("consumption", 0) > 0 else ""
                info_line = f"⛽ {rec.get('type')} | {rec.get('liters')} л | {rec.get('price')} грн/л"
                cost_line = f"💰 Сумма: {rec.get('cost')} грн{cons_text}"
 
                h_col.controls.append(ft.Container(
                    content=ft.Row([
                        ft.Column([
                            ft.Row([ft.Text(f"📅 {rec.get('date')}"), ft.Text(f"📍 {rec.get('odometer')} км", weight=ft.FontWeight.BOLD)]),
                            ft.Text(info_line, size=13),
                            ft.Text(cost_line, size=13, color=ft.Colors.BLUE_GREY_700, weight=ft.FontWeight.W_500),
                            ft.Text(rec.get('comment', ""), size=11, color=ft.Colors.GREY_500, italic=True) if rec.get('comment') else ft.Container()
                        ], spacing=2, expand=True),
                        ft.Row([
                            ft.IconButton(ft.Icons.EDIT, icon_color=ft.Colors.BLUE_600, icon_size=18, on_click=make_edit()),
                            ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED_400, icon_size=18, on_click=make_del())
                        ], spacing=0)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=8, bgcolor=ft.Colors.GREY_50, border_radius=6, border=ft.Border.all(1, ft.Colors.BLACK_12)
                ))
        if dlg: dlg.update()
        else: page.update()
 
    total_count = len(car_profile.get("fuel_history", []))
    dlg = ft.AlertDialog(
        bgcolor=ft.Colors.WHITE,
        title=ft.Text(f"Журнал заправок (чеков: {total_count})"),
        content=ft.Column([
            ft.Divider(height=1, color=ft.Colors.BLACK_12),
            h_col
        ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=10, tight=True, width=380),
        actions=[ft.TextButton("Закрыть", on_click=lambda _: [setattr(dlg, "open", False), page.update()])]
    )
    page.overlay.append(dlg); dlg.open = True; page.update(); refresh()


def show_add_fuel_dialog(page, db_data, car_profile, rebuild, show_msg):
    f_type = ft.RadioGroup(content=ft.Row([
        ft.Radio(value="Бензин", label="Бензин"),
        ft.Radio(value="Газ", label="Газ")
    ], alignment=ft.MainAxisAlignment.SPACE_AROUND), value="Бензин")
    
    in_liters = ft.TextField(label="Количество литров", keyboard_type=ft.KeyboardType.NUMBER)
    in_cost = ft.TextField(label="Общая сумма (грн)", keyboard_type=ft.KeyboardType.NUMBER)
    in_odo = ft.TextField(label="Текущий пробег (км)", keyboard_type=ft.KeyboardType.NUMBER, value=str(car_profile.get("odometer", {}).get("value", "")))
    in_date = ft.TextField(label="Дата заправки", value=datetime.now().strftime("%d.%m.%Y"))
    in_comm = ft.TextField(label="Комментарий (АЗС, марка)", value="БРСМ")

    def save_click(_):
        try:
            liters = float(in_liters.value)
            cost = float(in_cost.value)
            odo = int(in_odo.value)
            dt_str = in_date.value.strip()
            datetime.strptime(dt_str, "%d.%m.%Y")
            
            if liters <= 0 or cost <= 0 or odo <= 0:
                raise ValueError
                
            # Передаем cost вместо price в обновленный метод
            engine.add_fuel_record(car_profile, f_type.value, liters, cost, odo, dt_str, in_comm.value.strip())
            
            if odo >= car_profile["odometer"].get("value", 0):
                car_profile["odometer"] = {"value": odo, "date": dt_str}
                car_profile["daily_mileage"] = engine.recalculate_auto_daily_mileage(car_profile)
                
            engine.save_data(db_data)
            dlg.open = False
            page.update()
            rebuild()
            show_msg("Заправка успешно учтена!")
        except:
            show_msg("Ошибка! Проверьте формат полей.")

    dlg = ft.AlertDialog(
        title=ft.Text("Учёт заправки (до полного)"),
        content=ft.Column([
            ft.Text("Тип топлива:", size=12, color=ft.Colors.GREY_600),
            f_type, in_liters, in_cost, in_odo, in_date, in_comm
        ], tight=True, spacing=10),
        actions=[
            ft.TextButton("Отмена", on_click=lambda _: [setattr(dlg, "open", False), page.update()]),
            ft.ElevatedButton("Сохранить", bgcolor=ft.Colors.AMBER_700, color=ft.Colors.WHITE, on_click=save_click)
        ]
    )
    page.overlay.append(dlg)
    dlg.open = True
    page.update()