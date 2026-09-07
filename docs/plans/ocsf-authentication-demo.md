# OCSF authentication demo

## Goal and scope

Add one opt-in credential-check endpoint to the existing Python demo image. It
must emit the same OCSF 1.3 Authentication shape as the TypeScript and Rust
services, on one stdout line, and return IDs that connect the browser response
to audit records, application logs, and the active trace.

This is a credential check, not a production login system. It does not issue a
session, cookie, or token. Existing reservation/MCP routes remain unchanged.
Infrastructure, FireLens configuration, retention, and AWS deployment belong to
`movie-platform-infra` issue #43. This is a first implementation slice of agent
issue #11, not the completion of a distributable audit SDK.

## Current code and decisions

- `llm_agent/demo_app.py` is the Docker entrypoint. It uses explicit constructor
  wiring and `app.state`, not the older application's `svcs` registry.
- `core/telemetry.py` already establishes FastAPI request spans. Read the active
  span; do not interpret an incoming `traceparent` as proof of an active trace.
- The older `api/http/middlewares/authentication.py` catches JWT failures, but
  is not part of the deployed demo composition. Leave that unrelated application
  unchanged in this slice; its real provider boundary needs separate coverage.
- The shared `platform-audit/1` contract uses activity 99, “Credential
  validation”, rather than claiming a session was created.
- Direct Firehose publishing would provide an AWS acceptance acknowledgement,
  but couples application code to AWS. The requested stdout/FireLens transport
  avoids that coupling and is explicitly not durable acceptance.

## Implementation

1. Add `application/audit/` with a typed event builder, safe correlation values,
   and a narrow async sink protocol. Generate one event ID per attempt; preserve
   it in the event, response, and operational summary.
2. Add a compact JSON stdout adapter under `infrastructure/audit/`. Write and
   flush through a worker thread; serialize concurrent writes with a lock. The
   exact transport envelope is `{"audit": EVENT}` with one trailing newline.
3. Add demo credential settings and a small comparison service. An enabled
   endpoint requires explicitly supplied nonblank username/password. Compare
   fixed-size credential hashes in constant time, and never retain attempted
   credentials in audit/log records.
4. Add `POST /demo/auth/login`. Disabled returns 404. Wrong or missing
   credentials return 401; matching credentials return 200. Bound body size and
   field lengths; malformed requests return a generic 400 without echoing input.
5. Wire the route in `demo_app.py` through its existing explicit constructor
   composition. Do not change the legacy application or add an auth bypass.
6. Add deterministic fixture/unit tests, real ASGI endpoint tests, and CI lint
   coverage. Declare the existing locked `jsonschema` package as an explicit
   development dependency for contract checks; add no runtime dependency.
   Document local usage and the FireLens transport limitation.

## Security and reliability

Failure events use the literal `unknown`, not a submitted username or decoded
JWT identity. Success uses the fixed demonstration identity `demo-user`.
Capture only allowlisted IDs, fixed route names, bounded AWS correlation
headers, service version, and environment. No body, token, password, cookie,
query string, or arbitrary exception text enters an audit event.

Stdout publication can block on a stalled pipe, and task termination can lose
buffered records. The sink runs outside the event loop but does not claim
unbounded buffering, replay, or compliance-grade delivery. An explicit write
failure cannot become a successful credential-check response. This route is
only for restricted demo ingress; it is disabled by default and has no account
management or production brute-force protection.

## Verification and rollout

Run `uv sync --frozen`, targeted audit/demo tests, then the full existing pytest
suite and CI lint/format commands. Verify the fixture's class/activity/type,
redaction, exactly-one-line stdout framing, concurrent isolation, active
sampled and unsampled trace context, ALB/CloudFront header handling, disabled
route, invalid startup configuration, successful/failed login, malformed and
oversized input, and existing integrated workflow behavior.

Deployment is opt-in through `DEMO_AUTH_ENABLED=true`,
`DEMO_AUTH_USERNAME`, and `DEMO_AUTH_PASSWORD`; pass the latter through secret
injection. Set `SERVICE_VERSION` and `DEPLOYMENT_ENVIRONMENT`. Roll back by
disabling the route or restoring the previous exact image digest. No database
migration or AWS resources are created by this repository change.

## Done

- All new and existing relevant checks pass.
- The contract fixture matches the cross-repository contract.
- No credentials appear in stdout, operational logs, or error bodies.
- Documentation distinguishes credential validation, audit stdout emission,
  collector delivery, and storage acceptance.
- Commit subject and PR title start with `[ai]`.
