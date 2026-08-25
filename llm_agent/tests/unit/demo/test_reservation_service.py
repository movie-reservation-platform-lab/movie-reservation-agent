from __future__ import annotations

import pytest

from llm_agent.demo.config import DemoAgentSettings
from llm_agent.demo.models import (
    DemoDependencyError,
    DemoFault,
    DemoReservationRequest,
    DemoWorkflowTimeoutError,
)
from llm_agent.demo.trace_context import DemoTraceContext
from llm_agent.services.demo.reservation import DemoReservationService
from tests.fake_implementations.demo_mcp_client import FakeMcpClient


@pytest.mark.asyncio
async def test_happy_path_calls_frozen_tools_and_confirms_reservation() -> None:
    client = FakeMcpClient(statuses=["REQUESTED", "CONFIRMED"])
    service = make_service(client)

    result = await service.reserve_recommended_seat(make_request())

    assert result.outcome == "confirmed"
    assert result.reservation_request_id == "request-1"
    assert result.seat == {"id": "seat-2", "row": "A", "number": 2}
    assert [call.tool_name for call in client.calls] == [
        "recommendation_get_movies",
        "reservation_get_catalog",
        "reservation_request_seats",
        "reservation_get_request_status",
        "reservation_get_request_status",
    ]
    assert [item.tool_name for item in result.tool_results] == [
        "recommendation_get_movies",
        "reservation_get_catalog",
        "reservation_request_seats",
        "reservation_get_request_status",
    ]
    assert client.calls[0].trace_context.correlation_id == "correlation-1"
    assert client.calls[2].arguments == {"screening_id": "screening-1", "seat_ids": ["seat-2"]}


@pytest.mark.asyncio
async def test_dependency_failure_stops_the_workflow() -> None:
    client = FakeMcpClient(fail_tool="recommendation_get_movies")
    service = make_service(client)

    with pytest.raises(DemoDependencyError) as error:
        await service.reserve_recommended_seat(make_request(fault="recommendation-error"))

    assert error.value.result.outcome == "dependency_failed"
    assert error.value.result.error == "recommendation_dependency_failed"
    assert [call.tool_name for call in client.calls] == ["recommendation_get_movies"]


@pytest.mark.asyncio
async def test_tool_timeout_is_reported_as_workflow_timeout() -> None:
    client = FakeMcpClient(timeout_tool="reservation_get_catalog")
    service = make_service(client)

    with pytest.raises(DemoWorkflowTimeoutError) as error:
        await service.reserve_recommended_seat(make_request())

    assert error.value.result.outcome == "timeout"
    assert error.value.result.error == "mcp_tool_timeout"


@pytest.mark.asyncio
async def test_pending_reservation_is_bounded_by_poll_attempts() -> None:
    client = FakeMcpClient(statuses=["REQUESTED", "REQUESTED"])
    service = make_service(client, poll_attempts=2)

    with pytest.raises(DemoWorkflowTimeoutError) as error:
        await service.reserve_recommended_seat(make_request())

    assert error.value.result.error == "reservation_confirmation_timeout"
    assert error.value.result.reservation_request_id == "request-1"
    assert len([call for call in client.calls if call.tool_name == "reservation_get_request_status"]) == 2


def make_service(client: FakeMcpClient, *, poll_attempts: int = 4) -> DemoReservationService:
    return DemoReservationService(
        settings=DemoAgentSettings(
            demo_reservation_poll_attempts=poll_attempts,
            demo_reservation_poll_interval_seconds=0,
        ),
        mcp_client=client,
    )


def make_request(*, fault: DemoFault = "none") -> DemoReservationRequest:
    return DemoReservationRequest(
        movie_preference="something exciting",
        seat_preference="aisle",
        fault=fault,
        trace_context=DemoTraceContext(
            traceparent="00-11111111111111111111111111111111-2222222222222222-01",
            tracestate=None,
            correlation_id="correlation-1",
            request_id="request-1",
            workflow_id="workflow-1",
        ),
    )
