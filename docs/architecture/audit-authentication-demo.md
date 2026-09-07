# Authentication audit demo

The production container runs `llm_agent.demo_app:app`. Its optional
`POST /demo/auth/login` endpoint checks configured demonstration credentials and
emits an OCSF event. It does **not** create a session, issue a token, or protect
the existing reservation workflow. The older OIDC/PostgreSQL application is
unchanged.

## Event path

```text
HTTP credential check
  -> DemoAuthenticationService
  -> AuthenticationEvent (pure OCSF builder)
  -> StdoutAuditSink: {"audit": EVENT} + newline
  -> ECS FireLens / Fluent Bit
  -> Firehose -> S3 -> Athena
```

This repository owns the first four steps. `movie-platform-infra` owns the
router, archive, queries, deployment, and teardown. See
[the platform delivery issue](https://github.com/movie-reservation-platform-lab/movie-platform-infra/issues/43).

The builder and sink protocol live in `llm_agent/application/audit/`; the stdout
adapter lives in `llm_agent/infrastructure/audit/`. Neither the use case nor the
event builder imports AWS code. The HTTP route extracts context and maps status
codes; it does not construct storage requests.

The event follows the platform's constrained
[OCSF 1.3 Authentication](https://schema.ocsf.io/1.3.0/classes/authentication)
contract. Activity 99, “Credential validation”, describes what actually
happened. A successful credential check is not evidence of a new login session.
The copied contract, shared example, and JSON Schema are in
`llm_agent/tests/fixtures/audit/`. The schema tests cover this subset, not every
optional OCSF field/profile.

## Run locally

From `llm_agent/`, install locked dependencies with `uv sync --frozen`. In a
**Bash** terminal, provide throwaway demo credentials without putting the
password in shell history:

```bash
export DEMO_AUTH_ENABLED=true
export DEMO_AUTH_USERNAME=demo-presenter
read -r -s -p 'Demo-only password: ' DEMO_AUTH_PASSWORD
export DEMO_AUTH_PASSWORD
export SERVICE_VERSION=local-audit-demo
export DEPLOYMENT_ENVIRONMENT=local
uv run --frozen --no-sync uvicorn llm_agent.demo_app:app --host 127.0.0.1 --port 8080
```

In another terminal, send an intentionally wrong credential check:

```bash
curl -i http://127.0.0.1:8080/demo/auth/login \
  -H 'Content-Type: application/json' \
  -H 'X-Request-Id: audit-request-001' \
  -H 'X-Correlation-Id: audit-action-001' \
  --data '{"username":"nonexistent-user","password":"intentionally-wrong"}'
```

Expect 401, `authenticated: false`, `request_id`, `audit_event_id`, and an active
`trace_id`. One compact audit record appears on stdout; a separate
`demo.auth.checked` operational log has the same IDs. Supplying the configured
credentials yields 200 and “Demo credentials accepted”, without a cookie or
token. Use the platform's browser demo page for that check instead of putting
the configured password in a curl argument.

Disabled is the default: the route is absent and returns 404. Enabling it
without both nonblank credentials aborts application startup. Wrong or missing
credentials return 401; malformed JSON, incorrect types, unknown fields, or
oversized bodies return a generic 400. Input limits are 256 username characters,
1,024 password characters, and 16 KiB for the complete JSON body.

For ECS, inject `DEMO_AUTH_PASSWORD` from a secret. Keep ingress restricted, use
throwaway credentials, and use TLS before transmitting any real credentials.
This endpoint has no production identity store, sessions, MFA, or brute-force
protection. Disable it when the demonstration ends. Stopping the local server
creates no AWS resources; cloud teardown is documented by the infrastructure
repository.

## Correlation and privacy

- `metadata.uid` is generated once and returned as `audit_event_id`.
- `metadata.correlation_uid` preserves a bounded `X-Correlation-Id` action ID.
- `unmapped.platform.request_id` preserves a bounded `X-Request-Id`, or a new
  ID is generated. Invalid external IDs are replaced, not logged.
- `trace_id` and `span_id` come from the actual active OpenTelemetry span,
  including unsampled spans. An incoming header alone does not populate them.
  The request span also carries `audit.event_id`, `audit.outcome`,
  `app.request_id`, `app.correlation_id`, and the ALB correlation header.
- `aws_alb_trace_id` contains a bounded, printable `X-Amzn-Trace-Id` when
  present. Match it to the ALB access-log trace field. CloudFront's
  `X-Amz-Cf-Id` is recorded only when actually present; it is not fabricated.
- Service identity is fixed to `movie-reservation-agent`. `SERVICE_VERSION`
  and `DEPLOYMENT_ENVIRONMENT` identify the build and deployment.

Failed events contain the literal `unknown`, never the attempted username or
decoded token claims. Successful demo events use the literal `demo-user`.
Passwords, cookies, tokens, request bodies, and query strings are not copied
into audit events or the operational summary. Correlation headers are search
keys, not authenticated identity or proof of AWS origin.

## Delivery limits and checks

A returned audit ID proves that the application emitted the record to stdout.
It does not acknowledge Firehose or S3 acceptance. Task loss, full router
buffers, or downstream outages can lose records; trace sampling can also leave
an event with no retained trace. An explicit stdout write failure returns 503
instead of a successful credential check. There is no outbox or durable replay
in this application.

Run `uv run --frozen --no-sync pytest tests automation/tests` from `llm_agent/`.
The tests validate the shared schema, response/event/log IDs, sampled and
unsampled contexts, input bounds, redaction, concurrent stdout framing,
disabled configuration, and the unchanged reservation workflow.
