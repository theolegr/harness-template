#!/usr/bin/env python3
"""other-sessions.py — Claude Code "SessionStart" hook: warn when another session works in this folder.

Two sessions in one checkout clobber each other: one switches branch under the
other, commits its half-done files, overwrites its build output. AGENTS.md §5
says: another session active here and you'll change files → your own worktree.

"Active" = another Claude Code transcript of this project written to in the
last 15 minutes, whose latest working directory is this same checkout (a
session that moved into a worktree doesn't count). Not counted either: the
conversation a /clear just closed, and the earlier steps of the same loop.sh
run (it exports HARNESS_LOOP). Silent when there's none; never fails the
session start.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

WINDOW = 15 * 60   # seconds without a write before a session counts as gone


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


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    if os.environ.get("HARNESS_LOOP"):
        return   # a step of loop.sh: the steps before it are the same run, not another session
    transcript, me = data.get("transcript_path"), data.get("session_id")
    here = toplevel(data.get("cwd") or os.getcwd())
    if not transcript or not here:
        return
    now, ages = time.time(), []
    for p in Path(transcript).parent.glob("*.jsonl"):
        if p.stem == me:
            continue
        try:
            age = now - p.stat().st_mtime
        except OSError:
            continue
        if age <= WINDOW and toplevel(last_cwd(p)) == here:
            ages.append(age)
    if data.get("source") == "clear" and ages:
        ages.remove(min(ages))   # /clear: the newest one is the conversation just cleared
    if not ages:
        return
    n, last = len(ages), int(min(ages) // 60)
    repo = os.path.basename(here)
    print(f"⚠ OTHER SESSIONS — {n} other agent session{'s' if n > 1 else ''} wrote from this folder "
          f"in the last {WINDOW // 60} min (latest {last} min ago).\n"
          f"  Before changing files, work in your own worktree (AGENTS.md §5):\n"
          f"    git worktree add ../{repo}-<topic> -b <branch>   then, in Claude Code, EnterWorktree with that path\n"
          f"  If the user says that session is closed, stay here.")


if __name__ == "__main__":
    try:
        main()
    except Exception:   # a hook must never break the session start
        pass
