#!/usr/bin/env python3
"""other-sessions.py — Claude Code hook: warn when another session works in this folder.

Two sessions in one checkout clobber each other: one switches branch under the
other, commits its half-done files, overwrites its build output. AGENTS.md §5
says: another session active here and you'll change files → your own worktree.

  SessionStart:  other-sessions.py        → the warning, or nothing
  SessionEnd:    other-sessions.py end    → records the session as ended

"Active" = another Claude Code transcript of this project written to in the
last 15 minutes, whose latest working directory is this same checkout. Not
counted: a session that moved into a worktree, a session that ended (exit,
/clear — recorded in harness/.sessions-ended, git-ignored), the earlier steps
of the same loop.sh run (it exports HARNESS_LOOP). Silent when there's none;
never fails the session.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

WINDOW = 15 * 60   # seconds without a write before a session counts as gone
ENDED = "harness/.sessions-ended"
KEEP = 50          # ended session ids remembered


def toplevel(path):
    """The checkout (main folder or worktree) that path belongs to, or None."""
    if not path or not os.path.isdir(path):
        return None
    r = subprocess.run(["git", "-C", path, "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return os.path.realpath(r.stdout.strip()) if r.returncode == 0 else None


def last_cwd(transcript):
    """The working directory recorded in the transcript's latest entries."""
    try:
        with open(transcript, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - 65536))
            lines = f.read().decode("utf-8", "ignore").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        try:
            cwd = json.loads(line).get("cwd")
        except (ValueError, AttributeError):
            continue
        if cwd:
            return cwd
    return None


def ended(here):
    try:
        return Path(here, ENDED).read_text().split()
    except OSError:
        return []


def end(data):
    """SessionEnd: remember this session ended, so the next one doesn't count it as active."""
    here, me = toplevel(data.get("cwd") or os.getcwd()), data.get("session_id")
    if not here or not me or not Path(here, "harness").is_dir():
        return
    ids = [i for i in ended(here) if i != me][-(KEEP - 1):] + [me]
    Path(here, ENDED).write_text("\n".join(ids) + "\n")


def start(data):
    if os.environ.get("HARNESS_LOOP"):
        return   # a step of loop.sh: the steps before it are the same run, not another session
    transcript, me = data.get("transcript_path"), data.get("session_id")
    here = toplevel(data.get("cwd") or os.getcwd())
    if not transcript or not here:
        return
    gone, now, ages = set(ended(here)), time.time(), []
    for p in Path(transcript).parent.glob("*.jsonl"):
        if p.stem == me or p.stem in gone:
            continue
        try:
            age = now - p.stat().st_mtime
        except OSError:
            continue
        if age <= WINDOW and toplevel(last_cwd(p)) == here:
            ages.append(age)
    if data.get("source") == "clear" and ages and min(ages) < 60:
        ages.remove(min(ages))   # fallback if SessionEnd didn't record it: the conversation just cleared
    if not ages:
        return
    n, last = len(ages), int(min(ages) // 60)
    repo = os.path.basename(here)
    print(f"⚠ OTHER SESSIONS — {n} other agent session{'s' if n > 1 else ''} wrote from this folder "
          f"in the last {WINDOW // 60} min (latest {last} min ago) and hasn't ended.\n"
          f"  Before changing files, work in your own worktree (AGENTS.md §5):\n"
          f"    git worktree add ../{repo}-<topic> -b <branch>   then, in Claude Code, EnterWorktree with that path\n"
          f"  If the user says that session is closed, stay here.")


if __name__ == "__main__":
    try:
        payload = json.load(sys.stdin)
        if isinstance(payload, dict):
            (end if sys.argv[1:] == ["end"] else start)(payload)
    except Exception:   # a hook must never break the session
        pass
