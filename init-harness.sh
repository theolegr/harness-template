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
#   --type saas|web|app|api|bot|cli   (free text, e.g. "mobile app")
#   --no-interview        only copy the files; run /harness-init in Claude later
#   --update              bring an installed project up to this template version
#                         (no interview, your data is never overwritten — see below)
#
# What it does:
#   1. Copies project/ from the template into the target:
#        AGENTS.md, CLAUDE.md                → project root (what agents read first)
#        harness/…                           → goal, state, features, guide, scripts
#        .claude/skills/                     → harness-init (interview), ship (loop in the chat), design (visual direction)
#        .claude/settings.json, agents/      → hooks (guard, stop-check) + reviewer, strategist
#        .agents/skills/                     → project skills folder
#   2. Keeps the template itself in harness/template/ (git-ignored).
#   3. Adds .gitignore entries; outside a git repo, git-inits and stages the
#      harness files (no commit: the interview commits, with your OK).
#   4. Launches Claude with the harness-init interview.
#
# Non-destructive: a file that already exists is kept as-is; if the harness
# version differs, it is written next to it as <file>.harness-new for review.
# Your data (GOAL, STATE, FEATURES, EVAL, PLAN, DECISIONS, DESIGN, ARTIFACTS in harness/)
# is never touched once it exists: no merge, no <file>.harness-new.
#
# --update (run the NEW template on the project:
#   git -C ~/harness-template pull && ~/harness-template/init-harness.sh --update my-project)
# compares each file with harness/template/ — the version installed last time:
#   you never edited it            → replaced by the new version
#   the template didn't change it  → yours, untouched
#   both changed it                → 3-way merge when the edits don't overlap,
#                                    else kept + <file>.harness-new to merge by hand
#   you deleted it                 → not re-added
#   new in the template            → added
#   your data                      → never touched (says if the template's version changed)
# then refreshes harness/template/. Nothing is committed: review with git diff.
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
TARGET="" NAME="" TYPE="" INTERVIEW=1 UPDATE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --name) NAME="${2:?--name needs a value}"; shift 2;;
    --type) TYPE="${2:?--type needs a value}"; shift 2;;
    --no-interview) INTERVIEW=0; shift;;
    --update) UPDATE=1; INTERVIEW=0; shift;;
    -h|--help) sed -n '2,46s/^# \{0,1\}//p' "$0"; exit 0;;
    -*) echo "unknown option: $1" >&2; exit 2;;
    *) TARGET="$1"; shift;;
  esac
done

# Default target: the project that contains harness/template/
if [ -z "$TARGET" ]; then
  case "$SRC" in
    */harness/template) TARGET="$(dirname "$(dirname "$SRC")")";;
    *) echo "usage: init-harness.sh <target-dir> [--name ...] [--type ...] [--no-interview | --update]" >&2
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

# --update: the copy installed last time (harness/template/) is the merge base
BASE=""
if [ "$UPDATE" -eq 1 ]; then
  if [ "$SRC" = "$TARGET/harness/template" ]; then
    echo "✗ --update needs the NEW template — run it from your template clone, not from harness/template/:" >&2
    echo "    git -C ~/harness-template pull && ~/harness-template/init-harness.sh --update $TARGET" >&2
    exit 1
  fi
  if [ -d harness/template/project ]; then
    BASE="harness/template/project"
  else
    echo "  ⚠ no harness/template/ — can't tell your edits from the template's: every file that"
    echo "    differs is kept, with the new version next to it as <file>.harness-new (your data: just kept)"
  fi
fi

# The project's data: once it exists, never merged, replaced or shadowed by a .harness-new
is_data() {
  case "$1" in
    harness/GOAL.md|harness/STATE.md|harness/FEATURES.json|harness/EVAL.md|harness/PLAN.md|\
    harness/DECISIONS.md|harness/DESIGN.md|harness/ARTIFACTS.md) return 0;;
  esac
  return 1
}

# 3-way merge of the template's changes (base → new) into your file. Fails —
# leaving your file untouched — on overlapping edits or a merge that isn't valid JSON.
merge3() {
  local out; out="$(mktemp)"
  if git merge-file -p "$1" "$2" "$3" > "$out" 2>/dev/null \
     && { case "$1" in *.json) python3 -m json.tool "$out" >/dev/null 2>&1;; esac; }; then
    cat "$out" > "$1"; rm -f "$out"; return 0
  fi
  rm -f "$out"; return 1
}

echo "── $([ "$UPDATE" -eq 1 ] && echo Updating || echo Installing) project harness in $TARGET"

# 1. Copy project/ into the target, never overwriting your edits
ADDED=() REVIEW=()
while IFS= read -r f; do
  new="$SRC/project/$f" base=""
  [ -n "$BASE" ] && [ -f "$BASE/$f" ] && base="$BASE/$f"
  if [ ! -e "$f" ]; then
    if [ -n "$base" ]; then
      echo "  - $f (you deleted it — not re-added)"
      continue
    fi
    mkdir -p "$(dirname "$f")"
    cp "$new" "$f"
    ADDED+=("$f")
    echo "  + $f"
  elif cmp -s "$new" "$f"; then
    echo "  · $f (already up to date)"
  elif is_data "$f"; then
    if [ -n "$base" ] && ! cmp -s "$base" "$new"; then
      echo "  · $f (your data, untouched — the template's version changed: harness/template/project/$f)"
    else
      echo "  · $f (your data, untouched)"
    fi
  elif [ -n "$base" ] && cmp -s "$base" "$f"; then
    cp "$new" "$f"
    echo "  ↑ $f (updated — you hadn't edited it)"
  elif [ -n "$base" ] && cmp -s "$base" "$new"; then
    echo "  · $f (yours — unchanged in the template)"
  elif [ -n "$base" ] && merge3 "$f" "$base" "$new"; then
    echo "  ⇄ $f (merged: your edits + the template's)"
  else
    cp "$new" "$f.harness-new"
    REVIEW+=("$f")
    echo "  ~ $f kept — harness version written to $f.harness-new"
  fi
done < <(cd "$SRC/project" && find . -type f ! -name '.DS_Store' ! -path '*/__pycache__/*' | sed 's|^\./||' | sort)
chmod +x harness/scripts/*.sh harness/scripts/*.py
# tests/ only for a new project with no stack yet (a monorepo keeps its tests in its packages)
MANIFEST=0
for m in package.json pyproject.toml requirements.txt go.mod Cargo.toml Gemfile pom.xml build.gradle composer.json; do
  if [ -f "$m" ]; then MANIFEST=1; fi
done
if [ "$UPDATE" -eq 0 ] && [ "$MANIFEST" -eq 0 ]; then mkdir -p tests; fi
if [ -f CLAUDE.md ] && ! grep -q '@AGENTS.md' CLAUDE.md; then
  echo "  ⚠ your CLAUDE.md doesn't import AGENTS.md — add a line '@AGENTS.md' to it"
  echo "    (the interview will offer to do it)"
fi

# 2. Keep a copy of the template (for re-runs, and the base of the next --update),
#    unless we run from it
if [ "$SRC" != "$TARGET/harness/template" ] && { [ ! -e harness/template ] || [ "$UPDATE" -eq 1 ]; }; then
  rm -rf harness/template.tmp && mkdir -p harness/template.tmp
  (cd "$SRC" && tar --exclude .git --exclude .DS_Store --exclude __pycache__ -cf - .) \
    | (cd harness/template.tmp && tar -xf -)
  # the template's own files, listed — the next update tells them from the ones you add
  (cd harness/template.tmp && find . -type f ! -name .harness-files | sed 's|^\./||' | sort) \
    > harness/template.tmp/.harness-files
  # a file you added there (notes…) isn't the template's: keep it, but say where it belongs.
  # Without the list (installed by an older version), anything the new template lacks counts as yours.
  if [ -d harness/template ]; then
    while IFS= read -r f; do
      [ -e "harness/template.tmp/$f" ] && continue
      if [ -f harness/template/.harness-files ] && grep -qxF "$f" harness/template/.harness-files; then
        continue   # the template's, dropped upstream
      fi
      mkdir -p "harness/template.tmp/$(dirname "$f")" && cp -p "harness/template/$f" "harness/template.tmp/$f"
      echo "  · kept harness/template/$f — not part of the template; harness notes belong in harness/TEMPLATE-FEEDBACK.md"
    done < <(cd harness/template && find . -type f ! -name .DS_Store ! -name .harness-files ! -path './.git/*' \
               | sed 's|^\./||')
  fi
  rm -rf harness/template && mv harness/template.tmp harness/template
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
    s = old = p.read_text()
    if name:
        s = s.replace("<PROJECT NAME>", name).replace("<PROJECT>", name)
    if ptype:
        s = s.replace("- **Type**: SaaS / web app / API / tool / bot", f"- **Type**: {ptype}")
    if s != old:
        p.write_text(s)
        print(f"  ✎ {t}: pre-filled")
PY
fi

# 3. .gitignore — the template copy and the loop's runtime files never go in git
touch .gitignore
for pat in harness/template/ harness/.loop.log harness/.loop.stop harness/.check.ok harness/dashboard.html \
           harness/.sessions-ended '*.harness-new'; do
  grep -qxF "$pat" .gitignore || echo "$pat" >> .gitignore
done
echo "  + .gitignore entries"

# Inside any repo (a worktree, a package of a monorepo): use it. Otherwise git init.
# Nothing is committed: the first commit is the interview's, made with your OK.
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "  · git repo already present — not committing (review with git status)"
else
  git init -q
  # stage the harness only, never the rest of the folder (an .env, build output…)
  for p in AGENTS.md CLAUDE.md .gitignore harness .claude .agents; do
    if [ -e "$p" ]; then git add -- "$p"; fi
  done
  echo "  + git repository initialised — harness files staged, nothing committed"
  git config user.email >/dev/null 2>&1 \
    || echo "  ⚠ no git identity set — before the first commit: git config --global user.name/user.email"
fi

if [ "$UPDATE" -eq 1 ]; then
  echo
  echo "── Updated. Nothing committed — review with: git status && git diff"
  if [ "${#REVIEW[@]}" -gt 0 ]; then
    echo "   To merge by hand (you and the template changed the same lines):"
    for f in "${REVIEW[@]}"; do echo "     $f  ←  $f.harness-new"; done
    echo "   Then delete the .harness-new files (harness-status.sh reminds you until they're gone)."
  fi
  exit 0
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
