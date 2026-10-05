#!/usr/bin/env bash
# harness-check.sh — the verification instrument.
# Runs the checks that prove the project is healthy. Exit != 0 means the loop
# must NOT proceed.
set -uo pipefail

# macOS: keep the Mac awake while the checks run — a sleep mid-run fails them for
# nothing. (Idle sleep only: closing the lid on battery still sleeps.)
if [ "$(uname)" = Darwin ] && [ -z "${HARNESS_AWAKE:-}" ] && command -v caffeinate >/dev/null 2>&1; then
  export HARNESS_AWAKE=1
  exec caffeinate -i bash "$0" "$@"
fi

cd "$(dirname "$0")/../.."   # project root
H=harness

# ── Project commands (filled by /harness-init; edit freely) ──
# Leave empty to auto-detect (package.json scripts, ruff, pytest).
LINT_CMD=""
TEST_CMD=""

# package.json scripts run with the package manager its lockfile names (npm if none)
PM=npm
for lock in pnpm-lock.yaml:pnpm yarn.lock:yarn bun.lock:bun bun.lockb:bun; do
  if [ -f "${lock%%:*}" ]; then PM="${lock##*:}"; break; fi
done
RUN="$PM run"; [ "$PM" = npm ] && RUN="npm run --silent"

FAIL=0
step() { printf "\n── %s ──\n" "$1"; }

# ── 1. Harness integrity: required files exist ──
step "Harness files"
for f in AGENTS.md CLAUDE.md \
         $H/GOAL.md $H/STATE.md $H/FEATURES.json $H/EVAL.md $H/PLAN.md $H/DECISIONS.md \
         $H/guide/BOOT.md $H/guide/SOUL.md $H/guide/TESTING.md $H/guide/LOOP.md \
         $H/guide/MEMORY.md $H/guide/SKILLS.md; do
  if [ -f "$f" ]; then printf "  ✓ %s\n" "$f"; else printf "  ✗ %s MISSING\n" "$f"; FAIL=1; fi
done

# ── 2. FEATURES.json is valid JSON + schema-ish ──
step "Feature tracker"
if [ -f $H/FEATURES.json ]; then
  if python3 -c "
import json,sys
d=json.load(open('$H/FEATURES.json'))
assert 'features' in d, 'no features key'
for f in d['features']:
    for k in ('id','name','status'):
        assert k in f, f'feature missing {k}: {f}'
print(f'  ✓ valid — {len(d[\"features\"])} features')
"; then :; else echo "  ✗ $H/FEATURES.json invalid"; FAIL=1; fi
else
  echo "  ✗ $H/FEATURES.json missing"; FAIL=1
fi

# ── 3. Lint / typecheck (configure per project) ──
step "Lint / typecheck"
if [ -n "$LINT_CMD" ]; then
  echo "  \$ $LINT_CMD"; bash -c "$LINT_CMD" || FAIL=1
elif [ -f package.json ] && grep -q '"lint"' package.json 2>/dev/null; then
  echo "  \$ $RUN lint"; $RUN lint || FAIL=1
elif [ -f pyproject.toml ] || [ -f requirements.txt ]; then
  if command -v ruff >/dev/null 2>&1; then
    ruff check . || FAIL=1
  else
    echo "  ⚠ ruff not installed — lint skipped (install it or set your own lint cmd)"
  fi
else
  echo "  (no linter configured — set LINT_CMD in harness/scripts/harness-check.sh)"
fi

# ── 4. Tests (configure per project) ──
step "Tests"
if [ -n "$TEST_CMD" ]; then
  echo "  \$ $TEST_CMD"; bash -c "$TEST_CMD" || FAIL=1
elif [ -f package.json ] && grep -q '"test"' package.json 2>/dev/null; then
  echo "  \$ $RUN test"; $RUN test || FAIL=1   # `run test`: `bun test` would skip the script
elif [ -f pytest.ini ] || [ -f pyproject.toml ]; then
  if python3 -c 'import pytest' 2>/dev/null; then
    python3 -m pytest -q; rc=$?
    # 5 = no tests collected: not a failure for a fresh project
    if [ "$rc" -ne 0 ] && [ "$rc" -ne 5 ]; then FAIL=1; fi
  else
    echo "  ✗ pytest not installed — cannot verify"; FAIL=1
  fi
else
  echo "  ⚠ no tests configured — this check proves nothing about the code yet."
  echo "    Normal before the first feature; after it, set TEST_CMD in harness/scripts/harness-check.sh"
fi

# ── 5. No secrets committed ──
step "Secret scan"
if git rev-parse --git-dir >/dev/null 2>&1; then
  HITS=$(git grep -nIE '(api[_-]?key|secret|password|token)\s*[:=]\s*["'"'"'][A-Za-z0-9_\-]{16,}' -- ':!*.example' ':!*.md' 2>/dev/null | head -20 || true)
  if [ -n "$HITS" ]; then echo "  ✗ possible secrets:"; echo "$HITS" | sed 's/^/    /'; FAIL=1; else echo "  ✓ none found"; fi
else
  echo "  (not a git repo)"
fi

printf "\n═══════════════════════════════════════════════\n"
if [ "$FAIL" -eq 0 ]; then echo "  ✓ HARNESS CHECK PASSED"; else echo "  ✗ HARNESS CHECK FAILED"; fi
printf "═══════════════════════════════════════════════\n"
exit $FAIL
