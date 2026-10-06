---
name: design
description: Set the visual direction of a product with UI (website, web app, iOS, Android, desktop, email) before the first screen is built — a short design interview, 2–3 contrasting mockup directions, iterations on the chosen one, then the values written into harness/DESIGN.md. Use when the user says "design", "/design", "maquette", "mockup", "direction visuelle", "the look", when the next backlog item is the design item, or when a UI item is about to be planned while harness/DESIGN.md has no direction.
---

# design — from a brief to a validated mockup

A UI built without a direction gets redone. This skill gets the direction
first: ask the questions only the user can answer, show options instead of
describing them, iterate on what they react to, and write the result where
builders will read it (`harness/DESIGN.md`).

Speak the user's language. Short messages: the user looks at mockups, not at
paragraphs about them.

## 0. Look before you ask

1. Read `AGENTS.md`, `harness/GOAL.md`, `harness/guide/SOUL.md` (voice, copy
   language), `harness/DESIGN.md`, the design item in `harness/FEATURES.json`,
   the tail of `harness/DECISIONS.md`.
2. Look for what already exists: a logo, brand colours or fonts, a current site
   or app (URL, screenshots), a design system, UI code (Tailwind config, theme
   files, SwiftUI colours). Turn each into a proposal ("I see your logo is
   navy and orange — keep them?") rather than an open question.
3. No UI (CLI, API, bot)? Say so, set `Status: no UI` in `harness/DESIGN.md`,
   fill only *Voice in the UI*, and stop.

## 1. The interview — 4 short rounds

Use the AskUserQuestion tool when the answer has natural options (max 4
questions per call, your recommendation first); plain text for free answers.
After each round, restate in 2 lines what you understood. Every question can
be skipped: skipped answers become open questions.

**Round 1 — Who and what**
- Who uses it, in what situation (on a phone between two jobs, at a desk…)?
- Which screen comes first, and what is the ONE thing a person must do there?

**Round 2 — The feel**
- 3 words for how it should feel, and 3 it must not (offer pairs: calm /
  energetic, warm / technical, premium / friendly, editorial / futuristic…).
- Light, dark or both? Motion: none, subtle, expressive?
- A signature element (a mascot, a motif, an illustration style) or none?

**Round 3 — References and assets**
- 1 to 3 references: links or screenshots. For **each**, ask what to take from
  it (material and texture, typography, colour, density, tone of the copy) and
  whether it is **inspiration or a close reproduction**. Default: inspiration —
  take the principles, never the layout, widgets, copy or brand.
- Anything it must not look like (anti-references)?

**Round 4 — Constraints**
- Platforms and sizes (propose from the table below).
- Copy language(s) and tone — propose from `SOUL.md` → Voice; if the user asks
  for another language, flag the conflict and record the answer.
- Accessibility (default WCAG AA) and stack limits (system fonts on iOS, a CSS
  framework…).

| Platform | Main size | Smallest | Mind |
|---|---|---|---|
| Website / web app | 1440 | 390 | touch targets ≥ 44 px, `prefers-reduced-motion` |
| iOS | 393×852 | 375×667 | Apple HIG, safe areas, Dynamic Type, 44 pt targets |
| Android | 412×915 | 360×800 | Material 3, 48 dp targets |
| Desktop app | 1280×800 | 1024×640 | keyboard, focus states |
| Email | 600 wide | 320 | table layout, web-safe fonts, no script |

Write the brief into `harness/DESIGN.md` → *Brief* before drawing anything.

## 2. Directions — show, don't describe

Make **2 or 3 directions** of the same first screen, with the same real copy,
that differ in what matters (type, colour, layout, material) — not three
shades of one idea. Name each in two words.

Where the mockups live, in this order:
1. **Claude Design** (the Artifact tool's Design canvas), if available: one
   artboard per direction, side by side, with the main size as the frame.
2. The user's tool if they have one (Figma link) — then you describe, they draw.
3. Otherwise static HTML files in `design/` in the repo, opened in a browser.

Real content, no lorem ipsum; missing facts become placeholders like `[PRICE]`.
Give the user the link and one line per direction. Let them pick, mix or reject.
A new canvas gets its line in `harness/ARTIFACTS.md` right away (link, what,
status), so the next session can find it.

## 3. Iterate on the chosen one

- One round = one set of changes the user asked for. Change only that.
- **A choice they can't make yet becomes a tweak** on the mockup (an option
  list for the palette, a switch for a decorative layer) and, later, a
  variable in the code — so it never blocks building.
- **The user drew on the mockup** (crosses, circles, arrows)? Re-read the file,
  map each mark to the element under it, restate ("crossed: the settings
  panel → remove; circled: the logo → keep"), apply, then remove the marks.
- **Feedback is ambiguous** (dictated, cut off, contradictory)? Apply the clear
  part, ask about the rest in at most 3 short questions. Never guess a change
  of direction (light vs dark, removing the main action).
- Keep one main action per screen; no decorative control panels.
- Before calling it done: the chosen screen exists at the **smallest size**
  too, or the design item's notes say explicitly where the small size will be
  designed.

## 4. Record — the direction is only real once it is written

1. `harness/DESIGN.md`: status `direction chosen (provisional)`, the mockup
   link, tokens, type, materials, components, layout per size, voice. Exact
   values (hex, px, font weights), not adjectives.
2. `harness/DECISIONS.md`: one entry — what was chosen, why, what was rejected
   (directions, palettes, fonts, the elements the user crossed out). A new
   direction marks the old entry `superseded`.
3. `harness/STATE.md` → Open questions: every open choice, numbered and prefixed
   (`**Q4** — Design: …`, numbering in `AGENTS.md` §5, rule 10),
   with who decides and before which item.
4. `harness/FEATURES.json`: the UI items' notes point to the mockup and to
   `DESIGN.md` ("implements the validated mockup, no improvised design").
5. Close the design item only when the **user** validates the mockup
   (`./harness/scripts/feature.sh <id> done "<what was validated, what was deferred>"`),
   then commit: `docs(<id>): visual direction`.

## Pitfalls seen in real projects

- Copying a reference's layout and widgets when the user wanted its feel.
- A lone hero element in an empty framed box: compose with the page, not in a box.
- Many small controls and options on a landing page: it should read as one
  message with one action.
- Copy in a different language than `SOUL.md` without noticing.
- A mockup validated at desktop size only, discovered while building mobile.
