# PLAN.md — active plan

> Written BEFORE executing anything that takes >30 min. Deleted/archived when done.
> Plan and execution are separate phases with a hard gate between them.
> If a plan is stale, delete it — a wrong plan is worse than none.

## Task

<One line: what we're doing and why now.>

## Definition of done

- [ ] <acceptance criterion 1> — verified by `<test command>` → expected: <result>
- [ ] <criterion 2> — verified by …
- [ ] Tests pass / eval score held or improved

## Approach

Grounded in the real codebase: cite real file paths and real symbols.

1. `<path/to/file.py>` — <change: which function/class, and why>
2. `<path/to/other.ts>` — <change>
3. `<new file>` — <what it does>

## Risks / unknowns

- <risk> → <mitigation>

## Out of scope (explicitly)

- <thing not being done in this plan>

---
**Gate:** do not start step 1 until this file is complete and the approach is
grounded in files that actually exist. After the plan is agreed, execute
top-to-bottom without re-planning mid-flight.
