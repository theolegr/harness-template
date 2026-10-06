#!/usr/bin/env python3
"""guard-bash.py — Claude Code "PreToolUse" hook on Bash: autonomy boundaries, enforced.

AGENTS.md rule 6 and harness/guide/SOUL.md say "no deletes, no force-push, no
migrations without confirmation". This makes it mechanical:

  deny  → irreversible: force-push, reset --hard, clean -f, rm -rf (outside
          build/cache dirs), branch -D
  ask   → needs a human: migrations, DROP/TRUNCATE, deploys
          (in a non-interactive run, e.g. loop.sh, "ask" means refused)

Commands are split quote-aware (a `|` inside a grep pattern is not a pipe), and
what a line hands to a shell (`bash -c "…"`, `eval`, a heredoc fed to `sh`) is
checked too. Tests: tests/test_guard_bash.py in the template repo.

A safety net, not a sandbox: it matches command patterns, so it catches an
agent's mistakes, not every way to do damage (a script, or `find … -delete`,
can still remove files — IDEAS.md I-16 in the template repo). For unattended
runs, use a sandbox.

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


SHELLS = {"sh", "bash", "zsh", "dash", "ksh"}
OPS = "();<>|&\n"
# a heredoc marker (<<EOF, <<-'EOF', <<"EOF"), not a here-string (<<<)
HEREDOC = re.compile(r"(?<!<)<<(?!<)(-?)\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")


def split_commands(cmd):
    """Split a shell line into simple commands on ; && || | ( ) and newlines.

    Quote-aware: a | or ; inside quotes is text (e.g. a grep pattern), not a
    separator. '#' is not treated as a comment: shlex would swallow the newline
    that ends it, and the next line's command with it."""
    lex = shlex.shlex(cmd, posix=True, punctuation_chars=OPS)
    lex.whitespace_split = True
    lex.whitespace = " \t\r"
    lex.commenters = ""
    try:
        toks = list(lex)
    except ValueError:                  # unbalanced quotes: coarse split, errs on catching
        return [p.split() for p in re.split(r"[;&|\n]+", cmd) if p.split()]
    segs, cur = [], []
    for t in toks:
        if t and set(t) <= set(OPS):
            if cur:
                segs.append(cur)
            cur = []
        else:
            cur.append(t)
    if cur:
        segs.append(cur)
    return segs


def strip_prefix(toks):
    while toks and (toks[0] in ("sudo", "command", "exec", "env", "nohup", "time", "nice")
                    or "=" in toks[0]):
        toks = toks[1:]
    return toks


def prog_of(toks):
    return toks[0].rsplit("/", 1)[-1]


def split_heredocs(cmd):
    """Take heredoc bodies out of the command line: they are data, not commands —
    unless they are fed to a shell, in which case they are returned to be checked."""
    lines, out, to_shell, i = cmd.split("\n"), [], [], 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        i += 1
        for m in HEREDOC.finditer(line):
            dash, delim, body = m.group(1), m.group(3), []
            while i < len(lines):
                end = lines[i].lstrip("\t") if dash else lines[i]
                i += 1
                if end == delim:
                    break
                body.append(lines[i - 1])
            head = [strip_prefix(s) for s in split_commands(line[:m.start()])]
            head = [s for s in head if s]
            if head and prog_of(head[-1]) in SHELLS:
                to_shell.append("\n".join(body))
    return "\n".join(out), to_shell


def segments(cmd, depth=0):
    """Every simple command the line would run, including what it hands to a
    shell: `bash -c "…"`, `eval "…"`, and heredocs fed to a shell."""
    text, nested = split_heredocs(cmd)
    for toks in split_commands(text):
        toks = strip_prefix(toks)
        if not toks:
            continue
        yield toks
        prog, args = prog_of(toks), toks[1:]
        if prog in SHELLS:
            for j, a in enumerate(args):
                if a.startswith("-") and not a.startswith("--") and "c" in a[1:]:
                    if j + 1 < len(args):
                        nested.append(args[j + 1])
                    break
        elif prog == "eval":
            nested.append(" ".join(args))
    if depth < 3:
        for sub in nested:
            yield from segments(sub, depth + 1)


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


def check(cmd):
    """→ ("deny" | "ask", reason), or (None, None) when the command is fine."""
    segs = list(segments(cmd))
    for toks in segs:
        reason = deny_reason(toks)
        if reason:
            return "deny", reason
    for toks in segs:
        # a word in a commit message or a search is not an action
        if prog_of(toks) in ("git", "echo", "printf", "grep", "rg"):
            continue
        for pattern, reason in ASK:
            if re.search(pattern, " ".join(toks), re.IGNORECASE):
                return "ask", reason
    return None, None


def main():
    try:
        cmd = json.load(sys.stdin).get("tool_input", {}).get("command", "")
    except Exception:
        return
    kind, reason = check(cmd)
    if kind:
        decide(kind, reason)


if __name__ == "__main__":
    main()
