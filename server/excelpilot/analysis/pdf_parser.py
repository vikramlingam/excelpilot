"""Extract tables and text from an attached PDF for Excel ingestion.

Digital PDFs are parsed with pdfplumber (tables) and pypdf (text fallback).
Scanned / image-only documents can optionally be sent to a multimodal model.
"""

from __future__ import annotations

import base64
import io
import re
from dataclasses import dataclass, field
from typing import Any

MAX_PDF_BYTES = 8 * 1024 * 1024
MAX_PAGES = 20
MAX_PROMPT_CHARS = 24_000
_SHEET_FORBIDDEN = re.compile(r"[\\/*?:\[\]]")
_AMOUNT = re.compile(r"^\$?\(?-?[\d,]+(?:\.\d+)?\)?%?$")


@dataclass
class PdfExtractResult:
    file_name: str
    sheet_name: str
    page_count: int = 0
    tables: list[list[list[str]]] = field(default_factory=list)
    text: str = ""
    markdown: str = ""
    method: str = "none"
    error: str = ""

    def excel_grids(self) -> list[list[list[str]]]:
        return [t for t in self.tables if t and any(any(c for c in row) for row in t)]

    def prompt_block(self) -> str:
        body = self.markdown.strip() or self.text.strip() or "(no tabular or text content extracted)"
        if len(body) > MAX_PROMPT_CHARS:
            body = body[:MAX_PROMPT_CHARS] + "\n…(truncated)"
        err = f"\nParser note: {self.error}" if self.error else ""
        return (
            f'[Attached PDF Document: "{self.file_name}"]\n'
            f"Suggested sheet name: {self.sheet_name}\n"
            f"Pages: {self.page_count}. Extraction: {self.method}. "
            f"Tables found: {len(self.tables)}.{err}\n"
            f"Extracted Tables / Content:\n{body}"
        )


def suggested_sheet_name(file_name: str) -> str:
    stem = re.sub(r"\.pdf$", "", file_name or "PDF", flags=re.IGNORECASE).strip() or "PDF"
    stem = _SHEET_FORBIDDEN.sub(" ", stem)
    stem = re.sub(r"\s+", " ", stem).strip(" '\"") or "PDF"
    return stem[:31]


def default_ingest_instruction(file_name: str) -> str:
    sheet = suggested_sheet_name(file_name)
    return (
        f'Extract the tabular data from this document, create a new sheet named "{sheet}", '
        "insert the data as an official formatted Excel table, and autofit the columns."
    )



def tables_to_markdown(tables: list[list[list[str]]]) -> str:
    chunks: list[str] = []
    for i, table in enumerate(tables, start=1):
        rows = [[(c or "").replace("\n", " ").strip() for c in row] for row in table if row]
        if not rows:
            continue
        width = max(len(r) for r in rows)
        rows = [r + [""] * (width - len(r)) for r in rows]
        header, *body = rows
        if not any(header):
            header = [f"Col{j}" for j in range(1, width + 1)]
        sep = ["---"] * width
        lines = [
            f"### Table {i}",
            "| " + " | ".join(header) + " |",
            "| " + " | ".join(sep) + " |",
        ]
        for row in body:
            lines.append("| " + " | ".join(row) + " |")
        chunks.append("\n".join(lines))
    return "\n\n".join(chunks)


def tables_to_grid(tables: list[list[list[str]]]) -> list[list[str]]:
    """Flatten extracted tables into one grid (blank row between tables)."""
    grid: list[list[str]] = []
    for i, table in enumerate(tables):
        if i:
            grid.append([])
        for row in table:
            grid.append([(c or "").replace("\n", " ").strip() for c in row])
    return grid


def decode_pdf_base64(file_base64: str) -> bytes:
    raw = (file_base64 or "").strip()
    if "," in raw and raw.lower().startswith("data:"):
        raw = raw.split(",", 1)[1]
    try:
        data = base64.b64decode(raw, validate=False)
    except Exception as err:
        raise ValueError(f"Invalid PDF encoding: {err}") from err
    if not data:
        raise ValueError("Empty PDF payload")
    if len(data) > MAX_PDF_BYTES:
        raise ValueError(f"PDF exceeds {MAX_PDF_BYTES // (1024 * 1024)} MB limit")
    if not data.startswith(b"%PDF"):
        raise ValueError("File is not a PDF")
    return data



def extract_pdf_bytes(data: bytes, file_name: str = "document.pdf") -> PdfExtractResult:
    result = PdfExtractResult(file_name=file_name, sheet_name=suggested_sheet_name(file_name))
    if len(data) > MAX_PDF_BYTES:
        result.error = f"PDF exceeds {MAX_PDF_BYTES // (1024 * 1024)} MB limit"
        return result
    try:
        _extract_pdfplumber(data, result)
    except Exception as err:
        result.error = str(err)
    if not result.tables and not result.text.strip():
        try:
            _extract_pypdf_text(data, result)
        except Exception as err:
            result.error = (result.error + "; " if result.error else "") + str(err)
    if not result.tables and result.text.strip():
        text_tables = _line_items_from_text(result.text)
        if text_tables:
            result.tables = text_tables
            result.method = "text-line-items"
    result.markdown = tables_to_markdown(result.tables)
    if not result.markdown and result.text.strip():
        result.markdown = result.text.strip()
        if result.method == "none":
            result.method = "pypdf-text"
    return result


def extract_from_base64(file_base64: str, file_name: str) -> PdfExtractResult:
    try:
        data = decode_pdf_base64(file_base64)
    except ValueError as err:
        return PdfExtractResult(
            file_name=file_name,
            sheet_name=suggested_sheet_name(file_name),
            error=str(err),
        )
    return extract_pdf_bytes(data, file_name)


def _is_amount(s: str) -> bool:
    s = (s or "").strip().replace(" ", "")
    return bool(s) and bool(_AMOUNT.fullmatch(s))


def _peel_amount(texts: list[str]) -> tuple[str, str]:
    texts = [t for t in texts if t]
    amount_parts: list[str] = []
    while texts and _is_amount(texts[-1]):
        amount_parts.insert(0, texts.pop())
    label = " ".join(texts).strip()
    amount = " ".join(amount_parts).strip()
    if not amount and label:
        m = re.search(r"^(.*?)(?:\s+)(\$?\(?-?[\d,]+(?:\.\d+)?\)?%?)$", label)
        if m and _is_amount(m.group(2)):
            label, amount = m.group(1).strip(), m.group(2)
    return label, amount


def _cluster_rows(words: list[dict[str, Any]], ytol: float = 3.5) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for w in sorted(words, key=lambda x: (x["top"], x["x0"])):
        if not rows or abs(rows[-1][0] - w["top"]) > ytol:
            rows.append([w["top"], [w]])
        else:
            rows[-1][1].append(w)
    return rows


def _line_item_tables_from_page(page: Any) -> list[list[list[str]]]:
    words = page.extract_words() or []
    if len(words) < 4:
        return []
    rows = _cluster_rows(words)
    mid = float(page.width) * 0.50
    both = sum(
        1
        for _, ws in rows
        if any(w["x0"] < mid for w in ws) and any(w["x0"] >= mid for w in ws)
    )
    two_col = both >= 5
    blocks: list[list[Any]] = []
    for top, ws in rows:
        if not blocks or top - blocks[-1][-1][0] > 48:
            blocks.append([[top, ws]])
        else:
            blocks[-1].append([top, ws])
    tables: list[list[list[str]]] = []
    for block in blocks:
        grid: list[list[str]] = []
        titles: list[str] = []
        started = False
        for _top, ws in block:
            if two_col:
                left = [w for w in ws if w["x0"] < mid]
                right = [w for w in ws if w["x0"] >= mid]
                ll, la = _peel_amount([w["text"] for w in sorted(left, key=lambda x: x["x0"])])
                rl, ra = _peel_amount([w["text"] for w in sorted(right, key=lambda x: x["x0"])])
                if not any((ll, la, rl, ra)):
                    continue
                if not started and not la and not ra:
                    titles.append(" ".join(x for x in (ll, rl) if x))
                    continue
                started = True
                grid.append([ll, la, rl, ra])
            else:
                label, amt = _peel_amount([w["text"] for w in sorted(ws, key=lambda x: x["x0"])])
                if not label and not amt:
                    continue
                if not started and not amt:
                    titles.append(label)
                    continue
                started = True
                grid.append([label, amt])
        if len(grid) < 2:
            continue
        header = ["Item", "Amount", "Item", "Amount"] if two_col else ["Line item", "Amount"]
        title = " — ".join(titles[:3])
        table = [[title] + [""] * (len(header) - 1), header] + grid if title else [header] + grid
        tables.append(table)
    return tables


def _line_items_from_text(text: str) -> list[list[list[str]]]:
    rows: list[list[str]] = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            if rows and rows[-1] != ["", ""]:
                rows.append(["", ""])
            continue
        label, amt = _peel_amount(line.split())
        rows.append([label or line, amt])
    body = [r for r in rows if any(r)]
    if len(body) < 3:
        return []
    return [[["Line item", "Amount"]] + body]


def _extract_pdfplumber(data: bytes, result: PdfExtractResult) -> None:
    import pdfplumber

    with pdfplumber.open(io.BytesIO(data)) as pdf:
        result.page_count = len(pdf.pages)
        texts: list[str] = []
        ruled: list[list[list[str]]] = []
        lined: list[list[list[str]]] = []
        for page in pdf.pages[:MAX_PAGES]:
            for table in page.extract_tables() or []:
                cleaned = [[(c or "").replace("\n", " ").strip() for c in row] for row in table]
                if any(any(cell) for cell in cleaned):
                    ruled.append(cleaned)
            lined.extend(_line_item_tables_from_page(page))
            page_text = page.extract_text() or ""
            if page_text.strip():
                texts.append(page_text.strip())
        result.text = "\n\n".join(texts)
        if ruled:
            result.tables = ruled
            result.method = "pdfplumber-tables"
        elif lined:
            result.tables = lined
            result.method = "pdfplumber-line-items"
        else:
            result.method = "pdfplumber-text" if result.text else "none"


def _extract_pypdf_text(data: bytes, result: PdfExtractResult) -> None:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    result.page_count = len(reader.pages)
    texts: list[str] = []
    for page in reader.pages[:MAX_PAGES]:
        page_text = page.extract_text() or ""
        if page_text.strip():
            texts.append(page_text.strip())
    result.text = "\n\n".join(texts)
    if result.text:
        result.method = "pypdf-text"


def _col_letter(n: int) -> str:
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s or "A"


def _unique_sheet_name(base: str, existing: set[str]) -> str:
    name = (base or "PDF")[:31]
    if name not in existing:
        return name
    i = 2
    while True:
        suffix = f" {i}"
        cand = name[: 31 - len(suffix)] + suffix
        if cand not in existing:
            return cand
        i += 1


def _stack_tables(tables: list[list[list[str]]]) -> tuple[list[list[str]], list[tuple[int, int, int]]]:
    grid: list[list[str]] = []
    spans: list[tuple[int, int, int]] = []
    for table in tables:
        rows = [
            [(c or "").replace("\n", " ").strip() for c in row]
            for row in table
            if any((c or "").strip() for c in row)
        ]
        if not rows:
            continue
        if grid:
            grid.append([])
        start = len(grid) + 1
        grid.extend(rows)
        end = len(grid)
        cols = max(len(r) for r in rows)
        spans.append((start, end, cols))
    width = max((len(r) for r in grid), default=1)
    padded = [list(r) + [""] * (width - len(r)) for r in grid]
    return padded, spans


async def ingest_extracted(extracted: PdfExtractResult) -> dict[str, Any]:
    """Write extracted tables into a new sheet using existing Excel tools. No LLM."""
    from excelpilot.tools.formatting import autofit, format_range
    from excelpilot.tools.ranges import range_write_values
    from excelpilot.tools.sheets import sheet_add, sheet_list
    from excelpilot.tools.tables import table_create

    tables = extracted.excel_grids()
    if not tables:
        raise ValueError("No tabular content could be extracted from the PDF")

    infos = await sheet_list()
    existing: set[str] = set()
    for s in infos:
        if isinstance(s, dict):
            existing.add(str(s.get("name") or ""))
        else:
            existing.add(str(getattr(s, "name", "") or ""))
    sheet_name = _unique_sheet_name(extracted.sheet_name, existing)
    added = await sheet_add(sheet_name)
    if isinstance(added, dict) and added.get("name"):
        sheet_name = str(added["name"])

    grid, spans = _stack_tables(tables)
    width = max(len(r) for r in grid)
    address = f"A1:{_col_letter(width)}{len(grid)}"
    await range_write_values(sheet_name, address, grid)

    created: list[str] = []
    for i, (start, end, cols) in enumerate(spans, start=1):
        taddr = f"A{start}:{_col_letter(cols)}{end}"
        tname = re.sub(r"[^A-Za-z0-9]", "", extracted.sheet_name)[:20] or "PDF"
        tname = f"{tname}{i}"
        try:
            await table_create(sheet_name, taddr, table_name=tname, has_headers=True)
            created.append(tname)
        except Exception:
            pass
        try:
            await format_range(sheet_name, f"A{start}:{_col_letter(cols)}{start}", font={"bold": True})
        except Exception:
            pass
    try:
        await autofit(sheet_name, address)
    except Exception:
        pass
    return {
        "sheet": sheet_name,
        "address": address,
        "rows": len(grid),
        "cols": width,
        "tables": created,
        "method": extracted.method,
    }


async def maybe_vision_extract(result: PdfExtractResult, data: bytes) -> PdfExtractResult:
    """Optional multimodal fallback for scanned / empty PDFs. Never raises."""
    if result.tables or len(result.text.strip()) >= 40:
        return result
    try:
        from excelpilot.config import settings

        if not settings.openrouter_api_key:
            return result
        import json
        import urllib.error
        import urllib.request

        snippet = result.text.strip()[:4000] or "(no digital text — likely a scanned PDF)"
        payload: dict[str, Any] = {
            "model": "google/gemini-2.5-flash",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Extract every table and line-item list from this document as GitHub-flavored "
                        "Markdown tables. If there are no tables, return key-value pairs as a 2-column "
                        "table (Field | Value). Do not invent numbers.\n\n"
                        f"Filename: {result.file_name}\n{snippet}"
                    ),
                }
            ],
            "temperature": 0,
            "max_tokens": 2000,
        }
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "HTTP-Referer": settings.openrouter_app_url,
                "X-Title": settings.openrouter_app_title,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            result.error = (result.error + "; " if result.error else "") + f"vision HTTP {err.code}"
            return result
        content = (((body or {}).get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        if content.strip():
            result.markdown = content.strip()
            result.method = "vision-fallback"
    except Exception as err:
        result.error = (result.error + "; " if result.error else "") + f"vision skipped: {err}"
    return result

