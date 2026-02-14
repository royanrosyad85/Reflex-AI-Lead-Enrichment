import os
import sys
import reflex as rx
import asyncio
import csv
import time
import uuid
from io import StringIO, BytesIO
from typing import List, Dict, TypedDict, cast
from dotenv import load_dotenv
from tavily import TavilyClient
from openai import AsyncAzureOpenAI

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.researcher import ResearchPipeline
from .enrichment_overlay_mapper import (
    ProgressItem,
    QueryItem,
    SourceItem,
    map_stream_event_to_updates,
)

load_dotenv()


def _default_companies() -> List[Dict[str, str]]:
    return [
        {
            "Nama Perusahaan": "",
            "Sektor Perusahaan": "",
            "Alamat": "",
            "Kontak": "",
            "Potensi Polis": "",
            "Jumlah Karyawan": "",
            "Short Description": "",
            "Kantor Cabang": "",
            "PIC Perusahaan": "",
            "Laporan Keuangan": "",
        }
        for _ in range(5)
    ]


class ResearchSession(TypedDict):
    session_id: str
    is_running: bool
    started_at: float
    total_companies: int
    completed_companies: int
    current_company: str


class LastSessionSummary(TypedDict):
    session_id: str
    completed_companies: int
    total_companies: int
    ended_at: float
    status_text: str


class State(rx.State):

    companies: List[Dict[str, str]] = _default_companies()
   
    # UI State
    is_processing: bool = False
    progress: int = 0
    status_log: str = ""
    research_logs: List[str] = []
    overlay_phase: str = "hidden"
    overlay_close_token: int = 0
    research_session: ResearchSession | None = None
    last_session_summary: LastSessionSummary | None = None
    progress_items: List[ProgressItem] = []
    active_queries: List[QueryItem] = []
    active_sources: List[SourceItem] = []
    overlay_research_phase_key: str = "idle"
    overlay_query_count_hint: int = 0
    overlay_source_count_hint: int = 0
    log_query: str = ""
    current_company: str = ""
    undo_visible: bool = False
    undo_snapshot_logs: List[str] = []
    undo_snapshot_progress: List[ProgressItem] = []
    undo_snapshot_queries: List[QueryItem] = []
    undo_snapshot_sources: List[SourceItem] = []
    undo_seconds_left: int = 0
    undo_token: int = 0

    def add_row(self):
        self.companies = self.companies + [{
            "Nama Perusahaan": "", "Sektor Perusahaan": "", "Alamat": "", "Kontak": "",
            "Potensi Polis": "", "Jumlah Karyawan": "", "Short Description": "",
            "Kantor Cabang": "", "PIC Perusahaan": "", "Laporan Keuangan": ""
        }]

    def update_company_name(self, value: str, index: int):
        new_companies = list(self.companies)
        new_companies[index] = {**new_companies[index], "Nama Perusahaan": value}
        self.companies = new_companies

    def set_log_query(self, value: str):
        self.log_query = value

    def append_log(self, message: str):
        self.research_logs = self.research_logs + [message]

    def close_overlay(self):
        self.overlay_phase = "hidden"
        self.overlay_close_token += 1

    def reopen_last_enrichment_log(self):
        if self.last_session_summary is None:
            return
        self.overlay_phase = "closed_with_result"
        self.overlay_close_token += 1

    def start_research_session(self, total_companies: int):
        started_at = time.time()
        self.overlay_phase = "running"
        self.overlay_close_token += 1
        self.progress_items = []
        self.active_queries = []
        self.active_sources = []
        self.overlay_research_phase_key = "planning"
        self.overlay_query_count_hint = 0
        self.overlay_source_count_hint = 0
        self.research_session = {
            "session_id": uuid.uuid4().hex,
            "is_running": True,
            "started_at": started_at,
            "total_companies": total_companies,
            "completed_companies": 0,
            "current_company": "",
        }

    def finish_research_session(self):
        if self.research_session is None:
            return
        completed = self.research_session.get("completed_companies", 0)
        total = self.research_session.get("total_companies", 0)
        self.last_session_summary = {
            "session_id": self.research_session.get("session_id", ""),
            "completed_companies": completed,
            "total_companies": total,
            "ended_at": time.time(),
            "status_text": f"Last run {completed}/{total} completed",
        }
        self.research_session = {
            **self.research_session,
            "is_running": False,
            "current_company": "",
        }
        self.active_queries = [
            {**q, "status": "done" if q.get("status") == "active" else q.get("status", "done")}
            for q in self.active_queries
        ]
        self.progress_items = [
            {
                **item,
                "status": "done"
                if item.get("status") in {"running", "active"}
                else item.get("status", "done"),
            }
            for item in self.progress_items
        ]
        self.overlay_research_phase_key = "extracting"
        self.overlay_phase = "closing"
        self.overlay_close_token += 1
        return State.run_overlay_auto_close

    @rx.event(background=True)
    async def run_overlay_auto_close(self):
        async with self:
            token = self.overlay_close_token

        await asyncio.sleep(1.8)

        async with self:
            if token != self.overlay_close_token:
                return
            if self.overlay_phase != "closing":
                return
            self.overlay_phase = "hidden"

    def append_progress_item(self, item: ProgressItem):
        company = str(item.get("subtitle", ""))
        if item.get("status") == "active" and company:
            self.progress_items = [
                {**existing, "status": "done"}
                if existing.get("status") in {"running", "active"}
                and existing.get("subtitle") == company
                else existing
                for existing in self.progress_items
            ]
        self.progress_items = self.progress_items + [item]

    def finalize_running_progress(self, company: str):
        self.progress_items = [
            {**item, "status": "done"}
            if item.get("status") in {"running", "active"} and item.get("subtitle") == company
            else item
            for item in self.progress_items
        ]

    def update_overlay_phase(self, phase_key: str, query_count: int, source_count: int):
        self.overlay_research_phase_key = phase_key
        if query_count >= 0:
            self.overlay_query_count_hint = query_count
        if source_count >= 0:
            self.overlay_source_count_hint = source_count

    def replace_active_queries(self, queries: List[QueryItem], company: str, round_num: int):
        kept = [q for q in self.active_queries if not (q.get("company") == company and q.get("round_num") == round_num)]
        self.active_queries = kept + queries

    def upsert_active_sources(self, sources: List[SourceItem]):
        normalized_existing: dict[str, SourceItem] = {}
        for source in self.active_sources:
            domain = str(source.get("domain", "")).strip()
            if not domain:
                continue
            normalized_existing[domain] = {
                "domain": domain,
                "favicon": str(source.get("favicon", "")).strip(),
                "url": str(source.get("url", "")).strip(),
                "company": str(source.get("company", "")).strip(),
                "last_seen_at": float(source.get("last_seen_at", 0.0)),
            }

        by_domain: dict[str, SourceItem] = dict(normalized_existing)
        for source in sources:
            domain = str(source.get("domain", "")).strip()
            if domain:
                by_domain[domain] = {
                    "domain": domain,
                    "favicon": str(source.get("favicon", "")).strip(),
                    "url": str(source.get("url", "")).strip(),
                    "company": str(source.get("company", "")).strip(),
                    "last_seen_at": float(source.get("last_seen_at", 0.0)),
                }
        ordered = sorted(by_domain.values(), key=lambda item: item.get("last_seen_at", 0.0), reverse=True)
        self.active_sources = ordered

    def finalize_company_activity(self, company: str, status: str = "done"):
        self.active_queries = [
            {**q, "status": status} if q.get("company") == company and q.get("status") == "active" else q
            for q in self.active_queries
        ]

    def mark_company_completed(self, company: str):
        if self.research_session is None:
            return
        completed = self.research_session.get("completed_companies", 0) + 1
        self.research_session = {
            **self.research_session,
            "completed_companies": completed,
            "current_company": company,
        }

    def clear_search(self):
        self.undo_snapshot_logs = list(self.research_logs)
        self.undo_snapshot_progress = cast(List[ProgressItem], [dict(item) for item in self.progress_items])
        self.undo_snapshot_queries = cast(List[QueryItem], [dict(item) for item in self.active_queries])
        self.undo_snapshot_sources = cast(List[SourceItem], [dict(item) for item in self.active_sources])
        has_logs = bool(
            self.undo_snapshot_logs
            or self.undo_snapshot_progress
            or self.undo_snapshot_queries
            or self.undo_snapshot_sources
        )

        self.log_query = ""
        self.research_logs = []
        self.progress_items = []
        self.active_queries = []
        self.active_sources = []

        self.undo_visible = has_logs
        self.undo_token += 1
        self.undo_seconds_left = 5

        if not has_logs:
            self.undo_seconds_left = 0
            return

        return State.run_undo_countdown

    @rx.event(background=True)
    async def run_undo_countdown(self):
        async with self:
            token = self.undo_token

        for seconds in [4, 3, 2, 1, 0]:
            await asyncio.sleep(1)

            async with self:
                if not self.undo_visible or token != self.undo_token:
                    return

                self.undo_seconds_left = seconds

                if seconds == 0:
                    self.undo_visible = False
                    self.undo_snapshot_logs = []
                    self.undo_snapshot_progress = []
                    self.undo_snapshot_queries = []
                    self.undo_snapshot_sources = []
                    self.undo_seconds_left = 0
                    return

    def undo_clear_search(self):
        if not self.undo_visible:
            return

        self.research_logs = list(self.undo_snapshot_logs)
        self.progress_items = cast(List[ProgressItem], [dict(item) for item in self.undo_snapshot_progress])
        self.active_queries = cast(List[QueryItem], [dict(item) for item in self.undo_snapshot_queries])
        self.active_sources = cast(List[SourceItem], [dict(item) for item in self.undo_snapshot_sources])
        self.undo_visible = False
        self.undo_snapshot_logs = []
        self.undo_snapshot_progress = []
        self.undo_snapshot_queries = []
        self.undo_snapshot_sources = []
        self.undo_seconds_left = 0
        self.undo_token += 1

    def reset_session_state(self):
        if self.is_processing:
            return
        self.log_query = ""
        self.research_logs = []
        self.progress_items = []
        self.active_queries = []
        self.active_sources = []
        self.overlay_research_phase_key = "idle"
        self.overlay_query_count_hint = 0
        self.overlay_source_count_hint = 0
        self.overlay_phase = "hidden"
        self.overlay_close_token += 1
        self.research_session = None
        self.last_session_summary = None
        self.undo_visible = False
        self.undo_snapshot_logs = []
        self.undo_snapshot_progress = []
        self.undo_snapshot_queries = []
        self.undo_snapshot_sources = []
        self.undo_seconds_left = 0
        self.undo_token += 1
        self.progress = 0
        self.status_log = ""
        self.current_company = ""
        self.is_processing = False
        self.companies = _default_companies()

    @rx.var
    def filtered_research_logs(self) -> List[str]:
        query = self.log_query.strip().lower()
        if not query:
            return self.research_logs
        return [entry for entry in self.research_logs if query in entry.lower()]

    @rx.var
    def filtered_progress_items(self) -> List[ProgressItem]:
        query = self.log_query.strip().lower()
        if not query:
            return self.progress_items
        return [
            item
            for item in self.progress_items
            if query in str(item.get("title", "")).lower()
            or query in str(item.get("subtitle", "")).lower()
        ]

    @rx.var
    def active_query_count(self) -> int:
        return len([q for q in self.active_queries if q.get("status") == "active"])

    @rx.var
    def overlay_query_panel_count(self) -> int:
        return len(self.active_queries)

    @rx.var
    def overlay_visible(self) -> bool:
        return self.overlay_phase != "hidden"

    @rx.var
    def overlay_running(self) -> bool:
        return self.overlay_phase == "running"

    @rx.var
    def show_reopen_overlay_cta(self) -> bool:
        return self.overlay_phase == "hidden" and self.last_session_summary is not None

    @rx.var
    def last_run_status_chip(self) -> str:
        if self.overlay_phase == "running" and self.research_session is not None:
            completed = self.research_session.get("completed_companies", 0)
            total = self.research_session.get("total_companies", 0)
            return f"Running {completed}/{total}"
        if self.last_session_summary is None:
            return "No runs yet"
        return self.last_session_summary.get("status_text", "Last run completed")

    @rx.var
    def ordered_active_queries(self) -> List[QueryItem]:
        return self.active_queries

    @rx.var
    def visible_sources(self) -> List[SourceItem]:
        return self.active_sources[:24]

    @rx.var
    def source_overflow_count(self) -> int:
        count = len(self.active_sources) - 24
        return count if count > 0 else 0

    @rx.var
    def progress_item_count(self) -> int:
        return len(self.filtered_progress_items)

    @rx.var
    def session_company_progress_label(self) -> str:
        if self.research_session is None:
            return "0/0 entities"
        completed = self.research_session.get("completed_companies", 0)
        total = self.research_session.get("total_companies", 0)
        return f"{completed}/{total} entities"

    @rx.var
    def session_current_company(self) -> str:
        if self.research_session is None:
            return ""
        return str(self.research_session.get("current_company", ""))

    @rx.var
    def overlay_phase_label(self) -> str:
        phase = self.overlay_research_phase_key
        if phase == "planning":
            return "Planning research strategy..."
        if phase == "planning_again":
            return "Planning research again..."
        if phase == "searching":
            count = self.overlay_query_count_hint if self.overlay_query_count_hint > 0 else self.active_query_count
            return f"Searching the web ({count} queries)..."
        if phase == "found_sources":
            return f"Found {self.overlay_source_count_hint} sources from WebSearch"
        if phase == "summarizing":
            return "Summaries the result..."
        if phase == "extracting":
            return "Extracting into table..."
        if phase == "error":
            return "Encountered an issue while enriching..."
        return "Enriching entire table..."

    @rx.var
    def undo_button_label(self) -> str:
        return f"Undo ({self.undo_seconds_left}s)"

    async def run_enrichment(self):
        # Filter companies that have names
        targets = [(i, c["Nama Perusahaan"]) for i, c in enumerate(self.companies) if c["Nama Perusahaan"].strip()]

        if not targets:
            self.status_log = "Please enter at least one company name."
            self.append_log(self.status_log)
            return

        self.is_processing = True
        self.progress = 0
        self.status_log = f"Starting enrichment for {len(targets)} companies..."
        self.append_log(self.status_log)
        self.start_research_session(len(targets))
        yield

        try:
            tavily_api_key = os.getenv("TAVILY_API_KEY")
            azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
            azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
            api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

            if not all([tavily_api_key, azure_api_key, azure_endpoint, deployment]):
                self.status_log = "Error: Missing environment variables."
                self.append_log(self.status_log)
                self.append_progress_item(
                    {
                        "id": f"global-config-{int(time.time() * 1000)}",
                        "phase": "config",
                        "title": self.status_log,
                        "subtitle": "Please check TAVILY and Azure OpenAI env vars.",
                        "status": "error",
                        "timestamp": time.time(),
                    }
                )
                self.update_overlay_phase("error", self.active_query_count, self.overlay_source_count_hint)
                return

            tavily_client = TavilyClient(api_key=str(tavily_api_key))
            azure_client = AsyncAzureOpenAI(
                api_key=str(azure_api_key),
                api_version=api_version,
                azure_endpoint=str(azure_endpoint)
            )
           
            pipeline = ResearchPipeline(tavily_client, azure_client, str(deployment))

            total = len(targets)
            for idx, (table_index, company_name) in enumerate(targets):
                # Check if already enriched (simple check: if Sektor Perusahaan is not empty)
                current_row = self.companies[table_index]
                sektor = current_row.get("Sektor Perusahaan")
                if sektor and isinstance(sektor, str) and sektor.strip():
                    self.status_log = f"Skipping {company_name} (already enriched)..."
                    self.append_log(self.status_log)
                    self.append_progress_item(
                        {
                            "id": f"{company_name}-skip-{int(time.time() * 1000)}",
                            "phase": "complete",
                            "title": self.status_log,
                            "subtitle": "Data already present in table.",
                            "status": "done",
                            "timestamp": time.time(),
                        }
                    )
                    self.mark_company_completed(company_name)
                    self.progress = int((idx + 1) / total * 100)
                    yield
                    continue

                self.status_log = f"Processing {idx + 1}/{total}: {company_name}..."
                self.append_log(self.status_log)
                if self.research_session is not None:
                    self.research_session = {**self.research_session, "current_company": company_name}
                yield

                try:
                    # Run research pipeline dengan streaming logs real-time
                    result_state = None
                    self.current_company = company_name
                    async for event_type, payload in pipeline.run_research_stream(company_name):
                        if event_type == "log":
                            # payload adalah string log message
                            self.append_log(f"{company_name}: {payload}")
                            yield
                        elif event_type == "event":
                            if not isinstance(payload, dict):
                                self.append_progress_item(
                                    {
                                        "id": f"{company_name}-invalid-event-{int(time.time() * 1000)}",
                                        "phase": "event",
                                        "title": "Received invalid stream event payload",
                                        "subtitle": company_name,
                                        "status": "warning",
                                        "timestamp": time.time(),
                                    }
                                )
                                yield
                                continue

                            mapped = map_stream_event_to_updates(payload, company_name, time.time())
                            self.append_progress_item(mapped["progress_item"])
                            self.update_overlay_phase(
                                mapped["phase_key"],
                                mapped["query_count"],
                                mapped["source_count"],
                            )

                            if mapped["queries"]:
                                self.replace_active_queries(
                                    mapped["queries"],
                                    company_name,
                                    mapped["round_num"],
                                )

                            if mapped["sources"]:
                                self.upsert_active_sources(mapped["sources"])

                            if mapped["phase"] == "complete":
                                self.finalize_company_activity(company_name, "done")
                                self.finalize_running_progress(company_name)
                                self.update_overlay_phase("extracting", 0, self.overlay_source_count_hint)

                            yield
                        elif event_type == "result":
                            # payload adalah CompanyProfileState object
                            result_state = payload

                    if result_state is None:
                        raise ValueError("No result returned from research pipeline.")

                    # Ensure result_state is CompanyProfileState type
                    from backend.researcher import CompanyProfileState as CPState
                    if not isinstance(result_state, CPState):
                        raise ValueError(f"Invalid result type: expected CompanyProfileState, got {type(result_state)}")

                    result_dict = result_state.to_dict()
                    fields = result_dict.get("fields", {})

                    # Update state - create new list to trigger reactivity
                    new_companies = list(self.companies)
                    updated_row = dict(new_companies[table_index])

                    mapping = {
                        "Sektor Perusahaan": "Sektor Perusahaan",
                        "Alamat": "Alamat",
                        "Kontak": "Kontak",
                        "Potensi Polis": "Potensi Polis",
                        "Jumlah Karyawan": "Jumlah Karyawan",
                        "Short Description": "Short Description",
                        "Kantor Cabang": "Kantor Cabang",
                        "PIC Perusahaan": "PIC Perusahaan",
                        "Laporan Keuangan": "Laporan Keuangan"
                    }

                    for field_key, col_key in mapping.items():
                        field_data = fields.get(field_key, {})
                        updated_row[col_key] = field_data.get("value", "") if isinstance(field_data, dict) else ""

                    new_companies[table_index] = updated_row
                    self.companies = new_companies

                    self.finalize_company_activity(company_name, "done")
                    self.mark_company_completed(company_name)
                    self.update_overlay_phase("extracting", 0, self.overlay_source_count_hint)

                except Exception as e:
                    self.status_log = f"Error processing {company_name}: {str(e)}"
                    self.append_log(self.status_log)
                    self.append_progress_item(
                        {
                            "id": f"{company_name}-error-{int(time.time() * 1000)}",
                            "phase": "error",
                            "title": self.status_log,
                            "subtitle": company_name,
                            "status": "error",
                            "timestamp": time.time(),
                        }
                    )
                    self.finalize_company_activity(company_name, "cancelled")
                    self.mark_company_completed(company_name)
                    self.update_overlay_phase("error", self.active_query_count, self.overlay_source_count_hint)
                    print(f"Error: {e}")

                # Clear current company after processing (Root Cause 1 fix)
                self.current_company = ""
                if self.research_session is not None:
                    self.research_session = {**self.research_session, "current_company": ""}
                # Update progress
                self.progress = int((idx + 1) / total * 100)
                if not self.status_log.startswith("Error processing"):
                    self.append_log(f"Completed {company_name}.")
                yield

            self.status_log = "Enrichment Completed!"
            self.append_log(self.status_log)
            self.update_overlay_phase("extracting", 0, self.overlay_source_count_hint)

        except Exception as e:
            self.status_log = f"Unexpected error: {str(e)}"
            self.append_log(self.status_log)
            self.append_progress_item(
                {
                    "id": f"global-error-{int(time.time() * 1000)}",
                    "phase": "error",
                    "title": self.status_log,
                    "subtitle": "Unexpected pipeline failure",
                    "status": "error",
                    "timestamp": time.time(),
                }
            )
            self.update_overlay_phase("error", self.active_query_count, self.overlay_source_count_hint)
            print(f"Unexpected error: {e}")
        finally:
            self.is_processing = False
            self.current_company = ""
            close_event = self.finish_research_session()
            if close_event is not None:
                yield close_event
            yield

    def export_csv(self):
        output = StringIO()
        if not self.companies:
            return
       
        fieldnames = list(self.companies[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
       
        writer.writeheader()
        writer.writerows(self.companies)
       
        # Get CSV content
        csv_content = output.getvalue()
        output.close()
       
        return rx.download(
            data=csv_content,
            filename="company_enrichment.csv",
        )

    def export_excel(self):
        if not self.companies:
            return

        from openpyxl import Workbook

        workbook = Workbook()
        sheet = workbook.active
        if sheet is None:
            sheet = workbook.create_sheet(title="Enrichment")

        assert sheet is not None
        sheet.title = "Enrichment"

        headers = list(_default_companies()[0].keys())
        sheet.append(headers)

        for row in self.companies:
            sheet.append([str(row.get(header, "")) for header in headers])

        output = BytesIO()
        workbook.save(output)
        output.seek(0)

        return rx.download(
            data=output.getvalue(),
            filename="company_enrichment.xlsx",
        )

    def export_pdf(self):
        from datetime import datetime
        from .pdf_export import generate_company_enrichment_pdf

        pdf_bytes = generate_company_enrichment_pdf(
            companies=self.companies,
            export_datetime=datetime.now(),
        )

        return rx.download(
            data=pdf_bytes,
            filename="company_enrichment.pdf",
        )
