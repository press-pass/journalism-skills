#!/usr/bin/env python3
"""Manage an investigation state file — leads, entities, cold threads.

Persistent, on-disk checklist that survives agent restarts and context
compaction. Designed to be the single source of truth for "what have we
checked, what's open, who are the people of interest" across many sessions.

The state lives at `research/investigation_state.json` (gitignored leads
table can be committed for audit). All operations are append-only by default
to preserve trace.

Usage:
  python3 lead.py list                                # show open + recent
  python3 lead.py add  --title "..." [--evidence ...] [--tags rd,foreign]
  python3 lead.py close <id> [--resolution "..."]
  python3 lead.py cold <id>  [--reason "..."]
  python3 lead.py reopen <id>
  python3 lead.py entity-add --kind person --name "Joe Smith" \
                            [--bioguide ID] [--note "..."]
  python3 lead.py entity-list
  python3 lead.py log <id> --note "..."              # append timestamped note
  python3 lead.py export  > investigation_state.md   # render markdown briefing
"""
import argparse
import datetime as dt
import json
import os
import sys
import textwrap
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STATE = ROOT / "research" / "investigation_state.json"
STATE.parent.mkdir(parents=True, exist_ok=True)


def load():
    if not STATE.exists():
        return {"leads": [], "entities": [], "schema_version": 1}
    return json.load(open(STATE))


def save(state):
    STATE.write_text(json.dumps(state, indent=2, default=str) + "\n")


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def cmd_list(args):
    s = load()
    leads = sorted(s["leads"], key=lambda L: (L["status"] != "open", L["created"]))
    if not leads:
        print("(no leads)")
        return
    for L in leads:
        if args.all or L["status"] != "closed":
            tags = ",".join(L.get("tags") or [])
            print(f"  [{L['status']:<6}] {L['id'][:8]}  {L['title']}  ({tags})")


def cmd_add(args):
    s = load()
    L = {
        "id": uuid.uuid4().hex,
        "title": args.title,
        "status": "open",
        "tags": args.tags.split(",") if args.tags else [],
        "evidence": [args.evidence] if args.evidence else [],
        "log": [],
        "created": now(),
    }
    s["leads"].append(L)
    save(s)
    print(L["id"])


def _find(s, prefix):
    matches = [L for L in s["leads"] if L["id"].startswith(prefix)]
    if not matches:
        sys.exit(f"no lead matches {prefix}")
    if len(matches) > 1:
        sys.exit(f"prefix {prefix} ambiguous ({len(matches)} matches)")
    return matches[0]


def cmd_close(args):
    s = load()
    L = _find(s, args.id)
    L["status"] = "closed"
    L["closed"] = now()
    if args.resolution:
        L.setdefault("log", []).append({"t": now(), "note": f"RESOLVED: {args.resolution}"})
    save(s)
    print("closed", L["id"][:8])


def cmd_cold(args):
    s = load()
    L = _find(s, args.id)
    L["status"] = "cold"
    L.setdefault("log", []).append({"t": now(), "note": f"COLD: {args.reason or ''}"})
    save(s)
    print("cold", L["id"][:8])


def cmd_reopen(args):
    s = load()
    L = _find(s, args.id)
    L["status"] = "open"
    L.setdefault("log", []).append({"t": now(), "note": "REOPENED"})
    save(s)
    print("reopened", L["id"][:8])


def cmd_entity_add(args):
    s = load()
    E = {
        "id": uuid.uuid4().hex,
        "kind": args.kind,
        "name": args.name,
        "bioguide": args.bioguide,
        "note": args.note,
        "added": now(),
    }
    s["entities"].append(E)
    save(s)
    print(E["id"])


def cmd_entity_list(args):
    s = load()
    for E in sorted(s["entities"], key=lambda e: (e["kind"], e["name"].lower())):
        line = f"  [{E['kind']:<8}] {E['name']}"
        if E.get("bioguide"):
            line += f" ({E['bioguide']})"
        if E.get("note"):
            line += f"  — {E['note']}"
        print(line)


def cmd_log(args):
    s = load()
    L = _find(s, args.id)
    L.setdefault("log", []).append({"t": now(), "note": args.note})
    save(s)
    print("logged", L["id"][:8])


def cmd_export(args):
    s = load()
    out = []
    out.append("# Investigation state\n")
    out.append(f"_Snapshot at {now()}_\n")
    out.append("\n## Open leads\n")
    open_ = [L for L in s["leads"] if L["status"] == "open"]
    for L in sorted(open_, key=lambda L: L["created"]):
        tags = " ".join(f"`{t}`" for t in (L.get("tags") or []))
        out.append(f"### {L['title']} {tags}")
        out.append(f"- id: `{L['id']}`")
        out.append(f"- opened: {L['created']}")
        for e in L.get("evidence") or []:
            out.append(f"- evidence: {e}")
        for entry in (L.get("log") or [])[-5:]:
            out.append(f"  - {entry['t']}: {entry['note']}")
        out.append("")
    out.append("\n## Cold threads\n")
    for L in [L for L in s["leads"] if L["status"] == "cold"]:
        out.append(f"- {L['title']}  (`{L['id'][:8]}`)")
    out.append("\n## Significant entities\n")
    for E in sorted(s["entities"], key=lambda e: (e["kind"], e["name"].lower())):
        line = f"- **{E['name']}** ({E['kind']})"
        if E.get("bioguide"):
            line += f"  · bioguide={E['bioguide']}"
        if E.get("note"):
            line += f"  · {E['note']}"
        out.append(line)
    print("\n".join(out))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list"); p.add_argument("--all", action="store_true"); p.set_defaults(fn=cmd_list)
    p = sub.add_parser("add"); p.add_argument("--title", required=True)
    p.add_argument("--evidence"); p.add_argument("--tags"); p.set_defaults(fn=cmd_add)
    p = sub.add_parser("close"); p.add_argument("id"); p.add_argument("--resolution"); p.set_defaults(fn=cmd_close)
    p = sub.add_parser("cold"); p.add_argument("id"); p.add_argument("--reason"); p.set_defaults(fn=cmd_cold)
    p = sub.add_parser("reopen"); p.add_argument("id"); p.set_defaults(fn=cmd_reopen)
    p = sub.add_parser("entity-add"); p.add_argument("--kind", required=True)
    p.add_argument("--name", required=True); p.add_argument("--bioguide"); p.add_argument("--note"); p.set_defaults(fn=cmd_entity_add)
    p = sub.add_parser("entity-list"); p.set_defaults(fn=cmd_entity_list)
    p = sub.add_parser("log"); p.add_argument("id"); p.add_argument("--note", required=True); p.set_defaults(fn=cmd_log)
    p = sub.add_parser("export"); p.set_defaults(fn=cmd_export)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
