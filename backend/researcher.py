import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from tavily import TavilyClient
from openai import AzureOpenAI, AsyncAzureOpenAI

logger = logging.getLogger(__name__)

@dataclass
class EnrichmentField:
    value: str = "Tidak Tersedia"
    confidence: str = "Low"
    source: str = ""
    rounds_taken: int = 0

@dataclass
class CompanyProfileState:
    company_name: str
    fields: Dict[str, EnrichmentField]
    iteration_logs: List[str] = field(default_factory=list)

    def to_dict(self):
        return{
            "company_name": self.company_name,
            "fields": {k: {"value": v.value, "confidence": v.confidence, "source": v.source} for k, v in self.fields.items()},
            "iteration_logs": self.iteration_logs
        }

ENRICHMENT_SCHEMA = {
    "Sektor Perusahaan": {
        "desc": "Industri Utama Perusahaan (Max 5 kata). Contoh: 'Jasa Pengiriman Barang dan Logistik', 'Information and Communication Technology'.",
        "max_rounds": 2
    },
    "Alamat": {
        "desc": "Alamat lengkap kantor pusat (Jalan, Kelurahan, Kecamatan, Kota, Kode Pos).",
        "max_rounds": 3
    },
    "Kontak": {
        "desc": "Email dan nomor telepon utama perusahaan yang dapat dihubungi untuk kerjasama.",
        "max_rounds": 2
    },
    "Potensi Polis": {
        "desc": "Klasifikasi kebutuhan asuransi berdasarkan Short Description & Sektor Perusahaan. Pilih dari: MV4, TPL, PA, MV2, Properti, Travel, Cargo.",
        "max_rounds": 1
    },
    "Jumlah Karyawan": {
        "desc": "Total jumlah karyawan aktif terbaru di perusahaan tersebut (dalam bentuk angka ataupun range). Contoh: '100-200', '1500'.",
        "max_rounds": 3
    },
    "Short Description": {
        "desc": "Deskripsi singkat terkait bisnis perusahaan (1-3 kalimat). Fokus pada produk/jasa utama",
        "max_rounds": 2
    },
    "Kantor Cabang": {
        "desc": "Jumlah kantor cabang yang dimiliki perusahaan tersebut di seluruh indonesia. Tambahkan terkait list informasi detail wilayah kota kantor cabangnya. Contoh: '3 Kantor Cabang (Surabaya, Semarang, Denpasar).",
        "max_rounds": 3
    },
    "PIC Perusahaan": {
        "desc": "Nama Key Person (CEO/Owner/Direktur). Contoh: 'Royan Rosyad (CEO)'.",
        "max_rounds": 3
    },
    "Laporan Keuangan": {
        "desc": "Revenue atau Laba tahun terbaru 2025 (jika ada). Contoh: 'Revenue 500 Miliar Rupiah (2025)'.",
        "max_rounds": 3
    }
}
class ResearchPipeline:
    def __init__(self, tavily_client: TavilyClient, azure_client: AsyncAzureOpenAI, deployment_name: str):
        self.tavily = tavily_client
        self.client = azure_client
        self.deployment = deployment_name

    async def generate_subqueries(self, company_name: str, missing_fields: List[str], round_num: int) -> List[str]:
        prompt = f"""
        Target Company: {company_name}
        Missing Fields: {', '.join(missing_fields)}
        Round: {round_num}
       
        Generate 3-5 specific search queries to find the missing information.
        If this is a later round, try different keywords or specific document types (e.g., 'Annual Report', 'LinkedIn', 'Contact Us page').
        Return ONLY a JSON list of strings. Example: ["query1", "query2"]
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=[{"role": "user", "content": prompt}],
                temperature=1
            )
            content = response.choices[0].message.content

            if content is None:
                raise ValueError("No content returned from LLM")
           
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            return json.loads(content.strip())
        except Exception as e:
            logger.warning(f"Failed to parse query JSON: {e}, using fallback")
            return [f"{company_name} {field}" for field in missing_fields]
       
    async def perform_search(self, queries: List[str]) -> str:
        """Perform Tavily search for a list of queries and aggregrate results."""
        aggregrated_content = []
       
        # Deduplicate queries
        unique_queries = list(set(queries))

        # Limit to 5 queries
        for query in unique_queries[:5]:
            try:
                logger.info(f"Searching: {query}")
                result = await asyncio.to_thread(
                    self.tavily.search,
                    query=query,
                    search_depth="basic",
                    max_results=3,
                    include_raw_content=False,
                    include_answer=True
                )
                for res in result.get("results", []):
                    snippet = res.get("content") or res.get("snippet", "")
                    aggregrated_content.append(f"Source: {res.get('url')}\nContent: {snippet[:500]}")
            except Exception as e:
                logger.error(f"Search failed for query '{query}': {e}")

        return "\n\n".join(aggregrated_content)
   
    async def extract_and_evaluate(self, company_name: str, content: str, current_fields: Dict[str, EnrichmentField]) -> Dict[str, EnrichmentField]:
        """Extract information from search tool content and update fields."""

        # Identify fields that still need enrichment (Low confidence or 'Tidak Tersedia')
        target_fields = [k for k, v in current_fields.items() if v.value == "Tidak Tersedia" or v.confidence == "Low"]
        if not target_fields:
            return current_fields
       
        schema_desc = {k: ENRICHMENT_SCHEMA[k]["desc"] for k in target_fields}
       
        prompt = f"""
        You're a Data Extraction Specialist.
        Company: {company_name}
       
        Search results:
        {content[:15000]} # Limit to first 15000 characters

        Task: Extract information for the following fields based on the search results.
        Fields to find: {json.dumps(schema_desc, indent=2)}

        Instructions:
        1. If found, extract the value concisely.
        2. Assign a confidence level: 'High (explicitly found), 'Medium' (inferred)', 'Low' (not found/uncertain).
        3. Return JSON format: {{ "Field Name": {{"value": "...", "confidence": "..."}} }}
        """

        try:
            response = await self.client.chat.completions.create(
                model = self.deployment,
                messages=[{"role": "user", "content": prompt}],
                temperature=1
            )
            content_response = response.choices[0].message.content

            if content_response is None:
                raise ValueError("No content returned from LLM")

            # parse response

            if "```json" in content_response:
                content_response = content_response.split("```json")[1].split("```")[0]
            elif "```" in content_response:
                content_response = content_response.split("```")[1].split("```")[0]
           
            extracted_data = json.loads(content_response.strip())

            # Update state
            for field, data in extracted_data.items():
                if field in current_fields:
                    # Only update if found something better
                    if data.get("value") != "Tidak Tersedia":
                        current_fields[field].value = data.get("value")
                        current_fields[field].confidence = data.get("confidence")
        except Exception as e:
            logger.error(f"Extraction failed: {e}")

        return current_fields
   
    async def run_research(self, company_name: str, max_global_rounds: int = 3) -> CompanyProfileState:
        fields = {k: EnrichmentField() for k in ENRICHMENT_SCHEMA.keys()}
        state = CompanyProfileState(company_name=company_name, fields=fields)

        logger.info(f"Starting research for {company_name}")
       
        for round_num in range(1, max_global_rounds + 1):
            logger.info(f"--- Pencarian ke- {round_num} ---")
            state.iteration_logs.append(f"Starting search round {round_num}")

            # Identify missing fields
            missing_fields = [
                k for k, v in state.fields.items()
                if (v.value == "Tidak Tersedia" or v.confidence == "Low")
                and v.rounds_taken < ENRICHMENT_SCHEMA[k]["max_rounds"]
            ]
            if not missing_fields:
                logger.info("All fields enriched or max rounds reached.")
                state.iteration_logs.append("All fields enriched")
                break
           
            logger.info(f"Looking for: {', '.join(missing_fields)}")

            # Generate Queries
            queries = await self.generate_subqueries(company_name, missing_fields, round_num)
            logger.info(f"Generated Queries: {queries}")

            # Perform Search
            content = await self.perform_search(queries)
            if not content or content == "No search resuls available":
                logger.info("No new information found in search.")
                continue
           
            # Extract and Evaluate
            state.fields = await self.extract_and_evaluate(company_name, content, state.fields)

            # Update rounds count for checked fields
            for f in missing_fields:
                state.fields[f].rounds_taken += 1

        return state