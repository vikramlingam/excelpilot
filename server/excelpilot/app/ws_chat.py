import asyncio
import json

from fastapi import WebSocket, WebSocketDisconnect

from excelpilot.agent.orchestrator import orchestrator
from excelpilot.app.events import ChatRequest
from excelpilot.telemetry import logger


async def handle_chat_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    logger.info("Task-pane chat client connected")
    send_lock = asyncio.Lock()
    turn_task: asyncio.Task[None] | None = None

    async def emit(event: dict) -> None:
        async with send_lock:
            await websocket.send_text(json.dumps(event))

    async def run_turn(req: ChatRequest) -> None:
        try:
            await emit({"type": "status", "message": "Analyzing request..."})
            event_count = 0
            async for event in orchestrator.execute_turn(
                user_message=req.message,
                session_id=req.session_id,
                active_sheet=req.active_sheet,
                selection=req.selection,
                selected_model=req.model,
                file_base64=req.file_base64,
                file_name=req.file_name,
            ):
                await emit(event)
                event_count += 1
            if event_count == 0:
                await emit({"type": "done", "full_text": "No response generated.", "cost_usd": 0, "latency_ms": 0})
        except Exception as err:
            logger.error("Error in chat turn", error=str(err))
            try:
                await emit({"type": "error", "message": str(err)})
            except Exception:
                pass

    try:
        while True:
            text_data = await websocket.receive_text()
            data = json.loads(text_data)

            if data.get("type") == "approval":
                orchestrator.resolve_approval(
                    data.get("session_id") or "addin_session",
                    bool(data.get("approved")),
                )
                continue

            req = ChatRequest(**data)
            if turn_task is not None and not turn_task.done():
                await emit({"type": "status", "message": "Still working on the previous request…"})
                continue
            turn_task = asyncio.create_task(run_turn(req))

    except WebSocketDisconnect:
        logger.info("Task-pane chat client disconnected")
        if turn_task and not turn_task.done():
            turn_task.cancel()
    except Exception as err:
        logger.error("Error in chat WebSocket", error=str(err))
        if turn_task and not turn_task.done():
            turn_task.cancel()
