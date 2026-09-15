# movie-reservation-agent

Python FastAPI runtime for the movie reservation demo agent.

This repository is being re-scoped from a generic LLM-agent scaffold into the
agent component of the Movie Reservation Platform Lab. The agent is expected to
sit between browser or platform callers and MCP/tool services, then coordinate
movie recommendation and reservation workflows.

The proven local experiment is:

```text
browser -> Python agent -> recommendation MCP -> Rust recommendation API
                        -> reservation MCP -> NestJS reservation API
```

That experiment is the recovery baseline for future implementation work. This
repository currently contains reusable infrastructure and several legacy
example areas, so do not assume every existing route or domain package is part
of the target product.

## Current Status

The deterministic movie reservation demo is implemented in `llm_agent.demo_app`
and is the production container entry point. It exposes `/health` and the
recommendation/reservation workflow on port 8080, plus an opt-in authentication
audit demo. See [runtime and container instructions](llm_agent/README.md).

The repository also contains:

- FastAPI service composition with `svcs` dependency injection.
- OIDC/JWT authentication middleware and request execution context plumbing.
- Structured logging and OpenTelemetry setup hooks.
- Piccolo/PostgreSQL infrastructure scaffolding.
- In-memory agent run orchestration, run event log, cancellation, worker, queue,
  and fake-executor patterns.
- Legacy throttle/game/navigation routes and domain models retained from the
  scaffold.

The original demo reference is `/home/patex1987/development/python-agent-with-idp`,
branch `demo-multi-service-observability` at commit `73441fc`. Broader conversational
agent behavior remains future work. CI checks the agent’s production image and
publishes v1alpha3 candidate evidence only from canonical main pushes.

## Runtime Role

The movie reservation agent owns the conversational/runtime boundary for
reservation assistance:

- Accept browser or platform requests for an agent task or conversation turn.
- Authenticate callers and preserve request/correlation context.
- Dispatch work to an execution runtime instead of doing long-running work in
  FastAPI request handlers.
- Call MCP/tool services for recommendation and reservation actions.
- Fold internal execution state into caller-safe API responses.
- Emit structured logs/traces that connect browser, agent, MCP services, and
  downstream APIs.

The agent should remain the orchestrator. The reservation API owns reservation
state, the recommendation API owns recommendation logic, and MCP wrappers own
tool contracts to those services.

## Runtime Non-goals

This repository should not become:

- The reservation system of record.
- The recommendation engine.
- A deployment manifest or environment promotion repository.
- A direct replacement for service-specific MCP wrappers.
- A place to keep the old throttle/game/navigation product behavior.
- A broad platform control plane.

## Reuse / Delete / Defer Map

| Area | Decision | Notes |
| --- | --- | --- |
| `llm_agent/llm_agent/app.py`, `api/http/middlewares/`, `core/`, `di/` | Reuse | Keep FastAPI composition, request context, logging, telemetry hooks, and `svcs` wiring. |
| `llm_agent/llm_agent/application/authentication/`, `domain/authentication/`, `infrastructure/authentication/` | Reuse | Keep OIDC/JWT validation infrastructure. Treat as security-sensitive. |
| `llm_agent/llm_agent/api/http/v1/routes/health.py` | Reuse | Keep simple health behavior for platform checks. |
| `llm_agent/llm_agent/services/agent/`, `domain/agent/runs/`, `agent_run_worker/`, `contracts/`, `local_runtime/` | Reuse and rename later | These are useful orchestration patterns. Future work should align vocabulary with the movie reservation agent boundary and the proven demo. |
| `llm_agent/llm_agent/infrastructure/db/`, `repositories/piccolo/` | Defer | Useful for durable state later. Current issue does not add migrations or persistence behavior. |
| `llm_agent/llm_agent/domain/game/`, `domain/grid/`, `domain/navigation/`, `domain/genetic_path/`, `infrastructure/navigation/`, `infrastructure/game/` | Delete later | Legacy scaffold/example product code. Keep only until replacement issues remove dependencies safely. |
| `llm_agent/llm_agent/api/http/v1/routes/throttle_steps_calculator.py`, throttle DTOs/mappers/service/registrar | Delete later | Public throttle API is not part of the movie reservation agent target. |
| Multi-database failover scripts and reports | Defer or archive | Useful as educational infrastructure reference, not core agent runtime. |
| Original demo code in `/home/patex1987/development/python-agent-with-idp` | Reference only | Use to recover proven behavior; do not blindly copy code without fitting current boundaries. |

## API Boundary

Current public routes:

- `GET /api/v1/health/dummy-health`
- `POST /api/v1/agent/runs`
- `GET /api/v1/agent/runs/{run_id}`
- `POST /api/v1/agent/runs/{run_id}/cancel`
- `GET /api/v1/agent/runs/{run_id}/events`
- `POST /api/v1/throttle/calculate_throttle_steps` (legacy)

Target caller boundary for the movie reservation agent:

- Browser/platform callers interact with agent task or conversation resources,
  not raw worker internals.
- Internal execution ids, event logs, leases, and queue notifications remain
  internal unless an explicit admin/debug API is designed.
- Tool calls go through MCP clients/adapters and must preserve trace context.
- API DTOs stay in `llm_agent/llm_agent/api/http/v1/dto/`, with mapping at the
  API boundary.

The exact target resource names are deferred to the follow-up implementation
issue. The existing `/api/v1/agent/runs` routes are acceptable as a scaffold
reference, but should not be treated as the final browser contract.

## Local Development

Work from the package directory:

```shell
cd llm_agent
```

Install/sync dependencies with the local environment tooling after inspecting
`pyproject.toml`. In the current workspace, the expected commands are:

```shell
uv sync
uv run pytest
uv run ruff check .
uv run --env-file ../configuration/local_or_ide/local_development.env python manage.py
```

Focused test example:

```shell
uv run pytest tests/thin_integration/test_agent_run_orchestration.py -k "run_executed_successfully"
```

Docker and dependency services remain documented in `DEVELOPMENT.md`. Some
commands still reflect scaffold history and should be corrected when the
corresponding runtime slice is stabilized.

## Test Strategy

Use the narrowest test that covers the changed boundary:

- Pure domain/application behavior: unit tests with fake ports.
- FastAPI routes, middleware, DI wiring, and HTTP mapping: thin integration
  tests with `TestClient` or `httpx`.
- Worker, cancellation, leases, queue wakeups, and event-log behavior: assert
  emitted events and folded run/message state.
- MCP/tool integrations: contract tests against fake MCP clients first, then
  local end-to-end smoke tests against the demo services.
- Documentation-only changes: no runtime tests required; verify generated
  guidance and links are coherent.

## Documentation

- Architecture notes live in `docs/architecture/`.
- Implementation plans live in `docs/plans/`.
- Durable project context and research notes live in `docs/knowledge/`.
- Canonical AI guidance lives in `.ai/`; run `.ai/sync.sh` after editing it so
  generated tool files stay consistent.
