from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import fastapi
import pytest
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.resources import Resource
from starlette.testclient import TestClient

from llm_agent.core.telemetry import TelemetryRuntime, create_telemetry_runtime, instrument_for_telemetry
from llm_agent.demo.config import DemoAgentSettings
from llm_agent.demo_app import create_demo_app
from tests.fake_implementations.demo_mcp_client import FakeMcpClient

RESOURCE_ATTRIBUTES = {
    "service.name": "movie-reservation-agent",
    "service.version": "test-revision",
    "deployment.environment.name": "test",
}
OUTCOME_METRIC = "movie_reservation_agent.http.server.requests"


@dataclass
class MetricHarness:
    app: fastapi.FastAPI
    runtime: TelemetryRuntime
    reader: InMemoryMetricReader


@pytest.fixture
def metric_harness() -> Iterator[MetricHarness]:
    app = fastapi.FastAPI()

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/items/{result}")
    async def item(result: str) -> dict[str, str]:
        if result == "client-error":
            raise fastapi.HTTPException(status_code=422, detail="invalid test item")
        if result == "server-error":
            raise fastapi.HTTPException(status_code=502, detail="test dependency failed")
        return {"result": result}

    resource = Resource.create(RESOURCE_ATTRIBUTES)
    reader = InMemoryMetricReader()
    runtime = create_telemetry_runtime(resource=resource, metric_readers=[reader])
    instrument_for_telemetry(app, runtime=runtime)
    yield MetricHarness(app, runtime, reader)
    runtime.shutdown()


def test_initializes_bounded_error_classes_without_fake_traffic(metric_harness: MetricHarness) -> None:
    points = metric_points(metric_harness.reader, OUTCOME_METRIC)

    assert point_values(points) == {
        ("GET", "/items/{result}", "4xx", "client_error"): 0,
        ("GET", "/items/{result}", "5xx", "server_error"): 0,
    }
    assert native_metric_names(metric_harness.reader) == set()


def test_emits_native_http_metrics_and_bounded_request_outcomes(metric_harness: MetricHarness) -> None:
    with TestClient(metric_harness.app) as client:
        assert client.get("/items/ok").status_code == 200
        assert client.get("/items/client-error").status_code == 422
        assert client.get("/items/server-error").status_code == 502

    points = metric_points(metric_harness.reader, OUTCOME_METRIC)
    assert point_values(points) == {
        ("GET", "/items/{result}", "2xx", "success"): 1,
        ("GET", "/items/{result}", "4xx", "client_error"): 1,
        ("GET", "/items/{result}", "5xx", "server_error"): 1,
    }
    assert {frozenset(point.attributes) for point in points} == {
        frozenset(
            {
                "http.request.method",
                "http.route",
                "http.response.status_class",
                "outcome",
            }
        )
    }
    assert "http.server.duration" in native_metric_names(metric_harness.reader)
    assert native_duration_attribute_keys(metric_harness.reader) == {
        "http.method",
        "http.status_code",
        "http.target",
    }
    exported_resource = resource_attributes(metric_harness.reader, OUTCOME_METRIC)
    assert {key: exported_resource[key] for key in RESOURCE_ATTRIBUTES} == RESOURCE_ATTRIBUTES


def test_health_traffic_is_excluded_from_native_and_outcome_metrics(metric_harness: MetricHarness) -> None:
    with TestClient(metric_harness.app) as client:
        assert client.get("/health").status_code == 200

    points = metric_points(metric_harness.reader, OUTCOME_METRIC)
    assert all(point.attributes["http.route"] != "/health" for point in points)
    assert native_metric_names(metric_harness.reader) == set()


def test_repeated_setup_does_not_duplicate_observations(metric_harness: MetricHarness) -> None:
    instrument_for_telemetry(metric_harness.app, runtime=metric_harness.runtime)

    with TestClient(metric_harness.app) as client:
        assert client.get("/items/ok").status_code == 200

    points = metric_points(metric_harness.reader, OUTCOME_METRIC)
    assert point_values(points)[("GET", "/items/{result}", "2xx", "success")] == 1


def test_demo_runtime_records_the_primary_route_without_raw_request_values() -> None:
    resource = Resource.create(RESOURCE_ATTRIBUTES)
    reader = InMemoryMetricReader()
    runtime = create_telemetry_runtime(resource=resource, metric_readers=[reader])
    app = create_demo_app(
        settings=DemoAgentSettings(demo_reservation_poll_interval_seconds=0),
        mcp_client=FakeMcpClient(),
        telemetry_runtime=runtime,
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/demo/reserve-recommended-seat",
                json={
                    "movie_preference": "a value that must not become a metric label",
                    "seat_preference": "aisle",
                    "fault": "none",
                },
            )
        assert response.status_code == 200
        points = metric_points(reader, OUTCOME_METRIC)
        assert (
            point_values(points)[
                (
                    "POST",
                    "/api/v1/demo/reserve-recommended-seat",
                    "2xx",
                    "success",
                )
            ]
            == 1
        )
        duration_targets = {point.attributes["http.target"] for point in metric_points(reader, "http.server.duration")}
        assert duration_targets == {"/reserve-recommended-seat"}
        assert "a value that must not become a metric label" not in repr(points)
    finally:
        runtime.shutdown()


def test_runtime_shutdown_is_idempotent(metric_harness: MetricHarness) -> None:
    metric_harness.runtime.shutdown()
    metric_harness.runtime.shutdown()

    assert metric_harness.runtime._is_shutdown is True


def metric_points(reader: InMemoryMetricReader, name: str) -> list[object]:
    data = reader.get_metrics_data()
    assert data is not None
    for resource_metrics in data.resource_metrics:
        for scope_metrics in resource_metrics.scope_metrics:
            for metric in scope_metrics.metrics:
                if metric.name == name:
                    return list(metric.data.data_points)
    raise AssertionError(f"metric {name!r} was not exported")


def native_metric_names(reader: InMemoryMetricReader) -> set[str]:
    data = reader.get_metrics_data()
    if data is None:
        return set()
    return {
        metric.name
        for resource_metrics in data.resource_metrics
        for scope_metrics in resource_metrics.scope_metrics
        for metric in scope_metrics.metrics
        if metric.name != OUTCOME_METRIC
    }


def point_values(points: list[object]) -> dict[tuple[str, str, str, str], int]:
    return {
        (
            point.attributes["http.request.method"],
            point.attributes["http.route"],
            point.attributes["http.response.status_class"],
            point.attributes["outcome"],
        ): point.value
        for point in points
    }


def resource_attributes(reader: InMemoryMetricReader, metric_name: str) -> dict[str, object]:
    data = reader.get_metrics_data()
    assert data is not None
    for resource_metrics in data.resource_metrics:
        if any(
            metric.name == metric_name
            for scope_metrics in resource_metrics.scope_metrics
            for metric in scope_metrics.metrics
        ):
            return dict(resource_metrics.resource.attributes)
    raise AssertionError(f"resource for {metric_name!r} was not exported")


def native_duration_attribute_keys(reader: InMemoryMetricReader) -> set[str]:
    points = metric_points(reader, "http.server.duration")
    return set().union(*(point.attributes for point in points))
