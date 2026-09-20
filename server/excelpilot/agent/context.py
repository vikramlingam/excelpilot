from pathlib import Path
from typing import Any

from excelpilot.bridge.router import router

SKILLS_DIR = Path(__file__).parent / "skills"


def load_skill_prompt(skill_name: str) -> str:
    base_file = SKILLS_DIR / "base.md"
    skill_file = SKILLS_DIR / f"{skill_name}.md"

    base_text = base_file.read_text(encoding="utf-8") if base_file.exists() else ""
    skill_text = skill_file.read_text(encoding="utf-8") if skill_file.exists() else ""

    return f"{base_text}\n\n{skill_text}".strip()


async def build_sheet_schema_card(sheet_name: str) -> dict[str, Any]:
    try:
        used = await router.used_range(sheet_name)
        used_addr = used.address
    except Exception:
        used_addr = "A1"

    # Read top 4 rows for header and sample data
    page = await router.read(
        router.file_bridge.used_range(sheet_name)
        if not router.officejs_bridge.is_connected
        else used,
        values=True,
    )
    rows = page.values or []
    headers = [str(c) for c in rows[0]] if rows else []
    sample = rows[1:4] if len(rows) > 1 else []

    tables = await router.list_tables(sheet_name)
    pivots = await router.list_pivots(sheet_name)
    charts = await router.list_charts(sheet_name)

    return {
        "sheet": sheet_name,
        "used_range": used_addr,
        "headers": headers[:15],
        "sample_rows": sample,
        "tables": [t.get("name") for t in tables],
        "pivots": [p.get("name") for p in pivots],
        "charts": [c.get("name") for c in charts],
    }


def truncate_context_if_needed(text: str, max_chars: int = 40000) -> str:
    if len(text) > max_chars:
        return text[:max_chars] + "\n[Context truncated to remain within token budget]"
    return text
