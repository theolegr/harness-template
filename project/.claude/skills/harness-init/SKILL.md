---
name: harness-init
description: Interview the user to fill in this project's harness (AGENTS.md, harness/GOAL.md, harness/FEATURES.json, harness/STATE.md, test commands). Use right after init-harness.sh, when AGENTS.md or harness/ files still contain <placeholders>, or when the user wants to redefine the goal, stack or feature list.
---

# harness-init — fill the harness through an interview

The harness files were copied with `<placeholders>`. Your job: get the real
answers from the user, write them into the files, verify, and commit — with the
user's OK. Speak the user's language. Keep it short: the whole interview should
take ~10 minutes.

## 0. Look before you ask

Never ask what you can read. Before the first question:

1. Read `AGENTS.md`, `harness/GOAL.md`, `harness/FEATURES.json`, `harness/STATE.md`.
   - If they are already filled (no `<placeholders>`), this is a **re-run**: ask
     the user what they want to change (goal, stack, features…) and only run
     those rounds.
2. Detect what already exists in the repo, ignoring `harness/`:
   - manifests: `package.json`, `pyproject.toml`, `requirements.txt`, `go.mod`,
     `Cargo.toml`, `Gemfile`, `docker-compose.yml`, `vercel.json`, `fly.toml`…
   - their scripts (`npm run dev/test/lint`, pytest config, Makefile targets)
   - `README.md`, existing `src/`, `tests/`, git remote (`git remote -v`)
3. If `CLAUDE.md` exists but doesn't contain `@AGENTS.md` (the project had its
   own before the harness), offer to add that line so Claude Code loads
   `AGENTS.md`. Same for any `*.harness-new` file: show the diff and ask whether
   to merge it.
4. Turn every finding into a **proposal** the user confirms ("I see Next.js +
   Supabase and `npm test` — correct?") instead of an open question.
5. Read `harness/guide/SKILLS.md`: the external skills you may suggest.

## 1. The interview — 5 rounds

Use the AskUserQuestion tool when the answer has natural options (max 4
questions per call, put your recommendation first). Ask open questions in plain
text when the answer is free-form. After each round, restate in 2–3 lines what
you understood before moving on.

Every question can be skipped. A skipped answer keeps its `<placeholder>` and is
listed at the end as an open question.

**Skill suggestions.** After Round 2 (stack) and Round 4 (features), check
`harness/guide/SKILLS.md`. If a skill clearly fits this project, suggest it in
the next AskUserQuestion call (multiSelect): name + one line on why. Follow the
rules in that file: only real fits, at most 2 at a time, never an excluded tool.
No suggestion is the normal case. Install nothing during the interview.

**Round 1 — The project**
- Name, and one sentence: what it does, for whom, why it exists.
- Type (SaaS / web app / API / CLI / bot / other) and stage (idea / prototype /
  MVP / beta / production).

**Round 2 — Stack and commands** (propose from what you detected)
- Language, frontend, backend, DB, hosting, auth, payments — "none yet" is a
  valid answer. For a new project with no preference, propose a stack that fits
  the type and say why, in one line.
- The commands: install, dev, build or typecheck, test, lint, deploy. The
  build/typecheck one must **end** (unlike dev): it's how agents check the app
  starts. For a brand-new project, propose the conventional ones for the
  chosen stack.

**Round 3 — The goal** (the most important round — don't rush it)
- Target: one sentence describing what "winning" looks like.
- Success metric: a number, its current value, its target, and **how it is
  measured**. If the user has no instrument, say so plainly and propose the
  simplest one (e.g. "number of acceptance tests passing" for an early MVP).
  Never invent a metric the user hasn't agreed to.
- Constraints: time budget, money budget, scope cap. Non-goals (what we
  deliberately won't build).

**Round 4 — The first features**
- Propose 3–5 features derived from the goal, each with a priority (p0–p3) and
  a testable acceptance criterion. Show them as a short list; let the user
  edit, add, remove, reorder. Features must be small enough for one session each.

**Round 5 — How the agents work** (offer the defaults, most users accept them)
- Autonomy: keep the defaults of `harness/guide/SOUL.md` (code/tests/docs free;
  deploy, publish, spend money, destroy data need approval)? Anything to add?
- Public voice, if the product has user-facing copy (tone in one line).
- Day to day the user drives from this chat with the `ship` skill ("ship the
  next one"): nothing to configure. Only for unattended runs (`loop.sh`, cron):
  keep the default commands already in `AGENTS.md` §3, or change them.
  Can be left for later.

## 2. Write the files

| Answer | Where it goes |
|---|---|
| Name | `AGENTS.md` title, `harness/FEATURES.json` → `project`, `harness/guide/SOUL.md` |
| One-sentence description, type, stage, repo URL | `AGENTS.md` §1 |
| Stack (with the "why" column) | `AGENTS.md` §2 |
| Commands | `AGENTS.md` §3 and `harness/guide/TESTING.md` → Commands |
| Test / lint commands | `harness/scripts/harness-check.sh` → `TEST_CMD=` / `LINT_CMD=` (only these two lines) |
| Install / build / test / lint / dev commands | `.claude/settings.json` → `permissions.allow` as `Bash(<cmd>*)` (never deploy: the guard asks for it on purpose) |
| Map of the codebase | `AGENTS.md` §4 — reflect the real folders |
| Target, metric table, constraints, non-goals | `harness/GOAL.md` — the target replaces the `<the target, in one sentence>` line under `## Target` (`harness-status.sh` prints that line) |
| Features | `harness/FEATURES.json` (keep the schema: id `F-001`…, type `feature`, name, status `todo`, priority, acceptance, files, notes) + the MVP milestone. Bugs and debt come later, as `B-…` / `D-…` via `feature.sh add` |
| Phase, health 🟢, "Working on" = first p0 feature, "Next" = the next ones, today's date | `harness/STATE.md` |
| Skipped answers | `harness/STATE.md` → Open questions |
| Autonomy / voice changes | `harness/guide/SOUL.md` |
| Loop commands | `AGENTS.md` §3 (the `loop.sh` line) |
| Stack choice | `harness/DECISIONS.md` → the "Initial stack choice" entry, dated today |
| Accepted / declined skills | `harness/DECISIONS.md` → one entry "Initial skills": which, why, which were declined |

Rules while writing:
- Replace placeholders; don't rewrite the surrounding doctrine text.
- Delete example rows (`e.g. …`) once real rows exist.
- `harness/FEATURES.json` must stay valid JSON.
- Never touch `harness/template/`.

## 3. Verify, show, commit

1. If skills were accepted, install them as `harness/guide/SKILLS.md` says
   (show the commands, run them; `/plugin …` commands go to the user).
   Report any failed install.
2. Run `./harness/scripts/harness-check.sh`. For a project with no code yet,
   failing tests only because nothing exists is expected — say so. Any other
   failure: fix it.
3. Run `./harness/scripts/harness-status.sh` and show the output.
4. Summarize for the user in a few lines: goal, metric, first feature, what was
   skipped (open questions).
5. Ask for the OK, then commit: `chore: initialise project harness`.
   Do not commit without the OK.
6. Tell the user the next step, in one or two lines: say "ship the next one"
   (or `/ship`) to start the first feature — you'll show them the plan before
   building. Mention they can ask the `strategist` for an overview or a
   brainstorm any time.
