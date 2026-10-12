# Skills

Reusable task-specific skills live here.

Currently available:

- `clean-architecture`: keep API, service, domain, infrastructure, worker, event-log, and registrar boundaries clear.
- `fastapi-service`: build FastAPI service code that fits this repo's Python, Pydantic, async, and `svcs` conventions.
- `principal-engineer-planner`: plan complex engineering work before implementation and write the plan under `docs/plans/`.
- `programming-kb`: retrieve focused local programming and architecture knowledge from `/home/patex1987/Documents/programming_kb`.
- `python-control-flow`: write and review Python with flat control flow, guard clauses, explicit logic, and behavior-preserving readability refactors.
- `rest-api-design`: design consistent REST resources, HTTP methods, status codes, request/response contracts, OpenAPI docs, and API tests.
- `testing`: write behavior-focused Python tests with fake-first pytest, async, FastAPI, and `svcs` DI patterns.

For package-specific dependency-injection conventions, see `docs/patterns/svcs_notes.md`.

Expected layout:

```text
.ai/skills/<skill-name>/SKILL.md
.ai/meta/<skill-name>.yaml
```

Example metadata:

```yaml
type: skill
skillName: <skill-name>
description: "Use when ..."
```

The sync script copies skill directories into supported tool-specific locations.
