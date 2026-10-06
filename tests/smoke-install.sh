#!/usr/bin/env bash
# smoke-install.sh — install the harness on throwaway projects, run its scripts,
# then --update one with a modified template. Exit code 1 on the first failure;
# the failing step's output is printed and the work dir kept.
#
# Run: bash tests/smoke-install.sh   (needs git and python3; no Claude, no network)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rc=$?; if [ $rc -eq 0 ]; then rm -rf "$WORK"; else echo "  (work dir kept: $WORK)"; fi' EXIT

# hermetic git: the developer's config (signing, hooks, default branch…) stays out
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
export GIT_AUTHOR_NAME=smoke GIT_AUTHOR_EMAIL=smoke@example.com
export GIT_COMMITTER_NAME=smoke GIT_COMMITTER_EMAIL=smoke@example.com

step() { printf '\n── %s\n' "$1"; }
fail() { echo "✗ $*"; exit 1; }
# run <cmd…>: quiet when it works, its output when it doesn't
run() { "$@" >"$WORK/out.log" 2>&1 || { cat "$WORK/out.log"; fail "$*"; }; }
has() { grep -qF -- "$2" "$1" || fail "$1 doesn't contain: $2"; }
lacks() { if grep -qF -- "$2" "$1"; then fail "$1 still contains: $2"; fi; }
# edit <file> <python expression on s>: portable in-place edit (no sed -i)
edit() { python3 -c 'import sys, pathlib; p = pathlib.Path(sys.argv[1]); s = p.read_text(); p.write_text(eval(sys.argv[2]))' "$1" "$2"; }

# ── 1. A folder that isn't a git repo: init, stage the harness only, no commit
step "install in a new folder"
DEMO="$WORK/demo"
mkdir -p "$DEMO" && echo "SECRET=1" > "$DEMO/.env"
run "$ROOT/init-harness.sh" --no-interview --name "Smoke Test" --type cli "$DEMO"
cd "$DEMO"
[ -z "$(git rev-list --all)" ] || fail "the install made a commit"
STAGED="$(git diff --cached --name-only)"
for f in AGENTS.md CLAUDE.md .gitignore .claude/settings.json harness/FEATURES.json harness/scripts/hooks/guard-bash.py; do
  printf '%s\n' "$STAGED" | grep -qxF "$f" || fail "not staged after install: $f"
done
if printf '%s\n' "$STAGED" | grep -qxF .env; then fail ".env was staged"; fi
rm .env
has AGENTS.md "# AGENTS.md — Smoke Test"
has AGENTS.md "**Type**: cli"
python3 -c 'import json; json.load(open(".claude/settings.json"))' || fail ".claude/settings.json is not valid JSON"

step "scripts, before the first commit"
run ./harness/scripts/harness-status.sh
run ./harness/scripts/harness-check.sh
run python3 harness/scripts/state.py
run python3 harness/scripts/dashboard.py

step "first commit (the interview's), a backlog item"
git commit -qm "chore: initialise project harness"
run ./harness/scripts/feature.sh add feature p1 "Smoke feature" "it exists"
python3 -c 'import json, sys; sys.exit(not any(i["name"] == "Smoke feature" for i in json.load(open("harness/FEATURES.json"))["features"]))' \
  || fail "feature.sh add did not land in FEATURES.json"
git add harness/FEATURES.json && git commit -qm "smoke: backlog item"

# ── 2. Inside an existing repo: a worktree, a package of a monorepo
step "install in a worktree and in a repo's subfolder"
mkdir -p "$WORK/mono" && cd "$WORK/mono" && git init -q && echo a > a.txt && git add a.txt && git commit -qm init
git worktree add -q "$WORK/mono-wt" -b wt
echo "SECRET=1" > "$WORK/mono-wt/.env"
run "$ROOT/init-harness.sh" --no-interview "$WORK/mono-wt"
cd "$WORK/mono-wt"
[ "$(git rev-list --count HEAD)" = 1 ] || fail "the install committed in a worktree"
[ -z "$(git diff --cached --name-only)" ] || fail "the install staged files in a worktree"
mkdir -p "$WORK/mono/packages/app"
run "$ROOT/init-harness.sh" --no-interview "$WORK/mono/packages/app"
[ ! -e "$WORK/mono/packages/app/.git" ] || fail "the install created a nested repo in a subfolder"

# ── 3. --update with the same template: nothing to do
step "update, same template"
cd "$DEMO"
run "$ROOT/init-harness.sh" --update "$DEMO"
[ -z "$(git status --porcelain)" ] || { git status --short; fail "--update changed an untouched project"; }

# ── 4. --update with a new template version
step "update, new template"
TPL="$WORK/tpl"
mkdir -p "$TPL" && (cd "$ROOT" && tar --exclude .git -cf - .) | (cd "$TPL" && tar -xf -)
P="$TPL/project/harness"
edit "$P/guide/TESTING.md" 's + "\ntemplate: testing\n"'                       # template only → replaced
edit "$P/guide/MEMORY.md"  's.replace("\n", "\ntemplate: memory\n", 1)'         # both, apart → merged
edit "$P/guide/BOOT.md"    's + "\ntemplate: boot\n"'                          # both, same place → conflict
edit "$P/GOAL.md"          's + "\ntemplate: goal\n"'                          # project data → never touched
echo "# new" > "$P/guide/NEW.md"                                                # new → added
# the user's side
edit harness/guide/MEMORY.md 's + "\nuser: memory\n"'
edit harness/guide/BOOT.md   's + "\nuser: boot\n"'
git rm -q harness/guide/SKILLS.md                                               # deleted → not re-added
git commit -qam "smoke: user edits"
GOAL_BEFORE="$(cat harness/GOAL.md)"

run "$TPL/init-harness.sh" --update "$DEMO"
has harness/guide/TESTING.md "template: testing"
has harness/guide/MEMORY.md "template: memory"
has harness/guide/MEMORY.md "user: memory"
[ ! -e harness/guide/MEMORY.md.harness-new ] || fail "MEMORY.md: a clean merge left a .harness-new"
has harness/guide/BOOT.md "user: boot"
lacks harness/guide/BOOT.md "template: boot"
has harness/guide/BOOT.md.harness-new "template: boot"
[ "$(cat harness/GOAL.md)" = "$GOAL_BEFORE" ] || fail "--update changed GOAL.md (project data)"
[ ! -e harness/guide/SKILLS.md ] || fail "--update re-added a file the user deleted"
[ -e harness/guide/NEW.md ] || fail "--update didn't add a new template file"
has harness/FEATURES.json "Smoke feature"

printf '\n✓ smoke install passed\n'
