# LOOP.md — running agents: the outer loop, automations, parallel work

> **Harness = the environment for one agent. Loop = the harness that runs on a
> timer, finds work, dispatches it, verifies it, and records state.**
> Inner loop (agent: code → test → fix) + outer loop (ship → measure → change
> tack → descend toward the goal).

## The outer loop

```
DISCOVER  failing tests / CI, FEATURES.json todo items, issues labelled `agent`
SELECT    one item, highest priority
PLAN      write harness/PLAN.md (real paths)           ← hard gate
EXECUTE   branch loop/<id> (worktree if parallel)
VERIFY    harness-check.sh + a SEPARATE reviewer agent ← maker ≠ checker
RECORD    commit, feature.sh <id> done, STATE.md
MEASURE   EVAL.md score; did the GOAL.md metric move?
          → loop, or stop
```

Two ways to run it — same steps, same maker ≠ checker split:

| You are… | Use | Plan gate | Verify |
|---|---|---|---|
| in the chat (default) | the `ship` skill — "ship the next one" | the user validates `PLAN.md` | `reviewer` subagent, fresh context |
| away (cron, overnight) | `harness/scripts/loop.sh` | none: the plan is executed as written | `claude -p --agent reviewer` |

In both, the reviewer's non-blocking findings become `bug` / `debt` items in
`harness/FEATURES.json` (`feature.sh add`), picked up later like features.

```bash
./harness/scripts/loop.sh once                              # one iteration
0 3 * * * cd /path/to/project && ./harness/scripts/loop.sh run >> harness/.loop.log 2>&1
```

**Stop conditions** — the loop halts when ANY is true:
- The metric in `harness/GOAL.md` hit its target.
- Budget (time / money / `MAX_ITER`) exhausted.
- Two iterations in a row moved no metric → **stall** (see `harness/GOAL.md`).
- A decision only a human can make → write it in `harness/STATE.md` "Open questions" and stop.

**What the loop does NOT do:** verify itself, replace your understanding of what
it ships (review it), or think for you — a loop without judgement accelerates
whatever direction you're pointed in, including the wrong one.

## Any automation — five required parts

Applies to `loop.sh` and to anything else you automate (cron jobs, digests,
triage). Missing one = a runaway that rots or burns tokens.

| # | Part | Failure if missing |
|---|---|---|
| 1 | **Trigger** — schedule or signal | work waits for a human to notice |
| 2 | **One change per round** | "do everything" runs that can't be verified |
| 3 | **Eval gate** — the same deterministic check every time | bad output ships silently |
| 4 | **State file** — what's been tried/done | pays twice for the same work |
| 5 | **Stop rule** + budget | runs forever |

Pick the least autonomous shape that works: **cron** (fixed job, repeats) <
**loop** (one change per round until a stop rule) < **goal** (works until a
finish line). For a `/goal`, "done when" must be a proof that can be *shown*
(a green test run pasted in chat), not assumed — the judge only sees the conversation.

Every new automation starts 🟡 (human approves) — see the autonomy table in
`harness/guide/SOUL.md`. Promote to 🟢 only after its eval gate has held over
many runs.

| Automation | Shape | Schedule | Color | Stop rule |
|---|---|---|---|---|
| <name> | cron / loop / goal | | 🟡 | |

**Monthly audit**: which automations cost the most? Which have no stop rule?
Which get sharper every run vs. just run? Fewer loops that compound beat more loops.

## Parallel work

- **The "and then" test**: does the next step read the previous step's output?
  If not, there's no real dependency — run them in parallel.
- **Isolate**: parallel agents in one directory clobber each other's checkout.
  One git worktree per worker:
  ```bash
  git worktree add ../wt-<task> -b <task>   # … agent works there …
  git worktree remove ../wt-<task>
  ```
- **Fresh context per worker**: each agent call starts clean (`loop.sh` already
  runs plan, execute and review as separate calls). Hand it a bounded input —
  the plan, the files — not the whole history.
- **Cost**: the strongest model for anything that writes or gates code; a fast
  one only for read-only chores (see Model routing in `harness/GOAL.md`). Cap
  concurrency; every fan-out needs a stop condition.
