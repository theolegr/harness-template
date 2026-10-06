# TODO — what's left to validate

The scripts are tested on throwaway projects (fake agents stand in for Claude
in `loop.sh`). What follows needs a **real project with a real Claude** —
tick it off, then update the *Status* note in the README.

## Real-world test — one small project, end to end

- [x] `init-harness.sh` on a new folder → the interview fills every file;
      `harness-status.sh` shows the target and no placeholder warning.
      *(2026-09-29, first real project: existing folder, `--no-interview` then `harness-init`.)*
- [ ] `/ship` on 2–3 features:
  - [ ] it shows the plan and waits for the OK before building
  - [ ] the `reviewer` subagent is really launched (fresh context), ends with
        `VERDICT:`, and its `FINDING:` lines land in the backlog as `B-` / `D-`
  - [ ] on a FAIL: fix → new reviewer, at most 2 rounds, then it asks
  - [ ] record step: item archived, `STATE.md` and the metric updated, one commit
- [ ] A backlog item of type `bug` shipped the same way (`fix B-001`).
- [ ] `strategist`: an overview and a brainstorm; `PROPOSAL:` lines; nothing
      added without an OK. Check Claude delegates to it (and not to the
      built-in `Explore` agent) when asked for a brainstorm.
- [ ] Hooks in a real session: SessionStart shows the status; the guard refuses
      `rm -rf src` and asks before a migration; the Stop hook sends the agent
      back on a red check.
- [x] A project skill created in `.agents/skills/` is linked and usable as
      `/<name>` in the next session.
      *(2026-09-29, first real project: `react-native-testing`, linked by `link-skills.sh`, usable in the same session.)*
- [ ] `/design` on a project with screens: the interview asks "inspiration or
      copy?" for each reference; 2–3 directions land on a canvas; a crossed-out
      element is removed and the mark cleaned up; `DESIGN.md` gets exact values;
      `/ship` of the next UI item reads it and the reviewer checks against it.
      (First run in a real project, 2026-09 — the skill is distilled
      from it, not yet run as written.)
- [ ] `loop.sh once` with the real `claude -p` commands from `AGENTS.md` §3:
      plan, build, review, state update — and a forced failure (blocked item,
      row in `STATE.md` Blockers, attempt kept on its branch).

## Known limits

- Windows: `link-skills.sh` needs symlink support in git; not tested.
- `loop.sh` never merges into your main branch — by design.

## After the test

- Adjust the skills and agents to what was actually observed.
- Measure before changing models (see *Model routing* in `project/harness/GOAL.md`).
- Go through [IDEAS.md](IDEAS.md): the improvement backlog, decisions still open.
