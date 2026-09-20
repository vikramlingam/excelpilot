from typing import Any

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from excelpilot.agent.jev.client import jev_client
from excelpilot.analysis.report import generate_audit_report
from excelpilot.app.ws_bridge import handle_bridge_websocket
from excelpilot.app.ws_chat import handle_chat_websocket
from excelpilot.bridge.router import router
from excelpilot.config import settings
from excelpilot.telemetry import setup_logging

setup_logging()

app = FastAPI(title="ExcelPilot", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> dict[str, Any]:
    jev_probe = await jev_client.probe()
    active_b = router.active_bridge
    return {
        "status": "ok",
        "active_bridge": active_b.__class__.__name__,
        "bridge_connected": router.officejs_bridge.is_connected,
        "jev": jev_probe,
        "model_fast": settings.openrouter_model,
        "model_capable": settings.openrouter_model_capable,
    }


@app.get("/api/analyze")
async def analyze_workbook_endpoint() -> dict[str, Any]:
    return await generate_audit_report()


@app.websocket("/bridge")
async def bridge_ws_endpoint(websocket: WebSocket) -> None:
    await handle_bridge_websocket(websocket)


@app.websocket("/chat")
async def chat_ws_endpoint(websocket: WebSocket) -> None:
    await handle_chat_websocket(websocket)
