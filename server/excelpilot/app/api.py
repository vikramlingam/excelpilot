from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from excelpilot.agent.jev.client import jev_client
from excelpilot.analysis.report import generate_audit_report
from excelpilot.app.ws_bridge import handle_bridge_websocket
from excelpilot.app.ws_chat import handle_chat_websocket
from excelpilot.bridge.router import router
from excelpilot.config import settings
from excelpilot.telemetry import setup_logging

setup_logging()

app = FastAPI(title="ExcelPilot", version="1.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> dict[str, Any]:
    # Cached/circuit-broken snapshot — never block the UI on a Jev probe.
    active_b = router.active_bridge
    return {
        "status": "ok",
        "active_bridge": active_b.__class__.__name__,
        "bridge_connected": router.officejs_bridge.is_connected,
        "jev": jev_client.status_snapshot(),
        "model_fast": settings.openrouter_model,
        "model_capable": settings.openrouter_model_capable,
    }


@app.get("/api/models")
async def get_models_endpoint() -> dict[str, Any]:
    return {
        "current_fast": settings.openrouter_model,
        "current_capable": settings.openrouter_model_capable,
        "models": [
            {
                "id": "auto",
                "name": "Auto (Smart Routing)",
                "description": "Automatically routes between fast flash & capable models based on prompt complexity.",
                "badge": "Recommended",
                "provider": "ExcelPilot",
            },
            {
                "id": "qwen/qwen3.8-flash",
                "name": "Qwen 3.8 Flash",
                "description": "Ultra-fast, low-latency execution for everyday formulas and data formatting.",
                "badge": "Fast",
                "provider": "Alibaba",
            },
            {
                "id": "qwen/qwen3.8-max-0902",
                "name": "Qwen 3.8 Max",
                "description": "High-capacity reasoning for complex financial modeling and multi-sheet tasks.",
                "badge": "Smart",
                "provider": "Alibaba",
            },
            {
                "id": "anthropic/claude-3.5-sonnet",
                "name": "Claude 3.5 Sonnet",
                "description": "Industry-leading reasoning and coding benchmark for advanced spreadsheet logic.",
                "badge": "Flagship",
                "provider": "Anthropic",
            },
            {
                "id": "openai/gpt-4o",
                "name": "GPT-4o",
                "description": "High-speed flagship multimodal model for complex data tasks.",
                "badge": "Flagship",
                "provider": "OpenAI",
            },
            {
                "id": "openai/gpt-4o-mini",
                "name": "GPT-4o Mini",
                "description": "Fast and lightweight for quick calculations and formula drafting.",
                "badge": "Fast",
                "provider": "OpenAI",
            },
            {
                "id": "google/gemini-2.5-flash",
                "name": "Gemini 2.5 Flash",
                "description": "Google's ultra-fast model with extensive context reasoning.",
                "badge": "Fast",
                "provider": "Google",
            },
            {
                "id": "deepseek/deepseek-chat",
                "name": "DeepSeek V3",
                "description": "Economical and capable model for general Excel automation tasks.",
                "badge": "Value",
                "provider": "DeepSeek",
            },
        ],
    }


@app.get("/api/analyze")
async def analyze_workbook_endpoint() -> dict[str, Any]:
    return await generate_audit_report()


@app.post("/api/upload-pdf")
async def upload_pdf_endpoint(file: UploadFile = File(...)) -> dict[str, Any]:
    """Fast path: extract tables from a PDF without going through the chat WebSocket."""
    name = file.filename or "document.pdf"
    if not name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only .pdf files are supported")
    data = await file.read()
    from excelpilot.analysis.pdf_parser import MAX_PDF_BYTES, extract_pdf_bytes, maybe_vision_extract

    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="PDF exceeds 8 MB limit")
    extracted = extract_pdf_bytes(data, name)
    if not extracted.tables and len((extracted.text or "").strip()) < 40:
        extracted = await maybe_vision_extract(extracted, data)
    return {
        "file_name": extracted.file_name,
        "sheet_name": extracted.sheet_name,
        "page_count": extracted.page_count,
        "method": extracted.method,
        "table_count": len(extracted.tables),
        "markdown": extracted.markdown,
        "prompt_block": extracted.prompt_block(),
        "error": extracted.error,
    }


@app.websocket("/bridge")
async def bridge_ws_endpoint(websocket: WebSocket) -> None:
    await handle_bridge_websocket(websocket)


@app.websocket("/chat")
async def chat_ws_endpoint(websocket: WebSocket) -> None:
    await handle_chat_websocket(websocket)
