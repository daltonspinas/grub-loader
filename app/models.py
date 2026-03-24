from pydantic import BaseModel, Field


class OneShotRequest(BaseModel):
    alias: str = Field(..., min_length=1, max_length=64)


class StateResponse(BaseModel):
    fallback_alias: str
    fallback_target: str
    pending_alias: str | None
    pending_target: str | None
    updated_at: str
