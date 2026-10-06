# SKILLS.md — external skills that augment the harness

> A short library of well-known, open skills and tools on GitHub. The agent
> **suggests** one when the project actually needs it, and says why. It never
> suggests a skill just because it exists, and never installs one without an OK.
>
> Install commands checked on **2026-09-25** (Expo, React Native Testing and `--agent universal`: **2026-09-29**). These tools move fast: before
> installing, read the repo README and use its current command if it differs.

## The rule: augment, never replace

The harness owns the goal, state, feature list, plan and verification
(`harness/GOAL.md`, `STATE.md`, `FEATURES.json`, `PLAN.md`, `EVAL.md`,
`scripts/loop.sh`). A skill is in scope only if it brings something the harness
doesn't: domain know-how (a stack, a test tool, security, documents) or a
technique used *inside* a feature (TDD, debugging, UI design).

If an installed skill also plans or tracks work, the harness wins: plans go to
`harness/PLAN.md`, features to `harness/FEATURES.json`, state to `harness/STATE.md`.

## When to suggest

Check the **Suggest when** column at these moments:

1. **Init**: during the `harness-init` interview, once the type, stack and
   features are known.
2. **Starting a feature**: at step 7 of `harness/guide/BOOT.md`, before writing the plan.
3. **In a discussion**: when the user brings up a need a skill covers
   (e.g. "we need E2E tests", "let's add payments", "security review before launch").

How to suggest:
- Only a real fit, **at most 2 at a time**. Saying nothing is the normal case.
- One line each: name, repo, *why this project needs it now*.
- Skip what's already installed (`.claude/skills/`, `.agents/skills/`,
  `claude plugin list`, `claude mcp list`).
- Skip what was declined in `harness/DECISIONS.md`, unless the context has
  clearly changed. Then say what changed.

If accepted:
1. Show the exact command, then run it. It fetches code from GitHub.
   Slash commands (`/plugin …`) can't run from a shell: give them to the user.
   For `npx skills add`, pass `--agent universal`: the skill lands in
   `.agents/skills/`, the home of project skills, and `link-skills.sh` links it
   for Claude Code. With `--agent claude-code` it lands in `.claude/skills/`
   only, where other agents don't look.
2. Log it in `harness/DECISIONS.md`: skill, repo, why, date.
   **Log declined suggestions too**, so they aren't suggested again.

Not in the list? `npx skills find <query>` searches the open directory
(skills.sh). Suggest a result only if it's widely used, and show its repo.

## The library

### Stack

| Skill | Repo | Suggest when | Install |
|---|---|---|---|
| Supabase + Postgres best practices | [supabase/agent-skills](https://github.com/supabase/agent-skills) | Supabase in the stack, or Postgres anywhere | `npx skills add supabase/agent-skills --agent universal` |
| React / Next.js / React Native, web design guidelines, Vercel deploy | [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) | React or Next.js web frontend, or hosting on Vercel. For an Expo app, prefer expo/skills: the React Native part here is one generic page, and the default install adds 8 web/Vercel skills | `npx skills add vercel-labs/agent-skills --agent universal` |
| Expo, official: project structure, Expo Router, design tokens, animation, EAS releases | [expo/skills](https://github.com/expo/skills) | Expo or React Native mobile app | `claude plugin install expo@claude-plugins-official --scope project` |
| modern-python (uv, ruff, pytest) | [trailofbits/skills](https://github.com/trailofbits/skills) | Python project | `/plugin marketplace add trailofbits/skills` then install `modern-python` |

### Testing & verification (feeds `harness/EVAL.md` and `harness-check.sh`)

| Skill | Repo | Suggest when | Install |
|---|---|---|---|
| Playwright | [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp) | Web UI whose acceptance criteria are checked in a browser. The README now recommends its CLI + skills over the MCP for coding agents: check it first | `claude mcp add playwright npx @playwright/mcp@latest` |
| webapp-testing | [anthropics/skills](https://github.com/anthropics/skills) (example-skills) | Web app with no E2E setup yet, lighter than a full Playwright suite | `/plugin marketplace add anthropics/skills` then `/plugin install example-skills@anthropic-agent-skills` |
| mutation-testing | [trailofbits/skills](https://github.com/trailofbits/skills) | Tests pass but you doubt they catch anything (useful for the maker ≠ checker loop) | `/plugin marketplace add trailofbits/skills` then install `mutation-testing` |
| react-native-testing (React Native Testing Library) | [callstack/react-native-testing-library](https://github.com/callstack/react-native-testing-library) | React Native component tests with Jest | `npx skills add callstack/react-native-testing-library --skill react-native-testing --agent universal` |

### Security

| Skill | Repo | Suggest when | Install |
|---|---|---|---|
| static-analysis, supply-chain-risk-auditor, building-secure-contracts… | [trailofbits/skills](https://github.com/trailofbits/skills) | Handles money, auth, personal data, smart contracts, or a pre-launch audit | `/plugin marketplace add trailofbits/skills` then install the relevant plugins |

### Development techniques (used inside one feature)

| Skill | Repo | Suggest when | Install |
|---|---|---|---|
| Superpowers: brainstorming, test-driven-development, systematic debugging, code review | [obra/superpowers](https://github.com/obra/superpowers) | A feature needs TDD discipline, or the agent keeps failing at debugging. **Overlap**: its planning/execution skills (writing-plans, subagent-driven-development) duplicate `PLAN.md` and `loop.sh`. Use the techniques; plans still go to `harness/PLAN.md` | `/plugin install superpowers@claude-plugins-official` |
| frontend-design | [anthropics/skills](https://github.com/anthropics/skills) (example-skills) | Feature with user-facing UI where look and feel matter. Complements the harness's `design` skill: `design` sets the direction and `DESIGN.md`, this one helps build screens that match it | same as webapp-testing |

### Domain

| Skill | Repo | Suggest when | Install |
|---|---|---|---|
| docx / pdf / pptx / xlsx | [anthropics/skills](https://github.com/anthropics/skills) (document-skills) | The product reads or generates office documents or PDFs | `/plugin install document-skills@anthropic-agent-skills` |
| mcp-builder | [anthropics/skills](https://github.com/anthropics/skills) (example-skills) | The project is, or exposes, an MCP server | same as webapp-testing |

### Growing the harness itself

| Skill | Repo | Suggest when | Install |
|---|---|---|---|
| skill-creator | [anthropics/skills](https://github.com/anthropics/skills) (example-skills) | The same non-obvious procedure was done twice and should become a project skill in `.agents/skills/` (see `MEMORY.md`) | same as webapp-testing |
| skills CLI | [vercel-labs/skills](https://github.com/vercel-labs/skills) | Needed to install `npx skills add …` entries; also searches skills.sh | nothing to install: runs through `npx` |

## Excluded: they replace the harness

Never suggest these. Each one brings its own goal/spec/plan/state workflow that
competes with `GOAL.md`, `FEATURES.json`, `PLAN.md`, `STATE.md` and `loop.sh`.
Good sources of ideas for improving the harness, not add-ons.

| Tool | Repo | What it would replace |
|---|---|---|
| Spec Kit | [github/spec-kit](https://github.com/github/spec-kit) | Goal/constitution, specs, plan, tasks |
| OpenSpec | [Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec) | Change proposals → plan + tasks |
| cc-sdd | [gotalab/cc-sdd](https://github.com/gotalab/cc-sdd) | Specs → plan → autonomous implementation loop |
| BMad Method | [bmad-code-org/BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) | The whole planning and delivery process |
| GSD (Get Shit Done) | [open-gsd/gsd-core](https://github.com/open-gsd/gsd-core) | STATE.md, phase loop, subagent orchestration |
| Task Master | [eyaltoledano/claude-task-master](https://github.com/eyaltoledano/claude-task-master) | FEATURES.json (PRD → task graph) |

## Maintaining this file

Add a skill only if it's widely used, maintained, and passes the augment rule.
Remove one when its repo is archived or it stops adding value (*build to
delete*). Update the "checked on" date when you re-verify install commands.
