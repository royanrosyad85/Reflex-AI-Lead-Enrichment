from typing import Any, cast

import reflex as rx
from reflex.style import color_mode, set_color_mode

from ...state import State


def dark_mode_toggle() -> rx.Component:
    return rx.segmented_control.root(
        rx.segmented_control.item(rx.icon(tag="sun", size=20), value="light"),
        rx.segmented_control.item(rx.icon(tag="moon", size=20), value="dark"),
        on_change=lambda val: set_color_mode(val),
        variant="classic",
        radius="large",
        value=color_mode,
    )


def reposition_controls() -> rx.Component:
    return rx.cond(
        State.header_reposition_mode,
        rx.hstack(
            rx.slider(
                min=0,
                max=100,
                value=[State.temp_header_position],
                on_change=cast(Any, State.set_temp_header_position),
                width="140px",
                size="1",
                variant="surface",
                class_name="header-reposition-slider",
                style={"border_radius": "8px"},
            ),
            rx.button(
                "Done",
                on_click=cast(Any, State.save_reposition),
                variant="solid",
                size="1",
                font_size="12px",
                font_weight="600",
                letter_spacing="0.01em",
                height="30px",
                min_width="62px",
                padding_x="14px",
                border_radius="8px",
                background="#F1F5F9",
                color="#0F172A",
                border="1px solid #E2E8F0",
                box_shadow=rx.color_mode_cond(
                    light="0 1px 1px rgba(15,23,42,0.16)",
                    dark="0 1px 1px rgba(15,23,42,0.18)",
                ),
                _hover={
                    "background": "#FFFFFF",
                    "transform": "translateY(-1px)",
                },
                transition="background 160ms ease, transform 160ms ease",
            ),
            spacing="2",
            align="center",
            position="absolute",
            top="0.75rem",
            right="0.75rem",
            z_index="10",
            padding="8px 10px",
            border_radius="14px",
            class_name="header-reposition-panel",
            display=["none", "none", "flex"],
        ),
        rx.cond(
            State.header_hovered,
            rx.box(
                    rx.button(
                        rx.hstack(
                            rx.icon("move", size=14),
                            rx.text("Reposition", size="1"),
                            align="center",
                            spacing="1",
                        ),
                        on_click=cast(Any, State.enter_reposition_mode),
                        variant="ghost",
                        color_scheme="gray",
                        size="1",
                        font_size="11px",
                        height="24px",
                        padding_x="8px",
                        border_radius="10px",
                        opacity="0",
                        transform="translateY(-4px)",
                        animation="reposition-fade-in 180ms ease forwards",
                        transition="transform 220ms cubic-bezier(0.22, 1, 0.36, 1)",
                        background=rx.color("gray", 1),
                        border=f"1px solid {rx.color('gray', 4)}",
                        _hover={"transform": "translateY(-1px)"},
                    ),
                position="absolute",
                top="1.3rem",
                right="1.5rem",
                z_index="10",
                display=["none", "none", "block"],
            ),
            rx.fragment(),
        ),
    )


def project_header() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.image(
                    src="/zurich-logo-update.png",
                    alt="Zurich Logo",
                    height="30px",
                    width="auto",
                    filter=rx.color_mode_cond(
                        light="none",
                        dark="brightness(0) invert(1)",
                    ),
                ),
                rx.spacer(),
                dark_mode_toggle(),
                width="100%",
                align_items="center",
                padding_x=["1rem", "1.5rem", "2rem"],
                padding_y="0.7rem",
                background=rx.color("gray", 1),
                border_bottom=f"1px solid {rx.color('gray', 4)}",
            ),
            rx.box(
                # Image container with drag events
                rx.box(
                    rx.image(
                        src="/Zurich%20Header.png",
                        alt="Zurich building header",
                        width="100%",
                        height="100%",
                        object_fit="cover",
                        object_position=f"center {State.temp_header_position}%",
                        style={
                            "user_select": "none",
                            "pointer_events": "none",  # Prevent default image dragging behavior
                        },
                    ),
                    width="100%",
                    height="100%",
                    cursor=rx.cond(State.header_reposition_mode, "ns-resize", "default"),
                ),
                reposition_controls(),
                on_mouse_enter=cast(Any, State.set_header_hovered)(True),
                on_mouse_leave=cast(Any, State.set_header_hovered)(False),
                width="100%",
                height=["110px", "140px", "180px"],
                overflow="hidden",
                border_bottom=f"1px solid {rx.color('gray', 4)}",
                position="relative",
            ),
            width="100%",
            spacing="0",
            align_items="stretch",
        ),
        width="100%",
        background=rx.color("gray", 1),
    )
