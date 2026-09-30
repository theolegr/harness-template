#!/usr/bin/env bash
# init-harness.sh — install the project harness into a project, then hand over
# to Claude for a short interview that fills it in.
#
# Usage (recommended — template kept elsewhere; a copy goes to harness/template/):
#   /path/to/harness-template/init-harness.sh <target-dir>
#
# Usage (template copied into the project first):
#   mkdir -p my-project/harness && cp -R /path/to/harness-template my-project/harness/template
#   cd my-project && ./harness/template/init-harness.sh
#
# Options:
#   --name "My Project"   pre-fill the project name (the interview asks otherwise)
#   --type saas|web|api|bot|cli
#   --no-interview        only copy the files; run /harness-init in Claude later
#
# What it does:
#   1. Copies project/ from the template into the target:
#        AGENTS.md, CLAUDE.md                → project root (what agents read first)
#        harness/…                           → goal, state, features, guide, scripts
#        .claude/skills/                     → harness-init (interview), ship (loop in the chat), design (visual direction)
#        .claude/settings.json, agents/      → hooks (guard, stop-check) + reviewer, strategist
#        .agents/skills/                     → project skills folder
#   2. Keeps the template itself in harness/template/ (git-ignored).
#   3. Adds .gitignore entries, git-inits + commits if the repo is new.
#   4. Launches Claude with the harness-init interview.
#
# Non-destructive: a file that already exists is kept as-is; if the harness
# version differs, it is written next to it as <file>.harness-new for review.
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
TARGET="" NAME="" TYPE="" INTERVIEW=1
while [ $# -gt 0 ]; do
  case "$1" in
    --name) NAME="${2:?--name needs a value}"; shift 2;;
    --type) TYPE="${2:?--type needs a value}"; shift 2;;
    --no-interview) INTERVIEW=0; shift;;
    -h|--help) sed -n '2,28s/^# \{0,1\}//p' "$0"; exit 0;;
    -*) echo "unknown option: $1" >&2; exit 2;;
    *) TARGET="$1"; shift;;
  esac
done

# Default target: the project that contains harness/template/
if [ -z "$TARGET" ]; then
  case "$SRC" in
    */harness/template) TARGET="$(dirname "$(dirname "$SRC")")";;
    *) echo "usage: init-harness.sh <target-dir> [--name ...] [--type ...] [--no-interview]" >&2
       echo "       (or copy the template to <project>/harness/template and run it from there)" >&2
       exit 2;;
  esac
fi

mkdir -p "$TARGET"
TARGET="$(cd "$TARGET" && pwd)"
case "$TARGET/" in
  "$SRC/"*) echo "✗ target ($TARGET) is inside the harness template — refusing." >&2; exit 1;;
esac
cd "$TARGET"

echo "── Installing project harness in $TARGET"

# 1. Copy project/ into the target, never overwriting
ADDED=()
while IFS= read -r f; do
  mkdir -p "$(dirname "$f")"
  if [ ! -e "$f" ]; then
    cp "$SRC/project/$f" "$f"
    ADDED+=("$f")
    echo "  + $f"
  elif cmp -s "$SRC/project/$f" "$f"; then
    echo "  · $f (already up to date)"
  else
    cp "$SRC/project/$f" "$f.harness-new"
    echo "  ~ $f kept — harness version written to $f.harness-new"
  fi
done < <(cd "$SRC/project" && find . -type f ! -name '.DS_Store' | sed 's|^\./||' | sort)
chmod +x harness/scripts/*.sh
mkdir -p tests
if [ -f CLAUDE.md ] && ! grep -q '@AGENTS.md' CLAUDE.md; then
  echo "  ⚠ your CLAUDE.md doesn't import AGENTS.md — add a line '@AGENTS.md' to it"
  echo "    (the interview will offer to do it)"
fi

# 2. Keep a copy of the template (for re-runs and updates), unless we run from it
if [ "$SRC" != "$TARGET/harness/template" ] && [ ! -e harness/template ]; then
  mkdir -p harness/template
  (cd "$SRC" && tar --exclude .git --exclude .DS_Store -cf - .) | (cd harness/template && tar -xf -)
  echo "  + harness/template/ (copy of the template, git-ignored)"
fi

# Pre-fill name / type if given (only in files this run added — never touch yours)
if [ -n "$NAME$TYPE" ] && [ "${#ADDED[@]}" -gt 0 ]; then
python3 - "$NAME" "$TYPE" "${ADDED[@]}" <<'PY'
import sys, pathlib
name, ptype, added = sys.argv[1], sys.argv[2], set(sys.argv[3:])
targets = ["AGENTS.md", "harness/guide/SOUL.md", "harness/GOAL.md", "harness/STATE.md",
           "harness/FEATURES.json", "harness/guide/LOOP.md"]
for t in targets:
    if t not in added: continue
    p = pathlib.Path(t)
    s = p.read_text()
    if name:
        s = s.replace("<PROJECT NAME>", name).replace("<PROJECT>", name)
    if ptype:
        s = s.replace("- **Type**: SaaS / web app / API / tool / bot", f"- **Type**: {ptype}")
    p.write_text(s)
    print(f"  ✎ {t}: pre-filled")
PY
fi

# 3. .gitignore — the template copy and the loop's runtime files never go in git
touch .gitignore
for pat in harness/template/ harness/.loop.log harness/.loop.stop harness/.check.ok '*.harness-new'; do
  grep -qxF "$pat" .gitignore || echo "$pat" >> .gitignore
done
echo "  + .gitignore entries"

if [ ! -d .git ]; then
  git init -q
  git add -A
  if git config user.email >/dev/null 2>&1; then
    git commit -qm "chore: add project harness" || true
  else   # no git identity configured yet: don't fail, but say so
    git -c user.email=harness@local -c user.name=harness commit -qm "chore: add project harness" || true
    echo "  ⚠ no git identity set — first commit signed 'harness'. Set yours: git config --global user.name/user.email"
  fi
  echo "  + git repository initialised (first commit made)"
else
  echo "  · git repo already present — not committing (review with git status)"
fi

# 4. Interview
PROMPT="Use the harness-init skill (.claude/skills/harness-init/SKILL.md) to interview me and fill in this project's harness."
echo
if [ "$INTERVIEW" -eq 1 ] && [ -t 0 ] && [ -t 1 ] && command -v claude >/dev/null 2>&1; then
  echo "── Starting the interview with Claude (≈10 min)…"
  echo
  exec claude "$PROMPT"
fi

cat <<EOF
── Files installed. Next step: the interview.

   cd $TARGET && claude "$PROMPT"

   (or open Claude Code in the project and type /harness-init)

EOF
