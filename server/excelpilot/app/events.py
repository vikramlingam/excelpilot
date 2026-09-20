from typing import Any

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default_session"
    active_sheet: str = "Sheet1"
    selection: str | None = None


class AgentEvent(BaseModel):
    type: str  # text_delta, tool_call, tool_result, intent, tier, approval_required, verified_claims, done, error
    data: dict[str, Any] | None = None
    delta: str | None = None
