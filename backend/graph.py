import asyncio
import hashlib
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional

from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph
from openai import AsyncAzureOpenAI
from tavily import TavilyClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


class SearchCache:
   
    def __init__(self, max_size: int = 100):
        self.cache: Dict[str, Dict] = {}
        self.max_size = max_size
   
    def get_key(self, company: str, column: str) -> str:
        """Generate MD5 hash key from company and column."""
        return hashlib.md5(f"{company}_{column}".encode()).hexdigest()
   
    def get(self, company: str, column: str) -> Optional[Dict]:
        """Retrieve cached result if exists."""
        return self.cache.get(self.get_key(company, column))
   
    def set(self, company: str, column: str, result: Dict):
        """Store result in cache with LRU-like eviction."""
        if len(self.cache) >= self.max_size:
            self.cache.pop(next(iter(self.cache)))
        self.cache[self.get_key(company, column)] = result


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        pass

class AzureOpenAIProvider(LLMProvider):
    def __init__(self, client, deployment_name: str):
        self.client = client
        self.deployment_name = deployment_name

    async def generate(self, prompt: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.deployment_name, messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()


@dataclass
class EnrichmentContext:
    column_name: str
    target_value: str
    context_values: Dict[str, str]
    search_result: Optional[Dict] = None
    answer: Optional[str] = None
# Initialize global search cache
search_cache = SearchCache(max_size=100)


class EnrichmentPipeline:
    def __init__(self, tavily_client, llm_provider: LLMProvider):
        self.tavily = tavily_client
        self.llm = llm_provider

    async def search_tavily(self, state: EnrichmentContext):
        """Run Tavily search with caching and optimized parameters."""
        try:
            # Check cache first
            cached = search_cache.get(state.target_value, state.column_name)
            if cached:
                logger.info(f"Cache hit for {state.target_value} - {state.column_name}")
                return {"search_result": cached}
           
            # Cache miss - perform search
            query = f"{state.column_name} of {state.target_value}?"
            logger.info(f"Searching Tavily: {query} (depth=advanced, max_results=2, raw_content=False, include_answer=True)")
           
            result = await asyncio.to_thread(
                lambda: self.tavily.search(
                    query=query,
                    search_depth="advanced",  # Bisa pilih basic or advanced sesuai kebutuhan
                    max_results=5,  
                    include_raw_content=False,  # Disabled to avoid HTML bloat (~12K tokens saved)
                    include_answers=True
                )
            )
           
            logger.info(f"Tavily search completed with {len(result.get('results', []))} results")
           
            # Store in cache
            search_cache.set(state.target_value, state.column_name, result)
           
            return {"search_result": result}
        except Exception as e:
            logger.error(f"❌ Error in search_tavily: {str(e)}")
            raise

    async def extract_minimal_answer(
        self, state: EnrichmentContext
    ) -> Dict:
        """Use LLM to extract a minimal answer from Tavily's snippet results."""
        # Build content from snippets only (not raw_content) - Fix 2
        result_contents = []
       
        if state.search_result and "results" in state.search_result:
            for result in state.search_result["results"][:5]:  # Max 2 results
                snippet = result.get("content") or result.get("snippet", "")
                if snippet:
                    # Truncate to 500 chars to minimize tokens
                    snippet_truncated = snippet[:500]
                    title = result.get("title", "No title")
                    result_contents.append(
                        f"Title: {title}\nSnippet: {snippet_truncated}"
                    )
       
        content = "\n\n---\n\n".join(result_contents) if result_contents else "No search results available"
       
        logger.info(f"Content prepared: {len(content)} chars (from {len(result_contents)} snippets)")
       
        try:
            # Column-specific extraction rules
            column_rules = {
                "Nama Perusahaan": "Extract official company name only. Max 50 chars.",
                "Sektor Perusahaan": "Extract primary industry sector. Max 50 chars.",
                "Alamat": "Extract headquarters address with city and country. Max 100 chars.",
                "Kontak (Mobile/Email)": "Extract official phone or email contact. Max 50 chars.",
                "Potensi Polis": "Extract insurance needs or risk exposure info. Max 100 chars.",
                "Jumlah Karyawan": "Extract employee count (exact number or range). Max 30 chars.",
                "Produk Perusahaan": "Extract main products/services offered. Max 100 chars.",
                "Kantor Cabang": "Extract branch office locations. Max 100 chars.",
                "Aset Perusahaan": "Extract total assets value if available. Max 50 chars.",
                "Laporan Keuangan": "Extract key financial metrics (revenue/profit). Max 100 chars."
            }
           
            # Get column-specific instruction (with generic fallback)
            column_guideline = column_rules.get(
                state.column_name,
                "Extract the most relevant value for this field. Max 100 chars."
            )
           
            # Optimized prompt - only includes current column rule (Fix 3)
            prompt = f"""You are an Insurance Data Enrichment Agent.

Column: {state.column_name}
Company: {state.target_value}
Instruction: {column_guideline}

Search Results:
{content}

Answer (only the value, no explanation):"""
           
            logger.info(f"Extracting answer for column '{state.column_name}' | company '{state.target_value}'")
            logger.info(f"Prompt size: {len(prompt)} chars")

            answer = await self.llm.generate(prompt)
            logger.info(f"Extracted answer: {answer}")
            return {"answer": answer}
        except Exception as e:
            logger.error(f"❌ Error in extract_minimal_answer: {str(e)}")
            return {"answer": "Information not found"}

    def build_graph(self):
        """build and compile the graph"""
        graph = StateGraph(EnrichmentContext)
        graph.add_node("search", self.search_tavily)
        graph.add_node("extract", self.extract_minimal_answer)
        #graph.add_node("enrich", self.enrich)
        graph.add_edge(START, "search")
        graph.add_edge("search", "extract")
        graph.add_edge("extract", END)
        compiled_graph = graph.compile()
        return compiled_graph


async def enrich_cell_with_graph(
    column_name: str,
    target_value: str,
    context_values: Dict[str, str],
    tavily_client,
    llm_provider: LLMProvider
) -> Dict:
    """Helper function to enrich a single cell using langgraph."""
    try:
        logger.info(f"Starting enrich_cell_with_graph for {target_value}")
        pipeline = EnrichmentPipeline(tavily_client, llm_provider)
        initial_context = EnrichmentContext(
            column_name=column_name,
            target_value=target_value,
            context_values=context_values,
            search_result=None,
            answer=None
        )
        graph = pipeline.build_graph()
        result = await graph.ainvoke(initial_context)
        #print(f"Result: {result}")
        logger.info(f"Completed enrich_cell_with_graph for {target_value}")
        return result #, result['urls']
    except Exception as e:
        logger.error(f"Error in enrich_cell_with_graph: {str(e)}")
        return {"answer": "Error during enrichment", "search_result": None}


# Example usage:
if __name__ == "__main__":
    context = EnrichmentContext(
        column_name="CEO",
        target_value="Amazon",
        context_values={
            "Industry": "E-commerce",
            "Founded": "1994",
            "Location": "Seattle, WA",
        },
    )

    tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
   
    # Example with Azure OpenAI
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
   
    if not azure_endpoint or not deployment_name:
        raise ValueError("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT_NAME must be set")
   
    azure_client = AsyncAzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
        azure_endpoint=azure_endpoint
    )
    azure_provider = AzureOpenAIProvider(
        azure_client,
        deployment_name=deployment_name
    )
    pipeline_azure = EnrichmentPipeline(tavily_client, azure_provider)

    # Using the graph
    graph = pipeline_azure.build_graph()
    initial_context = EnrichmentContext(
        column_name="CEO",
        target_value="Amazon",
        context_values={
            "Industry": "E-commerce",
            "Founded": "1994",
            "Location": "Seattle, WA",
        },
        search_result=None,
        answer=None
    )
    result = asyncio.run(graph.ainvoke(initial_context))

    # Or using the helper function
    result_helper = asyncio.run(enrich_cell_with_graph(
        column_name="CEO",
        target_value="Amazon",
        context_values={
            "Industry": "E-commerce",
            "Founded": "1994",
            "Location": "Seattle, WA",
        },
        tavily_client=tavily_client,
        llm_provider=azure_provider
    ))