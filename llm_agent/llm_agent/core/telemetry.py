from __future__ import annotations

import os
from typing import Any

import fastapi
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_TELEMETRY_CONFIGURED = False
_HTTPX_INSTRUMENTED = False


def instrument_for_telemetry(app: fastapi.FastAPI) -> None:
    configure_telemetry()
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=trace.get_tracer_provider(),
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


def configure_telemetry() -> None:
    global _HTTPX_INSTRUMENTED, _TELEMETRY_CONFIGURED

    if not _TELEMETRY_CONFIGURED:
        provider = TracerProvider(
            resource=Resource.create(
                {
                    "service.name": os.getenv("OTEL_SERVICE_NAME", "movie-reservation-agent"),
                    "service.version": os.getenv("SERVICE_VERSION", "unknown"),
                    "deployment.environment.name": os.getenv("DEPLOYMENT_ENVIRONMENT", "local"),
                }
            )
        )
        if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        trace.set_tracer_provider(provider)
        _TELEMETRY_CONFIGURED = True

    if not _HTTPX_INSTRUMENTED:
        HTTPXClientInstrumentor().instrument()
        _HTTPX_INSTRUMENTED = True


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
