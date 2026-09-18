import fastapi
import svcs

from llm_agent.api.http.middlewares.authentication import (
    AuthenticationMiddleware,
)
from llm_agent.api.http.middlewares.execution import ExecutionContextMiddleware
from llm_agent.api.http.v1.routes.agent import agent_router
from llm_agent.api.http.v1.routes.health import health_router
from llm_agent.api.http.v1.routes.throttle_steps_calculator import throttle_router
from llm_agent.application.authentication.manager import AsyncAuthenticationManager
from llm_agent.application.execution_context import ExecutionContextEnricher
from llm_agent.core.log_config import configure_logging
from llm_agent.core.telemetry import TelemetryRuntime, instrument_for_telemetry
from llm_agent.di.fastapi_lifespan import di_lifespan
from llm_agent.infrastructure.db.piccolo_llm_agent_app.programmatic_migration import maybe_migrate


def create_app(*, registry: svcs.Registry, telemetry_runtime: TelemetryRuntime | None = None) -> fastapi.FastAPI:
    """
    Construct the FastAPI application using an explicitly provided DI registry.

    The application lifespan is wrapped with ``svcs.fastapi.lifespan`` to ensure
    that the given registry is used consistently for dependency resolution and
    properly managed for startup and shutdown.
    """
    configure_logging()
    svcs_lifespan = svcs.fastapi.lifespan(di_lifespan, registry=registry)
    app = fastapi.FastAPI(lifespan=svcs_lifespan)

    app.include_router(router=health_router, prefix="/api/v1/health", tags=["health"])
    app.include_router(router=throttle_router, prefix="/api/v1/throttle", tags=["throttle"])
    app.include_router(router=agent_router, prefix="/api/v1/agent", tags=["agent"])

    instrument_for_telemetry(app, runtime=telemetry_runtime)

    # app.add_exception_handler(Exception, exception_handler)
    # app.add_exception_handler(500, exception_handler)

    maybe_migrate()

    return app


def register_middlewares(app: fastapi.FastAPI, di_container: svcs.Container) -> None:
    """
    Register FastAPI middleware components.

    Middleware is initialized using a container derived from the same DI registry
    as the rest of the application, ensuring consistent access to shared
    dependencies (e.g. authentication, request context, logging).
    """
    app.add_middleware(AuthenticationMiddleware, authentication_manager=di_container.get(AsyncAuthenticationManager))
    app.add_middleware(
        ExecutionContextMiddleware, execution_context_enricher=di_container.get(ExecutionContextEnricher)
    )
