from __future__ import annotations

import asyncio
import io
import json
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import jsonschema
import pytest
from opentelemetry import trace

from llm_agent.api.http.audit_context import audit_context_from_headers
from llm_agent.application.audit.authentication import (
    AuditContext,
    AuditSource,
    AuthenticationEvent,
    AuthenticationOutcome,
    safe_header,
    safe_identifier,
)
from llm_agent.infrastructure.audit.stdout import StdoutAuditSink

FIXTURES = Path(__file__).parents[2] / "fixtures" / "audit"
CONTRACT = json.loads((FIXTURES / "platform-audit-contract-v1.json").read_text())
SCHEMA = json.loads((FIXTURES / "platform-audit-event-v1.schema.json").read_text())


def example_event() -> AuthenticationEvent:
    example = CONTRACT["event"]
    platform = example["unmapped"]["platform"]
    return AuthenticationEvent(
        uid=example["metadata"]["uid"],
        time_ms=example["time"],
        source=AuditSource(example["service"]["name"], example["service"]["version"], platform["environment"]),
        context=AuditContext(
            request_id=platform["request_id"],
            correlation_id=example["metadata"]["correlation_uid"],
            route=platform["route"],
            auth_boundary=platform["auth_boundary"],
            trace_id=platform["trace_id"],
            span_id=platform["span_id"],
            aws_alb_trace_id=platform["aws_alb_trace_id"],
        ),
        outcome=AuthenticationOutcome.INVALID_CREDENTIALS,
    )


def test_builder_matches_cross_language_fixture_exactly() -> None:
    event = example_event().to_ocsf()
    assert event == CONTRACT["event"]
    jsonschema.Draft7Validator(SCHEMA).validate(event)


@pytest.mark.parametrize("outcome", list(AuthenticationOutcome))
def test_all_outcomes_validate_and_never_use_submitted_identity(outcome: AuthenticationOutcome) -> None:
    event = replace(example_event(), outcome=outcome).to_ocsf()
    jsonschema.Draft7Validator(SCHEMA).validate(event)
    assert event["status_id"] == (1 if outcome == AuthenticationOutcome.AUTHENTICATED else 2)
    assert event["user"]["name"] in {"unknown", "demo-user"}
    assert "session" not in event
    assert "actor" not in event


def test_absent_telemetry_is_omitted_not_fabricated() -> None:
    context = audit_context_from_headers(
        {"traceparent": "00-11111111111111111111111111111111-2222222222222222-01"},
        route="/demo/auth/login",
        auth_boundary="demo_login",
    )
    event = replace(example_event(), context=context).to_ocsf()
    platform = event["unmapped"]["platform"]
    assert "trace_id" not in platform
    assert "span_id" not in platform
    assert "aws_alb_trace_id" not in platform
    assert "aws_cloudfront_request_id" not in platform
    assert context.request_id == context.correlation_id
    jsonschema.Draft7Validator(SCHEMA).validate(event)


@pytest.mark.parametrize("sampled", [False, True])
def test_context_uses_actual_active_span_including_unsampled(sampled: bool) -> None:
    span_context = trace.SpanContext(
        trace_id=int("a" * 32, 16),
        span_id=int("b" * 16, 16),
        is_remote=False,
        trace_flags=trace.TraceFlags(1 if sampled else 0),
    )
    with trace.use_span(trace.NonRecordingSpan(span_context)):
        context = audit_context_from_headers(
            {
                "traceparent": "00-11111111111111111111111111111111-2222222222222222-01",
                "x-request-id": "request-123",
                "x-correlation-id": "action-456",
                "x-amzn-trace-id": "Root=1-6a9dd271-0123456789abcdef01234567",
                "x-amz-cf-id": "actual-cloudfront-id==",
            },
            route="/demo/auth/login",
            auth_boundary="demo_login",
        )
    assert context.trace_id == "a" * 32
    assert context.span_id == "b" * 16
    assert context.request_id == "request-123"
    assert context.correlation_id == "action-456"
    assert context.aws_cloudfront_request_id == "actual-cloudfront-id=="


@pytest.mark.parametrize("value", ["", "x" * 129, "bad\nvalue", "bad value", "bad?token=secret", "é"])
def test_unsafe_external_identifiers_are_replaced(value: str) -> None:
    assert safe_identifier(value) is None
    context = audit_context_from_headers(
        {"x-request-id": value, "x-correlation-id": value}, route="/demo/auth/login", auth_boundary="demo_login"
    )
    assert safe_identifier(context.request_id) is not None
    assert context.request_id == context.correlation_id


@pytest.mark.parametrize("value", ["", "x" * 513, "bad\r\nheader", "bad\x7fheader", "é"])
def test_unsafe_aws_headers_are_omitted(value: str) -> None:
    assert safe_header(value) is None
    context = audit_context_from_headers(
        {"x-amzn-trace-id": value, "x-amz-cf-id": value}, route="/demo/auth/login", auth_boundary="demo_login"
    )
    assert context.aws_alb_trace_id is None
    assert context.aws_cloudfront_request_id is None


@pytest.mark.parametrize(
    "changes",
    [
        {"trace_id": "0" * 32},
        {"span_id": "0" * 16},
        {"trace_id": "A" * 32},
        {"span_id": None},
        {"route": "/demo/auth/login?token=secret"},
        {"route": "not-a-path"},
        {"auth_boundary": "arbitrary body"},
    ],
)
def test_builder_rejects_invalid_context(changes: dict[str, str | None]) -> None:
    with pytest.raises(ValueError):
        replace(example_event().context, **changes)


def test_builder_rejects_raw_exception_outcome() -> None:
    with pytest.raises(TypeError):
        replace(example_event(), outcome="provider rejected secret token")


@pytest.mark.asyncio
async def test_stdout_is_one_compact_json_envelope() -> None:
    output = io.StringIO()
    event = example_event()
    await StdoutAuditSink(output).publish(event)
    line = output.getvalue()
    assert line == json.dumps({"audit": event.to_ocsf()}, separators=(",", ":")) + "\n"
    assert len(line.splitlines()) == 1
    assert set(json.loads(line)) == {"audit"}


@pytest.mark.asyncio
async def test_concurrent_stdout_writes_keep_event_boundaries() -> None:
    output = io.StringIO()
    sink = StdoutAuditSink(output)
    events = [replace(example_event(), uid=str(uuid4())) for _ in range(30)]
    await asyncio.gather(*(sink.publish(event) for event in events))
    lines = output.getvalue().splitlines()
    assert len(lines) == 30
    assert {json.loads(line)["audit"]["metadata"]["uid"] for line in lines} == {event.uid for event in events}


@pytest.mark.asyncio
async def test_stdout_failure_is_not_reported_as_emission() -> None:
    output = io.StringIO()
    output.close()
    with pytest.raises(OSError, match="Audit stdout emission failed"):
        await StdoutAuditSink(output).publish(example_event())
