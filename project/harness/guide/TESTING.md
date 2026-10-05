# TESTING.md — how tests work here

> Tests are the best milestone: deterministic, clear expectations, no arguing.
> A task is done when its acceptance criterion has a passing test.

## Commands

```bash
<test command>       # full suite
<test command> -k X  # single test
<lint command>       # must be clean before commit
```

## Conventions

- **Naming**: `<what>_<condition>_<expected>` (e.g. `signup_with_dup_email_returns_409`).
- **One assertion of intent per test.** Testing behavior, not implementation.
- **No network in unit tests.** Mock externals at the boundary.
- **Fixtures**: shared fixtures live in `<path>`. Don't inline big blobs.

## What to test

- Every feature in `harness/FEATURES.json` has an acceptance test before it's marked `done`.
- Bug fixes get a regression test that fails before the fix.
- Don't chase coverage %. Test what matters; skip the ceremony.

> **Anti-pattern (Foxconn factory):** 262K lines of app code + 276K lines of tests
> policing it. Build freedom, not cages. Test the behavior that carries risk.

## The contract: acceptance criterion + definition of done

The contract for a task is its `acceptance` in `harness/FEATURES.json`, made
concrete in the **Definition of done** of `harness/PLAN.md`: each criterion
with the command that proves it and the expected result. Write it before
implementing; the reviewer judges against it. No separate contract file.

## Adversarial verification (for critical changes)

For anything risky (payments, auth, data migrations), don't just test — attack:
1. Agent A: find bugs.
2. Agent B: try to disprove each finding.
3. Human/referee: decide.

**Input a stranger controls** (a form field, an email, a URL, a file, a prompt) is risky too, and the
attack starts at the plan: list the cases in the definition of done, each with its test — links and
addresses, IPs, look-alike and invisible Unicode characters, oversize input, injection. Prefer an
**allowlist** (what a valid value looks like) to a blocklist (what a bad one looks like): a blocklist
loses to the next disguise. On a real project, a name field echoed in an email took 4 reviews because
it started as a blocklist — beaten by an IP, then a full-width dot, then a zero-width space — before
an allowlist passed.

Catches the sycophancy problem where an agent "finds" bugs that don't exist, or
misses real ones to please.
