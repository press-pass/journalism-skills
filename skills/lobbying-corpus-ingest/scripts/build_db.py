#!/usr/bin/env python3
"""
Ingest the GAIN corpus (Senate JSON, House XML, Congressional press JSONL) into
a single DuckDB database with normalized tables and a source-of-record column
on every row so claims can be audited.

Usage:
  python build_db.py --data-root <path/to/data> --db <path/to/lobbying.duckdb>

Selective rebuilds via:
  --skip {senate-filings,senate-contributions,house,press,constants}

Tables produced:
  senate_filings, senate_activities, senate_lobbyists, senate_gov_entities,
  senate_contribution_items, house_filings, house_activities, house_lobbyists,
  press_releases, plus several lookup tables.
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


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


SCHEMA = """
DROP TABLE IF EXISTS senate_filings;
CREATE TABLE senate_filings (
    filing_uuid VARCHAR PRIMARY KEY,
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
    house_file VARCHAR PRIMARY KEY,
    doc_type VARCHAR,                   -- LD1 or LD2
    report_type VARCHAR,                -- Q1..Q4, 1T, MM, YE etc from XML
    filing_period VARCHAR,              -- normalized Q1..Q4 or RR
    filing_year INTEGER,
    senate_id VARCHAR,
    senate_registrant_id BIGINT,        -- numeric prefix before '-' in senate_id
    house_id VARCHAR,
    organization_name VARCHAR,
    organization_name_clean VARCHAR,    -- uppercase, stripped
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


def _str(x):
    if isinstance(x, dict):
        return x.get("name") or x.get("display") or None
    return x


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
    return re.sub(r"[\s,.&]+", " ", s).strip().upper() or None


def load_senate_constants(con, root: Path) -> None:
    consts = root / "senate" / "constants"
    if not consts.exists():
        log(f"missing senate/constants at {consts}")
        return

    def _load(name):
        p = consts / name
        return json.loads(p.read_text()) if p.exists() else []

    rows = [(c.get("value"), c.get("name")) for c in _load("lobbying_activity_issues.json")]
    if rows:
        con.executemany("INSERT OR REPLACE INTO issue_codes VALUES (?,?)", rows)
    rows = [(c.get("value"), c.get("name")) for c in _load("filing_types.json")]
    if rows:
        con.executemany("INSERT OR REPLACE INTO filing_types VALUES (?,?)", rows)
    rows = [(c.get("id"), c.get("name")) for c in _load("government_entities.json")]
    if rows:
        con.executemany("INSERT OR REPLACE INTO government_entities_lookup VALUES (?,?)", rows)
    rows = [(c.get("value"), c.get("name")) for c in _load("states.json")]
    if rows:
        con.executemany("INSERT OR REPLACE INTO states_lookup VALUES (?,?)", rows)
    rows = [(c.get("value"), c.get("name")) for c in _load("countries.json")]
    if rows:
        con.executemany("INSERT OR REPLACE INTO countries_lookup VALUES (?,?)", rows)
    log("Loaded senate constants")


def load_senate_filings(con, root: Path) -> None:
    base = root / "senate"
    total = 0
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
                f_rows.append((
                    fuid,
                    f.get("filing_type"),
                    f.get("filing_type_display"),
                    f.get("filing_year") or year,
                    f.get("filing_period"),
                    f.get("filing_period_display"),
                    f.get("dt_posted"),
                    _floaty(f.get("income")),
                    _floaty(f.get("expenses")),
                    f.get("expenses_method"),
                    registrant.get("id"),
                    registrant.get("name"),
                    registrant.get("country_display") or registrant.get("country"),
                    registrant.get("state_display") or registrant.get("state"),
                    registrant.get("contact_name"),
                    registrant.get("house_registrant_id"),
                    client.get("id"),
                    client.get("name"),
                    client.get("country_display") or client.get("country"),
                    client.get("state_display") or client.get("state"),
                    client.get("general_description"),
                    f.get("termination_date"),
                    f.get("filing_document_url"),
                    f.get("url"),
                ))
                for idx, act in enumerate(f.get("lobbying_activities") or []):
                    fei = act.get("foreign_entity_issues")
                    if isinstance(fei, list):
                        fei = json.dumps(fei)
                    a_rows.append((
                        fuid, idx,
                        act.get("general_issue_code"),
                        (act.get("description") or "").strip() or None,
                        fei,
                    ))
                    for lob in act.get("lobbyists") or []:
                        lo = lob.get("lobbyist") or {}
                        full = f"{(lo.get('first_name') or '').strip()} {(lo.get('last_name') or '').strip()}".strip()
                        l_rows.append((
                            fuid, idx,
                            lo.get("id"),
                            lo.get("first_name"),
                            lo.get("last_name"),
                            full or None,
                            lob.get("covered_position"),
                            bool(lob.get("new")),
                        ))
                    for ge in act.get("government_entities") or []:
                        ge_rows.append((
                            fuid, idx, ge.get("id"), ge.get("name"),
                        ))
            if f_rows:
                con.executemany(
                    "INSERT OR REPLACE INTO senate_filings VALUES (" + ",".join(["?"] * 24) + ")",
                    f_rows,
                )
            if a_rows:
                con.executemany("INSERT INTO senate_activities VALUES (?,?,?,?,?)", a_rows)
            if l_rows:
                con.executemany("INSERT INTO senate_lobbyists VALUES (?,?,?,?,?,?,?,?)", l_rows)
            if ge_rows:
                con.executemany("INSERT INTO senate_gov_entities VALUES (?,?,?,?)", ge_rows)
            total += len(f_rows)
            log(f"  +{len(f_rows)} filings (total={total})")


def load_senate_contributions(con, root: Path) -> None:
    base = root / "senate"
    total = 0
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
                    rows.append((
                        fuid,
                        report.get("filing_year") or year,
                        report.get("filing_period"),
                        reg.get("id"),
                        reg.get("name"),
                        lob.get("id"),
                        lob.get("first_name"),
                        lob.get("last_name"),
                        ci.get("contributor_name"),
                        ci.get("contribution_type"),
                        _floaty(ci.get("amount")),
                        ci.get("payee_name"),
                        ci.get("honoree_name"),
                        ci.get("date"),
                    ))
            if rows:
                con.executemany(
                    "INSERT INTO senate_contribution_items VALUES (" + ",".join(["?"] * 14) + ")",
                    rows,
                )
            total += len(rows)
            log(f"  +{len(rows)} contribution items (total={total})")


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
        # report types like 1T (1st Quarter Termination), 2T, 1A (amendment)
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

    filing_row = (
        house_file,
        doc_type,
        report_type,
        filing_period,
        filing_year,
        senate_id,
        _senate_registrant_from_id(senate_id),
        house_id,
        org,
        _clean(org),
        client,
        _clean(client),
        _txt(root.find("clientState")) or _txt(root.find("state")),
        _txt(root.find("clientCountry")) or _txt(root.find("country")),
        _floaty(_txt(root.find("income"))),
        _floaty(_txt(root.find("expenses"))),
        _txt(root.find("expensesMethod")),
        _txt(root.find("noLobbying")),
        _txt(root.find("terminationDate")),
        _txt(root.find("printedName")),
        _txt(root.find("signedDate")),
    )

    activity_rows = []
    lobbyist_rows = []
    for idx, ai in enumerate(root.findall("./alis/ali_info")):
        code = _txt(ai.find("issueAreaCode"))
        desc = _txt(ai.find("./specific_issues/description"))
        agencies = _txt(ai.find("federal_agencies"))
        fei = _txt(ai.find("foreign_entity_issues"))
        if not any([code, desc, agencies, fei]):
            # all-empty ali_info — skip filler
            # but still emit if there are lobbyists with names below
            lobs_named = [lob for lob in ai.findall("./lobbyists/lobbyist")
                          if _txt(lob.find("lobbyistFirstName")) or _txt(lob.find("lobbyistLastName"))]
            if not lobs_named:
                continue
        activity_rows.append((house_file, idx, code, desc, agencies, fei))
        for lob in ai.findall("./lobbyists/lobbyist"):
            fn = _txt(lob.find("lobbyistFirstName"))
            ln = _txt(lob.find("lobbyistLastName"))
            if not (fn or ln):
                continue
            lobbyist_rows.append((
                house_file, idx, fn, ln,
                f"{fn or ''} {ln or ''}".strip(),
                _txt(lob.find("lobbyistSuffix")),
                _txt(lob.find("coveredPosition")),
                _txt(lob.find("lobbyistNew")),
            ))
    return filing_row, activity_rows, lobbyist_rows


def load_house_xml(con, root: Path, workers: int = 6) -> None:
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
        log(f"House {sd.name}: {len(xml_paths)} files (period={dir_period}, year={dir_year}) workers={workers}")
        if not xml_paths:
            continue
        args_iter = [(p, dir_period, dir_year) for p in xml_paths]

        filings_batch = []
        activities_batch = []
        lobbyists_batch = []
        processed = 0
        BATCH = 5000

        def _flush():
            nonlocal filings_batch, activities_batch, lobbyists_batch
            if filings_batch:
                con.executemany(
                    "INSERT OR REPLACE INTO house_filings VALUES (" + ",".join(["?"] * 21) + ")",
                    filings_batch,
                )
            if activities_batch:
                con.executemany("INSERT INTO house_activities VALUES (?,?,?,?,?,?)", activities_batch)
            if lobbyists_batch:
                con.executemany("INSERT INTO house_lobbyists VALUES (?,?,?,?,?,?,?,?)", lobbyists_batch)
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
                    log(f"  {sd.name}: {processed}/{len(xml_paths)}")
            _flush()
        grand_total += processed
        log(f"  done {sd.name}; cumulative={grand_total}")


def load_press(con, root: Path) -> None:
    base = root / "congress_press"
    if not base.exists():
        log(f"missing {base}")
        return
    files = sorted(list(base.glob("*.jsonl")) + list(base.glob("*/*.jsonl")))
    total = 0
    for fp in files:
        rows = []
        with open(fp) as f:
            for line in f:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                m = r.get("member") or {}
                rows.append((
                    r.get("url"),
                    r.get("title"),
                    r.get("date"),
                    r.get("date_source"),
                    r.get("source"),
                    r.get("domain"),
                    r.get("scraper"),
                    m.get("bioguide_id"),
                    m.get("name"),
                    m.get("party"),
                    m.get("state"),
                    m.get("chamber"),
                    r.get("text"),
                ))
        if rows:
            con.executemany("INSERT INTO press_releases VALUES (" + ",".join(["?"] * 13) + ")", rows)
            total += len(rows)
            log(f"{fp.name}: +{len(rows)} (total={total})")


def build_indexes(con) -> None:
    log("Creating indexes / analyzing")
    con.execute("""
        CREATE INDEX IF NOT EXISTS idx_filings_year ON senate_filings(filing_year);
        CREATE INDEX IF NOT EXISTS idx_filings_client ON senate_filings(client_id);
        CREATE INDEX IF NOT EXISTS idx_filings_registrant ON senate_filings(registrant_id);
        CREATE INDEX IF NOT EXISTS idx_act_uuid ON senate_activities(filing_uuid);
        CREATE INDEX IF NOT EXISTS idx_act_issue ON senate_activities(general_issue_code);
        CREATE INDEX IF NOT EXISTS idx_lob_uuid ON senate_lobbyists(filing_uuid);
        CREATE INDEX IF NOT EXISTS idx_lob_full ON senate_lobbyists(full_name);
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
    build_indexes(con)
    log("Done.")


if __name__ == "__main__":
    main()
