from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

_SAFE_ID = re.compile(r"[A-Za-z0-9._:/@-]{1,128}\Z")
_TRACE_ID = re.compile(r"[0-9a-f]{32}\Z")
_SPAN_ID = re.compile(r"[0-9a-f]{16}\Z")
_EVENT_ID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z")


def safe_identifier(value: str | None) -> str | None:
    return value if value and _SAFE_ID.fullmatch(value) else None


def safe_header(value: str | None) -> str | None:
    if value and len(value) <= 512 and all(32 <= ord(character) <= 126 for character in value):
        return value
    return None


class AuthenticationOutcome(StrEnum):
    AUTHENTICATED = "AUTHENTICATED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    MISSING_CREDENTIALS = "MISSING_CREDENTIALS"
    MALFORMED_CREDENTIALS = "MALFORMED_CREDENTIALS"
    INVALID_TOKEN = "INVALID_TOKEN"
    UNAUTHENTICATED = "UNAUTHENTICATED"


@dataclass(frozen=True)
class AuditSource:
    service_name: str
    service_version: str = "unknown"
    environment: str = "local"

    def __post_init__(self) -> None:
        if self.service_name not in {
            "movie-reservation-agent",
            "movie-reservation-service",
            "movie-recommendation-service",
        }:
            raise ValueError("Unknown audit event producer")
        for value in (self.service_name, self.service_version, self.environment):
            if safe_identifier(value) is None:
                raise ValueError("Audit source values must be bounded identifiers")


@dataclass(frozen=True)
class AuditContext:
    request_id: str
    correlation_id: str
    route: str
    auth_boundary: str
    trace_id: str | None = None
    span_id: str | None = None
    aws_alb_trace_id: str | None = None
    aws_cloudfront_request_id: str | None = None

    def __post_init__(self) -> None:
        if not self.route.startswith("/") or any(
            safe_identifier(value) is None for value in (self.request_id, self.correlation_id, self.route)
        ):
            raise ValueError("Audit context requires safe request, correlation, and route identifiers")
        if self.auth_boundary not in {"demo_login", "api_auth", "graphql"}:
            raise ValueError("Unknown authentication boundary")
        for value, pattern in ((self.trace_id, _TRACE_ID), (self.span_id, _SPAN_ID)):
            if value is not None and (not pattern.fullmatch(value) or int(value, 16) == 0):
                raise ValueError("Invalid active trace context")
        if (self.trace_id is None) != (self.span_id is None):
            raise ValueError("Trace and span IDs must be supplied together")
        for value in (self.aws_alb_trace_id, self.aws_cloudfront_request_id):
            if value is not None and safe_header(value) is None:
                raise ValueError("Invalid AWS correlation header")


@dataclass(frozen=True)
class AuthenticationEvent:
    uid: str
    time_ms: int
    source: AuditSource
    context: AuditContext
    outcome: AuthenticationOutcome

    def __post_init__(self) -> None:
        if not _EVENT_ID.fullmatch(self.uid) or type(self.time_ms) is not int or self.time_ms < 0:
            raise ValueError("Audit event requires a safe ID and nonnegative timestamp")
        if not isinstance(self.outcome, AuthenticationOutcome):
            raise TypeError("Audit outcome must be an allowlisted authentication outcome")

    @property
    def authenticated(self) -> bool:
        return self.outcome == AuthenticationOutcome.AUTHENTICATED

    def to_ocsf(self) -> dict[str, Any]:
        platform = {
            "schema_version": "1",
            "environment": self.source.environment,
            "request_id": self.context.request_id,
            "route": self.context.route,
            "auth_boundary": self.context.auth_boundary,
        }
        for field in ("trace_id", "span_id", "aws_alb_trace_id", "aws_cloudfront_request_id"):
            value = getattr(self.context, field)
            if value is not None:
                platform[field] = value
        return {
            "activity_id": 99,
            "activity_name": "Credential validation",
            "category_uid": 3,
            "class_uid": 3002,
            "type_uid": 300299,
            "severity_id": 1 if self.authenticated else 2,
            "status_id": 1 if self.authenticated else 2,
            "status_detail": self.outcome.value,
            "time": self.time_ms,
            "metadata": {
                "version": "1.3.0",
                "uid": self.uid,
                "correlation_uid": self.context.correlation_id,
                "product": {
                    "name": self.source.service_name,
                    "vendor_name": "Movie Reservation Platform Lab",
                    "version": self.source.service_version,
                },
            },
            "service": {"name": self.source.service_name, "version": self.source.service_version},
            "user": {"name": "demo-user", "type_id": 1} if self.authenticated else {"name": "unknown", "type_id": 0},
            "unmapped": {"platform": platform},
        }


class AuditSink(Protocol):
    async def publish(self, event: AuthenticationEvent) -> None: ...
