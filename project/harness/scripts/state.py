#!/usr/bin/env python3
"""state.py — the project's state as one JSON object.

Reads the harness files (GOAL, STATE, FEATURES, FEATURES-DONE, EVAL, PLAN,
DECISIONS, ARTIFACTS, and OPEN-DECISIONS when the project keeps one), git and
the loop's runtime files, and prints what they say. It never writes anything:
the files stay the source of truth, this is a view.

  ./harness/scripts/state.py            # JSON on stdout (for agents and scripts)

Used by harness-status.sh (backlog) and dashboard.py (the HTML page).
Placeholders (`<like this>`) and template choice lists (`a | b | c`) count as
"not filled in" and come out as null / are left out.
"""
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
H = ROOT / "harness"
TOKEN = re.compile(r"<([A-Za-z][^>]*)>")
CODE = re.compile(r"`([^`]*)`")
AUTOLINK = re.compile(r"<[^<>\s]*(?:://|@)[^<>\s]*>")
# what may precede a value: a list marker, ❌, a label (**Repo**:, Did:, "name":)
FIELD = re.compile(r'^\s*(?:[-*]\s+|\d+\.\s+)?(?:❌\s*)?(?:\*\*[^*]+\*\*:\s*|[A-Za-z][\w ]{0,30}:\s+|"[\w-]+":\s*)?')
RUNTIME = ("harness/.loop.log", "harness/.loop.stop", "harness/.check.ok", "harness/dashboard.html")
REQUIRED = ["AGENTS.md", "CLAUDE.md", "harness/GOAL.md", "harness/STATE.md", "harness/FEATURES.json",
            "harness/EVAL.md", "harness/PLAN.md", "harness/DECISIONS.md", "harness/guide/BOOT.md"]
PRIORITY = {"p0": 0, "p1": 1, "p2": 2, "p3": 3}
QREF = re.compile(r"\bQ\d+\b")   # an open question of STATE.md (Q1, Q2…), cited in a blocked item's reason
DID = re.compile(r"[A-Z][A-Z0-9]*-\d+")   # an id: F-003, OD-04
MDLINK = re.compile(r"\[([^\]]+)\]\(((?:[^()\s]|\([^()\s]*\))+)\)")   # the URL may hold (balanced) parentheses


# ── Markdown helpers ──

def read(rel):
    try:
        return (ROOT / rel).read_text(encoding="utf-8")
    except OSError:
        return ""


def placeholder(text):
    """True when text still holds a template placeholder:
    - a <…> with a space in it: <the target, in one sentence>, <e.g. Python>;
    - a value made of nothing but <…> and punctuation — a line, a list item, a table
      cell, a JSON string, what follows a label: <command>, **Repo**: <url>, "<criteria>",
      <F-XXX> — <what>, Did: <what>;
    - `code` holding only a <…>: `<cmd>`.
    A <…> inside a command or a path (npm run new <name>, feature.sh <id> <status>,
    `../<repo>-<topic>`) is an argument, not a placeholder; nor is an HTML tag with attributes,
    nor a Markdown autolink or email (<https://…>, <name@example.com>)."""
    if any(TOKEN.fullmatch(c.strip()) for c in CODE.findall(text)):
        return True
    text = AUTOLINK.sub("", CODE.sub("", text))
    if any(" " in m.group(1) and '="' not in m.group(1) for m in TOKEN.finditer(text)):
        return True
    for cell in text.split("|"):
        v = FIELD.sub("", cell)
        if TOKEN.search(v) and not re.search(r"\w", TOKEN.sub("", v)):
            return True
    return False


def filled(v):
    """The value, or None when it's empty, a placeholder or a template choice list."""
    v = (v or "").strip()
    if not v or placeholder(v) or " | " in v or v in ("—", "-"):
        return None
    return v


def section(md, title):
    """Body of the '## <title>…' section (up to the next '## '), comments removed."""
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    m = re.search(rf"^## {re.escape(title)}.*?$(.*?)(?=^## |\Z)", md, flags=re.M | re.S)
    return m.group(1) if m else ""


def bullets(text):
    out = []
    for line in text.splitlines():
        m = re.match(r"\s*(?:[-*]|\d+\.)\s+(.*)", line)
        if m and filled(m.group(1)):
            out.append(m.group(1).strip())
    return out


def header(text):
    """Lower-cased header cells of the first Markdown table in text."""
    for l in text.splitlines():
        if l.strip().startswith("|"):
            return [c.strip().lower() for c in l.strip().strip("|").split("|")]
    return []


def column(head, *names, default=None):
    """Index of the first header cell containing one of names, else default."""
    return next((i for i, h in enumerate(head) if any(n in h for n in names)), default)


def cell(row, i):
    return row[i] if i is not None and i < len(row) else ""


def mentions(text, ids):
    """The ids that text cites as whole words, in the order of ids."""
    return [i for i in ids if re.search(rf"(?<![\w-]){re.escape(i)}(?![\w-])", text or "")]


def table(text):
    """Rows of the first Markdown table in text, header and separator dropped."""
    rows = [l.strip() for l in text.splitlines() if l.strip().startswith("|")]
    out = []
    for r in rows[2:]:
        cells = [c.strip() for c in r.strip("|").split("|")]
        if any(cells):
            out.append(cells)
    return out


# ── Sections of the state ──

def goal():
    md = read("harness/GOAL.md")
    target = None
    for line in section(md, "Target").splitlines():
        if line.strip() and not line.startswith(">"):
            target = filled(line)
            break
    metrics = [{"metric": r[0], "current": r[1], "target": r[2], "measured_by": r[3] if len(r) > 3 else ""}
               for r in table(section(md, "Success metric"))
               if len(r) >= 3 and not r[0].lower().startswith("e.g.") and filled(r[0])]
    return {"target": target, "metrics": metrics}


def state():
    md = read("harness/STATE.md")
    now = {}
    for line in section(md, "Now").splitlines():
        m = re.match(r"\s*-\s+\*\*(.+?)\*\*:\s*(.*)", line)
        if m:
            now[m.group(1).strip().lower().replace(" ", "_")] = filled(m.group(2))
    health = now.get("health") or ""
    level = next((lvl for icon, lvl in (("🟢", "good"), ("🟡", "warning"), ("🔴", "critical"))
                  if icon in health), None)
    blockers = [{"blocker": r[0], "impact": r[1] if len(r) > 1 else "", "owner": r[2] if len(r) > 2 else "",
                 "status": r[3] if len(r) > 3 else ""}
                for r in table(section(md, "Blockers")) if filled(r[0])]
    sessions = re.findall(r"^### (\d{4}-\d{2}-\d{2}.*)$", section(md, "Session log"), flags=re.M)
    return {"phase": now.get("phase"), "health": health or None, "health_level": level,
            "last_session": now.get("last_session"), "working_on": now.get("working_on"),
            "next": bullets(section(md, "Next")), "recently_done": bullets(section(md, "Recently done")),
            "blockers": blockers, "stalls": bullets(section(md, "Stalls")),
            "open_questions": bullets(section(md, "Open questions")), "sessions": sessions[:5]}


def backlog():
    warnings = []
    try:
        active = json.loads(read("harness/FEATURES.json") or "{}")
    except json.JSONDecodeError as e:
        active = {}
        warnings.append(f"harness/FEATURES.json is not valid JSON ({e})")
    try:
        archive = json.loads(read("harness/FEATURES-DONE.json") or "{}").get("features", [])
    except json.JSONDecodeError as e:
        archive = []
        warnings.append(f"harness/FEATURES-DONE.json is not valid JSON ({e})")
    items = active.get("features", [])
    # template examples ("name": "<feature name>") left out
    real = [f for f in items if not re.fullmatch(r"\s*<[^>]*>\s*", str(f.get("name", "")))]
    everything = real + archive

    counts = {}
    for f in everything:
        counts[f.get("status", "?")] = counts.get(f.get("status", "?"), 0) + 1
    done = counts.get("done", 0)
    total = len(everything) - counts.get("cut", 0)          # cut work isn't work left or done
    by_prio = lambda f: PRIORITY.get(str(f.get("priority")), 9)   # stable: backlog order breaks ties, as in loop.sh
    pick = lambda s: sorted((f for f in real if f.get("status") == s), key=by_prio)
    open_types = {}
    for f in real:
        if f.get("status") not in ("done", "cut"):
            open_types[f.get("type", "feature")] = open_types.get(f.get("type", "feature"), 0) + 1

    by_id = {f.get("id"): f for f in everything}
    milestones = []
    for m in active.get("milestones", []):
        ids = [i for i in m.get("features", []) if i in by_id and by_id[i].get("status") != "cut"]
        milestones.append({"name": m.get("name"), "definition_of_done": filled(m.get("definition_of_done")),
                           "done": sum(by_id[i].get("status") == "done" for i in ids), "total": len(ids),
                           "items": [{"id": i, "name": by_id[i].get("name"), "status": by_id[i].get("status")}
                                     for i in ids]})

    # newest first; the archive is in closing order, so reversing it first breaks same-day ties
    closed = sorted((f for f in reversed(archive) if f.get("status") == "done"),
                    key=lambda f: str(f.get("closed", "")), reverse=True)
    return {"project": filled(active.get("project")), "updated": filled(active.get("updated")),
            "done": done, "total": total, "percent": round(done / total * 100) if total else 0,
            "counts": counts, "open_types": open_types,
            "in_progress": pick("in_progress"), "todo": pick("todo"), "blocked": pick("blocked"),
            "recently_closed": closed[:8], "shipped": closed, "milestones": milestones,
            "stale": [f["id"] for f in items if f.get("status") in ("done", "cut")],
            "template_items": len(items) - len(real), "warnings": warnings}


def evals():
    rows = table(section(read("harness/EVAL.md"), "Score history"))
    history = []
    for r in rows:
        if not filled(r[0]):
            continue
        # a plain number (95, 0.87, 92 %) can be charted; "M1 3/6" can't
        m = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*%?\s*", r[2] if len(r) > 2 else "")
        history.append({"date": r[0], "commit": r[1] if len(r) > 1 else "",
                        "score": r[2] if len(r) > 2 else "", "value": float(m.group(1)) if m else None,
                        "notes": r[3] if len(r) > 3 else ""})
    return {"history": history}


def plan():
    task = None
    for line in section(read("harness/PLAN.md"), "Task").splitlines():
        if line.strip() and not line.startswith(">"):
            task = filled(line)
            break
    return {"task": task}


def decisions():
    out = []
    for m in re.finditer(r"^## (\d{4}-\d{2}-\d{2}) — (.+)$(.*?)(?=^## |\Z)", read("harness/DECISIONS.md"),
                         flags=re.M | re.S):
        if not filled(m.group(2)):
            continue
        st = re.search(r"\*\*Status\*\*:\s*(.+)", m.group(3))
        out.append({"date": m.group(1), "title": m.group(2).strip(),
                    "status": filled(st.group(1)) if st else None})
    return out[:6]


def open_decisions():
    """harness/OPEN-DECISIONS.md, when the project keeps one: decisions only the user can make, each a
    `## <ID> — <title>` section, optionally summed up first in a table (ID | Topic | Blocks | Default)."""
    md = re.sub(r"<!--.*?-->", "", read("harness/OPEN-DECISIONS.md"), flags=re.S)
    intro = re.split(r"^## ", md, maxsplit=1, flags=re.M)[0]
    head = header(intro)
    title, blocks, default = column(head, "topic", "title", "decision", "question"), column(head, "block"), \
        column(head, "default")
    out = {}
    for r in table(intro):
        if DID.fullmatch(r[0]):
            out[r[0]] = {"id": r[0], "title": filled(cell(r, title)), "blocks": filled(cell(r, blocks)),
                         "default": filled(cell(r, default)), "body": ""}
    for m in re.finditer(r"^## (\S+)\s+[—–-]\s+(.+?)\s*$(.*?)(?=^## |\Z)", md, flags=re.M | re.S):
        if not DID.fullmatch(m.group(1)) or not filled(m.group(2)):
            continue
        d = out.setdefault(m.group(1), {"id": m.group(1), "title": None, "blocks": None, "default": None})
        d["title"] = d["title"] or m.group(2)
        d["body"] = re.sub(r"\n-{3,}\s*$", "", m.group(3)).strip()
    return list(out.values())


def waiting(st, b, decisions):
    """What waits on the user: STATE.md's open questions and the open decisions, each with what it holds up —
    the blocked items that cite it, the milestones whose definition of done names it — and their links."""
    open_items = b["in_progress"] + b["todo"] + b["blocked"]
    ods = [d["id"] for d in decisions]
    questions = []
    for q in st["open_questions"]:
        m = re.match(r"\*\*(Q\d+)\*\*\s*(?:[—–:-]\s*)?(.*)", q, flags=re.S)
        qid, text = (m.group(1), m.group(2)) if m else (None, q)
        questions.append({"id": qid, "text": text, "decisions": mentions(text, ods),
                          "blocks": [f["id"] for f in b["blocked"] if qid and qid in QREF.findall(f.get("blocked") or "")]})
    for d in decisions:
        d["questions"] = [q["id"] for q in questions if q["id"] and d["id"] in q["decisions"]]
        d["blocks_items"] = [f["id"] for f in open_items
                             if mentions(d["blocks"], [f["id"]]) or mentions(f.get("blocked"), [d["id"]])]
        d["milestones"] = [m["name"] for m in b["milestones"]
                           if not (m["total"] and m["done"] == m["total"])   # a complete one waits on nothing
                           and mentions(m["definition_of_done"], [d["id"]])]
    return {"questions": questions, "decisions": decisions}


def artifacts():
    """harness/ARTIFACTS.md: the pages published outside the repo, in the file's order (newest first)."""
    md = read("harness/ARTIFACTS.md")
    head = header(md)
    date, page, what, status = (column(head, "updated", "date", default=0), column(head, "page", default=1),
                                column(head, "what", default=2), column(head, "status", default=3))
    out = []
    for r in table(md):
        link = MDLINK.search(cell(r, page))
        url = link.group(2) if link else (re.findall(r"https?://[^\s<>|]+", cell(r, page)) or [""])[0]
        name = link.group(1) if link else cell(r, page).replace(url, "").strip(" <>—-") or url
        if not filled(name) or not filled(url):
            continue
        out.append({"date": filled(cell(r, date)), "title": name, "url": url, "what": filled(cell(r, what)),
                    "archived": "archived" in cell(r, status).lower()})
    return out


def git():
    def run(*args):
        r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
        return r.stdout if r.returncode == 0 else None
    if run("rev-parse", "--git-dir") is None:
        return {"repo": False}
    commits = []
    for line in (run("log", "-10", "--format=%h%x09%ad%x09%s", "--date=short") or "").splitlines():
        h, d, s = (line.split("\t", 2) + ["", ""])[:3]
        commits.append({"hash": h, "date": d, "subject": s})
    dirty = [l for l in (run("status", "--porcelain") or "").splitlines()
             if l[3:].strip('"') not in RUNTIME]
    # symbolic-ref: a repo with no commit yet still has a branch name
    branch = run("symbolic-ref", "--short", "-q", "HEAD") or run("rev-parse", "--short", "HEAD") or "?"
    return {"repo": True, "branch": branch.strip(),
            "commits": commits, "uncommitted": dirty}


def checks():
    ok = H / ".check.ok"
    when = (datetime.datetime.fromtimestamp(ok.stat().st_mtime).isoformat(timespec="minutes")
            if ok.exists() else None)
    log = read("harness/.loop.log").splitlines()
    return {"last_pass": when, "loop_log": log[-15:], "loop_stopped": (H / ".loop.stop").exists()}


def update_warnings():
    """<file>.harness-new left by init-harness.sh --update (you and the template changed the same lines)."""
    # where the template writes — never harness/template/ or .claude/worktrees/
    where = [(".", "*"), (".claude", "*"), ("harness", "*"), ("harness/guide", "**/*"), ("harness/scripts", "**/*"),
             (".claude/agents", "**/*"), (".claude/skills", "**/*"), (".agents", "**/*")]
    pending = sorted(str(p.relative_to(ROOT)) for d, pat in where for p in (ROOT / d).glob(pat + ".harness-new"))
    return [f"template update not merged: {', '.join(pending)} — merge what you need into the file "
            f"next to it, then delete the .harness-new"] if pending else []


def placeholder_lines():
    """Lines of the files the interview fills in that still hold a placeholder."""
    return sum(placeholder(l) for f in ("AGENTS.md", "harness/GOAL.md", "harness/FEATURES.json")
               for l in read(f).splitlines())


def collect():
    b = backlog()
    warnings = list(b.pop("warnings"))
    ph = placeholder_lines()
    if ph:
        warnings.append(f"{ph} lines still have <placeholders> — run /harness-init in Claude Code")
    if b["stale"]:
        warnings.append(f"still in FEATURES.json: {', '.join(b['stale'])} — archive with "
                        f"./harness/scripts/feature.sh <id> done")
    warnings += update_warnings()
    missing = [f for f in REQUIRED if not (ROOT / f).exists()]
    if missing:
        warnings.append("missing: " + ", ".join(missing))
    st = state()
    return {"project": b["project"] or ROOT.name,
            "generated": datetime.datetime.now().isoformat(timespec="seconds"),
            "goal": goal(), "state": st, "backlog": b, "eval": evals(), "plan": plan(),
            "decisions": decisions(), "waiting": waiting(st, b, open_decisions()), "artifacts": artifacts(),
            "git": git(), "checks": checks(), "warnings": warnings}


if __name__ == "__main__":
    json.dump(collect(), sys.stdout, indent=2, ensure_ascii=False)
    print()
