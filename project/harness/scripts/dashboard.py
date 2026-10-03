#!/usr/bin/env python3
"""dashboard.py — the project's state as one HTML page.

  ./harness/scripts/dashboard.py              # writes harness/dashboard.html
  ./harness/scripts/dashboard.py --open       # … and opens it in the browser
  ./harness/scripts/dashboard.py --watch [N]  # rewrites it every N s (default 5); the page reloads itself

A view, never a source: everything comes from state.py, and the only file
written is harness/dashboard.html (git-ignored). One self-contained page — no
network, no dependency — readable offline and safe to attach to a message.
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


# ── Small helpers ──

def esc(s):
    return html.escape("" if s is None else str(s))


def inline(s):
    """Escape, then the bits of Markdown the harness files use: `code` and **bold**."""
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", esc(s))
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)


def ago(iso):
    if not iso:
        return None
    s = (datetime.datetime.now() - datetime.datetime.fromisoformat(iso)).total_seconds()
    for limit, unit, div in ((60, "", 0), (3600, "min", 60), (86400, "h", 3600), (math.inf, "d", 86400)):
        if s < limit:
            return "just now" if not div else f"{int(s // div)} {unit} ago"


def panel(title, body, cls=""):
    return f'<section class="panel {cls}"><h2>{esc(title)}</h2>{body}</section>'


def empty(text):
    return f'<p class="empty">{inline(text)}</p>'


def ul(items, cls="list"):
    return f'<ul class="{cls}">' + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


def meter(done, total, label):
    pct = done / total * 100 if total else 0
    return (f'<div class="meter" role="progressbar" aria-label="{esc(label)}" aria-valuemin="0" '
            f'aria-valuemax="{total}" aria-valuenow="{done}"><span style="width:{pct:.1f}%"></span></div>')


def card(f):
    prio, kind = str(f.get("priority", "")).upper(), f.get("type", "feature")
    acc, notes = f.get("acceptance") or "", f.get("notes") or ""
    top = f'<span class="id">{esc(f.get("id"))}</span>'
    if prio:
        top += f'<span class="chip">{esc(prio)}</span>'
    if kind != "feature":
        top += f'<span class="kind">{esc(kind)}</span>'
    body = f'<div class="card-name">{inline(f.get("name"))}</div>'
    if acc and not acc.startswith("<"):
        body += f'<div class="card-acc">{inline(acc)}</div>'
    if notes:
        body += f'<div class="card-note">{inline(notes)}</div>'
    return f'<li class="card"><div class="card-top">{top}</div>{body}</li>'


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


def score_chart(history):
    pts = [h for h in history if h["value"] is not None]
    if len(pts) < 2:
        return empty("Not enough scores yet for a trend — append a row to Score history in "
                     "`harness/EVAL.md` after each meaningful change.")
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
    rows = "".join(f"<tr><td>{esc(p['date'])}</td><td>{esc(p['commit'])}</td><td class=num>{esc(p['score'])}</td>"
                   f"<td>{inline(p['notes'])}</td></tr>" for p in reversed(history))
    return (f'<div class="chart-wrap" data-points="{esc(json.dumps(data))}">{svg}'
            f'<div class="tip" hidden></div></div>'
            f'<details><summary>Score table</summary><table><thead><tr><th>Date</th><th>Commit</th>'
            f'<th class=num>Score</th><th>Notes</th></tr></thead><tbody>{rows}</tbody></table></details>')


# ── The page ──

def render(s, refresh=None):
    b, st, g, gt, ck = s["backlog"], s["state"], s["goal"], s["git"], s["checks"]
    level = st["health_level"]
    # the health line carries its own icon (🟢 🟡 🔴); the border echoes it
    health = f'<span class="pill {level or "none"}">{esc(st["health"] or "Health not set")}</span>'
    meta = [health]
    if st["phase"]:
        meta.append(f'<span>Phase <strong>{esc(st["phase"])}</strong></span>')
    if gt.get("repo"):
        meta.append(f'<span>Branch <code>{esc(gt["branch"])}</code></span>')
    meta.append(f'<span>Generated {esc(s["generated"].replace("T", " ")[:16])} · '
                f'refresh: <code>./harness/scripts/dashboard.py</code></span>')
    goal = (f'<p class="goal">{inline(g["target"])}</p>' if g["target"]
            else empty("No target yet — set it in `harness/GOAL.md` (or run `/harness-init`)."))
    warn = (f'<div class="warn" role="status"><strong>⚠ Needs attention</strong>{ul(map(inline, s["warnings"]))}</div>'
            if s["warnings"] else "")

    # tiles — one hero figure (backlog progress), then four stat tiles
    open_n = sum(b["open_types"].values())
    split = " · ".join(f"{n} {k}" for k, n in sorted(b["open_types"].items())) or "nothing open"
    cur = b["in_progress"][0] if b["in_progress"] else None
    cur = inline(cur["id"] + " " + cur["name"]) if cur else "nothing started"
    last_pass = ago(ck["last_pass"])
    tiles = (
        f'<div class="tile hero"><div class="label">Backlog done</div>'
        f'<div class="value">{b["percent"]}%</div>'
        f'<div class="sub">{b["done"]} of {b["total"]} items</div>{meter(b["done"], b["total"], "Backlog done")}</div>'
        f'<div class="tile"><div class="label">In progress</div><div class="value">{len(b["in_progress"])}</div>'
        f'<div class="sub">{cur}</div></div>'
        f'<div class="tile"><div class="label">Blocked</div>'
        f'<div class="value">{len(b["blocked"])}</div>'
        f'<div class="sub">{"<span class=status-critical>⛔ needs a decision</span>" if b["blocked"] else "none"}</div></div>'
        f'<div class="tile"><div class="label">Open items</div><div class="value">{open_n}</div>'
        f'<div class="sub">{esc(split)}</div></div>'
        f'<div class="tile"><div class="label">Last green check</div>'
        f'<div class="value small">{esc(last_pass or "—")}</div>'
        f'<div class="sub">{"harness-check, via the Stop hook" if last_pass else "no pass recorded yet"}</div></div>')

    # backlog board
    more = len(b["todo"]) - 8
    col = lambda title, items, hint: (
        f'<div class="col"><h3>{title} <span class="count">{len(items)}</span></h3>'
        + (f'<ul class="cards">{"".join(card(f) for f in items)}</ul>' if items else empty(hint)) + "</div>")
    board = (col("In progress", b["in_progress"], "Nothing in progress — say “ship the next one”.")
             + col("Next up", b["todo"][:8], "Backlog empty — ask the strategist for ideas, or "
                   "`./harness/scripts/feature.sh add …`")
             + (f'<p class="more">+ {more} more in <code>harness/FEATURES.json</code></p>' if more > 0 else "")
             + col("Blocked", b["blocked"], "Nothing blocked."))
    board = f'<div class="board">{board}</div>'

    # milestones
    ms = ""
    for m in b["milestones"]:
        dod = f'<p class="dod">{inline(m["definition_of_done"])}</p>' if m["definition_of_done"] else ""
        ms += (f'<div class="milestone"><div class="ms-head"><strong>{esc(m["name"])}</strong>'
               f'<span class="num">{m["done"]}/{m["total"]}</span></div>'
               f'{meter(m["done"], m["total"], m["name"])}{dod}</div>')
    ms = ms or empty("No milestones in `harness/FEATURES.json`.")

    # goal metrics + score trend
    metrics = (f'<table class="metrics"><thead><tr><th>Metric</th><th class=num>Current</th>'
               f'<th class=num>Target</th></tr></thead><tbody>'
               + "".join(f'<tr><td>{inline(m["metric"])}</td><td class=num>{inline(m["current"])}</td>'
                         f'<td class=num>{inline(m["target"])}</td></tr>' for m in g["metrics"])
               + "</tbody></table>") if g["metrics"] else empty("No success metric yet — `harness/GOAL.md`.")
    measure = f'{metrics}<h3>Score history</h3>{score_chart(s["eval"]["history"])}'

    # state of the world (STATE.md, PLAN.md)
    now = [(k, v) for k, v in (("Working on", st["working_on"]), ("Last session", st["last_session"]),
                                ("Active plan", s["plan"]["task"])) if v]
    parts = [f'<dl class="now">{"".join(f"<dt>{k}</dt><dd>{inline(v)}</dd>" for k, v in now)}</dl>' if now else
             empty("`harness/STATE.md` not filled in yet — it's updated at the end of each session.")]
    if st["next"]:
        parts.append("<h3>Next</h3>" + ul(map(inline, st["next"]), "list ordered"))
    if st["blockers"]:
        parts.append("<h3>Blockers</h3>" + ul(
            f'<span class="status-critical">⛔</span> {inline(x["blocker"])}'
            + (f' — <span class="muted">{inline(x["impact"])}</span>' if x["impact"] else "")
            for x in st["blockers"]))
    if st["stalls"]:
        parts.append("<h3>Stalls</h3>" + ul(map(inline, st["stalls"])))
    if st["open_questions"]:
        parts.append("<h3>Open questions</h3>" + ul(map(inline, st["open_questions"])))

    # activity: shipped, decided, committed
    act = []
    act.append("<h3>Recently shipped</h3>" + (ul(
        f'<span class="date">{esc(f.get("closed", ""))}</span><span class="id">{esc(f["id"])}</span> {inline(f["name"])}'
        for f in b["recently_closed"]) if b["recently_closed"] else empty("Nothing shipped yet.")))
    if s["decisions"]:
        act.append("<h3>Decisions</h3>" + ul(
            f'<span class="date">{esc(d["date"])}</span>{inline(d["title"])}'
            + (f' <span class="muted">({esc(d["status"])})</span>'
               if d["status"] and d["status"] != "accepted" else "")
            for d in s["decisions"]))
    if gt.get("repo"):
        act.append("<h3>Commits</h3>" + (ul(
            f'<span class="date">{esc(c["date"])}</span><code>{esc(c["hash"])}</code> {esc(c["subject"])}'
            for c in gt["commits"]) if gt["commits"] else empty("No commits yet.")))
        if gt["uncommitted"]:
            act.append(f'<h3>Uncommitted <span class="count">{len(gt["uncommitted"])}</span></h3>'
                       + ul((f"<code>{esc(l)}</code>" for l in gt["uncommitted"][:12]), "list files"))
    else:
        act.append(empty("Not a git repository."))

    loop = ""
    if ck["loop_log"]:
        loop = panel("Unattended loop" + (" — stopped" if ck["loop_stopped"] else ""),
                     f'<pre class="log">{esc(chr(10).join(ck["loop_log"]))}</pre>', "wide")

    title = f'{s["project"]} — harness'
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{f'<meta http-equiv="refresh" content="{refresh}">' if refresh else ""}
<title>{esc(title)}</title>
<style>{CSS}</style></head>
<body><main class="wrap">
<header><h1>{esc(s["project"])}</h1>{goal}<div class="meta">{"".join(meta)}</div></header>
{warn}
<div class="tiles">{tiles}</div>
{panel("Backlog", board, "wide")}
<div class="grid2">{panel("Milestones", ms)}{panel("Goal & metric", measure)}</div>
<div class="grid2">{panel("State", "".join(parts))}{panel("Activity", "".join(act))}</div>
{loop}
</main><script>{JS}</script></body></html>
"""


CSS = """
:root{color-scheme:light;--page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink-2:#52514e;--muted:#898781;
--grid:#e1e0d9;--axis:#c3c2b7;--border:rgba(11,11,11,.10);--accent:#2a78d6;--track:#cde2fb;--wash:#f0efec;
--good:#0ca30c;--warning:#fab219;--critical:#d03b3b}
@media (prefers-color-scheme:dark){:root{color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;--ink:#fff;
--ink-2:#c3c2b7;--grid:#2c2c2a;--axis:#383835;--border:rgba(255,255,255,.10);--accent:#3987e5;--track:#0d366b;
--wash:#262624}}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
.wrap{max-width:1200px;margin:0 auto;padding:28px 16px 56px;display:flex;flex-direction:column;gap:16px}
h1{font-size:24px;line-height:1.2;margin:0 0 6px;font-weight:650}
h2{font-size:15px;margin:0 0 12px;font-weight:650}
h3{font-size:12px;margin:18px 0 8px;font-weight:600;color:var(--ink-2);text-transform:uppercase;letter-spacing:.04em}
h3:first-child{margin-top:0}
code{font:12px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--wash);padding:1px 5px;border-radius:4px;
overflow-wrap:anywhere}
.goal{font-size:16px;margin:0 0 10px;max-width:70ch}
header .empty{margin-bottom:10px}
.meta{display:flex;flex-wrap:wrap;gap:6px 18px;align-items:center;color:var(--ink-2);font-size:13px}
.pill{display:inline-flex;align-items:center;padding:2px 10px;border:1px solid var(--border);border-radius:999px;
color:var(--ink);background:var(--surface)}
.pill.good{border-color:var(--good)}.pill.warning{border-color:var(--warning)}.pill.critical{border-color:var(--critical)}
.warn{border:1px solid var(--border);border-left:3px solid var(--warning);background:var(--surface);border-radius:10px;
padding:10px 14px}
.warn ul{margin:4px 0 0;padding-left:18px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.tile,.panel{background:var(--surface);border:1px solid var(--border);border-radius:12px}
.tile{padding:14px 16px;min-width:0}
.tile .label{font-size:13px;color:var(--ink-2)}
.tile .value{font-size:28px;font-weight:600;line-height:1.25;margin-top:2px}
.tile .value.small{font-size:20px;line-height:1.7}
.tile .sub{font-size:13px;color:var(--ink-2);margin-top:2px;overflow-wrap:anywhere}
.tile.hero .value{font-size:48px;line-height:1.1}
.tile.hero .meter{margin-top:10px}
.tile.hero{grid-column:1/-1}
@media (min-width:720px){.tile.hero{grid-column:span 2}}
.meter{height:8px;border-radius:4px;background:var(--track);overflow:hidden}
.meter span{display:block;height:100%;background:var(--accent);border-radius:4px}
.panel{padding:16px 18px;min-width:0}
.grid2{display:grid;grid-template-columns:1fr;gap:16px}
@media (min-width:900px){.grid2{grid-template-columns:1fr 1fr}}
.board{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}
.col h3{margin-top:0}
.count{display:inline-block;min-width:20px;padding:0 6px;border-radius:999px;background:var(--wash);
color:var(--ink-2);text-align:center;font-size:11px;letter-spacing:0}
.cards{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:8px}
.card{border:1px solid var(--border);border-radius:10px;padding:9px 11px;background:var(--page)}
.card-top{display:flex;gap:8px;align-items:center;font-size:12px;color:var(--ink-2)}
.id{font:600 12px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--ink-2);margin-right:6px}
.card-top .id{margin:0}
.chip{border:1px solid var(--border);border-radius:5px;padding:0 5px;font-size:11px;font-weight:600}
.kind{font-size:11px;text-transform:uppercase;letter-spacing:.04em}
.card-name{font-weight:550;margin-top:3px}
.card-acc,.card-note{font-size:12.5px;color:var(--ink-2);margin-top:3px;display:-webkit-box;-webkit-line-clamp:2;
-webkit-box-orient:vertical;overflow:hidden}
.more{font-size:12.5px;color:var(--ink-2);margin:0;align-self:end}
.milestone+.milestone{margin-top:16px}
.ms-head{display:flex;justify-content:space-between;margin-bottom:6px}
.dod{font-size:12.5px;color:var(--ink-2);margin:6px 0 0}
.num{font-variant-numeric:tabular-nums;text-align:right}
table{width:100%;border-collapse:collapse;font-size:13px}
th{font-weight:600;color:var(--ink-2);text-align:left}
th,td{padding:6px 8px 6px 0;border-bottom:1px solid var(--grid);vertical-align:top}
details{margin-top:8px}summary{cursor:pointer;color:var(--ink-2);font-size:13px}
.list{margin:0;padding-left:18px}.list li+li{margin-top:4px}
.list.ordered{list-style:decimal}
.panel:has(.date) .list,.list.files{list-style:none;padding:0}
.date{font-variant-numeric:tabular-nums;color:var(--ink-2);font-size:12.5px;margin-right:8px}
.now{display:grid;grid-template-columns:max-content 1fr;gap:4px 14px;margin:0}
.now dt{color:var(--ink-2)}.now dd{margin:0}
.muted{color:var(--ink-2)}
.status-critical{color:var(--critical)}
.empty{color:var(--ink-2);margin:0;font-size:13px}
.log{margin:0;font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap;overflow-wrap:anywhere;
color:var(--ink-2)}
.chart-wrap{position:relative}
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
"""


def write(refresh=None):
    page = render(collect(), refresh)
    OUT.write_text(page, encoding="utf-8")
    return OUT


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Write the project dashboard to harness/dashboard.html.")
    ap.add_argument("--open", action="store_true", help="open the page in the browser")
    ap.add_argument("--watch", nargs="?", const=5, type=int, metavar="N",
                    help="rewrite the page every N seconds (default 5); Ctrl-C to stop")
    a = ap.parse_args()
    out = write(a.watch)
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
