import reflex as rx
from typing import Any, cast
from reflex.style import set_color_mode, color_mode

from .state import State


def render_progress_item(item: dict[str, Any]) -> rx.Component:
    status_icon = rx.match(
        item["status"],
        ("active", rx.spinner(size="1", color=rx.color("blue", 9))),
        ("done", rx.icon(tag="check", size=14, color=rx.color("green", 10))),
        ("error", rx.icon(tag="circle_alert", size=14, color=rx.color("red", 10))),
        ("warning", rx.icon(tag="triangle_alert", size=14, color=rx.color("amber", 10))),
        rx.icon(tag="circle", size=14, color=rx.color("gray", 8)),
    )

    return rx.hstack(
        rx.box(status_icon, min_width="18px", padding_top="2px"),
        rx.vstack(
            rx.text(item["title"], size="2", weight="medium", color=rx.color("gray", 12), line_height="1.25"),
            rx.cond(
                item["subtitle"] != "",
                rx.text(item["subtitle"], size="1", color=rx.color("gray", 10)),
                rx.fragment(),
            ),
            spacing="1",
            align_items="start",
            width="100%",
        ),
        spacing="3",
        align_items="start",
        width="100%",
        padding="11px 12px",
        border_radius="10px",
        border=f"1px solid {rx.color('gray', 4)}",
        background=rx.color("gray", 1),
        box_shadow="0 1px 2px rgba(15,23,42,0.03)",
    )


def render_query_row(query: dict[str, Any]) -> rx.Component:
    status_icon = rx.match(
        query["status"],
        ("active", rx.spinner(size="1", color=rx.color("blue", 9))),
        ("cancelled", rx.icon(tag="x", size=13, color=rx.color("amber", 10))),
        rx.icon(tag="check", size=13, color=rx.color("green", 10)),
    )

    return rx.hstack(
        rx.box(status_icon, min_width="16px"),
        rx.text(query["text"], size="2", color=rx.color("gray", 11), line_height="1.3"),
        spacing="3",
        align_items="center",
        width="100%",
        padding="10px 12px",
        border_radius="10px",
        background=rx.color("gray", 1),
        border=f"1px solid {rx.color('gray', 4)}",
        box_shadow="0 1px 2px rgba(15,23,42,0.03)",
    )


def render_source_chip(source: dict[str, Any]) -> rx.Component:
    icon_box = rx.box(
        rx.image(
            src=source["favicon"],
            width="18px",
            height="18px",
            border_radius="4px",
        ),
        width=["32px", "30px", "28px"],
        height=["32px", "30px", "28px"],
        display="flex",
        align_items="center",
        justify_content="center",
        border_radius="8px",
        border=f"1px solid {rx.color('gray', 5)}",
        background=rx.color("gray", 1),
        _hover={
            "opacity": "0.88",
            "border": f"1px solid {rx.color('blue', 7)}",
            "transform": "translateY(-1px)",
            "box-shadow": "0 4px 12px rgba(29,78,216,0.14)",
        },
        transition="opacity 150ms ease, border 150ms ease, transform 150ms ease, box-shadow 150ms ease",
    )

    clickable_chip = rx.cond(
        source.get("url", "") != "",
        rx.link(icon_box, href=source["url"], is_external=True, cursor="pointer"),
        icon_box,
    )

    return rx.tooltip(clickable_chip, content=source["domain"])


def render_enrichment_overlay() -> rx.Component:
    return rx.box(
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.hstack(
                        rx.box(
                            rx.spinner(
                                size="3",
                                color=rx.color("sky", 8),
                                loading=State.overlay_running,
                            ),
                            rx.box(
                                rx.spinner(
                                    size="2",
                                    color=rx.color("blue", 9),
                                    loading=State.overlay_running,
                                ),
                                position="absolute",
                                left="50%",
                                top="50%",
                                transform="translate(-50%, -50%)",
                            ),
                            width=["34px", "36px", "38px"],
                            height=["34px", "36px", "38px"],
                            display="flex",
                            align_items="center",
                            justify_content="center",
                            position="relative",
                        ),
                        rx.vstack(
                            rx.heading("Enriching entire table...", size="6"),
                            rx.text(
                                State.overlay_phase_label,
                                size="2",
                                color=rx.color("gray", 10),
                            ),
                            spacing="1",
                            align_items="start",
                        ),
                        spacing="3",
                        align_items="center",
                    ),
                    rx.spacer(),
                    rx.badge(
                        State.session_company_progress_label,
                        radius="full",
                        variant="surface",
                        style={
                            "background": "#E0F2FE",
                            "color": "#0369A1",
                            "border": "1px solid #BAE6FD",
                            "font-weight": "600",
                            "padding": "3px 10px",
                        },
                    ),
                    rx.button(
                        rx.icon(tag="x", size=16),
                        on_click=cast(rx.EventHandler[[]], State.close_overlay),
                        variant="ghost",
                        size="3",
                        cursor="pointer",
                        aria_label="Close enrichment overlay",
                        min_width=["34px", "34px", "32px"],
                    ),
                    width="100%",
                    align_items="start",
                    padding_bottom="4px",
                ),
                rx.box(
                    rx.vstack(
                        rx.hstack(
                            rx.text("Sources", size="1", weight="medium", color=rx.color("gray", 10)),
                            rx.spacer(),
                            rx.cond(
                                State.source_overflow_count > 0,
                                rx.badge(
                                    "+" + State.source_overflow_count.to_string(),
                                    radius="full",
                                    variant="surface",
                                    style={
                                        "background": "#EFF6FF",
                                        "color": "#1D4ED8",
                                        "border": "1px solid #DBEAFE",
                                        "font-weight": "500",
                                    },
                                ),
                                rx.fragment(),
                            ),
                            width="100%",
                        ),
                        rx.hstack(
                            rx.foreach(State.visible_sources, render_source_chip),
                            width="100%",
                            wrap="wrap",
                            spacing=rx.breakpoints(initial="1", sm="2", lg="2"),
                            align_items="center",
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    width="100%",
                    padding=["9px 10px", "10px 12px", "10px 12px"],
                    border_radius="12px",
                    border=f"1px solid {rx.color('gray', 4)}",
                    background="linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%)",
                    box_shadow="inset 0 1px 0 rgba(255,255,255,0.65)",
                ),
                rx.grid(
                    rx.box(
                        rx.vstack(
                            rx.hstack(
                                rx.text("Research Progress", size="3", weight="bold"),
                                rx.spacer(),
                                rx.badge(
                                    State.progress_item_count,
                                    radius="full",
                                    variant="surface",
                                    style={
                                        "background": "#EEF2FF",
                                        "color": "#3730A3",
                                        "border": "1px solid #E0E7FF",
                                        "font-weight": "600",
                                    },
                                ),
                                width="100%",
                            ),
                            rx.vstack(
                                rx.foreach(State.filtered_progress_items, render_progress_item),
                                width="100%",
                                spacing="2",
                                align_items="start",
                            ),
                            width="100%",
                            align_items="start",
                            spacing="3",
                        ),
                        border=f"1px solid {rx.color('gray', 4)}",
                        background=rx.color("gray", 2),
                        border_radius="12px",
                        padding="14px",
                        min_height=["220px", "280px", "420px"],
                        max_height=["34vh", "44vh", "60vh"],
                        overflow_y="auto",
                        scrollbar_gutter="stable",
                        padding_right=["8px", "10px", "12px"],
                    ),
                    rx.box(
                        rx.vstack(
                            rx.hstack(
                                rx.text("Active Queries", size="3", weight="bold"),
                                rx.badge(
                                    State.overlay_query_panel_count,
                                    radius="full",
                                    variant="surface",
                                    style={
                                        "background": "#DBEAFE",
                                        "color": "#1D4ED8",
                                        "border": "1px solid #BFDBFE",
                                        "font-weight": "600",
                                        "padding": "2px 10px",
                                    },
                                ),
                                width="100%",
                                spacing="2",
                                align_items="center",
                            ),
                            rx.cond(
                                State.overlay_query_panel_count > 0,
                                rx.vstack(
                                    rx.foreach(State.ordered_active_queries, render_query_row),
                                    width="100%",
                                    spacing="2",
                                    align_items="start",
                                ),
                                rx.box(
                                    rx.text(
                                        "No active queries yet...",
                                        size="2",
                                        color=rx.color("gray", 10),
                                    ),
                                    width="100%",
                                    padding="12px",
                                    border_radius="8px",
                                    border=f"1px dashed {rx.color('gray', 5)}",
                                    background=rx.color("gray", 1),
                                ),
                            ),
                            width="100%",
                            align_items="start",
                            spacing="3",
                        ),
                        border=f"1px solid {rx.color('gray', 4)}",
                        background=rx.color("gray", 2),
                        border_radius="12px",
                        padding="14px",
                        min_height=["220px", "280px", "420px"],
                        max_height=["34vh", "44vh", "60vh"],
                        overflow_y="auto",
                        scrollbar_gutter="stable",
                        padding_right=["8px", "10px", "12px"],
                    ),
                    columns=rx.breakpoints(initial="1fr", lg="1fr 1fr"),
                    gap=["12px", "14px", "14px"],
                    width="100%",
                ),
                spacing="3",
                align_items="start",
                width="100%",
            ),
            width=["95vw", "92vw", "min(1120px, 92vw)"],
            max_height=["94vh", "92vh", "90vh"],
            overflow_y="auto",
            overflow_x="hidden",
            border_radius="20px",
            border=f"1px solid {rx.color('gray', 5)}",
            background="linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%)",
            box_shadow="0 28px 90px rgba(2,6,23,0.24)",
            padding=["14px", "18px", "20px"],
            transform=rx.cond(State.overlay_visible, "translateY(0)", "translateY(10px)"),
            transition="transform 180ms ease, opacity 180ms ease",
        ),
        position="fixed",
        inset="0",
        z_index="2200",
        display="flex",
        align_items="center",
        justify_content="center",
        background="rgba(15, 23, 42, 0.42)",
        backdrop_filter="blur(4px)",
        padding=["8px", "12px", "12px"],
        opacity=rx.cond(State.overlay_visible, "1", "0"),
        visibility=rx.cond(State.overlay_visible, "visible", "hidden"),
        pointer_events=rx.cond(State.overlay_visible, "auto", "none"),
        transition="opacity 180ms ease",
    )


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
                placeholder="Company Name",
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


def main_content() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.vstack(
                rx.heading("👾ZGTI AI Lead Enrichment", size="7", text_align="left"),
                rx.vstack(
                    rx.text(
                        "This tool automates the process of enriching company profiles using AI agents.",
                        size="2",
                        color=rx.color("gray", 10),
                        text_align="left",
                        max_width="680px",
                    ),
                    rx.text(
                        "Powered by LangGraph & Tavily",
                        size="1",
                        weight="medium",
                        color=rx.color("gray", 9),
                        text_align="left",
                    ),
                    spacing="2",
                    align_items="center",
                ),
                spacing="4",
                width="100%",
                align_items="center",
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
                        rx.button(
                            rx.icon(tag="file_spreadsheet", size=16),
                            on_click=cast(rx.EventHandler[[]], State.export_excel),
                            variant="surface",
                            size="2",
                            cursor="pointer",
                            aria_label="Export Excel",
                            title="Export Excel",
                        ),
                        rx.button(
                            rx.icon(tag="file_text", size=16),
                            on_click=cast(rx.EventHandler[[]], State.export_pdf),
                            variant="surface",
                            size="2",
                            cursor="pointer",
                            aria_label="Export PDF",
                            title="Export PDF",
                        ),
                        spacing="2",
                    ),
                    width="100%",
                    padding="8px 8px 10px 8px",
                    align_items="center",
                ),
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
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
            max_width="1360px",
            margin_x="auto",
            padding_x=["1rem", "1.5rem", "2rem"],
            padding_y="1.05rem",
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


app = rx.App()
app.add_page(index, title="AI Lead Enrichment", image="zurich-logo-update.png")
