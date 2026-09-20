import json

from fastapi import WebSocket, WebSocketDisconnect

from excelpilot.agent.context import invalidate_schema_cache
from excelpilot.bridge.router import router
from excelpilot.telemetry import logger


async def handle_bridge_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    # Connect the active OfficeJsBridge instance
    router.officejs_bridge.set_websocket(websocket)
    logger.info("Office.js task-pane add-in connected to bridge")

    try:
        while True:
            text_data = await websocket.receive_text()
            data = json.loads(text_data)

            # Route incoming RPC response back to waiting future
            if "id" in data and ("result" in data or "error" in data):
                router.officejs_bridge.handle_incoming_rpc_response(data)

            # Handle event notifications from Excel (e.g. selection or change events)
            elif "method" in data and data["method"].startswith("event."):
                logger.debug("Received Excel event notification", method=data["method"])
                invalidate_schema_cache()

    except WebSocketDisconnect:
        logger.info("Office.js add-in disconnected from bridge")
        router.officejs_bridge.set_websocket(None)
    except Exception as err:
        logger.error("Error in bridge WebSocket", error=str(err))
        router.officejs_bridge.set_websocket(None)
