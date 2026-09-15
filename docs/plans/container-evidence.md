# Implementation Plan: agent container security evidence

## 1. Summary

Resume #15 / PR #17 with reviewed actions bb40579c285df0b581c48b10f9b34574d5c78639, v1alpha3 evidence, a read-only PR production-image scan, and agent-specific image remediation.

## 2. Goals

Preserve and include local docs/skills, retain complete diagnostics, validate the agent image, update existing PR #17 with [ai] prefixes and actual results.

## 3. Non-goals

Business/API changes, deployment, AWS changes, environment admission, exemptions and canonical image publication during PR preparation.

## 4. Current State

The issue branch already has shared v2 evidence in .github/workflows/ci.yml. Production uses Bookworm and includes uv, curl and source. llm_agent/automation/container_smoke.sh exercises the deterministic reservation flow with local MCP fakes but deletes diagnostics. Local docs/skills are on a separate old checkout. Merged recommendation-MCP #11 and reservation-MCP #9 demonstrate the requested v3 pattern.

## 5. Requirements and Assumptions

Confirmed: use the exact reviewed SHA; keep existing quality and publication check names; PRs cannot publish; keep .ai as canonical and ignore generated tooling. Unknowns resolved through execution: actual agent CVEs, required dependency upgrades, installed-image compatibility. Original checkout remains untouched while its changes are merged into the issue worktree.

## 6. Proposed Design

Keep security orchestration outside FastAPI/domain layers. Add container-security-check with contents:read only, linux/amd64 prod build, shared local v3 evaluator and full-directory artifact upload after failures. Main publication consumes the exact digest using pinned v3 composite actions. Isolate build tooling from the runtime; use compatible Python bases and a non-editable environment. Remediate scan-confirmed OS findings with Trixie and refreshed perl-base following MCP implementations; update locked Python dependencies for demonstrated findings. FastAPI/Starlette security updates also require compatible OpenTelemetry instrumentation; upgrade that family together and verify trace/audit correlation tests. Preserve build, smoke and policy logs.

## 7. Alternatives Considered

- Copy evaluator code: easy initially, duplicates security policy; rejected.
- Shared reviewed tooling in existing jobs: preserves ownership and signer identities; chosen.
- Upgrade all dependencies blindly: broader compatibility risk; prefer scan-directed updates.

## 8. API / Interface Changes

No application API changes. Evidence becomes ci.movie-platform.dev/v1alpha3 with the same four canonical files and embedded policy evaluation. vulnerability-policy.json is diagnostic only. PR artifacts are diagnostics only. Add optional smoke output directory for retained diagnostics.

## 9. Data Model / Persistence Changes

None. Hosted artifacts retain 14 days; old v2 runs do not substitute for fresh v3 acceptance.

## 10. Security, Privacy, and Abuse Considerations

Canonical repository/main/push guard only; write permissions stay in publish-image. Disable persisted checkout credentials. Use reviewed full SHAs. Scanner uses current central approved policy; fail closed on evaluation errors and unexempted CRITICAL findings. Never upload tokens or local-change backups. No exemption requested.

## 11. Performance, Scalability, and Reliability Considerations

Bound CI timeouts, preserve PR cancellation and serialized main publication. Dedicated PR scan adds one build but avoids canonical duplicate scans. Complete diagnostics survive rejected policy and smoke failures. Production copies only installed application dependencies.

## 12. Implementation Steps

1. Back up original changes under ignored .local-container-security and reconcile docs/skills in the issue worktree.
2. Update workflow shared pins/v3 input and read-only security job, with correct llm_agent build context and root tooling path.
3. Build/scan baseline; remediate llm_agent/Dockerfile and scan-confirmed pyproject.toml/uv.lock dependencies.
4. Strengthen automation/container_smoke.sh contents checks and diagnostic retention; add behavior-focused failure-path tests and workflow boundary assertions.
5. Ignore/untrack generated assistant directories and AGENTS.md; regenerate locally from .ai; update documentation.
6. Run runtime/automation tests, scoped CI lint/format/compile, production smoke and shared v3 scan; retain actual results.
7. Commit/push with [ai], update existing PR #17, inspect hosted checks and download diagnostic artifact.

## 13. Testing Strategy

From llm_agent: uv sync --frozen; uv run --frozen --no-sync pytest tests automation/tests. Run exact workflow lint/format/compile targets. Build linux/amd64 prod, smoke health and full reservation sequence with local MCP fakes, verify UID and installed contents. Scan baseline and remediated images with reviewed Node 24 helper and current central v3 policy. Test failure retention without real external dependencies.

## 14. Rollout / Migration Plan

Actions #13 is merged at the requested SHA. Environment reader/admission support is separately tracked by movie-platform-environments#82. Owner merge triggers fresh canonical publication; PR success does not prove publication/admission. Roll back image/workflow changes by reverting commits.

## 15. Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| Agent differs from siblings | High | Medium | Scan its own image before and after |
| Dependency incompatibility | High | Medium | Full runtime suite and installed-image smoke |
| Lost local edits | High | Low | Backup and merge; leave original checkout intact |
| PR gains publication authority | High | Low | Read-only job and guard contract tests |
| Policy/network failure | Medium | Medium | Fail closed and upload complete diagnostics |

## 16. Done Criteria

Local changes included, generated tooling untracked, agent image built/smoked/scanned, blocking findings remediated, remaining findings disclosed, tests green, hosted checks inspected, PR #17 updated.

## 17. Review Checklist

- [x] Requirements, non-goals and repository conventions checked.
- [x] Alternatives, security, reliability and rollback explicit.
- [x] Ordered implementation and validation commands specified.
- [x] Actual local image results recorded in `docs/knowledge/container-security-validation.md`.
- [ ] Hosted PR checks and artifact inspected.

## 18. Handoff Prompt for Implementation Agent

Implement this plan in the named files, preserving original local work and application boundaries. Use the reviewed shared SHA, scan the agent image, retain diagnostics and update PR #17. Run the verification above. No image publication or AWS changes during PR preparation.

## KB basis

Used `/home/patex1987/Documents/programming_kb/patterns/Multi-Stage Python Container Builds with uv.md`: compatible interpreter bases, non-editable runtime environment, isolated tooling and final-image entry-point smoke.
