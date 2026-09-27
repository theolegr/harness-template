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
PH=$(cat AGENTS.md $H/GOAL.md $H/FEATURES.json 2>/dev/null | grep -cE '<[A-Za-z][^>]*>' || true)
if [ "${PH:-0}" -gt 0 ]; then
  echo "  ⚠ $PH lines still have <placeholders> — run /harness-init in Claude Code"
fi

echo
echo "── BACKLOG ──"
if [ -f $H/FEATURES.json ]; then
  python3 - <<'PY'
import json, collections, os
d = json.load(open("harness/FEATURES.json"))
fs = d.get("features", [])
arch = json.load(open("harness/FEATURES-DONE.json")).get("features", []) if os.path.exists("harness/FEATURES-DONE.json") else []
c = collections.Counter(f.get("status", "?") for f in fs + arch)
total = len(fs) + len(arch)
done = c.get("done", 0)
stale = [f["id"] for f in fs if f.get("status") in ("done", "cut")]
if stale:
    print(f"  ⚠ still in FEATURES.json: {', '.join(stale)} — archive with ./harness/scripts/feature.sh <id> done")
pct = (done / total * 100) if total else 0
print(f"  {done}/{total} done ({pct:.0f}%)  {dict(c)}")
kinds = collections.Counter(f.get("type", "feature") for f in fs)
if fs:
    print("  open: " + ", ".join(f"{n} {k}" for k, n in sorted(kinds.items())))
cur = [f for f in fs if f.get("status") == "in_progress"]
if cur:
    for f in cur:
        print(f"  ▶ in progress: {f['id']} {f['name']}")
nxt = [f for f in fs if f.get("status") == "todo"]
nxt.sort(key=lambda f: str(f.get("priority", "p9")))
if nxt:
    print(f"  → next: {nxt[0]['id']} {nxt[0]['name']}  (say \"ship the next one\" / /ship)")
blocked = [f for f in fs if f.get("status") == "blocked"]
for f in blocked:
    print(f"  ⛔ blocked: {f['id']} {f['name']}")
PY
else
  echo "  ⚠ $H/FEATURES.json missing"
fi

echo
echo "── GIT ──"
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "  ⚠ not a git repository"
else
  echo "  branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"
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
echo "═══════════════════════════════════════════════"
