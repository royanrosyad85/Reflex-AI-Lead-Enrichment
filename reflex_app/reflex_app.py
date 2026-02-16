import reflex as rx

from .ui.components.header import dark_mode_toggle, project_header
from .ui.components.overlay import (
    render_enrichment_overlay,
    render_progress_item,
    render_query_row,
    render_source_chip,
)
from .ui.components.table import table_header_cell, table_row
from .ui.page_index import index, main_content

app = rx.App(stylesheets=["/fonts/fonts.css"])
app.add_page(index, title="AI Lead Enrichment", image="zurich-logo-update.png")
