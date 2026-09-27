# .agents/skills/ — project skills

> Skills are the project explained **once**. Without them, the agent re-derives
> the project on every run (**intent debt**). With them, knowledge compounds.
>
> A skill = `SKILL.md` (instructions + metadata) + optional `scripts/`, `references/`,
> `templates/` — the open Agent Skills format (the one Claude Code and Codex use).

## When to create a skill

Create one when you've done the same non-obvious thing **twice**:
- A deploy procedure with gotchas
- A data migration pattern
- A testing setup for a specific subsystem
- A domain rule the agent keeps getting wrong

## Where skills live

```
.agents/skills/<skill-name>/SKILL.md
```

`.agents/skills/` is the home of project skills, whatever the agent: Codex and
other agents read it directly. **Claude Code only loads skills from
`.claude/skills/`**, so `harness/scripts/link-skills.sh` links each skill there
(`.claude/skills/<name>` → `../../.agents/skills/<name>`). It runs at every
Claude Code session start; after creating a skill mid-session, run it once.
One source, no copies to keep in sync. (On Windows without symlink support in
git, copy the folder into `.claude/skills/` instead.)

The harness's own workflows (`harness-init`, `ship`) live directly in
`.claude/skills/`: they drive Claude Code features (subagents, questions to
the user).

## Format

```md
---
name: <skill-name>
description: <when to use this — be specific, this is the trigger>
---

# <Title>

## When to use
<trigger conditions>

## Steps
1. <exact command / action>
2. ...

## Pitfalls
- <thing that broke before>

## Verification
<how to confirm it worked>
```

## Invocation

- Explicit: `/<skill-name>` (Claude Code), `$<skill-name>` (Codex)
- Implicit: matched automatically from the description

## Maintenance

Skills rot. When one is wrong or incomplete, **fix it immediately** — a stale
skill is worse than no skill because it's trusted. Prune aggressively:
`Build to delete` — if a skill adds no measurable quality, remove it.
