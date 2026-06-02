# Фрагмент №13: Точка входа приложения (Main)

def main(page: ft.Page):
    """Главная функция интерфейса."""
    page.title = "Журнал ТО автомобиля"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = ft.ScrollMode.AUTO

    def show_message(text):
        snack = ft.SnackBar(ft.Text(text))
        page.overlay.append(snack)
        snack.open = True
        page.update()

    def build_tabs_ui():
        page.controls.clear()
        db_data = load_data()
        cars_dict = db_data.get("cars", {})
        tab_buttons = []
        tab_contents = []

        for car_name, car_profile in cars_dict.items():
            car_view_content = generate_car_view(
                page,
                db_data,
                car_name,
                car_profile,
                show_message,
                build_tabs_ui,
            )
            tab_buttons.append(
                ft.Tab(
                    label=car_name,
                    icon=ft.Icons.DIRECTIONS_CAR,
                )
            )
            tab_contents.append(car_view_content)

        tabs_layout = ft.Column(
            controls=[
                ft.TabBar(tabs=tab_buttons),
                ft.TabBarView(
                    controls=tab_contents,
                    expand=True,
                ),
            ],
            expand=True,
        )

        tabs_container = ft.Tabs(
            length=len(tab_buttons),
            selected_index=0,
            animation_duration=300,
            content=tabs_layout,
            expand=True,
        )
        page.add(tabs_container)
        page.update()

    build_tabs_ui()


if __name__ == "__main__":
    ft.run(main)
