# AI Setup

This directory is the source of truth for repository-specific AI guidance.

Edit files under `.ai/`, then run:

```bash
bash .ai/sync.sh
```

The sync script publishes guidance, rules, skills, and review agents to tool-specific locations for common coding assistants.

## Directory layout

```text
.ai/
├── project-guidance.md
├── agents/
│   ├── performance-scalability.md
│   ├── readability-maintainability.md
│   ├── security-practices.md
│   └── system-design-scalability.md
├── skills/
│   ├── clean-architecture/
│   │   └── SKILL.md
│   ├── fastapi-service/
│   │   └── SKILL.md
│   ├── README.md
│   ├── principal-engineer-planner/
│   │   ├── SKILL.md
│   │   └── agents/openai.yaml
│   ├── programming-kb/
│   │   ├── SKILL.md
│   │   └── scripts/kb-query.sh
│   └── rest-api-design/
│       └── SKILL.md
├── meta/
│   ├── clean-architecture.yaml
│   ├── fastapi-service.yaml
│   ├── principal-engineer-planner.yaml
│   ├── programming-kb.yaml
│   ├── rest-api-design.yaml
│   └── ...
├── sync.sh
└── README.md
```

## Editing workflow

1. Update `.ai/project-guidance.md` for always-on repository guidance.
2. Add or update `.ai/skills/<name>/SKILL.md` for focused context that assistants should load on demand.
3. Keep always-on guidance short; prefer skills for detailed conventions.
4. Update `.ai/agents/*.md` for reusable read-only review subagents.
5. Keep `.ai/meta/*.yaml` in sync so generated rules and indexes have useful descriptions.
6. Run `bash .ai/sync.sh`.

## Generated outputs

The sync script currently generates content for:

- Cursor
- Roo Code
- Codex
- Claude
- Gemini
- root `AGENTS.md`

Generated files include a header noting they were produced by `.ai/sync.sh`.

## Notes

- Edit canonical files under `.ai/`, not generated outputs.
- If you add a new skill, create `.ai/skills/<name>/SKILL.md` and `.ai/meta/<name>.yaml`.
- If you add a new agent, include YAML frontmatter with at least `name`, `codexName`, `description`, and `nicknames`.

Only `.ai/` is versioned for AI guidance. Tool-specific directories and root
`AGENTS.md` are generated locally and ignored by Git. Run the sync command
after cloning or updating canonical guidance.
