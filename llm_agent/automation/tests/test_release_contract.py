from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (ROOT.parent / ".github/workflows/ci.yml").read_text(encoding="utf-8")
DOCKERFILE = (ROOT / "Dockerfile").read_text(encoding="utf-8")
SMOKE = (ROOT / "automation/container_smoke.sh").read_text(encoding="utf-8")


def test_production_image_is_locked_and_non_root() -> None:
    assert "ghcr.io/astral-sh/uv:0.12.3" in DOCKERFILE
    assert "UV_PYTHON_DOWNLOADS=never" in DOCKERFILE
    assert "useradd -r -u 10001 appuser" in DOCKERFILE
    assert "USER appuser" in DOCKERFILE
    assert "EXPOSE 8080" in DOCKERFILE
    assert "http://127.0.0.1:8080/health" in DOCKERFILE


def test_container_smoke_uses_local_mcp_fakes_and_happy_path() -> None:
    assert "fake_mcp_server.py recommendation" in SMOKE
    assert "fake_mcp_server.py reservation" in SMOKE
    assert "/api/v1/demo/reserve-recommended-seat" in SMOKE
    assert '"outcome":"confirmed"' in SMOKE
    assert 'docker exec "$container_name" id -u' in SMOKE


def test_publication_is_main_only_gated_and_attested() -> None:
    publish_job = workflow_job("publish-image")

    assert "github.event_name == 'push'" in publish_job
    assert "github.ref == 'refs/heads/main'" in publish_job
    assert "- quality" in publish_job
    assert "- tests" in publish_job
    assert "- automation-tests" in publish_job
    assert "- container-smoke" in publish_job
    assert "packages: write" in publish_job
    assert "id-token: write" in publish_job
    assert "attestations: write" in publish_job
    assert "platforms: linux/amd64" in publish_job
    assert "provenance: false" in publish_job
    assert "/actions/container-evidence@" in publish_job
    assert "digest: ${{ steps.build.outputs.digest }}" in publish_job
    assert "pull_request_target:" not in WORKFLOW


def test_repository_automation_is_separate_from_runtime_tests() -> None:
    runtime_job = workflow_job("tests")
    automation_job = workflow_job("automation-tests")

    assert "pytest tests" in runtime_job
    assert "pytest automation/tests" not in runtime_job
    assert "pytest automation/tests" in automation_job
    assert "pytest tests" not in automation_job


def workflow_job(name: str) -> str:
    lines = WORKFLOW.splitlines()
    start = lines.index(f"  {name}:")
    end = next(
        (
            index
            for index in range(start + 1, len(lines))
            if lines[index].startswith("  ") and lines[index].endswith(":") and not lines[index].startswith("    ")
        ),
        len(lines),
    )
    return "\n".join(lines[start:end])


def test_shared_evidence_has_pinned_identity_and_precedes_no_quality_gate() -> None:
    publish_job = workflow_job("publish-image")
    assert "github.repository == 'movie-reservation-platform-lab/movie-reservation-agent'" in publish_job
    assert "cancel-in-progress: ${{ github.event_name == 'pull_request' }}" in WORKFLOW
    assert "persist-credentials: false" in publish_job
    assert "component: reservation-agent" in publish_job
    assert "tags: ${{ steps.candidate.outputs.image_ref }}:${{ steps.candidate.outputs.tag }}" in publish_job
    assert publish_job.index("/actions/prepare-container-candidate@") < publish_job.index("docker/login-action@")
    assert publish_job.index("docker/build-push-action@") < publish_job.index("/actions/container-evidence@")
    references = re.findall(r"uses: (\S+)", WORKFLOW)
    assert all(re.fullmatch(r"[^@]+@[0-9a-f]{40}", reference) for reference in references)
    shared_pins = [
        reference.split("@")[1] for reference in references if "/movie-platform-actions/actions/" in reference
    ]
    assert len(shared_pins) == 2 and shared_pins[0] == shared_pins[1]
    assert "aws-actions/" not in WORKFLOW
