#!/usr/bin/env bash
# link-skills.sh — make the project skills in .agents/skills/ visible to Claude Code.
#
# .agents/skills/ is the agent-agnostic home of project skills (Codex and other
# agents read it). Claude Code only loads skills from .claude/skills/, but
# accepts a skill folder there that is a symlink. So for each
# .agents/skills/<name>/SKILL.md this creates
#   .claude/skills/<name> → ../../.agents/skills/<name>
# and removes links whose skill was deleted. A real folder already at
# .claude/skills/<name> is never touched.
#
# Run by the SessionStart hook; safe to run any time. Silent when nothing changes.
set -euo pipefail

cd "$(dirname "$0")/../.."   # project root
[ -d .agents/skills ] || exit 0
mkdir -p .claude/skills

for skill in .agents/skills/*/; do
  name="$(basename "$skill")"
  [ -f ".agents/skills/$name/SKILL.md" ] || continue
  link=".claude/skills/$name"
  if [ -L "$link" ] || [ -e "$link" ]; then continue; fi
  ln -s "../../.agents/skills/$name" "$link"
  echo "  + skill '$name' linked for Claude Code (.claude/skills/$name)"
done

# links to skills that no longer exist
for link in .claude/skills/*; do
  [ -L "$link" ] || continue
  case "$(readlink "$link")" in
    ../../.agents/skills/*)
      if [ ! -e "$link" ]; then
        rm "$link"
        echo "  - skill '$(basename "$link")' unlinked (removed from .agents/skills/)"
      fi;;
  esac
done
