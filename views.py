# views.py - Часть 1 из 5
# -*- coding: utf-8 -*-
import flet as ft
import os
from datetime import datetime, timedelta
import engine

def build_action_panel(page, current_db, selected_car, async_mobile_import, async_pc_import, toggle_analytics_click, network, show_message, refresh_callback):
    return ft.Column(
        spacing=5, horizontal_alignment=ft.CrossAxisAlignment.START, 
        controls=[
            ft.Text("База и управление профилями:", size=12, weight=ft.FontWeight.W_500, color=ft.Colors.BLUE_GREY_700), 
            ft.Row(
                scroll=ft.ScrollMode.AUTO, spacing=5, vertical_alignment=ft.CrossAxisAlignment.CENTER, 
                controls=[
                    ft.IconButton(ft.Icons.CLOUD_UPLOAD, tooltip="Экспорт базы в Telegram", on_click=lambda _: network.auto_export_file_to_telegram(page, show_message)), 
                    ft.IconButton(ft.Icons.CLOUD_DOWNLOAD, tooltip="Импорт базы данных", on_click=async_mobile_import if os.name != "nt" else async_pc_import), 
                    ft.IconButton(ft.Icons.BAR_CHART_ROUNDED, tooltip="Аналитика", on_click=toggle_analytics_click), 
                    ft.VerticalDivider(width=10, color=ft.Colors.BLACK_12), 
                    ft.IconButton(ft.Icons.REFRESH, tooltip="Обновить интерфейс", on_click=lambda _: refresh_callback())
                ]
            )
        ]
    )
# views.py - Часть 2 из 5
def build_maintenance_list(page, db_data, car_name, car_profile, header_card, rebuild, show_msg, add_task_fn=None):
    lazy_list = ft.ListView(expand=True, spacing=10, padding=ft.Padding(0, 10, 0, 10))
    
    header_container = ft.Container(content=header_card, width=450, alignment=ft.alignment.Alignment(0, 0))
    lazy_list.controls.append(header_container)
    
    status_header = ft.Row([
        ft.Text("Статус регламентных работ:", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_800),
        ft.IconButton(ft.Icons.ADD_CIRCLE, tooltip="Создать новый регламент ТО", icon_color=ft.Colors.BLUE_600, on_click=add_task_fn)
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, width=450)
    
    lazy_list.controls.append(ft.Container(content=status_header, width=450, alignment=ft.alignment.Alignment(0, 0)))
    
    current_km = car_profile.get("odometer", {}).get("value", 0)
    daily = car_profile.get("daily_mileage", 45)
    tasks = car_profile.get("maintenance_data", {})
    
    if not tasks:
        lazy_list.controls.append(ft.Container(content=ft.Text("Нет регламентов ТО.", color=ft.Colors.GREY_500), alignment=ft.alignment.Alignment(0,0), padding=20))
        return ft.Container(content=lazy_list, expand=True, alignment=ft.alignment.Alignment(0,0))
        
    for t_name, t_data in tasks.items():
        remains = (t_data.get("last_service", 0) + t_data.get("interval", 0)) - current_km
        f_str = (datetime.now() + timedelta(days=remains/daily)).strftime("%d.%m.%Y") if remains > 0 and daily > 0 else "Срочно ТО!"
        color = ft.Colors.RED_600 if remains <= 0 else (ft.Colors.ORANGE_700 if remains <= 500 else ft.Colors.GREEN_700)
        sub = f"Осталось: {remains} км | Срок: {f_str}"
        
        r_fn, c_fn, d_fn = create_task_actions(page, db_data, car_profile, t_name, current_km, rebuild, show_msg)
        card_bgcolor = "#FFF0F0" if remains <= 0 else ("#FFF9F2" if remains <= 500 else ft.Colors.SURFACE)
        
        item_card = ft.Container(
            width=450, bgcolor=card_bgcolor, margin=ft.Margin(4, 0, 4, 2), padding=ft.Padding(4, 0, 4, 0), border_radius=ft.BorderRadius(12, 12, 12, 12),
            shadow=ft.BoxShadow(blur_radius=6, color=ft.Colors.with_opacity(0.04, ft.Colors.BLACK), offset=ft.Offset(0, 2)),
            alignment=ft.alignment.Alignment(0, 0),
            content=ft.ExpansionTile(
                title=ft.Text(t_name, weight=ft.FontWeight.BOLD, size=14), subtitle=ft.Text(sub, color=color, size=12),
                controls=[
                    ft.Container(
                        content=ft.Column([
                            ft.Row([ft.Text(f"Интервал: {t_data.get('interval')} км", size=13), ft.Text(f"Прошлый: {t_data.get('last_service')} км", size=13)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Row([
                                ft.Button("История ТО", icon=ft.Icons.HISTORY, on_click=lambda e, tn=t_name: show_task_history_dialog(page, db_data, tn, car_profile, rebuild, show_msg)),
                                ft.IconButton(ft.Icons.POST_ADD, icon_color=ft.Colors.GREEN_700, on_click=lambda e, tn=t_name: show_add_task_history_dialog(page, db_data, tn, car_profile, rebuild, show_msg)),
                                ft.IconButton(ft.Icons.CHECK_CIRCLE, icon_color=ft.Colors.BLUE_600, on_click=r_fn),
                                ft.IconButton(ft.Icons.SETTINGS, icon_color=ft.Colors.BLUE_GREY_600, on_click=c_fn),
                                ft.IconButton(ft.Icons.DELETE_FOREVER, icon_color=ft.Colors.RED_400, on_click=d_fn)
                            ], alignment=ft.MainAxisAlignment.END)
                        ]), padding=12, bgcolor=ft.Colors.with_opacity(0.4, ft.Colors.SURFACE_CONTAINER_LOW)
                    )
                ]
            )
        )
        lazy_list.controls.append(item_card)
    return ft.Container(content=lazy_list, expand=True, alignment=ft.alignment.Alignment(0, 0))
# views.py - Часть 3 из 5
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
        if "history" in p: p["history"] = [h for h in p.get("history", []) if h["task"] != t]
        engine.save_data(db_data); rebuild(); show_msg("Регламент полностью удален")
    return reset_click, change_click, delete_click

def generate_analytics_view(page, car_profile, header_card):
    view_column = ft.Column(spacing=15, scroll=ft.ScrollMode.AUTO, width=450)
    stats_30 = engine.calculate_fuel_stats(car_profile, days=30)
    cost_per_km = engine.calculate_cost_per_km_brsm(car_profile)
    
    fin_card = ft.Card(content=ft.Container(content=ft.Column([
        ft.Row([ft.Icon(ft.Icons.MONETIZATION_ON, color=ft.Colors.GREEN_700, size=24), ft.Text("Финансовая аналитика (30 дн.)", size=16, weight=ft.FontWeight.BOLD, expand=True)]),
        ft.Divider(height=1, color=ft.Colors.BLACK_12),
        ft.Row([ft.Text(" Топливо:"), ft.Text(f"{stats_30['fuel_spent']} грн", weight=ft.FontWeight.W_600)]),
        ft.Row([ft.Text(" Ремонт и ТО:"), ft.Text(f"{stats_30['maintenance_spent']} грн", weight=ft.FontWeight.W_600)]),
        ft.Row([ft.Text(" Всего затрат:", weight=ft.FontWeight.BOLD), ft.Text(f"{stats_30['total_spent']} грн", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900)]),
        ft.Divider(height=1, color=ft.Colors.BLACK_12),
        ft.Row([ft.Text(" Стоимость 1 км пути:", weight=ft.FontWeight.W_500), ft.Container(content=ft.Text(f"{cost_per_km} грн/км", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), bgcolor=ft.Colors.GREEN_700, padding=ft.Padding(6, 2, 6, 2), border_radius=4)])
    ], spacing=8), padding=14), width=450)
    
    view_column.controls.append(ft.Container(content=header_card, width=450))
    view_column.controls.append(fin_card)
    return ft.Container(content=view_column, expand=True, alignment=ft.alignment.Alignment(0, 0))
# views.py - Часть 4 из 5
def show_task_history_dialog(page, db_data, task_name, car_profile, rebuild, show_msg):
    h_col = ft.Column(scroll=ft.ScrollMode.ALWAYS, height=350, spacing=8)
    def refresh():
        h_col.controls.clear()
        if "history" not in car_profile: car_profile["history"] = []
        t_hist = [h for h in car_profile.get("history", []) if h.get("task") == task_name]
        if not t_hist: h_col.controls.append(ft.Text("Пусто", italic=True))
        else:
            for rec in sorted(t_hist, key=lambda x: int(x.get('odometer', 0)), reverse=True):
                def make_del(r=rec): return lambda _: [car_profile["history"].remove(r), engine.save_data(db_data), refresh(), rebuild(), show_msg("Удалено")]
                h_col.controls.append(ft.Container(content=ft.Row([
                    ft.Column([
                        ft.Row([ft.Icon(ft.Icons.CALENDAR_TODAY, size=14), ft.Text(f"{rec.get('date')}"), ft.Icon(ft.Icons.SPEED, size=14), ft.Text(f"{rec.get('odometer')} км")]),
                        ft.Text(rec.get('comment', ""), size=11, italic=True)
                    ], expand=True),
                    ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED_400, on_click=make_del())
                ]), padding=6, bgcolor=ft.Colors.GREY_50, border_radius=6))
        page.update()
    dlg = ft.AlertDialog(title=ft.Text(f"История: {task_name}"), content=ft.Container(content=h_col, width=450), actions=[ft.TextButton("Закрыть", on_click=lambda _: [setattr(dlg, "open", False), page.update()])])
    page.overlay.append(dlg); dlg.open = True; refresh()

def show_add_task_history_dialog(page, db_data, t_name, p_profile, rebuild, show_msg):
    h_odo = ft.TextField(label="Пробег")
    h_date = ft.TextField(label="Дата", value=datetime.now().strftime("%d.%m.%Y"))
    def save(_):
        try:
            km = int(h_odo.value)
            if "history" not in p_profile: p_profile["history"] = []
            p_profile["history"].append({"task": t_name, "odometer": km, "date": h_date.value.strip(), "comment": "Ручной ввод"})
            if km > p_profile["maintenance_data"][t_name].get("last_service", 0): p_profile["maintenance_data"][t_name].update({"last_service": km, "date": h_date.value.strip()})
            engine.save_data(db_data); dlg.open = False; rebuild(); show_msg("Добавлено!")
        except: show_msg("Ошибка формата!")
    dlg = ft.AlertDialog(title=ft.Text("Ввод истории ремонта"), content=ft.Column([h_odo, h_date], tight=True), actions=[ft.TextButton("Сохранить", on_click=save)])
    page.overlay.append(dlg); dlg.open = True; page.update()
# views.py - Часть 5 из 5
def show_car_odometer_history_dialog(page, db_data, car_profile, rebuild, show_msg):
    h_cont = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, height=240)
    def render():
        h_cont.controls.clear()
        for item in sorted(car_profile.get("odometer_history", []), key=lambda x: int(x.get("value", 0)), reverse=True):
            def make_del(i=item): return lambda _: [car_profile["odometer_history"].remove(i), engine.save_data(db_data), render(), rebuild(), show_msg("Удалено")]
            h_cont.controls.append(ft.Container(content=ft.Row([
                ft.Column([ft.Text(f"{item['value']} км", weight=ft.FontWeight.BOLD), ft.Text(item['date'])]),
                ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED_400, on_click=make_del())
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), padding=5, border=ft.Border.all(1, ft.Colors.BLACK_12), border_radius=6))
        page.update()
    dlg = ft.AlertDialog(title=ft.Text("История пробега"), content=h_cont, actions=[ft.TextButton("Закрыть", on_click=lambda _: [setattr(dlg, "open", False), page.update()])])
    page.overlay.append(dlg); dlg.open = True; render()

def show_fuel_history_dialog(page, db_data, car_profile, rebuild, show_msg):
    h_col = ft.Column(scroll=ft.ScrollMode.ALWAYS, height=350, spacing=8)
    def refresh():
        h_col.controls.clear()
        f_hist = car_profile.get("fuel_history", [])
        if not f_hist: h_col.controls.append(ft.Text("История пуста", italic=True))
        else:
            for rec in sorted(f_hist, key=lambda x: int(x.get("odometer", 0)), reverse=True):
                h_col.controls.append(ft.Text(f"{rec.get('date')} | {rec.get('odometer')} км | {rec.get('cost')} грн"))
        page.update()
    dlg = ft.AlertDialog(title=ft.Text("Журнал расходов"), content=ft.Container(content=h_col, width=450), actions=[ft.TextButton("Закрыть", on_click=lambda _: [setattr(dlg, "open", False), page.update()])])
    page.overlay.append(dlg); dlg.open = True; refresh()

def show_repair_history_dialog(page, db_data, car_profile, rebuild, show_msg):
    h_col = ft.Column(scroll=ft.ScrollMode.ALWAYS, height=350, spacing=8)
    dlg = ft.AlertDialog(title=ft.Text("Журнал ремонтов"), content=ft.Container(content=h_col, width=450), actions=[ft.TextButton("Закрыть", on_click=lambda _: [setattr(dlg, "open", False), page.update()])])
    page.overlay.append(dlg); dlg.open = True
