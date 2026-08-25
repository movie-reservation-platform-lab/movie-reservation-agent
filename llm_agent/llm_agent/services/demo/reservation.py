from __future__ import annotations

import asyncio
from typing import Any

import structlog
from opentelemetry.trace import Status, StatusCode

from llm_agent.core.telemetry import get_tracer, set_span_attributes
from llm_agent.demo.config import DemoAgentSettings
from llm_agent.demo.models import (
    DemoDependencyError,
    DemoMcpToolClient,
    DemoReservationRequest,
    DemoReservationResult,
    DemoToolResult,
    DemoWorkflowTimeoutError,
)

logger = structlog.get_logger(__name__)


class DemoReservationService:
    def __init__(self, *, settings: DemoAgentSettings, mcp_client: DemoMcpToolClient) -> None:
        self._settings = settings
        self._mcp_client = mcp_client
        self._tracer = get_tracer(__name__)

    async def reserve_recommended_seat(self, request: DemoReservationRequest) -> DemoReservationResult:
        tool_results: list[DemoToolResult] = []
        with self._tracer.start_as_current_span("agent.reserve_recommended_seat") as span:
            set_span_attributes(
                span,
                {
                    "demo.workflow_id": request.trace_context.workflow_id,
                    "demo.fault": request.fault,
                    "correlation_id": request.trace_context.correlation_id,
                    "request_id": request.trace_context.request_id,
                },
            )
            logger.info(
                "agent.workflow.started",
                workflow_id=request.trace_context.workflow_id,
                correlation_id=request.trace_context.correlation_id,
                request_id=request.trace_context.request_id,
                fault=request.fault,
            )
            try:
                return await self._run_workflow(request, tool_results)
            except (DemoDependencyError, DemoWorkflowTimeoutError) as exc:
                span.set_status(Status(StatusCode.ERROR, exc.result.error or exc.result.outcome))
                logger.warning(
                    "agent.workflow.failed",
                    workflow_id=request.trace_context.workflow_id,
                    correlation_id=request.trace_context.correlation_id,
                    request_id=request.trace_context.request_id,
                    outcome=exc.result.outcome,
                    error=exc.result.error,
                )
                raise

    async def _run_workflow(
        self,
        request: DemoReservationRequest,
        tool_results: list[DemoToolResult],
    ) -> DemoReservationResult:
        recommendation_payload = await self._call_required(
            request,
            tool_results,
            "recommendation_get_movies",
            {
                "limit": self._settings.demo_recommendation_limit,
                "preference": request.movie_preference,
            },
        )
        recommendation = first_mapping(recommendation_payload.get("recommendations"))
        movie_id = string_value(recommendation, "movie_reservation_movie_id")
        if recommendation is None or movie_id is None:
            raise self._dependency_error(request, tool_results, "recommendation_contract_invalid")

        catalog_payload = await self._call_required(
            request,
            tool_results,
            "reservation_get_catalog",
            {"movie_id": movie_id},
        )
        catalog = mapping_value(catalog_payload, "catalog")
        movie = find_mapping(catalog.get("movies"), key="id", expected=movie_id) or recommendation
        screening = first_screening_with_seats(catalog.get("screenings"), movie_id=movie_id)
        seat = choose_seat(screening, request.seat_preference)
        screening_id = string_value(screening, "id")
        seat_id = string_value(seat, "id")
        if screening is None or seat is None or screening_id is None or seat_id is None:
            raise self._dependency_error(request, tool_results, "reservation_catalog_has_no_seats")

        reservation_payload = await self._call_required(
            request,
            tool_results,
            "reservation_request_seats",
            {"screening_id": screening_id, "seat_ids": [seat_id]},
        )
        reservation_request = mapping_value(reservation_payload, "reservation_request")
        reservation_request_id = string_value(reservation_request, "id")
        reservation_status = normalized_status(reservation_request)
        if reservation_request_id is None:
            raise self._dependency_error(request, tool_results, "reservation_request_contract_invalid")

        for attempt in range(self._settings.demo_reservation_poll_attempts):
            status_payload = await self._call_required(
                request,
                tool_results,
                "reservation_get_request_status",
                {"reservation_request_id": reservation_request_id},
                replace_existing=True,
            )
            status_request = mapping_value(status_payload, "reservation_request")
            reservation_status = normalized_status(status_request) or reservation_status
            reservation = optional_mapping_value(status_payload, "reservation")

            if reservation is not None or reservation_status == "confirmed":
                result = DemoReservationResult(
                    workflow_id=request.trace_context.workflow_id,
                    outcome="confirmed",
                    reservation_status="confirmed",
                    reservation_request_id=reservation_request_id,
                    final_answer=f"Reserved seat {display_seat(seat)} for {display_movie(movie)}.",
                    trace_context=request.trace_context,
                    movie=movie,
                    screening=screening,
                    seat=seat,
                    tool_results=list(tool_results),
                )
                logger.info(
                    "agent.workflow.completed",
                    workflow_id=result.workflow_id,
                    correlation_id=request.trace_context.correlation_id,
                    request_id=request.trace_context.request_id,
                    outcome=result.outcome,
                    reservation_request_id=result.reservation_request_id,
                )
                return result

            if reservation_status in {"rejected", "failed"}:
                return DemoReservationResult(
                    workflow_id=request.trace_context.workflow_id,
                    outcome=reservation_status,
                    reservation_status=reservation_status,
                    reservation_request_id=reservation_request_id,
                    final_answer=f"The reservation request was {reservation_status}.",
                    trace_context=request.trace_context,
                    movie=movie,
                    screening=screening,
                    seat=seat,
                    tool_results=list(tool_results),
                )

            if attempt + 1 < self._settings.demo_reservation_poll_attempts:
                await asyncio.sleep(self._settings.demo_reservation_poll_interval_seconds)

        raise self._timeout_error(
            request,
            tool_results,
            "reservation_confirmation_timeout",
            reservation_request_id=reservation_request_id,
            reservation_status=reservation_status,
        )

    async def _call_required(
        self,
        request: DemoReservationRequest,
        tool_results: list[DemoToolResult],
        tool_name: str,
        arguments: dict[str, Any],
        *,
        replace_existing: bool = False,
    ) -> dict[str, Any]:
        result = await self._mcp_client.call_tool(
            tool_name,
            arguments,
            request.trace_context,
            fault=request.fault,
        )
        if replace_existing:
            tool_results[:] = [item for item in tool_results if item.tool_name != tool_name]
        tool_results.append(result)

        if result.outcome == "timeout":
            raise self._timeout_error(request, tool_results, result.error or "mcp_tool_timeout")
        if result.outcome != "succeeded":
            raise self._dependency_error(request, tool_results, result.error or "mcp_tool_failed")
        if not isinstance(result.payload, dict):
            raise self._dependency_error(request, tool_results, "mcp_tool_contract_invalid")
        return result.payload

    @staticmethod
    def _dependency_error(
        request: DemoReservationRequest,
        tool_results: list[DemoToolResult],
        error: str,
    ) -> DemoDependencyError:
        return DemoDependencyError(
            DemoReservationResult(
                workflow_id=request.trace_context.workflow_id,
                outcome="dependency_failed",
                reservation_status=None,
                reservation_request_id=None,
                final_answer="A dependency failed during the reservation workflow.",
                trace_context=request.trace_context,
                tool_results=list(tool_results),
                error=error,
            )
        )

    @staticmethod
    def _timeout_error(
        request: DemoReservationRequest,
        tool_results: list[DemoToolResult],
        error: str,
        *,
        reservation_request_id: str | None = None,
        reservation_status: str | None = None,
    ) -> DemoWorkflowTimeoutError:
        return DemoWorkflowTimeoutError(
            DemoReservationResult(
                workflow_id=request.trace_context.workflow_id,
                outcome="timeout",
                reservation_status=reservation_status,
                reservation_request_id=reservation_request_id,
                final_answer="The reservation workflow timed out before confirmation.",
                trace_context=request.trace_context,
                tool_results=list(tool_results),
                error=error,
            )
        )


def first_mapping(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, list):
        return None
    return next((item for item in value if isinstance(item, dict)), None)


def find_mapping(items: Any, *, key: str, expected: str) -> dict[str, Any] | None:
    if not isinstance(items, list):
        return None
    return next((item for item in items if isinstance(item, dict) and item.get(key) == expected), None)


def mapping_value(value: Any, key: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    nested = value.get(key)
    return nested if isinstance(nested, dict) else {}


def optional_mapping_value(value: Any, key: str) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    nested = value.get(key)
    return nested if isinstance(nested, dict) else None


def first_screening_with_seats(value: Any, *, movie_id: str) -> dict[str, Any] | None:
    if not isinstance(value, list):
        return None
    return next(
        (
            item
            for item in value
            if isinstance(item, dict)
            and item.get("movieId") == movie_id
            and isinstance(item.get("seats"), list)
            and item["seats"]
        ),
        None,
    )


def choose_seat(screening: dict[str, Any] | None, preference: str) -> dict[str, Any] | None:
    if screening is None:
        return None
    seats = [seat for seat in screening.get("seats", []) if isinstance(seat, dict)]
    if not seats:
        return None
    if "aisle" in preference.casefold():
        return max(seats, key=lambda seat: numeric_value(seat.get("number")))
    return seats[0]


def numeric_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def string_value(value: dict[str, Any] | None, key: str) -> str | None:
    if value is None:
        return None
    item = value.get(key)
    return item if isinstance(item, str) and item else None


def normalized_status(value: dict[str, Any] | None) -> str | None:
    status = string_value(value, "status")
    return status.casefold() if status else None


def display_movie(movie: dict[str, Any]) -> str:
    return string_value(movie, "title") or "the recommended movie"


def display_seat(seat: dict[str, Any]) -> str:
    row = seat.get("row")
    number = seat.get("number")
    if isinstance(row, str) and isinstance(number, (str, int)):
        return f"{row}{number}"
    return string_value(seat, "id") or "the selected seat"
