from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DemoLoginRequestDto(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True, strict=True)

    username: str | None = Field(default=None, max_length=256, repr=False)
    password: str | None = Field(default=None, max_length=1024, repr=False)


class DemoLoginResponseDto(BaseModel):
    authenticated: bool
    message: str
    request_id: str
    audit_event_id: str
    trace_id: str | None = None
