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


def render_source_card(source: dict[str, Any]) -> rx.Component:
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


def render_research_event(event: dict[str, Any]) -> rx.Component:
    """Render a single research event in Perplexity style."""
    return rx.box(
        rx.match(
            event["phase"],
            # Thinking phase - conditional spinner (active) or static icon (done)
            (
                "thinking",
                rx.hstack(
                    rx.cond(
                        event["is_active"],
                        rx.spinner(size="1"),
                        rx.icon(tag="minus", size=14, color=rx.color("gray", 8)),
                    ),
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
            # Analyzing phase - conditional spinner (active) or static icon (done)
            (
                "analyzing",
                rx.hstack(
                    rx.cond(
                        event["is_active"],
                        rx.spinner(size="1"),
                        rx.icon(tag="minus", size=14, color=rx.color("gray", 8)),
                    ),
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


def resize_handle() -> rx.Component:
    return rx.box(
        rx.box(
            width="1px",
            height="100%",
            border_radius="full",
            background=rx.color("gray", 7),
        ),
        display=["none", "none", "flex"],
        width="12px",
        min_width="12px",
        align_self="stretch",
        align_items="center",
        justify_content="center",
        cursor="col-resize",
        background="transparent",
        _hover={"background": rx.color("gray", 3)},
        _active={"background": rx.color("blue", 3)},
        on_mouse_down=rx.call_script(
            """
            (() => {
                const panel = document.getElementById('sidebar-panel');
                if (!panel) return null;

                if (window.matchMedia('(max-width: 1024px)').matches) {
                    return parseInt(getComputedStyle(panel).width, 10) || 340;
                }

                const min = 280;
                const max = 520;

                const setWidth = (clientX) => {
                    const nextWidth = Math.min(max, Math.max(min, Math.round(clientX)));
                    panel.style.width = `${nextWidth}px`;
                    return nextWidth;
                };

                document.body.style.cursor = 'col-resize';
                document.body.style.userSelect = 'none';

                return new Promise((resolve) => {
                    const onMove = (moveEvent) => {
                        setWidth(moveEvent.clientX);
                    };

                    const onUp = (upEvent) => {
                        const finalWidth = setWidth(upEvent.clientX);
                        window.removeEventListener('mousemove', onMove);
                        window.removeEventListener('mouseup', onUp);
                        document.body.style.cursor = '';
                        document.body.style.userSelect = '';
                        resolve(finalWidth);
                    };

                    window.addEventListener('mousemove', onMove);
                    window.addEventListener('mouseup', onUp);
                });
            })()
            """,
            callback=cast(rx.EventHandler[[Any]], State.set_sidebar_width),
        ),
        aria_label="Resize sidebar",
        role="separator",
    )


def sidebar():
    return rx.cond(
        State.sidebar_open,
        rx.box(
            rx.hstack(
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
                            cursor="pointer",
                            aria_label="Close sidebar",
                        ),
                        width="100%",
                        align_items="center",
                        margin_bottom="0.5rem",
                    ),
                    rx.heading("Project Overview", size="5", margin_bottom="0.5rem"),
                    rx.text(
                        "Agentic LangGraph Researcher",
                        weight="bold",
                        margin_bottom="0.25rem",
                    ),
                    rx.text(
                        "This tool automates the process of enriching company profiles using AI agents.",
                        size="2",
                        margin_bottom="0.5rem",
                        color=rx.color("gray", 11),
                    ),
                    rx.text("Powered by LangGraph & Tavily", size="1", color=rx.color("gray", 10)),
                    rx.divider(margin_y="0.5rem"),
                    rx.heading("Research Logs", size="3"),
                    rx.hstack(
                        rx.button(
                            "Clear Search",
                            on_click=cast(rx.EventHandler[[]], State.clear_search),
                            variant="soft",
                            size="1",
                            color_scheme="tomato",
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
                    rx.box(
                        rx.vstack(
                            # Show current company being processed
                            rx.cond(
                                State.is_processing & (State.current_company != ""),
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
                    width="100%",
                    padding_right="12px",
                ),
                resize_handle(),
                align_items="stretch",
                spacing="0",
                min_height="100%",
                width="100%",
            ),
            id="sidebar-panel",
            padding="2rem",
            height=["100vh", "100vh", "auto"],
            min_height="100vh",
            width=["100%", "360px", State.sidebar_width_storage + "px"],
            min_width=["100%", "360px", "280px"],
            max_width=["100%", "420px", "520px"],
            display="block",
            position=["fixed", "fixed", "sticky"],
            align_self="stretch",
            top="0",
            left="0",
            z_index="1000",
            background=rx.color("gray", 1),
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
                        aria_label="Open sidebar",
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
            min_height="100vh",
        ),
        width="100%",
        min_height="100vh",
        align_items="stretch",
        on_mount=cast(rx.EventHandler[[]], State.hydrate_sidebar_width),
    )


app = rx.App()
app.add_page(index, title="AI Lead Enrichment", image="zurich-logo-update.png")
