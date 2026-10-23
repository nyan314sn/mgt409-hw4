"""Append-only audit trail of agent-loop activity: output/audit_trail.json.

The file is always a valid JSON array, but it is only ever *appended to*: new entries are
written by overwriting the closing "]" at the very end of the file, so earlier entries are
never rewritten, reordered, or wiped - not between requests, not between server runs.

One entry per step of the agent loop:
  {"time", "run_id", "kind", "user", "step", "event", "tool", "args", "result", "stop_reason", ...}
- event "tool_call": a tool the model called, with short args and a short result.
- event "final":     the run's end - stop reason, the reply (short), tokens, estimated cost.
- event "error":     the run failed - stop reason "request_limit" or "error: <Type>".
"""
import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

from settings import HW_DIR

log = logging.getLogger("campus_customs")
_lock = threading.Lock()
SHORT = 200  # max characters kept for args/results


def audit_path() -> Path:
    return Path(os.getenv("AUDIT_TRAIL_PATH", HW_DIR / "output" / "audit_trail.json"))


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def short(value, limit: int = SHORT) -> str:
    """Compact text for args/results: JSON for structured data, truncated."""
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    elif isinstance(value, list):
        value = [v.model_dump(mode="json") if hasattr(v, "model_dump") else v for v in value]
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def short_result(content) -> str:
    """One readable line per tool result - the facts the agent got back, not the whole object."""
    from models import DescriptionInfo, LookupMiss, PageInfo, PriceInfo, ProductSummary, StockReport

    if isinstance(content, StockReport):
        asked = (f"{content.requested_size}: {content.requested_size_quantity} ({content.requested_size_status})"
                 if content.requested_size else "all sizes")
        sold_out = ", ".join(content.sold_out_sizes) or "none"
        return short(f"{content.product.name} · {asked} · sold out: {sold_out} · total {content.total_in_stock}")
    if isinstance(content, PriceInfo):
        return short(f"{content.product.name} · ${content.price:.2f}")
    if isinstance(content, DescriptionInfo):
        return short(f"{content.product.name} · {content.category} · colors: {', '.join(content.colors)}")
    if isinstance(content, LookupMiss):
        names = ", ".join(s.name for s in content.suggestions) or "no suggestions"
        return short(f"miss ({content.reason}) for '{content.query}' · {names}")
    if isinstance(content, PageInfo):
        on = content.product.name if content.product else content.page_type
        return short(f"page: {on} · spotlight: {len(content.spotlight)} cards")
    if isinstance(content, list) and all(isinstance(p, ProductSummary) for p in content):
        return short(f"{len(content)} results: " + ", ".join(f"{p.id} ${p.price:.0f}" for p in content))
    return short(content)


def append(entries: list[dict]) -> None:
    """Append entries to the audit file without touching what's already there."""
    if not entries:
        return
    path = audit_path()
    chunk = ",\n".join(json.dumps(e, ensure_ascii=False) for e in entries).encode("utf-8")
    try:
        with _lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists() or path.stat().st_size == 0:
                path.write_bytes(b"[\n" + chunk + b"\n]\n")
                return
            with open(path, "r+b") as f:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                back = min(size, 4096)
                f.seek(size - back)
                tail = f.read()
                close = tail.rfind(b"]")
                if close == -1:
                    # Never "repair" by rewriting: keep the file as is and say so.
                    log.error("Audit trail %s does not end with ']'; not appending.", path)
                    return
                empty = tail[:close].rstrip().endswith(b"[")
                f.seek(size - back + close)
                f.write((b"\n" if empty else b",\n") + chunk + b"\n]\n")
                f.truncate()
    except OSError:
        log.exception("Could not write audit trail %s", path)
