---
name: agent-inspiration
description: Use when designing or reviewing this project's LLM agent behavior using curated local inspiration from reference agent repositories, including execution lifecycle, tool calling, approvals, sandboxing, context management, skills, evaluation, and agent runtime patterns. Prefer the local inspiration index before raw repositories or internet research.
---

# Agent Inspiration

Use this skill to retrieve focused inspiration for the local Python FastAPI agent
from curated reference material.

The goal is pattern transfer, not copying. Keep the active context small and
translate findings into this project's vocabulary: `Dialogue`, `Message`, and
`AgentExecution`.

## Knowledge Surfaces

- Project policy: `docs/knowledge/agent-inspiration-sources.md`
- Local inspiration index:
  `/home/patex1987/development/gh_agent_projects/_index`
- Raw local reference sources:
  `/home/patex1987/development/gh_agent_projects`

The project knowledge document should stay source-agnostic. Source-specific
lookup belongs in the external `_index` folder and raw repos.

## Default Retrieval Workflow

1. Read `_index/tag-map.md` first.
2. Infer 2-6 likely tags from the task.
3. Search the local index with `rg` or `scripts/agent-inspiration-query.sh`.
4. Read only the matching grouped pattern page and, if needed, one or two source
   records or source files listed there.
5. Prefer reviewed `docs/knowledge/` notes over candidate index entries.
6. Treat raw repositories as evidence, not as project architecture authority.
7. Cite local files and source commits when a recommendation depends on them.

Example:

```bash
bash .ai/skills/agent-inspiration/scripts/agent-inspiration-query.sh tag tool-approval
bash .ai/skills/agent-inspiration/scripts/agent-inspiration-query.sh search "checkpoint resume approval"
```

## Tag-First Retrieval

Common tags include:

`agent-execution-lifecycle`, `execution-loop`, `dialogue-message-model`,
`event-log`, `event-streaming`, `tool-registry`, `tool-calling`,
`tool-approval`, `permission-policy`, `sandboxing`, `shell-execution`,
`filesystem-edits`, `checkpointing`, `resumability`, `cancellation`,
`idempotency`, `memory`, `context-management`, `prompt-assembly`, `retrieval`,
`subagents`, `scheduler`, `worker-queue`, `model-client`, `observability`,
`audit-log`, `security-secrets`, `testing-evals`, `mcp`, `api-sdk`,
`skill-loading`, `progressive-disclosure`, `travel-in-time`,
`reverting-tool-call`, `evaluation`, `steering`.

When unsure, run:

```bash
bash .ai/skills/agent-inspiration/scripts/agent-inspiration-query.sh tags
```

## Answer Workflow

- State that you are checking the local agent inspiration index when it
  materially affects the answer.
- Separate `local index says` from `raw source evidence says` when both are used.
- Summarize patterns in your own words.
- Include concrete applicability to this repository.
- Include cautions when an external architecture does not fit this project.
- If local knowledge has no useful match, say so before falling back.

## External Research

Default to local-only retrieval.

Use internet research only when:

- the user explicitly asks to browse, validate, refresh, compare, or research
- local knowledge is missing and current facts matter
- source metadata, licenses, repository status, or package details may have
  changed

When browsing, prefer primary sources such as official repositories,
documentation, papers, or project websites. Cite links and dates. Do not update
local source notes with external claims unless the user asks for that.

## Promotion Workflow

Promote candidate findings into `docs/knowledge/` only when they are:

- backed by source pointers and commits or external citations
- summarized without large copied code
- mapped to `Dialogue`, `Message`, and `AgentExecution`
- converted into a project task, principle, or explicit non-goal
