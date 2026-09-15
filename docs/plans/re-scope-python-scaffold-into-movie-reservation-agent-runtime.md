# Implementation Plan: Re-scope Python Scaffold Into Movie Reservation Agent Runtime

> Status update (2026-09-15): the deterministic demo composition and opt-in audit
> endpoint are implemented. This document preserves the earlier re-scope design;
> see `llm_agent/README.md` for current runnable behavior and
> `docs/plans/container-evidence.md` for image/evidence work.


Issue: https://github.com/movie-reservation-platform-lab/movie-reservation-agent/issues/1

Branch: `issue-1-rescope-agent-runtime`

Last reviewed: 2026-08-04

## 1. Summary

Update repository documentation and AI guidance so this repository is clearly
described as `movie-reservation-agent`, the Python runtime that coordinates
browser/platform requests with MCP-backed recommendation and reservation
services. This slice is documentation-only and intentionally avoids porting
product behavior from the proven demo.

## 2. Goals

- Describe the repository as the movie reservation agent runtime.
- Mark current scaffold code as reusable, legacy/delete-later, or deferred.
- Define the intended browser/platform API and execution runtime boundary.
- Clarify local development commands and test strategy.
- Leave a clear follow-up path for stabilizing the proven demo behavior.

## 3. Non-goals

- No new FastAPI route behavior.
- No MCP client implementation.
- No LLM/model integration.
- No database migrations.
- No removal of legacy throttle/game/navigation code in this issue.
- No deployment or CI changes.

## 4. Current State

Relevant evidence:

- Root `README.md` and `DEVELOPMENT.md` still described the old throttle
  sequencer scaffold.
- `llm_agent/README.md` was generic service guidance.
- `.ai/project-guidance.md` already warned that old throttle/game/navigation
  code exists as legacy example code.
- `llm_agent/llm_agent/app.py` registers health, throttle, and agent routes.
- `llm_agent/llm_agent/api/http/v1/routes/agent.py` exposes current run
  scaffolding: create, get, cancel, and event listing.
- `llm_agent/llm_agent/api/http/v1/routes/throttle_steps_calculator.py` exposes
  legacy throttle behavior.
- `llm_agent/agent_run_worker/`, `llm_agent/contracts/`, and
  `llm_agent/local_runtime/` contain reusable in-memory run/worker/event-log
  patterns.
- Platform context at
  `/home/patex1987/development/movie-reservation-platform-lab/PLATFORM_CONTEXT.md`
  identifies `movie-reservation-agent` as the Python agent repository and cites
  the proven local flow:
  `browser -> Python agent -> recommendation MCP -> Rust recommendation API`
  and `reservation MCP -> NestJS reservation API`.
- Original agent reference is available at
  `/home/patex1987/development/python-agent-with-idp`, with the proven demo
  branch `demo-multi-service-observability` at commit `73441fc`.

## 5. Requirements and Assumptions

### Confirmed Requirements

- Repository docs clearly describe this as `movie-reservation-agent`.
- Legacy scaffold areas are marked as reuse, delete, or defer.
- Agent runtime responsibilities and non-goals are explicit.
- A follow-up implementation issue can stabilize the proven demo behavior.
- Broad product behavior is not implemented in this repo-guidance slice.

### Assumptions

- The current public run routes remain as scaffold references until a follow-up
  issue replaces or reshapes the browser/platform contract.
- The throttle route remains temporarily to avoid mixing documentation scope
  with behavior removal.
- The platform context file remains at the workspace parent, not in this repo.
- `.ai/project-guidance.md` is the canonical source for generated `AGENTS.md`.

### Open Questions

- Should the final browser contract be task-based, dialogue/message-based, or
  both?
- Should MCPs run as independent ECS services or initial sidecars?
- Which proven demo code should be adopted first: route contract, MCP client
  adapters, trace propagation, or fakeable worker flow?

## 6. Proposed Design

Use a documentation-first re-scope:

- Replace stale scaffold README/development copy with movie reservation agent
  runtime guidance.
- Add a durable architecture note for the runtime ownership boundary.
- Keep the current route inventory honest by labeling run APIs as scaffold and
  throttle APIs as legacy.
- Update canonical AI guidance and regenerate `AGENTS.md`.
- Keep all runtime code untouched.

This is preferred because issue #1 is a repo-guidance slice. It prepares the
next implementation issue without changing behavior under an unclear contract.

## 7. Alternatives Considered

### Alternative A: Documentation-only re-scope

- Pros: Low risk, matches acceptance criteria, creates shared vocabulary before
  implementation.
- Cons: Leaves stale runtime code in place temporarily.
- Decision: Recommended.

### Alternative B: Re-scope docs and delete legacy code

- Pros: Removes confusion immediately.
- Cons: Higher risk because throttle/game dependencies may still be wired into
  DI and tests; exceeds issue scope.
- Decision: Reject for this issue. Track deletion as a follow-up.

### Alternative C: Port proven demo behavior now

- Pros: Moves product functionality forward quickly.
- Cons: Mixes documentation, API design, MCP integration, observability, and
  behavior changes in one slice.
- Decision: Reject for this issue. Use a follow-up implementation issue.

## 8. API / Interface Changes

No runtime API changes.

Documentation now distinguishes:

- Current scaffold run API under `/api/v1/agent/runs`.
- Legacy throttle API under `/api/v1/throttle/calculate_throttle_steps`.
- Target browser/platform boundary as future product-level agent task or
  conversation resources.

## 9. Data Model / Persistence Changes

None.

## 10. Security, Privacy, and Abuse Considerations

- Keep OIDC/JWT authentication infrastructure marked reusable and
  security-sensitive.
- Do not log raw tokens, credentials, full prompts, or unnecessarily detailed
  reservation payloads.
- Future MCP integrations must validate caller authorization and preserve
  trace/correlation context without leaking secrets.
- Public APIs should not expose internal execution event details by accident.

## 11. Performance, Scalability, and Reliability Considerations

- Documentation preserves the control-plane/data-plane split so long-running
  agent work does not block request handlers.
- Current in-memory runtime is acceptable for local scaffolding only.
- Durable worker, queue, event-log, retry, cancellation, and projection behavior
  must be designed before production-like AWS demo use.

## 12. Implementation Steps

1. Replace stale root README
   - Change: Describe runtime role, current status, reuse/delete/defer map,
     API boundary, local commands, and test strategy.
   - Files/modules likely affected: `README.md`.
   - Notes: Keep behavior inventory honest.
   - Verification: Read rendered Markdown and check links/paths.

2. Replace stale development guide
   - Change: Rename scaffold concepts to movie reservation agent concepts and
     document current commands.
   - Files/modules likely affected: `DEVELOPMENT.md`, `llm_agent/README.md`.
   - Notes: Keep legacy Keycloak realm name explicit.
   - Verification: Read command blocks and route inventory.

3. Add durable runtime boundary note
   - Change: Document ownership, current scaffold, API/runtime boundary, and MCP
     integration direction.
   - Files/modules likely affected:
     `docs/architecture/movie-reservation-agent-runtime.md`, `docs/README.md`.
   - Notes: Reference original agent demo as baseline only.
   - Verification: Check docs index includes the note.

4. Update AI guidance
   - Change: Update canonical `.ai/project-guidance.md` and regenerate
     generated `AGENTS.md`.
   - Files/modules likely affected: `.ai/project-guidance.md`, `AGENTS.md`.
   - Notes: Do not hand-edit generated guidance only.
   - Verification: Run `.ai/sync.sh` and inspect generated diff.

5. Verify documentation-only scope
   - Change: Review diff for unintended runtime edits.
   - Files/modules likely affected: docs and guidance only.
   - Notes: Runtime tests are optional because no behavior changes.
   - Verification: `git diff --check`; optional Markdown text search for stale
     scaffold claims.

## 13. Testing Strategy

- Run `git diff --check` for whitespace/patch hygiene.
- Use `rg` to check remaining stale throttle/scaffold references and ensure they
  are intentionally labeled legacy where touched.
- Runtime test execution is not required for documentation-only changes.

## 14. Rollout / Migration Plan

No runtime rollout. Merge as a documentation PR. Follow-up issues can then:

- Adopt the proven demo behavior.
- Replace or reshape `/api/v1/agent/runs`.
- Add MCP adapters and fake-client tests.
- Remove legacy throttle/game/navigation packages.

## 15. Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|---|---:|---:|---|
| Docs describe target behavior as already implemented | Medium | Medium | Separate current state from target state in each doc. |
| Legacy route remains confusing | Medium | High | Label it legacy and add deletion follow-up. |
| Original demo is copied blindly later | High | Medium | Document it as reference/recovery baseline only. |
| Generated AI guidance drifts from canonical `.ai` source | Medium | Low | Edit `.ai/project-guidance.md` and run `.ai/sync.sh`. |

## 16. Done Criteria

- `README.md` describes `movie-reservation-agent`.
- `DEVELOPMENT.md` and `llm_agent/README.md` define local commands and test
  strategy for this repo.
- Legacy scaffold areas are marked as reuse, delete later, or defer.
- Runtime responsibilities and non-goals are explicit.
- A follow-up implementation issue can start from the documented proven demo
  baseline.
- Generated `AGENTS.md` matches canonical `.ai/project-guidance.md`.
