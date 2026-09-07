from __future__ import annotations

import asyncio
import json
import sys
from threading import Lock
from typing import TextIO

from llm_agent.application.audit.authentication import AuthenticationEvent


class StdoutAuditSink:
    """A completed write means stdout emission, not collector or archive acceptance."""

    def __init__(self, stream: TextIO | None = None) -> None:
        self._stream = stream
        self._write_lock = Lock()

    async def publish(self, event: AuthenticationEvent) -> None:
        line = json.dumps({"audit": event.to_ocsf()}, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n"
        await asyncio.to_thread(self._write, line)

    def _write(self, line: str) -> None:
        with self._write_lock:
            stream = self._stream or sys.stdout
            try:
                if stream.write(line) != len(line):
                    raise OSError("Audit stdout write was incomplete")
                stream.flush()
            except (OSError, ValueError):
                raise OSError("Audit stdout emission failed") from None
