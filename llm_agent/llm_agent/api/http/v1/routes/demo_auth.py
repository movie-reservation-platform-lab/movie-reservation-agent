from __future__ import annotations

import fastapi
import structlog
from fastapi.responses import JSONResponse
from opentelemetry import trace
from pydantic import ValidationError

from llm_agent.api.http.audit_context import audit_context_from_headers
from llm_agent.api.http.v1.dto.demo_auth import DemoLoginRequestDto, DemoLoginResponseDto
from llm_agent.application.audit.authentication import AuthenticationOutcome
from llm_agent.core.telemetry import set_span_attributes
from llm_agent.services.demo.authentication import DemoAuthenticationService

demo_auth_router = fastapi.APIRouter()
logger = structlog.get_logger(__name__)
MAX_LOGIN_BODY_BYTES = 16_384


@demo_auth_router.post(
    "/demo/auth/login",
    response_model=DemoLoginResponseDto,
    response_model_exclude_none=True,
    summary="Check demonstration credentials; does not create a session",
    responses={
        400: {"model": DemoLoginResponseDto, "description": "Malformed or oversized credentials"},
        401: {"model": DemoLoginResponseDto, "description": "Missing or incorrect credentials"},
        503: {"description": "Audit stdout emission failed"},
    },
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": DemoLoginRequestDto.model_json_schema()}},
        }
    },
)
async def demo_login(request: fastapi.Request) -> JSONResponse:
    service: DemoAuthenticationService = request.app.state.demo_authentication_service
    context = audit_context_from_headers(request.headers, route="/demo/auth/login", auth_boundary="demo_login")
    malformed = False
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_LOGIN_BODY_BYTES:
            malformed = True
            break
        body.extend(chunk)
    try:
        payload = None if malformed else DemoLoginRequestDto.model_validate_json(body)
    except ValidationError:
        payload = None
    try:
        event = (
            await service.record(AuthenticationOutcome.MALFORMED_CREDENTIALS, context)
            if payload is None
            else await service.check_credentials(payload.username, payload.password, context)
        )
    except OSError:
        logger.error("audit.stdout.failed", request_id=context.request_id, trace_id=context.trace_id)
        return JSONResponse(status_code=503, content={"detail": "Audit emission unavailable"})

    status_code = 400 if payload is None else (200 if event.authenticated else 401)
    set_span_attributes(
        trace.get_current_span(),
        {
            "audit.event_id": event.uid,
            "audit.outcome": event.outcome.value,
            "app.request_id": context.request_id,
            "app.correlation_id": context.correlation_id,
            "aws.alb.trace_id": context.aws_alb_trace_id,
        },
    )
    logger.info(
        "demo.auth.checked",
        authenticated=event.authenticated,
        audit_event_id=event.uid,
        request_id=context.request_id,
        correlation_id=context.correlation_id,
        trace_id=context.trace_id,
        span_id=context.span_id,
        aws_alb_trace_id=context.aws_alb_trace_id,
        service_name=event.source.service_name,
        service_version=event.source.service_version,
        environment=event.source.environment,
        status_code=status_code,
    )
    response = DemoLoginResponseDto(
        authenticated=event.authenticated,
        message="Demo credentials accepted" if event.authenticated else "Invalid credentials",
        request_id=context.request_id,
        audit_event_id=event.uid,
        trace_id=context.trace_id,
    )
    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(exclude_none=True),
        headers={
            "X-Request-Id": context.request_id,
            "X-Correlation-Id": context.correlation_id,
            "Cache-Control": "no-store",
        },
    )
