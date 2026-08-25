#!/usr/bin/env bash
set -euo pipefail

image="${1:-movie-reservation-agent:smoke}"
container_name="movie-reservation-agent-smoke-${RANDOM}"
smoke_dir="$(mktemp -d)"
recommendation_pid=""
reservation_pid=""

cleanup() {
  status=$?
  trap - EXIT
  if [[ $status -ne 0 ]]; then
    docker logs "$container_name" 2>/dev/null || true
    cat "$smoke_dir/recommendation.log" 2>/dev/null || true
    cat "$smoke_dir/reservation.log" 2>/dev/null || true
  fi
  docker rm --force "$container_name" >/dev/null 2>&1 || true
  [[ -z "$recommendation_pid" ]] || kill "$recommendation_pid" >/dev/null 2>&1 || true
  [[ -z "$reservation_pid" ]] || kill "$reservation_pid" >/dev/null 2>&1 || true
  rm -rf "$smoke_dir"
  exit "$status"
}
trap cleanup EXIT

./.venv/bin/python automation/fake_mcp_server.py recommendation >"$smoke_dir/recommendation.log" 2>&1 &
recommendation_pid=$!
./.venv/bin/python automation/fake_mcp_server.py reservation >"$smoke_dir/reservation.log" 2>&1 &
reservation_pid=$!

for port in 8091 8092; do
  for attempt in {1..30}; do
    status="$(curl --silent --output /dev/null --write-out '%{http_code}' "http://127.0.0.1:${port}/mcp" || true)"
    if [[ "$status" != "000" ]]; then
      break
    fi
    if [[ $attempt -eq 30 ]]; then
      echo "Fake MCP on port ${port} did not start." >&2
      exit 1
    fi
    sleep 1
  done
done

docker run --detach --name "$container_name" --network host "$image" >/dev/null

for attempt in {1..30}; do
  if curl --fail --silent http://127.0.0.1:8080/health >/dev/null; then
    break
  fi
  if [[ $attempt -eq 30 ]]; then
    echo "Agent did not become healthy." >&2
    exit 1
  fi
  sleep 1
done

response="$(
  curl \
    --fail \
    --silent \
    --header 'Content-Type: application/json' \
    --header 'traceparent: 00-11111111111111111111111111111111-2222222222222222-01' \
    --header 'X-Correlation-Id: smoke-correlation-1' \
    --header 'X-Request-Id: smoke-request-1' \
    --data '{"movie_preference":"something exciting","seat_preference":"aisle","fault":"none"}' \
    http://127.0.0.1:8080/api/v1/demo/reserve-recommended-seat
)"

grep --quiet '"outcome":"confirmed"' <<<"$response"
grep --quiet '"correlation_id":"smoke-correlation-1"' <<<"$response"
grep --quiet '"tool_name":"reservation_get_request_status"' <<<"$response"
test "$(docker exec "$container_name" id -u)" = "10001"

echo "Reservation agent container smoke passed."
