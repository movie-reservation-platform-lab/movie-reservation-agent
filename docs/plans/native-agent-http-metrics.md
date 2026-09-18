# Implementation Plan: Native agent HTTP metrics

## 1. Summary

Configure the existing OpenTelemetry FastAPI instrumentation with a real metrics
provider and add one bounded HTTP outcome counter for registered application
routes. Preserve tracing and application behavior while producing local payload
evidence for infrastructure issue #57.

## 2. Goals

- Export native FastAPI traffic and duration metrics through OTLP/HTTP.
- Export a bounded request counter with method, route, status code/class, and
  outcome attributes.
- Publish real zero-valued 4xx and 5xx series before the first error.
- Exclude health and readiness traffic from application request signals.
- Prove identity, success, 4xx, 5xx, idempotent setup, and shutdown behavior.

## 3. Non-goals

- Dashboard, alert, collector, deployment, or environment changes.
- Fake requests or seeded duration observations.
- A shared cross-language metric library or universal metric name.

## 4. Current State

`llm_agent/core/telemetry.py` configures a trace provider and instruments FastAPI
and HTTPX, but supplies no metrics provider. Both `app.py` and `demo_app.py` call
the same instrumentation boundary. The locked OpenTelemetry FastAPI version
accepts an explicit meter provider and emits native HTTP server duration and
active-request instruments.

## 5. Requirements and Assumptions

The advisory platform contract requires canonical resource identity, bounded
dimensions, honest idle/missing semantics, and local observed payloads. Health
and readiness requests are excluded. Registered route templates provide the
finite route allowlist. Status codes are finite HTTP integers and are paired
with bounded `2xx` through `5xx` status classes and success/client_error/
server_error outcomes.

## 6. Proposed Design

Create one process-owned telemetry runtime containing the resource, tracer
provider, and meter provider. Production uses an OTLP metric exporter and
periodic reader only when an OTLP endpoint is configured; tests inject an
in-memory reader/provider.

Pass that meter provider to FastAPI instrumentation so the SDK emits its native
HTTP metrics. Add a small ASGI middleware that records one custom counter event
after each eligible registered-route response. At startup, initialize the 4xx
and 5xx combinations for every eligible method/route with `add(0)`. Route
templates come from FastAPI's registered `APIRoute` objects, never raw URLs.

## 7. Alternatives Considered

- Native metrics only: smallest change, but cannot guarantee explicit pre-error
  zero 4xx/5xx series. Rejected.
- Duplicate custom traffic and latency middleware: provides full control but
  duplicates supported framework instrumentation. Rejected.
- Native metrics plus one custom outcome counter: selected; preserves native
  duration semantics and adds only the required zero/error contract.

## 8. API / Interface Changes

No HTTP API changes. Telemetry composition accepts an optional test/runtime
provider. New metric: `movie_reservation_agent.http.server.requests` with unit
`{request}`.

## 9. Data Model / Persistence Changes

None.

## 10. Security, Privacy, and Abuse Considerations

Metric attributes are restricted to registered route templates, methods,
integer status codes, bounded status classes, and bounded outcomes. No raw URL,
query, request, trace, user, prompt, or credential data is recorded.

## 11. Performance, Scalability, and Reliability Considerations

The custom middleware performs one counter update per eligible request. Series
cardinality is bounded by the finite registered route/method set and status
space. OTLP export remains asynchronous and fail-open; exporter failures do not
affect requests. Shutdown flushes the process-owned providers.

## 12. Implementation Steps

1. Add lifecycle-managed metrics composition and inject the meter provider into
   FastAPI instrumentation in `llm_agent/core/telemetry.py`.
2. Add bounded route outcome instrumentation and initialize 4xx/5xx zeros.
3. Add in-memory payload tests for identity, native metrics, zero/error
   behavior, exclusions, duplicate setup, bounded labels, and shutdown.
4. Document exact observed native/custom payloads and PromQL semantics.

## 13. Testing Strategy

Use `InMemoryMetricReader` with FastAPI `TestClient` to inspect real SDK metric
data. Exercise a successful demo request, validation 422, controlled 502, and
health requests. Add focused lifecycle tests, then run the full pytest, Ruff,
format, compile, and diff checks.

## 14. Rollout / Migration Plan

Publish the reviewed image independently. Infrastructure issue #57 will update
collector acceptance from the observed payload, followed by one coordinated
environment composition. Existing log- and span-derived alerts remain until
issue #58 performs a live comparison. Rollback restores the previous image.

## 15. Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Duplicate observations | Instrument each app once and use a single custom counter boundary. |
| Unbounded route labels | Derive labels only from registered route templates. |
| False healthy state | Do not seed request totals or duration; queries require fresh positive traffic. |
| Export outage affects traffic | Keep periodic OTLP export asynchronous and fail-open. |

## 16. Done Criteria

- Local payload proves native traffic/duration plus bounded outcomes.
- Initial 4xx/5xx zeros and later increments are tested.
- Health/readiness signals are absent from the user-path counter.
- Tracing and the full repository checks remain healthy.
- Exact payload mapping and query semantics are documented.

## 17. Review Checklist

- [x] Requirements and non-goals are explicit.
- [x] Existing instrumentation and test conventions were inspected.
- [x] Alternatives, security, reliability, rollout, and rollback are covered.
- [x] Implementation and verification steps are concrete.

## 18. Handoff Prompt for Implementation Agent

Implement this plan without changing HTTP behavior, infrastructure, or live
resources. Use the existing OpenTelemetry dependencies, add focused in-memory
payload tests, and record observed names and attributes before opening the PR.
