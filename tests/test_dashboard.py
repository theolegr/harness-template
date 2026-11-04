#!/usr/bin/env python3
"""Tests for state.py and dashboard.py: what waits on the user (WAITING.md), and the published pages.

Run: python3 tests/test_dashboard.py   (no dependencies; exit code 1 on failure)
Each check reads a small project written to a temp folder, as state.py reads a real one.
"""
import atexit
import json
import pathlib
import shutil
import sys
import tempfile

# no __pycache__ next to the scripts: init-harness.sh copies everything under project/
sys.dont_write_bytecode = True

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "project/harness/scripts"))
import state  # noqa: E402
import dashboard  # noqa: E402

WAITING_MD = """# WAITING.md

> Last numbers: Q9 · A3

## Actions

- **A2** — Paste the Stripe key into `.env` · Done when: `stripe whoami` answers · By: 2999-01-01
  1. Developers → API keys
  2. Copy the test key
- **A3** — Call the accountant · By: 2000-01-01
<!-- - **A9** — a commented-out example -->

## Questions

- **Q3** — Error copy to OK: “That didn't save.” (B-002)
- **Q8** — Which domain: A) a.com B) b.com? See https://example.com/domains/ · Reco: A · Blocks: F-011
- **Q9** — Gates M3; asked again in A2 · Owner: the user · see https://example.com/q9
- An unnumbered one.

## Later

- **Q5** — A partnership, some day
"""

STATE_MD = """# STATE.md
## Now
- **Health**: 🟢 fine
## Open questions

> Last number: Q7

- **Q7** — An old question, not moved yet (OD-04)
- <question> → <who/what will answer it>
"""

FEATURES = {
    "project": "Demo",
    "features": [
        {"id": "F-010", "name": "Custom domain", "type": "feature", "status": "blocked", "priority": "p1",
         "blocked": "waiting on the user: a domain name (Q8), the key (A2), A1, A54 of the research, Q4"},
        {"id": "F-011", "name": "Export", "type": "feature", "status": "todo", "priority": "p1",
         "blocked": None},
        {"id": "F-012", "name": "Payments", "type": "feature", "status": "blocked", "priority": "p1",
         "blocked": "waiting on the user: A2"},
        {"id": "F-001", "name": "Shipped", "type": "feature", "status": "done", "priority": "p1"},
    ],
    "milestones": [
        {"name": "M3 — Export", "definition_of_done": "Q9 and OD-04 are decided first.", "features": []},
        {"name": "M1 — Done", "definition_of_done": "Q9 was mentioned once.", "features": ["F-001"]},
    ],
}

OPEN_DECISIONS = """# OPEN-DECISIONS.md

| ID | Topic | Blocks | Current default in the code |
|---|---|---|---|
| OD-01 | Logo colours | final art | grey placeholder |
| OD-04 | Where the data lives | export (M3), F-011 | on the device |

---

## OD-01 — Logo colours

- **Context**: a warm palette is the leading idea,
  wrapped on two lines.
  - a nested option

## OD-04 — Where the data lives

The tension, in a paragraph.
"""

ARTIFACTS = """# ARTIFACTS.md

| Updated | Page | What | Status |
|---|---|---|---|
| 2026-10-08 | [Research](https://claude.ai/artifact/abc) | competitor review, `draft` | **current** |
| 2026-10-01 | [Bad](javascript:alert(1)) | not a web link | current |
| 2026-09-29 | [Old canvas](https://claude.ai/artifact/old) | early sketches | **archived** |
| <date> | [<title>](<url>) | <what> | <status> |
"""

failed = 0


def check(name, ok, got=None):
    global failed
    failed += not ok
    print(f"  {'✓' if ok else '✗'} {name}" + ("" if ok else f"   → got {got!r}"))


def project(files):
    """A temp project holding files; state.py reads it."""
    tmp = pathlib.Path(tempfile.mkdtemp())
    atexit.register(shutil.rmtree, tmp, ignore_errors=True)
    for rel, text in files.items():
        (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp / rel).write_text(text if isinstance(text, str) else json.dumps(text), encoding="utf-8")
    state.ROOT, state.H = tmp, tmp / "harness"
    return state.collect()


def main():
    print("── WAITING.md: actions, questions, later")
    s = project({"harness/WAITING.md": WAITING_MD, "harness/FEATURES.json": FEATURES,
                 "harness/STATE.md": "## Now\n- **Health**: 🟢 fine\n", "harness/ARTIFACTS.md": ARTIFACTS})
    w = s["waiting"]
    acts, qs = w["actions"], w["questions"]
    check("actions: the overdue one first, the commented example left out", [r["id"] for r in acts] == ["A3", "A2"],
          [r["id"] for r in acts])
    check("questions: file order (no date, Q8 blocks the most first)", [r["id"] for r in qs] == ["Q8", "Q3", "Q9", None],
          [r["id"] for r in qs])
    check("later: kept apart", [r["id"] for r in w["later"]] == ["Q5"], w["later"])
    a2 = acts[1]
    check("A2: gist without its fields", a2["text"] == "Paste the Stripe key into `.env`", a2["text"])
    check("A2: fields", a2["fields"] == [["Done when", "`stripe whoami` answers"], ["By", "2999-01-01"]], a2["fields"])
    check("A2: steps kept as its body", a2["body"] == "1. Developers → API keys\n2. Copy the test key", a2["body"])
    check("A2: due, not overdue", (a2["due"], a2["overdue"]) == ("2999-01-01", False), (a2["due"], a2["overdue"]))
    check("A3: overdue, counted", acts[0]["overdue"] and w["overdue"] == 1, (acts[0], w["overdue"]))
    check("A2 blocks the items whose reason cites it", a2["blocks"] == ["F-010", "F-012"], a2["blocks"])
    q8 = qs[0]
    check("Q8 blocks F-011 (its Blocks field) and F-010 (cited)", q8["blocks"] == ["F-011", "F-010"], q8["blocks"])
    check("Q9: milestone M3, not the complete M1", qs[2]["milestones"] == ["M3 — Export"], qs[2]["milestones"])
    check("Q9 cites A2", qs[2]["cites"] == ["A2"], qs[2]["cites"])
    check("Q9: a field that isn't Blocks stays a field; a URL after · isn't one",
          (qs[2]["fields"], qs[2]["text"]) == ([["Owner", "the user"]], "Gates M3; asked again in A2 · see https://example.com/q9"),
          (qs[2]["fields"], qs[2]["text"]))
    check("last numbers", w["last"] == {"Q": 9, "A": 3}, w["last"])
    check("no warning: nothing left to move", state.waiting_warnings(w) == [], state.waiting_warnings(w))

    page = dashboard.render(s, refresh=0)
    check("card “Waiting on you”, 2 actions + 4 questions counted, 1 overdue, in the header",
          'id="waiting"' in page and 'Waiting on you <strong>6</strong> · <strong class="late">1 overdue</strong>' in page)
    check("two columns: Actions, then Questions", page.index(">Actions <") < page.index(">Questions <"))
    check("rows have anchors", all(f'id="{a}"' in page for a in ("w-A2", "w-Q8", "w-questions-4", "w-Q5", "item-F-010")))
    check("overdue shown on A3", '<span class="chip overdue" title="to settle by 2000-01-01">overdue · Jan 1</span>' in page)
    check("later folded", 'data-key="later"' in page)
    check("questions: the top 3 shown, the 4th (unnumbered, last in order) folded",
          'data-key="more:questions"><summary>1 more question<' in page
          and page.index('id="w-Q9"') < page.index('data-key="more:questions"') < page.index('id="w-questions-4"'))
    check("actions: 2, none folded", 'data-key="more:actions"' not in page)
    check("a blocked item links to the action it waits on", 'class="chip a" href="#w-A2"' in page)
    check("… and to the question", 'class="chip q" href="#w-Q8"' in page)
    check("A1 (given once, now settled): grey", 'class="chip a unknown"' in page and ">A1?<" in page)
    check("A54 (past the last number: not ours): no chip", "A54?" not in page and 'href="#w-A54"' not in page)
    check("Q4 (settled): grey", ">Q4?<" in page)
    check("Q8 links to the items it blocks", 'href="#item-F-011"' in page)
    check("A2's steps shown, numbered", '<ol class="list ordered"><li data-ol style="margin-left:0px">Developers → API keys'
          '</li><li data-ol style="margin-left:0px">Copy the test key</li></ol>' in page)
    check("Q9 links to A2", 'href="#w-A2">A2</a> <span class="muted">action</span>' in page)
    check("current page linked in the header", 'class="page" title="2026-10-08 — competitor review, draft"' in page)
    check("archived page folded", 'data-key="pages-archived"' in page and "Old canvas" in page)
    check("no javascript: link", "javascript:" not in page)
    check("no dead link", 'href="#w-"' not in page)

    print("── not moved yet: STATE.md's open questions, OPEN-DECISIONS.md")
    s = project({"harness/STATE.md": STATE_MD, "harness/FEATURES.json": FEATURES,
                 "harness/OPEN-DECISIONS.md": OPEN_DECISIONS})
    qs = s["waiting"]["questions"]
    check("read as questions, placeholder left out", [q["id"] for q in qs] == ["OD-04", "Q7", "OD-01"],
          [q["id"] for q in qs])
    od4 = qs[0]
    check("OD-04: topic, default, blocks from the table", (od4["text"], od4["fields"]) ==
          ("Where the data lives", [["Default", "on the device"], ["Blocks", "export (M3), F-011"]]), od4)
    check("OD-04: body from its section", od4["body"] == "The tension, in a paragraph.", od4["body"])
    check("OD-04: blocks open item F-011", od4["blocks"] == ["F-011"], od4["blocks"])
    check("OD-04: milestone M3", od4["milestones"] == ["M3 — Export"], od4["milestones"])
    check("Q7 cites OD-04", qs[1]["cites"] == ["OD-04"], qs[1]["cites"])
    check("no WAITING.md yet: no warning", state.waiting_warnings(s["waiting"]) == [], s["warnings"])
    page = dashboard.render(s, refresh=0)
    check("legacy rows tagged with their file", '<span class="chip src" title="not moved to WAITING.md yet">STATE.md</span>' in page)
    check("Q7 (open): linked, no grey chip", ">Q4?<" in page and ">Q8?<" not in page)
    check("nested list item indented", 'style="margin-left:16px">a nested option</li>' in page)
    check("a wrapped line stays in its item", "leading idea, wrapped on two lines.</li>" in page)
    s = project({"harness/STATE.md": STATE_MD, "harness/FEATURES.json": FEATURES,
                 "harness/OPEN-DECISIONS.md": OPEN_DECISIONS, "harness/WAITING.md": "## Actions\n"})
    check("WAITING.md added: a warning per file to move",
          [x.split(" — ")[0] for x in state.waiting_warnings(s["waiting"])] == ["1 open question still in harness/STATE.md",
                                                       "2 open questions still in harness/OPEN-DECISIONS.md"],
          s["warnings"])

    print("── links in text")
    cases = [
        ("see https://x.dev/a.", 'see <a href="https://x.dev/a" target="_blank" rel="noopener">https://x.dev/a</a>.'),
        ("[the canvas](https://x.dev/c)", '<a href="https://x.dev/c" target="_blank" rel="noopener">the canvas</a>'),
        ("(<https://x.dev>)", '(<a href="https://x.dev" target="_blank" rel="noopener">https://x.dev</a>)'),
        ("[x](javascript:alert(1))", "[x](javascript:alert(1))"),
        ("<script>**b**</script>", "&lt;script&gt;<strong>b</strong>&lt;/script&gt;"),
        ("`https://x.dev`", '<code><a href="https://x.dev" target="_blank" rel="noopener">https://x.dev</a></code>'),
        ("~~drop https://x.dev~~", '<s>drop <a href="https://x.dev" target="_blank" rel="noopener">https://x.dev</a></s>'),
        ("**https://x.dev**", '<strong><a href="https://x.dev" target="_blank" rel="noopener">https://x.dev</a></strong>'),
        ("(see https://w.org/A_(b))", '(see <a href="https://w.org/A_(b)" target="_blank" rel="noopener">https://w.org/A_(b)</a>)'),
        ("a \x000\x00 b", "a 0 b"),
        ("[A](https://w.org/A_(b))", '<a href="https://w.org/A_(b)" target="_blank" rel="noopener">A</a>'),
        ('https://x.dev/?a=1&b="2"', '<a href="https://x.dev/?a=1&amp;b=" target="_blank" rel="noopener">'
                                     'https://x.dev/?a=1&amp;b=</a>&quot;2&quot;'),
    ]
    for text, want in cases:
        got = dashboard.inline(text)
        check(repr(text), got == want, got)

    print("── a fresh project: nothing waits, no pages")
    s = project({"harness/STATE.md": (ROOT / "project/harness/STATE.md").read_text(encoding="utf-8"),
                 "harness/WAITING.md": (ROOT / "project/harness/WAITING.md").read_text(encoding="utf-8"),
                 "harness/ARTIFACTS.md": "| Updated | Page | What | Status |\n|---|---|---|---|\n"})
    w = s["waiting"]
    check("the template's files: no action, no question, no page",
          (w["actions"], w["questions"], w["later"], s["artifacts"]) == ([], [], [], []), (w, s["artifacts"]))
    page = dashboard.render(s, refresh=0)
    check("no card, no header link, no pages strip",
          'id="waiting"' not in page and "Waiting on you" not in page and 'class="pages"' not in page)

    print("── the overview: a bar by status, metrics against their target, long lists folded")
    done = [{"id": f"F-1{n:02}", "name": f"Shipped {n}", "type": "feature", "status": "done", "priority": "p2",
             "closed": f"2026-10-{n:02}"} for n in range(1, 7)]
    feats = {"project": "Demo", "features": [
        {"id": "F-200", "name": "Checkout", "type": "feature", "status": "in_progress", "priority": "p0"},
        {"id": "F-201", "name": "Portal", "type": "feature", "status": "blocked", "priority": "p1", "blocked": "A1"},
        {"id": "F-202", "name": "Export", "type": "feature", "status": "todo", "priority": "p1"},
        {"id": "F-203", "name": "Digest", "type": "feature", "status": "todo", "priority": "p2"}],
        "milestones": [{"name": "M2 — Launch", "definition_of_done": "Paid.",
                        "features": ["F-101", "F-200", "F-201", "F-202"]}]}
    s = project({"harness/FEATURES.json": feats, "harness/FEATURES-DONE.json": {"features": done},
                 "harness/STATE.md": "## Now\n- **Health**: 🟡 on track\n- **Working on**: F-200 — Checkout\n"
                                     "- **Last session**: 2026-11-03 — checkout started\n",
                 "harness/GOAL.md": "## Success metric\n\n| Metric | Current | Target | Measured by |\n|---|---|---|---|\n"
                                    "| Activation | 34% | 40% | x |\n| Teams | 1,200 | 1,000 | y |\n"
                                    "| p95 latency | 620ms | <500ms | z |\n| Revenue | — | $1K | w |\n",
                 "harness/EVAL.md": "## Score history\n\n| Date | Commit | Score | Notes |\n|---|---|---|---|\n"
                                    "| 2026-10-04 | a1 | 12 | |\n| 2026-10-22 | b2 | 31 | |\n| 2026-11-02 | c3 | 34 | |\n",
                 "harness/DECISIONS.md": "# DECISIONS\n\n## 2026-10-20 — PNG reports\n\n**Status**: accepted\n\n"
                                         "## 2026-10-09 — Postgres\n\n**Status**: superseded by 2026-10-20\n\n"
                                         "## YYYY-MM-DD — <Decision title>\n"})
    page = dashboard.render(s, refresh=0)
    check("decisions: one per section, the title its own line", [(d["title"], d["status"]) for d in s["decisions"]]
          == [("PNG reports", "accepted"), ("Postgres", "superseded by 2026-10-20")], s["decisions"])
    check("backlog split by status, in a bar and its key",
          'aria-label="Backlog: 6 done, 1 in progress, 1 blocked, 2 to do"' in page
          and '<span class="seg done" style="flex:6 1 0"' in page and "<strong>2</strong> to do" in page)
    check("health: the dot carries the color, the emoji is dropped",
          '<span class="pill warning"><span class="sdot" aria-hidden="true"></span>Health <strong>on track</strong>' in page)
    check("“Working on” naming the item in progress: not shown twice", ">Working on<" not in page)
    check("the last session sits under what's in progress", '<span class="label">Last session</span>2026-11-03' in page)
    check("a metric under its target: a meter, 85% full", 'aria-label="Activation: 34 of 40"' in page
          and 'aria-valuenow="85"' in page)
    check("a metric past its target: full, green, ticked", 'class="meter met"' in page and "target reached" in page)
    check("a lower-is-better target, a metric not measured yet: no meter",
          'aria-label="p95 latency' not in page and 'aria-label="Revenue' not in page)
    check("the latest score, and how it moved", '<span class="stat">34</span><span class="delta">+3 since Oct 22</span>'
          in page)
    check("Done: the 3 newest shown, the rest folded", '3 more shipped' in page and 'data-key="more:Done"' in page
          and page.index('id="item-F-104"') < page.index('data-key="more:Done"') < page.index('id="item-F-103"'))
    check("a shipped item's priority folds out, an open one's shows", page.count('class="prio"') == 4
          and "feature · P2 · closed 2026-10-06" in page)
    check("milestone: “3 left · 1 blocked”, the ids folded out with their names",
          '3 left · <span class="st-blocked">' in page and 'href="#item-F-202">F-202</a> Export' in page)

    print(f"\n{'all passed' if not failed else f'{failed} failed'}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
