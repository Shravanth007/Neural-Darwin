from __future__ import annotations

def format_event(row) -> str:
    actor = row["actor"] or "system"
    target = f" -> {row['target']}" if row["target"] else ""
    return f"[tick {row['tick']}] {row['event_type']} | {actor}{target} | {row['details']}"
