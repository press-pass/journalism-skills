"""Senate LDA ETL: JSON arrays → parquet (filings, activities, lobbyists, contributions, contribution_items).

Run inside docker. Source = data/senate/. Writes:
  parquet/senate_filings.parquet      one row per filing
  parquet/senate_activities.parquet   one row per lobbying_activity within a filing
  parquet/senate_lobbyists.parquet    one row per lobbyist-activity pairing
  parquet/senate_contrib_filings.parquet
  parquet/senate_contrib_items.parquet
"""
from __future__ import annotations
import argparse, json, sys, glob
from pathlib import Path
import pyarrow as pa, pyarrow.parquet as pq
from tqdm import tqdm


def write_pq(path: str, rows: list, schema: pa.Schema):
    if not rows:
        # write empty
        pq.write_table(pa.Table.from_pylist([], schema=schema), path, compression="zstd")
        return
    pq.write_table(pa.Table.from_pylist(rows, schema=schema), path, compression="zstd")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--senate_root", required=True)
    ap.add_argument("--out_dir", required=True)
    args = ap.parse_args()
    out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)

    filing_rows = []
    activity_rows = []
    lobbyist_rows = []
    contrib_rows = []
    contrib_item_rows = []

    filings_files = sorted(glob.glob(f"{args.senate_root}/*/filings/filings_*.json"))
    for fp in tqdm(filings_files, desc="senate filings"):
        with open(fp) as f:
            d = json.load(f)
        for filing in d:
            filing_uuid = filing.get("filing_uuid")
            reg = filing.get("registrant") or {}
            cli = filing.get("client") or {}
            # foreign entities flagged separately
            foreign = filing.get("foreign_entities") or []
            filing_rows.append({
                "filing_uuid": filing_uuid,
                "filing_type": filing.get("filing_type"),
                "filing_type_display": filing.get("filing_type_display"),
                "filing_year": int(filing.get("filing_year") or 0) or None,
                "filing_period": filing.get("filing_period"),
                "filing_period_display": filing.get("filing_period_display"),
                "income": _num(filing.get("income")),
                "expenses": _num(filing.get("expenses")),
                "dt_posted": filing.get("dt_posted"),
                "termination_date": filing.get("termination_date"),
                "registrant_id": reg.get("id"),
                "registrant_name": (reg.get("name") or "").strip(),
                "registrant_house_id": reg.get("house_registrant_id"),
                "registrant_country": reg.get("country"),
                "registrant_state": reg.get("state"),
                "client_id": cli.get("id"),
                "client_name": (cli.get("name") or "").strip(),
                "client_general_description": cli.get("general_description"),
                "client_state": cli.get("state"),
                "client_country": cli.get("country"),
                "n_foreign_entities": len(foreign),
                "foreign_entity_names": "|".join(sorted(set([(fe.get("name") or "").strip() for fe in foreign if fe.get("name")]))),
                "filing_document_url": filing.get("filing_document_url"),
            })
            for act in filing.get("lobbying_activities") or []:
                code = act.get("general_issue_code")
                desc = act.get("description") or ""
                gov = act.get("government_entities") or []
                activity_rows.append({
                    "filing_uuid": filing_uuid,
                    "issue_code": code,
                    "issue_code_display": act.get("general_issue_code_display"),
                    "description": desc,
                    "n_government_entities": len(gov),
                    "government_entity_names": "|".join([(ge.get("name") or "").strip() for ge in gov]),
                    "filing_year": filing.get("filing_year"),
                    "filing_period": filing.get("filing_period"),
                    "income": _num(filing.get("income")),
                    "expenses": _num(filing.get("expenses")),
                    "client_name": (cli.get("name") or "").strip(),
                    "registrant_name": (reg.get("name") or "").strip(),
                })
                for la in act.get("lobbyists") or []:
                    lo = la.get("lobbyist") or {}
                    lobbyist_rows.append({
                        "filing_uuid": filing_uuid,
                        "issue_code": code,
                        "lobbyist_id": lo.get("id"),
                        "first_name": (lo.get("first_name") or "").strip(),
                        "last_name": (lo.get("last_name") or "").strip(),
                        "covered_position": (la.get("covered_position") or "").strip(),
                        "new_lobbyist": bool(la.get("new")),
                        "filing_year": filing.get("filing_year"),
                        "filing_period": filing.get("filing_period"),
                        "registrant_name": (reg.get("name") or "").strip(),
                        "client_name": (cli.get("name") or "").strip(),
                    })

    # Contributions
    contrib_files = sorted(glob.glob(f"{args.senate_root}/*/contributions/contributions_*.json"))
    for fp in tqdm(contrib_files, desc="senate contributions"):
        with open(fp) as f:
            d = json.load(f)
        for cr in d:
            uuid = cr.get("filing_uuid")
            reg = cr.get("registrant") or {}
            lo = cr.get("lobbyist") or {}
            contrib_rows.append({
                "filing_uuid": uuid,
                "filing_type": cr.get("filing_type"),
                "filing_year": cr.get("filing_year"),
                "filing_period": cr.get("filing_period"),
                "filer_type": cr.get("filer_type"),
                "no_contributions": cr.get("no_contributions"),
                "registrant_id": reg.get("id"),
                "registrant_name": (reg.get("name") or "").strip(),
                "lobbyist_id": lo.get("id") if isinstance(lo, dict) else None,
                "lobbyist_first": (lo.get("first_name") if isinstance(lo, dict) else None) or "",
                "lobbyist_last": (lo.get("last_name") if isinstance(lo, dict) else None) or "",
                "n_pacs": len(cr.get("pacs") or []),
                "n_items": len(cr.get("contribution_items") or []),
            })
            for ci in cr.get("contribution_items") or []:
                contrib_item_rows.append({
                    "filing_uuid": uuid,
                    "filing_year": cr.get("filing_year"),
                    "filing_period": cr.get("filing_period"),
                    "registrant_name": (reg.get("name") or "").strip(),
                    "lobbyist_first": (lo.get("first_name") if isinstance(lo, dict) else None) or "",
                    "lobbyist_last": (lo.get("last_name") if isinstance(lo, dict) else None) or "",
                    "contribution_type": ci.get("contribution_type") or ci.get("type"),
                    "amount": _num(ci.get("amount")),
                    "date": ci.get("date"),
                    "payee": (ci.get("payee_name") or ci.get("payee") or "").strip(),
                    "honoree": (ci.get("honoree_name") or ci.get("honoree") or "").strip(),
                    "contributor": (ci.get("contributor_name") or "").strip(),
                })

    # schemas
    fs = pa.schema([
        ("filing_uuid", pa.string()), ("filing_type", pa.string()), ("filing_type_display", pa.string()),
        ("filing_year", pa.int64()), ("filing_period", pa.string()), ("filing_period_display", pa.string()),
        ("income", pa.float64()), ("expenses", pa.float64()), ("dt_posted", pa.string()),
        ("termination_date", pa.string()), ("registrant_id", pa.int64()), ("registrant_name", pa.string()),
        ("registrant_house_id", pa.int64()), ("registrant_country", pa.string()), ("registrant_state", pa.string()),
        ("client_id", pa.int64()), ("client_name", pa.string()), ("client_general_description", pa.string()),
        ("client_state", pa.string()), ("client_country", pa.string()),
        ("n_foreign_entities", pa.int64()), ("foreign_entity_names", pa.string()),
        ("filing_document_url", pa.string()),
    ])
    acts = pa.schema([
        ("filing_uuid", pa.string()), ("issue_code", pa.string()), ("issue_code_display", pa.string()),
        ("description", pa.string()), ("n_government_entities", pa.int64()),
        ("government_entity_names", pa.string()), ("filing_year", pa.int64()),
        ("filing_period", pa.string()), ("income", pa.float64()), ("expenses", pa.float64()),
        ("client_name", pa.string()), ("registrant_name", pa.string()),
    ])
    los = pa.schema([
        ("filing_uuid", pa.string()), ("issue_code", pa.string()),
        ("lobbyist_id", pa.int64()), ("first_name", pa.string()), ("last_name", pa.string()),
        ("covered_position", pa.string()), ("new_lobbyist", pa.bool_()),
        ("filing_year", pa.int64()), ("filing_period", pa.string()),
        ("registrant_name", pa.string()), ("client_name", pa.string()),
    ])
    contrs = pa.schema([
        ("filing_uuid", pa.string()), ("filing_type", pa.string()), ("filing_year", pa.int64()),
        ("filing_period", pa.string()), ("filer_type", pa.string()), ("no_contributions", pa.bool_()),
        ("registrant_id", pa.int64()), ("registrant_name", pa.string()),
        ("lobbyist_id", pa.int64()), ("lobbyist_first", pa.string()), ("lobbyist_last", pa.string()),
        ("n_pacs", pa.int64()), ("n_items", pa.int64()),
    ])
    citems = pa.schema([
        ("filing_uuid", pa.string()), ("filing_year", pa.int64()), ("filing_period", pa.string()),
        ("registrant_name", pa.string()), ("lobbyist_first", pa.string()), ("lobbyist_last", pa.string()),
        ("contribution_type", pa.string()), ("amount", pa.float64()), ("date", pa.string()),
        ("payee", pa.string()), ("honoree", pa.string()), ("contributor", pa.string()),
    ])

    write_pq(str(out / "senate_filings.parquet"), filing_rows, fs)
    write_pq(str(out / "senate_activities.parquet"), activity_rows, acts)
    write_pq(str(out / "senate_lobbyists.parquet"), lobbyist_rows, los)
    write_pq(str(out / "senate_contrib_filings.parquet"), contrib_rows, contrs)
    write_pq(str(out / "senate_contrib_items.parquet"), contrib_item_rows, citems)

    print(f"FILINGS={len(filing_rows)} ACTIVITIES={len(activity_rows)} LOBBYISTS={len(lobbyist_rows)} CONTRIB_FILINGS={len(contrib_rows)} CONTRIB_ITEMS={len(contrib_item_rows)}", file=sys.stderr)


def _num(v):
    try:
        if v in (None, "", "null"):
            return None
        return float(v)
    except (ValueError, TypeError):
        return None


if __name__ == "__main__":
    main()
