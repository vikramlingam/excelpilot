from pathlib import Path

from excelpilot.analysis.pdf_parser import (
    _line_items_from_text,
    _peel_amount,
    _stack_tables,
    default_ingest_instruction,
    extract_from_base64,
    extract_pdf_bytes,
    suggested_sheet_name,
    tables_to_markdown,
)


def test_suggested_sheet_name_strips_extension_and_illegal_chars():
    assert suggested_sheet_name("Q1 Invoice.pdf") == "Q1 Invoice"
    assert suggested_sheet_name("a/b:c*.pdf") == "a b c"
    assert len(suggested_sheet_name("x" * 80 + ".pdf")) == 31


def test_default_ingest_instruction_names_sheet():
    text = default_ingest_instruction("Bank Statement.pdf")
    assert "Bank Statement" in text
    assert "table" in text.lower()
    assert "autofit" in text.lower()


def test_tables_to_markdown_builds_header():
    md = tables_to_markdown([[["Item", "Qty"], ["Widget", "2"]]])
    assert "| Item | Qty |" in md
    assert "| Widget | 2 |" in md


def test_extract_rejects_non_pdf_base64():
    result = extract_from_base64("not-a-pdf", "foo.pdf")
    assert result.error
    assert result.tables == []


def test_peel_amount():
    assert _peel_amount(["Service", "revenue", "$2,750"]) == ("Service revenue", "$2,750")
    assert _peel_amount(["Dividends", "declared", "(500)"]) == ("Dividends declared", "(500)")
    assert _peel_amount(["Operating", "Expenses:"]) == ("Operating Expenses:", "")


def test_line_items_from_text():
    tables = _line_items_from_text("Service revenue $2,750\nWages 1,200\nNet income $945")
    assert tables
    assert tables[0][0] == ["Line item", "Amount"]
    assert any(row[1] == "$2,750" for row in tables[0])


def test_stack_tables_pads_and_spans():
    grid, spans = _stack_tables([[["A", "1"], ["B", "2"]], [["C", "3", "x"]]])
    assert spans[0] == (1, 2, 2)
    assert spans[1][0] == 4
    assert all(len(r) == 3 for r in grid)


def test_extract_pdf_bytes_reads_text():
    data = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R"
        b"/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
        b"4 0 obj<</Length 88>>stream\n"
        b"BT /F1 12 Tf 72 720 Td (Item Amount) Tj 0 -20 Td (Widget 12.50) Tj ET\n"
        b"endstream\nendobj\n"
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n"
        b"0000000115 00000 n \n0000000266 00000 n \n0000000404 00000 n \n"
        b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n479\n%%EOF\n"
    )
    result = extract_pdf_bytes(data, "Invoice.pdf")
    assert result.sheet_name == "Invoice"
    assert result.page_count >= 1


def test_sample_financial_statements_extracts_line_items():
    pdf = Path("/Users/vikramlingam/Desktop/Sample-Financial-Statements-1.pdf")
    if not pdf.exists():
        return
    result = extract_pdf_bytes(pdf.read_bytes(), pdf.name)
    assert result.excel_grids(), f"expected tables, got method={result.method} err={result.error}"
    blob = " ".join(c for t in result.tables for r in t for c in r).lower()
    assert "net income" in blob or "service revenue" in blob
