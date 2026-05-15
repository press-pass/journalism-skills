"""House LDA ETL: 409K XML files → parquet.

Run inside docker. Streams XML to keep memory bounded. Writes:
  parquet/house_filings.parquet      one row per filing
  parquet/house_activities.parquet   one row per ali_info block
  parquet/house_lobbyists.parquet    one row per lobbyist within an ali_info

Schemas mirror the Senate parquet so they can be union'd.
"""
from __future__ import annotations
import argparse, glob, sys, os, re
from pathlib import Path
import pyarrow as pa, pyarrow.parquet as pq
from lxml import etree
from tqdm import tqdm


FILING_SCHEMA = pa.schema([
    ("house_filing_id", pa.string()),    # filename (numeric)
    ("filing_dir", pa.string()),         # e.g. 2025_1stQuarter_XML
    ("filing_year", pa.int64()),
    ("filing_quarter", pa.string()),     # Q1..Q4 or REG
    ("organization_name", pa.string()),
    ("client_name", pa.string()),
    ("senate_id", pa.string()),
    ("house_id", pa.string()),
    ("report_type", pa.string()),
    ("report_year", pa.int64()),
    ("termination_date", pa.string()),
    ("no_lobbying", pa.string()),
    ("income", pa.float64()),
    ("expenses", pa.float64()),
    ("state", pa.string()),
    ("country", pa.string()),
    ("signed_date", pa.string()),
    ("foreign_entity_count", pa.int64()),
    ("foreign_entity_names", pa.string()),
])
ACT_SCHEMA = pa.schema([
    ("house_filing_id", pa.string()),
    ("filing_dir", pa.string()),
    ("filing_year", pa.int64()),
    ("filing_quarter", pa.string()),
    ("issue_code", pa.string()),
    ("description", pa.string()),
    ("federal_agencies", pa.string()),
    ("organization_name", pa.string()),
    ("client_name", pa.string()),
    ("income", pa.float64()),
    ("expenses", pa.float64()),
])
LO_SCHEMA = pa.schema([
    ("house_filing_id", pa.string()),
    ("filing_dir", pa.string()),
    ("filing_year", pa.int64()),
    ("filing_quarter", pa.string()),
    ("issue_code", pa.string()),
    ("first_name", pa.string()),
    ("last_name", pa.string()),
    ("suffix", pa.string()),
    ("covered_position", pa.string()),
    ("new_lobbyist", pa.string()),
    ("organization_name", pa.string()),
    ("client_name", pa.string()),
])


def quarter_from_dir(dirname: str):
    m = re.match(r"(\d{4})_(Registrations|(\d)(st|nd|rd|th)Quarter)_XML", dirname)
    if not m:
        return None, None
    year = int(m.group(1))
    if m.group(2) == "Registrations":
        return year, "REG"
    return year, f"Q{m.group(3)}"


def _txt(elem, default=""):
    if elem is None:
        return default
    t = (elem.text or "")
    return t.strip()


def _num(v):
    try:
        v = (v or "").strip().replace(",", "").replace("$", "")
        if not v:
            return None
        return float(v)
    except (ValueError, TypeError):
        return None


def parse_filing(path: Path, filing_dir: str):
    house_id = path.stem
    year, qtr = quarter_from_dir(filing_dir)
    try:
        root = etree.parse(str(path)).getroot()
    except etree.XMLSyntaxError:
        return None, [], []
    is_reg = root.tag == "LOBBYINGDISCLOSURE1"
    org = _txt(root.find("organizationName"))
    client = _txt(root.find("clientName"))
    senate_id = _txt(root.find("senateID"))
    house_id_inside = _txt(root.find("houseID"))
    report_type = _txt(root.find("reportType"))
    report_year = _txt(root.find("reportYear"))
    try:
        report_year_i = int(report_year) if report_year else None
    except ValueError:
        report_year_i = None
    income = _num(_txt(root.find("income")))
    expenses = _num(_txt(root.find("expenses")))
    state = _txt(root.find("state"))
    country = _txt(root.find("country"))
    signed = _txt(root.find("signedDate"))
    term = _txt(root.find("terminationDate"))
    no_lobbying = _txt(root.find("noLobbying"))
    # foreign entities
    fe_names = []
    for fe in root.findall(".//foreignEntities/foreignEntity"):
        nm = _txt(fe.find("name") if fe.find("name") is not None else fe.find("foreign_entity_name"))
        if nm:
            fe_names.append(nm)

    activities = []
    lobbyists = []
    for ali in root.findall(".//alis/ali_info"):
        code = _txt(ali.find("issueAreaCode"))
        desc_elem = ali.find("specific_issues/description")
        description = _txt(desc_elem)
        fed = _txt(ali.find("federal_agencies"))
        activities.append({
            "house_filing_id": house_id,
            "filing_dir": filing_dir,
            "filing_year": year,
            "filing_quarter": qtr,
            "issue_code": code or None,
            "description": description,
            "federal_agencies": fed,
            "organization_name": org,
            "client_name": client,
            "income": income,
            "expenses": expenses,
        })
        for lo in ali.findall("lobbyists/lobbyist"):
            first = _txt(lo.find("lobbyistFirstName"))
            last = _txt(lo.find("lobbyistLastName"))
            suffix = _txt(lo.find("lobbyistSuffix"))
            cov = _txt(lo.find("coveredPosition"))
            new = _txt(lo.find("lobbyistNew"))
            if not (first or last or cov):
                continue  # blank slot
            lobbyists.append({
                "house_filing_id": house_id,
                "filing_dir": filing_dir,
                "filing_year": year,
                "filing_quarter": qtr,
                "issue_code": code or None,
                "first_name": first,
                "last_name": last,
                "suffix": suffix,
                "covered_position": cov,
                "new_lobbyist": new,
                "organization_name": org,
                "client_name": client,
            })

    filing = {
        "house_filing_id": house_id,
        "filing_dir": filing_dir,
        "filing_year": year,
        "filing_quarter": qtr,
        "organization_name": org,
        "client_name": client,
        "senate_id": senate_id,
        "house_id": house_id_inside,
        "report_type": report_type,
        "report_year": report_year_i,
        "termination_date": term,
        "no_lobbying": no_lobbying,
        "income": income,
        "expenses": expenses,
        "state": state,
        "country": country,
        "signed_date": signed,
        "foreign_entity_count": len(fe_names),
        "foreign_entity_names": "|".join(fe_names),
    }
    return filing, activities, lobbyists


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--house_root", required=True)
    ap.add_argument("--out_dir", required=True)
    args = ap.parse_args()
    out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)

    filing_writer = pq.ParquetWriter(str(out / "house_filings.parquet"), FILING_SCHEMA, compression="zstd")
    act_writer = pq.ParquetWriter(str(out / "house_activities.parquet"), ACT_SCHEMA, compression="zstd")
    lo_writer = pq.ParquetWriter(str(out / "house_lobbyists.parquet"), LO_SCHEMA, compression="zstd")

    filings = []
    activities = []
    lobbyists = []
    BATCH = 10000
    n_fil = n_act = n_lo = 0

    dirs = sorted(d for d in os.listdir(args.house_root) if d.endswith("_XML"))
    for d in dirs:
        files = sorted(glob.glob(os.path.join(args.house_root, d, "*.xml")))
        for p in tqdm(files, desc=d):
            filing, acts, los = parse_filing(Path(p), d)
            if filing is None:
                continue
            filings.append(filing)
            activities.extend(acts)
            lobbyists.extend(los)
            if len(filings) >= BATCH:
                filing_writer.write_table(pa.Table.from_pylist(filings, schema=FILING_SCHEMA))
                n_fil += len(filings); filings = []
            if len(activities) >= BATCH:
                act_writer.write_table(pa.Table.from_pylist(activities, schema=ACT_SCHEMA))
                n_act += len(activities); activities = []
            if len(lobbyists) >= BATCH:
                lo_writer.write_table(pa.Table.from_pylist(lobbyists, schema=LO_SCHEMA))
                n_lo += len(lobbyists); lobbyists = []

    if filings:
        filing_writer.write_table(pa.Table.from_pylist(filings, schema=FILING_SCHEMA)); n_fil += len(filings)
    if activities:
        act_writer.write_table(pa.Table.from_pylist(activities, schema=ACT_SCHEMA)); n_act += len(activities)
    if lobbyists:
        lo_writer.write_table(pa.Table.from_pylist(lobbyists, schema=LO_SCHEMA)); n_lo += len(lobbyists)

    filing_writer.close(); act_writer.close(); lo_writer.close()
    print(f"HOUSE FILINGS={n_fil} ACTIVITIES={n_act} LOBBYISTS={n_lo}", file=sys.stderr)


if __name__ == "__main__":
    main()
