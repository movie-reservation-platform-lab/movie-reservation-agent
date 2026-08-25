from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from llm_agent.demo.models import DemoFault, DemoToolResult
from llm_agent.demo.trace_context import DemoTraceContext


@dataclass(frozen=True)
class ObservedCall:
    tool_name: str
    arguments: dict[str, Any]
    trace_context: DemoTraceContext
    fault: DemoFault


class FakeMcpClient:
    def __init__(
        self,
        *,
        statuses: list[str] | None = None,
        fail_tool: str | None = None,
        timeout_tool: str | None = None,
    ) -> None:
        self._statuses = iter(statuses or ["CONFIRMED"])
        self._fail_tool = fail_tool
        self._timeout_tool = timeout_tool
        self.calls: list[ObservedCall] = []

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        trace_context: DemoTraceContext,
        *,
        fault: DemoFault,
    ) -> DemoToolResult:
        self.calls.append(ObservedCall(tool_name, arguments, trace_context, fault))
        if tool_name == self._fail_tool:
            return DemoToolResult(tool_name, "failed", error="recommendation_dependency_failed")
        if tool_name == self._timeout_tool:
            return DemoToolResult(tool_name, "timeout", error="mcp_tool_timeout")

        payload_by_tool: dict[str, Any] = {
            "recommendation_get_movies": {
                "ok": True,
                "recommendations": [
                    {
                        "id": "recommendation-1",
                        "title": "The Type-Safe Matinee",
                        "movie_reservation_movie_id": "movie-1",
                    }
                ],
            },
            "reservation_get_catalog": {
                "ok": True,
                "catalog": {
                    "movies": [{"id": "movie-1", "title": "The Type-Safe Matinee"}],
                    "screenings": [
                        {
                            "id": "screening-1",
                            "movieId": "movie-1",
                            "seats": [
                                {"id": "seat-1", "row": "A", "number": 1},
                                {"id": "seat-2", "row": "A", "number": 2},
                            ],
                        }
                    ],
                },
            },
            "reservation_request_seats": {
                "ok": True,
                "reservation_request": {"id": "request-1", "status": "REQUESTED"},
            },
        }
        if tool_name == "reservation_get_request_status":
            status = next(self._statuses)
            return DemoToolResult(
                tool_name,
                "succeeded",
                {
                    "ok": True,
                    "found": True,
                    "reservation_request": {"id": "request-1", "status": status},
                    "reservation": {"id": "reservation-1"} if status == "CONFIRMED" else None,
                },
            )
        return DemoToolResult(tool_name, "succeeded", payload_by_tool[tool_name])
