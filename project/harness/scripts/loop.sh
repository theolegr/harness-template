#!/usr/bin/env bash
# loop.sh — the outer loop engine.
#
# Design: this script orchestrates, it does not think. It discovers work,
# dispatches ONE item to an agent, then hands verification to a SEPARATE agent.
# The maker/checker split is enforced here, not by convention.
#
# This is the UNATTENDED way to run the loop (cron, overnight). When you drive
# the project from a chat, use the ship skill instead (/ship): same loop, but
# you validate the plan and answer the agent's questions.
#
# Usage:
#   ./harness/scripts/loop.sh status     # show loop state
#   ./harness/scripts/loop.sh once       # run a single iteration
#   ./harness/scripts/loop.sh run        # run until stop condition (bounded)
#
# Configure AGENT_CMD (required) and VERIFIER_CMD (strongly recommended).
# With Claude Code (non-interactive runs need an explicit permission mode —
# without one, every edit is refused):
#   AGENT_CMD="claude -p --model opus --permission-mode acceptEdits --max-budget-usd 5"
#   VERIFIER_CMD="claude -p --agent reviewer --permission-mode dontAsk"
# The .claude/settings.json hooks still apply: the Bash guard refuses
# destructive commands, and the Stop hook makes the agent fix a red check.
# Commands the agent must run (tests, lint) go in permissions.allow there.
#
# The reviewer must not touch the working tree: if it does, the review fails.
# Its non-blocking findings (FINDING: lines) are added to the backlog as bug /
# debt items (feature.sh add), whatever the verdict.
#
# Branches: each feature runs on loop/<id>, branched from wherever the previous
# iteration left off — so features stack (F-002 builds on F-001). Nothing is
# merged into your main branch: review the last loop/* branch and merge it.
#
# On failure: the attempt is committed on its branch as `wip(<id>)`, the loop
# returns to the base branch, marks the feature `blocked`, and STOPS. It never
# retries on top of broken code. Unblock by setting the status back to `todo`:
# the next attempt starts fresh, and the failed one is kept, renamed
# loop/<id>-failed-<timestamp>.
set -uo pipefail

cd "$(dirname "$0")/../.."   # project root

MAX_ITER="${MAX_ITER:-5}"
AGENT_CMD="${AGENT_CMD:-}"          # e.g. "claude -p --model opus --permission-mode acceptEdits"
VERIFIER_CMD="${VERIFIER_CMD:-}"    # MUST be a different agent/command (fresh context)
LOG="harness/.loop.log"
STOP_FILE="harness/.loop.stop"

VERDICT_OUT=""                      # last reviewer answer (for its FINDING lines)

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" | tee -a "$LOG"; }

# Fingerprint of the working tree (to prove the reviewer changed nothing).
tree_fp() {
  local x=':!harness/.loop.log'
  { git status --porcelain -- . "$x"; git diff HEAD -- . "$x"
    git ls-files -o --exclude-standard -- . "$x" | while IFS= read -r f; do git hash-object "$f"; done
  } | git hash-object --stdin
}

# Stage everything except the loop's own runtime files.
commit_all() {
  git add -A && git reset -q -- "$LOG" "$STOP_FILE" 2>/dev/null
  git commit -qm "$1"
}

discover() {
  # Print the next work item as "ID|name|priority", or nothing if none.
  # in_progress items come first (finish what was started), then by priority.
  python3 - <<'PY'
import json
try:
    d = json.load(open("harness/FEATURES.json"))
except Exception:
    raise SystemExit(0)
order = {"p0": 0, "p1": 1, "p2": 2, "p3": 3, "p9": 9}
cands = [f for f in d.get("features", []) if f.get("status") in ("in_progress", "todo")]
cands.sort(key=lambda f: (f.get("status") != "in_progress", order.get(str(f.get("priority")), 9)))
if cands:
    f = cands[0]
    print(f"{f['id']}|{f['name']}|{f.get('priority','')}")
PY
}

acceptance() {
  python3 - "$1" <<'PY'
import json, sys
for f in json.load(open("harness/FEATURES.json")).get("features", []):
    if f.get("id") == sys.argv[1]:
        print(f.get("acceptance", ""))
PY
}

record_findings() {
  # record_findings <id> — add the reviewer's FINDING lines to the backlog
  local id="$1" line kind prio title check trim='s/^[[:space:]]*//;s/[[:space:]]*$//'
  printf '%s\n' "$VERDICT_OUT" | grep -E '^[-* `]*FINDING:' | head -5 | while IFS= read -r line; do
    line="${line#*FINDING:}"; line="${line%\`}"
    IFS='|' read -r kind prio title check <<<"$line"
    kind="$(sed "$trim" <<<"$kind")"; prio="$(sed "$trim" <<<"$prio")"
    title="$(sed "$trim" <<<"$title")"; check="$(sed "$trim" <<<"$check")"
    ./harness/scripts/feature.sh add "$kind" "$prio" "$title" "$check" "from review of $id" \
      || log "  ⚠ could not record finding: $line"
  done | tee -a "$LOG"
}

note_blocker() {
  # note_blocker <id> <reason> — add a row to STATE.md "Blockers / risks"
  python3 - "$1" "$2" <<'PY'
import sys, pathlib, datetime
fid, reason = sys.argv[1], sys.argv[2].replace("|", "/")
p = pathlib.Path("harness/STATE.md")
if not p.exists():
    raise SystemExit(0)
lines = p.read_text().splitlines()
try:
    h = next(i for i, l in enumerate(lines) if l.startswith("## Blockers"))
    sep = next(i for i in range(h, len(lines)) if lines[i].startswith("|---"))
except StopIteration:
    raise SystemExit(0)
row = f"| {fid}: {reason} ({datetime.date.today()}) | loop stopped | human | open — attempt on branch loop/{fid} |"
lines.insert(sep + 1, row)
p.write_text("\n".join(lines) + "\n")
PY
}

set_status() {
  # set_status <id> <status> [note] — done/cut features get archived
  ./harness/scripts/feature.sh "$@"
}

preflight() {
  if [ -z "$AGENT_CMD" ]; then
    echo "✗ AGENT_CMD is not set — refusing to run (nothing would be built, yet features would be marked done)." >&2
    echo "  e.g. AGENT_CMD=\"claude -p\" VERIFIER_CMD=\"claude -p\" $0 once" >&2
    return 1
  fi
  if ! git rev-parse --git-dir >/dev/null 2>&1; then
    echo "✗ not a git repository — the loop needs branches and commits." >&2
    return 1
  fi
  if [ -z "$VERIFIER_CMD" ]; then
    log "⚠ VERIFIER_CMD unset — verification is harness-check.sh only (no independent reviewer)"
  fi
  case "$AGENT_CMD" in
    claude*)
      case "$AGENT_CMD" in
        *--permission-mode*|*--dangerously-skip-permissions*) ;;
        *) echo "✗ AGENT_CMD runs claude without --permission-mode — in -p mode every edit would be refused." >&2
           echo "  e.g. AGENT_CMD=\"claude -p --permission-mode acceptEdits\"" >&2
           return 1;;
      esac;;
  esac
}

check_stop() {
  # Return 0 (stop) if a stop condition is met.
  # 1) Goal metric met?  -> you must wire this to your eval
  # 2) No work left?
  # 3) Budget exhausted? (MAX_ITER)
  if [ -f "$STOP_FILE" ]; then log "STOP: $STOP_FILE present"; return 0; fi
  if [ -z "$(discover)" ]; then log "STOP: no work items left"; return 0; fi
  return 1
}

fail_iteration() {
  # fail_iteration <id> <base-branch> <reason>
  local id="$1" base="$2" reason="$3"
  log "  ✗ $reason — keeping the attempt on loop/$id, marking $id blocked"
  commit_all "wip($id): failed verification — $reason" 2>&1 | tee -a "$LOG" || true
  git checkout -q "$base"
  record_findings "$id"
  note_blocker "$id" "$reason"
  set_status "$id" blocked "loop: $reason on $(date +%F) — attempt kept on branch loop/$id" | tee -a "$LOG"
  commit_all "chore(loop): $id blocked — $reason" 2>&1 | tee -a "$LOG" || true
}

run_once() {
  local item id rest name base start
  VERDICT_OUT=""
  item="$(discover)"
  if [ -z "$item" ]; then log "nothing to do"; return 1; fi
  id="${item%%|*}"; rest="${item#*|}"; name="${rest%%|*}"
  base="$(git rev-parse --abbrev-ref HEAD)"

  log "=== ITERATION: $id — $name ==="
  set_status "$id" in_progress | tee -a "$LOG"   # an interrupted run shows what it was on

  # 1. PLAN  (separate phase, hard gate)
  log "[1/5] plan"
  $AGENT_CMD "Read AGENTS.md and harness/guide/BOOT.md. Then write harness/PLAN.md for feature $id: $name. Ground it in real files that exist. Do not start implementing." 2>&1 | tee -a "$LOG"

  # 2. EXECUTE (isolated branch)
  log "[2/5] execute on branch loop/$id"
  if git show-ref --verify -q "refs/heads/loop/$id"; then
    # a previous attempt (blocked, then unblocked): keep it, start fresh
    local old="loop/$id-failed-$(date +%Y%m%d-%H%M%S)"
    git branch -m "loop/$id" "$old" && log "  previous attempt kept as $old"
  fi
  git checkout -q -b "loop/$id"
  start="$(git rev-parse HEAD)"
  $AGENT_CMD "Execute harness/PLAN.md for $id. One feature only. Commit when done." 2>&1 | tee -a "$LOG"

  # 3. VERIFY — the instrument first, then a SEPARATE agent (maker/checker split)
  log "[3/5] verify"
  if ! ./harness/scripts/harness-check.sh >>"$LOG" 2>&1; then
    if [ -n "$VERIFIER_CMD" ]; then
      $VERIFIER_CMD "harness-check failed for $id. Diagnose the root cause and report only. Do not fix." 2>&1 | tee -a "$LOG"
    fi
    fail_iteration "$id" "$base" "harness-check failed"
    return 1
  fi
  log "  ✓ harness-check passed"

  if [ -n "$VERIFIER_CMD" ]; then
    local before; before="$(tree_fp)"
    VERDICT_OUT="$($VERIFIER_CMD "You are the reviewer, not the author. Review the changes since commit $start (uncommitted ones included) for feature $id: $name. Acceptance criterion: $(acceptance "$id"). Do not modify any file. End your answer with exactly one line: VERDICT: PASS or VERDICT: FAIL. List non-blocking findings as FINDING: lines, as your instructions say." 2>&1)"
    printf '%s\n' "$VERDICT_OUT" | tee -a "$LOG"
    if [ "$(tree_fp)" != "$before" ]; then
      fail_iteration "$id" "$base" "reviewer modified the working tree (maker/checker split broken)"
      return 1
    fi
    if ! printf '%s\n' "$VERDICT_OUT" | grep -q '^VERDICT: PASS'; then
      fail_iteration "$id" "$base" "reviewer did not pass it"
      return 1
    fi
    log "  ✓ reviewer passed"
  fi

  # 4. RECORD
  log "[4/5] record"
  record_findings "$id"
  set_status "$id" done | tee -a "$LOG"
  commit_all "feat($id): $name" 2>&1 | tee -a "$LOG" || log "  (nothing to commit)"

  # 5. MEASURE — keep the state files true for the next session
  log "[5/5] measure — STATE.md, GOAL.md metric, EVAL.md"
  $AGENT_CMD "Feature $id ($name) was just shipped and committed by the outer loop. Update the state files only, no code: harness/STATE.md (Now, Next from harness/FEATURES.json, Recently done, a session-log entry dated today, any new blocker); if $id moved the metric in harness/GOAL.md, update its Current value and add a row to harness/EVAL.md Score history. Do not commit." 2>&1 | tee -a "$LOG"
  commit_all "chore($id): update state after loop iteration" 2>&1 | tee -a "$LOG" || log "  (state unchanged)"
  log "=== ITERATION COMPLETE: $id ==="
  return 0
}

case "${1:-status}" in
  status)
    echo "LOOP status for $(basename "$PWD")"
    echo "next item: $(discover || echo none)"
    echo "log: $LOG"
    [ -f "$LOG" ] && tail -5 "$LOG"
    ;;
  once)
    preflight || exit 1
    run_once
    ;;
  run)
    preflight || exit 1
    i=0
    while [ "$i" -lt "$MAX_ITER" ]; do
      if check_stop; then break; fi
      i=$((i+1))
      log "───── outer loop iteration $i/$MAX_ITER ─────"
      if ! run_once; then
        log "iteration $i failed — stopping (a human needs to look)"
        exit 1
      fi
      sleep 1
    done
    log "loop finished after $i iteration(s)"
    ;;
  *)
    echo "usage: $0 {status|once|run}" >&2; exit 2;;
esac
