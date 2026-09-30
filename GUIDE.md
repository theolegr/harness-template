# Getting started — the whole workflow, from a chat

This guide walks you through a project from zero to shipping features, using
one example all the way: **TableDispo**, a small web app where a restaurant's
customers book a table online and the owner sees today's bookings.

You drive everything **from a chat with Claude Code** (terminal, VS Code or
desktop). You type one command to install; after that you talk, and the agent
runs the commands. The harness makes sure it goes in the right direction,
one small step at a time, and that every step is checked by something other
than the agent that wrote it.

---

## 0. Before you start (once)

You need `git`, `python3`, Claude Code, and the tools of your stack (for
TableDispo: Node.js). Get the template:

```bash
git clone https://github.com/theolegr/harness-template ~/harness-template
```

## 1. Install — the only command you type

```bash
~/harness-template/init-harness.sh ~/Projects/tabledispo --name "TableDispo" --type web
```

It copies the harness into the project, creates the git repo, and **opens
Claude, who starts the interview**. (Already in Claude Code? Type
`/harness-init`.)

What lands in your project:

```
tabledispo/
├── AGENTS.md, CLAUDE.md   ← what every agent reads first
├── harness/               ← goal, state, backlog, plan, decisions
│   ├── guide/             ← how the agents work (you rarely touch it)
│   └── scripts/           ← status, check, loop — the agent runs them
└── .claude/               ← hooks, the reviewer & strategist agents, the skills
```

## 2. The interview (~10 minutes)

Claude asks five rounds of questions and proposes answers from what it can
see. For TableDispo:

| Round | Claude asks | You answer |
|---|---|---|
| 1. Project | What is it, for whom? | "Online table booking for small independent restaurants, no commission." Web app, stage: idea |
| 2. Stack | Proposes a stack and commands | Next.js + Supabase + Vercel. `npm install / run dev / test / run lint` |
| 3. Goal | Target + a metric you can measure | "A customer books in under a minute and the owner sees it." Metric: acceptance tests passing, **0/4 → 4/4**, measured by `npm test`. 3 weeks, < €20/month. Not doing: payments, mobile app |
| 4. First features | Proposes 3–5, each with a testable criterion | You edit, reorder, remove (see below) |
| 5. How agents work | Keep the default autonomy? | Yes: code freely; ask before deploying, spending, deleting |

After rounds 2 and 4 it may suggest **at most two** skills that fit (here:
Supabase best practices, then Playwright for browser tests). Accept or
decline; either way it's written in `harness/DECISIONS.md` so it isn't asked again.

The backlog it writes (`harness/FEATURES.json`), simplified:

```
F-001  p0  Booking form      → POST /api/reservations (name, date, party size) → 201, saved
F-002  p0  Refuse when full  → over the slot's capacity → 409 + a clear message
F-003  p1  Owner's day view  → /admin lists today's bookings by time, behind a login
F-004  p2  Confirmation email
```

It shows you a summary and **asks before committing**.

**Check these two yourself before saying yes:** the goal (`harness/GOAL.md`)
and the backlog. Everything else follows from them.

### A product with screens? The look comes before the code

TableDispo has screens, so the interview puts a design item first:
`F-005 p0 Visual direction and first mockups`. When it's that item's turn,
say **"/design"** (or "let's do the mockups"):

1. **A short design interview** — who books (a diner, on a phone, often
   outside the restaurant), the first screen and its one action ("pick a time"),
   3 words for the feel and 3 to avoid, 1–3 references with *what you take from
   each* (inspiration, not a copy), platforms and sizes (web 1440 + 390; the
   skill knows iOS, Android, desktop and email sizes too), the language of the copy.
2. **2–3 directions** of that screen, side by side on a Claude Design canvas
   (or HTML files in `design/`). You pick one, or mix.
3. **Iterations**: you answer in words or by drawing on the mockup — cross out
   what goes, circle what stays. Choices you can't make yet (palette, dark or
   light) become switches on the mockup instead of more rounds.
4. **Recorded**: exact values in `harness/DESIGN.md`, the why in
   `harness/DECISIONS.md`, open choices in `harness/STATE.md`. From then on,
   every UI item is planned from `DESIGN.md`, and the reviewer checks screens
   against it.

## 3. Everyday work: "ship the next one"

Open Claude Code in the project and say:

> **ship the next one**

(or `/ship`, or `ship F-003` for a specific item). Here's what happens:

1. **It picks one item** — F-001, the highest priority — and marks it in progress.
   When the session opened, a hook had already shown it the goal, the backlog
   and the git state.
2. **It shows you the plan** — which files change, how it will be tested,
   what's out of scope — and **waits for your OK**. This is your main job:
   correcting a plan costs a sentence; correcting code costs an afternoon.
3. **It builds**: the code and the acceptance test.
4. **A separate reviewer checks it.** A second agent, with a fresh context and
   no write access, reads the change against F-001's criterion and answers
   PASS or FAIL. On FAIL, the builder fixes what the reviewer named and a new
   reviewer checks again (twice at most, then it asks you).
5. **It records**: F-001 → done, `STATE.md` updated, the metric updated
   (1/4), one commit `feat(F-001): booking form`.
6. **It reports** in a few lines and asks: *ship the next one?*

Things that happen on their own, whatever the agent "decides":

| If the agent… | Then |
|---|---|
| tries `rm -rf src`, `git push --force`, `git reset --hard` | the command is **refused** |
| runs a database migration or a deploy | **you're asked** to confirm |
| wants to finish while tests or lint are red | it's **sent back** to fix them (once; then it must tell you why it can't) |

Want several in a row? *"ship until the MVP"* or *"ship 3"*. It still stops on
anything only you can decide.

## 4. The reviewer feeds the backlog

The reviewer never edits code. When it spots a real problem **outside** the
item it's reviewing, it doesn't fail the review — it writes a finding, and
the builder adds it to the backlog:

```
B-001  p1  bug   Double booking possible on concurrent requests (src/app/api/reservations/route.ts:31)
D-001  p3  debt  Capacity check duplicated in two routes
```

Bugs (`B-`) and debt (`D-`) are items like any feature: same priorities, and
"ship the next one" picks them up when their turn comes. Ask *"what's in the
backlog?"* anytime.

## 5. Stepping back: the strategist

When you want the big picture rather than the next step:

> *"give me an overview of where we are"*
> *"brainstorm: what would get more restaurants to use this?"*
> *"the backlog is empty, what's next?"*

The **strategist** agent reads the whole project — goal, backlog, history,
decisions, code — and answers, then proposes at most five items tied to the
goal's metric, flags items that no longer serve the goal, and lists the
questions only you can answer. Nothing is added until you say which ones you want.

## 6. Changing course

| You want to… | Say |
|---|---|
| add an idea | *"add a feature: owner can block a slot for a private event"* — it gets a testable criterion and a priority |
| drop something | *"cut F-004, not needed for the MVP"* |
| change the goal or the stack | `/harness-init` — it re-runs only the rounds you want to change |
| see where things stand | *"status"* |
| deploy | *"deploy to Vercel"* — it will always ask you first |

When you correct the agent, it turns the correction into a principle in the
harness files (not a pile of rules), committed so you can see and revert it.

## 7. Running unattended (optional, later)

Once you trust the process, the same loop can run without you, e.g. overnight:
*"run the loop once, unattended"*. The agent uses `harness/scripts/loop.sh`.
Differences with `/ship`: no plan validation, each item on its own
`loop/<id>` branch, never merged into main without you. A failed item is marked
blocked and the loop stops; it doesn't retry on top of broken code. Start
with one item at a time, and review the branch before merging.

## 8. Your weekly five minutes

- Did the metric in `harness/GOAL.md` move? Two sessions without progress →
  say *"we're stalling"*: the agent will propose a different approach.
- Skim `harness/DECISIONS.md`: do you still agree?
- Is the goal still the right one? If not, `/harness-init`.

## Cheat sheet

| Say | What happens |
|---|---|
| *ship the next one* / `/ship` | one item: plan → your OK → build → review → commit |
| *ship F-003* / *fix B-001* | that item |
| *ship until the MVP* | several in a row, stops on questions and failures |
| *status* | goal, backlog, git state |
| *add a feature: …* / *cut F-004* | backlog changes |
| *overview* / *brainstorm …* | the strategist |
| `/design` | visual direction and first mockups, before building screens |
| `/harness-init` | change goal, stack, features |
