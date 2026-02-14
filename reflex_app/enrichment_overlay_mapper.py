from typing import Any, TypedDict


class QueryItem(TypedDict):
    id: str
    text: str
    company: str
    round_num: int
    status: str
    timestamp: float


class SourceItem(TypedDict):
    domain: str
    favicon: str
    url: str
    company: str
    last_seen_at: float


class ProgressItem(TypedDict):
    id: str
    phase: str
    title: str
    subtitle: str
    status: str
    timestamp: float


class StreamMapping(TypedDict):
    progress_item: ProgressItem
    queries: list[QueryItem]
    sources: list[SourceItem]
    phase: str
    phase_key: str
    round_num: int
    query_count: int
    source_count: int


def _status_for_phase(phase: str) -> str:
    if phase == "complete":
        return "done"
    if phase in {"thinking", "searching", "reading", "analyzing"}:
        return "active"
    return "warning"


def _phase_key_for_overlay(phase: str, round_num: int) -> str:
    if phase == "thinking":
        return "planning_again" if round_num > 1 else "planning"
    if phase == "searching":
        return "searching"
    if phase == "reading":
        return "found_sources"
    if phase == "analyzing":
        return "summarizing"
    if phase == "complete":
        return "extracting"
    if phase == "error":
        return "error"
    return "idle"


def map_stream_event_to_updates(payload: dict[str, Any], company: str, now_ts: float) -> StreamMapping:
    phase_raw = payload.get("phase", "")
    phase = phase_raw if isinstance(phase_raw, str) else ""
    if not phase:
        phase = "unknown"

    round_raw = payload.get("round_num", 0)
    try:
        round_num = int(round_raw)
    except (TypeError, ValueError):
        round_num = 0

    message_raw = payload.get("message", "")
    message = message_raw if isinstance(message_raw, str) else ""
    if not message:
        message = "Received malformed research event payload"

    progress_item: ProgressItem = {
        "id": f"{company}-{phase}-{int(now_ts * 1000)}",
        "phase": phase,
        "title": message,
        "subtitle": f"{company}" if company else "",
        "status": _status_for_phase(phase),
        "timestamp": now_ts,
    }

    queries: list[QueryItem] = []
    query_count = 0
    if phase == "searching":
        query_values = payload.get("queries", [])
        if isinstance(query_values, list):
            query_count = len(query_values)
        for idx, query in enumerate(query_values):
            if not isinstance(query, str) or not query.strip():
                continue
            queries.append(
                {
                    "id": f"{company}-r{round_num}-q{idx}",
                    "text": query,
                    "company": company,
                    "round_num": round_num,
                    "status": "active",
                    "timestamp": now_ts,
                }
            )

    sources: list[SourceItem] = []
    source_count = 0
    if phase == "reading":
        source_values = payload.get("sources", [])
        if isinstance(source_values, list):
            source_count = len(source_values)
        for source in source_values:
            if not isinstance(source, dict):
                continue
            domain = str(source.get("domain", "")).strip()
            favicon = str(source.get("favicon", "")).strip()
            url = str(source.get("url", "")).strip()
            if not domain:
                continue
            sources.append(
                {
                    "domain": domain,
                    "favicon": favicon,
                    "url": url,
                    "company": company,
                    "last_seen_at": now_ts,
                }
            )

    return {
        "progress_item": progress_item,
        "queries": queries,
        "sources": sources,
        "phase": phase,
        "phase_key": _phase_key_for_overlay(phase, round_num),
        "round_num": round_num,
        "query_count": query_count,
        "source_count": source_count,
    }
