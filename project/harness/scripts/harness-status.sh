#!/usr/bin/env bash
# harness-status.sh — print the current harness state at a glance.
# Machine-readable where possible; this is the "show state, don't describe it" instrument.
set -euo pipefail

cd "$(dirname "$0")/../.."   # project root
H=harness

echo "═══════════════════════════════════════════════"
echo "  PROJECT HARNESS — $(basename "$PWD")"
echo "═══════════════════════════════════════════════"

echo
echo "── GOAL ──"
if [ -f $H/GOAL.md ]; then
  awk '/^## Target/{f=1;next} f&&/^>/{next} f&&NF{print "  " $0; exit}' $H/GOAL.md || echo "  (not set)"
else
  echo "  ⚠ $H/GOAL.md missing"
fi
# placeholders still unfilled → the interview hasn't been run (or was skipped)
PH=$(python3 -c 'import sys; sys.dont_write_bytecode = True; sys.path.insert(0, "harness/scripts")
from state import placeholder_lines; print(placeholder_lines())' 2>/dev/null || echo 0)
if [ "${PH:-0}" -gt 0 ]; then
  echo "  ⚠ $PH lines still have <placeholders> — run /harness-init in Claude Code"
fi

echo
echo "── BACKLOG ──"
if [ -f $H/FEATURES.json ]; then
  python3 - <<'PY'
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, "harness/scripts")
from state import backlog, update_warnings   # same reading as the dashboard
b = backlog()
for w in b["warnings"] + update_warnings():
    print(f"  ⚠ {w}")
if b["stale"]:
    print(f"  ⚠ still in FEATURES.json: {', '.join(b['stale'])} — archive with ./harness/scripts/feature.sh <id> done")
print(f"  {b['done']}/{b['total']} done ({b['percent']}%)  {b['counts']}")
if b["open_types"]:
    print("  open: " + ", ".join(f"{n} {k}" for k, n in sorted(b["open_types"].items())))
for f in b["in_progress"]:
    print(f"  ▶ in progress: {f['id']} {f['name']}")
if b["todo"]:
    print(f"  → next: {b['todo'][0]['id']} {b['todo'][0]['name']}  (say \"ship the next one\" / /ship)")
for f in b["blocked"]:
    why = f" — {f['blocked'][:90]}" if f.get("blocked") else ""
    print(f"  ⛔ blocked: {f['id']} {f['name'][:60]}{why}")
PY
else
  echo "  ⚠ $H/FEATURES.json missing"
fi

echo
echo "── GIT ──"
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "  ⚠ not a git repository"
else
  echo "  branch: $(git symbolic-ref --short -q HEAD 2>/dev/null || git rev-parse --short HEAD 2>/dev/null || echo '?')"
  # other checkouts of this repo (parallel sessions, AGENTS.md §5)
  git worktree list 2>/dev/null | grep -vF "$(git rev-parse --show-toplevel) " | tr -s ' ' | sed 's/^/  worktree: /' || true
  git log --oneline -5 2>/dev/null | sed 's/^/  /' || true
  if [ -n "$(git status --porcelain)" ]; then
    echo "  ⚠ uncommitted changes:"
    git status --short | sed 's/^/    /'
  else
    echo "  ✓ working tree clean"
  fi
fi

echo
echo "── FILES ──"
for f in AGENTS.md CLAUDE.md $H/GOAL.md $H/STATE.md $H/FEATURES.json $H/EVAL.md $H/PLAN.md $H/DECISIONS.md $H/guide/BOOT.md; do
  if [ -f "$f" ]; then
    printf "  ✓ %s\n" "$f"
  else
    printf "  ✗ %s  (missing)\n" "$f"
  fi
done

echo
echo "  dashboard: ./harness/scripts/dashboard.py --open   ·   as JSON: ./harness/scripts/state.py"
echo "═══════════════════════════════════════════════"
