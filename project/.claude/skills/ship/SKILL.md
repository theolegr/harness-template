---
name: ship
description: Ship the next backlog item (feature, bug or tech debt from harness/FEATURES.json) inside this chat — pick it, plan it (the user validates), build it, have the independent reviewer subagent verify it, record it. Use when the user says, in any language, "ship", "ship the next one", "next feature", "let's do the next one", "ship F-003", "fix B-002", or asks to work through the backlog.
---

# ship — the outer loop, in the chat

The same loop as `harness/scripts/loop.sh` (pick → plan → build → verify →
record), run by you in this conversation so the user sees each step and
answers questions. `loop.sh` is for unattended runs; this is the default.

The one guarantee you must keep: **the maker is not the checker.** You build;
the `reviewer` subagent — fresh context, read-only — decides if it passes.

Speak the user's language. Keep your messages short: the user reads the plan
and the result, not a narration.

## 1. Pick one item

- The user named one (`ship F-003`, `fix B-002`) → that one.
- Otherwise the next one, like `loop.sh`: `in_progress` first, then by
  priority (`p0` before `p1`). `./harness/scripts/harness-status.sh` shows it.
  `blocked` items wait on the user (their reason says what for): skip them.
- Backlog empty → say so and offer the `strategist` agent to propose what's next.
- `./harness/scripts/harness-check.sh` already red before you start → fixing
  that is the item. Never build on a broken base.
- The status warns `⚠ OTHER SESSIONS`, or there are uncommitted changes you
  didn't make → another session is working here: don't touch, stash or commit
  its files; build in your own worktree (`AGENTS.md` §5). Unsure whose they
  are → ask.

Then `./harness/scripts/feature.sh <id> in_progress`.

## 2. Plan — the user validates

Follow `harness/guide/BOOT.md` (the SessionStart hook already injected the
status; read what it doesn't show: the item's acceptance, `STATE.md`, the tail
of `DECISIONS.md`, the files you'll touch).

Check `harness/guide/SKILLS.md`: if this item needs a skill that isn't
installed, suggest it now (at most 2, with the reason).

The item touches user-facing UI → read `harness/DESIGN.md` and build from its
values and mockups. Its status is still "no direction yet" → stop and propose
the `design` skill first (or add a design item): UI built without a direction
gets redone. The design item itself is run by the `design` skill, not here.

The item handles input a stranger controls (a form field, an email, a URL, an
uploaded file, a prompt) → plan the attacks now, not after the review: list the
cases in the definition of done (links and addresses, look-alike and invisible
characters, oversize input, injection…) and prefer an allowlist to a blocklist
(`harness/guide/TESTING.md` → Adversarial verification).

Write the plan to `harness/PLAN.md` — real paths, real symbols, definition of
done = the acceptance criterion. Show the user a short version (5–10 lines:
what changes where, how it's tested, what's out of scope) and **wait for their
OK**. This is the cheapest moment to change direction.

Small item (a one-line bug, a rename): a 3-line plan in the chat is enough,
no `PLAN.md` — but still wait for the OK.

The user may waive the gate ("ship F-002 to F-004 without asking"): then go on
without waiting, and say so in the report.

## 3. Build

- Implement the plan, and the acceptance test with it (`harness/guide/TESTING.md`).
- Stay in scope. Something wrong you notice outside it → don't fix it, note it
  for step 5.
- Run `./harness/scripts/harness-check.sh` until it's green. (The Stop hook
  runs it anyway when you end your turn.)

## 4. Verify — the reviewer subagent

Note the commit the work started from (`git rev-parse HEAD` before building,
or the last commit if you didn't). Launch the `reviewer` subagent with only
the facts:

> Review the changes since commit `<sha>` (uncommitted ones included) for
> `<id>`: `<name>`. Acceptance criterion: `<acceptance>`.

Add the attack cases from the plan when there are some (they're part of the
definition of done, not your opinion).

Don't tell it what you think of your own code, and don't pre-empt its findings.

Read the answer: the `VERDICT:` line, the blocking problems, the `FINDING:` lines.

- **PASS** → step 5.
- **FAIL** → fix the blocking problems it named, re-run `harness-check.sh`,
  then launch a **new** reviewer (fresh context again). At most 2 fix rounds.
  Still FAIL → stop and ask the user: keep going, park it
  (`feature.sh <id> blocked "<why>"`, commit the attempt on a `wip/<id>`
  branch), or drop the change (destructive: needs their explicit OK).
- You disagree with a verdict or a finding → tell the user why; they decide.
  Never skip the reviewer, never argue a FAIL away on your own.

## 5. Record

1. Findings → backlog, one call each, then list them to the user:
   `./harness/scripts/feature.sh add <bug|debt> <prio> "<title>" "<how to check it's fixed>" "from review of <id>"`
   Add your own out-of-scope notes from step 3 the same way.
2. `./harness/scripts/feature.sh <id> done`.
3. `harness/STATE.md`: Now, Next, Recently done, a session-log entry.
4. The metric: if this item moved the number in `harness/GOAL.md`, update its
   "Current" value and add a row to `harness/EVAL.md` → Score history.
5. A real choice was made → `harness/DECISIONS.md`.
6. Commit: `feat(<id>): <name>` for a feature, `fix(<id>): …` for a bug,
   `refactor(<id>): …` for debt.

## 6. Report

A few lines: what shipped, the verdict (and fix rounds, if any), the new
backlog items, the metric, the next item. Then ask: "Ship the next one?"

A question you asked that the user hasn't answered yet, or an item that now
waits on them, is written down before you end the turn: `feature.sh <id>
blocked "<what it waits on>"` (citing the `Qn` of the open question it waits
on, if any), or `harness/STATE.md` → Open questions, numbered `Qn` (`AGENTS.md` §5,
rule 10: numbers are never reused).

Don't chain to the next item on your own — unless the user asked for several
("ship 3", "ship until the MVP"). Even then, stop at the first FAIL you can't
fix, at any question only they can answer, and at anything the guard hook
asks about (migrations, deploys).
