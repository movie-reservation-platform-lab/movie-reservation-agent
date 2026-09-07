from __future__ import annotations

import io
import json
from pathlib import Path

import jsonschema
import pytest
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic import ValidationError
from starlette.testclient import TestClient

from llm_agent.application.audit.authentication import AuthenticationEvent
from llm_agent.demo.auth_config import DemoAuthSettings
from llm_agent.demo_app import create_demo_app
from llm_agent.infrastructure.audit.stdout import StdoutAuditSink
from tests.fake_implementations.demo_mcp_client import FakeMcpClient

SCHEMA = json.loads(
    (Path(__file__).parents[2] / "fixtures" / "audit" / "platform-audit-event-v1.schema.json").read_text()
)
TEST_USERNAME = "test-configured-username"
TEST_PASSWORD = "test-only-configured-password"


def enabled_settings() -> DemoAuthSettings:
    return DemoAuthSettings(enabled=True, username=TEST_USERNAME, password=TEST_PASSWORD)


def auth_client(output: io.StringIO) -> TestClient:
    return TestClient(
        create_demo_app(
            mcp_client=FakeMcpClient(), auth_settings=enabled_settings(), audit_sink=StdoutAuditSink(output)
        )
    )


@pytest.mark.parametrize(
    ("payload", "expected_status", "reason"),
    [
        ({"username": "nonexistent-user", "password": "submitted-secret"}, 401, "INVALID_CREDENTIALS"),
        ({"username": TEST_USERNAME, "password": "submitted-secret"}, 401, "INVALID_CREDENTIALS"),
        ({"username": "nonexistent-user", "password": TEST_PASSWORD}, 401, "INVALID_CREDENTIALS"),
        ({"username": TEST_USERNAME}, 401, "MISSING_CREDENTIALS"),
        ({"password": TEST_PASSWORD}, 401, "MISSING_CREDENTIALS"),
        ({}, 401, "MISSING_CREDENTIALS"),
        ({"username": "", "password": ""}, 401, "MISSING_CREDENTIALS"),
        ({"username": TEST_USERNAME, "password": TEST_PASSWORD}, 200, "AUTHENTICATED"),
    ],
)
def test_credentials_emit_correlated_event_and_safe_response(
    payload: dict[str, str], expected_status: int, reason: str, caplog: pytest.LogCaptureFixture
) -> None:
    output = io.StringIO()
    with auth_client(output) as client:
        response = client.post(
            "/demo/auth/login",
            json=payload,
            headers={
                "x-request-id": "browser-request-123",
                "x-correlation-id": "browser-action-456",
                "traceparent": "00-6a9dd2710123456789abcdef01234567-0123456789abcdef-01",
                "x-amzn-trace-id": "Root=1-6a9dd271-0123456789abcdef01234567",
                "Authorization": "Bearer must-not-be-logged",
                "Cookie": "private=session-value",
            },
        )
    assert response.status_code == expected_status
    event = json.loads(output.getvalue())["audit"]
    jsonschema.Draft7Validator(SCHEMA).validate(event)
    assert event["status_detail"] == reason
    assert event["metadata"]["correlation_uid"] == "browser-action-456"
    assert event["unmapped"]["platform"]["request_id"] == "browser-request-123"
    assert event["unmapped"]["platform"]["trace_id"] == "6a9dd2710123456789abcdef01234567"
    assert event["unmapped"]["platform"]["span_id"] != "0123456789abcdef"
    assert event["unmapped"]["platform"]["aws_alb_trace_id"] == "Root=1-6a9dd271-0123456789abcdef01234567"
    body = response.json()
    assert body == {
        "authenticated": expected_status == 200,
        "message": "Demo credentials accepted" if expected_status == 200 else "Invalid credentials",
        "request_id": "browser-request-123",
        "audit_event_id": event["metadata"]["uid"],
        "trace_id": "6a9dd2710123456789abcdef01234567",
    }
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"] == "browser-request-123"
    assert "set-cookie" not in response.headers
    assert not response.cookies
    emitted_text = output.getvalue() + caplog.text + response.text
    for secret in (
        TEST_USERNAME,
        TEST_PASSWORD,
        "submitted-secret",
        "nonexistent-user",
        "must-not-be-logged",
        "session-value",
    ):
        assert secret not in emitted_text
    summary = next(record for record in caplog.records if "demo.auth.checked" in record.getMessage())
    assert event["metadata"]["uid"] in summary.getMessage()


def test_disabled_endpoint_is_absent_and_writes_nothing() -> None:
    output = io.StringIO()
    app = create_demo_app(
        mcp_client=FakeMcpClient(), auth_settings=DemoAuthSettings(enabled=False), audit_sink=StdoutAuditSink(output)
    )
    with TestClient(app) as client:
        assert client.post("/demo/auth/login", json={"username": "any", "password": "any"}).status_code == 404
        assert "/demo/auth/login" not in client.get("/openapi.json").json()["paths"]
        assert client.get("/health").status_code == 200
    assert output.getvalue() == ""


@pytest.mark.parametrize(
    "credentials",
    [
        {},
        {"username": TEST_USERNAME},
        {"password": TEST_PASSWORD},
        {"username": "   ", "password": TEST_PASSWORD},
        {"username": TEST_USERNAME, "password": "   "},
        {"username": "x" * 257, "password": TEST_PASSWORD},
        {"username": TEST_USERNAME, "password": "x" * 1025},
    ],
)
def test_enabled_config_requires_explicit_bounded_credentials(
    credentials: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DEMO_AUTH_USERNAME", raising=False)
    monkeypatch.delenv("DEMO_AUTH_PASSWORD", raising=False)
    with pytest.raises(ValidationError) as error:
        DemoAuthSettings(enabled=True, **credentials)
    assert TEST_PASSWORD not in str(error.value)
    assert TEST_USERNAME not in str(error.value)


@pytest.mark.parametrize(
    "content",
    [
        b'{"password":"secret-in-invalid-json",',
        b'{"username":42,"password":"secret-wrong-shape"}',
        b'{"username":[],"password":"secret-wrong-shape"}',
        b'{"username":"name","password":{},"token":"never-copy"}',
        b'"secret-json-scalar"',
        b"[]",
        b'{"username":"name","password":"' + b"x" * 1025 + b'"}',
        b'{"username":"' + b"x" * 257 + b'","password":"secret"}',
        b"x" * 16385,
    ],
)
def test_malformed_input_is_bounded_audited_and_not_echoed(content: bytes, caplog: pytest.LogCaptureFixture) -> None:
    output = io.StringIO()
    with auth_client(output) as client:
        response = client.post("/demo/auth/login", content=content, headers={"content-type": "application/json"})
    assert response.status_code == 400
    assert response.json()["message"] == "Invalid credentials"
    event = json.loads(output.getvalue())["audit"]
    assert event["status_detail"] == "MALFORMED_CREDENTIALS"
    assert "secret" not in output.getvalue() + caplog.text + response.text
    assert "never-copy" not in output.getvalue() + caplog.text + response.text
    jsonschema.Draft7Validator(SCHEMA).validate(event)


def test_deployment_provenance_is_part_of_audit_event(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTEL_SERVICE_NAME", "local-display-alias")
    monkeypatch.setenv("SERVICE_VERSION", "sha-demo-123")
    monkeypatch.setenv("DEPLOYMENT_ENVIRONMENT", "demo")
    output = io.StringIO()
    with auth_client(output) as client:
        client.post("/demo/auth/login", json={})
    event = json.loads(output.getvalue())["audit"]
    assert event["service"] == {"name": "movie-reservation-agent", "version": "sha-demo-123"}
    assert event["metadata"]["product"]["version"] == "sha-demo-123"
    assert event["unmapped"]["platform"]["environment"] == "demo"


def test_generic_system_credentials_cannot_enable_demo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEMO_AUTH_USERNAME", raising=False)
    monkeypatch.delenv("DEMO_AUTH_PASSWORD", raising=False)
    monkeypatch.setenv("USERNAME", "ambient-system-username")
    monkeypatch.setenv("PASSWORD", "ambient-system-password")
    with pytest.raises(ValidationError):
        DemoAuthSettings(enabled=True)


def test_exact_demo_environment_names_enable_route(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEMO_AUTH_ENABLED", "true")
    monkeypatch.setenv("DEMO_AUTH_USERNAME", TEST_USERNAME)
    monkeypatch.setenv("DEMO_AUTH_PASSWORD", TEST_PASSWORD)
    with TestClient(create_demo_app(mcp_client=FakeMcpClient())) as client:
        response = client.post("/demo/auth/login", json={})
    assert response.status_code == 401


def test_explicit_stdout_failure_does_not_return_success() -> None:
    class UnavailableAuditSink:
        async def publish(self, event: AuthenticationEvent) -> None:
            raise OSError("secret operating system context must not be echoed")

    app = create_demo_app(
        mcp_client=FakeMcpClient(), auth_settings=enabled_settings(), audit_sink=UnavailableAuditSink()
    )
    with TestClient(app) as client:
        response = client.post("/demo/auth/login", json={"username": TEST_USERNAME, "password": TEST_PASSWORD})
    assert response.status_code == 503
    assert response.json() == {"detail": "Audit emission unavailable"}


def test_existing_demo_workflow_stays_public_when_login_is_enabled() -> None:
    output = io.StringIO()
    with auth_client(output) as client:
        response = client.post(
            "/api/v1/demo/reserve-recommended-seat",
            json={"movie_preference": "adventure", "seat_preference": "aisle", "fault": "none"},
        )
    assert response.status_code == 200
    assert response.json()["outcome"] == "confirmed"
    assert output.getvalue() == ""


def test_exported_request_span_has_the_audit_and_aws_correlation_ids() -> None:
    output = io.StringIO()
    app = create_demo_app(
        mcp_client=FakeMcpClient(), auth_settings=enabled_settings(), audit_sink=StdoutAuditSink(output)
    )
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    FastAPIInstrumentor.uninstrument_app(app)
    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider, exclude_spans=["receive", "send"])
    # uninstrument_app eagerly caches the old stack; rebuild with the isolated provider.
    app.middleware_stack = app.build_middleware_stack()
    try:
        with TestClient(app) as client:
            response = client.post(
                "/demo/auth/login",
                json={},
                headers={
                    "x-request-id": "exported-request",
                    "x-correlation-id": "exported-action",
                    "x-amzn-trace-id": "Root=1-6a9dd271-0123456789abcdef01234567",
                },
            )
        event = json.loads(output.getvalue())["audit"]
        span = next(span for span in exporter.get_finished_spans() if span.name == "POST /demo/auth/login")
        assert f"{span.context.trace_id:032x}" == response.json()["trace_id"]
        assert f"{span.context.span_id:016x}" == event["unmapped"]["platform"]["span_id"]
        assert span.attributes["audit.event_id"] == event["metadata"]["uid"]
        assert span.attributes["audit.outcome"] == "MISSING_CREDENTIALS"
        assert span.attributes["app.request_id"] == "exported-request"
        assert span.attributes["app.correlation_id"] == "exported-action"
        assert span.attributes["aws.alb.trace_id"] == "Root=1-6a9dd271-0123456789abcdef01234567"
    finally:
        provider.shutdown()
