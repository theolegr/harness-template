# BOOT.md — Session boot sequence

> Run this at the START of every agent session. 7 steps, ~30 seconds.
> Skipping it costs 20 minutes of re-exploration and produces stale work.

## The 7 steps

1. **Confirm the working directory.**
   `pwd` — you must be at the project root. If not, `cd` there.
   The status warns `⚠ OTHER SESSIONS`, or there are uncommitted changes you didn't make, and you'll
   change files → work in your own worktree first (`AGENTS.md` §5).

2. **Read the state of the world.**
   Read `harness/STATE.md` (current status) and `harness/GOAL.md` (the target + metric).
   Read the last 10 lines of `harness/DECISIONS.md`.

3. **Read the git reality.**
   `git log --oneline -10 && git status`
   This tells you what actually shipped vs. what the notes claim.

4. **Read the feature tracker.**
   `harness/FEATURES.json` — the backlog: features, bugs (`B-…`) and tech debt (`D-…`).
   Find the next item with `"status": "in_progress"`, else `"todo"` by priority.
   It only holds the work left; finished features are in `harness/FEATURES-DONE.json`
   (don't read it unless you need history).
   Pick exactly ONE, and mark it: `./harness/scripts/feature.sh <id> in_progress`. Do not batch.

5. **Verify the app still runs.**
   Run `./harness/scripts/harness-check.sh` (tests + lint). To check the app starts, use a
   command that **ends** — the build or typecheck from `AGENTS.md` §3 — never a dev server in
   the foreground: it never exits and you'd wait for the timeout. If you need the running app,
   start the server in the background, hit it once (`curl`), then stop it.
   If something is already broken, fix that FIRST — do not build on a broken base.

6. **Declare the session goal (out loud, in one line).**
   Example: "Session goal: implement email verification callback (F-012)."
   If you cannot state it in one line, the task is too big — split it.

7. **Write the plan (if >30min of work).**
   Update `harness/PLAN.md` with the concrete steps, real file paths, and the definition
   of done. Then execute.
   Before planning, glance at `harness/guide/SKILLS.md`: if this feature needs a skill
   that isn't installed (a test tool, a stack, security…), suggest it with the reason.
   A feature with user-facing UI: read `harness/DESIGN.md` first (no direction yet →
   the `design` skill comes before the code).

## Anti-patterns (do not do these)

- ❌ Starting to code before step 5 (running app).
- ❌ Picking three features "to save time" — context bloat kills quality.
- ❌ Trusting `harness/STATE.md` over `git log`. Git wins.
- ❌ Working from memory of a previous session instead of re-reading the files.

## End-of-session routine

1. Run tests + update the eval score in `harness/EVAL.md`.
2. Update the status of the item you touched: `./harness/scripts/feature.sh <id> <status>`
   (`done` / `cut` moves it to `FEATURES-DONE.json`). Don't edit statuses by hand.
3. Update `harness/STATE.md` (what changed, what's next, any blocker). Anything that waits on the
   user → a `blocked` item with its reason, or a line in Open questions (`AGENTS.md` §5).
4. Append any real decision to `harness/DECISIONS.md` (dated, with rationale).
5. `git add <your files> && git commit -m "<type>: <what>"` — `git add -A` only when you're alone in
   this folder (no other session's work in it).
6. If the loop continued nothing: log why in `harness/STATE.md`.
