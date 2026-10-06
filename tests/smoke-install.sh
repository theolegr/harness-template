#!/usr/bin/env bash
# smoke-install.sh — install the harness on a throwaway project, run its scripts,
# then --update it. Exit code 1 on the first failure.
#
# Run: bash tests/smoke-install.sh   (needs git and python3; no Claude, no network)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
DEMO="$WORK/demo"

# a git identity for the first commit, without touching the user's config
export GIT_AUTHOR_NAME=smoke GIT_AUTHOR_EMAIL=smoke@example.com
export GIT_COMMITTER_NAME=smoke GIT_COMMITTER_EMAIL=smoke@example.com

step() { printf '\n── %s\n' "$1"; }

step "install"
"$ROOT/init-harness.sh" --no-interview --name "Smoke Test" --type cli "$DEMO"
cd "$DEMO"
for f in AGENTS.md CLAUDE.md .claude/settings.json harness/GOAL.md harness/FEATURES.json \
         harness/scripts/harness-check.sh harness/scripts/hooks/guard-bash.py; do
  [ -e "$f" ] || { echo "✗ missing after install: $f"; exit 1; }
done
git log --oneline | grep -q "chore: add project harness" || { echo "✗ no first commit"; exit 1; }

step "scripts"
./harness/scripts/harness-status.sh >/dev/null
./harness/scripts/harness-check.sh >/dev/null
python3 harness/scripts/state.py >/dev/null
python3 harness/scripts/dashboard.py >/dev/null
./harness/scripts/feature.sh add feature p1 "Smoke feature" "it exists" >/dev/null
python3 - <<'EOF'
import json
items = json.load(open("harness/FEATURES.json"))
items = items.get("features", items) if isinstance(items, dict) else items
assert any(i.get("name") == "Smoke feature" for i in items), "feature.sh add did not land"
EOF

step "update (no changes on either side → nothing to merge)"
git add -A && git commit -qm "smoke: backlog item"
"$ROOT/init-harness.sh" --update "$DEMO"
if find . -name '*.harness-new' -not -path './harness/template/*' | grep -q .; then
  echo "✗ --update left .harness-new files on an untouched project"; exit 1
fi

printf '\n✓ smoke install passed\n'
