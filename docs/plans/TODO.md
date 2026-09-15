# TODO - Agent Runtime Status

> Status update (2026-09-15): the deterministic demo composition and opt-in audit
> endpoint are implemented. This document preserves the earlier re-scope design;
> see `llm_agent/README.md` for current runnable behavior and
> `docs/plans/container-evidence.md` for image/evidence work.


Last reviewed: 2026-08-04

## Current State

`movie-reservation-agent` is not yet production-ready. The repository is being
re-scoped from a generic FastAPI LLM-agent scaffold into the Python agent
runtime for the Movie Reservation Platform Lab.

Implemented or reusable today:

- FastAPI application factory, middleware, and route registration.
- `svcs` dependency injection and registrar composition.
- OIDC/JWT validation infrastructure.
- Request execution context and structured logging.
- OpenTelemetry instrumentation hooks.
- Piccolo/PostgreSQL scaffolding.
- In-memory run orchestration, run event log, run signal queue, cancellation
  intent, worker consumer, and fake executor tests.
- Current health and agent run routes.

Legacy or scaffold-era behavior:

- Throttle calculation route.
- Game/grid/navigation/genetic-path domain packages.
- Some Keycloak realm names, payloads, and development examples.
- Multi-database failover scripts and reports.

## Missing For The Movie Reservation Demo

### 1. Public Agent API Contract

Status: Not designed.

Define whether browser/platform callers use task resources,
dialogue/message resources, or both. Keep internal execution ids, worker leases,
raw event logs, and queue details out of the public contract unless an explicit
admin/debug API is designed.

### 2. Proven Demo Behavior Adoption

Status: Not adopted on current `main`.

Use `/home/patex1987/development/python-agent-with-idp` branch
`demo-multi-service-observability` at commit `73441fc` as the reference
baseline for the already-proven local flow:

```text
browser -> Python agent -> recommendation MCP -> Rust recommendation API
                        -> reservation MCP -> NestJS reservation API
```

Adopt behavior in small slices rather than copying the branch wholesale.

### 3. MCP Client Boundary

Status: Not implemented.

Add narrow application ports and infrastructure adapters for:

- Recommendation MCP.
- Reservation MCP.

Start with fake-client tests. Preserve trace/correlation context and avoid
logging secrets or full prompt/reservation payloads.

### 4. Runtime Persistence And Queue Strategy

Status: Deferred.

The in-memory runtime is useful for local development and tests. A future issue
must decide whether the first AWS demo uses Piccolo/PostgreSQL plus a broker,
SQS, sidecar MCPs, independent MCP services, or another workflow runtime.

### 5. Legacy Code Removal

Status: Deferred.

Remove or archive throttle/game/grid/navigation/genetic-path code after the
movie reservation agent API and MCP runtime no longer depend on it.

## Testing Priorities

- Unit tests for pure domain/application behavior.
- Thin integration tests for FastAPI routes, middleware, DTO mapping, and DI.
- Worker/runtime tests that assert emitted events and folded state.
- Cancellation tests that cover checkpoint behavior and terminal projection.
- Fake MCP client contract tests before local end-to-end smoke tests.

## Near-term Follow-up Issues

1. Stabilize the proven movie reservation demo flow in the current repo.
2. Define and implement the browser/platform agent API contract.
3. Introduce MCP client ports/adapters and fake-client tests.
4. Remove or isolate legacy throttle/game/navigation routes and DI wiring.
5. Decide durable runtime state and queue strategy for the first AWS demo.
