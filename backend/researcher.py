import asyncio
import json
import logging
import re
import time as _time
from urllib.parse import urlparse
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from tavily import TavilyClient
from openai import AzureOpenAI, AsyncAzureOpenAI
from backend.guideline_policy import infer_potensi_polis
from backend.research_events import thinking_event, searching_event, reading_event, analyzing_event, complete_event

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Setup console handler dengan INFO format jika belum ada
if not logger.handlers:
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

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
        "desc": "Klasifikasi kebutuhan asuransi. Dihitung otomatis dari sektor, deskripsi, jumlah karyawan, dan kantor cabang menggunakan guideline rules. JANGAN di-search.",
        "max_rounds": 0
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

# --- Field Tier Classification ---
TIER_1_FIELDS = ["Sektor Perusahaan", "Short Description", "Jumlah Karyawan", "Kantor Cabang"]
TIER_2_FIELDS = ["Alamat", "Kontak", "PIC Perusahaan"]
TIER_3_FIELDS = ["Laporan Keuangan"]

CORE_FIELDS = ["Sektor Perusahaan", "Short Description", "Jumlah Karyawan"]

def should_continue_search(fields: dict) -> bool:
    """Return False when core fields are all High confidence."""
    return not all(
        fields.get(f, EnrichmentField()).confidence == "High"
        for f in CORE_FIELDS
    )

NOT_FOUND_REASONS = {
    "Kontak": "Tidak ditemukan di sumber publik",
    "PIC Perusahaan": "Tidak ditemukan di sumber publik",
    "Laporan Keuangan": "Tidak tersedia (data keuangan non-publik)",
    "Kantor Cabang": "Tidak ditemukan informasi cabang",
    "Alamat": "Tidak ditemukan alamat lengkap",
}

def format_not_found(field_name: str) -> str:
    """Return a field-specific 'not found' reason instead of generic text."""
    return NOT_FOUND_REASONS.get(field_name, "Tidak ditemukan")

MAX_SEARCH_SECONDS = 45

TAVILY_SEARCH_CONFIG = {
    "search_depth": "advanced",
    "max_results": 5,
    "country": "indonesia",
    "include_raw_content": False,
    "include_answer": False,
    "exclude_domains": [
        "facebook.com",
        "instagram.com",
        "twitter.com",
        "x.com",
        "tiktok.com",
        "youtube.com",
        "pinterest.com",
    ],
}

TAVILY_EXTRACT_CONFIG = {
    "extract_depth": "advanced",
    "chunks_per_source": 3,
    "timeout": 45.0,
}

def is_time_budget_exceeded(start_time: float, max_seconds: int = MAX_SEARCH_SECONDS) -> bool:
    """Return True when elapsed time exceeds the budget."""
    return (_time.time() - start_time) > max_seconds


def build_extract_query(missing_fields: list) -> str:
    """Build focused extraction guidance for Tavily extract."""
    field_hints = {
        "Kontak": "kontak resmi (email, telepon, whatsapp)",
        "Alamat": "alamat kantor pusat lengkap",
        "PIC Perusahaan": "nama pimpinan (CEO/Owner/Direktur)",
    }
    selected = [field_hints.get(field, field.lower()) for field in missing_fields]
    if not selected:
        selected = ["profil perusahaan"]
    ordered_selected = list(dict.fromkeys(str(item) for item in selected))
    return (
        "Ekstrak bukti untuk: "
        + ", ".join(ordered_selected)
        + ". Return only factual statements from the page."
    )


def normalize_contact_value(raw):
    """Normalize contact object/string into a consistent string value."""
    def _clean(val: str) -> str:
        return re.sub(r"\s+", "", val.strip())

    if isinstance(raw, dict):
        email = _clean(str(raw.get("email", "")))
        phone = _clean(str(raw.get("phone", "")))
        whatsapp = _clean(str(raw.get("whatsapp", "")))

        parts = []
        if email:
            parts.append(f"Email: {email}")
        if phone:
            parts.append(f"Telp: {phone}")
        if whatsapp:
            parts.append(f"WA: {whatsapp}")

        return " | ".join(parts) if parts else "Tidak Tersedia"

    if raw is None:
        return "Tidak Tersedia"

    if isinstance(raw, str):
        candidate = raw.strip()
        if candidate.startswith("{") and candidate.endswith("}"):
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return normalize_contact_value(parsed)
            except json.JSONDecodeError:
                pass

    value = str(raw).strip()
    return value or "Tidak Tersedia"


def curate_candidate_urls(company_name: str, results: list, min_score: float = 0.5) -> list:
    """Curate high-signal URLs from raw Tavily search results."""
    if not results:
        return []

    exclude_domains = set(TAVILY_SEARCH_CONFIG.get("exclude_domains", []))
    company_tokens = [t.lower() for t in re.findall(r"[a-zA-Z0-9]+", company_name) if len(t) > 2]

    curated_urls = []
    seen = set()

    for result in results:
        url = (result or {}).get("url", "")
        if not url:
            continue

        parsed = urlparse(url)
        domain = (parsed.netloc or "").lower().replace("www.", "")
        if not domain:
            continue

        if any(domain == blocked or domain.endswith(f".{blocked}") for blocked in exclude_domains):
            continue

        score = result.get("score")
        try:
            score_value = float(score) if score is not None else 0.0
        except (TypeError, ValueError):
            score_value = 0.0

        title = str(result.get("title", "")).lower()
        content = str(result.get("content") or result.get("snippet") or "").lower()
        token_hit = any(token in domain or token in title or token in content for token in company_tokens)
        if score_value < min_score and not token_hit:
            continue

        normalized_url = url.split("#", 1)[0]
        if normalized_url in seen:
            continue
        seen.add(normalized_url)
        curated_urls.append(normalized_url)

    return curated_urls

def build_search_queries(company_name: str, missing_fields: list) -> list:
    """Build dual-language field-aware queries and preserve insertion order."""
    queries: list = []
    company = company_name.strip()

    tier1_missing = [f for f in missing_fields if f in TIER_1_FIELDS]
    if tier1_missing:
        queries.extend(
            [
                f"{company} company profile industry employee count",
                f"{company} profil perusahaan sektor jumlah karyawan",
                f"{company} business overview products services",
            ]
        )

    if "Kontak" in missing_fields:
        queries.extend(
            [
                f"{company} contact us email phone whatsapp",
                f"{company} kontak resmi email telepon whatsapp",
            ]
        )

    if "Alamat" in missing_fields:
        queries.extend(
            [
                f"{company} headquarters office address",
                f"{company} alamat kantor pusat",
            ]
        )

    if "PIC Perusahaan" in missing_fields:
        queries.extend(
            [
                f"{company} CEO director leadership",
                f"{company} direktur utama CEO owner",
            ]
        )

    if "Laporan Keuangan" in missing_fields:
        queries.extend(
            [
                f"{company} annual report revenue 2024 2025",
                f"{company} laporan keuangan pendapatan 2024 2025",
            ]
        )

    ordered_unique = list(dict.fromkeys(queries))
    return ordered_unique[:8]

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
                temperature=0.2
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
       
    async def extract_from_urls(self, urls: List[str], missing_fields: List[str]) -> List[dict]:
        """Extract richer evidence from curated URLs using Tavily extract."""
        if not urls:
            return []
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.tavily.extract,
                    urls=urls,
                    query=build_extract_query(missing_fields),
                    **TAVILY_EXTRACT_CONFIG,
                ),
                timeout=TAVILY_EXTRACT_CONFIG["timeout"],
            )
            return response.get("results", []) if isinstance(response, dict) else []
        except asyncio.TimeoutError:
            logger.error("Extraction from curated URLs timed out")
            return []
        except Exception as e:
            logger.error(f"Extraction from curated URLs failed: {e}")
            return []

    async def perform_search(self, company_name: str, queries: List[str], missing_fields: List[str]):
        """Run Tavily search in parallel, curate URLs, then run extraction."""
        unique_queries = list(dict.fromkeys(queries))[:8]

        tasks = [
            asyncio.to_thread(
                self.tavily.search,
                query=query,
                **TAVILY_SEARCH_CONFIG,
            )
            for query in unique_queries
        ]
        try:
            search_outputs = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=MAX_SEARCH_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.error("Parallel Tavily search timed out")
            search_outputs = []

        raw_results = []
        for query, output in zip(unique_queries, search_outputs):
            if isinstance(output, Exception):
                logger.error(f"Search failed for query '{query}': {output}")
                continue
            if not isinstance(output, dict):
                continue
            raw_results.extend(output.get("results", []))

        curated_urls = curate_candidate_urls(company_name, raw_results)
        curated_set = {url.split("#", 1)[0] for url in curated_urls}
        extracted_results = await self.extract_from_urls(curated_urls, missing_fields)

        aggregated_content = []
        for item in extracted_results:
            snippet = item.get("raw_content") or item.get("content") or ""
            aggregated_content.append(f"Source: {item.get('url')}\nContent: {snippet[:1800]}")

        if not aggregated_content:
            for res in raw_results:
                if (res.get("url") or "").split("#", 1)[0] in curated_set:
                    snippet = res.get("content") or res.get("snippet", "")
                    aggregated_content.append(f"Source: {res.get('url')}\nContent: {snippet[:1200]}")

        collected_sources = []
        seen_sources = set()
        for res in raw_results:
            url = res.get("url")
            normalized_url = (url or "").split("#", 1)[0]
            if normalized_url in curated_set and normalized_url not in seen_sources:
                seen_sources.add(normalized_url)
                collected_sources.append({"url": normalized_url, "title": res.get("title", "Untitled")})

        return "\n\n".join(aggregated_content), collected_sources

    async def perform_search_stream(self, company_name: str, queries: List[str], missing_fields: List[str]):
        """Perform Tavily search pipeline and stream progress logs."""
        unique_queries = list(dict.fromkeys(queries))[:8]
        for query in unique_queries:
            yield ("log", f"Searching: {query}")

        tasks = [
            asyncio.to_thread(
                self.tavily.search,
                query=query,
                **TAVILY_SEARCH_CONFIG,
            )
            for query in unique_queries
        ]
        try:
            search_outputs = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=MAX_SEARCH_SECONDS,
            )
        except asyncio.TimeoutError:
            yield ("log", "Search timeout reached")
            search_outputs = []

        raw_results = []
        for query, output in zip(unique_queries, search_outputs):
            if isinstance(output, Exception):
                yield ("log", f"Search failed for query '{query}': {output}")
                continue
            if not isinstance(output, dict):
                continue
            results_count = len(output.get("results", []))
            raw_results.extend(output.get("results", []))
            yield ("log", f"Search completed: {query} ({results_count} results)")

        curated_urls = curate_candidate_urls(company_name, raw_results)
        curated_set = {url.split("#", 1)[0] for url in curated_urls}
        yield ("log", f"Curated URLs: {len(curated_urls)}")

        extracted_results = await self.extract_from_urls(curated_urls, missing_fields)
        yield ("log", f"Extracted results: {len(extracted_results)}")

        aggregated_content = []
        if extracted_results:
            for item in extracted_results:
                snippet = item.get("raw_content") or item.get("content") or ""
                aggregated_content.append(f"Source: {item.get('url')}\nContent: {snippet[:1800]}")
        else:
            for res in raw_results:
                if (res.get("url") or "").split("#", 1)[0] in curated_set:
                    snippet = res.get("content") or res.get("snippet", "")
                    aggregated_content.append(f"Source: {res.get('url')}\nContent: {snippet[:1200]}")

        collected_sources = []
        seen_sources = set()
        for res in raw_results:
            url = res.get("url")
            normalized_url = (url or "").split("#", 1)[0]
            if normalized_url in curated_set and normalized_url not in seen_sources:
                seen_sources.add(normalized_url)
                collected_sources.append({"url": normalized_url, "title": res.get("title", "Untitled")})

        yield ("sources", collected_sources)
        yield ("result", "\n\n".join(aggregated_content))
   
    async def extract_and_evaluate(self, company_name: str, content: str, current_fields: Dict[str, EnrichmentField]) -> Dict[str, EnrichmentField]:
        """Extract information from search tool content and update fields."""

        # Identify fields that still need enrichment (Low confidence or 'Tidak Tersedia')
        target_fields = [k for k, v in current_fields.items() if v.value == "Tidak Tersedia" or v.confidence == "Low"]
        if not target_fields:
            return current_fields
       
        schema_desc = {k: ENRICHMENT_SCHEMA[k]["desc"] for k in target_fields}
       
        prompt = f"""
        You're a Data Extraction Specialist for Insurance Lead Enrichment.
        Company: {company_name}
       
        Search results:
        {content[:15000]}

        Task: Extract information for the following fields based on the search results.
        Fields to find: {json.dumps(schema_desc, indent=2)}

        IMPORTANT GUIDELINES:
        - For 'Sektor Perusahaan': identify the primary industry sector in max 5 words
        - For 'Alamat': extract full headquarters address (street, city, postal code)
        - For 'Kontak': return value as object with keys email, phone, whatsapp
        - For 'Jumlah Karyawan': extract exact number or range of active employees
        - For 'Short Description': write 1-3 sentences about core business/products
        - For 'Kantor Cabang': list number of branches and their city locations
        - For 'PIC Perusahaan': find CEO/Owner/Director name and title
        - For 'Laporan Keuangan': find latest revenue or profit figures (preferably 2024-2025)
        - Do NOT fill 'Potensi Polis' - it will be calculated separately

        Instructions:
        1. If found, extract the value concisely.
        2. Assign a confidence level: 'High' (explicitly found), 'Medium' (inferred), 'Low' (not found/uncertain).
        3. Include the source URL where the info was found.
        4. Return JSON format: {{ "Field Name": {{"value": "...", "confidence": "...", "source": "..."}} }}
        5. For 'Kontak', value MUST be an object: {{"email": "...", "phone": "...", "whatsapp": "..."}}
        """

        try:
            response = await self.client.chat.completions.create(
                model = self.deployment,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
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
                        value = data.get("value")
                        if field == "Kontak":
                            value = normalize_contact_value(value)
                        current_fields[field].value = value
                        current_fields[field].confidence = data.get("confidence")
                        current_fields[field].source = data.get("source", "")
        except Exception as e:
            logger.error(f"Extraction failed: {e}")

        return current_fields
   
    async def run_research(self, company_name: str, max_global_rounds: int = 2) -> CompanyProfileState:
        fields = {k: EnrichmentField() for k in ENRICHMENT_SCHEMA.keys()}
        state = CompanyProfileState(company_name=company_name, fields=fields)

        logger.info(f"Starting research for {company_name}")
        state.iteration_logs.append(f"INFO:backend.researcher:Starting research for {company_name}")

        _start = _time.time()
       
        for round_num in range(1, max_global_rounds + 1):
            if is_time_budget_exceeded(_start):
                logger.info("Time budget exceeded, finalizing results")
                state.iteration_logs.append("INFO:backend.researcher:Time budget exceeded, finalizing results")
                break

            logger.info(f"--- Pencarian ke- {round_num} ---")
            state.iteration_logs.append(f"INFO:backend.researcher:--- Pencarian ke- {round_num} ---")

            # Identify missing fields
            missing_fields = [
                k for k, v in state.fields.items()
                if (v.value == "Tidak Tersedia" or v.confidence == "Low")
                and v.rounds_taken < ENRICHMENT_SCHEMA[k]["max_rounds"]
            ]
            if not missing_fields:
                logger.info("All fields enriched or max rounds reached.")
                state.iteration_logs.append("INFO:backend.researcher:All fields enriched or max rounds reached.")
                break
           
            logger.info(f"Looking for: {', '.join(missing_fields)}")
            state.iteration_logs.append(f"INFO:backend.researcher:Looking for: {', '.join(missing_fields)}")

            # Generate Queries
            queries = build_search_queries(company_name, missing_fields)
            logger.info(f"Generated Queries: {queries}")
            state.iteration_logs.append(f"INFO:backend.researcher:Generated Queries: {queries}")

            # Perform Search
            content, _ = await self.perform_search(company_name, queries, missing_fields)
            if not content or content == "No search results available":
                logger.info("No new information found in search.")
                state.iteration_logs.append("INFO:backend.researcher:No new information found in search.")
                continue
           
            # Extract and Evaluate
            state.fields = await self.extract_and_evaluate(company_name, content, state.fields)

            # Update rounds count for checked fields
            for f in missing_fields:
                state.fields[f].rounds_taken += 1

            # Early stop if core fields are complete
            if not should_continue_search(state.fields):
                logger.info("Core fields enriched, stopping early")
                state.iteration_logs.append("INFO:backend.researcher:Core fields enriched, stopping early")
                break

        # Post-process: derive Potensi Polis from enriched fields
        potensi = infer_potensi_polis(
            sektor=state.fields["Sektor Perusahaan"].value,
            short_description=state.fields["Short Description"].value,
            jumlah_karyawan=state.fields["Jumlah Karyawan"].value,
            kantor_cabang=state.fields["Kantor Cabang"].value,
        )
        state.fields["Potensi Polis"].value = potensi
        # Determine confidence based on input completeness
        _input_count = sum(1 for v in [
            state.fields["Sektor Perusahaan"].value,
            state.fields["Short Description"].value,
            state.fields["Jumlah Karyawan"].value,
            state.fields["Kantor Cabang"].value,
        ] if v not in ("Tidak Tersedia", "") and v.strip())

        if potensi == "Tidak Tersedia":
            _polis_confidence = "Low"
        elif _input_count >= 3:
            _polis_confidence = "High"
        else:
            _polis_confidence = "Medium"
        state.fields["Potensi Polis"].confidence = _polis_confidence
        state.fields["Potensi Polis"].source = "GuidelinePolicyEngine"

        # Replace generic "Tidak Tersedia" with field-specific reasons
        for _field_name, _field_data in state.fields.items():
            if _field_data.value == "Tidak Tersedia":
                _field_data.value = format_not_found(_field_name)

        return state

    async def run_research_stream(
        self, company_name: str, max_global_rounds: int = 2
    ):
        fields = {k: EnrichmentField() for k in ENRICHMENT_SCHEMA.keys()}
        state = CompanyProfileState(company_name=company_name, fields=fields)

        log_message = "Starting research"
        state.iteration_logs.append(log_message)
        yield ("log", log_message)
        yield ("event", thinking_event("Starting research for " + company_name))

        _start = _time.time()

        for round_num in range(1, max_global_rounds + 1):
            if is_time_budget_exceeded(_start):
                log_message = "Time budget exceeded, finalizing results"
                state.iteration_logs.append(log_message)
                yield ("log", log_message)
                break

            log_message = f"Starting search round {round_num}"
            state.iteration_logs.append(log_message)
            yield ("log", log_message)
            yield ("event", thinking_event(f"Planning search round {round_num}", round_num))

            # Identify missing fields
            missing_fields = [
                k for k, v in state.fields.items()
                if (v.value == "Tidak Tersedia" or v.confidence == "Low")
                and v.rounds_taken < ENRICHMENT_SCHEMA[k]["max_rounds"]
            ]
            if not missing_fields:
                log_message = "All fields enriched"
                state.iteration_logs.append(log_message)
                yield ("log", log_message)
                break

            log_message = f"Looking for: {', '.join(missing_fields)}"
            state.iteration_logs.append(log_message)
            yield ("log", log_message)

            # Generate Queries
            log_message = "Generating search queries"
            state.iteration_logs.append(log_message)
            yield ("log", log_message)
            queries = build_search_queries(company_name, missing_fields)
            log_message = f"Generated queries: {queries}"
            state.iteration_logs.append(log_message)
            yield ("log", log_message)
            yield ("event", searching_event(queries, round_num))

            # Perform Search
            content = ""
            collected_sources = []
            async for event_type, payload in self.perform_search_stream(company_name, queries, missing_fields):
                if event_type == "log" and isinstance(payload, str):
                    state.iteration_logs.append(payload)
                    yield ("log", payload)
                elif event_type == "result" and isinstance(payload, str):
                    content = payload
                elif event_type == "sources" and isinstance(payload, list):
                    collected_sources = payload

            if collected_sources:
                yield ("event", reading_event(collected_sources, round_num))

            if not content or content == "No search results available":
                log_message = "No new information found in search."
                state.iteration_logs.append(log_message)
                yield ("log", log_message)
                continue

            # Extract and Evaluate
            log_message = "Extracting data from search results"
            state.iteration_logs.append(log_message)
            yield ("log", log_message)
            yield ("event", analyzing_event("Extracting data from search results", round_num))
            state.fields = await self.extract_and_evaluate(company_name, content, state.fields)
            log_message = f"Extraction round {round_num} completed"
            state.iteration_logs.append(log_message)
            yield ("log", log_message)

            # Update rounds count for checked fields
            for f in missing_fields:
                state.fields[f].rounds_taken += 1

            # Early stop if core fields are complete
            if not should_continue_search(state.fields):
                log_message = "Core fields enriched, stopping early"
                state.iteration_logs.append(log_message)
                yield ("log", log_message)
                break

        # Post-process: derive Potensi Polis from enriched fields
        potensi = infer_potensi_polis(
            sektor=state.fields["Sektor Perusahaan"].value,
            short_description=state.fields["Short Description"].value,
            jumlah_karyawan=state.fields["Jumlah Karyawan"].value,
            kantor_cabang=state.fields["Kantor Cabang"].value,
        )
        state.fields["Potensi Polis"].value = potensi
        # Determine confidence based on input completeness
        _input_count = sum(1 for v in [
            state.fields["Sektor Perusahaan"].value,
            state.fields["Short Description"].value,
            state.fields["Jumlah Karyawan"].value,
            state.fields["Kantor Cabang"].value,
        ] if v not in ("Tidak Tersedia", "") and v.strip())

        if potensi == "Tidak Tersedia":
            _polis_confidence = "Low"
        elif _input_count >= 3:
            _polis_confidence = "High"
        else:
            _polis_confidence = "Medium"
        state.fields["Potensi Polis"].confidence = _polis_confidence
        state.fields["Potensi Polis"].source = "GuidelinePolicyEngine"

        # Replace generic "Tidak Tersedia" with field-specific reasons
        for _field_name, _field_data in state.fields.items():
            if _field_data.value == "Tidak Tersedia":
                _field_data.value = format_not_found(_field_name)

        yield ("event", complete_event(f"Research completed for {company_name}"))
        yield ("result", state)
