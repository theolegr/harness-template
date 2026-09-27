#!/usr/bin/env python3
"""guard-bash.py — Claude Code "PreToolUse" hook on Bash: autonomy boundaries, enforced.

AGENTS.md rule 6 and harness/guide/SOUL.md say "no deletes, no force-push, no
migrations without confirmation". This makes it mechanical:

  deny  → irreversible: force-push, reset --hard, clean -f, rm -rf (outside
          build/cache dirs), branch -D
  ask   → needs a human: migrations, DROP/TRUNCATE, deploys
          (in a non-interactive run, e.g. loop.sh, "ask" means refused)

Edit the lists below per project. Anything not matched goes through the normal
permission flow.
"""
import json
import re
import shlex
import sys

# rm -rf is fine on these (regenerable) paths
SAFE_RM = {"node_modules", "dist", "build", ".next", "coverage", "__pycache__",
           ".pytest_cache", ".ruff_cache", ".mypy_cache", ".turbo", ".cache",
           "tmp", "harness/.loop.stop", "harness/.check.ok"}

ASK = [
    (r"\b(migrate|migration)\b|\bdb\s+(push|reset)\b|\balembic\s+(upgrade|downgrade)\b",
     "database migration"),
    (r"\b(drop\s+(table|database|schema)|truncate\s+table)\b", "destructive SQL"),
    (r"\bdeploy\b|\bvercel\b.*--prod|\bnetlify\b.*--prod", "deploy"),
]


def segments(cmd):
    """Split a shell line into simple commands (on ; && || | and newlines)."""
    for part in re.split(r"[;&|\n]+", cmd):
        try:
            toks = shlex.split(part)
        except ValueError:
            toks = part.split()
        while toks and (toks[0] in ("sudo", "command", "exec") or "=" in toks[0]):
            toks = toks[1:]
        if toks:
            yield toks


def deny_reason(toks):
    prog, args = toks[0].rsplit("/", 1)[-1], toks[1:]
    flags = "".join(a[1:] for a in args if a.startswith("-") and not a.startswith("--"))
    longs = {a.split("=")[0] for a in args if a.startswith("--")}

    if prog == "rm" and ("r" in flags.lower() or "--recursive" in longs) \
            and ("f" in flags or "--force" in longs):
        targets = [a.rstrip("/").removeprefix("./") for a in args if not a.startswith("-")]
        if not targets or any(t not in SAFE_RM for t in targets):
            return "rm -rf outside build/cache dirs"
    if prog == "git" and args:
        sub, rest = args[0], args[1:]
        if sub == "push" and ("f" in flags or any(l.startswith("--force") for l in longs)
                              or any(a.startswith("+") for a in rest)):
            return "force-push"
        if sub == "reset" and "--hard" in longs:
            return "git reset --hard"
        if sub == "clean" and "f" in flags:
            return "git clean -f"
        if sub == "branch" and "D" in flags:
            return "git branch -D"
        if sub in ("checkout", "restore") and "." in rest:
            return "discarding all local changes"
    return None


def decide(kind, reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": kind,
        "permissionDecisionReason":
            f"harness guard: {reason} needs the user's explicit OK "
            f"(harness/guide/SOUL.md → autonomy boundaries).",
    }}))
    sys.exit(0)


def main():
    try:
        cmd = json.load(sys.stdin).get("tool_input", {}).get("command", "")
    except Exception:
        return
    segs = list(segments(cmd))
    for toks in segs:
        reason = deny_reason(toks)
        if reason:
            decide("deny", reason)
    for toks in segs:
        # a word in a commit message or a search is not an action
        if toks[0].rsplit("/", 1)[-1] in ("git", "echo", "printf", "grep", "rg"):
            continue
        for pattern, reason in ASK:
            if re.search(pattern, " ".join(toks), re.IGNORECASE):
                decide("ask", reason)


if __name__ == "__main__":
    main()
