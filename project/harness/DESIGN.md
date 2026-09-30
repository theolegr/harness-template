# DESIGN.md — visual direction and design values

> Read before any item that touches user-facing UI. Filled by the `design` skill
> (`/design`); the *why* of each choice goes in `harness/DECISIONS.md`, the
> values to build with go here. Nothing is final: change a value here and in the
> mockups, never only in the code.
>
> **Status**: no direction yet
> <!-- no UI (CLI, API, bot: fill only "Voice in the UI") | no direction yet |
>      direction chosen (provisional) | stable -->

## Source of truth

- Mockups: <canvas / Figma / `design/` folder — link, and which screens (artboards)>
- Tweaks or variants still open on the mockups: <e.g. palette: 4 options, dark/light>

## Brief

| | |
|---|---|
| Audience | <who uses it, in what situation> |
| First screens | <screen → its ONE main action> |
| Feel — yes | <3 words, e.g. calm, precise, warm> |
| Feel — no | <3 words, e.g. corporate, gimmicky, gloomy> |
| References | <link → what we take from it (material, type, colour, tone) — inspiration, not layout> |
| Anti-references | <what it must not look like> |
| Platforms and sizes | <e.g. web 1440 + 390 / iOS 393×852 + 375×667> |
| Copy language and tone | <language(s), see guide/SOUL.md → Voice> |
| Theme, motion | <light / dark / both — none / subtle / expressive> |
| Accessibility | <WCAG AA: text 4.5:1, targets ≥ 44 px (48 dp Android), reduced motion> |

## Tokens

Built as variables (CSS custom properties, a theme file, an asset catalog…): a
choice still open costs a variable swap, not a rewrite.

| Role | Value | Notes |
|---|---|---|
| background | <#…> | |
| surface | <#…> | cards, panels |
| text / secondary / label | <#…> | check contrast on background and surface |
| accent | <#…> | |
| border | <#…> | |

- **Type**: <families, weights, the scale: display / h2 / body / label, with size, line height, tracking>
- **Spacing and radii**: <grid unit, margins, radius per component>
- **Materials**: <shadows, blur, gradients, textures — the recipe, not an adjective>
- **Motion**: <what moves, duration, easing; everything stops under reduced motion>

## Components

| Component | Recipe |
|---|---|
| <primary button> | <fill, border, radius, height, states> |
| <card> | <…> |
| <signature element (mascot, motif…)> | <shape, behaviour> |

## Layout

- <main size>: <margins, columns, content width, section rhythm, the order of sections>
- <smallest size>: <what stacks, what hides, what changes size>

## Voice in the UI

- <copy rules: length, tone, words to avoid, how errors and empty states speak>

## Open design questions

In `harness/STATE.md` → Open questions (prefix them "Design:").
