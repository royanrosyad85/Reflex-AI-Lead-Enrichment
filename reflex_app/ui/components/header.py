import reflex as rx
from reflex.style import color_mode, set_color_mode


def dark_mode_toggle() -> rx.Component:
    return rx.segmented_control.root(
        rx.segmented_control.item(rx.icon(tag="sun", size=20), value="light"),
        rx.segmented_control.item(rx.icon(tag="moon", size=20), value="dark"),
        on_change=lambda val: set_color_mode(val),
        variant="classic",
        radius="large",
        value=color_mode,
    )


def project_header() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.image(
                src="/zurich-logo-update.png",
                alt="Zurich Logo",
                height="30px",
                width="auto",
            ),
            rx.spacer(),
            dark_mode_toggle(),
            width="100%",
            align_items="center",
        ),
        width="100%",
        background=rx.color("gray", 1),
        padding_x=["1rem", "1.5rem", "2rem"],
        padding_y="0.7rem",
    )
