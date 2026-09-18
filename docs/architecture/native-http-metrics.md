# Native HTTP metrics

Tracking: [issue #20](https://github.com/movie-reservation-platform-lab/movie-reservation-agent/issues/20).

The reservation agent passes a process-owned OpenTelemetry `MeterProvider` to
FastAPI instrumentation. When `OTEL_EXPORTER_OTLP_ENDPOINT` is configured, a
periodic OTLP/HTTP metric reader exports asynchronously alongside the existing
trace exporter. Export failures do not change HTTP responses. The SDK providers
flush and stop during normal process shutdown; the runtime's explicit,
idempotent `shutdown()` supports tests and composed runtimes.

The reader uses the OpenTelemetry SDK's default 60-second export interval and
respects `OTEL_METRIC_EXPORT_INTERVAL` and the standard OTLP metric exporter
settings. The instrumentation wraps the HTTP boundary, so deterministic and
model-backed runtime implementations share the same request metrics.

## Observed local payload

An `InMemoryMetricReader` with OpenTelemetry Python 1.44.0 and instrumentation
0.65b0 observed the following cumulative instruments:

| Native instrument | Type | Unit | Relevant attributes |
| --- | --- | --- | --- |
| `http.server.active_requests` | up/down sum | `{request}` | `http.method` |
| `http.server.duration` | histogram | `ms` | templated `http.target`, `http.method`, integer `http.status_code` |
| `http.server.response.size` | histogram | `By` | templated `http.target`, `http.method`, integer `http.status_code` |
| `movie_reservation_agent.http.server.requests` | monotonic sum | `{request}` | `http.request.method`, `http.route`, `http.response.status_class`, `outcome` |

Views remove caller-controlled host and raw network attributes from native HTTP
metrics. Every instrument carries the configured `service.name`, `service.version`, and
`deployment.environment.name` resource attributes. Health and readiness URLs
are excluded from native and custom HTTP metrics.

For routers included with a prefix, the locked FastAPI/OpenTelemetry combination
reports the native `http.target` as the router-local template (for example,
`/reserve-recommended-seat`). The custom counter reports the complete registered
application route (`/api/v1/demo/reserve-recommended-seat`). Consumers must use
these observed values rather than assuming both instruments have identical route
labels.

The custom counter uses only registered route templates and these bounded
values:

- status class: `1xx`, `2xx`, `3xx`, `4xx`, `5xx`, or `unknown`;
- outcome: `informational`, `success`, `redirect`, `client_error`,
  `server_error`, or `unknown`.

For every eligible registered method/route, the 4xx and 5xx counter series are
initialized with a real zero. Successful requests create and increment the 2xx
series. The implementation does not create fake requests or seed the duration
histogram, so zero traffic remains distinct from healthy traffic.

## Query semantics

The expected Prometheus translation is
`movie_reservation_agent_http_server_requests_total`, with dots in attribute
names translated to underscores. Infrastructure issue #57 must confirm this
name and the final labels through the ADOT/AMP acceptance path; the producer's
local OTLP evidence does not claim that backend translation as observed.

For a two-minute server-error percentage, sum increases for status class `5xx`
and divide by the increase across all status classes for the same eligible
route. Require a positive denominator and a recently timestamped source series.
Counter resets are handled by `increase()`. Missing or stale telemetry remains
NoData/Error and must not be converted to recovery. A return to Normal requires
fresh successful traffic after the failure stops.

The native duration histogram remains the source for latency. The custom
counter is the source for request/error-rate panels and alerts because its
route, status-class, and zero-series behavior are explicit. Span-error and log
signals remain separate investigation evidence.
