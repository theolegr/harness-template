# WAITING.md — what waits on the user

> What only the user can settle, written down here, never only in the chat (`AGENTS.md` §5, rule 10).
> The dashboard opens on it ("Waiting on you"), and the status at session start lists it.
>
> - **Q — question**: they answer in a sentence: a choice (the options inline, your recommendation
>   first), a fact only they know, an OK.
> - **A — action**: they do it themselves, outside the session, because the agent can't: an account,
>   a key or a token, a payment, a call, a signature, a draft to review, a test on their device.
>
> One short line each; the context lives in a linked file, not here. Optional fields after ` · `:
> `Reco:` (Q), `Done when:` (A — what the agent will check), `Blocks:` (item ids),
> `By: YYYY-MM-DD` (past that date it shows overdue). An action's steps: indented under it.
> Nothing blocked and no date → `## Later`. Settled → the line leaves the file: a choice goes to
> `DECISIONS.md`, a fact to where it's used; a done action, once checked, unblocks its items.
> Numbers are never reused: a new one takes the next after `Last numbers`, updated each time.
>
> Last numbers: Q0 · A0

## Actions

<!-- - **A1** — Open the company's Stripe account and put its test key in `.env` · Done when: `stripe whoami` answers · Blocks: F-012 · By: 2026-11-15
       1. Sign up at dashboard.stripe.com with the company email
       2. Developers → API keys → copy the test secret key into `.env` as `STRIPE_KEY` -->

## Questions

<!-- - **Q1** — The domain: A) brand.com ($12/yr) B) getbrand.com ($9/yr)? · Reco: A, the shorter one · Blocks: F-019 -->

## Later

<!-- Same lines, Q or A: nothing waits on them yet. Folded away on the dashboard, not counted. -->
