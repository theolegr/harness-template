# IDEAS — improvement backlog, decisions open

Ideas for the template itself, not for a project using it. Nothing here is
decided: each item states the problem, the options on the table, and what is
still open. When an item is decided, record the choice (and why) in the item,
then move it to *Decided* at the bottom — or delete it if it's dropped.

[TODO.md](TODO.md) comes first: most of these should wait for the real-world
test, which will show what the agent actually uses.

| ID | Idea | Size | Status |
|---|---|---|---|
| I-01 | Project dashboard | M | open |
| I-02 | Safe git when several sessions share a checkout | S | open |
| I-03 | Git `pre-commit` hook running `harness-check.sh` | S | open |
| I-04 | Enforce protected paths (blind eval, `harness/template/`) | S | open |
| I-05 | Reviewer: don't trust the maker's claims | XS | open |
| I-06 | Handoff instead of compaction | S | open |
| I-07 | Simplification pass after a feature | S | open |
| I-08 | Concrete conversation rules in `SOUL.md` | XS | open |
| I-09 | Supply-chain defaults for JS projects | S | open |
| I-10 | Sandbox for unattended `loop.sh` | M | open |
| I-11 | `harness-init` only on explicit request | XS | open |
| I-12 | Slim the doctrine | M | open — after the test |
| I-13 | Support pi as an agent | S | open |

Sources: own ideas, and a comparison with [pi](https://github.com/earendil-works/pi)
(commit `69f0be6`, 2026-10-02) — see *Context* at the end.

---

## I-01 — Project dashboard

**Why.** `harness-status.sh` prints the state in a terminal. A page would show it
at a glance and let you share it: goal and metric trend, backlog by status,
milestone progress, health, last check, recent commits.

**Options**
- **A. Static HTML, generated.** A `harness/scripts/state.py --json` parses
  `FEATURES.json`, `FEATURES-DONE.json`, `STATE.md`, the score history in
  `EVAL.md`, `git log` and `.check.ok` into one JSON; `harness-status.sh` and a
  `dashboard.sh` (→ git-ignored `harness/dashboard.html`) both read it. Stdlib
  only, works with any agent. Read-only: it shows state, never writes it.
  *Leaning.*
- **B. claude.ai artifact.** Live, shareable, nicer — but Claude-only and
  outside the repo.
- **C. Terminal UI** (or `watch harness-status.sh`). No browser, but more code
  to maintain for little more than today.
- **D. Nothing.** `harness-status.sh` is enough.

**Open**
- `STATE.md` *Health* / *Phase* are free text. Freeze the `**Health**: 🟢` line
  format, or move the *Now* fields to JSON?
- Which panels earn their place? Decide from what the real-world test actually
  fills in — a dashboard over empty fields is noise.

## I-02 — Safe git when several sessions share a checkout

**Why.** Two agents in the same directory: `git add -A` commits the other
session's half-done work. [BOOT.md:59](project/harness/guide/BOOT.md#L59) and
[loop.sh:63](project/harness/scripts/loop.sh#L63) use it, and
[guard-bash.py](project/harness/scripts/hooks/guard-bash.py) doesn't stop
`git stash`, `git add -A` / `.` or `git commit --no-verify`. pi's `AGENTS.md`:
"only commit files YOU changed, stage explicit paths".

**Options**
- **A. Rule + guard.** Rule in `AGENTS.md` §5; guard denies `stash`,
  `add -A`/`.`, `--no-verify`. *Leaning.*
- **B. Rule only.** Prose, no enforcement.
- **C. Worktrees only.** Parallel work always in its own worktree
  (`LOOP.md` already says so); keep `add -A`.

**Open**
- `loop.sh` works on its own branch — is `add -A` there acceptable, or does it
  also need explicit paths?
- Is denying `git stash` too strict for a solo, single-session user?

## I-03 — Git `pre-commit` hook running `harness-check.sh`

**Why.** Today the "can't finish on a red check" rule exists only for Claude
(Stop hook) and `loop.sh`. A git hook enforces it for Codex, Cursor and humans
too — what "agent-agnostic" promises. pi runs `npm run check` in pre-commit.

**Options**
- **A. Versioned hooks dir.** `harness/scripts/git-hooks/pre-commit` +
  `git config core.hooksPath` set by `init-harness.sh`. *Leaning.*
- **B. Copy into `.git/hooks/`** at init. Simple, but not versioned.
- **C. husky / pre-commit framework.** A dependency for a one-line hook.
- **D. Keep it Claude-only.**

**Open**
- A slow check on every commit: allow a fast mode (lint only) in the hook?
- Running twice with the Stop hook — skip in the hook when `.check.ok` is fresh?

## I-04 — Enforce protected paths

**Why.** `EVAL.md` says the agent that writes the code must not see the eval's
answer key; `AGENTS.md` says never read `harness/template/`. Nothing enforces
either.

**Options**
- **A. `permissions.deny` in `.claude/settings.json`** (`Read(harness/template/**)`,
  answer-key paths). No code. *Leaning for Claude.*
- **B. PreToolUse hook on Read/Edit/Write** with a list in a file — more
  flexible (messages, exceptions), more code.
- **C. Prose only**, as today.

**Open**
- Where do answer keys live by convention? (`harness/eval/private/`?)
- Other agents can't be enforced this way — only a sandbox (I-10) would.

## I-05 — Reviewer: don't trust the maker's claims

**Why.** pi's issue prompt: "do not trust analysis written in the issue;
verify independently." [reviewer.md](project/.claude/agents/reviewer.md) doesn't
say that the maker's summary is a claim to check, not a fact.

**Options**
- **A. One line in `reviewer.md`.** *Leaning.*
- **B. Don't pass the maker's summary to the reviewer at all** — only the diff
  and the acceptance criterion.

**Open** — B is stricter; does the reviewer lose useful context?

## I-06 — Handoff instead of compaction

**Why.** Compaction loses context unpredictably. pi's `handoff` extension writes
a focused prompt (decisions, files, next task) to start a fresh session.

**Options**
- **A. Last step of `/ship`:** after recording, draft the next session's prompt
  from `STATE.md` + the next item.
- **B. Standalone `/handoff` skill**, usable mid-task.
- **C. Nothing** — `STATE.md`'s session log + `BOOT.md` already do this.

**Open** — does the boot sequence already make this redundant? The real-world
test will tell.

## I-07 — Simplification pass after a feature

**Why.** Agents add wrappers, flags and defensive branches. pi's `/deslop`
simplifies a finished change, but **asks before any significant removal**
(behaviour, public API, validation, anything tested or documented).

**Options**
- **A. Skill** adapted from `/deslop`, run on demand or as a `/ship` step.
- **B. Reviewer section** that emits `FINDING:` lines → `debt` items.
- **C. Point to Claude Code's `/simplify`** in `SKILLS.md`, plus the approval
  rule in `AGENTS.md`.

**Open** — inside `/ship` (slower, every feature) or on demand?

## I-08 — Concrete conversation rules in `SOUL.md`

**Why.** pi's rules are concrete where principles are vague: "answer the
question before editing"; "on feedback, say whether you agree before saying
what you changed"; "explain as problem → example → solution".

**Options** — **A.** add 2–3 such lines to `SOUL.md`; **B.** leave as is.

## I-09 — Supply-chain defaults for JS projects

**Why.** pi pins direct deps, delays fresh releases (`min-release-age=2`),
installs with `--ignore-scripts`, and treats lockfile changes as reviewed code.

**Options**
- **A. By project type at init:** ship an `.npmrc` (`save-exact=true`,
  `min-release-age=2`) for `saas|web|api` on Node.
- **B. A rule in `AGENTS.md` / `TESTING.md`**, no files.
- **C. Nothing** — out of scope for a harness.

**Open** — Python equivalent (`uv` lock, pinned versions)?

## I-10 — Sandbox for unattended `loop.sh`

**Why.** `loop.sh` runs unattended with `acceptEdits`. The guard hook catches
known-bad commands, not everything. pi has no permissions at all and documents
containers instead (Docker, micro-VM, policy sandbox).

**Options**
- **A. `loop.sh --sandbox`** running the agent in a container.
- **B. A devcontainer** shipped with the template.
- **C. Claude Code's own sandbox settings** — check what they cover.
- **D. Document only** (a section in `LOOP.md`).

**Open** — weight vs. benefit for a solo project; Docker as a requirement?

## I-11 — `harness-init` only on explicit request

**Why.** The interview rewrites harness files; it should never start because a
message looked like a match. `disable-model-invocation: true` in the skill's
frontmatter (Claude Code and pi both support it).

**Options** — **A.** add it; **B.** keep auto-invocation.

## I-12 — Slim the doctrine

**Why.** pi's `AGENTS.md` is ~110 lines, all concrete and imperative. Ours:
~1,200 lines across `AGENTS.md`, guides, skills and agents, with some doctrine
prose. More context read every session; our own *Build to Delete* argues for
less.

**Options**
- **A. Cut by evidence:** after the real-world test, delete what the agent
  never needed.
- **B. Merge guides** (e.g. `MEMORY.md` + `SKILLS.md` into `AGENTS.md`).
- **C. Split big skills into small prompts**, pi-style (`/ship` → plan / record).
- **D. Keep** — the template is meant to be trimmed per project.

**Open** — decide only after the test.

## I-13 — Support pi as an agent

**Why.** pi already reads `AGENTS.md` and `.agents/skills/`, so most of the
template works there unchanged. Hooks and subagents don't (pi has none).

**Options**
- **A. Test and document** it as a supported agent (README, `loop.sh`
  `AGENT_CMD` example with `pi -p`).
- **B. Also port the hooks** as pi extensions (guard, stop-check).
- **C. Ignore.**

---

## Context — comparison with pi (2026-10-02)

Not the same layer: pi is a coding agent (runtime, providers, TUI, SDK); this is
a method on top of an existing agent. Comparable: pi's philosophy (minimal core,
"skips sub-agents and plan mode", extend it yourself) and the harness pi's own
repo is built with (`AGENTS.md`, `.pi/prompts`, `.pi/skills`, husky, `test.sh`).

**Where this template is ahead**
- A project layer — goal, metric, backlog, state. pi has none, by design.
- Enforced maker/checker: read-only reviewer in a fresh context, Stop hook on a
  red check. pi reviews in the same context.
- Guardrails (`guard-bash.py`). pi has no permission system.
- Onboarding interview, design skill, feedback → principle.

**Where pi is ahead**
- Battle-tested: its rules come from real incidents (sessions stomping on git,
  e2e tests burning paid tokens). Ours mostly come from reading — hence TODO.md.
- Concise, concrete instructions.
- Small single-purpose prompts (`/is`, `/pr`, `/wr`, `/cl`, `/deslop`).

The underlying difference: pi gives mechanisms, this template gives a workflow.
Both hold; our risk is doctrine piling up before it's been tested.

## Decided

<!-- ### I-XX — <idea> · <date>
Chose <option> because <reason>. Done in <commit / file>. -->
