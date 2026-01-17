import os
import sys
import reflex as rx
import asyncio
import csv
from io import StringIO
from typing import List, Dict, Any
from dotenv import load_dotenv
from tavily import TavilyClient
from openai import AsyncAzureOpenAI

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.researcher import ResearchPipeline

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


class State(rx.State):

    companies: List[Dict[str, str]] = _default_companies()
   
    # UI State
    is_processing: bool = False
    progress: int = 0
    status_log: str = ""
    sidebar_open: bool = True
    research_logs: List[str] = []
    log_query: str = ""
   
    def toggle_sidebar(self):
        self.sidebar_open = not self.sidebar_open
   
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

    def clear_search(self):
        self.log_query = ""

    def reset_session_state(self):
        if self.is_processing:
            return
        self.log_query = ""
        self.research_logs = []
        self.progress = 0
        self.status_log = ""
        self.is_processing = False
        self.companies = _default_companies()

    @rx.var
    def filtered_research_logs(self) -> List[str]:
        query = self.log_query.strip().lower()
        if not query:
            return self.research_logs
        return [entry for entry in self.research_logs if query in entry.lower()]

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
                self.is_processing = False
                yield
                return

            tavily_client = TavilyClient(api_key=str(tavily_api_key))
            azure_client = AsyncAzureOpenAI(
                api_key=str(azure_api_key),
                api_version=api_version,
                azure_endpoint=str(azure_endpoint)
            )
           
            pipeline = ResearchPipeline(tavily_client, azure_client, str(deployment))

        except Exception as e:
            self.status_log = f"Initialization Error: {str(e)}"
            self.append_log(self.status_log)
            self.is_processing = False
            yield
            return

        total = len(targets)
        for idx, (table_index, company_name) in enumerate(targets):
            # Check if already enriched (simple check: if Sektor Perusahaan is not empty)
            current_row = self.companies[table_index]
            sektor = current_row.get("Sektor Perusahaan")
            if sektor and isinstance(sektor, str) and sektor.strip():
                self.status_log = f"Skipping {company_name} (already enriched)..."
                self.append_log(self.status_log)
                self.progress = int((idx + 1) / total * 100)
                yield
                continue

            self.status_log = f"Processing {idx + 1}/{total}: {company_name}..."
            self.append_log(self.status_log)
            yield
           
            try:
                # Run research pipeline dengan streaming logs real-time
                result_state = None
                async for event_type, payload in pipeline.run_research_stream(company_name):
                    if event_type == "log":
                        # payload adalah string log message
                        self.append_log(f"{company_name}: {payload}")
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
               
            except Exception as e:
                self.status_log = f"Error processing {company_name}: {str(e)}"
                self.append_log(self.status_log)
                print(f"Error: {e}")
           
            # Update progress
            self.progress = int((idx + 1) / total * 100)
            if not self.status_log.startswith("Error processing"):
                self.append_log(f"Completed {company_name}.")
            yield

        self.status_log = "Enrichment Completed!"
        self.append_log(self.status_log)
        self.is_processing = False
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
