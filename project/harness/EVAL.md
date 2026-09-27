# EVAL.md — the instrument panel

> **"A constraint without an instrument is a vibe — the agent will violate it
> cheerfully because it can't tell it's violating it."**
> Every claim about quality must come from a script here, not from an agent's
> opinion. This is the maker/checker split made concrete.

## Rules

1. **No self-grading.** The agent that wrote the code does not score it.
2. **Blind where possible.** If the eval has an answer key, the implementing
   agent must not see it. Score post-hoc, report per-item misses.
3. **Widen, don't narrow.** A small eval set gets memorized. Prefer many items.
4. **Hard limits.** Cap any list a loop could grow (keywords, retries, etc.).

## Eval layers

| Layer | What | Command | Threshold |
|---|---|---|---|
| Unit tests | logic correctness | `<test cmd>` | 100% pass |
| Integration | features work end-to-end | `<cmd>` | 100% pass |
| Lint/type | code hygiene | `<cmd>` | 0 errors |
| Visual | UI matches intent | `<screenshot diff>` | 0 regressions |
| LLM-judge | subjective quality | `scripts/eval_judge.py` | >0.85 |

## Score history

Append the score after each meaningful change. Trend > absolute value.

| Date | Commit | Score | Notes |
|---|---|---|---|
| | | | |

## The future-proofing test

> If the app gets better when the model gets better — **without you adding
> harness complexity** — the design is sound. If you keep needing more scaffolding
> to hold quality up, your scaffolding is the problem.

Re-run this test when a new model drops. Delete components that no longer earn
their keep. See "Build to Delete" in the harness doctrine.
