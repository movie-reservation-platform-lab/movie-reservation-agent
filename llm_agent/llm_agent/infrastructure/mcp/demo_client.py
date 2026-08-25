from __future__ import annotations

import asyncio
import json
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from opentelemetry.trace import Status, StatusCode

from llm_agent.core.telemetry import get_current_traceparent, get_tracer, set_span_attributes
from llm_agent.demo.config import DemoAgentSettings
from llm_agent.demo.models import DemoFault, DemoMcpToolClient, DemoToolResult
from llm_agent.demo.trace_context import DemoTraceContext

RECOMMENDATION_TOOL = "recommendation_get_movies"
RESERVATION_TOOLS = {
    "reservation_get_catalog",
    "reservation_request_seats",
    "reservation_get_request_status",
}
REQUIRED_TOOLS = {RECOMMENDATION_TOOL, *RESERVATION_TOOLS}


class FastMcpDemoToolClient(DemoMcpToolClient):
    def __init__(self, settings: DemoAgentSettings) -> None:
        self._settings = settings
        self._tracer = get_tracer(__name__)

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        trace_context: DemoTraceContext,
        *,
        fault: DemoFault,
    ) -> DemoToolResult:
        if tool_name not in REQUIRED_TOOLS:
            return DemoToolResult(
                tool_name=tool_name,
                outcome="failed",
                error="agent_tool_not_allowlisted",
            )

        url = self._url_for_tool(tool_name)
        with self._tracer.start_as_current_span(f"agent.mcp.{tool_name}") as span:
            current_traceparent = get_current_traceparent() or trace_context.traceparent
            propagated_arguments = {
                **arguments,
                **trace_context.to_tool_arguments(fault=fault, traceparent=current_traceparent),
            }
            transport = StreamableHttpTransport(
                url,
                headers=trace_context.to_headers(traceparent=current_traceparent),
            )
            set_span_attributes(
                span,
                {
                    "mcp.tool.name": tool_name,
                    "mcp.server.url": url,
                    "demo.fault": fault,
                    "correlation_id": trace_context.correlation_id,
                    "request_id": trace_context.request_id,
                },
            )

            try:
                async with asyncio.timeout(self._settings.demo_mcp_timeout_seconds):
                    async with Client(transport, timeout=self._settings.demo_mcp_timeout_seconds) as client:
                        result = await client.call_tool(
                            tool_name,
                            propagated_arguments,
                            timeout=self._settings.demo_mcp_timeout_seconds,
                        )
            except TimeoutError as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, "MCP tool timed out"))
                return DemoToolResult(tool_name=tool_name, outcome="timeout", error="mcp_tool_timeout")
            except Exception as exc:  # noqa: BLE001 - FastMCP exposes transport failures through multiple libraries.
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, "MCP tool failed"))
                return DemoToolResult(tool_name=tool_name, outcome="failed", error="mcp_tool_failed")

        payload = extract_tool_payload(result)
        if isinstance(payload, dict) and payload.get("ok") is False:
            return DemoToolResult(
                tool_name=tool_name,
                outcome="failed",
                payload=payload,
                error=str(payload.get("error") or "mcp_dependency_failed"),
            )
        if bool(getattr(result, "isError", False)):
            return DemoToolResult(tool_name=tool_name, outcome="failed", error="mcp_tool_failed")
        return DemoToolResult(tool_name=tool_name, outcome="succeeded", payload=payload)

    def _url_for_tool(self, tool_name: str) -> str:
        if tool_name == RECOMMENDATION_TOOL:
            return self._settings.movie_recommendation_mcp_url
        return self._settings.movie_reservation_mcp_url


def extract_tool_payload(result: Any) -> Any:
    if isinstance(result, (dict, list, str, int, float, bool)) or result is None:
        return result

    structured_content = getattr(result, "structuredContent", None)
    if structured_content is not None:
        if isinstance(structured_content, dict) and set(structured_content) == {"result"}:
            return structured_content["result"]
        return structured_content

    content = getattr(result, "content", None)
    if not content:
        return None

    payloads: list[Any] = []
    for item in content:
        text = getattr(item, "text", None)
        if text is None:
            continue
        try:
            payloads.append(json.loads(text))
        except json.JSONDecodeError:
            payloads.append(text)

    if len(payloads) == 1:
        return payloads[0]
    return payloads
