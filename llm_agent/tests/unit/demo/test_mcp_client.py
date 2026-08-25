from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from llm_agent.infrastructure.mcp.demo_client import extract_tool_payload


@dataclass
class ToolResult:
    structuredContent: dict[str, Any] | None = None
    content: list[Any] | None = None


@dataclass
class TextContent:
    text: str


def test_extract_tool_payload_unwraps_fastmcp_result_envelope() -> None:
    result = ToolResult(structuredContent={"result": {"ok": True}})

    assert extract_tool_payload(result) == {"ok": True}


def test_extract_tool_payload_parses_text_content() -> None:
    result = ToolResult(content=[TextContent('{"ok": true}')])

    assert extract_tool_payload(result) == {"ok": True}
