#!/usr/bin/env python3
"""Tests for state.py and dashboard.py: what waits on the user, and the published pages.

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

STATE_MD = """# STATE.md
## Now
- **Health**: 🟢 fine
## Open questions

> Last number: Q9

- **Q3** — Error copy to OK: “That didn't save.” (B-002)
- **Q8** — Which domain do we buy? See https://example.com/domains/. Blocks the launch.
- **Q9** — OD-04 gates M3; also [the mockup](https://claude.ai/artifact/abc).
- An unnumbered one about OD-04.
- <question> → <who/what will answer it>
"""

FEATURES = {
    "project": "Demo",
    "features": [
        {"id": "F-010", "name": "Custom domain", "type": "feature", "status": "blocked", "priority": "p1",
         "blocked": "waiting on the user: a domain name (Q8)"},
        {"id": "F-011", "name": "Export", "type": "feature", "status": "todo", "priority": "p1",
         "blocked": None},
        {"id": "F-001", "name": "Shipped", "type": "feature", "status": "done", "priority": "p1"},
    ],
    "milestones": [
        {"name": "M3 — Export", "definition_of_done": "OD-04 is decided first.", "features": []},
        {"name": "M1 — Done", "definition_of_done": "OD-04 was mentioned once.", "features": ["F-001"]},
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

## OD-12 — Only a section

- no table row for this one
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
    print("── a project with open questions, OPEN-DECISIONS.md and ARTIFACTS.md")
    s = project({"harness/STATE.md": STATE_MD, "harness/FEATURES.json": FEATURES,
                 "harness/OPEN-DECISIONS.md": OPEN_DECISIONS, "harness/ARTIFACTS.md": ARTIFACTS})
    qs, ds = s["waiting"]["questions"], s["waiting"]["decisions"]
    check("open questions, placeholder left out", [q["id"] for q in qs] == ["Q3", "Q8", "Q9", None],
          [q["id"] for q in qs])
    check("Q8 blocks F-010 (cited in its reason)", qs[1]["blocks"] == ["F-010"], qs[1]["blocks"])
    check("Q9 cites OD-04", qs[2]["decisions"] == ["OD-04"], qs[2]["decisions"])
    check("decisions: table order, then sections", [d["id"] for d in ds] == ["OD-01", "OD-04", "OD-12"],
          [d["id"] for d in ds])
    od4 = ds[1]
    check("OD-04: topic, blocks, default from the table",
          (od4["title"], od4["blocks"], od4["default"]) == ("Where the data lives", "export (M3), F-011", "on the device"), od4)
    check("OD-04: body from its section", od4["body"] == "The tension, in a paragraph.", od4["body"])
    check("OD-04: asked in Q9 (an unnumbered question can't be cited)", od4["questions"] == ["Q9"],
          od4["questions"])
    check("OD-04: blocks open item F-011", od4["blocks_items"] == ["F-011"], od4["blocks_items"])
    check("OD-04: milestone M3 (no items yet), not the complete M1", od4["milestones"] == ["M3 — Export"],
          od4["milestones"])
    check("OD-12: title from its heading", ds[2]["title"] == "Only a section", ds[2]["title"])
    arts = s["artifacts"]
    check("artifacts: placeholder row left out", [a["title"] for a in arts] == ["Research", "Bad", "Old canvas"],
          [a["title"] for a in arts])
    check("artifacts: archived read from Status", [a["archived"] for a in arts] == [False, False, True],
          [a["archived"] for a in arts])
    check("artifacts: url", arts[0]["url"] == "https://claude.ai/artifact/abc", arts[0]["url"])

    page = dashboard.render(s, refresh=0)
    check("card “Waiting on you”, counted in the header",
          'id="waiting"' in page and 'Waiting on you <strong>7</strong>' in page)
    check("rows have anchors", all(f'id="{a}"' in page for a in ("q-Q8", "decision-OD-04", "item-F-010")))
    check("a blocked item's Q8 links to the question", 'href="#q-Q8"' in page)
    check("Q8 links to the item it blocks", 'href="#item-F-010"' in page)
    check("OD-04 shows its milestone", '<span class="chip ms">M3</span>' in page)
    check("open questions left the State panel", 'data-key="questions"' not in page)
    check("current page linked in the header", 'class="page" title="2026-10-08 — competitor review, draft"' in page)
    check("archived page folded", 'data-key="pages-archived"' in page and "Old canvas" in page)
    check("no javascript: link", "javascript:" not in page)
    check("nested list item indented", 'style="margin-left:16px">a nested option</li>' in page)
    check("a wrapped line stays in its item", "leading idea, wrapped on two lines.</li>" in page)
    check("no dead link to a question", 'href="#q-"' not in page)

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
    s = project({"harness/STATE.md": "## Open questions\n\n- <question> → <who/what will answer it>\n",
                 "harness/ARTIFACTS.md": "| Updated | Page | What | Status |\n|---|---|---|---|\n"})
    check("no questions, no decisions, no pages",
          (s["waiting"], s["artifacts"]) == ({"questions": [], "decisions": []}, []), (s["waiting"], s["artifacts"]))
    page = dashboard.render(s, refresh=0)
    check("no card, no header link, no pages strip",
          'id="waiting"' not in page and "Waiting on you" not in page and 'class="pages"' not in page)

    print(f"\n{'all passed' if not failed else f'{failed} failed'}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
