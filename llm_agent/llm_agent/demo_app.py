from __future__ import annotations

import fastapi

from llm_agent.api.http.v1.routes.demo import demo_router
from llm_agent.core.log_config import configure_logging
from llm_agent.core.telemetry import instrument_for_telemetry
from llm_agent.demo.config import DemoAgentSettings
from llm_agent.demo.models import DemoMcpToolClient
from llm_agent.infrastructure.mcp.demo_client import FastMcpDemoToolClient
from llm_agent.services.demo.reservation import DemoReservationService


def create_demo_app(
    *,
    settings: DemoAgentSettings | None = None,
    mcp_client: DemoMcpToolClient | None = None,
) -> fastapi.FastAPI:
    configure_logging()
    runtime_settings = settings or DemoAgentSettings()
    runtime_client = mcp_client or FastMcpDemoToolClient(runtime_settings)

    app = fastapi.FastAPI(title="Movie Reservation Agent Demo", version="0.1.0")
    app.state.demo_reservation_service = DemoReservationService(
        settings=runtime_settings,
        mcp_client=runtime_client,
    )
    app.include_router(demo_router, prefix="/api/v1/demo", tags=["demo"])

    @app.get("/health", include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": runtime_settings.service_name}

    instrument_for_telemetry(app)
    return app


app = create_demo_app()
