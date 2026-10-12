---
name: python-control-flow
description: Use when writing, refactoring, or reviewing Python code in this repository for control flow and readability, including nesting depth, guard clauses, early returns, redundant else branches, helper extraction, complex conditions, validation ordering, mutable state, and behavior-preserving refactors.
---

# Python Control Flow

Use this skill to keep Python code readable: shallow nesting, an obvious happy
path, and explicit logic that is easy to review, test, and change. It applies to
all Python in this repo — FastAPI routes and services, domain rules, auth,
worker/run/event-log code, and MCP client orchestration.

Pair with `fastapi-service` for FastAPI conventions and `testing` when a
refactor needs test coverage first.

## Guiding Principle

Minimize cognitive complexity, not indentation, line count, or the number of
conditionals. Code should read top to bottom, make exceptional cases obvious,
and keep the main path straightforward. Flat control flow should emerge from
good decomposition and clear responsibilities, not be enforced mechanically.

Favor boring code. In production paths — especially authentication,
authorization, cancellation, and event ordering — predictable and explicit code
beats clever abstractions.

## Flat Control Flow And Guard Clauses

- Aim for 1–2 levels of nesting. Treat this as a guideline: extra nesting is
  fine when it genuinely reads better. Never add abstractions only to reduce
  indentation.
- Handle missing input, invalid state, and terminal cases first, then let the
  main path run unwrapped.
- Prefer `if not condition: raise ...` followed by the operation over wrapping
  the operation in `if condition: ... else: raise ...`.

Avoid:

```python
async def cancel_run(run: Run | None, principal: Principal) -> Run:
    if run is not None:
        if run.owner_id == principal.subject:
            if not run.is_terminal():
                return await run_store.request_cancellation(run.id)
            else:
                raise RunAlreadyFinishedError(run.id)
        else:
            raise RunAccessDeniedError(run.id)
    else:
        raise RunNotFoundError()
```

Prefer:

```python
async def cancel_run(run: Run | None, principal: Principal) -> Run:
    if run is None:
        raise RunNotFoundError()
    if run.owner_id != principal.subject:
        raise RunAccessDeniedError(run.id)
    if run.is_terminal():
        raise RunAlreadyFinishedError(run.id)
    return await run_store.request_cancellation(run.id)
```

## Redundant Else Branches

- When a branch ends in `return`, `raise`, `break`, or `continue`, do not wrap
  the remaining code in `else`. Use sequential conditions for multiple
  terminal branches.
- Keep `if`/`elif`/`else` when branches are mutually exclusive and converge on
  shared logic afterward. Do not split a clear chain into independent `if`
  statements when that changes behavior or hides exclusivity.

## Meaningful Abstractions

- Extract a helper when it separates a distinct responsibility, names a domain
  rule, or simplifies complex logic — for example `_validate_tool_call()`,
  `_is_cancellable(run)`, or `_build_mcp_headers(context)`.
- Do not extract trivial helpers that only hide a few lines, or split related
  logic so readers have to jump between functions to follow it.

## Explicit Over Clever

- Avoid nested ternaries, dense boolean expressions, unnecessary
  comprehensions, and compact one-liners when plain code is clearer.
- Extract a complex condition into a well-named predicate:
  `if is_expired_lease(claim, now): ...`.
- Simple boolean expressions are fine inline; do not turn every condition into
  a function.

## Validation Before Business Logic

- Where practical, validate inputs and invariants up front, then run the
  operation, instead of interleaving checks and side effects through nested
  conditions.
- Security-sensitive validation needs extra care. Do not use early returns or
  short-circuit evaluation that could skip checking other claims, scopes,
  audiences, or policy entries. Preserve fail-closed behavior: when in doubt,
  deny.

## Mutable State

- Return results directly instead of using flags that only feed the final
  return: `return any(scope in granted for scope in required)` over a
  `found = False` loop.
- Keep an explicit loop when it reads better, gives better diagnostics (for
  example, logging which tool call failed), or is needed to preserve
  validation and side-effect ordering.

## Maintainability Over Line Count

- A few more lines are worth it when they make edge cases explicit or
  debugging easier.
- Avoid unnecessary indirection, premature generalization, and forcing an
  idiom at the expense of straightforward control flow.

## Preserve Semantics

Readability changes must not change observable behavior unless requested.
Check:

- validation order and completeness
- exception types and messages, including API error contracts
- side effects and execution order, including emitted events and log/trace
  records
- short-circuit behavior and awaited calls
- security checks and fail-closed guarantees
- edge cases and public contracts

When proposing a refactor, call out any behavioral difference and trade-off.

## Scope Of Changes

Apply these rules to new code and to code under review. Do not refactor
unrelated code just because it violates a stylistic preference; avoid
unnecessary diffs, especially in legacy scaffold code slated for removal.

## Review Checklist

1. Is there nesting that guard clauses or early returns would flatten?
2. Are there `else` branches after terminal statements?
3. Would a complex condition read better as a named predicate?
4. Do extracted helpers represent meaningful responsibilities?
5. Is there mutable state that only controls a final return?
6. Are behavior, validation guarantees, error handling, and fail-closed
   security checks preserved?
7. Is readability favored over brevity?
8. Does every change provide a clear benefit beyond style preference?
9. Are non-obvious decisions and trade-offs explained?
