# Фрагмент №12: Панель пробега автомобиля и создание карточки вида

def generate_car_view(
    page,
    db_data,
    car_name,
    car_profile,
    show_message,
    rebuild_callback,
):
    """Генерация основного экрана автомобиля."""
    odo_data = car_profile.get(
        "odometer", {"value": 125000, "date": "—"}
    )
    lbl_odo = (
        f"Пробег (км) [от {odo_data.get('date', '—')}]"
    )

    current_odo_input = ft.TextField(
        label=lbl_odo,
        value=str(odo_data.get("value", 125000)),
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
    )
    daily_input = ft.TextField(
        label="Пробег в день (км)",
        value=str(car_profile.get("daily_mileage", 45)),
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
    )

    def execute_custom_export(full_path):
        try:
            with open(
                full_path, "w", encoding="utf-8"
            ) as f:
                json.dump(
                    db_data,
                    f,
                    ensure_ascii=False,
                    indent=4,
                )
            show_message("Экспорт завершен!")
        except Exception as ex:
            show_message(f"Ошибка экспорта: {ex}")

    def execute_custom_import(full_path):
        try:
            with open(
                full_path, "r", encoding="utf-8"
            ) as f:
                imported_json = json.load(f)
                if "cars" in imported_json:
                    save_data(imported_json)
                    rebuild_callback()
                    show_message("База импортирована!")
                else:
                    show_message("Неверный формат!")
        except Exception as ex:
            show_message(f"Ошибка импорта: {ex}")

    def update_forecast_click(e):
        try:
            val = int(current_odo_input.value)
            now_str = datetime.now().strftime(
                "%d.%m.%Y"
            )
            car_profile["odometer"] = {
                "value": val,
                "date": now_str,
            }
            car_profile["daily_mileage"] = int(
                daily_input.value
            )
            h_list = car_profile["odometer_history"]

            if not any(
                h["value"] == val for h in h_list
            ):
                h_list.append(
                    {"value": val, "date": now_str}
                )

            car_profile[
                "daily_mileage"
            ] = recalculate_auto_daily_mileage(
                car_profile
            )
            save_data(db_data)
            rebuild_callback()
            show_message("Данные обновлены!")
        except ValueError:
            show_message("Ошибка: Проверьте поля!")

    def add_custom_task_click(e):
        t_title = ft.TextField(label="Название")
        t_int = ft.TextField(
            label="Интервал", value="10000"
        )

        def save_custom_task(_):
            title = t_title.value.strip()
            m_data = car_profile["maintenance_data"]
            if not title or title in m_data:
                return
            try:
                km = int(current_odo_input.value)
                now_date = datetime.now().strftime(
                    "%d.%m.%Y"
                )
                
                m_data[title] = {
                    "last_service": km,
                    "interval": int(t_int.value),
                    "date": now_date,
                }
                
                car_profile["history"].append(
                    {
                        "task": title,
                        "odometer": km,
                        "date": now_date
                    }
                )
                
                save_data(db_data)
                dlg.open = False
                page.update()
                rebuild_callback()
            except ValueError:
                pass

        dlg = ft.AlertDialog(
            title=ft.Text("Добавить свою работу"),
            content=ft.Column(
                [t_title, t_int], tight=True
            ),
            actions=[
                ft.TextButton(
                    "Сохранить",
                    on_click=save_custom_task,
                )
            ],
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    act_fns = setup_car_profile_actions(
        page,
        db_data,
        car_name,
        show_message,
        rebuild_callback,
    )
    add_car_fn, edit_car_fn, del_car_fn = act_fns

    def open_export(_):
        show_custom_file_manager_dialog(
            page,
            "export",
            execute_custom_export,
            show_message,
        )

    def open_import(_):
        show_custom_file_manager_dialog(
            page,
            "import",
            execute_custom_import,
            show_message,
        )

    def open_odo_hist(_):
        show_car_odometer_history_dialog(
            page,
            db_data,
            car_profile,
            rebuild_callback,
            show_message,
        )

    action_panel = ft.Row(
        [
            ft.Row(
                [
                    ft.Text(
                        "База:",
                        size=14,
                        weight=ft.FontWeight.W_500,
                    ),
                    ft.IconButton(
                        ft.Icons.CLOUD_UPLOAD,
                        icon_color=ft.Colors.BLUE_600,
                        on_click=open_export,
                    ),
                    ft.IconButton(
                        ft.Icons.CLOUD_DOWNLOAD,
                        icon_color=ft.Colors.GREEN_600,
                        on_click=open_import,
                    ),
                ],
                spacing=2,
            ),
            ft.Row(
                [
                    ft.IconButton(
                        ft.Icons.ADD_CIRCLE,
                        on_click=add_car_fn,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.EDIT,
                        on_click=edit_car_fn,
                    ),
                    ft.IconButton(
                        ft.Icons.DELETE_FOREVER,
                        icon_color=ft.Colors.RED_500,
                        on_click=del_car_fn,
                    ),
                    ft.Container(width=40),
                ],
                spacing=2,
            ),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    header_card = ft.Card(
        content=ft.Container(
            content=ft.Column(
                [
                    action_panel,
                    ft.Divider(
                        height=5,
                        color=ft.Colors.BLACK_12,
                    ),
                    ft.Text(
                        "Обновление данных пробега",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Row(
                        [
                            current_odo_input,
                            daily_input,
                        ],
                        vertical_alignment=(
                            ft.CrossAxisAlignment.CENTER
                        ),
                        spacing=8,
                    ),
                    ft.Row(
                        [
                            ft.Button(
                                "Обновить",
                                on_click=(
                                    update_forecast_click
                                ),
                                height=45,
                            ),
                            ft.OutlinedButton(
                                "📖 История пробега",
                                icon=ft.Icons.HISTORY,
                                height=45,
                                on_click=open_odo_hist,
                            ),
                        ],
                        alignment=(
                            ft.MainAxisAlignment.CENTER
                        ),
                        spacing=10,
                    ),
                ],
                spacing=12,
            ),
            padding=12,
        )
    )

    # НАСТРОЕНА ПЕРЕДАЧА ФУНКЦИИ add_custom_task_click В СЛЕДУЮЩИЙ БЛОК
    return build_maintenance_list(
        page,
        db_data,
        car_name,
        car_profile,
        header_card,
        rebuild_callback,
        show_message,
        add_custom_task_click,
    )
