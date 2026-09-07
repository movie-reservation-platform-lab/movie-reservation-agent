from __future__ import annotations

from hashlib import sha256
from secrets import compare_digest
from time import time_ns
from uuid import uuid4

from llm_agent.application.audit.authentication import (
    AuditContext,
    AuditSink,
    AuditSource,
    AuthenticationEvent,
    AuthenticationOutcome,
)


class DemoAuthenticationService:
    def __init__(self, *, username: str, password: str, source: AuditSource, sink: AuditSink) -> None:
        self._username_hash = sha256(username.encode()).digest()
        self._password_hash = sha256(password.encode()).digest()
        self._source = source
        self._sink = sink

    async def check_credentials(
        self, username: str | None, password: str | None, context: AuditContext
    ) -> AuthenticationEvent:
        username_matches = compare_digest(self._username_hash, sha256((username or "").encode()).digest())
        password_matches = compare_digest(self._password_hash, sha256((password or "").encode()).digest())
        if not username or not password:
            outcome = AuthenticationOutcome.MISSING_CREDENTIALS
        elif username_matches and password_matches:
            outcome = AuthenticationOutcome.AUTHENTICATED
        else:
            outcome = AuthenticationOutcome.INVALID_CREDENTIALS
        return await self.record(outcome, context)

    async def record(self, outcome: AuthenticationOutcome, context: AuditContext) -> AuthenticationEvent:
        event = AuthenticationEvent(
            uid=str(uuid4()), time_ms=time_ns() // 1_000_000, source=self._source, context=context, outcome=outcome
        )
        await self._sink.publish(event)
        return event
