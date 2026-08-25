from __future__ import annotations

from typing import Annotated

import fastapi
from fastapi.responses import JSONResponse
from starlette import status

from llm_agent.api.http.v1.dto.demo import (
    DemoReservationErrorDto,
    DemoReservationRequestDto,
    DemoReservationResponseDto,
    DemoToolResultDto,
    DemoTraceDto,
)
from llm_agent.core.telemetry import get_current_trace_id, get_current_traceparent
from llm_agent.demo.models import (
    DemoDependencyError,
    DemoReservationRequest,
    DemoReservationResult,
    DemoWorkflowTimeoutError,
)
from llm_agent.demo.trace_context import DemoTraceContext
from llm_agent.services.demo.reservation import DemoReservationService

demo_router = fastapi.APIRouter()


def get_demo_reservation_service(request: fastapi.Request) -> DemoReservationService:
    return request.app.state.demo_reservation_service


@demo_router.get("/health", summary="Demo agent health")
async def demo_health() -> dict[str, str]:
    return {"status": "ok", "service": "movie-reservation-agent"}


@demo_router.post(
    "/reserve-recommended-seat",
    response_model=DemoReservationResponseDto,
    summary="Reserve a seat for a recommended movie",
    responses={
        status.HTTP_502_BAD_GATEWAY: {"model": DemoReservationErrorDto},
        status.HTTP_504_GATEWAY_TIMEOUT: {"model": DemoReservationErrorDto},
    },
)
async def reserve_recommended_seat(
    payload: DemoReservationRequestDto,
    request: fastapi.Request,
    reservation_service: Annotated[DemoReservationService, fastapi.Depends(get_demo_reservation_service)],
) -> DemoReservationResponseDto | JSONResponse:
    trace_context = DemoTraceContext.from_headers(
        request.headers,
        current_traceparent=get_current_traceparent(),
    )
    service_request = DemoReservationRequest(
        movie_preference=payload.movie_preference,
        seat_preference=payload.seat_preference,
        fault=payload.fault,
        trace_context=trace_context,
    )

    try:
        result = await reservation_service.reserve_recommended_seat(service_request)
    except DemoDependencyError as exc:
        return error_response("demo_dependency_failed", exc.result, status.HTTP_502_BAD_GATEWAY)
    except DemoWorkflowTimeoutError as exc:
        return error_response("demo_workflow_timeout", exc.result, status.HTTP_504_GATEWAY_TIMEOUT)

    return response_dto(result)


def error_response(error_code: str, result: DemoReservationResult, status_code: int) -> JSONResponse:
    dto = DemoReservationErrorDto(
        error=error_code,
        message=result.error or result.final_answer,
        workflow_id=result.workflow_id,
        trace=trace_dto(result),
    )
    return JSONResponse(status_code=status_code, content=dto.model_dump())


def response_dto(result: DemoReservationResult) -> DemoReservationResponseDto:
    return DemoReservationResponseDto(
        workflow_id=result.workflow_id,
        outcome=result.outcome,
        reservation_status=result.reservation_status,
        reservation_request_id=result.reservation_request_id,
        final_answer=result.final_answer,
        movie=result.movie,
        screening=result.screening,
        seat=result.seat,
        tool_results=[
            DemoToolResultDto(tool_name=tool_result.tool_name, outcome=tool_result.outcome)
            for tool_result in result.tool_results
        ],
        trace=trace_dto(result),
    )


def trace_dto(result: DemoReservationResult) -> DemoTraceDto:
    return DemoTraceDto(
        trace_id=get_current_trace_id() or result.trace_context.trace_id,
        correlation_id=result.trace_context.correlation_id,
        request_id=result.trace_context.request_id,
    )
