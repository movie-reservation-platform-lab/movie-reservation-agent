from __future__ import annotations

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DemoAgentSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", populate_by_name=True)

    service_name: str = Field(default="movie-reservation-agent", validation_alias="OTEL_SERVICE_NAME")
    movie_reservation_mcp_url: str = Field(
        default="http://127.0.0.1:8091/mcp",
        validation_alias="MOVIE_RESERVATION_MCP_URL",
    )
    movie_recommendation_mcp_url: str = Field(
        default="http://127.0.0.1:8092/mcp",
        validation_alias=AliasChoices("MOVIE_RECOMMENDATION_MCP_URL", "AXUM_TOOLS_MCP_URL"),
    )
    demo_mcp_timeout_seconds: float = Field(default=15.0, gt=0, le=60)
    demo_recommendation_limit: int = Field(default=5, ge=1, le=20)
    demo_reservation_poll_attempts: int = Field(default=6, ge=1, le=20)
    demo_reservation_poll_interval_seconds: float = Field(default=0.25, ge=0, le=5)
