from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True)
class DemoTraceContext:
    traceparent: str | None
    tracestate: str | None
    correlation_id: str
    request_id: str
    workflow_id: str

    @classmethod
    def from_headers(
        cls,
        headers: Mapping[str, str],
        *,
        current_traceparent: str | None,
    ) -> DemoTraceContext:
        request_id = headers.get("x-request-id") or str(uuid4())
        correlation_id = headers.get("x-correlation-id") or request_id
        return cls(
            traceparent=headers.get("traceparent") or current_traceparent,
            tracestate=headers.get("tracestate"),
            correlation_id=correlation_id,
            request_id=request_id,
            workflow_id=str(uuid4()),
        )

    @property
    def trace_id(self) -> str | None:
        if self.traceparent is None:
            return None
        parts = self.traceparent.split("-")
        if len(parts) != 4 or len(parts[1]) != 32:
            return None
        return parts[1]

    def to_headers(self, *, traceparent: str | None = None) -> dict[str, str]:
        headers = {
            "X-Correlation-Id": self.correlation_id,
            "X-Request-Id": self.request_id,
        }
        effective_traceparent = traceparent or self.traceparent
        if effective_traceparent:
            headers["traceparent"] = effective_traceparent
        if self.tracestate:
            headers["tracestate"] = self.tracestate
        return headers

    def to_tool_arguments(self, *, fault: str, traceparent: str | None = None) -> dict[str, str]:
        arguments = {
            "correlation_id": self.correlation_id,
            "request_id": self.request_id,
            "demo_fault": fault,
        }
        effective_traceparent = traceparent or self.traceparent
        if effective_traceparent:
            arguments["traceparent"] = effective_traceparent
        if self.tracestate:
            arguments["tracestate"] = self.tracestate
        return arguments
