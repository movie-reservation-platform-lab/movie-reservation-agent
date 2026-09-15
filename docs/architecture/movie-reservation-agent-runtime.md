# Movie Reservation Agent Runtime

> Status update (2026-09-15): the deterministic demo composition and opt-in audit
> endpoint are implemented. This document preserves the earlier re-scope design;
> see `llm_agent/README.md` for current runnable behavior and
> `docs/plans/container-evidence.md` for image/evidence work.


Last reviewed: 2026-08-04

## Purpose

`movie-reservation-agent` is the Python agent runtime in the Movie Reservation
Platform Lab. Its role is to accept browser or platform requests, coordinate
agent execution, call MCP/tool services, and return caller-safe agent state.

The target platform flow is:

```text
browser -> Python agent -> recommendation MCP -> Rust recommendation API
                        -> reservation MCP -> NestJS reservation API
```

The reference implementation that proved this locally lives in
`/home/patex1987/development/python-agent-with-idp` on branch
`demo-multi-service-observability` at commit `73441fc`.

## Ownership Boundaries

The agent owns:

- Public agent/conversation/task API translation.
- Caller authentication and request context propagation.
- Agent execution intake, dispatch, cancellation intent, and status projection.
- MCP/tool client orchestration.
- Correlation and trace continuity across MCP and downstream service calls.

The agent does not own:

- Movie reservation persistence or invariants.
- Recommendation ranking/business logic.
- MCP service HTTP/tool contracts beyond client adapters.
- Environment promotion, deployment manifests, or DORA event storage.
- Legacy throttle/game/navigation product behavior.

## Current Scaffold

Current `main` includes reusable runtime infrastructure:

- FastAPI app creation in `llm_agent/llm_agent/app.py`.
- Authentication middleware in `llm_agent/llm_agent/api/http/middlewares/`.
- `svcs` composition under `llm_agent/llm_agent/di/`.
- Run orchestration under `llm_agent/llm_agent/services/agent/`,
  `llm_agent/agent_run_worker/`, `llm_agent/contracts/`, and
  `llm_agent/local_runtime/`.
- Piccolo/PostgreSQL infrastructure under `llm_agent/llm_agent/infrastructure/db/`.

It also includes scaffold-era behavior that should not guide product design:

- `llm_agent/llm_agent/api/http/v1/routes/throttle_steps_calculator.py`.
- `llm_agent/llm_agent/domain/game/`, `domain/grid/`, `domain/navigation/`,
  and `domain/genetic_path/`.
- Navigation/game infrastructure and test payloads.
- Multi-database failover notes and scripts.

## API Boundary

The current public agent API exposes raw run resources:

- `POST /api/v1/agent/runs`
- `GET /api/v1/agent/runs/{run_id}`
- `POST /api/v1/agent/runs/{run_id}/cancel`
- `GET /api/v1/agent/runs/{run_id}/events`

These are a scaffold boundary. The target movie reservation caller boundary
should expose product-level agent task or conversation resources and keep
execution ids, worker leases, event logs, and queue notifications internal
unless an explicit admin/debug API is designed.

Future route design should answer these before implementation:

- Is the browser contract task-based, dialogue/message-based, or both?
- Which response states are public and stable?
- What is the caller support handle: task id, message id, or reservation id?
- Which internal event details are safe to expose as progress?
- How are cancellation and retry represented to the browser?

## Runtime Boundary

Keep the control-plane/data-plane split:

```text
API/control plane -> execution intake/dispatcher -> worker/data plane
                  <- status/result projection <- event log/terminal state
```

Control-plane responsibilities:

- Validate and authorize incoming API requests.
- Create caller-visible task/message state.
- Create internal execution requests.
- Record cancellation intent.
- Project terminal execution state into caller-visible state.

Data-plane responsibilities:

- Wait for work notifications.
- Claim execution work.
- Maintain leases or heartbeats when the adapter supports them.
- Execute the agent workflow.
- Emit internal execution events.
- Set terminal execution state.

The current same-process in-memory runtime can keep proving these abstractions,
but production-shaped adapters should preserve the ports instead of leaking
queue, database, or worker details into route handlers.

## MCP Integration Direction

MCP integration should live behind infrastructure/client adapters and narrow
application ports. Route handlers should not know MCP transport details.

Expected first tools:

- Recommendation MCP for movie recommendations backed by
  `movie-recommendation-service`.
- Reservation MCP for availability/reservation actions backed by
  `movie-reservation-service`.

Tool calls must preserve correlation headers or trace context where supported.
Do not log full user prompts, raw tokens, credentials, or unnecessarily detailed
reservation payloads.

## Follow-ups

- Stabilize the proven local demo behavior in this repository.
- Decide the public browser/platform API vocabulary.
- Add MCP client ports/adapters with fake-client tests.
- Remove legacy throttle/game/navigation code once replacement routes no longer
  depend on it.
- Decide whether durable state uses Piccolo/PostgreSQL, a broker, SQS, or
  another workflow runtime for the first AWS demo.
