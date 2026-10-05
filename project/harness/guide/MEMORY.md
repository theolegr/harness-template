# MEMORY.md — what the project remembers, and how it learns

> **A bigger context window is not memory.** The agent forgets; the repo doesn't.
> Anything that lives only in a chat is already lost.

## Where each kind of knowledge lives

| Kind | Lives in | Lifetime |
|---|---|---|
| Identity, autonomy | `harness/guide/SOUL.md` | permanent |
| How we work | `AGENTS.md`, `harness/guide/` | stable, versioned |
| Why things are this way | `harness/DECISIONS.md` | append-only |
| Current state | `harness/STATE.md` | overwritten constantly |
| What's left (features, bugs, debt) | `harness/FEATURES.json` | until done → `FEATURES-DONE.json` |
| Hard-won procedures | `.agents/skills/` | maintained, pruned |
| Links to pages published outside the repo (canvases, diagrams) | `harness/ARTIFACTS.md` | a line per page, marked archived when stale |
| The target | `harness/GOAL.md` | reviewed weekly |

## The agent's own memory vs. the repo

Some agents keep a memory of their own (Claude Code's auto-memory, in
`~/.claude/projects/<project>/memory/`). It lives on one machine, for one
agent: the reviewer, a `loop.sh` run on another machine, Codex or a
teammate never see it. So:

- **Agent memory** — only facts about the person: how they write (dictation,
  language), how they like to be answered, what they don't want running on
  their machine.
- **The repo** — every rule about the project: naming, process, testing,
  design choices and rejected directions. When a correction is a project rule,
  write it where the work happens (`AGENTS.md` §5, a guide, `DESIGN.md`),
  commit it, and don't keep a copy in agent memory — two copies drift apart.

## Rules

1. **The 3-month test.** Before writing a durable note: will it still be true
   and useful in 3 months? No → it doesn't go in the repo.
2. **Don't write it twice.** If it's in the code, don't restate it in docs.
3. **State, not diary.** `STATE.md` says where we are now, not what happened.
4. **Surface contradictions, don't auto-merge them.** Two notes that clash may
   each be right in their context — flag it in `STATE.md` open questions, a human decides.
5. **Let stale knowledge decay.** Flag it for review (monthly); don't let skills
   and docs calcify. Delete what no longer earns its place — *build to delete*.

## Learning from corrections

When a human corrects the agent (rewrites output, rejects a draft, reverts a
change), the naive fix is a new rule. Rules pile up into a checklist nobody
follows. Extract the **principle** instead:

1. Ask why — what principle was missing or vague?
2. Look for the pattern across recent corrections. One-off → do nothing.
3. Check the existing principles — maybe one is there but unclear: sharpen it.
4. Write it as a principle, in the right file (`AGENTS.md`, a guide, a skill),
   and commit it with the correction that triggered it in the message.

Instructions are code: versioned, reviewed as a diff, revertable. That's how the
harness improves itself **without losing human control**.

## Anti-patterns

- ❌ Rule accretion — every correction becomes a new rule.
- ❌ Silent self-modification — editing instructions without a diff and a commit.
- ❌ Dumping transcripts or diaries into memory files.
- ❌ Assuming the agent remembers last session. It doesn't — write it down.
