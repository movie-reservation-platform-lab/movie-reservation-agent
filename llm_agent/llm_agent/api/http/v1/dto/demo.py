from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class DemoReservationRequestDto(BaseModel):
    movie_preference: str = Field(default="something exciting", min_length=1, max_length=500)
    seat_preference: str = Field(default="aisle", min_length=1, max_length=100)
    fault: Literal["none", "slow-recommendation", "recommendation-error"] = "none"


class DemoTraceDto(BaseModel):
    trace_id: str | None
    correlation_id: str
    request_id: str


class DemoToolResultDto(BaseModel):
    tool_name: str
    outcome: str


class DemoReservationResponseDto(BaseModel):
    workflow_id: str
    outcome: str
    reservation_status: str | None
    reservation_request_id: str | None
    final_answer: str
    movie: dict[str, Any] | None
    screening: dict[str, Any] | None
    seat: dict[str, Any] | None
    tool_results: list[DemoToolResultDto]
    trace: DemoTraceDto


class DemoReservationErrorDto(BaseModel):
    error: str
    message: str
    workflow_id: str
    trace: DemoTraceDto
