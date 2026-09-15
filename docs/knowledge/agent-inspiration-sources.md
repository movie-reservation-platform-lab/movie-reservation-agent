# Agent Inspiration Sources

Last reviewed: 2026-06-16

Use this document to define how agent inspiration sources are admitted into the
project knowledge base. The goal is not to copy another project into this
repository. The goal is to extract durable patterns, constraints, and tasks that
fit this Python FastAPI agent backend.

This file intentionally does not name specific reference projects. The active
lookup surface is decoupled from this repo and lives in the local inspiration
index under `/home/patex1987/development/gh_agent_projects/_index`.

## Intake Rules

- Keep one short source card per repository, article, paper, or book.
- Link to the original source and record the license when relevant.
- Summarize ideas in your own words.
- For books, store notes, page references, and short paraphrases. Do not copy long excerpts into the repo.
- Translate each useful idea into an explicit project task or a deliberate non-goal.
- Prefer high-signal notes over large pasted docs.
- Keep source-specific candidate notes outside this repo until they are reviewed.
- Promote only stable conclusions into `docs/knowledge/`.

## Knowledge Layers

Use three layers:

1. Raw sources live outside this repository.
2. The local inspiration index stores candidate tags, source records, and source pointers.
3. `docs/knowledge/` stores reviewed conclusions that should influence this project.

The local index may name specific sources. Project knowledge should prefer
pattern names and implementation lessons over source branding.

## Reviewed Source Card Template

```md
## <Reviewed Source Or Pattern>

- Type:
- Source reference:
- Why it matters:
- Patterns worth borrowing:
- Not relevant / do not copy:
- Concrete tasks suggested:
- Open questions:
```

## Promotion Criteria

A candidate pattern can be promoted into `docs/knowledge/` when it is:

- backed by a local source pointer and commit or an external citation
- summarized in our own words
- mapped to this repository's vocabulary: `Dialogue`, `Message`, `AgentExecution`
- relevant to the current roadmap
- clear about what not to copy

## Current Pattern Interests

- Agent execution lifecycle, event logs, and progress streaming.
- Tool calls, approvals, permission policy, and reversible operations.
- Context management, prompt assembly, retrieval, and skill loading.
- Sandbox boundaries, secret handling, audit logs, and observability.
- Worker queues, scheduling, model clients, evals, and regression testing.
