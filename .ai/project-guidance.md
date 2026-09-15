# Project AI Guidance

This repository is the Python 3.12 FastAPI runtime for
`movie-reservation-agent`, the agent component of the Movie Reservation Platform
Lab. The agent coordinates browser or platform requests with MCP/tool services
for recommendations and reservations.

The repository is being re-scoped from a generic LLM-agent scaffold. Prefer
reading the current code, docs, and
`/home/patex1987/development/movie-reservation-platform-lab/PLATFORM_CONTEXT.md`
before making assumptions. The original proven demo reference is available at
`/home/patex1987/development/python-agent-with-idp`, especially branch
`demo-multi-service-observability` at commit `73441fc`.

Some older throttle/game/navigation code still exists as scaffold or legacy
example code. Do not treat it as the long-term product direction unless the
current task explicitly says so.

## Runtime Role

The target platform flow is:

```text
browser -> Python agent -> recommendation MCP -> Rust recommendation API
                        -> reservation MCP -> NestJS reservation API
```

The agent owns:

- browser/platform-facing agent API translation
- authentication and request/correlation context propagation
- agent execution intake, dispatch, cancellation intent, and status projection
- MCP/tool client orchestration
- structured logs/traces that correlate agent work with MCP and downstream APIs

The agent does not own reservation persistence, recommendation business logic,
MCP service contracts, deployment manifests, environment promotion, or legacy
throttle/game/navigation product behavior.

## Repository Layout

- `llm_agent/`: Python package workspace and service runtime.
- `llm_agent/llm_agent/`: main FastAPI application package.
- `llm_agent/llm_agent/api/`: HTTP API, DTOs, mappers, routes, and middleware.
- `llm_agent/llm_agent/application/`: application-facing ports and request/auth context abstractions.
- `llm_agent/llm_agent/domain/`: domain objects and domain rules.
- `llm_agent/llm_agent/services/`: use-case orchestration services.
- `llm_agent/llm_agent/infrastructure/`: concrete adapters for auth, execution context, database, service discovery, and future MCP clients.
- `llm_agent/llm_agent/di/`: `svcs` registry and FastAPI composition.
- `llm_agent/agent_run_worker/`, `llm_agent/contracts/`, `llm_agent/local_runtime/`: worker, contracts, event log, queue, and run-store experiments.
- `llm_agent/tests/`: tests and fake implementations.
- `docs/`: project documentation, architecture notes, plans, patterns, and knowledge.
- `.ai/`: canonical AI guidance. Generated tool files are produced from this folder by `.ai/sync.sh`.

## Reuse / Delete / Defer Map

- Reuse FastAPI composition, middleware, `svcs` DI, structured logging,
  OpenTelemetry hooks, OIDC/JWT authentication, and request context plumbing.
- Reuse and refine in-memory run orchestration, worker, queue, event-log, and
  cancellation patterns as the runtime envelope for future agent behavior.
- Defer Piccolo/PostgreSQL persistence changes until a specific durable-state
  issue defines the data model and migration plan.
- Delete or archive legacy throttle/game/grid/navigation/genetic-path behavior
  in a later cleanup issue after replacement routes no longer depend on it.
- Treat multi-database failover scripts and reports as educational scaffold
  references unless a task explicitly adopts them.

## Development Commands

- Install or sync dependencies from `llm_agent/`: inspect the local `pyproject.toml` first and use the existing Python environment tooling.
- Run tests from `llm_agent/`: `uv run pytest` or `pytest`, depending on the active environment.
- Run focused tests from `llm_agent/`: `uv run pytest tests/path/to/test_file.py -k "<case>"`.
- Run Ruff checks from `llm_agent/`: `uv run ruff check .` when Ruff is available in the environment.
- Run the app from `llm_agent/`: `uv run --env-file ../configuration/local_or_ide/local_development.env python manage.py`.
- Docker and dependency services are described in `DEVELOPMENT.md` and `llm_agent/README.md`.

When the exact command is uncertain, inspect `llm_agent/pyproject.toml`,
`DEVELOPMENT.md`, and existing scripts before inventing a new workflow.

## Code And Architecture Conventions

- Prefer small, incremental changes that fit the existing package structure.
- Keep FastAPI-specific concerns in the API layer: routes, DTOs, mappers, middleware, and dependency extraction.
- Keep application services focused on use cases and orchestration.
- Keep domain objects and domain rules free of FastAPI, database, `svcs`, MCP transport details, and framework concerns.
- Keep infrastructure adapters behind protocols or narrow interfaces where the code already follows that pattern.
- Use `svcs` registration as the composition boundary. Avoid hidden global dependencies.
- Preserve async boundaries carefully. Do not block the event loop with synchronous I/O in request paths.
- Treat worker/run/event-log code as concurrency-sensitive. Be explicit about state transitions, idempotency, cancellation, and event ordering.
- Keep internal execution ids, worker leases, queue notifications, and raw event logs out of the browser contract unless an explicit admin/debug API is designed.
- Prefer typed Python with clear dataclasses/Pydantic models over unstructured dictionaries at boundaries.
- Keep comments sparse and useful: explain decisions, invariants, or non-obvious side effects.

## Testing Guidance

- Add or update tests for behavior changes.
- Prefer narrow unit tests for pure domain/application logic.
- Use fake implementations for ports, stores, queues, event logs, and future MCP clients where they make behavior easier to isolate.
- Add integration-style tests around FastAPI routes, middleware behavior, DI wiring, worker orchestration, and event-log invariants when those boundaries change.
- For cancellation, claiming, leases, and event logs, assert both emitted events and the folded/derived state where possible.
- For MCP/tool integrations, start with fake MCP clients and add local end-to-end smoke coverage against demo services once wiring is stable.
- Run the narrowest useful tests while iterating, then run the relevant full check before handing work back.

## Security And Operations

- Do not commit secrets, tokens, credentials, local `.env` values, or copied JWTs.
- Treat OIDC discovery, JWKS validation, token extraction, authorization, and user identity propagation as security-sensitive.
- Validate external input at API boundaries with Pydantic/FastAPI DTOs.
- Avoid logging raw tokens, credentials, PII, full prompts, or full reservation payloads unless explicitly safe.
- Keep health endpoints simple and platform-friendly.
- Preserve trace/correlation context across agent, MCP, and downstream API calls.
- Be explicit about database migration behavior, connection pooling, startup side effects, and runtime teardown.

## Documentation

- Update docs for user-facing behavior, architecture decisions, operations, or developer workflow changes.
- Use `docs/plans/` for implementation plans.
- Use `docs/architecture/` for durable architecture decisions and topology notes.
- Use `docs/patterns/` for reusable implementation patterns.
- Use `docs/knowledge/` for durable project context and research notes.
- Edit `.ai/project-guidance.md` first for AI guidance changes, then run `.ai/sync.sh` to regenerate ignored local `AGENTS.md` and tool-specific files. Only `.ai/` is versioned for AI guidance.
