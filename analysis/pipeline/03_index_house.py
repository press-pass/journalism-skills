"""Index House LDA XML filings into Parquet using parallel parsing.

Handles two schemas:
- LD-1 registrations: <LOBBYINGDISCLOSURE1>
- LD-2 quarterly reports: <LOBBYINGDISCLOSURE2>

For each quarter/registration directory, writes:
  /parquet/house/filings/{dir}.parquet  - one row per filing
  /parquet/house/lobbyists/{dir}.parquet - one row per (filing, lobbyist) pair
  /parquet/house/issues/{dir}.parquet   - one row per (filing, ali_info specific_issue)
  /parquet/house/agencies/{dir}.parquet - one row per (filing, federal_agency)

Run from container: python analysis/pipeline/03_index_house.py
"""
from __future__ import annotations

import os
import re
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
from lxml import etree

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
PARQUET_DIR = Path(os.environ.get("PARQUET_DIR", "/parquet"))


def _txt(elem, tag: str) -> str | None:
    """Read text from a child tag, stripped; return None if empty."""
    if elem is None:
        return None
    e = elem.find(tag)
    if e is None or e.text is None:
        return None
    s = e.text.strip()
    return s or None


def _float(elem, tag: str) -> float | None:
    s = _txt(elem, tag)
    if s is None:
        return None
    try:
        return float(s.replace(",", "").replace("$", "").strip())
    except ValueError:
        return None


def _parse_quarter_period(dirname: str) -> tuple[int, str]:
    """Return (year, period_code) for a directory name.

    Periods: Q1, Q2, Q3, Q4 for quarterlies; REG for registrations.
    """
    m = re.match(r"(\d{4})_(\d)(st|nd|rd|th)Quarter_XML", dirname)
    if m:
        return int(m.group(1)), f"Q{m.group(2)}"
    m = re.match(r"(\d{4})_Registrations_XML", dirname)
    if m:
        return int(m.group(1)), "REG"
    return 0, "UNKNOWN"


def parse_ld2(root, filing_id: str, year: int, period: str) -> dict:
    """Parse an LD-2 (quarterly) filing root element into a flat dict."""
    rec = {
        "filing_id": filing_id,
        "schema": "LD2",
        "year": year,
        "period": period,
        "organizationName": _txt(root, "organizationName"),
        "selfSelect": _txt(root, "selfSelect"),
        "clientName": _txt(root, "clientName"),
        "clientGovtEntity": _txt(root, "clientGovtEntity"),
        "senateID": _txt(root, "senateID"),
        "houseID": _txt(root, "houseID"),
        "reportYear": _txt(root, "reportYear"),
        "reportType": _txt(root, "reportType"),
        "terminationDate": _txt(root, "terminationDate"),
        "noLobbying": _txt(root, "noLobbying"),
        "income": _float(root, "income"),
        "expenses": _float(root, "expenses"),
        "expensesMethod": _txt(root, "expensesMethod"),
        "signedDate": _txt(root, "signedDate"),
        "city": _txt(root, "city"),
        "state": _txt(root, "state"),
        "country": _txt(root, "country"),
    }
    return rec


def parse_ld1(root, filing_id: str, year: int, period: str) -> dict:
    rec = {
        "filing_id": filing_id,
        "schema": "LD1",
        "year": year,
        "period": period,
        "organizationName": _txt(root, "organizationName"),
        "selfSelect": _txt(root, "selfSelect"),
        "clientName": _txt(root, "clientName"),
        "clientGovtEntity": _txt(root, "clientGovtEntity"),
        "senateID": _txt(root, "senateID"),
        "houseID": _txt(root, "houseID"),
        "registrantGeneralDescription": _txt(root, "registrantGeneralDescription"),
        "clientGeneralDescription": _txt(root, "clientGeneralDescription"),
        "regType": _txt(root, "regType"),
        "specific_issues": _txt(root, "specific_issues"),
        "signedDate": _txt(root, "signedDate"),
        "city": _txt(root, "city"),
        "state": _txt(root, "state"),
        "country": _txt(root, "country"),
        "clientState": _txt(root, "clientState"),
        "clientCity": _txt(root, "clientCity"),
        "clientCountry": _txt(root, "clientCountry"),
        "effectiveDate": _txt(root, "effectiveDate"),
    }
    return rec


def parse_quarterly_extras(root, filing_id: str, year: int, period: str):
    """Yield lobbyist, issue, agency rows for an LD-2 file."""
    lobbyists, issues, agencies = [], [], []
    alis = root.find("alis")
    if alis is None:
        return lobbyists, issues, agencies

    for ali in alis.findall("ali_info"):
        ali_code = _txt(ali, "issueAreaCode")

        # specific_issues description (text)
        si = ali.find("specific_issues")
        si_desc = _txt(si, "description") if si is not None else None

        # federal_agencies
        agencies_txt = _txt(ali, "federal_agencies")
        if agencies_txt:
            for ag in agencies_txt.split(","):
                ag = ag.strip()
                if ag:
                    agencies.append({
                        "filing_id": filing_id, "year": year, "period": period,
                        "ali_code": ali_code, "agency": ag,
                    })

        if ali_code or si_desc:
            issues.append({
                "filing_id": filing_id, "year": year, "period": period,
                "ali_code": ali_code, "description": si_desc,
            })

        lob_container = ali.find("lobbyists")
        if lob_container is not None:
            for lob in lob_container.findall("lobbyist"):
                first = _txt(lob, "lobbyistFirstName")
                last = _txt(lob, "lobbyistLastName")
                covered = _txt(lob, "coveredPosition")
                new = _txt(lob, "lobbyistNew")
                if first or last or covered:
                    lobbyists.append({
                        "filing_id": filing_id, "year": year, "period": period,
                        "ali_code": ali_code,
                        "first_name": first,
                        "last_name": last,
                        "suffix": _txt(lob, "lobbyistSuffix"),
                        "covered_position": covered,
                        "is_new": new,
                    })
    return lobbyists, issues, agencies


def parse_registration_extras(root, filing_id: str, year: int, period: str):
    """Yield lobbyist rows for an LD-1 file."""
    lobbyists = []
    lob_container = root.find("lobbyists")
    if lob_container is not None:
        for lob in lob_container.findall("lobbyist"):
            first = _txt(lob, "lobbyistFirstName")
            last = _txt(lob, "lobbyistLastName")
            covered = _txt(lob, "coveredPosition")
            if first or last or covered:
                lobbyists.append({
                    "filing_id": filing_id, "year": year, "period": period,
                    "ali_code": None,
                    "first_name": first,
                    "last_name": last,
                    "suffix": _txt(lob, "lobbyistSuffix"),
                    "covered_position": covered,
                    "is_new": None,
                })
    return lobbyists


def parse_dir(dir_path: str) -> tuple[str, int, int, int, int]:
    """Parse all XMLs in one directory; write 4 Parquet files."""
    d = Path(dir_path)
    year, period = _parse_quarter_period(d.name)
    out = PARQUET_DIR / "house"

    filings_rows = []
    lobbyists_rows = []
    issues_rows = []
    agencies_rows = []

    parser = etree.XMLParser(recover=True, huge_tree=True)
    for xml_path in d.glob("*.xml"):
        filing_id = xml_path.stem
        try:
            tree = etree.parse(str(xml_path), parser)
            root = tree.getroot()
        except Exception:
            continue

        tag = (root.tag or "").upper()
        if tag == "LOBBYINGDISCLOSURE2":
            filings_rows.append(parse_ld2(root, filing_id, year, period))
            lobs, issues, ags = parse_quarterly_extras(root, filing_id, year, period)
            lobbyists_rows.extend(lobs)
            issues_rows.extend(issues)
            agencies_rows.extend(ags)
        elif tag == "LOBBYINGDISCLOSURE1":
            filings_rows.append(parse_ld1(root, filing_id, year, period))
            lobs = parse_registration_extras(root, filing_id, year, period)
            lobbyists_rows.extend(lobs)
        else:
            continue

    if filings_rows:
        (out / "filings").mkdir(parents=True, exist_ok=True)
        pd.DataFrame(filings_rows).to_parquet(
            out / "filings" / f"{d.name}.parquet", index=False
        )
    if lobbyists_rows:
        (out / "lobbyists").mkdir(parents=True, exist_ok=True)
        pd.DataFrame(lobbyists_rows).to_parquet(
            out / "lobbyists" / f"{d.name}.parquet", index=False
        )
    if issues_rows:
        (out / "issues").mkdir(parents=True, exist_ok=True)
        pd.DataFrame(issues_rows).to_parquet(
            out / "issues" / f"{d.name}.parquet", index=False
        )
    if agencies_rows:
        (out / "agencies").mkdir(parents=True, exist_ok=True)
        pd.DataFrame(agencies_rows).to_parquet(
            out / "agencies" / f"{d.name}.parquet", index=False
        )

    return d.name, len(filings_rows), len(lobbyists_rows), len(issues_rows), len(agencies_rows)


def main() -> None:
    house_root = DATA_DIR / "house"
    dirs = sorted([p for p in house_root.iterdir() if p.is_dir()])
    print(f"Parsing {len(dirs)} directories in parallel")

    with ProcessPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(parse_dir, str(d)): d.name for d in dirs}
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                d_name, n_f, n_l, n_i, n_a = fut.result()
                print(f"  {d_name}: filings={n_f:,} lobbyists={n_l:,} issues={n_i:,} agencies={n_a:,}")
            except Exception as e:
                print(f"  {name}: FAILED: {e}")


if __name__ == "__main__":
    main()
