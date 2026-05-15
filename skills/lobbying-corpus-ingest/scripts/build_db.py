#!/usr/bin/env python3
"""
Ingest the GAIN corpus (Senate JSON, House XML, Congressional press JSONL) into
a single DuckDB database with normalized tables. Optimised for speed via
Arrow / DataFrame bulk inserts.

Usage:
  python build_db.py --data-root <path/to/data> --db <path/to/lobbying.duckdb>

Selective rebuilds via --skip {senate-filings,senate-contributions,house,press,constants}
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import re
import sys
import time
from pathlib import Path
from xml.etree import ElementTree as ET

import duckdb
import pyarrow as pa


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


SCHEMA = """
DROP TABLE IF EXISTS senate_filings;
CREATE TABLE senate_filings (
    filing_uuid VARCHAR,
    filing_type VARCHAR,
    filing_type_display VARCHAR,
    filing_year INTEGER,
    filing_period VARCHAR,
    filing_period_display VARCHAR,
    dt_posted TIMESTAMP,
    income DOUBLE,
    expenses DOUBLE,
    expenses_method VARCHAR,
    registrant_id BIGINT,
    registrant_name VARCHAR,
    registrant_country VARCHAR,
    registrant_state VARCHAR,
    registrant_contact_name VARCHAR,
    registrant_house_id BIGINT,
    client_id BIGINT,
    client_name VARCHAR,
    client_country VARCHAR,
    client_state VARCHAR,
    client_general_description VARCHAR,
    termination_date VARCHAR,
    filing_document_url VARCHAR,
    url VARCHAR
);
DROP TABLE IF EXISTS senate_activities;
CREATE TABLE senate_activities (
    filing_uuid VARCHAR,
    activity_idx INTEGER,
    general_issue_code VARCHAR,
    description VARCHAR,
    foreign_entity_issues VARCHAR
);
DROP TABLE IF EXISTS senate_lobbyists;
CREATE TABLE senate_lobbyists (
    filing_uuid VARCHAR,
    activity_idx INTEGER,
    lobbyist_id BIGINT,
    first_name VARCHAR,
    last_name VARCHAR,
    full_name VARCHAR,
    covered_position VARCHAR,
    new_lobbyist BOOLEAN
);
DROP TABLE IF EXISTS senate_gov_entities;
CREATE TABLE senate_gov_entities (
    filing_uuid VARCHAR,
    activity_idx INTEGER,
    entity_id BIGINT,
    entity_name VARCHAR
);
DROP TABLE IF EXISTS senate_contribution_items;
CREATE TABLE senate_contribution_items (
    filing_uuid VARCHAR,
    filing_year INTEGER,
    filing_period VARCHAR,
    registrant_id BIGINT,
    registrant_name VARCHAR,
    lobbyist_id BIGINT,
    lobbyist_first VARCHAR,
    lobbyist_last VARCHAR,
    contributor_name VARCHAR,
    contribution_type VARCHAR,
    amount DOUBLE,
    payee_name VARCHAR,
    honoree_name VARCHAR,
    date_string VARCHAR
);
DROP TABLE IF EXISTS house_filings;
CREATE TABLE house_filings (
    house_file VARCHAR,
    doc_type VARCHAR,
    report_type VARCHAR,
    filing_period VARCHAR,
    filing_year INTEGER,
    senate_id VARCHAR,
    senate_registrant_id BIGINT,
    house_id VARCHAR,
    organization_name VARCHAR,
    organization_name_clean VARCHAR,
    client_name VARCHAR,
    client_name_clean VARCHAR,
    client_state VARCHAR,
    client_country VARCHAR,
    income DOUBLE,
    expenses DOUBLE,
    expenses_method VARCHAR,
    no_lobbying VARCHAR,
    termination_date VARCHAR,
    printed_name VARCHAR,
    signed_date VARCHAR
);
DROP TABLE IF EXISTS house_activities;
CREATE TABLE house_activities (
    house_file VARCHAR,
    activity_idx INTEGER,
    issue_area_code VARCHAR,
    description VARCHAR,
    federal_agencies VARCHAR,
    foreign_entity_issues VARCHAR
);
DROP TABLE IF EXISTS house_lobbyists;
CREATE TABLE house_lobbyists (
    house_file VARCHAR,
    activity_idx INTEGER,
    first_name VARCHAR,
    last_name VARCHAR,
    full_name VARCHAR,
    suffix VARCHAR,
    covered_position VARCHAR,
    new_lobbyist VARCHAR
);
DROP TABLE IF EXISTS press_releases;
CREATE TABLE press_releases (
    url VARCHAR,
    title VARCHAR,
    date DATE,
    date_source VARCHAR,
    source VARCHAR,
    domain VARCHAR,
    scraper VARCHAR,
    bioguide_id VARCHAR,
    member_name VARCHAR,
    party VARCHAR,
    state VARCHAR,
    chamber VARCHAR,
    text VARCHAR
);
DROP TABLE IF EXISTS issue_codes;
CREATE TABLE issue_codes (code VARCHAR PRIMARY KEY, name VARCHAR);
DROP TABLE IF EXISTS filing_types;
CREATE TABLE filing_types (code VARCHAR PRIMARY KEY, name VARCHAR);
DROP TABLE IF EXISTS government_entities_lookup;
CREATE TABLE government_entities_lookup (id BIGINT PRIMARY KEY, name VARCHAR);
DROP TABLE IF EXISTS states_lookup;
CREATE TABLE states_lookup (code VARCHAR PRIMARY KEY, name VARCHAR);
DROP TABLE IF EXISTS countries_lookup;
CREATE TABLE countries_lookup (code VARCHAR PRIMARY KEY, name VARCHAR);
"""


def ensure_schema(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(SCHEMA)


def _floaty(v):
    if v in (None, ""):
        return None
    try:
        return float(str(v).replace(",", "").replace("$", ""))
    except (ValueError, TypeError):
        return None


def _clean(s):
    if not s:
        return None
    return re.sub(r"[^a-zA-Z0-9 ]+", " ", s).strip().upper() or None


def load_senate_constants(con, root: Path) -> None:
    consts = root / "senate" / "constants"
    if not consts.exists():
        log(f"missing senate/constants at {consts}")
        return

    def _load(name):
        p = consts / name
        return json.loads(p.read_text()) if p.exists() else []

    for tbl, file, cols in [
        ("issue_codes", "lobbying_activity_issues.json", ("value", "name")),
        ("filing_types", "filing_types.json", ("value", "name")),
        ("states_lookup", "states.json", ("value", "name")),
        ("countries_lookup", "countries.json", ("value", "name")),
    ]:
        rows = [(c.get(cols[0]), c.get(cols[1])) for c in _load(file)]
        if rows:
            con.executemany(f"INSERT OR REPLACE INTO {tbl} VALUES (?,?)", rows)
    rows = [(c.get("id"), c.get("name")) for c in _load("government_entities.json")]
    if rows:
        con.executemany("INSERT OR REPLACE INTO government_entities_lookup VALUES (?,?)", rows)
    log("Loaded senate constants")


def load_senate_filings(con, root: Path) -> None:
    base = root / "senate"
    grand = 0
    for year_dir in sorted(p for p in base.iterdir() if p.is_dir() and p.name != "constants"):
        try:
            year = int(year_dir.name)
        except ValueError:
            continue
        filings_dir = year_dir / "filings"
        if not filings_dir.exists():
            continue
        for fp in sorted(filings_dir.glob("*.json")):
            log(f"Loading {fp}")
            data = json.loads(fp.read_text())
            f_rows, a_rows, l_rows, ge_rows = [], [], [], []
            for f in data:
                fuid = f.get("filing_uuid")
                if not fuid:
                    continue
                registrant = f.get("registrant") or {}
                client = f.get("client") or {}
                f_rows.append({
                    "filing_uuid": fuid,
                    "filing_type": f.get("filing_type"),
                    "filing_type_display": f.get("filing_type_display"),
                    "filing_year": f.get("filing_year") or year,
                    "filing_period": f.get("filing_period"),
                    "filing_period_display": f.get("filing_period_display"),
                    "dt_posted": f.get("dt_posted"),
                    "income": _floaty(f.get("income")),
                    "expenses": _floaty(f.get("expenses")),
                    "expenses_method": f.get("expenses_method"),
                    "registrant_id": registrant.get("id"),
                    "registrant_name": registrant.get("name"),
                    "registrant_country": registrant.get("country_display") or registrant.get("country"),
                    "registrant_state": registrant.get("state_display") or registrant.get("state"),
                    "registrant_contact_name": registrant.get("contact_name"),
                    "registrant_house_id": registrant.get("house_registrant_id"),
                    "client_id": client.get("id"),
                    "client_name": client.get("name"),
                    "client_country": client.get("country_display") or client.get("country"),
                    "client_state": client.get("state_display") or client.get("state"),
                    "client_general_description": client.get("general_description"),
                    "termination_date": f.get("termination_date"),
                    "filing_document_url": f.get("filing_document_url"),
                    "url": f.get("url"),
                })
                for idx, act in enumerate(f.get("lobbying_activities") or []):
                    fei = act.get("foreign_entity_issues")
                    if isinstance(fei, list):
                        fei = json.dumps(fei)
                    a_rows.append({
                        "filing_uuid": fuid,
                        "activity_idx": idx,
                        "general_issue_code": act.get("general_issue_code"),
                        "description": (act.get("description") or "").strip() or None,
                        "foreign_entity_issues": fei,
                    })
                    for lob in act.get("lobbyists") or []:
                        lo = lob.get("lobbyist") or {}
                        full = f"{(lo.get('first_name') or '').strip()} {(lo.get('last_name') or '').strip()}".strip()
                        l_rows.append({
                            "filing_uuid": fuid,
                            "activity_idx": idx,
                            "lobbyist_id": lo.get("id"),
                            "first_name": lo.get("first_name"),
                            "last_name": lo.get("last_name"),
                            "full_name": full or None,
                            "covered_position": lob.get("covered_position"),
                            "new_lobbyist": bool(lob.get("new")),
                        })
                    for ge in act.get("government_entities") or []:
                        ge_rows.append({
                            "filing_uuid": fuid,
                            "activity_idx": idx,
                            "entity_id": ge.get("id"),
                            "entity_name": ge.get("name"),
                        })
            if f_rows:
                _insert_arrow(con, "senate_filings", f_rows)
            if a_rows:
                _insert_arrow(con, "senate_activities", a_rows)
            if l_rows:
                _insert_arrow(con, "senate_lobbyists", l_rows)
            if ge_rows:
                _insert_arrow(con, "senate_gov_entities", ge_rows)
            grand += len(f_rows)
            log(f"  +{len(f_rows):,} filings, +{len(a_rows):,} activities, +{len(l_rows):,} lobbyists, +{len(ge_rows):,} gov_entities (grand={grand:,})")


def _insert_arrow(con, table: str, dict_rows: list):
    """Bulk insert via Arrow. Much faster than executemany."""
    if not dict_rows:
        return
    # Build columns from union of keys (all rows share keys here, but be safe)
    cols = list(dict_rows[0].keys())
    data = {c: [r.get(c) for r in dict_rows] for c in cols}
    tbl = pa.table(data)
    con.register("__tmp_arrow", tbl)
    try:
        con.execute(f"INSERT INTO {table} SELECT * FROM __tmp_arrow")
    finally:
        con.unregister("__tmp_arrow")


def load_senate_contributions(con, root: Path) -> None:
    base = root / "senate"
    grand = 0
    for year_dir in sorted(p for p in base.iterdir() if p.is_dir() and p.name != "constants"):
        try:
            year = int(year_dir.name)
        except ValueError:
            continue
        contrib_dir = year_dir / "contributions"
        if not contrib_dir.exists():
            continue
        for fp in sorted(contrib_dir.glob("*.json")):
            log(f"Loading {fp}")
            data = json.loads(fp.read_text())
            rows = []
            for report in data:
                fuid = report.get("filing_uuid")
                if not fuid:
                    continue
                reg = report.get("registrant") or {}
                lob = report.get("lobbyist") or {}
                for ci in report.get("contribution_items") or []:
                    rows.append({
                        "filing_uuid": fuid,
                        "filing_year": report.get("filing_year") or year,
                        "filing_period": report.get("filing_period"),
                        "registrant_id": reg.get("id"),
                        "registrant_name": reg.get("name"),
                        "lobbyist_id": lob.get("id"),
                        "lobbyist_first": lob.get("first_name"),
                        "lobbyist_last": lob.get("last_name"),
                        "contributor_name": ci.get("contributor_name"),
                        "contribution_type": ci.get("contribution_type"),
                        "amount": _floaty(ci.get("amount")),
                        "payee_name": ci.get("payee_name"),
                        "honoree_name": ci.get("honoree_name"),
                        "date_string": ci.get("date"),
                    })
            if rows:
                _insert_arrow(con, "senate_contribution_items", rows)
            grand += len(rows)
            log(f"  +{len(rows):,} contribution items (grand={grand:,})")


def _txt(el):
    if el is None:
        return None
    s = (el.text or "").strip()
    return s or None


def _parse_year(s):
    if not s:
        return None
    try:
        return int(re.findall(r"\d{4}", s)[0])
    except IndexError:
        return None


def _normalize_period(report_type: str, dir_period: str) -> str:
    if report_type:
        rt = report_type.upper()
        if rt in {"Q1", "Q2", "Q3", "Q4"}:
            return rt
        m = re.match(r"^([1-4])([TA])$", rt)
        if m:
            return f"Q{m.group(1)}"
        if rt in {"YE", "MM", "RR"}:
            return rt
    return dir_period


def _senate_registrant_from_id(sid):
    if not sid:
        return None
    m = re.match(r"^(\d+)", sid)
    return int(m.group(1)) if m else None


def parse_house_xml(args):
    xml_path, dir_period, dir_year = args
    try:
        root = ET.parse(xml_path).getroot()
    except (ET.ParseError, OSError):
        return None
    tag_upper = root.tag.upper()
    doc_type = "LD1" if "DISCLOSURE1" in tag_upper else "LD2"
    house_file = os.path.basename(xml_path)

    report_type = _txt(root.find("reportType")) or _txt(root.find("registrationPeriod"))
    filing_period = _normalize_period(report_type, dir_period)
    filing_year = _parse_year(_txt(root.find("reportYear"))) or dir_year
    org = _txt(root.find("organizationName")) or _txt(root.find("registrantName"))
    client = _txt(root.find("clientName"))
    senate_id = _txt(root.find("senateID"))
    house_id = _txt(root.find("houseID"))

    filing_row = {
        "house_file": house_file,
        "doc_type": doc_type,
        "report_type": report_type,
        "filing_period": filing_period,
        "filing_year": filing_year,
        "senate_id": senate_id,
        "senate_registrant_id": _senate_registrant_from_id(senate_id),
        "house_id": house_id,
        "organization_name": org,
        "organization_name_clean": _clean(org),
        "client_name": client,
        "client_name_clean": _clean(client),
        "client_state": _txt(root.find("clientState")) or _txt(root.find("state")),
        "client_country": _txt(root.find("clientCountry")) or _txt(root.find("country")),
        "income": _floaty(_txt(root.find("income"))),
        "expenses": _floaty(_txt(root.find("expenses"))),
        "expenses_method": _txt(root.find("expensesMethod")),
        "no_lobbying": _txt(root.find("noLobbying")),
        "termination_date": _txt(root.find("terminationDate")),
        "printed_name": _txt(root.find("printedName")),
        "signed_date": _txt(root.find("signedDate")),
    }

    activity_rows = []
    lobbyist_rows = []
    for idx, ai in enumerate(root.findall("./alis/ali_info")):
        code = _txt(ai.find("issueAreaCode"))
        desc = _txt(ai.find("./specific_issues/description"))
        agencies = _txt(ai.find("federal_agencies"))
        fei = _txt(ai.find("foreign_entity_issues"))
        lobs_named = [lob for lob in ai.findall("./lobbyists/lobbyist")
                      if _txt(lob.find("lobbyistFirstName")) or _txt(lob.find("lobbyistLastName"))]
        if not any([code, desc, agencies, fei]) and not lobs_named:
            continue
        activity_rows.append({
            "house_file": house_file,
            "activity_idx": idx,
            "issue_area_code": code,
            "description": desc,
            "federal_agencies": agencies,
            "foreign_entity_issues": fei,
        })
        for lob in lobs_named:
            fn = _txt(lob.find("lobbyistFirstName"))
            ln = _txt(lob.find("lobbyistLastName"))
            lobbyist_rows.append({
                "house_file": house_file,
                "activity_idx": idx,
                "first_name": fn,
                "last_name": ln,
                "full_name": f"{fn or ''} {ln or ''}".strip(),
                "suffix": _txt(lob.find("lobbyistSuffix")),
                "covered_position": _txt(lob.find("coveredPosition")),
                "new_lobbyist": _txt(lob.find("lobbyistNew")),
            })
    return filing_row, activity_rows, lobbyist_rows


def load_house_xml(con, root: Path, workers: int = 8) -> None:
    house_root = root / "house"
    if not house_root.exists():
        log(f"missing {house_root}")
        return
    sub_dirs = sorted([d for d in house_root.iterdir() if d.is_dir()])
    grand_total = 0
    for sd in sub_dirs:
        m_year = re.match(r"(\d{4})_", sd.name)
        dir_year = int(m_year.group(1)) if m_year else None
        if "Registrations" in sd.name:
            dir_period = "RR"
        elif "1stQuarter" in sd.name:
            dir_period = "Q1"
        elif "2ndQuarter" in sd.name:
            dir_period = "Q2"
        elif "3rdQuarter" in sd.name:
            dir_period = "Q3"
        elif "4thQuarter" in sd.name:
            dir_period = "Q4"
        else:
            dir_period = None

        xml_paths = [str(p) for p in sd.glob("*.xml")]
        log(f"House {sd.name}: {len(xml_paths):,} files (period={dir_period}, year={dir_year}) workers={workers}")
        if not xml_paths:
            continue
        args_iter = [(p, dir_period, dir_year) for p in xml_paths]

        filings_batch = []
        activities_batch = []
        lobbyists_batch = []
        processed = 0
        BATCH = 8000

        def _flush():
            nonlocal filings_batch, activities_batch, lobbyists_batch
            if filings_batch:
                _insert_arrow(con, "house_filings", filings_batch)
            if activities_batch:
                _insert_arrow(con, "house_activities", activities_batch)
            if lobbyists_batch:
                _insert_arrow(con, "house_lobbyists", lobbyists_batch)
            filings_batch, activities_batch, lobbyists_batch = [], [], []

        with mp.Pool(workers) as pool:
            for res in pool.imap_unordered(parse_house_xml, args_iter, chunksize=200):
                if res is None:
                    continue
                f_row, a_rows, l_rows = res
                filings_batch.append(f_row)
                activities_batch.extend(a_rows)
                lobbyists_batch.extend(l_rows)
                processed += 1
                if processed % BATCH == 0:
                    _flush()
                    log(f"  {sd.name}: {processed:,}/{len(xml_paths):,}")
            _flush()
        grand_total += processed
        log(f"  done {sd.name}; cumulative={grand_total:,}")


def load_press(con, root: Path) -> None:
    base = root / "congress_press"
    if not base.exists():
        log(f"missing {base}")
        return
    files = sorted(list(base.glob("*.jsonl")) + list(base.glob("*/*.jsonl")))
    grand = 0
    for fp in files:
        rows = []
        with open(fp) as f:
            for line in f:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                m = r.get("member") or {}
                rows.append({
                    "url": r.get("url"),
                    "title": r.get("title"),
                    "date": r.get("date"),
                    "date_source": r.get("date_source"),
                    "source": r.get("source"),
                    "domain": r.get("domain"),
                    "scraper": r.get("scraper"),
                    "bioguide_id": m.get("bioguide_id"),
                    "member_name": m.get("name"),
                    "party": m.get("party"),
                    "state": m.get("state"),
                    "chamber": m.get("chamber"),
                    "text": r.get("text"),
                })
        if rows:
            _insert_arrow(con, "press_releases", rows)
        grand += len(rows)
        log(f"{fp.name}: +{len(rows):,} (grand={grand:,})")


def dedupe_filings(con) -> None:
    log("Dedupe senate_filings on filing_uuid (keep latest dt_posted)")
    con.execute("""
        CREATE OR REPLACE TABLE senate_filings AS
        SELECT * FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY filing_uuid ORDER BY dt_posted DESC NULLS LAST) AS _rn
            FROM senate_filings
        ) WHERE _rn = 1;
        ALTER TABLE senate_filings DROP COLUMN _rn;
    """)
    n = con.execute("SELECT COUNT(*) FROM senate_filings").fetchone()[0]
    log(f"  senate_filings rows after dedup: {n:,}")
    log("Dedupe house_filings on house_file")
    con.execute("""
        CREATE OR REPLACE TABLE house_filings AS
        SELECT * FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY house_file ORDER BY filing_year DESC NULLS LAST) AS _rn
            FROM house_filings
        ) WHERE _rn = 1;
        ALTER TABLE house_filings DROP COLUMN _rn;
    """)
    n = con.execute("SELECT COUNT(*) FROM house_filings").fetchone()[0]
    log(f"  house_filings rows after dedup: {n:,}")


def build_indexes(con) -> None:
    log("Creating indexes / analyzing")
    con.execute("""
        CREATE INDEX IF NOT EXISTS idx_filings_uuid ON senate_filings(filing_uuid);
        CREATE INDEX IF NOT EXISTS idx_filings_year ON senate_filings(filing_year);
        CREATE INDEX IF NOT EXISTS idx_filings_client ON senate_filings(client_id);
        CREATE INDEX IF NOT EXISTS idx_filings_registrant ON senate_filings(registrant_id);
        CREATE INDEX IF NOT EXISTS idx_act_uuid ON senate_activities(filing_uuid);
        CREATE INDEX IF NOT EXISTS idx_act_issue ON senate_activities(general_issue_code);
        CREATE INDEX IF NOT EXISTS idx_lob_uuid ON senate_lobbyists(filing_uuid);
        CREATE INDEX IF NOT EXISTS idx_lob_full ON senate_lobbyists(full_name);
        CREATE INDEX IF NOT EXISTS idx_house_file ON house_filings(house_file);
        CREATE INDEX IF NOT EXISTS idx_house_year ON house_filings(filing_year);
        CREATE INDEX IF NOT EXISTS idx_house_senate ON house_filings(senate_id);
        CREATE INDEX IF NOT EXISTS idx_house_sreg ON house_filings(senate_registrant_id);
        CREATE INDEX IF NOT EXISTS idx_house_client ON house_filings(client_name_clean);
        CREATE INDEX IF NOT EXISTS idx_house_org ON house_filings(organization_name_clean);
        CREATE INDEX IF NOT EXISTS idx_house_act ON house_activities(house_file);
        CREATE INDEX IF NOT EXISTS idx_house_act_code ON house_activities(issue_area_code);
        CREATE INDEX IF NOT EXISTS idx_house_lob ON house_lobbyists(house_file);
        CREATE INDEX IF NOT EXISTS idx_press_date ON press_releases(date);
        CREATE INDEX IF NOT EXISTS idx_press_bio ON press_releases(bioguide_id);
        ANALYZE;
    """)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--db", required=True)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) // 2))
    ap.add_argument("--skip", nargs="*", default=[],
                    help="constants|senate-filings|senate-contributions|house|press")
    args = ap.parse_args()
    root = Path(args.data_root)
    if not root.exists():
        sys.exit(f"data root not found: {root}")
    con = duckdb.connect(args.db)
    ensure_schema(con)
    if "constants" not in args.skip:
        load_senate_constants(con, root)
    if "senate-filings" not in args.skip:
        load_senate_filings(con, root)
    if "senate-contributions" not in args.skip:
        load_senate_contributions(con, root)
    if "house" not in args.skip:
        load_house_xml(con, root, workers=args.workers)
    if "press" not in args.skip:
        load_press(con, root)
    dedupe_filings(con)
    build_indexes(con)
    log("Done.")


if __name__ == "__main__":
    main()
