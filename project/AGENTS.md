# AGENTS.md — <PROJECT NAME>

> Onboarding doc for any AI agent (Claude Code, Codex, Cursor…).
> Read at the START of every session. Keep it short (<200 lines).
> This file is the entry point — it points to where the real context lives.
> Still full of angle-bracket placeholders? Run the `harness-init` skill
> (`/harness-init` in Claude Code) to fill it in through a short interview.

## 1. What is this?

<One paragraph. What the product does, for whom, and why it exists.>

- **Type**: SaaS / web app / API / tool / bot
- **Stage**: idea | prototype | MVP | beta | production
- **Repo**: <url>

## 2. Stack

| Layer | Choice | Why |
|---|---|---|
| Language | <e.g. Python 3.12 / TypeScript> | |
| Frontend | <Next.js / Svelte / none> | |
| Backend | <FastAPI / Node / Supabase> | |
| DB | <Postgres / SQLite> | |
| Hosting | <Fly / Vercel / VPS> | |
| Auth | <Clerk / Supabase / custom> | |
| Payments | <Stripe / none yet> | |

## 3. How to run it

```bash
# install
<command>

# dev (long-running: agents start it in the background, never in the foreground)
<command>

# build / typecheck (ends — how an agent checks the app starts)
<command>

# test
<command>

# lint
<command>

# deploy
<command>

# outer loop — in a chat: the ship skill (/ship). Unattended (see harness/guide/LOOP.md):
AGENT_CMD="claude -p --model opus --permission-mode acceptEdits --max-budget-usd 5" \
  VERIFIER_CMD="claude -p --agent reviewer --permission-mode dontAsk" ./harness/scripts/loop.sh once
```

## 4. Map of the codebase

```
src/            <- application code
tests/          <- tests (see harness/guide/TESTING.md)
harness/        <- project state: goal, state, features, plan, evals, decisions
harness/guide/  <- how we work (boot sequence, autonomy, testing, loops…)
harness/scripts/<- status, check (the verification gate), loop
```

`harness/template/` is the untouched harness template, git-ignored. Never read
or edit it while working on the project.

**Rule: the codebase IS the documentation.** If you need context, read the code
and the files above — not a separate wiki. See `harness/DECISIONS.md` for why things
are the way they are.

## 5. Working rules (read before every task)

1. **One thing at a time.** Pick ONE item from `harness/FEATURES.json` (a feature, a bug or tech debt),
   finish it, commit, repeat. In a chat, the `ship` skill runs that loop: plan → user OK → build →
   reviewer → record.
2. **Plan before executing.** For anything >30min of work, write the plan to `harness/PLAN.md` first.
3. **Show state, don't describe it.** Point at real files, real symbols, real errors.
4. **Never self-grade.** Verification comes from tests, the eval harness, or the `reviewer` subagent
   (read-only, fresh context). Its non-blocking findings go to the backlog with
   `harness/scripts/feature.sh add bug|debt …` — they're handled later like any feature.
5. **Commit often.** Every completed feature = one commit with a clear message.
6. **Ask before destructive actions.** No deletes, no force-push, no schema migrations without confirmation.
   In Claude Code this is enforced by hooks (`.claude/settings.json`): destructive commands are refused,
   and you can't end a turn while `harness-check.sh` is red.
7. **Suggest skills that fit, don't hoard them.** When a feature or a discussion needs something the
   harness doesn't cover, check `harness/guide/SKILLS.md`, suggest at most 2 with the reason, install only with an OK.
8. **Brainstorm with the strategist.** For an overview, "what's next?", or an empty backlog, use the `strategist`
   subagent (read-only). Show its proposals to the user; add the accepted ones with `feature.sh add`.
9. **Another session in this folder → your own worktree.** The status at session start says so
   (`⚠ OTHER SESSIONS`); uncommitted changes you didn't make are a sign too. If you'll change files:
   `git worktree add ../<repo>-<topic> -b <branch>`, install the dependencies there, and in Claude Code
   `EnterWorktree` with that path. Merge back, then remove the worktree, with the user's OK. In a folder
   another session uses: never switch branches or `git stash`, and stage only your files (explicit paths,
   not `git add -A`). Alone in the folder: work there as usual.
10. **What waits on the user is written down, never only in the chat.** An item that needs their info,
    choice or OK → `feature.sh <id> blocked "waiting on <user>: <what>"` (the reason is kept apart, the
    notes stay). Any other question or decision you raised that's still open at the end of your turn →
    `harness/STATE.md` → Open questions. Both show at the top of the dashboard, under "Waiting on you".

## 6. Session boot sequence

Follow `harness/guide/BOOT.md` at the start of every session. It takes 30 seconds and prevents
20 minutes of re-exploration. `./harness/scripts/harness-status.sh` shows the state at a glance.

## 7. Where to look

| Need | File |
|---|---|
| Who the agent is, autonomy boundaries | `harness/guide/SOUL.md` |
| Current state / what's next | `harness/STATE.md` |
| Backlog: features, bugs, debt (work left) | `harness/FEATURES.json` — add / change status with `harness/scripts/feature.sh` |
| Ship the next item, in a chat | `.claude/skills/ship/SKILL.md` (`/ship`) |
| Review a change (read-only) | `.claude/agents/reviewer.md` |
| Overview, brainstorm, new ideas (read-only) | `.claude/agents/strategist.md` |
| Finished / cut features | `harness/FEATURES-DONE.json` (read only when you need history) |
| The goal + metric + /goal contract | `harness/GOAL.md` |
| Visual direction, design values (read before any UI work) | `harness/DESIGN.md` |
| Set the visual direction, first mockups | `.claude/skills/design/SKILL.md` (`/design`) |
| Pages published outside the repo (canvases, diagrams, shared mockups) | `harness/ARTIFACTS.md` — add a line whenever you publish one |
| Quality bar / instruments | `harness/EVAL.md` |
| Test conventions | `harness/guide/TESTING.md` |
| Decisions log | `harness/DECISIONS.md` |
| Active plan | `harness/PLAN.md` |
| Outer loop, automations, parallel work | `harness/guide/LOOP.md` |
| Memory + learning from corrections | `harness/guide/MEMORY.md` |
| A bug or gap in the harness itself (not the project) | `harness/TEMPLATE-FEEDBACK.md` (create it), then an issue or PR on the template repo |
| External skills to suggest | `harness/guide/SKILLS.md` |
| Health check (exit code = verdict) | `harness/scripts/harness-check.sh` |
| Project state as JSON / as a page for the user | `harness/scripts/state.py` / `harness/scripts/dashboard.py --open` (then rewritten at the end of each turn by the Stop hook; the open tab reloads itself) |
