import time
from typing import Optional
from urllib.parse import urlparse


def _domain(url: str) -> str:
    """Extract domain from URL."""
    return urlparse(url).netloc


def _favicon(url: str) -> str:
    """Generate Google favicon URL for a domain."""
    d = _domain(url)
    return f"https://www.google.com/s2/favicons?domain={d}&sz=32"


def make_event(phase: str, message: str, round_num: Optional[int] = None) -> dict:
    """Create a base research event."""
    return {
        "phase": phase,
        "message": message,
        "round_num": round_num,
        "timestamp": time.time(),
    }


def thinking_event(message: str, round_num: Optional[int] = None) -> dict:
    """Create a thinking phase event (AI is reasoning)."""
    e = make_event("thinking", message, round_num)
    e["is_active"] = True
    return e


def searching_event(queries: list, round_num: int) -> dict:
    """Create a searching phase event with query list."""
    e = make_event("searching", "Running web search queries", round_num)
    e["queries"] = queries
    e["query_count"] = len(queries)
    e["queries_preview"] = ", ".join(queries[:3])
    return e


def reading_event(sources: list, round_num: int) -> dict:
    """Create a reading phase event with source cards."""
    normalized = []
    for s in sources:
        u = s.get("url", "")
        normalized.append({
            "url": u,
            "title": s.get("title", "Untitled"),
            "domain": _domain(u),
            "favicon": _favicon(u),
        })
    e = make_event("reading", "Reviewing sources", round_num)
    e["sources"] = normalized
    e["source_count"] = len(normalized)
    e["sources_preview"] = ", ".join([s["domain"] for s in normalized[:3]])
    return e


def analyzing_event(message: str, round_num: int) -> dict:
    """Create an analyzing phase event (extracting data)."""
    e = make_event("analyzing", message, round_num)
    e["is_active"] = True
    return e


def complete_event(message: str) -> dict:
    """Create a completion event."""
    return make_event("complete", message)
