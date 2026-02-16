from typing import cast

import reflex as rx

from ..state import State
from .components.header import project_header
from .components.overlay import render_enrichment_overlay
from .components.table import table_header_cell, table_row


def main_content() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.vstack(
                rx.heading("👾 ZGTI AI Lead Enrichment", size="7", text_align="left"),
                rx.text(
                    "Company Enrichment Tool - Automates company profile enrichment using AI agents. Powered by LangGraph & Tavily.",
                    size="3",
                    weight="medium",
                    text_align="left",
                    color=rx.color("gray", 11),
                ),
                spacing="3",
                width="100%",
                align_items="start",
            ),
            rx.cond(
                State.undo_visible,
                rx.hstack(
                    rx.text("Logs cleared.", size="1", weight="medium"),
                    rx.spacer(),
                    rx.button(
                        State.undo_button_label,
                        on_click=cast(rx.EventHandler[[]], State.undo_clear_search),
                        size="1",
                        variant="surface",
                        cursor="pointer",
                    ),
                    width="100%",
                    padding="8px",
                    border_radius="8px",
                    border=f"1px solid {rx.color('blue', 6)}",
                    background=rx.color("blue", 2),
                    role="status",
                    aria_live="polite",
                ),
                rx.fragment(),
            ),
            rx.cond(
                State.is_processing,
                rx.box(
                    rx.text(State.status_log, size="2", margin_bottom="0.5rem"),
                    rx.progress(value=State.progress, width="100%"),
                    width="100%",
                    padding_y="0.75rem",
                ),
                rx.fragment(),
            ),
            rx.box(
                rx.hstack(
                    rx.button(
                        "View Last Log",
                        on_click=cast(rx.EventHandler[[]], State.reopen_last_enrichment_log),
                        variant="ghost",
                        size="2",
                        cursor="pointer",
                        color_scheme="blue",
                    ),
                    rx.button(
                        "Reset Session",
                        on_click=cast(rx.EventHandler[[]], State.reset_session_state),
                        variant="soft",
                        color_scheme="gray",
                        size="2",
                        cursor="pointer",
                        disabled=State.is_processing,
                    ),
                    rx.spacer(),
                    rx.hstack(
                        rx.tooltip(
                            rx.image(
                                src="/excel_icon.svg",
                                alt="Export Excel",
                                width="22px",
                                height="22px",
                                cursor="pointer",
                                on_click=cast(rx.EventHandler[[]], State.export_excel),
                                _hover={
                                    "transform": "scale(1.1)",
                                    "opacity": "0.8",
                                },
                                transition="all 0.2s ease",
                            ),
                            content="Export to Excel",
                            side="bottom",
                        ),
                        rx.tooltip(
                            rx.image(
                                src="/pdf_icon.svg",
                                alt="Export PDF",
                                width="22px",
                                height="22px",
                                cursor="pointer",
                                on_click=cast(rx.EventHandler[[]], State.export_pdf),
                                _hover={
                                    "transform": "scale(1.1)",
                                    "opacity": "0.8",
                                },
                                transition="all 0.2s ease",
                            ),
                            content="Export to PDF",
                            side="bottom",
                        ),
                        spacing="4",
                        align_items="center",
                        padding_right="0.5rem",
                    ),
                    width="100%",
                    padding="8px 8px 10px 8px",
                    align_items="center",
                ),
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell(
                                rx.text(""),
                                aria_label="Row actions",
                                style={"width": "56px", "min-width": "56px"},
                            ),
                            table_header_cell("Company Name"),
                            table_header_cell("Sector"),
                            table_header_cell("Address"),
                            table_header_cell("Contact Info"),
                            table_header_cell("Insurance Potential"),
                            table_header_cell("Employee Count"),
                            table_header_cell("Description"),
                            table_header_cell("Branches"),
                            table_header_cell("Company PIC"),
                            table_header_cell("Financial Report"),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            State.companies,
                            lambda company, i: table_row(company, i),
                        ),
                    ),
                    width="100%",
                    variant="surface",
                ),
                overflow_x="auto",
                width="100%",
                background=rx.color("gray", 1),
            ),
            rx.hstack(
                rx.button(
                    rx.hstack(rx.icon(tag="plus", size=14), rx.text("Add Row"), spacing="2", align_items="center"),
                    on_click=cast(rx.EventHandler[[]], State.add_row),
                    size="2",
                    cursor="pointer",
                    disabled=State.is_processing,
                    background="#1E4E8C",
                    color="white",
                    _hover={"background": "#173F72"},
                ),
                rx.button(
                    "Enrich Data",
                    on_click=cast(rx.EventHandler[[]], State.run_enrichment),
                    loading=State.is_processing,
                    size="2",
                    cursor="pointer",
                    background="#1E4E8C",
                    color="white",
                    _hover={"background": "#173F72"},
                ),
                width="100%",
                spacing="2",
                align_items="center",
                padding_top="0.25rem",
            ),
            align_items="start",
            width="100%",
            padding_x=["1rem", "1.5rem", "2rem"],
            padding_top="50px",
            padding_bottom="1.5rem",
            spacing="4",
        ),
        width="100%",
    )


def index() -> rx.Component:
    return rx.box(
        rx.vstack(
            project_header(),
            main_content(),
            width="100%",
            align_items="stretch",
            spacing="0",
        ),
        render_enrichment_overlay(),
        width="100%",
        min_height="100vh",
        background=rx.color("gray", 1),
    )
