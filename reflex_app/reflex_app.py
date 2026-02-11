import reflex as rx
from typing import cast, Any
from reflex.style import set_color_mode, color_mode
from .state import State


def render_query_badge(query: rx.Var[str]) -> rx.Component:
    """Render a single search query as a badge."""
    return rx.badge(
        rx.hstack(
            rx.icon(tag="search", size=12),
            rx.text(query, size="1"),
            spacing="1",
            align_items="center",
        ),
        variant="soft",
        size="1",
        radius="full",
    )


def render_source_card(source: rx.Var[dict]) -> rx.Component:
    """Render a single source as a card with favicon."""
    return rx.hstack(
        rx.image(
            src=source["favicon"],
            width="16px",
            height="16px",
            border_radius="2px",
        ),
        rx.text(source["domain"], size="1", weight="medium"),
        spacing="2",
        align_items="center",
        padding="4px 8px",
        border_radius="6px",
        background=rx.color("gray", 3),
        cursor="pointer",
        _hover={"background": rx.color("gray", 4)},
    )


def render_research_event(event: rx.Var[dict]) -> rx.Component:
    """Render a single research event in Perplexity style."""
    return rx.box(
        rx.match(
            event["phase"],
            # Thinking phase - spinner + italic message
            (
                "thinking",
                rx.hstack(
                    rx.spinner(size="1"),
                    rx.text(
                        event["message"],
                        size="1",
                        style={"font-style": "italic"},
                        color=rx.color("gray", 11),
                    ),
                    spacing="2",
                    align_items="center",
                ),
            ),
            # Searching phase - header + query pills
            (
                "searching",
                rx.vstack(
                    rx.hstack(
                        rx.text(
                            "SEARCHING",
                            size="1",
                            weight="bold",
                            color=rx.color("gray", 9),
                            style={"text-transform": "uppercase", "letter-spacing": "0.05em"},
                        ),
                        rx.badge(event["query_count"], variant="soft", size="1", radius="full"),
                        spacing="2",
                        align_items="center",
                    ),
                    rx.text(
                        event["queries_preview"],
                        size="1",
                        color=rx.color("gray", 10),
                        style={"word-break": "break-word"},
                    ),
                    spacing="2",
                    align_items="start",
                    width="100%",
                ),
            ),
            # Reading phase - header with count + source cards grid
            (
                "reading",
                rx.vstack(
                    rx.hstack(
                        rx.text(
                            "READING",
                            size="1",
                            weight="bold",
                            color=rx.color("gray", 9),
                            style={"text-transform": "uppercase", "letter-spacing": "0.05em"},
                        ),
                        rx.badge(
                            event["source_count"],
                            variant="solid",
                            size="1",
                            radius="full",
                        ),
                        spacing="2",
                        align_items="center",
                    ),
                    rx.flex(
                        rx.text(
                            event["sources_preview"],
                            size="1",
                            color=rx.color("gray", 10),
                            style={"word-break": "break-word"},
                        ),
                        width="100%",
                    ),
                    spacing="2",
                    align_items="start",
                    width="100%",
                ),
            ),
            # Analyzing phase
            (
                "analyzing",
                rx.hstack(
                    rx.spinner(size="1"),
                    rx.text(
                        event["message"],
                        size="1",
                        style={"font-style": "italic"},
                        color=rx.color("gray", 11),
                    ),
                    spacing="2",
                    align_items="center",
                ),
            ),
            # Complete phase
            (
                "complete",
                rx.hstack(
                    rx.icon(tag="check_check", size=14, color=rx.color("green", 9)),
                    rx.text(
                        event["message"],
                        size="1",
                        weight="medium",
                        color=rx.color("green", 11),
                    ),
                    spacing="2",
                    align_items="center",
                ),
            ),
            # Default fallback
            rx.text(event["message"], size="1"),
        ),
        width="100%",
        padding_y="6px",
        border_bottom=f"1px solid {rx.color('gray', 3)}",
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


def sidebar():
    return rx.cond(
        State.sidebar_open,
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.image(
                        src="/zurich-logo-update.png",
                        alt="Zurich Logo",
                        height="35px",
                        width="auto",
                    ),
                    rx.spacer(),
                    rx.button(
                        rx.icon(tag="x", size=20),
                        on_click=cast(rx.EventHandler[[]], State.toggle_sidebar),
                        variant="ghost",
                        size="2",
                        display=["flex", "flex", "none"],
                    ),
                    width="100%",
                    align_items="center",
                    margin_bottom="1rem",
                ),
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
                rx.text("Powered by LangGraph & Tavily", size="1"),
                rx.divider(margin_y="0.5rem"),
                rx.heading("Research Logs", size="3"),
                rx.hstack(
                    rx.button(
                        "Clear Search",
                        on_click=cast(rx.EventHandler[[]], State.clear_search),
                        variant="soft",
                        size="1",
                        cursor="pointer",
                    ),
                    rx.button(
                        "Reset Session",
                        on_click=cast(rx.EventHandler[[]], State.reset_session_state),
                        variant="outline",
                        size="1",
                        cursor="pointer",
                        disabled=State.is_processing,
                    ),
                    width="100%",
                    spacing="2",
                ),
                rx.box(
                    rx.vstack(
                        # Show current company being processed
                        rx.cond(
                            State.current_company != "",
                            rx.hstack(
                                rx.spinner(size="1"),
                                rx.text(
                                    State.current_company,
                                    size="2",
                                    weight="bold",
                                ),
                                spacing="2",
                                align_items="center",
                                padding="8px",
                                background=rx.color("blue", 2),
                                border_radius="6px",
                                width="100%",
                                margin_bottom="8px",
                            ),
                            rx.fragment(),
                        ),
                        # Render structured research events
                        rx.foreach(
                            State.filtered_research_events,
                            render_research_event,
                        ),
                        align_items="start",
                        spacing="1",
                        width="100%",
                        id="log-content",
                    ),
                    id="log-viewer",
                    width="100%",
                    padding="0.75rem",
                    border="1px solid",
                    border_color=rx.color("gray", 4),
                    border_radius="md",
                    background=rx.color("gray", 1),
                    overflow_y="auto",
                    min_height="50vh",
                    max_height="60vh",
                    on_mount=rx.call_script(
                        """
                        const logViewer = document.getElementById('log-viewer');
                        const logContent = document.getElementById('log-content');
                        if (logViewer && logContent) {
                            const observer = new MutationObserver(() => {
                                logViewer.scrollTop = logViewer.scrollHeight;
                            });
                            observer.observe(logContent, {
                                childList: true,
                                subtree: true,
                                characterData: true
                            });
                        }
                        """
                    ),
                ),
                align_items="start",
                spacing="4",
                height="100%",
                width="100%",
            ),
            padding="2rem",
            height="100vh",
            width=["100%", "360px", "340px"],
            display="block",
            position=["fixed", "fixed", "sticky"],
            top="0",
            left="0",
            z_index="1000",
            background=rx.color("gray", 1),
            border_right=f"1px solid {rx.color('gray', 4)}",
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
                rx.heading("👾 AI Lead Enrichment", size="7"),
                rx.spacer(),
                dark_mode_toggle(),
                width="100%",
                align_items="center",
            ),
            rx.text("Input company names below to automatically enrich their profiles."),

            # Progress Section (di atas table)
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

            # ===== NEW: Action Bar PINDAH KE BAWAH =====
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
                margin_top="1rem",
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


app = rx.App()
app.add_page(index, title="AI Lead Enrichment", image="zurich-logo-update.png")
