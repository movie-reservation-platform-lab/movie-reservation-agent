from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (ROOT.parent / ".github/workflows/ci.yml").read_text(encoding="utf-8")
DOCKERFILE = (ROOT / "Dockerfile").read_text(encoding="utf-8")
SMOKE = (ROOT / "automation/container_smoke.sh").read_text(encoding="utf-8")
REVIEWED_ACTIONS_SHA = "036531133bcefd454b5afc0eb55f8ba0328901ea"


def test_production_image_is_locked_and_non_root() -> None:
    assert "ghcr.io/astral-sh/uv:0.12.3" in DOCKERFILE
    assert "UV_PYTHON_DOWNLOADS=never" in DOCKERFILE
    assert "useradd -r -u 10001 appuser" in DOCKERFILE
    assert "USER appuser" in DOCKERFILE
    assert "EXPOSE 8080" in DOCKERFILE
    assert "http://127.0.0.1:8080/health" in DOCKERFILE
    production = DOCKERFILE.split("FROM python-runtime AS prod", 1)[1]
    assert "COPY --from=build --chown=10001:10001 /venv /venv" in production
    assert "ca-certificates tini perl-base" in production
    assert "COPY --from=uv" not in production
    assert "COPY --from=build /app" not in production
    assert "curl" not in production
    assert "pip uninstall -y pip" in production


def test_container_smoke_uses_local_mcp_fakes_and_happy_path() -> None:
    assert "fake_mcp_server.py recommendation" in SMOKE
    assert "fake_mcp_server.py reservation" in SMOKE
    assert "/api/v1/demo/reserve-recommended-seat" in SMOKE
    assert '"outcome":"confirmed"' in SMOKE
    assert 'docker exec "$container_name" id -u' in SMOKE


def test_publication_is_main_only_gated_and_attested() -> None:
    publish_job = workflow_job("publish-image")

    assert re.findall(r"^    if: (.+)$", publish_job, re.MULTILINE) == [
        (
            "github.event_name == 'push' && github.ref == 'refs/heads/main' && "
            "github.repository == 'movie-reservation-platform-lab/movie-reservation-agent'"
        )
    ]
    assert "- quality" in publish_job
    assert "- tests" in publish_job
    assert "- automation-tests" in publish_job
    assert "- container-smoke" in publish_job
    assert re.search(r"^    permissions:\n((?:      .+\n)+)", publish_job, re.MULTILINE).group(1) == (
        "      contents: read\n      packages: write\n      id-token: write\n      attestations: write\n"
    )
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


def workflow_step(job: str, name: str) -> str:
    match = re.search(rf"^      - name: {re.escape(name)}\n.*?(?=^      - name:|\Z)", job, re.MULTILINE | re.DOTALL)
    assert match is not None, f"Missing workflow step: {name}"
    return match.group()


def test_prepare_receives_explicit_caller_token() -> None:
    prepare_step = workflow_step(workflow_job("publish-image"), "Prepare canonical candidate")

    assert f"/actions/prepare-container-candidate@{REVIEWED_ACTIONS_SHA}" in prepare_step
    assert "        with:\n          component: reservation-agent\n" in prepare_step
    assert "          github-token: ${{ github.token }}\n" in prepare_step


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
    assert shared_pins == [REVIEWED_ACTIONS_SHA, REVIEWED_ACTIONS_SHA]
    assert "evidence-version: v1alpha3" in publish_job
    tooling_checkout = workflow_step(
        workflow_job("container-security-check"), "Check out reviewed shared security tooling"
    )
    assert f"          ref: {REVIEWED_ACTIONS_SHA}\n" in tooling_checkout
    assert "repository: movie-reservation-platform-lab/movie-platform-actions" in tooling_checkout
    assert "aws-actions/" not in WORKFLOW


def test_pr_security_gate_uses_shared_policy_without_publication_permissions() -> None:
    security_job = workflow_job("container-security-check")

    assert "pull_request:" in WORKFLOW
    assert "github.event_name != 'push' || github.ref != 'refs/heads/main'" in security_job
    assert "github.repository != 'movie-reservation-platform-lab/movie-reservation-agent'" in security_job
    assert "- quality" in security_job
    assert "- automation-tests" in security_job
    assert "permissions:\n      contents: read" in security_job
    assert ": write" not in security_job
    assert "docker/login-action" not in security_job
    assert "push: true" not in security_job
    assert security_job.count("persist-credentials: false") == 2
    assert "node-version: '24'" in security_job
    assert "--platform linux/amd64 --target prod" in security_job
    assert "node .platform-actions/local-tools/container-security/lib/scan.mjs" in security_job
    assert "--evidence-version v1alpha3 --component reservation-agent" in security_job
    assert security_job.count("GH_TOKEN:") == 1
    assert security_job.index("GH_TOKEN:") > security_job.index("docker build")
    assert "continue-on-error" not in security_job
    assert "|| true" not in security_job
    assert "aquasecurity/trivy-action" not in security_job


def test_pr_security_diagnostics_survive_policy_failure_and_are_not_candidate_evidence() -> None:
    security_job = workflow_job("container-security-check")

    assert security_job.index("lib/scan.mjs") < security_job.index("actions/upload-artifact@")
    assert "if: ${{ !cancelled() }}" in security_job
    assert '--output-dir "$RUNNER_TEMP/reservation-agent-pr-security"' in security_job
    assert "path: ${{ runner.temp }}/reservation-agent-pr-security/" in security_job
    assert "name: reservation-agent-pr-vulnerability-report-" in security_job
    assert "if-no-files-found: error" in security_job
    assert "retention-days: 14" in security_job
    assert "attest-build-provenance" not in security_job
    assert "container-evidence@" not in security_job


def test_pr_jobs_cannot_publish_or_mask_build_failures() -> None:
    before_publish = WORKFLOW.split("  publish-image:", 1)[0]
    assert ": write" not in before_publish
    for forbidden in ("push: true", "docker/login-action", "docker push", "container-evidence@"):
        assert forbidden not in before_publish
    security = workflow_job("container-security-check")
    assert "working-directory: ." in security
    assert "shell: bash" in security  # Explicit bash uses -e -o pipefail in Actions.
    assert "movie-reservation-agent:pr-security llm_agent" in security
    assert 'tee "$RUNNER_TEMP/reservation-agent-pr-security/build.log"' in security
    assert 'tee "$RUNNER_TEMP/reservation-agent-pr-security/scan.log"' in security
    smoke = workflow_job("container-smoke")
    assert "if: ${{ !cancelled() }}" in smoke
    assert "actions/upload-artifact@" in smoke
    assert "reservation-agent-smoke/" in smoke
