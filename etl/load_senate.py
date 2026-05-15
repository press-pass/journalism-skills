"""Load Senate LDA filings and contribution reports into duckdb.

Tables produced:
  senate_filing            - one row per filing (flattened)
  senate_activity          - one row per lobbying_activity (issue, description)
  senate_lobbyist          - one row per (filing, lobbyist) including covered_position
  senate_govt_entity       - one row per (filing, government entity lobbied)
  senate_contribution      - one row per (filing, contribution_item)
  senate_pac               - one row per (contribution filing, PAC)
"""
import duckdb
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = Path(os.environ.get("LDA_DATA_DIR", ROOT / ".context" / "data" / "data"))
DATA = DATA_ROOT / "senate"
DB = Path(os.environ.get("LDA_DB_PATH", ROOT / ".context" / "db" / "investigation.duckdb"))
con = duckdb.connect(str(DB))


def iter_filings():
    for yr_dir in sorted(DATA.iterdir()):
        if not yr_dir.is_dir() or yr_dir.name == "constants":
            continue
        fpath = yr_dir / "filings" / f"filings_{yr_dir.name}.json"
        if not fpath.exists():
            continue
        print(f"  reading {fpath.name}", file=sys.stderr)
        with open(fpath) as f:
            for filing in json.load(f):
                yield filing


def iter_contributions():
    for yr_dir in sorted(DATA.iterdir()):
        if not yr_dir.is_dir() or yr_dir.name == "constants":
            continue
        fpath = yr_dir / "contributions" / f"contributions_{yr_dir.name}.json"
        if not fpath.exists():
            continue
        print(f"  reading {fpath.name}", file=sys.stderr)
        with open(fpath) as f:
            for rep in json.load(f):
                yield rep


def flatten_filings():
    filings = []
    activities = []
    lobbyists = []
    entities = []
    foreign = []
    for f in iter_filings():
        uuid = f.get("filing_uuid")
        filings.append({
            "filing_uuid": uuid,
            "filing_type": f.get("filing_type"),
            "filing_type_display": f.get("filing_type_display"),
            "filing_year": f.get("filing_year"),
            "filing_period": f.get("filing_period"),
            "income": f.get("income"),
            "expenses": f.get("expenses"),
            "dt_posted": f.get("dt_posted"),
            "termination_date": f.get("termination_date"),
            "registrant_id": (f.get("registrant") or {}).get("id"),
            "registrant_name": (f.get("registrant") or {}).get("name"),
            "registrant_state": (f.get("registrant") or {}).get("state"),
            "registrant_country": (f.get("registrant") or {}).get("country"),
            "client_id": (f.get("client") or {}).get("id"),
            "client_name": (f.get("client") or {}).get("name"),
            "client_description": (f.get("client") or {}).get("general_description"),
            "client_state": (f.get("client") or {}).get("state"),
            "client_country": (f.get("client") or {}).get("country"),
            "client_self_select": (f.get("client") or {}).get("client_self_select"),
        })
        for i, act in enumerate(f.get("lobbying_activities") or []):
            activities.append({
                "filing_uuid": uuid,
                "act_idx": i,
                "general_issue_code": act.get("general_issue_code"),
                "general_issue_code_display": act.get("general_issue_code_display"),
                "description": act.get("description"),
                "foreign_entity_issues": act.get("foreign_entity_issues"),
            })
            for j, lobj in enumerate(act.get("lobbyists") or []):
                lo = lobj.get("lobbyist") or {}
                lobbyists.append({
                    "filing_uuid": uuid,
                    "act_idx": i,
                    "lobbyist_idx": j,
                    "lobbyist_id": lo.get("id"),
                    "first_name": lo.get("first_name"),
                    "last_name": lo.get("last_name"),
                    "middle_name": lo.get("middle_name"),
                    "covered_position": lobj.get("covered_position"),
                    "new": lobj.get("new"),
                })
            for j, ge in enumerate(act.get("government_entities") or []):
                entities.append({
                    "filing_uuid": uuid,
                    "act_idx": i,
                    "entity_idx": j,
                    "entity_id": ge.get("id"),
                    "entity_name": ge.get("name"),
                })
        for j, fe in enumerate(f.get("foreign_entities") or []):
            foreign.append({
                "filing_uuid": uuid,
                "foreign_idx": j,
                "entity_id": fe.get("id"),
                "entity_name": fe.get("name"),
                "entity_country": fe.get("country"),
            })
    return filings, activities, lobbyists, entities, foreign


def flatten_contributions():
    reports = []
    pacs = []
    items = []
    for r in iter_contributions():
        uuid = r.get("filing_uuid")
        reports.append({
            "filing_uuid": uuid,
            "filing_type": r.get("filing_type"),
            "filing_type_display": r.get("filing_type_display"),
            "filing_year": r.get("filing_year"),
            "filer_type": r.get("filer_type"),
            "filer_type_display": r.get("filer_type_display"),
            "no_contributions": r.get("no_contributions"),
            "dt_posted": r.get("dt_posted"),
            "registrant_id": (r.get("registrant") or {}).get("id"),
            "registrant_name": (r.get("registrant") or {}).get("name"),
            "lobbyist_id": (r.get("lobbyist") or {}).get("id"),
            "lobbyist_first_name": (r.get("lobbyist") or {}).get("first_name"),
            "lobbyist_last_name": (r.get("lobbyist") or {}).get("last_name"),
        })
        for j, pac in enumerate(r.get("pacs") or []):
            pacs.append({
                "filing_uuid": uuid,
                "pac_idx": j,
                "name": pac.get("name") if isinstance(pac, dict) else str(pac),
            })
        for j, it in enumerate(r.get("contribution_items") or []):
            items.append({
                "filing_uuid": uuid,
                "item_idx": j,
                "contribution_type": it.get("contribution_type"),
                "contributor_name": it.get("contributor_name"),
                "payee_name": it.get("payee_name"),
                "honoree_name": it.get("honoree_name"),
                "amount": it.get("amount"),
                "date": it.get("date"),
            })
    return reports, pacs, items


print("Flattening filings...", file=sys.stderr)
filings, activities, lobbyists, entities, foreign = flatten_filings()
print(f"  filings={len(filings)} acts={len(activities)} lobbyists={len(lobbyists)} entities={len(entities)} foreign={len(foreign)}", file=sys.stderr)

import pandas as pd

def materialize(name, rows):
    df = pd.DataFrame(rows)
    con.register("_tmp_df", df)
    con.execute(f"DROP TABLE IF EXISTS {name}")
    con.execute(f"CREATE TABLE {name} AS SELECT * FROM _tmp_df")
    con.unregister("_tmp_df")

materialize("senate_filing", filings)
materialize("senate_activity", activities)
materialize("senate_lobbyist", lobbyists)
materialize("senate_govt_entity", entities)
materialize("senate_foreign_entity", foreign)

print("Flattening contributions...", file=sys.stderr)
reports, pacs, items = flatten_contributions()
print(f"  reports={len(reports)} pacs={len(pacs)} items={len(items)}", file=sys.stderr)
materialize("senate_contrib_report", reports)
materialize("senate_contrib_pac", pacs)
materialize("senate_contrib_item", items)

for t in ("senate_filing", "senate_activity", "senate_lobbyist", "senate_govt_entity",
          "senate_foreign_entity", "senate_contrib_report", "senate_contrib_pac", "senate_contrib_item"):
    n = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
    print(f"  {t}: {n}", file=sys.stderr)
con.close()
