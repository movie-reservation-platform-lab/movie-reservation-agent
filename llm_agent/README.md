# llm_agent package

FastAPI package workspace for `movie-reservation-agent`.

The package currently contains the service scaffold, authentication
infrastructure, DI wiring, in-memory run orchestration, and legacy example
routes. The root README describes the movie reservation agent target and the
reuse/delete/defer map.

## Quick Start

From this directory:

```shell
uv sync
uv run pytest
uv run ruff check .
uv run --env-file ../configuration/local_or_ide/local_development.env python manage.py
```

Focused orchestration test:

```shell
uv run pytest tests/thin_integration/test_agent_run_orchestration.py -k "run_executed_successfully"
```

## Current Routes

- `GET /api/v1/health/dummy-health`
- `POST /api/v1/agent/runs`
- `GET /api/v1/agent/runs/{run_id}`
- `POST /api/v1/agent/runs/{run_id}/cancel`
- `GET /api/v1/agent/runs/{run_id}/events`
- `POST /api/v1/throttle/calculate_throttle_steps` (legacy)

The run routes are scaffolding for the future agent runtime boundary. The
throttle route is legacy scaffold behavior and should not be expanded for the
movie reservation product.

## Package Boundaries

- API and HTTP DTOs: `llm_agent/api/http/`
- Application-facing context and ports: `llm_agent/application/`
- Domain models and transition rules: `llm_agent/domain/`
- Use-case orchestration: `llm_agent/services/`
- Concrete infrastructure: `llm_agent/infrastructure/`
- DI composition: `llm_agent/di/`
- Worker/runtime experiments: `agent_run_worker/`, `contracts/`, `local_runtime/`
- Tests and fakes: `tests/`

Keep FastAPI, Piccolo, `svcs`, and concrete MCP/HTTP clients outside the domain
layer. Wire concrete implementations through registrars at the composition
boundary.

## Reservation demo runtime

The production image starts the isolated demo composition on port `8080`. It
does not require the legacy OIDC or PostgreSQL dependencies.

- `GET /health`: container health check.
- `GET /api/v1/demo/health`: public demo health check.
- `POST /api/v1/demo/reserve-recommended-seat`: deterministic recommendation
  and reservation workflow used by the frontend agent panel.

The workflow calls the frozen MCP tools in this order:

1. `recommendation_get_movies`
2. `reservation_get_catalog`
3. `reservation_request_seats`
4. `reservation_get_request_status`

The two MCP sidecars default to `http://127.0.0.1:8091/mcp` and
`http://127.0.0.1:8092/mcp`. Override them with
`MOVIE_RESERVATION_MCP_URL` and `MOVIE_RECOMMENDATION_MCP_URL`. Configure the
bounded calls and status polling with `DEMO_MCP_TIMEOUT_SECONDS`,
`DEMO_RESERVATION_POLL_ATTEMPTS`, and
`DEMO_RESERVATION_POLL_INTERVAL_SECONDS`.

The production container runs as UID `10001`. Pushes to `main` publish a Linux
AMD64 candidate to GHCR as `sha-<commit>-run-<run-id>-attempt-<attempt>`. CI disables BuildKit's automatic
registry attestation to keep the candidate a single-image manifest, then
records explicit GitHub build provenance against the published digest for the
environment admission gate.

The container smoke uses task-local FastMCP fakes to exercise the full
deterministic happy path without an LLM, cloud credentials, or external API.

Incoming `traceparent`, `tracestate`, `X-Correlation-Id`, and `X-Request-Id`
values are propagated to MCP calls. Set `OTEL_EXPORTER_OTLP_ENDPOINT` to export
agent traces and metrics through OTLP/HTTP. Native FastAPI duration metrics and
the bounded request-outcome counter are documented in
[Native HTTP metrics](../docs/architecture/native-http-metrics.md).

The optional authentication audit demo adds `POST /demo/auth/login` when
`DEMO_AUTH_ENABLED=true` and explicit demo credentials are supplied. It emits
OCSF to stdout for FireLens routing; it does not issue sessions or change the
reservation workflow. See [setup, event fields, and delivery limits](../docs/architecture/audit-authentication-demo.md).


### Container security evidence

The pinned organization-owned actions publish the signed
`reservation-agent-security-evidence-<run-id>-attempt-<attempt>` artifact:
`component-candidate-evidence-v1alpha3.json`, verified image provenance,
CycloneDX SBOM, and subject-bound vulnerability report. Evidence is retained
for 14 days. Missing provenance, policy lookup errors or unexempted CRITICAL findings fail publication of the
canonical evidence package; HIGH findings remain visible for admission review.

Run/attempt tags are discovery hints, not deployment selectors. Environment
verification independently checks the successful canonical run and signed
package before admitting its exact digest to ECR. This producer has no AWS
credentials or deployment authority. Older runs without this package are not
eligible for the new admission path; use a fresh successful main run.
See [the shared action contract](https://github.com/movie-reservation-platform-lab/movie-platform-actions/blob/036531133bcefd454b5afc0eb55f8ba0328901ea/docs/container-candidate-actions.md).

The publisher and PR/local scanner use reviewed actions commit
`036531133bcefd454b5afc0eb55f8ba0328901ea` from
[actions PR #18](https://github.com/movie-reservation-platform-lab/movie-platform-actions/pull/18).
Prepare receives `${{ github.token }}` for its authenticated canonical-main
lookup through the publishing job's existing `contents: read` permission. The
same release also bounds and sanitizes evidence failure handling and reports
scanner cleanup failures; this migration is not only a token-input change.

Hosted PR checks keep publication disabled, so they do not exercise prepare or
prove canonical publication or universal private-repository access. After merge,
use a new successful canonical main publication and admit that exact run; never
reuse an older agent or canary run. Rollback reverts both publisher pins, the
scanner checkout pin, and the prepare token input together. See the
[adoption plan](../docs/plans/authenticated-prepare-adoption.md).

V3 keeps four canonical files and embeds the current central policy revision and
evaluation in the candidate document. `vulnerability-policy.json` is a diagnostic
file, not a fifth canonical evidence member. Main publication scans the published
exact digest. The read-only `container-security-check` builds this repository’s
production target on PRs and manual checks, scans its complete report, and retains
build/scan/policy diagnostics for 14 days even after failure. It cannot push,
sign or publish an image. HIGH findings remain visible and non-blocking here.

### Local production verification

From `llm_agent/`, with Docker and Node 24:

```sh
uv sync --frozen
docker build --platform linux/amd64 --target prod -t movie-reservation-agent:local .
bash automation/container_smoke.sh movie-reservation-agent:local ../.local-container-security/smoke
# ACTIONS_CHECKOUT must be a checkout at 036531133bcefd454b5afc0eb55f8ba0328901ea.
GH_TOKEN="$(gh auth token)" node "$ACTIONS_CHECKOUT/local-tools/container-security/lib/scan.mjs" \
  movie-reservation-agent:local --evidence-version v1alpha3 --component reservation-agent \
  --output-dir ../.local-container-security/scans
```

Production runs the installed, non-editable application from `/venv`; uv, uvx,
curl, pip and the `/app` source checkout are absent. Debian Trixie packages are
refreshed for scan-identified fixes. The Python health check replaces curl.
Smoke uses local MCP fakes on ports 8091/8092 and agent port 8080; ensure they are
available. It retains the response, container inspection, agent/fake logs and exit
status, including on failure, while cleaning up its container and fake processes.
Local/PR diagnostics are not signed canonical evidence or environment admission.
