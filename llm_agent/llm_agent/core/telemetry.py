from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import fastapi
from fastapi.routing import APIRoute
from opentelemetry import metrics, trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.metrics import Counter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import MetricReader, PeriodicExportingMetricReader
from opentelemetry.sdk.metrics.view import View
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_TELEMETRY_RUNTIME: TelemetryRuntime | None = None
_HTTPX_INSTRUMENTED = False
_HEALTH_ROUTE_PATTERN = r"/(?:[^/?#]*health[^/?#]*|[^/?#]*ready[^/?#]*)(?:[/?#]|$)"
_HTTP_REQUEST_METRIC_NAME = "movie_reservation_agent.http.server.requests"
_HTTP_METHODS = frozenset({"DELETE", "GET", "PATCH", "POST", "PUT"})
_NATIVE_HTTP_VIEWS = (
    View(
        instrument_name="http.server.active_requests",
        attribute_keys={"http.method"},
    ),
    View(
        instrument_name="http.server.duration",
        attribute_keys={"http.method", "http.status_code", "http.target"},
    ),
    View(
        instrument_name="http.server.response.size",
        attribute_keys={"http.method", "http.status_code", "http.target"},
    ),
)


@dataclass
class TelemetryRuntime:
    resource: Resource
    tracer_provider: TracerProvider
    meter_provider: MeterProvider
    _is_shutdown: bool = field(default=False, init=False)

    def shutdown(self) -> None:
        """Flush and stop process-owned telemetry providers once."""
        if self._is_shutdown:
            return
        self.meter_provider.shutdown()
        self.tracer_provider.shutdown()
        self._is_shutdown = True


def create_telemetry_runtime(
    *,
    resource: Resource,
    metric_readers: list[MetricReader] | None = None,
) -> TelemetryRuntime:
    """Create providers with the agent's bounded native HTTP metric views."""
    return TelemetryRuntime(
        resource=resource,
        tracer_provider=TracerProvider(resource=resource),
        meter_provider=MeterProvider(
            resource=resource,
            metric_readers=metric_readers or (),
            views=_NATIVE_HTTP_VIEWS,
        ),
    )


class HttpOutcomeMetrics:
    """Record bounded outcomes for registered, non-health HTTP routes."""

    def __init__(self, meter_provider: MeterProvider, route_methods: dict[tuple[str, int], str]) -> None:
        meter = meter_provider.get_meter(__name__)
        self._requests: Counter = meter.create_counter(
            _HTTP_REQUEST_METRIC_NAME,
            unit="{request}",
            description="Completed agent HTTP requests by registered route and bounded outcome",
        )
        self._route_methods = route_methods
        for method, route in sorted({(method, route) for (method, _), route in route_methods.items()}):
            self._requests.add(0, self._attributes(method, route, "4xx"))
            self._requests.add(0, self._attributes(method, route, "5xx"))

    def record(self, method: str, route: APIRoute, status_code: int) -> None:
        route_path = self._route_methods.get((method, id(route)))
        if route_path is None:
            return
        status_class = f"{status_code // 100}xx" if 100 <= status_code <= 599 else "unknown"
        self._requests.add(1, self._attributes(method, route_path, status_class))

    @staticmethod
    def _attributes(method: str, route: str, status_class: str) -> dict[str, str]:
        outcomes = {
            "1xx": "informational",
            "2xx": "success",
            "3xx": "redirect",
            "4xx": "client_error",
            "5xx": "server_error",
        }
        return {
            "http.request.method": method,
            "http.route": route,
            "http.response.status_class": status_class,
            "outcome": outcomes.get(status_class, "unknown"),
        }


class HttpOutcomeMetricsMiddleware:
    def __init__(self, app: ASGIApp, *, metrics: HttpOutcomeMetrics) -> None:
        self.app = app
        self.metrics = metrics

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        status_code = 500

        async def capture_status(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, capture_status)
        finally:
            route = scope.get("route")
            if isinstance(route, APIRoute):
                self.metrics.record(scope.get("method", ""), route, status_code)


def instrument_for_telemetry(app: fastapi.FastAPI, *, runtime: TelemetryRuntime | None = None) -> None:
    if getattr(app.state, "agent_telemetry_instrumented", False):
        return

    configured_runtime = runtime or configure_telemetry()
    route_methods = _eligible_route_methods(app)
    app.add_middleware(
        HttpOutcomeMetricsMiddleware,
        metrics=HttpOutcomeMetrics(configured_runtime.meter_provider, route_methods),
    )
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=configured_runtime.tracer_provider,
        meter_provider=configured_runtime.meter_provider,
        excluded_urls=_HEALTH_ROUTE_PATTERN,
        http_capture_headers_server_request=[
            "traceparent",
            "tracestate",
            "x-correlation-id",
            "x-request-id",
            "x-demo-fault",
        ],
        http_capture_headers_sanitize_fields=[
            "authorization",
            "cookie",
            "set-cookie",
            "x-api-key",
        ],
        exclude_spans=["receive", "send"],
    )
    app.state.agent_telemetry_instrumented = True


def configure_telemetry() -> TelemetryRuntime:
    global _HTTPX_INSTRUMENTED, _TELEMETRY_RUNTIME

    if _TELEMETRY_RUNTIME is None:
        resource = _telemetry_resource()
        metric_readers = []
        if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
            from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            metric_readers.append(PeriodicExportingMetricReader(OTLPMetricExporter()))
        _TELEMETRY_RUNTIME = create_telemetry_runtime(resource=resource, metric_readers=metric_readers)
        if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
            _TELEMETRY_RUNTIME.tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        trace.set_tracer_provider(_TELEMETRY_RUNTIME.tracer_provider)
        metrics.set_meter_provider(_TELEMETRY_RUNTIME.meter_provider)

    if not _HTTPX_INSTRUMENTED:
        HTTPXClientInstrumentor().instrument()
        _HTTPX_INSTRUMENTED = True

    return _TELEMETRY_RUNTIME


def _telemetry_resource() -> Resource:
    return Resource.create(
        {
            "service.name": os.getenv("OTEL_SERVICE_NAME", "movie-reservation-agent"),
            "service.version": os.getenv("SERVICE_VERSION", "unknown"),
            "deployment.environment.name": os.getenv("DEPLOYMENT_ENVIRONMENT", "local"),
        }
    )


def _eligible_route_methods(app: fastapi.FastAPI) -> dict[tuple[str, int], str]:
    route_methods: dict[tuple[str, int], str] = {}
    for route in app.routes:
        if isinstance(route, APIRoute):
            _add_route_methods(route_methods, route, route.path)
            continue
        effective_route_contexts = getattr(route, "effective_route_contexts", None)
        if not callable(effective_route_contexts):
            continue
        for context in effective_route_contexts():
            original_route = context.original_route
            if isinstance(original_route, APIRoute):
                _add_route_methods(route_methods, original_route, context.path)
    return route_methods


def _add_route_methods(route_methods: dict[tuple[str, int], str], route: APIRoute, path: str) -> None:
    if _is_health_route(path):
        return
    for method in route.methods or ():
        if method in _HTTP_METHODS:
            route_methods[(method, id(route))] = path


def _is_health_route(path: str) -> bool:
    return any("health" in segment or "ready" in segment for segment in path.lower().split("/"))


def get_tracer(name: str) -> trace.Tracer:
    return trace.get_tracer(name)


def get_current_trace_id() -> str | None:
    context = trace.get_current_span().get_span_context()
    if not context.is_valid:
        return None
    return f"{context.trace_id:032x}"


def get_current_traceparent() -> str | None:
    context = trace.get_current_span().get_span_context()
    if not context.is_valid:
        return None
    return f"00-{context.trace_id:032x}-{context.span_id:016x}-{int(context.trace_flags):02x}"


def set_span_attributes(span: trace.Span, attributes: dict[str, Any]) -> None:
    if not span.is_recording():
        return
    for name, value in attributes.items():
        if isinstance(value, (str, bool, int, float)):
            span.set_attribute(name, value)
