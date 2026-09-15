# Development Guide

This repository is the Python FastAPI agent runtime for the Movie Reservation
Platform Lab. It is currently being re-scoped from a generic scaffold, so some
commands and code paths still exist only as reusable examples or temporary
legacy code.

## 1. Project Structure

Key folders:

```text
llm_agent/
├── llm_agent/
│   ├── api/                  # FastAPI HTTP routes, DTOs, mappers, middleware
│   ├── application/          # request/auth context and application-facing ports
│   ├── core/                 # logging, uvicorn config, telemetry hooks
│   ├── di/                   # svcs composition and registrars
│   ├── domain/               # pure domain models and transition rules
│   ├── infrastructure/       # auth, db, discovery, execution-context adapters
│   └── services/             # use-case orchestration services
├── agent_run_worker/         # in-memory worker and execution experiments
├── contracts/                # shared runtime contracts
├── local_runtime/            # in-memory event log, run store, and queue
└── tests/                    # unit, thin integration, fakes
```

Root-level folders such as `configuration/`, `docker-compose*.yml`,
`keycloak_config/`, and `multi_db_configuration/` support local dependencies or
scaffold-era experiments. Keep them until replacement issues decide whether to
reuse, archive, or delete them.

## 2. Prerequisites

- Python 3.12+
- `uv`, when using the checked-in lockfile workflow.
- Optional Docker for Keycloak/Postgres/local dependency services.
- Optional Keycloak when exercising authenticated flows.

Inspect `llm_agent/pyproject.toml` before changing dependency or tooling
commands.

## 3. Local Commands

For the production demo, run `uv run --frozen uvicorn llm_agent.demo_app:app --port 8080`
from `llm_agent/`. This composition uses task-local MCP services and does not
require the scaffold’s database/OIDC setup. See [production image verification](llm_agent/README.md#local-production-verification)
for build, smoke and scan commands. The `manage.py` commands below exercise the
legacy scaffold composition.


Run package commands from `llm_agent/`:

```shell
cd llm_agent
uv sync
uv run pytest
uv run ruff check .
uv run --env-file ../configuration/local_or_ide/local_development.env python manage.py
```

Focused tests:

```shell
uv run pytest tests/thin_integration/test_agent_run_orchestration.py -k "run_executed_successfully"
uv run pytest tests/thin_integration/test_canceled_runs.py
```

If the active environment is already prepared without `uv`, `pytest` can be run
directly from `llm_agent/`.

## 4. Local Dependencies

Keycloak can be started with:

```shell
docker compose -f docker-compose.e2e.yml up keycloak
```

or with the dependency profile:

```shell
docker compose -f docker-compose.e2e.yml -f docker-compose.multi-db.dev.yml --profile dependencies up
```

Local Keycloak defaults:

- URL: `http://localhost:8082`
- Realm: `throttling-test` (legacy name, still used by local config)
- Admin: `admin` / `admin`
- Test users: `test-user` / `test-password`, `admin-user` / `admin-password`

Token helper:

```shell
python testing_payloads/get_keycloak_token.py
```

The realm name and helper payloads should be renamed in a later cleanup issue
after the agent contract is stabilized.

## 5. Running Docker Images

Build from `llm_agent/`:

```shell
docker build --target dev -t movie-reservation-agent:local_dev -f Dockerfile .
docker build --target prod -t movie-reservation-agent:local_prod -f Dockerfile .
```

Run the development image from the repository root:

```shell
docker run -it -p 8080:8080 \
  --env-file configuration/docker/local_development.env \
  --rm \
  movie-reservation-agent:local_dev
```

The Dockerfile still starts `python manage.py`. Uvicorn configuration is read
from environment variables and `llm_agent/llm_agent/configuration/log_config_json.json`.

## 6. Dependency Injection

The project uses `svcs` as the composition boundary.

- Registrars live under `llm_agent/llm_agent/di/registrars/`.
- FastAPI lifespan integration lives in `llm_agent/llm_agent/di/fastapi_lifespan.py`.
- `create_app_with_selected_di` supports production/default and test-selected
  registrar sets.
- Business/domain code should receive typed dependencies through constructors
  or use-case services, not import `svcs` directly.

When changing DI wiring, keep the dependency direction:

```text
API -> services/application -> domain/contracts <- infrastructure/local_runtime
```

## 7. Current Runtime APIs

Current routes on `main`:

- `GET /api/v1/health/dummy-health`
- `POST /api/v1/agent/runs`
- `GET /api/v1/agent/runs/{run_id}`
- `POST /api/v1/agent/runs/{run_id}/cancel`
- `GET /api/v1/agent/runs/{run_id}/events`
- `POST /api/v1/throttle/calculate_throttle_steps` (legacy scaffold route)

The `/api/v1/agent/runs` API is useful for validating the run orchestration
scaffold. It is not yet the final browser/platform contract for the movie
reservation demo. The throttle route is legacy and should be removed in a later
cleanup issue.

## 8. Testing Expectations

- Add unit tests for pure domain/application changes.
- Add thin integration tests for FastAPI routes, middleware, `svcs` wiring, and
  HTTP DTO mapping.
- For worker/run/event-log changes, assert both the event sequence and folded
  current state.
- For cancellation and leases, test cooperative checkpoint behavior and
  terminal state projection.
- For MCP integrations, start with fake MCP clients and add local end-to-end
  smoke coverage once the demo services are wired.

Documentation-only changes generally do not require runtime tests, but do
require review of generated docs/guidance consistency.

## 9. Multi-database Notes

The HAProxy, pgbouncer, PostgreSQL failover scripts, AWS failover notes, and
historical reports are scaffold-era infrastructure experiments. They are not
part of the near-term movie reservation agent runtime unless a follow-up issue
explicitly adopts them.

## AI guidance

Only `.ai/` is tracked. Run `bash .ai/sync.sh` after cloning or editing guidance
to regenerate ignored assistant directories and root `AGENTS.md`.
