from typing import Any, cast

import reflex as rx

from ...state import State


def table_header_cell(text: str) -> rx.Component:
    return rx.table.column_header_cell(
        rx.text(text, weight="bold", size="2"),
    )


def _name_change_handler(row_id: str):
    return lambda val: cast(Any, State.update_company_name)(val, row_id)


def table_row(company: dict[str, str], index: int) -> rx.Component:
    row_id = company.get("_row_id", str(index))
    return rx.table.row(
        rx.table.cell(
            rx.button(
                rx.icon(tag="trash_2", size=14),
                on_click=cast(Any, State.delete_row)(row_id),
                variant="ghost",
                size="1",
                color_scheme="red",
                cursor="pointer",
                aria_label="Delete row",
                title="Delete row",
                disabled=State.is_processing,
            ),
            style={"width": "56px", "min-width": "56px", "vertical-align": "top"},
        ),
        rx.table.cell(
            rx.input(
                value=company["Nama Perusahaan"],
                on_change=_name_change_handler(row_id),
                placeholder="Company Name",
                width="100%",
                disabled=State.is_processing,
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
