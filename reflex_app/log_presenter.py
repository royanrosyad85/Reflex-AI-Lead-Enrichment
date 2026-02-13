def phase_title(event: dict) -> str:
    """Generate display title for a research event phase."""
    phase = event.get("phase", "")
    if phase == "reading":
        return f"READING {event.get('source_count', 0)}"
    if phase == "searching":
        return "SEARCHING"
    if phase == "thinking":
        return "Thinking..."
    if phase == "analyzing":
        return "Analyzing..."
    if phase == "complete":
        return "Complete"
    return phase.upper()
