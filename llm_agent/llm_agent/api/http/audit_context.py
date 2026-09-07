from __future__ import annotations

from collections.abc import Mapping
from uuid import uuid4

from opentelemetry import trace

from llm_agent.application.audit.authentication import AuditContext, safe_header, safe_identifier


def audit_context_from_headers(headers: Mapping[str, str], *, route: str, auth_boundary: str) -> AuditContext:
    request_id = safe_identifier(headers.get("x-request-id")) or str(uuid4())
    correlation_id = safe_identifier(headers.get("x-correlation-id")) or request_id
    span = trace.get_current_span().get_span_context()
    return AuditContext(
        request_id=request_id,
        correlation_id=correlation_id,
        route=route,
        auth_boundary=auth_boundary,
        trace_id=f"{span.trace_id:032x}" if span.is_valid else None,
        span_id=f"{span.span_id:016x}" if span.is_valid else None,
        aws_alb_trace_id=safe_header(headers.get("x-amzn-trace-id")),
        aws_cloudfront_request_id=safe_header(headers.get("x-amz-cf-id")),
    )
