"""Load House LDA XML disclosures into duckdb (parallel parsing).

Tables:
  house_filing       - one row per XML (LD-1 registrations + LD-2 quarterlies)
  house_activity     - one row per <ali_info>
  house_lobbyist     - one row per <lobbyist> under each <ali_info>
  house_foreign      - one row per foreign entity
"""
import duckdb
import sys
import os
import json
import re
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from xml.etree import ElementTree as ET
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = Path(os.environ.get("LDA_DATA_DIR", ROOT / ".context" / "data" / "data"))
DATA = DATA_ROOT / "house"
DB = Path(os.environ.get("LDA_DB_PATH", ROOT / ".context" / "db" / "investigation.duckdb"))
TMP = Path(os.environ.get("LDA_TMP_DIR", ROOT / ".context" / "db" / "_house_parts"))
TMP.mkdir(parents=True, exist_ok=True)


def _txt(elem, tag):
    if elem is None:
        return None
    v = elem.findtext(tag)
    if v is None:
        return None
    v = v.strip()
    return v or None


def _num(s):
    if s is None:
        return None
    s = s.strip().replace(",", "").replace("$", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_file(xml_path: str, period_dir: str):
    """Parse a single LDA XML. Returns (filing_row, activities, lobbyists, foreign)."""
    try:
        tree = ET.parse(xml_path)
    except ET.ParseError:
        return None, [], [], []
    root = tree.getroot()
    tag = root.tag  # LOBBYINGDISCLOSURE1 or LOBBYINGDISCLOSURE2

    # Detect period: e.g. "2025_1stQuarter_XML" or "2025_Registrations_XML"
    m = re.match(r"(\d{4})_(\d)(st|nd|rd|th)Quarter_XML", period_dir)
    if m:
        year = int(m.group(1))
        quarter = int(m.group(2))
        period_kind = "quarterly"
    elif period_dir.endswith("_Registrations_XML"):
        year = int(period_dir.split("_", 1)[0])
        quarter = None
        period_kind = "registration"
    else:
        year = None
        quarter = None
        period_kind = None

    filing_id = Path(xml_path).stem

    org = _txt(root, "organizationName")
    client = _txt(root, "clientName")
    senate_id = _txt(root, "senateID")
    house_id = _txt(root, "houseID")
    report_year = _txt(root, "reportYear")
    report_type = _txt(root, "reportType")
    termination_date = _txt(root, "terminationDate")
    income = _num(_txt(root, "income"))
    expenses = _num(_txt(root, "expenses"))
    expenses_method = _txt(root, "expensesMethod")
    signed_date = _txt(root, "signedDate")
    no_lobbying = _txt(root, "noLobbying")
    state = _txt(root, "state")
    country = _txt(root, "country")
    self_select = _txt(root, "selfSelect")

    filing = {
        "filing_id": filing_id,
        "doctype": tag,
        "period_dir": period_dir,
        "period_year": year,
        "period_quarter": quarter,
        "period_kind": period_kind,
        "organization_name": org,
        "client_name": client,
        "senate_id": senate_id,
        "house_id": house_id,
        "report_year": int(report_year) if report_year and report_year.isdigit() else None,
        "report_type": report_type,
        "termination_date": termination_date,
        "income": income,
        "expenses": expenses,
        "expenses_method": expenses_method,
        "signed_date": signed_date,
        "no_lobbying": no_lobbying,
        "state": state,
        "country": country,
        "self_select": self_select,
    }

    activities = []
    lobbyists = []

    # Activities under <alis>/<ali_info>
    alis = root.find("alis")
    if alis is not None:
        for i, ali in enumerate(alis.findall("ali_info")):
            issue_code = _txt(ali, "issueAreaCode")
            desc_elem = ali.find("specific_issues")
            desc = _txt(desc_elem, "description") if desc_elem is not None else None
            fed_agencies = _txt(ali, "federal_agencies")
            activities.append({
                "filing_id": filing_id,
                "act_idx": i,
                "issue_code": issue_code,
                "description": desc,
                "federal_agencies": fed_agencies,
            })
            lobj_parent = ali.find("lobbyists")
            if lobj_parent is not None:
                for j, lo in enumerate(lobj_parent.findall("lobbyist")):
                    fn = _txt(lo, "lobbyistFirstName")
                    ln = _txt(lo, "lobbyistLastName")
                    if not fn and not ln:
                        continue
                    lobbyists.append({
                        "filing_id": filing_id,
                        "act_idx": i,
                        "lob_idx": j,
                        "first_name": fn,
                        "last_name": ln,
                        "suffix": _txt(lo, "lobbyistSuffix"),
                        "covered_position": _txt(lo, "coveredPosition"),
                        "new": _txt(lo, "lobbyistNew"),
                    })

    # Foreign entities live under <foreignEntities><foreignEntity> typically
    foreigns = []
    fe_parent = root.find("foreignEntities")
    if fe_parent is not None:
        for j, fe in enumerate(fe_parent.findall(".//foreignEntity")):
            foreigns.append({
                "filing_id": filing_id,
                "f_idx": j,
                "name": _txt(fe, "name"),
                "country": _txt(fe, "country"),
                "ppb_country": _txt(fe, "ppbCountry"),
                "contribution": _num(_txt(fe, "contribution")),
                "ownership": _num(_txt(fe, "ownership")),
                "status": _txt(fe, "status"),
            })
    return filing, activities, lobbyists, foreigns


def process_dir(period_dir_name: str):
    """Process one period directory. Returns counts and writes 4 parquet shards."""
    period = DATA / period_dir_name
    filings = []
    activities = []
    lobbyists = []
    foreigns = []
    for xml in period.glob("*.xml"):
        f, acts, lobs, fe = parse_file(str(xml), period_dir_name)
        if f is None:
            continue
        filings.append(f)
        activities.extend(acts)
        lobbyists.extend(lobs)
        foreigns.extend(fe)

    base = TMP / period_dir_name
    base.mkdir(parents=True, exist_ok=True)
    if filings:
        pd.DataFrame(filings).to_parquet(base / "filings.parquet", index=False)
    if activities:
        pd.DataFrame(activities).to_parquet(base / "activities.parquet", index=False)
    if lobbyists:
        pd.DataFrame(lobbyists).to_parquet(base / "lobbyists.parquet", index=False)
    if foreigns:
        pd.DataFrame(foreigns).to_parquet(base / "foreigns.parquet", index=False)
    return period_dir_name, len(filings), len(activities), len(lobbyists), len(foreigns)


def main():
    period_dirs = sorted([d.name for d in DATA.iterdir() if d.is_dir()])
    print(f"Processing {len(period_dirs)} period dirs...", file=sys.stderr)

    workers = max(2, os.cpu_count() - 1)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(process_dir, p): p for p in period_dirs}
        for fut in as_completed(futures):
            p, nf, na, nl, nfe = fut.result()
            print(f"  {p}: filings={nf} acts={na} lobbyists={nl} foreign={nfe}", file=sys.stderr)

    # Now stitch the parquets into duckdb.
    con = duckdb.connect(str(DB))
    for tbl, glob in [
        ("house_filing", "filings.parquet"),
        ("house_activity", "activities.parquet"),
        ("house_lobbyist", "lobbyists.parquet"),
        ("house_foreign", "foreigns.parquet"),
    ]:
        files = sorted(TMP.glob(f"*/{glob}"))
        con.execute(f"DROP TABLE IF EXISTS {tbl}")
        if files:
            con.execute(
                f"CREATE TABLE {tbl} AS SELECT * FROM read_parquet(?, union_by_name=true)",
                [[str(f) for f in files]],
            )
            n = con.execute(f"SELECT count(*) FROM {tbl}").fetchone()[0]
            print(f"  {tbl}: {n}", file=sys.stderr)
        else:
            print(f"  {tbl}: no parquet files", file=sys.stderr)
    con.close()


if __name__ == "__main__":
    main()
