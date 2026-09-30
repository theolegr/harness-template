#!/usr/bin/env python3
"""Tests for project/harness/scripts/hooks/guard-bash.py.

Run: python3 tests/test_guard_bash.py   (no dependencies; exit code 1 on failure)
Each case is a Bash command line and the expected verdict: "deny", "ask" or None.
"""
import importlib.util
import pathlib
import sys

# no __pycache__ next to the hook: init-harness.sh copies everything under project/
sys.dont_write_bytecode = True

ROOT = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "guard_bash", ROOT / "project/harness/scripts/hooks/guard-bash.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

CASES = [
    # ── still denied (behaviour kept) ──
    ("rm -rf src", "deny"),
    ("rm -fr src", "deny"),
    ("rm -r -f src", "deny"),
    ("rm --recursive --force src", "deny"),
    ("sudo rm -rf /", "deny"),
    ("cd app && rm -rf src", "deny"),
    ("echo ok; rm -rf src", "deny"),
    ("ls\nrm -rf src", "deny"),
    ("ls # a comment\nrm -rf src", "deny"),
    ("rm -rf node_modules src", "deny"),
    ("git push --force", "deny"),
    ("git push -f origin main", "deny"),
    ("git push origin +main", "deny"),
    ("git reset --hard HEAD~1", "deny"),
    ("git clean -fd", "deny"),
    ("git branch -D feature", "deny"),
    ("git checkout .", "deny"),
    # ── now denied: commands handed to a shell (the old guard let these through) ──
    ('bash -c "rm -rf src"', "deny"),
    ('bash -lc "cd app && rm -rf src"', "deny"),
    ("sh -c 'git reset --hard'", "deny"),
    ('eval "rm -rf src"', "deny"),
    ("echo $(rm -rf src)", "deny"),
    ("bash <<'EOF'\nrm -rf src\nEOF", "deny"),
    # ── allowed ──
    ("rm -rf node_modules", None),
    ("rm -rf ./dist/", None),
    ("rm -rf build .next", None),
    ("git push origin feature", None),
    ("git status", None),
    # ── no longer false positives: text inside quotes or heredocs is not a command ──
    ("grep -nEi 'curl |wget |rm -rf|token' SKILL.md", None),
    ('git commit -m "fix: never rm -rf the cache; keep it"', None),
    ('echo "a | rm -rf b"', None),
    ("python3 - <<'EOF'\nprint('rm -rf is dangerous')\nEOF", None),
    ("cat > notes.md <<EOF\nDon't run: rm -rf src\nEOF", None),
    ("cat <<< 'hello'\nls", None),
    ("(cd project/hooks && rm -rf __pycache__)", None),   # was refused: target read as "__pycache__)"
    ("(cd app && rm -rf src)", "deny"),
    # ── ask ──
    ("npx prisma migrate dev", "ask"),
    ("vercel deploy --prod", "ask"),
    ("psql -c 'DROP TABLE users'", "ask"),
    ('git commit -m "add migration"', None),
    ("grep -r deploy .", None),
]


def main():
    failed = 0
    for cmd, want in CASES:
        got, reason = guard.check(cmd)
        ok = got == want
        failed += not ok
        print(f"  {'✓' if ok else '✗'} {want or 'allow':5}  {cmd!r}" + ("" if ok else f"   → got {got} ({reason})"))
    print(f"\n{len(CASES) - failed}/{len(CASES)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
