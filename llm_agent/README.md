# Service

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

Incoming `traceparent`, `tracestate`, `X-Correlation-Id`, and `X-Request-Id`
values are propagated to MCP calls. Set `OTEL_EXPORTER_OTLP_ENDPOINT` to export
agent traces through OTLP/HTTP.

## Health checks
Periodically executing a check against a dummy endpoint (you can define more advanced checks)
```json
{"event": "new request id has been created", "timestamp": "2025-09-08T17:11:06.045360Z", "service_name": "llm_agent_fastapi", "version": "0.1", "level": "info"}
INFO:     127.0.0.1:44232 - "GET /api/v1/health/dummy-health HTTP/1.1" 200 OK
```

# Development

## Running from IDE
To run in development mode in pycharm (or your preferred IDE) use: `[./configuration/local_or_ide/local_development.env](../configuration/local_or_ide/local_development.env)`
and execute `llm_agent/manage.py` with that env file

## Running from docker
To run in development mode once the container the image is built (see the sections below), run

To execute the service immediately:
```shell
docker run -it -p 8080:8080 \
  --env-file "/home/patex1987/development/llm_agent_webapp/configuration/docker/local_development.env"  \
  --rm \
  fastapi_rest:local_dev
```

Output:
```text
{"event": "Uvicorn server configuration: host='0.0.0.0' port=8080 log_level='info' reload=True log_config_path='/app/llm_agent/configuration/log_config_json.json'", "timestamp": "2025-09-09T15:41:58.886552Z", "service_name": "llm_agent_fastapi", "version": "0.1", "level": "info"}
{"event": "Will watch for changes in these directories: ['/app']", "timestamp": "2025-09-09T15:41:58.887500Z", "service_name": "llm_agent_fastapi", "version": "0.1", "level": "info"}
{"event": "Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)", "timestamp": "2025-09-09T15:41:58.887729Z", "service_name": "llm_agent_fastapi", "version": "0.1", "level": "info"}
{"event": "Started reloader process [7] using StatReload", "timestamp": "2025-09-09T15:41:58.887852Z", "service_name": "llm_agent_fastapi", "version": "0.1", "level": "info"}
{"event": "Started server process [9]", "timestamp": "2025-09-09T15:42:00.231746Z", "service_name": "llm_agent_fastapi", "version": "0.1", "level": "info"}
{"event": "Waiting for application startup.", "timestamp": "2025-09-09T15:42:00.231913Z", "service_name": "llm_agent_fastapi", "version": "0.1", "level": "info"}
```

To execute the container with a shell session:
```shell
docker run -it -p 8080:8080 \
  --env-file "/home/patex1987/development/llm_agent_webapp/configuration/docker/local_development.env"  \
  --rm \
  fastapi_rest:local_dev \
  /bin/bash
```

If you don't want to use the env vars, and run uvicorn directly and configure through cli args, check the Dockerfile for the commented out commands
```dockerfile
# ---------- dev (editable install) ----------
#CMD ["uvicorn","llm_agent.app:create_app","--host","0.0.0.0","--port","8080","--reload","--log-config","./llm_agent/configuration/log_config_json.json","--factory"]
CMD ["python", "manage.py"]

# ---------- prod (lean runtime) ----------
# ...
#CMD ["uvicorn","llm_agent.app:create_app","--host","0.0.0.0","--port","8080","--log-config","./llm_agent/configuration/log_config_json.json","--factory"]
CMD ["python", "manage.py"]
```


### Build in development mode

1. Navigate to the `llm_agent` folder
2. Execute:
```shell
docker build --target dev -t fastapi_rest:local_dev -f ./Dockerfile .
```

enter the container with non-running service:
```shell
docker run -it --rm fastapi_rest:local_dev /bin/bash 
```

### Build in production mode
1. Navigate to the `llm_agent` folder
2. Execute:
```shell
docker build --target prod -t fastapi_rest:local_prod -f ./Dockerfile .
```
