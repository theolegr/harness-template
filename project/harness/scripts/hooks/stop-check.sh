#!/usr/bin/env bash
# stop-check.sh — Claude Code "Stop" hook: the agent can't finish on a red check.
#
# Runs harness-check.sh when the agent tries to stop. On failure it exits 2,
# which sends the output back to the agent and makes it keep working.
#
# - Skipped when the working tree is clean, or unchanged since the last pass
#   (cached in harness/.check.ok) — chatting doesn't re-run the tests.
# - Blocks at most once in a row (stop_hook_active): if the agent still can't
#   fix it, it stops and says so instead of looping forever.
# - Checks the session's own checkout: the worktree it moved into, if any
#   (AGENTS.md §5), not the main folder another session may be changing.
# - Off switch: HARNESS_STOP_CHECK=0.
set -uo pipefail

[ "${HARNESS_STOP_CHECK:-1}" = "0" ] && exit 0
INPUT="$(cat)"
field() { printf '%s' "$INPUT" | python3 -c 'import json,sys
try: v = json.load(sys.stdin).get(sys.argv[1])
except Exception: v = None
print("" if v is None else str(v).lower() if isinstance(v, bool) else v)' "$1"; }
[ "$(field stop_hook_active)" = "true" ] && exit 0

CWD="$(field cwd)"
ROOT="$([ -n "$CWD" ] && git -C "$CWD" rev-parse --show-toplevel 2>/dev/null)"
cd "${ROOT:-${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../../..}}" || exit 0
git rev-parse --git-dir >/dev/null 2>&1 || exit 0
[ -x harness/scripts/harness-check.sh ] || exit 0   # a folder without the harness: nothing to check

# Fingerprint of the working tree, ignoring the harness runtime files.
IGNORE=(':!harness/.loop.log' ':!harness/.loop.stop' ':!harness/.check.ok')
STATUS="$(git status --porcelain -- . "${IGNORE[@]}")"
[ -z "$STATUS" ] && exit 0
FP="$({ printf '%s\n' "$STATUS"; git diff HEAD -- . "${IGNORE[@]}" 2>/dev/null
        git ls-files -o --exclude-standard -- . "${IGNORE[@]}" | while IFS= read -r f; do git hash-object "$f"; done
      } | git hash-object --stdin)"
[ "$(cat harness/.check.ok 2>/dev/null)" = "$FP" ] && exit 0

if OUT="$(./harness/scripts/harness-check.sh 2>&1)"; then
  printf '%s\n' "$FP" > harness/.check.ok
  exit 0
fi

{
  echo "harness-check.sh FAILED — you can't stop on a red check (harness/guide/TESTING.md)."
  echo "Fix the cause, or if it can't be fixed now, say so plainly and why."
  echo
  printf '%s\n' "$OUT" | tail -40
} >&2
exit 2
