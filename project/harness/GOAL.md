# GOAL.md — the target and the metric

> The single most important file. A project without a measurable target is a
> direction-less prompt. This is the **loss function** for the project: what we
> optimize, how we measure it, and what constrains us.

## Target

> **One sentence**: what does "winning" look like? Replace the line below.
> e.g. "A paying user can sign up, connect a data source, and get a weekly report
> without human help."

<the target, in one sentence>

## Success metric (the eval)

The number that tells us we're moving in the right direction. Must be measurable
automatically.

| Metric | Current | Target | Measured by |
|---|---|---|---|
| e.g. Activation rate | 0% | 40% | `scripts/eval.py` |
| e.g. p95 latency | — | <500ms | load test |
| e.g. Eval score | — | >0.85 | `harness/EVAL.md` rubric |

> **Rule:** if a constraint has no instrument, it's a vibe. Every target above
> needs a script or a test that produces the number. See `harness/EVAL.md`.

## Constraints (budget, time, scope)

- **Time budget**: <e.g. 6 weeks to MVP>
- **Money budget**: <e.g. <$50/mo infra>
- **Scope cap**: <what we deliberately do NOT build>
- **Methodology**: <e.g. no paid ads before PMF>

## Non-goals

- ❌ <thing that would be tempting but off-strategy>
- ❌ <another>

## The /goal contract

When you hand this project to an agent autonomously, use this shape:

```
/goal
Outcome:     [what must be true when done]
Sources:     [where to look — files, APIs, docs]
Constraints: [time budget, money cap, scope cap]
Deliverable: [the artifact]
Done when:   [a specific, PASTABLE proof — not "tests pass", but "green test run pasted"]
```

> ⚠️ A judge only sees the conversation. "Done when tests pass" is unverifiable by
> the judge. "Done when the green test run is pasted in chat" is a contract.

## Model routing

A bug costs more than the tokens a cheaper model saves: a failed attempt, a
second review, and your time to understand what went wrong. So:

| Work | Model | Why |
|---|---|---|
| Planning, coding, reviewing — anything that changes code or gates it | strongest (`opus`) | mistakes here become bugs |
| The reviewer | strongest, pinned with `model:` in `.claude/agents/reviewer.md` | the checker must be at least as strong as the maker |
| Read-only, mechanical: searching code, summarising logs or test output | a fast model is fine | a mistake there costs nothing |

- **Downgrade a step only on evidence**: run it on ~5 items with the cheaper
  model and compare the reviewer's PASS rate and the fix rounds (log them in
  `harness/EVAL.md`). No evidence → keep the strongest.
- **Tokens are saved by context, not by model**: one item at a time, a fresh
  context per phase, a lean `FEATURES.json`, a plan before code. That's where
  the waste is.

## Forced entropy (anti-stall)

When we stall (2+ sessions with no metric movement):
- Force a jump: change approach entirely for one session.
- Write an "overfit reflection": what are we grinding on, and is it the real lever?
- Log it in `harness/STATE.md` under "Stalls".

## Review cadence

- **Weekly**: compare metric to target. Update this file if the target was wrong.
- **Monthly**: is the target still the right thing to optimize? (Loss function review.)
