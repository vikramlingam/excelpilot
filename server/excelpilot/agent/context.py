import asyncio
import re
import time
from pathlib import Path
from typing import Any

from excelpilot.bridge.models import RangeRef
from excelpilot.bridge.router import router

SKILLS_DIR = Path(__file__).parent / "skills"
_SCHEMA_TTL_S = 45.0
_schema_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def load_skill_prompt(skill_name: str) -> str:
    mapped = "edit" if skill_name == "edit_values" else skill_name
    if skill_name == "pivot_or_chart":
        mapped = "pivot_chart"
    if skill_name == "question_only":
        mapped = "base"
    base_file = SKILLS_DIR / "base.md"
    skill_file = SKILLS_DIR / f"{mapped}.md"
    base_text = base_file.read_text(encoding="utf-8") if base_file.exists() else ""
    skill_text = ""
    if mapped != "base" and skill_file.exists():
        skill_text = skill_file.read_text(encoding="utf-8")
    return f"{base_text}\n\n{skill_text}".strip()


def _first_n_rows_address(used_address: str, n: int = 4) -> str:
    match = re.match(r"^([A-Za-z]+)(\d+):([A-Za-z]+)(\d+)$", used_address.replace("$", ""))
    if not match:
        return "A1:Z4"
    start_col, start_row, end_col, _end_row = match.groups()
    start = int(start_row)
    end = start + n - 1
    return f"{start_col}{start}:{end_col}{end}"


def invalidate_schema_cache(sheet: str | None = None) -> None:
    if sheet is None:
        _schema_cache.clear()
    else:
        _schema_cache.pop(sheet, None)


async def _safe(coro: Any, default: Any) -> Any:
    try:
        return await coro
    except Exception:
        return default


async def build_sheet_schema_card(sheet_name: str, force: bool = False) -> dict[str, Any]:
    cached = _schema_cache.get(sheet_name)
    if not force and cached and (time.monotonic() - cached[0]) < _SCHEMA_TTL_S:
        return cached[1]

    # Two parallel RPCs: used range (for real row counts) + a 4-row sample.
    used, page = await asyncio.gather(
        _safe(router.used_range(sheet_name), None),
        _safe(router.read(RangeRef(sheet=sheet_name, address="A1:Z4"), values=True), None),
    )
    used_addr = used.address if used is not None else "A1:Z4"
    rows = (page.values or []) if page else []
    headers = [str(c) if c is not None else "" for c in rows[0]] if rows else []
    # Trim trailing empty header columns so the model sees the real width.
    while headers and headers[-1] == "":
        headers.pop()
    width = len(headers) or 1
    sample = [r[:width] for r in rows[1:4]] if len(rows) > 1 else []

    card = {
        "sheet": sheet_name,
        "used_range": used_addr,
        "headers": headers[:20],
        "sample_rows": sample,
        "tables": [],
        "pivots": [],
        "charts": [],
    }
    _schema_cache[sheet_name] = (time.monotonic(), card)
    return card


def _col_letter(idx: int) -> str:
    out = ""
    idx += 1
    while idx:
        idx, rem = divmod(idx - 1, 26)
        out = chr(65 + rem) + out
    return out


def compact_schema_for_prompt(card: dict[str, Any]) -> str:
    headers = card.get("headers", [])
    used = str(card.get("used_range", "A1"))
    last_row = re.search(r"(\d+)$", used)
    n_rows = last_row.group(1) if last_row else "?"
    cols = ", ".join(f"{_col_letter(i)}={h}" for i, h in enumerate(headers[:20]) if h) or "(no headers)"
    sample = card.get("sample_rows") or []
    sample_txt = " | ".join(str(r) for r in sample[:2])
    return (
        f"Sheet '{card.get('sheet')}' used range {used} (header row 1, data rows 2-{n_rows}). "
        f"Columns: {cols}. Sample: {sample_txt}"
    )


def truncate_context_if_needed(text: str, max_chars: int = 12000) -> str:
    if len(text) > max_chars:
        return text[:max_chars] + "\n[Context truncated to remain within token budget]"
    return text
