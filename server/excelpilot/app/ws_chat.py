import json

from fastapi import WebSocket, WebSocketDisconnect

from excelpilot.agent.orchestrator import orchestrator
from excelpilot.app.events import ChatRequest
from excelpilot.telemetry import logger


async def handle_chat_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    logger.info("Task-pane chat client connected")

    try:
        while True:
            text_data = await websocket.receive_text()
            data = json.loads(text_data)
            req = ChatRequest(**data)

            # Stream turn execution events to the client
            async for event in orchestrator.execute_turn(
                user_message=req.message,
                session_id=req.session_id,
                active_sheet=req.active_sheet,
                selection=req.selection,
            ):
                await websocket.send_text(json.dumps(event))

    except WebSocketDisconnect:
        logger.info("Task-pane chat client disconnected")
    except Exception as err:
        logger.error("Error in chat WebSocket", error=str(err))
