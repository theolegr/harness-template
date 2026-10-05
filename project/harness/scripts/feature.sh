#!/usr/bin/env bash
# feature.sh — manage the backlog in harness/FEATURES.json.
#
# Usage:
#   ./harness/scripts/feature.sh <id> <status> [note]
#       status: todo | in_progress | blocked | done | cut
#       note: appended to the item's notes — with blocked, it's the reason
#       (what the item waits on), kept in "blocked" until the item moves on
#   ./harness/scripts/feature.sh add <type> <priority> "<name>" "<acceptance>" [note]
#       type: feature | bug | debt   (ids: F-001 / B-001 / D-001)
#       priority: p0 | p1 | p2 | p3   — prints the new id
#
# The backlog holds features, bugs and tech debt alike: same statuses, same
# loop. done / cut → the item is moved to harness/FEATURES-DONE.json (created on
# first use) with the date. FEATURES.json keeps only the work that's left, so
# reading it at every session boot stays cheap however long the project runs.
set -euo pipefail

SELF="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
cd "$(dirname "$0")/../.."   # project root

if [ $# -lt 2 ]; then
  sed -n '2,17s/^# \{0,1\}//p' "$SELF" >&2; exit 2
fi

python3 - "$@" <<'PY'
import json, sys, datetime, pathlib, re
args = sys.argv[1:]
today = datetime.date.today().isoformat()
active_p, done_p = pathlib.Path("harness/FEATURES.json"), pathlib.Path("harness/FEATURES-DONE.json")
def save(p, d):
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")

d = json.loads(active_p.read_text())

if args[0] == "add":
    if len(args) < 5:
        sys.exit('✗ usage: feature.sh add <feature|bug|debt> <p0-p3> "<name>" "<acceptance>" [note]')
    kind, prio, name, acceptance = args[1:5]
    note = args[5] if len(args) > 5 else ""
    prefix = {"feature": "F", "bug": "B", "debt": "D"}.get(kind)
    if prefix is None:
        sys.exit(f"✗ unknown type: {kind} (feature | bug | debt)")
    if prio not in ("p0", "p1", "p2", "p3"):
        sys.exit(f"✗ unknown priority: {prio} (p0 | p1 | p2 | p3)")
    items = d.get("features", [])
    if done_p.exists():
        items = items + json.loads(done_p.read_text()).get("features", [])
    nums = [int(m.group(1)) for f in items
            if (m := re.fullmatch(prefix + r"-(\d+)", str(f.get("id", ""))))]
    fid = f"{prefix}-{max(nums, default=0) + 1:03d}"
    d.setdefault("features", []).append({
        "id": fid, "type": kind, "name": name, "status": "todo", "priority": prio,
        "acceptance": acceptance, "files": [], "notes": note, "added": today})
    d["updated"] = today
    save(active_p, d)
    print(f"  + {fid} ({kind}, {prio}) {name}")
    sys.exit(0)

fid, status = args[0], args[1]
note = args[2] if len(args) > 2 else ""
if status not in ("todo", "in_progress", "blocked", "done", "cut"):
    sys.exit(f"✗ unknown status: {status}")

f = next((f for f in d.get("features", []) if f.get("id") == fid), None)
if f is None:
    sys.exit(f"✗ {fid} not found in {active_p} (already archived in {done_p}?)")
f["status"] = status
def add_note(text):   # notes are appended, never replaced: they hold decisions and context
    f["notes"] = f"{f['notes']} — {text}" if f.get("notes") else text
if status == "blocked":
    if note and f.get("blocked") and f["blocked"] != note:
        add_note(f"was blocked ({today}): {f['blocked']}")   # a new reason doesn't erase the old one
    if note:
        f["blocked"] = note
elif "blocked" in f:
    add_note(f"was blocked ({today}): {f.pop('blocked')}")
if note and status != "blocked":
    add_note(note)
d["updated"] = today

if status in ("done", "cut"):
    archive = json.loads(done_p.read_text()) if done_p.exists() else {
        "_comment": "Archive of done/cut features, moved here by harness/scripts/feature.sh. Read it only when you need history.",
        "features": []}
    f["closed"] = today
    archive["features"].append(f)
    d["features"].remove(f)
    save(done_p, archive)
    print(f"  ✓ {fid} → {status}, archived in {done_p}")
else:
    print(f"  ✓ {fid} → {status}")
save(active_p, d)
PY
