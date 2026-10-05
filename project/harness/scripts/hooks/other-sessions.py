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
/clear — recorded with its end time in harness/.sessions-ended, git-ignored)
and hasn't written since (a resumed one has), the earlier steps of the same
loop.sh run (it exports HARNESS_LOOP). Silent when there's none; never fails
the session.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

WINDOW = 15 * 60   # seconds without a write before a session counts as gone
ENDED = "harness/.sessions-ended"   # "<session id> <epoch it ended>" per line
KEEP = 50          # ended session ids remembered
MARGIN = 10        # seconds: last writes of a session right after its SessionEnd hook


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
    """{session id: when it ended (epoch s)}, oldest first."""
    out = {}
    try:
        lines = Path(here, ENDED).read_text().splitlines()
    except OSError:
        return out
    for line in lines:
        parts = line.split()
        if parts:
            try:
                out[parts[0]] = float(parts[1])
            except (IndexError, ValueError):
                out[parts[0]] = 0.0
    return out


def end(data):
    """SessionEnd: remember when this session ended, so the next one doesn't count it as active."""
    here, me = toplevel(data.get("cwd") or os.getcwd()), data.get("session_id")
    if not here or not isinstance(me, str) or not me or not Path(here, "harness").is_dir():
        return
    gone = ended(here)
    gone.pop(me, None)
    rows = list(gone.items())[-(KEEP - 1):] + [(me, time.time())]
    Path(here, ENDED).write_text("".join(f"{i} {int(t)}\n" for i, t in rows))


def start(data):
    if os.environ.get("HARNESS_LOOP"):
        return   # a step of loop.sh: the steps before it are the same run, not another session
    transcript, me = data.get("transcript_path"), data.get("session_id")
    here = toplevel(data.get("cwd") or os.getcwd())
    if not transcript or not here:
        return
    gone, now, ages = ended(here), time.time(), []
    for p in Path(transcript).parent.glob("*.jsonl"):
        if p.stem == me:
            continue
        try:
            mtime = p.stat().st_mtime
        except OSError:
            continue
        if p.stem in gone and mtime <= gone[p.stem] + MARGIN:
            continue   # ended, and not resumed since (a resumed session keeps its id and writes again)
        if now - mtime <= WINDOW and toplevel(last_cwd(p)) == here:
            ages.append(now - mtime)
    if data.get("source") == "clear" and ages and min(ages) < 60 \
            and not any(now - t < 60 for t in gone.values()):
        ages.remove(min(ages))   # SessionEnd didn't record the conversation just cleared: guess it's the newest
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
