import flet as ft
from datetime import datetime, timedelta
import engine

def generate_analytics_view(page, car_profile):
    view_column = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=15)
    current_km = car_profile.get("odometer", {}).get("value", 0)
    tasks = car_profile.get("maintenance_data", {})
    
    stats_30 = engine.calculate_fuel_stats(car_profile, days=30) if hasattr(engine, 'calculate_fuel_stats') else {"total_spend": 0, "avg_consumption": 0}
    cost_per_km = engine.calculate_cost_per_km_brsm(car_profile) if hasattr(engine, 'calculate_cost_per_km_brsm') else 0.0
    
    fin_card = ft.Card(
        content=ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.MONETIZATION_ON, color=ft.Colors.GREEN_700, size=24),
                    ft.Text("Финансовая аналитика (30 дн.)", size=16, weight=ft.FontWeight.BOLD)
                ], spacing=8),
                ft.Divider(height=1, color=ft.Colors.BLACK_12),
                ft.Text(f"Общие расходы на топливо: {stats_30.get('total_spend', 0)} ₽", size=14),
                ft.Text(f"Себестоимость км (БРСМ/ГБО): {cost_per_km:.2f} ₽/км", size=14, weight=ft.FontWeight.W_500),
            ], spacing=10), padding=15
        )
    )
    view_column.controls.append(fin_card)
    return view_column

def build_maintenance_list(page, current_db, selected_car, car_profile, header_card, rebuild_ui, show_message):
    scroll_column = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=10)
    scroll_column.controls.append(header_card)
    return scroll_column


def show_add_car_dialog(page, current_db, refresh_callback):
    car_name_input = ft.TextField(label="Марка / Модель")
    def save_new_car(_):
        name = car_name_input.value.strip()
        if not name or name in current_db["cars"]: return
        current_db["cars"][name] = {"odometer": {"value": 0, "date": datetime.now().strftime("%d.%m.%Y")},
        "daily_mileage": 0, "odometer_history": [], "maintenance_data": {}, "history": []}
        engine.save_data(current_db)
        engine.app_state["selected_car"] = name
        dialog.open = False
        page.update()
        refresh_callback()
    dialog = ft.AlertDialog(title=ft.Text("Добавить автомобиль"), content=ft.Column([car_name_input], tight=True),
    actions=[ft.TextButton("Добавить", on_click=save_new_car)])
    page.overlay.append(dialog)
    dialog.open = True
    page.update()

def show_edit_car_name_dialog(page, current_db, selected_car, refresh_callback):
    edit_name_input = ft.TextField(label="Новое имя профиля", value=selected_car)
    def save_name_change(_):
        new_name = edit_name_input.value.strip()
        success_rename, rename_msg = engine.rename_car_profile(current_db, selected_car, new_name)
        if not success_rename:
            if hasattr(page, "snack_bar"):
                page.snack_bar = ft.SnackBar(ft.Text(rename_msg), open=True)
                page.update()
            return
        engine.app_state["selected_car"] = new_name
        dialog.open = False
        page.update()
        refresh_callback()
    dialog = ft.AlertDialog(title=ft.Text("Редактировать имя"), content=ft.Column([edit_name_input], tight=True),
    actions=[ft.TextButton("Сохранить", on_click=save_name_change)])
    page.overlay.append(dialog)
    dialog.open = True
    page.update()

def show_delete_car_dialog(page, current_db, selected_car, refresh_callback):
    if len(current_db["cars"]) <= 1: return
    def confirm_delete(_):
        current_db["cars"].pop(selected_car)
        engine.save_data(current_db)
        engine.app_state["selected_car"] = list(current_db["cars"].keys())[0]
        dialog.open = False
        page.update()
        refresh_callback()
    dialog = ft.AlertDialog(title=ft.Text("Удаление профиля"), content=ft.Text(f"Удалить '{selected_car}'?"),
    actions=[ft.TextButton("Удалить", on_click=confirm_delete, style=ft.ButtonStyle(color=ft.Colors.RED_600))])
    page.overlay.append(dialog)
    dialog.open = True
    page.update()

def build_action_panel(page, current_db, selected_car, async_mobile_import, async_pc_import, toggle_analytics_click, network, show_message, refresh_callback):
    import flet as ft
    import os
    
    def on_analytics_click(e):
        current_mode = engine.app_state.get('view_mode', 'list')
        new_mode = 'analytics' if current_mode != 'analytics' else 'list'
        engine.app_state.update({'view_mode': new_mode})
        
        # Безопасный кроссплатформенный запуск асинхронного обновления экрана
        if hasattr(page, "run_task"):
            page.run_task(page.data["refresh_ui"])
        else:
            refresh_callback()

    analytics_btn = ft.IconButton(
        ft.Icons.BAR_CHART_ROUNDED, 
        tooltip="Аналитика", 
        on_click=on_analytics_click
    )
    
    return ft.Column(
        spacing=5,
        horizontal_alignment=ft.CrossAxisAlignment.START,
        controls=[
            ft.Text("База и управление профилями:", size=12, weight=ft.FontWeight.W_500, color=ft.Colors.BLUE_GREY_700),
            ft.Row(
                scroll=ft.ScrollMode.AUTO,
                spacing=5,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.IconButton(
                        ft.Icons.CLOUD_UPLOAD, 
                        tooltip="Экспорт базы в Telegram",
                        on_click=lambda _: network.auto_export_file_to_telegram(page, show_message)
                    ),
                    ft.IconButton(
                        ft.Icons.CLOUD_DOWNLOAD, 
                        tooltip="Импорт базы данных", 
                        on_click=lambda _: [
                            show_message("🔄 Запрос к API Telegram..."),
                            page.run_task(async_mobile_import)
                        ] if os.name != "nt" else [
                            page.run_task(async_pc_import)
                        ]
                    ),
                    analytics_btn,
                    ft.VerticalDivider(width=10, color=ft.Colors.BLACK_12),
                    ft.IconButton(ft.Icons.ADD_CIRCLE, tooltip="Добавить авто", on_click=lambda _: show_add_car_dialog(page, current_db, refresh_callback)),
                    ft.IconButton(icon=ft.Icons.EDIT, tooltip="Переименовать авто", on_click=lambda _: show_edit_car_name_dialog(page, current_db, selected_car, refresh_callback)),
                    ft.IconButton(ft.Icons.DELETE_FOREVER, tooltip="Удалить авто", on_click=lambda _: show_delete_car_dialog(page, current_db, selected_car, refresh_callback), icon_color=ft.Colors.RED_500),
                ]
            )
        ]
    )


# --- БЛОК УЧЕТА РАСХОДОВ, ЗАПРАВОК И РЕМОНТОВ (РЕФАКТОРИНГ) ---

def show_add_fuel_dialog(page, current_db, car_profile, refresh_callback, show_message):
    import flet as ft
    from datetime import datetime
    import engine
    liters_input = ft.TextField(label="Количество литров (газ/бензин)", keyboard_type=ft.KeyboardType.NUMBER)
    price_input = ft.TextField(label="Стоимость за литр (₽)", keyboard_type=ft.KeyboardType.NUMBER)
    odo_input = ft.TextField(label="Текущий пробег при заправке (км)", keyboard_type=ft.KeyboardType.NUMBER)
    
    def save_fuel_click(_):
        try:
            liters = float(liters_input.value.strip())
            price = float(price_input.value.strip())
            odo = int(odo_input.value.strip())
            
            if "fuel_history" not in car_profile:
                car_profile["fuel_history"] = []
                
            car_profile["fuel_history"].append({
                "date": datetime.now().strftime("%d.%m.%Y"),
                "liters": liters,
                "price": price,
                "odometer": odo
            })
            
            engine.save_data(current_db)
            dialog.open = False
            page.update()
            show_message("✅ Заправка успешно учтена!")
            refresh_callback()
        except Exception as err:
            show_message(f"❌ Ошибка ввода: {str(err)}")
            
    dialog = ft.AlertDialog(
        title=ft.Text("Заправить автомобиль"),
        content=ft.Column([liters_input, price_input, odo_input], tight=True, spacing=10),
        actions=[ft.TextButton("Сохранить", on_click=save_fuel_click)]
    )
    page.overlay.append(dialog)
    dialog.open = True
    page.update()

def show_fuel_history_dialog(page, current_db, car_profile, refresh_callback, show_message):
    import flet as ft
    history_list = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO, height=300)
    fuel_records = car_profile.get("fuel_history", [])
    
    if not fuel_records:
        history_list.controls.append(ft.Text("Журнал заправок пуст", italic=True))
    else:
        for rec in reversed(fuel_records):
            history_list.controls.append(
                ft.Text(f"📅 {rec.get('date')} | {rec.get('liters')} л | {rec.get('price')} ₽/л | 🚗 {rec.get('odometer')} км", size=13)
            )
            
    dialog = ft.AlertDialog(
        title=ft.Text("Журнал заправок (ГБО/Бензин)"),
        content=ft.Container(content=history_list, width=400),
        actions=[ft.TextButton("Закрыть", on_click=lambda _: [setattr(dialog, 'open', False), page.update()])]
    )
    page.overlay.append(dialog)
    dialog.open = True
    page.update()

def show_repair_history_dialog(page, current_db, car_profile, refresh_callback, show_message):
    import flet as ft
    repair_list = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO, height=300)
    history_records = car_profile.get("history", [])
    
    if not history_records:
        repair_list.controls.append(ft.Text("Журнал ремонтов пуст", italic=True))
    else:
        for rec in reversed(history_records):
            repair_list.controls.append(
                ft.Text(f"🛠️ {rec.get('date')} | {rec.get('task')} | 🚗 {rec.get('odometer')} км", size=13)
            )
            
    dialog = ft.AlertDialog(
        title=ft.Text("Журнал ремонтов и обслуживания"),
        content=ft.Container(content=repair_list, width=400),
        actions=[ft.TextButton("Закрыть", on_click=lambda _: [setattr(dialog, 'open', False), page.update()])]
    )
    page.overlay.append(dialog)
    dialog.open = True
    page.update()

def show_car_odometer_history_dialog(page, current_db, car_profile, refresh_callback, show_message):
    import flet as ft
    odo_list = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO, height=300)
    history_records = car_profile.get("odometer_history", [])
    
    if not history_records:
        odo_list.controls.append(ft.Text("История пробега пуста", italic=True))
    else:
        for rec in reversed(history_records):
            odo_list.controls.append(
                ft.Text(f"📈 Пробег: {rec.get('value')} км ({rec.get('date')})", size=13)
            )
            
    dialog = ft.AlertDialog(
        title=ft.Text("История изменения пробега"),
        content=ft.Container(content=odo_list, width=400),
        actions=[ft.TextButton("Закрыть", on_click=lambda _: [setattr(dialog, 'open', False), page.update()])]
    )
    page.overlay.append(dialog)
    dialog.open = True
    page.update()
