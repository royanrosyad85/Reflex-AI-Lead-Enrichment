import reflex as rx
from typing import cast, Any
from reflex.style import set_color_mode, color_mode
from .state import State


def dark_mode_toggle() -> rx.Component:
    return rx.segmented_control.root(
        rx.segmented_control.item(rx.icon(tag="sun", size=20), value="light"),
        rx.segmented_control.item(rx.icon(tag="moon", size=20), value="dark"),
        on_change=lambda val: set_color_mode(val),
        variant="classic",
        radius="large",
        value=color_mode,
    )


def sidebar():
    return rx.cond(
        State.sidebar_open,
        rx.box(
            rx.vstack(
                rx.heading("Project Overview", size="5", margin_bottom="1rem"),
                rx.text(
                    "Agentic LangGraph Researcher",
                    weight="bold",
                    margin_bottom="0.5rem",
                ),
                rx.text(
                    "This tool automates the process of enriching company profiles using AI agents.",
                    size="2",
                    margin_bottom="1rem",
                ),
                rx.divider(margin_y="1rem"),
                rx.text("Powered by LangGraph & Tavily", size="1"),
                align_items="start",
            ),
            padding="2rem",
            height="100vh",
            width="300px",
            display=["none", "none", "block"],
        ),
        rx.box(width="0"),  
    )


def table_header_cell(text: str):
    return rx.table.column_header_cell(
        rx.text(text, weight="bold", size="2"),
    )


def _name_change_handler(index: int):
    return lambda val: cast(Any, State.update_company_name)(val, index)


def table_row(company: dict, index: int):
    return rx.table.row(
        rx.table.cell(
            rx.input(
                value=company["Nama Perusahaan"],
                on_change=_name_change_handler(index),
                placeholder="Enter company name...",
                width="100%",
                style={
                    "word-break": "break-word",
                    "white-space": "normal",
                    "overflow-wrap": "anywhere",
                    "min-height": "44px",
                    "hyphens": "auto",
                    "line-height": "1.4",
                },
            ),
            style={"width": "250px", "min-width": "175px", "vertical-align": "top"},
        ),
        rx.table.cell(rx.text(company["Sektor Perusahaan"], size="2", style={"word-break": "break-word", "white-space": "normal", "overflow-wrap": "break-word"}), style={"min-width": "150px", "vertical-align": "top"}),
        rx.table.cell(rx.text(company["Alamat"], size="2", style={"word-break": "break-word", "white-space": "normal", "overflow-wrap": "break-word"}), style={"min-width": "200px", "vertical-align": "top"}),
        rx.table.cell(rx.text(company["Kontak"], size="2", style={"word-break": "break-word", "white-space": "normal", "overflow-wrap": "break-word"}), style={"min-width": "150px", "vertical-align": "top"}),
        rx.table.cell(rx.text(company["Potensi Polis"], size="2", style={"word-break": "break-word", "white-space": "normal", "overflow-wrap": "break-word"}), style={"min-width": "150px", "vertical-align": "top"}),
        rx.table.cell(rx.text(company["Jumlah Karyawan"], size="2", style={"word-break": "break-word", "white-space": "normal", "overflow-wrap": "break-word"}), style={"min-width": "150px", "vertical-align": "top"}),
        rx.table.cell(rx.text(company["Short Description"], size="2", style={"word-break": "break-word", "white-space": "normal", "overflow-wrap": "break-word"}), style={"min-width": "300px", "vertical-align": "top"}),
        rx.table.cell(rx.text(company["Kantor Cabang"], size="2", style={"word-break": "break-word", "white-space": "normal", "overflow-wrap": "break-word"}), style={"min-width": "200px", "vertical-align": "top"}),
        rx.table.cell(rx.text(company["PIC Perusahaan"], size="2", style={"word-break": "break-word", "white-space": "normal", "overflow-wrap": "anywhere"}), style={"min-width": "150px", "vertical-align": "top"}),
        rx.table.cell(rx.text(company["Laporan Keuangan"], size="2", style={"word-break": "break-word", "white-space": "normal", "overflow-wrap": "break-word"}), style={"min-width": "200px", "vertical-align": "top"}),
    )


def main_content():
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.heading("👾 Lead Enrichment ZGTI", size="7"),
                rx.spacer(),
                dark_mode_toggle(),
                width="100%",
                align_items="center",
            ),
            rx.text("Input company names below to automatically enrich their profiles."),

            # Action Bar
            rx.hstack(
                rx.button(
                    "Add Row",
                    on_click=cast(rx.EventHandler[[]], State.add_row),
                    variant="outline",
                    cursor="pointer",
                ),
                rx.button(
                    "Start Enrichment",
                    on_click=cast(rx.EventHandler[[]], State.run_enrichment),
                    loading=State.is_processing,
                    color_scheme="jade",
                    cursor="pointer",
                ),
                rx.spacer(),
                rx.button(
                    "Export CSV",
                    on_click=cast(rx.EventHandler[[]], State.export_csv),
                    variant="soft",
                    cursor="pointer",
                    color_mode="light"
                ),
                width="100%",
                padding_y="1rem",
            ),

            # Progress Section
            rx.cond(
                State.is_processing,
                rx.box(
                    rx.text(State.status_log, size="2", margin_bottom="0.5rem"),
                    rx.progress(value=State.progress, width="100%"),
                    width="100%",
                    padding_y="1rem",
                ),
            ),

            # Data Table using Radix Table
            rx.box(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            table_header_cell("Nama Perusahaan"),
                            table_header_cell("Sektor"),
                            table_header_cell("Alamat"),
                            table_header_cell("Kontak"),
                            table_header_cell("Potensi Polis"),
                            table_header_cell("Jml Karyawan"),
                            table_header_cell("Deskripsi"),
                            table_header_cell("Cabang"),
                            table_header_cell("PIC"),
                            table_header_cell("Keuangan"),
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
                border_radius="md",
            ),

            align_items="start",
            width="100%",
            padding="2rem",
            max_width=rx.cond(State.sidebar_open, "1200px", "100%"),
            margin_x="auto",
        ),
        width="100%",
        min_height="100vh",
    )


def index():
    return rx.hstack(
        sidebar(),
        rx.cond(
            State.sidebar_open,
            rx.box(
                width="1px",
                height="200vh",
                background=rx.color("gray", 4),
                display=["none", "none", "block"],
            ),
        ),
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.button(
                        rx.icon(tag="menu", size=20),
                        on_click=cast(rx.EventHandler[[]], State.toggle_sidebar),
                        variant="ghost",
                        size="2",
                        cursor="pointer",
                    ),
                    rx.spacer(),
                    width="100%",
                    align_items="center",
                    padding="1rem",
                    padding_right="0",
                    margin_bottom="0.5rem",
                ),
                main_content(),
                width="100%",
                height="100%",
                align_items="start",
            ),
            width="100%",
            height="100%",
        ),
        width="100%",
        height="100vh",
        align_items="start",
    )


app = rx.App(
    theme=rx.theme(
        has_background=True,
        radius="small",
        accent_color="violet"
    )
)
app.add_page(index)