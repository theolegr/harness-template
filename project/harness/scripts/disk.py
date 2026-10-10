#!/usr/bin/env python3
"""disk.py — when the disk runs low, show what this project could free.

Parallel work fills the disk: every worktree holds its own dependencies and
builds (npm copies node_modules into each one; pnpm shares one store), and
Xcode keeps a DerivedData folder per checkout path that outlives the worktree.

  ./harness/scripts/disk.py          # the report
  ./harness/scripts/disk.py --warn   # the report only when space is low (harness-status.sh)

It reads and suggests, never deletes: the agent shows the list to the user and
runs only what they OK (AGENTS.md §5). Low = under 15% of the disk free, 50 GB
at most; HARNESS_DISK_WARN_GB=<n> sets another threshold (0 = never warn).
A worktree is offered for removal only when it's clean, idle for an hour and
merged into the default branch (a squash-merged branch shows as not merged).
"""
import os
import plistlib
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WARN_PCT, WARN_GB_MAX = 15, 50
IDLE = 60 * 60   # seconds: a worktree git touched more recently is in use
BUDGET = 10      # seconds for all the size measurements (du) together
DERIVED = Path.home() / "Library/Developer/Xcode/DerivedData"
GB = 1024 ** 3


def git(*args, cwd=ROOT):
    """git's output, or None when it fails."""
    # --no-optional-locks: git status refreshes no index (another session may be using it)
    r = subprocess.run(["git", "--no-optional-locks", "-C", str(cwd), *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def human(n):
    if n is None:
        return "size ?"
    return f"{n / GB:.1f} GB" if n >= GB else f"{n / 1024 ** 2:.0f} MB"


def tilde(p):
    """p for display: next to the project as ../name, else with ~ for the home folder."""
    s, home = str(p), str(Path.home())
    if os.path.dirname(os.path.realpath(s)) == os.path.dirname(os.path.realpath(ROOT)):
        return "../" + os.path.basename(s)
    return "~" + s[len(home):] if s.startswith(home + os.sep) else s


def sh(p):
    """p as one shell word, the home folder as $HOME."""
    s, home = str(p), str(Path.home())
    if s.startswith(home + os.sep) and not any(c in s for c in '"$`\\'):
        return f'"$HOME{s[len(home):]}"'
    return shlex.quote(s)


def size(path, deadline):
    """Bytes under path (du), or None when the time budget is spent."""
    left = deadline - time.monotonic()
    if left <= 0:
        return None
    try:
        r = subprocess.run(["du", "-sk", str(path)], capture_output=True, text=True, timeout=left)
        return int(r.stdout.split()[0]) * 1024
    except (subprocess.TimeoutExpired, OSError, ValueError, IndexError):
        return None


def default_branch():
    """Where work gets merged: origin's default branch, else main, else master."""
    ref = git("symbolic-ref", "--short", "refs/remotes/origin/HEAD")   # origin/main
    for b in ([ref.split("/", 1)[1]] if ref and "/" in ref else []) + ["main", "master"]:
        if git("rev-parse", "--verify", "-q", f"refs/heads/{b}") is not None:
            return b
    return None


def worktrees():
    """The repo's other checkouts — not the main one, not this one."""
    out = []
    for line in (git("worktree", "list", "--porcelain") or "").splitlines():
        key, _, val = line.partition(" ")
        if key == "worktree":
            out.append({"path": Path(val)})
        elif out and key:   # HEAD, branch, detached, locked, prunable
            out[-1][key] = val or True
    here = os.path.realpath(git("rev-parse", "--show-toplevel") or ROOT)
    return [w for w in out[1:] if os.path.realpath(w["path"]) != here]


def verdict(w, base):
    """(what the worktree is, the command that would free it — or None)."""
    if "prunable" in w:
        return "folder gone", "git worktree prune"
    if "locked" in w:
        return "locked", None
    p = w["path"]
    gitdir = Path(git("rev-parse", "--absolute-git-dir", cwd=p) or p)
    touched = max((f.stat().st_mtime for f in (gitdir / "index", gitdir / "HEAD", gitdir / "logs/HEAD")
                   if f.exists()), default=0)
    status = git("status", "--porcelain", cwd=p)
    if status is None:
        return "unreadable", None
    if status:
        return "uncommitted changes", None
    if time.time() - touched < IDLE:
        return f"used in the last {IDLE // 60} min", None
    if base is None or "HEAD" not in w:
        return "clean", None
    if git("merge-base", "--is-ancestor", w["HEAD"], base) is None:
        return f"not merged into {base}", None
    return f"merged into {base}, clean, idle", f"git worktree remove {sh(p)}"


def orphan_builds():
    """Xcode DerivedData folders whose project is gone (a removed worktree, a moved project)."""
    out = []
    if not DERIVED.is_dir():
        return out
    for d in sorted(DERIVED.iterdir()):
        try:
            with open(d / "info.plist", "rb") as f:
                ws = plistlib.load(f).get("WorkspacePath")
        except Exception:   # no info.plist (Xcode's shared caches), or not one Xcode wrote
            continue
        if isinstance(ws, str) and ws and not os.path.exists(ws):
            out.append((d, ws))
    return out


def report(warn_only):
    du = shutil.disk_usage(ROOT)
    try:
        limit = float(os.environ["HARNESS_DISK_WARN_GB"]) * GB
    except (KeyError, ValueError):
        limit = min(du.total * WARN_PCT / 100, WARN_GB_MAX * GB)
    low = du.free < limit
    if warn_only and not low:
        return
    print("\n── DISK ──")
    print(f"  {'⚠' if low else '✓'} {human(du.free)} free of {human(du.total)} ({du.free * 100 // du.total}%)"
          + (f" — under {human(limit)}" if low else ""))
    deadline = time.monotonic() + BUDGET
    base, others, builds = default_branch(), worktrees(), orphan_builds()
    if others:
        print("  other worktrees of this repo:")
        for w in others:
            what, cmd = verdict(w, base)
            branch = w.get("branch", "detached").removeprefix("refs/heads/")
            sz = "" if "prunable" in w else f"  {human(size(w['path'], deadline))}"
            print(f"    {tilde(w['path'])}{sz}  {branch} — {what}")
            if cmd:
                print(f"      → {cmd}")
    if builds:
        print("  Xcode builds whose project folder is gone (rebuilt when needed):")
        for d, ws in builds:
            print(f"    {d.name}  {human(size(d, deadline))}  (was {tilde(ws)})")
            print(f"      → rm -rf {sh(d)}")
    if not others and not builds:
        print("  nothing for this project to free: no other worktree, no leftover Xcode build")
    print("  Not checked: caches outside this project (package managers, browsers, simulators, Docker).")
    print("  Nothing was deleted. Show this to the user; run only what they OK.")


if __name__ == "__main__":
    try:
        report("--warn" in sys.argv[1:])
    except Exception as e:   # in the session-start status: never break it
        if "--warn" not in sys.argv[1:]:
            raise SystemExit(f"disk.py: {e}")
