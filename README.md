# Project Harness — bootstrap template

A portable, agent-agnostic harness that gives any new project (SaaS, app, website,
API, bot) a strong base: identity, a measurable goal, a boot sequence, a feature
tracker, verification instruments, memory architecture, a self-improvement loop,
and an outer loop with orchestration patterns.

Works with Claude Code, Codex, Cursor — anything that reads `AGENTS.md`. The
hooks, skills and subagents are Claude Code's; other agents get the same rules
as prose in `AGENTS.md`, plus the checks inside `loop.sh`.

It comes out of my own setup: the harness I use to run my projects with
agents, distilled from what I read and tested. It's opinionated — take it,
then adapt it to your project (and delete what doesn't earn its place).

**New here? Read [GUIDE.md](GUIDE.md)** — the whole workflow on a concrete
example, driven from a chat with Claude Code.

> **Status: early.** The scripts (install, backlog, checks, hooks, `loop.sh`)
> are tested on throwaway projects. The chat workflow — `/ship`, the reviewer
> and strategist subagents — hasn't been run on a real project yet. What's
> left to validate is in [TODO.md](TODO.md). Issues and feedback welcome.

## Why

> Agent = Model + Harness. Same model, better harness → 52.8% → 66.5% on
> TerminalBench. **The harness is the product.**

Projects fail with agents not because the model is weak but because there's no
environment: no stated goal, no state, no boot sequence, no verification, no
"one thing at a time" discipline. This template is that environment.

## Bootstrap

```bash
git clone https://github.com/theolegr/harness-template ~/harness-template
~/harness-template/init-harness.sh my-project
```

`my-project` can be a new folder or an existing repo. The template is copied
into `my-project/harness/template/` (git-ignored, without the template's own `.git`).

The init copies the files (below), then **starts Claude, which interviews you**
(~10 min: project, stack + commands, goal + metric, first features, autonomy)
and fills everything in. It shows the result and commits only with your OK.

- Options: `--name "My Project"`, `--type saas|web|api|bot|cli`, `--no-interview`.
- Or copy the template into the project first and run it from there:
  `mkdir -p my-project/harness && cp -R /path/to/harness-template my-project/harness/template`,
  then `cd my-project && ./harness/template/init-harness.sh`.
- Re-run the interview any time (new goal, new features): `/harness-init` in Claude Code.
- A fresh project has no tests yet: `harness-check.sh` passes with a warning
  ("proves nothing about the code yet"). Once the first feature exists, the
  test command set by the interview makes it a real gate.
- Non-destructive — existing files are never touched; if the harness version
  differs, it is written next to yours as `<file>.harness-new` for review
  (not for your data: `GOAL.md`, `STATE.md`, `FEATURES.json`… are just kept).

### Update a project already set up

New version of the template, project already filled in — bring it up to date
without losing anything:

```bash
git -C ~/harness-template pull
~/harness-template/init-harness.sh --update my-project
```

`harness/template/` (the copy installed last time) tells your edits from the
template's. A file you never edited is replaced; a file the template didn't
change stays yours; when both changed it, the two are merged (3-way) if the
edits don't overlap, else yours is kept and the new version written next to it
as `<file>.harness-new`. A file you deleted is not re-added; new files are
added. Your data (`GOAL.md`, `STATE.md`, `FEATURES.json`, `EVAL.md`, `PLAN.md`,
`DECISIONS.md`, `DESIGN.md`, `ARTIFACTS.md`) is never touched — no merge, no `.harness-new`; the
update only says when the template's version of one changed (the new one is in
`harness/template/project/`). No interview, no commit — review with `git diff`, then commit.
`harness-status.sh` lists the `.harness-new` files until you've merged and
deleted them.

`harness/template/` is replaced on each update: don't keep notes there (a file
you added is kept, with a warning). A bug or a gap in the harness itself goes in
`harness/TEMPLATE-FEEDBACK.md` in your project — tracked by git — then upstream
as an issue or a PR.

## What you get

```
my-project/
├── AGENTS.md              ← entry point, read by every agent
├── CLAUDE.md              ← "@AGENTS.md" (Claude Code imports AGENTS.md)
├── harness/               ← committed: this project's harness
│   ├── GOAL.md  STATE.md  FEATURES.json  PLAN.md  EVAL.md  DECISIONS.md
│   ├── guide/             ← how we work (changes rarely)
│   ├── scripts/           ← status, dashboard, check, loop
│   └── template/          ← git-ignored copy of this template
├── .claude/
│   ├── settings.json          ← hooks: boot state, Bash guard, stop-on-red-check
│   ├── agents/reviewer.md     ← read-only reviewer (the checker) → findings to the backlog
│   ├── agents/strategist.md   ← read-only strategist: overview, brainstorm, new items
│   ├── skills/ship/           ← the outer loop, in the chat ("ship the next one")
│   ├── skills/design/         ← visual direction before the first screen (UI projects)
│   └── skills/harness-init/   ← the interview
└── .agents/skills/        ← project skills, any agent (linked into .claude/skills/ for Claude Code)
```

In this repo, everything that gets copied lives in [`project/`](project/).

### Project state — `harness/` (changes every session)

| File | Role |
|---|---|
| `AGENTS.md` (root) | Entry point / onboarding for agents |
| `GOAL.md` | Target + metric + constraints + the `/goal` contract |
| `STATE.md` | Current state of the world |
| `FEATURES.json` | Backlog (JSON, not MD): features `F-`, bugs `B-`, tech debt `D-` — only the work left |
| `FEATURES-DONE.json` | Archive of done/cut features (created by `feature.sh`) |
| `EVAL.md` | Instruments + blind scoring + score history |
| `PLAN.md` | Active plan (separate from execution) |
| `DECISIONS.md` | Decision log (ADR-lite), in-repo |
| `DESIGN.md` | Visual direction and the values to build UI with (brief, tokens, components, layout per size); `no UI` for a CLI or an API |
| `ARTIFACTS.md` | Links to the pages published outside the repo (design canvases, diagrams, shared mockups), current or archived |

### How we work — `harness/guide/` (changes rarely)

| File | Role |
|---|---|
| `BOOT.md` | 7-step session init + end-of-session routine |
| `SOUL.md` | Identity, voice, pushback rules, **autonomy boundaries** |
| `TESTING.md` | Test conventions + contracts + adversarial verification |
| `LOOP.md` | The outer loop, the 5 parts of any automation, monthly audit, parallel work (worktrees, fresh context, cost) |
| `MEMORY.md` | Where knowledge lives + learning from corrections (feedback → **principle**, not rule) |
| `SKILLS.md` | External skills the agent may suggest (augment, never replace the harness) + excluded tools |

### Executable — `harness/scripts/`

| File | Role |
|---|---|
| `harness-status.sh` | **Show** state, don't describe it |
| `dashboard.py` | The same state as one HTML page (`harness/dashboard.html`, git-ignored): progress, next item, milestones, the backlog as one ordered list (details fold out; a blocked item shows the numbered open question it waits on), metric and score trend, state and open questions, decisions, commits. Rewritten at the end of each Claude turn once it exists; an open tab reloads itself. `--open`, `--watch`. A view — writes nothing else |
| `state.py` | The state as JSON — what `harness-status.sh` and `dashboard.py` read; agents can too |
| `harness-check.sh` | The verification instrument (exit code); `TEST_CMD` / `LINT_CMD` at the top |
| `loop.sh` | Outer loop engine with enforced maker/checker split |
| `link-skills.sh` | Links each `.agents/skills/<name>` into `.claude/skills/` (the only place Claude Code loads skills from); run at session start |
| `feature.sh` | `add` a feature / bug / debt item; change a status — `done` / `cut` archives it to `FEATURES-DONE.json`; `blocked "<reason>"` keeps the reason apart; notes are appended, never replaced |
| `hooks/other-sessions.py` | SessionStart hook: warns when another agent session is active in the same folder (→ work in a worktree); SessionEnd (`end`): records the session as ended |
| `hooks/stop-check.sh` | Stop hook: the agent can't end a turn on a red `harness-check` (checks the session's own worktree) |
| `hooks/guard-bash.py` | PreToolUse hook: refuses force-push / `rm -rf` / `reset --hard`, asks before migrations & deploys |

## The 5 principles, mechanically enforced

1. **Context beats instructions** — `harness-status.sh` shows real state.
2. **Planning ≠ execution** — `loop.sh` phases `[1/5]` → `[2/5]`, hard gate.
3. **Feedback loops non-negotiable** — `harness-check.sh` exit code + `EVAL.md`; the Stop hook
   won't let the agent finish on a red check.
4. **One thing at a time** — `FEATURES.json` + `loop.sh` pick exactly one item.
5. **The codebase IS the documentation** — decisions live in the repo.

## Agents and skills (Claude Code)

| | Role | Writes code? |
|---|---|---|
| `ship` skill | The outer loop in the chat: pick one item → plan (you OK it) → build → reviewer → record | yes (the main agent) |
| `reviewer` agent | PASS/FAIL against the acceptance criterion; non-blocking `FINDING:` lines become `bug` / `debt` items | no — read-only |
| `strategist` agent | Overview, questions, brainstorm; proposes new items tied to the goal, flags items to cut | no — read-only |
| `harness-init` skill | The interview (init, or re-run to change goal / stack / features) | harness files only |
| `design` skill | UI projects, before the first screen: a design interview (audience, feel, references — inspiration or copy? —, platforms and sizes, copy language), 2–3 mockup directions, iterations, then `DESIGN.md` | mockups and harness files only |

Why only two agents: an agent earns its place when it changes the **tools**
(read-only), the **context** (fresh, no author bias) or the **model**. A
"planner" or "UI expert" persona is just a prompt — that knowledge goes in a
skill or in `AGENTS.md`. That's why design is a skill: it has to ask the user
questions and show mockups in the chat, which a subagent can't; the design
check at build time is a section of the `reviewer`. Both agents are pinned to the strongest model
(`model: opus`): see *Model routing* in `harness/GOAL.md`.

## The two loops

- **Inner loop** (agent): read → code → test → fix. Fast, automated.
- **Outer loop**: discover → plan → execute → verify → record → measure. In a
  chat, the `ship` skill runs it with you at the plan gate; unattended, `loop.sh` does.
  Verification is `harness-check.sh` **plus a separate reviewer agent**
  (`VERIFIER_CMD`, maker ≠ checker; the `reviewer` agent has no write tools, and the
  loop fails the review if the working tree changed) — self-evaluation doesn't work; models grade
  their own work ~10–25% higher. A failed item is marked `blocked` and the loop
  stops; it never retries on top of broken code.

Plus a third: the **self-improvement loop** (`MEMORY.md`) that observes
corrections and patches the process itself.

## Hooks — the rules the agent can't skip (Claude Code)

A hook is a script Claude Code runs by itself at a given moment. The agent
doesn't choose to run it, so it can't forget or bypass it. These are wired in
`.claude/settings.json`:

| When | Script | Effect |
|---|---|---|
| Session start | `link-skills.sh`, `harness-status.sh` | Project skills are linked for Claude Code; goal, current feature and git state are injected into the agent's context (the BOOT happens by itself) |
| Session start | `hooks/other-sessions.py` | Another session wrote from this folder in the last 15 min and hasn't ended → a warning: the late one works in its own worktree (`AGENTS.md` §5) |
| Session end | `hooks/other-sessions.py end` | Records the session as ended (`harness/.sessions-ended`, git-ignored), so the next one doesn't take it for parallel work |
| Before each Bash command | `hooks/guard-bash.py` | **Refuses** force-push, `reset --hard`, `clean -f`, `branch -D`, `rm -rf` (except build/cache dirs); **asks** before migrations, `DROP`/`TRUNCATE`, deploys |
| When the agent wants to stop | `hooks/stop-check.sh` | Runs `harness-check.sh` in the session's checkout if files changed; if red, the agent gets the error and must keep working (blocks once in a row at most) |
| When the agent wants to stop | `dashboard.py` | Rewrites `harness/dashboard.html` if you've generated it once (never blocks) |

- **Adapt the guard**: edit `SAFE_RM` and `ASK` at the top of `guard-bash.py`.
  In a non-interactive run (`claude -p`, `loop.sh`), "ask" means refused — on purpose.
- **Turn off**: the Stop check with `HARNESS_STOP_CHECK=0`; any hook with `/hooks`
  in Claude Code, or by removing its entry from `.claude/settings.json`.
- **Let the agent run your commands**: add them to `permissions.allow` in
  `.claude/settings.json` (the interview adds install/test/lint/dev).
- Other agents (Codex, Cursor…) don't run these hooks: for them the rules stay
  prose in `AGENTS.md`, plus the checks inside `loop.sh`.

## Build to delete

Every file here encodes an assumption about what the model *can't* do. As models
improve, those assumptions expire. **Test by turning components off.** If quality
doesn't change, delete the component. A harness that only ever grows becomes
overhead. See `EVAL.md` → "future-proofing test".

## Credits

Distilled from about 25 articles and threads on agent harnesses. The ideas
that shaped it, and where they come from:

- **Sai Rahul** — harness engineering: the 5 artifacts, the 5 principles, build to delete
- **Akshay Pachaar** — the anatomy of an agent harness (12 components)
- **Addy Osmani** — loop engineering: the loop primitives
- **Elvis Sun** — goals as loss functions, blinded evals
- **Thariq** — dynamic workflows in Claude Code, why the default harness breaks
- **0xcodez**, **argona0x** — graph engineering: nodes, edges, Amdahl's law
- **Warp** / **Buzz** — agent feedback loops: principles over rules, skills as code
- **Tony Simons** — SOUL.md: identity and autonomy boundaries
- Pieces on memory engineering, self-improving skills, revenue loops (the
  5-part automation, the loop audit), `/goal` + `/loop` — and, as
  counterpoints, on minimalism ("world-class agentic engineer", "stop building
  Foxconn factories").

## License

[MIT](LICENSE).
