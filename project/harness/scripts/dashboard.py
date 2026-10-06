#!/usr/bin/env python3
"""dashboard.py — the project's state as one HTML page.

  ./harness/scripts/dashboard.py              # writes harness/dashboard.html
  ./harness/scripts/dashboard.py --open       # … and opens it in the browser
  ./harness/scripts/dashboard.py --watch [N]  # rewrites it every N s (default 5)

A view, never a source: everything comes from state.py, and the only file
written is harness/dashboard.html (git-ignored). One self-contained page — no
network, no dependency — readable offline and safe to attach to a message.

Kept current without asking: Claude Code's Stop hook rewrites the page at the
end of each turn once it exists, and an open tab reloads itself every 30 s
(keeping its scroll position and what's unfolded).
"""
import argparse
import datetime
import html
import json
import math
import re
import sys
import time
import webbrowser
from pathlib import Path

sys.dont_write_bytecode = True   # no __pycache__ left in harness/scripts/
sys.path.insert(0, str(Path(__file__).resolve().parent))
from state import ROOT, collect  # noqa: E402

OUT = ROOT / "harness" / "dashboard.html"
RELOAD = 30   # seconds: an open tab picks up a rewrite (the Stop hook's, --watch's) on its own
QREF = re.compile(r"\bQ\d+\b")   # an open question of STATE.md (Q1, Q2…), cited in a blocked item's reason


# ── Small helpers ──

def esc(s):
    return html.escape("" if s is None else str(s))


def inline(s):
    """Escape, then the bits of Markdown the harness files use: `code`, **bold** and ~~struck~~."""
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", esc(s))
    s = re.sub(r"~~(.+?)~~", r"<s>\1</s>", s)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)


def ago(iso):
    if not iso:
        return None
    s = (datetime.datetime.now() - datetime.datetime.fromisoformat(iso)).total_seconds()
    for limit, unit, div in ((60, "", 0), (3600, "min", 60), (86400, "h", 3600), (math.inf, "d", 86400)):
        if s < limit:
            return "just now" if not div else f"{int(s // div)} {unit} ago"


TYPES = ("feature", "bug", "debt")


def empty(text):
    return f'<p class="empty">{inline(text)}</p>'


def ul(items, cls="list"):
    return f'<ul class="{cls}">' + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


def meter(done, total, label):
    pct = done / total * 100 if total else 0
    return (f'<div class="meter" role="progressbar" aria-label="{esc(label)}" aria-valuemin="0" '
            f'aria-valuemax="{total}" aria-valuenow="{done}"><span style="width:{pct:.1f}%"></span></div>')


def short_date(iso):
    try:
        d = datetime.date.fromisoformat(str(iso))
    except ValueError:
        return esc(iso)
    return f"{d:%b} {d.day}"


def dot(kind):
    """Type marker: the color carries identity, the legend and the hidden label name it."""
    cls = kind if kind in TYPES else "feature"
    return f'<span class="dot t-{cls}" title="{esc(kind)}"><span class="sr">{esc(kind)} </span></span>'


def chev():
    return '<span class="chev" aria-hidden="true"></span>'


def fold(key, title, body, n=None, opened=False):
    """A section folded behind its title; the page remembers it open across refreshes."""
    count = f' <span class="count">{n}</span>' if n is not None else ""
    return (f'<details class="fold" data-key="{esc(key)}"{" open" if opened else ""}>'
            f'<summary>{title}{count}{chev()}</summary><div class="fold-body">{body}</div></details>')


def item(f, mark, ms_of):
    """One backlog row: the title is always visible, the rest folds out."""
    fid, kind = f.get("id", ""), f.get("type", "feature")
    prio = str(f.get("priority", "")).upper()
    tags = "".join(f'<span class="chip ms">{esc(m)}</span>' for m in ms_of.get(fid, []))
    if f.get("status") == "blocked":   # the open question(s) it waits on, cited as Q<n> in its reason
        tags += "".join(f'<span class="chip q" title="waits on open question {q} (STATE.md)">{q}</span>'
                        for q in dict.fromkeys(QREF.findall(f.get("blocked") or "")))
    if prio:
        tags += f'<span class="chip">{esc(prio)}</span>'
    if f.get("status") == "done" and f.get("closed"):
        tags += f'<span class="when">{short_date(f["closed"])}</span>'
    facts = [("Waiting on", inline(f["blocked"]))] if f.get("status") == "blocked" and f.get("blocked") else []
    acc = f.get("acceptance") or ""
    if acc and not acc.startswith("<"):
        facts.append(("Acceptance", inline(acc)))
    if f.get("notes"):
        facts.append(("Notes", inline(f["notes"])))
    if f.get("files"):
        facts.append(("Files", " ".join(f"<code>{esc(x)}</code>" for x in f["files"])))
    dates = [f"{k} {f[k]}" for k in ("added", "closed") if f.get(k)]
    facts.append(("Type", esc(" · ".join([kind] + dates))))
    body = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in facts)
    status = f.get("status", "todo")
    return (f'<details class="item {esc(status)}" data-key="{esc(fid)}"><summary>'
            f'<span class="mark">{mark}</span>'
            f'<span class="line">{dot(kind)}<span class="id">{esc(fid)}</span> {inline(f.get("name"))}</span>'
            f'<span class="tags">{tags}</span>{chev()}</summary>'
            f'<dl class="facts">{body}</dl></details>')


def milestone(m):
    short, _, rest = (m["name"] or "").partition(" — ")
    name = (f'<strong>{esc(short)}</strong> {esc(rest)}' if rest else f'<strong>{esc(short)}</strong>')
    segs = "".join(f'<span class="seg {esc(i["status"])}" title="{esc(i["id"])} · {esc(i["name"])} '
                   f'({esc(i["status"])})"></span>' for i in m["items"])
    left = [i for i in m["items"] if i["status"] != "done"]
    if not m["items"]:
        foot = "No items yet"
    elif not left:
        foot = '<span class="ok">✓</span> Complete'
    elif len(left) == 1:
        foot = f'Left: <span class="id">{esc(left[0]["id"])}</span> {inline(left[0]["name"])}'
    else:
        foot = "Left: " + ", ".join(f'<span class="id">{esc(i["id"])}</span>' for i in left)
    dod = (f'<p>{inline(m["definition_of_done"])}</p>' if m["definition_of_done"]
           else empty("No definition of done."))
    return (f'<details class="ms" data-key="ms:{esc(m["name"])}"><summary>'
            f'<span class="ms-name">{name}</span><span class="num">{m["done"]}/{m["total"]}</span>{chev()}'
            f'<span class="segs" role="img" aria-label="{m["done"]} of {m["total"]} done">{segs}</span>'
            f'<span class="ms-left">{foot}</span></summary>'
            f'<div class="ms-dod"><span class="label">Definition of done</span>{dod}</div></details>')


# ── Score chart: one series, so no legend; the title names it ──

def nice_ticks(lo, hi, n=4):
    if hi == lo:
        lo, hi = lo - 1, hi + 1
    raw = (hi - lo) / n
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    start, end = math.floor(lo / step) * step, math.ceil(hi / step) * step
    return [round(start + i * step, 10) for i in range(int(round((end - start) / step)) + 1)]


def fmt(v):
    return f"{v:,.0f}" if abs(v) >= 100 or v == int(v) else f"{v:,.2f}".rstrip("0").rstrip(".")


def score_chart(pts):
    W, Ht, L, R, T, B = 640, 210, 44, 64, 14, 30
    ticks = nice_ticks(min(p["value"] for p in pts), max(p["value"] for p in pts))
    lo, hi = ticks[0], ticks[-1]
    x = lambda i: L + i * (W - L - R) / (len(pts) - 1)
    y = lambda v: T + (hi - v) / (hi - lo) * (Ht - T - B)
    grid = "".join(f'<line class="grid" x1="{L}" x2="{W - R}" y1="{y(t):.1f}" y2="{y(t):.1f}"/>'
                   f'<text class="tick" x="{L - 8}" y="{y(t) + 4:.1f}" text-anchor="end">{fmt(t)}</text>'
                   for t in ticks)
    line = " ".join(f"{x(i):.1f},{y(p['value']):.1f}" for i, p in enumerate(pts))
    last = pts[-1]
    data = [{"x": round(x(i), 1), "y": round(y(p["value"]), 1), "date": p["date"], "score": p["score"],
             "commit": p["commit"], "notes": p["notes"]} for i, p in enumerate(pts)]
    svg = (f'<svg class="chart" viewBox="0 0 {W} {Ht}" role="img" '
           f'aria-label="Score over time, {len(pts)} measurements, latest {esc(last["score"])}">'
           f'{grid}<line class="axis" x1="{L}" x2="{W - R}" y1="{Ht - B}" y2="{Ht - B}"/>'
           f'<text class="tick" x="{L}" y="{Ht - 8}">{esc(pts[0]["date"])}</text>'
           f'<text class="tick" x="{W - R}" y="{Ht - 8}" text-anchor="end">{esc(last["date"])}</text>'
           f'<polyline class="series" points="{line}"/>'
           f'<circle class="dot" cx="{x(len(pts) - 1):.1f}" cy="{y(last["value"]):.1f}" r="4.5"/>'
           f'<text class="end-label" x="{x(len(pts) - 1) + 10:.1f}" y="{y(last["value"]) + 4:.1f}">'
           f'{esc(fmt(last["value"]))}</text>'
           f'<line class="cross" y1="{T}" y2="{Ht - B}" x1="0" x2="0" visibility="hidden"/>'
           f'<circle class="dot hover-dot" r="5" cx="0" cy="0" visibility="hidden"/>'
           f'<rect class="hit" x="{L}" y="0" width="{W - L - R}" height="{Ht}"/></svg>')
    return f'<div class="chart-wrap" data-points="{esc(json.dumps(data))}">{svg}<div class="tip" hidden></div></div>'


def scores(history):
    """The trend when the scores are plain numbers, and the table in any case."""
    if not history:
        return empty("No score yet — append a row to Score history in `harness/EVAL.md` after each "
                     "meaningful change.")
    pts = [h for h in history if h["value"] is not None]
    chart = score_chart(pts) if len(pts) >= 2 else ""
    rows = "".join(f"<tr><td>{esc(p['date'])}</td><td>{esc(p['commit'])}</td><td>{esc(p['score'])}</td>"
                   f"<td>{inline(p['notes'])}</td></tr>" for p in reversed(history))
    table = (f'<table><thead><tr><th>Date</th><th>Commit</th><th>Score</th><th>Notes</th></tr></thead>'
             f'<tbody>{rows}</tbody></table>')
    return chart + fold("scores", "Score history", table, len(history))


# ── The page ──

def render(s, refresh=RELOAD):
    b, st, g, gt, ck = s["backlog"], s["state"], s["goal"], s["git"], s["checks"]

    # header: name, health and context on one line, the goal under it
    level = st["health_level"]
    meta = [f'<span class="pill {level or "none"}">Health {esc(st["health"] or "not set")}</span>']
    if st["phase"]:
        meta.append(f'<span>Phase <strong>{esc(st["phase"])}</strong></span>')
    if gt.get("repo"):
        meta.append(f'<span>Branch <code>{esc(gt["branch"])}</code></span>')
    last_pass = ago(ck["last_pass"])
    meta.append(f'<span>Last green check <strong>{esc(last_pass or "never")}</strong></span>')
    goal = (f'<p class="goal">{inline(g["target"])}</p>' if g["target"]
            else empty("No target yet — set it in `harness/GOAL.md` (or run `/harness-init`)."))
    warn = (f'<div class="warn" role="status"><strong>⚠ Needs attention</strong>{ul(map(inline, s["warnings"]))}</div>'
            if s["warnings"] else "")

    # overview: how far, what's next, the milestones
    open_split = "".join(f'<li>{dot(k)}<strong>{n}</strong> {esc(k)}</li>'
                         for k, n in sorted(b["open_types"].items(), key=lambda kv: (
                             TYPES.index(kv[0]) if kv[0] in TYPES else 9, kv[0])))
    progress = (f'<section class="card progress"><h2 class="label">Backlog done</h2>'
                f'<p class="hero">{b["percent"]}%</p>{meter(b["done"], b["total"], "Backlog done")}'
                f'<p class="sub">{b["done"]} of {b["total"]} items done</p>'
                + (f'<p class="label open-label">Open</p><ul class="split">{open_split}</ul>' if open_split else "")
                + "</section>")
    cur = (b["in_progress"] or b["todo"] or [None])[0]
    if cur:
        kind = cur.get("type", "feature")
        prio = str(cur.get("priority", "")).upper()
        nxt = (f'<p class="next-title">{dot(kind)}<span class="id">{esc(cur["id"])}</span> {inline(cur["name"])}</p>'
               f'<p class="sub">{esc(kind)}{" · " + esc(prio) if prio else ""} · '
               + ("in progress" if cur in b["in_progress"] else "say “ship the next one” or <code>/ship</code>")
               + "</p>")
    else:
        nxt = empty("Backlog empty — ask the strategist for ideas, or `./harness/scripts/feature.sh add …`")
    extra = []
    if st["working_on"]:
        extra.append(f'<p class="aside"><span class="label">Working on</span>{inline(st["working_on"])}</p>')
    nxt_card = (f'<section class="card next"><h2 class="label">'
                f'{"In progress" if b["in_progress"] else "Next up"}</h2>{nxt}{"".join(extra)}</section>')
    ms = "".join(milestone(m) for m in b["milestones"]) or empty("No milestones in `harness/FEATURES.json`.")
    ms_card = f'<section class="card milestones"><h2 class="label">Milestones</h2>{ms}</section>'

    # backlog: one ordered list — what's next (in the order /ship takes it), then what's done, greyed
    ms_of = {}
    for m in b["milestones"]:
        short = (m["name"] or "").partition(" — ")[0][:12]
        for i in m["items"]:
            ms_of.setdefault(i["id"], []).append(short)
    groups = []
    if b["in_progress"]:
        groups.append(("In progress", b["in_progress"], lambda i: '▶<span class="sr"> in progress</span>'))
    groups.append(("Up next", b["todo"], lambda i: str(i + 1)))
    if b["blocked"]:
        groups.append(("Blocked", b["blocked"], lambda i: '⛔<span class="sr"> blocked</span>'))
    groups.append(("Done", b["shipped"], lambda i: '✓<span class="sr"> done</span>'))
    lists = ""
    for title, items, mark in groups:
        rows = "".join(item(f, mark(i), ms_of) for i, f in enumerate(items))
        lists += (f'<h3 class="group">{title} <span class="count">{len(items)}</span></h3>'
                  + (f'<div class="items">{rows}</div>' if rows else empty(
                      "Nothing left — ask the strategist for ideas, or `./harness/scripts/feature.sh add …`"
                      if title == "Up next" else "Nothing shipped yet.")))
    legend = "".join(f'<li>{dot(k)}{k}</li>' for k in TYPES)
    backlog = (f'<section class="card backlog"><div class="backlog-head"><h2>Backlog</h2>'
               f'<ul class="legend" aria-label="Item types">{legend}</ul>'
               f'<button type="button" class="ghost" data-expand>Expand all</button></div>{lists}</section>')

    # side: the goal's metrics, the session state, the activity — details folded
    metrics = ("".join(f'<li><span class="m-name">{inline(m["metric"])}</span>'
                       f'<span class="m-val"><strong>{inline(m["current"])}</strong>'
                       f'<span class="muted"> → {inline(m["target"])}</span></span></li>' for m in g["metrics"])
               if g["metrics"] else "")
    goal_card = (f'<section class="card"><h2>Goal metrics</h2>'
                 + (f'<ul class="metrics">{metrics}</ul>' if metrics else
                    empty("No success metric yet — `harness/GOAL.md`."))
                 + scores(s["eval"]["history"]) + "</section>")

    now = [(k, v) for k, v in (("Last session", st["last_session"]), ("Active plan", s["plan"]["task"])) if v]
    state = [f'<dl class="now">{"".join(f"<dt>{k}</dt><dd>{inline(v)}</dd>" for k, v in now)}</dl>' if now else
             empty("`harness/STATE.md` not filled in yet — it's updated at the end of each session.")]
    if st["blockers"]:
        state.append('<h3>Blockers</h3>' + ul(
            f'<span class="status-critical">⛔</span> {inline(x["blocker"])}'
            + (f' — <span class="muted">{inline(x["impact"])}</span>' if x["impact"] else "")
            for x in st["blockers"]))
    if st["stalls"]:
        state.append("<h3>Stalls</h3>" + ul(map(inline, st["stalls"])))
    if st["next"]:
        state.append(fold("next", "Next steps", ul(map(inline, st["next"]), "list ordered"), len(st["next"])))
    if st["open_questions"]:
        state.append(fold("questions", "Open questions", ul(map(inline, st["open_questions"])),
                          len(st["open_questions"])))
    state_card = f'<section class="card"><h2>State</h2>{"".join(state)}</section>'

    act = []
    if gt.get("repo"):
        if gt["uncommitted"]:
            act.append(fold("uncommitted", "Uncommitted", ul(
                (f"<code>{esc(l)}</code>" for l in gt["uncommitted"][:12]), "list plain"), len(gt["uncommitted"])))
        act.append(fold("commits", "Commits", ul(
            (f'<span class="date">{esc(c["date"])}</span><code>{esc(c["hash"])}</code> {esc(c["subject"])}'
             for c in gt["commits"]), "list plain") if gt["commits"] else empty("No commits yet."),
            len(gt["commits"])))
    else:
        act.append(empty("Not a git repository."))
    if s["decisions"]:
        act.append(fold("decisions", "Decisions", ul(
            (f'<span class="date">{esc(d["date"])}</span>{inline(d["title"])}'
             + (f' <span class="muted">({esc(d["status"])})</span>'
                if d["status"] and d["status"] != "accepted" else "")
             for d in s["decisions"]), "list plain"), len(s["decisions"])))
    if ck["loop_log"]:
        act.append(fold("loop", "Unattended loop" + (" — stopped" if ck["loop_stopped"] else ""),
                        f'<pre class="log">{esc(chr(10).join(ck["loop_log"]))}</pre>'))
    activity_card = f'<section class="card"><h2>Activity</h2>{"".join(act)}</section>'

    title = f'{s["project"]} — harness'
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{f'<meta http-equiv="refresh" content="{refresh}">' if refresh else ""}
<title>{esc(title)}</title>
<style>{CSS}</style></head>
<body><main class="wrap">
<header class="top"><div class="head-row"><h1>{esc(s["project"])}</h1><div class="meta">{"".join(meta)}</div></div>
{goal}</header>
{warn}
<div class="overview">{progress}{nxt_card}{ms_card}</div>
<div class="layout">{backlog}<aside class="side">{goal_card}{state_card}{activity_card}</aside></div>
<footer>Generated {esc(s["generated"].replace("T", " ")[:16])} · rewritten at the end of each agent turn, reloads
every {refresh} s · by hand: <code>./harness/scripts/dashboard.py</code> · as JSON: <code>./harness/scripts/state.py</code></footer>
</main><script>{JS}</script></body></html>
"""


CSS = """
:root{color-scheme:light;--page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink-2:#52514e;--muted:#898781;
--grid:#e1e0d9;--axis:#c3c2b7;--border:rgba(11,11,11,.10);--accent:#2a78d6;--track:#cde2fb;--wash:#f0efec;
--good:#0ca30c;--warning:#fab219;--critical:#d03b3b;--t-feature:#2a78d6;--t-bug:#eb6834;--t-debt:#1baf7a}
@media (prefers-color-scheme:dark){:root{color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;--ink:#fff;
--ink-2:#c3c2b7;--muted:#898781;--grid:#2c2c2a;--axis:#383835;--border:rgba(255,255,255,.10);--accent:#3987e5;
--track:#0d366b;--wash:#262624;--t-feature:#3987e5;--t-bug:#d95926;--t-debt:#199e70}}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
.wrap{max-width:1280px;margin:0 auto;padding:24px 16px 48px;display:flex;flex-direction:column;gap:16px}
h1{font-size:24px;line-height:1.2;margin:0;font-weight:650}
h2{font-size:15px;margin:0 0 12px;font-weight:650}
h3{font-size:12px;margin:16px 0 8px;font-weight:600;color:var(--ink-2);text-transform:uppercase;letter-spacing:.04em}
p{margin:0}
code{font:12px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--wash);padding:1px 5px;border-radius:4px;
overflow-wrap:anywhere}
s{color:var(--muted)}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.label{display:block;font-size:12px;font-weight:600;color:var(--ink-2);text-transform:uppercase;letter-spacing:.04em;
margin:0 0 8px}
.muted,.sub{color:var(--ink-2)}
.sub{font-size:13px;margin-top:6px}
.empty{color:var(--ink-2);font-size:13px}
.num{font-variant-numeric:tabular-nums}
.id{font:600 12px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--ink-2)}
.ok{color:var(--good)}
.status-critical{color:var(--critical)}

/* header */
.head-row{display:flex;flex-wrap:wrap;align-items:center;gap:8px 20px}
.meta{display:flex;flex-wrap:wrap;gap:6px 16px;align-items:center;color:var(--ink-2);font-size:13px}
.meta strong{color:var(--ink);font-weight:600}
.pill{display:inline-flex;align-items:center;padding:1px 10px;border:1px solid var(--border);border-radius:999px;
color:var(--ink);background:var(--surface)}
.pill.good{border-color:var(--good)}.pill.warning{border-color:var(--warning)}.pill.critical{border-color:var(--critical)}
.goal{font-size:15px;margin-top:8px;max-width:80ch;color:var(--ink-2)}
.warn{border:1px solid var(--border);border-left:3px solid var(--warning);background:var(--surface);border-radius:10px;
padding:8px 14px;font-size:13px}
.warn ul{margin:2px 0 0;padding-left:18px}

/* cards and layout: one column in portrait, side column in landscape */
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:16px 18px;min-width:0}
.overview{display:grid;gap:12px;grid-template-columns:minmax(0,1fr)}
@media (min-width:640px){.overview{grid-template-columns:minmax(0,.8fr) minmax(0,1.2fr)}.milestones{grid-column:1/-1}}
@media (min-width:1100px){.overview{grid-template-columns:240px minmax(0,1fr) minmax(0,1.3fr)}
.milestones{grid-column:auto}}
.layout{display:grid;gap:16px;grid-template-columns:minmax(0,1fr)}
@media (min-width:1100px){.layout{grid-template-columns:minmax(0,1fr) 380px;align-items:start}}
.side{display:flex;flex-direction:column;gap:16px;min-width:0}

/* overview */
.hero{font-size:48px;font-weight:600;line-height:1.1;margin:0 0 12px}
.meter{height:8px;border-radius:4px;background:var(--track);overflow:hidden}
.meter span{display:block;height:100%;background:var(--accent);border-radius:4px}
.open-label{margin:16px 0 6px}
.split{list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:4px 14px;font-size:13px;color:var(--ink-2)}
.split strong{color:var(--ink);font-weight:600;margin-right:3px}
.next-title{font-size:18px;font-weight:600;line-height:1.35}
.next-title .id{font-size:13px;margin-right:4px}
.aside{margin-top:14px;padding-top:12px;border-top:1px solid var(--grid);font-size:13px;color:var(--ink-2)}
.aside .label{margin-bottom:2px}
.ms+.ms{border-top:1px solid var(--grid)}
.ms>summary{display:grid;grid-template-columns:minmax(0,1fr) auto 14px;grid-template-areas:"name num chev" "bar bar bar"
"left left left";gap:6px 10px;align-items:center;padding:8px 0}
.ms:first-of-type>summary{padding-top:0}
.ms-name{grid-area:name;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ms-name strong{margin-right:4px}
.ms>summary .num{grid-area:num;font-weight:600}
.ms>summary .chev{grid-area:chev}
.segs{grid-area:bar;display:flex;gap:2px;height:8px}
.seg{flex:1;background:var(--track);border-radius:2px}
.seg:first-child{border-radius:4px 2px 2px 4px}.seg:last-child{border-radius:2px 4px 4px 2px}
.seg:only-child{border-radius:4px}
.seg.done{background:var(--accent)}
.seg.in_progress{background:repeating-linear-gradient(135deg,var(--accent) 0 3px,var(--track) 3px 6px)}
.seg.blocked{background:var(--critical)}
.ms-left{grid-area:left;font-size:13px;color:var(--ink-2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ms-left .id{margin-right:2px}
.ms-dod{padding:2px 0 10px;font-size:13px;color:var(--ink-2)}
.ms-dod .label{margin-bottom:2px}

/* disclosure: native details, custom chevron */
summary{cursor:pointer;list-style:none;border-radius:6px}
summary::-webkit-details-marker{display:none}
summary:focus-visible,button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.chev{width:14px;height:20px;display:flex;align-items:center;justify-content:center}
.chev::before{content:"";width:6px;height:6px;border-right:1.5px solid var(--muted);border-bottom:1.5px solid var(--muted);
transform:rotate(-45deg);transition:transform .15s ease-out}
details[open]>summary .chev::before{transform:rotate(45deg)}
@media (prefers-reduced-motion:reduce){.chev::before{transition:none}}

/* backlog list */
.backlog-head{display:flex;flex-wrap:wrap;align-items:center;gap:8px 16px;margin-bottom:4px}
.backlog-head h2{margin:0}
.legend{list-style:none;margin:0;padding:0;display:flex;gap:12px;font-size:12px;color:var(--ink-2)}
.ghost{margin-left:auto;font:inherit;font-size:13px;color:var(--ink-2);background:none;border:1px solid var(--border);
border-radius:8px;padding:3px 10px;cursor:pointer}
.ghost:hover{background:var(--wash);color:var(--ink)}
.group{margin:20px 0 4px}
.count{display:inline-block;min-width:20px;padding:0 6px;border-radius:999px;background:var(--wash);
color:var(--ink-2);text-align:center;font-size:11px;font-weight:600;letter-spacing:0;text-transform:none}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:7px;vertical-align:1px;
background:var(--t-feature)}
.dot.t-bug{background:var(--t-bug)}.dot.t-debt{background:var(--t-debt)}
.item+.item{border-top:1px solid var(--grid)}
.item>summary{display:grid;grid-template-columns:26px minmax(0,1fr) auto 14px;
grid-template-areas:"mark line tags chev";gap:2px 10px;align-items:start;padding:8px 6px;line-height:20px}
.item>summary:hover{background:var(--wash)}
.mark{grid-area:mark;text-align:right;font:600 12px/20px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--muted)}
.todo:first-child .mark{color:var(--accent)}
.line{grid-area:line;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.item[open] .line{display:block}
.line .id{margin-right:2px}
.tags{grid-area:tags;display:flex;gap:6px;align-items:center;white-space:nowrap;min-height:20px}
.item>summary .chev{grid-area:chev}
.chip{border:1px solid var(--border);border-radius:5px;padding:0 5px;font-size:11px;font-weight:600;line-height:17px;
color:var(--ink-2)}
.chip.ms{border-color:transparent;background:var(--track);color:var(--ink)}
.chip.q{border-color:var(--critical);color:var(--ink)}
.when{font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums;min-width:44px;text-align:right}
@media (max-width:560px){.item>summary{grid-template-columns:22px minmax(0,1fr) 14px;
grid-template-areas:"mark line chev" ". tags ."}.tags{min-height:0}}
.done>summary{color:var(--muted)}
.done .mark{color:var(--good)}
.done .line .id,.done .chip{color:var(--muted)}
.done .dot,.done .chip.ms{opacity:.45}
.facts{margin:0;padding:2px 6px 12px 42px;display:grid;grid-template-columns:max-content minmax(0,1fr);gap:4px 14px;
font-size:13px}
.facts dt{color:var(--muted)}.facts dd{margin:0;color:var(--ink-2)}
@media (max-width:560px){.facts{padding-left:38px;grid-template-columns:minmax(0,1fr)}.facts dd{margin-bottom:6px}}

/* side */
.metrics{list-style:none;margin:0;padding:0}
.metrics li{padding:8px 0;border-top:1px solid var(--grid);display:flex;flex-direction:column;gap:2px}
.metrics li:first-child{border-top:0;padding-top:0}
.m-name{font-size:13px;color:var(--ink-2)}
.m-val{font-size:13px}
.now{display:grid;grid-template-columns:max-content minmax(0,1fr);gap:4px 14px;margin:0;font-size:13px}
.now dt{color:var(--muted)}.now dd{margin:0}
.fold{border-top:1px solid var(--grid);margin-top:12px}
.fold>summary{display:flex;align-items:center;gap:8px;padding:10px 0 0;font-weight:600;font-size:13px}
.fold>summary .chev{margin-left:auto}
.fold-body{padding-top:8px;font-size:13px}
.list{margin:0;padding-left:18px}.list li+li{margin-top:5px}
.list.ordered{list-style:decimal}
.list.plain{list-style:none;padding:0}
.date{font-variant-numeric:tabular-nums;color:var(--muted);font-size:12px;margin-right:8px}
.list.plain code{margin-right:6px}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th{font-weight:600;color:var(--ink-2);text-align:left}
th,td{padding:5px 8px 5px 0;border-bottom:1px solid var(--grid);vertical-align:top}
.log{margin:0;font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap;overflow-wrap:anywhere;
color:var(--ink-2)}
footer{color:var(--muted);font-size:12px}

/* score chart (only when scores are plain numbers) */
.chart-wrap{position:relative;margin-top:12px}
.chart{width:100%;height:auto;display:block;overflow:visible}
.chart .grid{stroke:var(--grid);stroke-width:1}
.chart .axis{stroke:var(--axis);stroke-width:1}
.chart .tick{fill:var(--muted);font-size:11px;font-variant-numeric:tabular-nums}
.chart .series{fill:none;stroke:var(--accent);stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.chart .dot{fill:var(--accent);stroke:var(--surface);stroke-width:2}
.chart .end-label{fill:var(--ink);font-size:12px;font-weight:600}
.chart .cross{stroke:var(--axis);stroke-width:1}
.chart .hit{fill:transparent;cursor:crosshair}
.tip{position:absolute;pointer-events:none;background:var(--surface);border:1px solid var(--border);border-radius:8px;
padding:6px 9px;font-size:12px;box-shadow:0 4px 14px rgba(0,0,0,.08);max-width:240px;transform:translate(-50%,-110%)}
.tip strong{font-size:14px}
"""

JS = """
// the page reloads itself: what's unfolded and the scroll position survive it (per tab; works without storage)
let saved = {};
try { saved = JSON.parse(sessionStorage.getItem('harness-open') || '{}'); } catch (e) {}
const folds = [...document.querySelectorAll('details[data-key]')];
folds.forEach(d => {
  if (d.dataset.key in saved) d.open = saved[d.dataset.key];
  d.addEventListener('toggle', () => {
    saved[d.dataset.key] = d.open;
    try { sessionStorage.setItem('harness-open', JSON.stringify(saved)); } catch (e) {}
  });
});

const items = [...document.querySelectorAll('.backlog details.item')], all = document.querySelector('[data-expand]');
const sync = () => { all.textContent = items.length && items.every(d => d.open) ? 'Collapse all' : 'Expand all'; };
if (all) {
  all.addEventListener('click', () => { const open = !items.every(d => d.open); items.forEach(d => { d.open = open; }); sync(); });
  items.forEach(d => d.addEventListener('toggle', sync));
  sync();
}

document.querySelectorAll('.chart-wrap').forEach(w => {
  const pts = JSON.parse(w.dataset.points), svg = w.querySelector('svg'), tip = w.querySelector('.tip');
  const cross = svg.querySelector('.cross'), dot = svg.querySelector('.hover-dot'), hit = svg.querySelector('.hit');
  const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const hide = () => { tip.hidden = true; cross.setAttribute('visibility','hidden'); dot.setAttribute('visibility','hidden'); };
  hit.addEventListener('mousemove', e => {
    const m = svg.getScreenCTM().inverse(), p = new DOMPoint(e.clientX, e.clientY).matrixTransform(m);
    const n = pts.reduce((a, b) => Math.abs(b.x - p.x) < Math.abs(a.x - p.x) ? b : a);
    cross.setAttribute('x1', n.x); cross.setAttribute('x2', n.x); cross.setAttribute('visibility','visible');
    dot.setAttribute('cx', n.x); dot.setAttribute('cy', n.y); dot.setAttribute('visibility','visible');
    const s = svg.getBoundingClientRect().width / svg.viewBox.baseVal.width;
    tip.style.left = (n.x * s) + 'px'; tip.style.top = (n.y * s - 8) + 'px';
    tip.innerHTML = `<strong>${esc(n.score)}</strong><br>${esc(n.date)}${n.commit ? ' · ' + esc(n.commit) : ''}`
      + (n.notes ? `<br>${esc(n.notes)}` : '');
    tip.hidden = false;
  });
  hit.addEventListener('mouseleave', hide);
});

try { const y = Number(sessionStorage.getItem('harness-scroll')); if (y) window.scrollTo(0, y); } catch (e) {}
addEventListener('pagehide', () => { try { sessionStorage.setItem('harness-scroll', String(scrollY)); } catch (e) {} });
"""


def write(refresh=RELOAD):
    page = render(collect(), refresh)
    OUT.write_text(page, encoding="utf-8")
    return OUT


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Write the project dashboard to harness/dashboard.html.")
    ap.add_argument("--open", action="store_true", help="open the page in the browser")
    ap.add_argument("--watch", nargs="?", const=5, type=int, metavar="N",
                    help="rewrite the page every N seconds (default 5); Ctrl-C to stop")
    a = ap.parse_args()
    out = write(a.watch or RELOAD)
    print(f"  ✓ {out.relative_to(ROOT)}")
    if a.open:
        webbrowser.open(out.as_uri())
    if a.watch:
        print(f"  ↻ rewriting every {a.watch}s — Ctrl-C to stop")
        try:
            while True:
                time.sleep(a.watch)
                write(a.watch)
        except KeyboardInterrupt:
            pass
