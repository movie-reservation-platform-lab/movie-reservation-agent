# Implementation Plan: Authenticated Prepare Adoption

## 1. Summary

[Issue #18](https://github.com/movie-reservation-platform-lab/movie-reservation-agent/issues/18)
adopts the authenticated prepare contract from merged
[movie-platform-actions PR #18](https://github.com/movie-reservation-platform-lab/movie-platform-actions/pull/18)
at reviewed commit `036531133bcefd454b5afc0eb55f8ba0328901ea`.
The recommended approach is one coordinated caller migration: move both
publisher actions and the PR/local scanner checkout to that commit, wire the
required GitHub token into prepare, and strengthen repository contract tests.

## 2. Goals

- Authenticate prepare's canonical-main lookup with the caller's GitHub token.
- Keep all three shared-action/tool consumers on one reviewed immutable commit.
- Protect publication and PR-security boundaries with focused offline tests.
- Document rollout limits, exact-run post-merge acceptance, and atomic rollback.

## 3. Non-goals

- Application behavior, APIs, Docker images, dependencies, exemptions, schemas,
  component identities, or unrelated action versions.
- Environment credentials, GitHub settings, deployment, publication/admission
  dispatch, ECR copy, issue closure, or PR merge.
- Reinterpreting historical validation performed with older shared-action pins.

## 4. Current State

Upstream `main` is `41a8f6b5bf02db38d47cff49e2f9721e49467941`.
`.github/workflows/ci.yml` pins prepare, evidence, and the PR scanner checkout to
`bb40579c285df0b581c48b10f9b34574d5c78639`. Prepare lacks `github-token`, while
evidence and the PR scanner already receive `${{ github.token }}`. Publishing is
restricted to a push on canonical `main` and grants exactly `contents: read`,
`packages: write`, `id-token: write`, and `attestations: write`. The PR security
job has only `contents: read`, builds the production image, and cannot publish.

`llm_agent/automation/tests/test_release_contract.py` already covers component
identity, v1alpha3, coordinated older pins, action ordering, PR scanning, and the
absence of `pull_request_target`, but does not assert prepare's required token or
the complete exact publication guard and permission block.

Open PR #14 changes only an audit fixture description and does not overlap this
slice. Merged recommendation-MCP PR #13 provides the successful caller canary.

## 5. Requirements and Assumptions

### Confirmed Requirements

- Use `036531133bcefd454b5afc0eb55f8ba0328901ea` for all three consumers.
- Add `github-token: ${{ github.token }}` only to prepare's inputs.
- Preserve v1alpha3, `reservation-agent`, existing permissions, canonical
  main-push-only publication, credential-restricted PR scanning, and fail-closed
  behavior.
- Cover caller wiring and boundaries with offline tests and current docs.

### Assumptions

- The successful recommendation-MCP canary establishes public-repository caller
  compatibility, while private-repository compatibility remains unproven.
- Failure-path and scanner-cleanup changes are consumed through the shared pin;
  the agent requires no compatibility workaround based on inspected workflows.
- Historical scan counts and hashes retain their original policy/tooling SHA.

### Open Questions

None block implementation. Live canonical publication and exact-run admission
remain post-merge acceptance activities requiring separate authorization.

## 6. Proposed Design

Update only the three reviewed shared-tool references and prepare input in the
workflow. Introduce one test constant for the reviewed SHA, extract named steps
for precise assertions, and assert the exact canonical condition and permission
set. Update current caller documentation and link the prior evidence plan to
this migration while leaving historical validation evidence unchanged.

This keeps the token within GitHub expression wiring, adds no secrets, and
inherits actions PR #18's bounded diagnostics and scanner-cleanup hardening.

## 7. Alternatives Considered

### Alternative A: Coordinated adoption

- Pros: one reviewed release for prepare, evidence, and scanning; includes all
  caller-impact hardening; matches the canary.
- Cons: consumes scanner behavior changes together with authenticated prepare.
- Decision: selected because actions PR #18 explicitly requires coordinated
  caller pins and the agent contract is compatible.

### Alternative B: Update prepare only

- Pros: smallest textual workflow change.
- Cons: pin drift, omission of related evidence/scanner hardening, and departure
  from the reviewed migration contract.
- Decision: rejected.

## 8. API / Interface Changes

The shared prepare action invocation gains its required `github-token` input.
No application API, internal Python interface, event, evidence schema, or
component identity changes.

## 9. Data Model / Persistence Changes

None.

## 10. Security, Privacy, and Abuse Considerations

Prepare uses `${{ github.token }}` with the publishing job's existing
`contents: read`; no environment reader-app credential or new secret is used.
Passing the token does not reduce its existing job authority. Tests retain exact
publisher permissions, the read-only PR job, credential-disabled checkouts,
canonical repository/main/push restriction, and no `pull_request_target`.
Diagnostics must not expose tokens, response bodies, or private configuration.

## 11. Performance, Scalability, and Reliability Considerations

The reviewed prepare action makes one bounded authenticated canonical-main
request and fails closed without anonymous fallback. The updated scanner also
surfaces cleanup failure. PR CI cannot exercise prepare because publication must
remain disabled there; a new canonical main run is required after merge.

## 12. Implementation Steps

1. Update shared tooling and prepare wiring.
   - Change: move three pins together and add the token input.
   - Files/modules likely affected: `.github/workflows/ci.yml`.
   - Notes: preserve all existing guards, permissions, identities, and versions.
   - Verification: focused workflow contract tests and diff inspection.
2. Strengthen caller contract tests.
   - Change: assert exact pins, prepare token, publication guard/permissions,
     PR scanner checkout, and existing security boundaries.
   - Files/modules likely affected:
     `llm_agent/automation/tests/test_release_contract.py`.
   - Notes: use step-scoped assertions so the evidence token cannot mask a
     missing prepare token.
   - Verification: automation pytest plus negative in-memory mutations.
3. Update current caller documentation.
   - Change: record authenticated prepare, full shared hardening, rollout limits,
     exact-run acceptance, and atomic rollback.
   - Files/modules likely affected: `llm_agent/README.md`,
     `docs/plans/container-evidence.md`, and this plan.
   - Notes: preserve historical scan evidence at its original SHA.
   - Verification: link/pin search and diff review.
4. Validate and deliver.
   - Change: run documented frozen tests, scoped lint/format/compile, diff checks,
     read-only reviews, commit/push one branch, and open one PR closing #18.
   - Files/modules likely affected: no additional production files.
   - Notes: ordinary PR CI is expected; publication remains skipped.
   - Verification: local results and GitHub status checks.

## 13. Testing Strategy

From `llm_agent/`, run `uv sync --frozen`, runtime and automation pytest, the
exact workflow Ruff lint/format scopes, and compileall. Run focused workflow
contract tests and safe in-memory negative mutations for token, pins,
permissions, and publication guards. Run `git diff --check` before and after
staging. Application/container behavior is unchanged, but the full documented
offline suite guards against accidental scope drift.

## 14. Rollout / Migration Plan

Merge producers one at a time. For this repository, a maintainer merge should
create a new canonical `CI` run for the merge commit on `main`; identify that
successful run by repository, workflow, `push` event, `main` branch, head SHA,
and successful `publish immutable GHCR image` job. Admit that exact new run ID
separately. Never reuse the canary or an older agent run. Roll back by reverting
both action pins, the scanner checkout pin, and prepare token input together,
with matching tests/current docs.

## 15. Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
| --- | ---: | ---: | --- |
| Missing or misplaced token input | High | Low | Step-scoped exact contract test |
| Partial pin update | High | Low | One constant and exact three-consumer tests |
| Accidental PR publication authority | High | Low | Exact guard/permission and forbidden-operation tests |
| Overstating live compatibility | Medium | Medium | Separate offline, PR CI, canonical publication, and admission evidence |
| Historical evidence rewritten | Medium | Low | Leave historical validation SHA/counts unchanged |

## 16. Done Criteria

- One issue, branch, bounded commit, and PR with required `[ai]` titles.
- Three exact coordinated pins and explicit prepare token are present.
- Tests cover required wiring and unchanged security/publication boundaries.
- Current caller docs explain full shared hardening, acceptance, and rollback.
- Local checks and read-only reviews pass; attributable PR CI failures are fixed.

## 17. Review Checklist

- [x] Requirements are explicit
- [x] Non-goals are explicit
- [x] Existing code conventions were checked
- [x] Alternatives were considered
- [x] Security implications were reviewed
- [x] Scalability and reliability implications were reviewed
- [x] Testing strategy is complete
- [x] Rollout and rollback are defined
- [x] Implementation steps are ordered and concrete

Implementation verification on 2026-09-15: frozen dependency sync passed;
78 runtime tests and 11 automation tests passed; the workflow's scoped Ruff
lint and format checks passed; compileall and diff checks passed. Seven safe
in-memory mutations confirmed the tests reject a missing prepare token, drift in
each of the three pins, broadened publisher or PR-scanner permissions, and a
weakened canonical publication guard. No application or image behavior changed,
and live canonical publication remains post-merge acceptance.

## 18. Handoff Prompt for Implementation Agent

```text
Implement the plan in docs/plans/authenticated-prepare-adoption.md.

Constraints:
- Stay within the scope of the plan and issue #18.
- Do not introduce dependencies or change application/container behavior.
- Preserve v1alpha3, reservation-agent identity, permissions, and event guards.
- Update the workflow, release contract tests, and current caller docs only.
- Keep historical validation evidence tied to its original tooling revision.

Relevant files/modules:
- .github/workflows/ci.yml
- llm_agent/automation/tests/test_release_contract.py
- llm_agent/README.md
- docs/plans/container-evidence.md

Expected verification commands:
- uv sync --frozen
- uv run --frozen --no-sync pytest tests automation/tests
- workflow-scoped Ruff lint/format and compileall commands from CI
- git diff --check
```
