from __future__ import annotations

from typing import Any

import pytest
from starlette.testclient import TestClient

from llm_agent.demo.config import DemoAgentSettings
from llm_agent.demo.models import DemoFault, DemoToolResult
from llm_agent.demo.trace_context import DemoTraceContext
from llm_agent.demo_app import create_demo_app
from tests.fake_implementations.demo_mcp_client import FakeMcpClient

TRACEPARENT = "00-11111111111111111111111111111111-2222222222222222-01"


@pytest.fixture
def client() -> TestClient:
    app = create_demo_app(
        settings=DemoAgentSettings(demo_reservation_poll_interval_seconds=0),
        mcp_client=FakeMcpClient(),
    )
    return TestClient(app)


def test_health_is_public_and_platform_friendly(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok", "service": "movie-reservation-agent"}
    assert client.get("/api/v1/demo/health").json() == {
        "status": "ok",
        "service": "movie-reservation-agent",
    }


def test_demo_route_preserves_browser_observability_context(client: TestClient) -> None:
    response = client.post(
        "/api/v1/demo/reserve-recommended-seat",
        headers={
            "traceparent": TRACEPARENT,
            "X-Correlation-Id": "browser-correlation-1",
            "X-Request-Id": "browser-request-1",
        },
        json={
            "movie_preference": "something exciting",
            "seat_preference": "aisle",
            "fault": "none",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "confirmed"
    assert body["trace"] == {
        "trace_id": "11111111111111111111111111111111",
        "correlation_id": "browser-correlation-1",
        "request_id": "browser-request-1",
    }
    assert [item["tool_name"] for item in body["tool_results"]] == [
        "recommendation_get_movies",
        "reservation_get_catalog",
        "reservation_request_seats",
        "reservation_get_request_status",
    ]


def test_demo_route_returns_bounded_dependency_error() -> None:
    app = create_demo_app(mcp_client=FailingMcpClient())

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/demo/reserve-recommended-seat",
            json={
                "movie_preference": "something exciting",
                "seat_preference": "aisle",
                "fault": "recommendation-error",
            },
        )

    assert response.status_code == 502
    assert response.json()["error"] == "demo_dependency_failed"
    assert response.json()["message"] == "recommendation_dependency_failed"


def test_demo_route_validates_fault_mode(client: TestClient) -> None:
    response = client.post(
        "/api/v1/demo/reserve-recommended-seat",
        json={"movie_preference": "something", "seat_preference": "aisle", "fault": "unknown"},
    )

    assert response.status_code == 422


class FailingMcpClient:
    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        trace_context: DemoTraceContext,
        *,
        fault: DemoFault,
    ) -> DemoToolResult:
        return DemoToolResult(tool_name, "failed", error="recommendation_dependency_failed")
