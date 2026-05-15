#!/usr/bin/env python3
"""Parse the LDA covered_position free-text into structured prior-role rows."""
from __future__ import annotations
import argparse
import re
import time
import duckdb


# Role family patterns; tuple of (regex, family, base_confidence)
ROLE_PATTERNS = [
    (r"\bU\.?S\.?\s+(Senator|Representative)\b|\bMember\s+of\s+Congress\b", "Member of Congress", 0.95),
    (r"\bChief\s+of\s+Staff\b", "Chief of Staff", 0.9),
    (r"\bDeputy\s+Chief\s+of\s+Staff\b", "Deputy Chief of Staff", 0.9),
    (r"\bLegislative\s+Director\b", "Legislative Director", 0.9),
    (r"\bLegislative\s+Assistant\b|\bLegislative\s+Counsel\b", "Legislative Staff", 0.85),
    (r"\bDistrict\s+Director\b", "District Director", 0.85),
    (r"\bCommunications\s+Director\b|\bPress\s+Secretary\b", "Communications Staff", 0.85),
    (r"\bPolicy\s+Director\b|\bPolicy\s+Advisor\b", "Policy Staff", 0.8),
    (r"\bSenior\s+Advisor\b|\bSenior\s+Adviser\b", "Senior Advisor", 0.85),
    (r"\bGeneral\s+Counsel\b", "General Counsel", 0.9),
    (r"\bCounsel\b", "Counsel", 0.7),
    (r"\bDeputy\s+Assistant\s+Secretary\b", "Deputy Assistant Secretary", 0.9),
    (r"\bAssistant\s+Secretary\b", "Assistant Secretary", 0.9),
    (r"\bUnder\s*Secretary\b", "Under Secretary", 0.9),
    (r"\bSecretary\b", "Secretary", 0.7),
    (r"\bDirector\b", "Director", 0.55),
    (r"\bDeputy\s+Director\b", "Deputy Director", 0.7),
    (r"\bCommissioner\b", "Commissioner", 0.85),
    (r"\bAdministrator\b", "Administrator", 0.85),
    (r"\bGovernor\b", "Governor", 0.85),
    (r"\bAttorney\s+General\b", "Attorney General", 0.85),
    (r"\bAmbassador\b", "Ambassador", 0.85),
    (r"\bJudge\b|\bJustice\b", "Judicial Officer", 0.85),
    (r"\bIntern\b|\bFellow\b|\bClerk\b", "Junior Staff", 0.6),
    (r"\bStaff\s+Director\b", "Staff Director", 0.9),
    (r"\bConfidential\s+Assistant\b|\bSpecial\s+Assistant\b", "Special Assistant", 0.75),
]

# Chamber detection
SENATE_PAT = re.compile(r"\b(U\.?S\.?\s+Senat\w*|Senator|Senate)\b", re.IGNORECASE)
HOUSE_PAT = re.compile(r"\bU\.?S\.?\s+(House|Representative)\b|\bHouse\s+of\s+Representatives\b|\bRep\.?\s+", re.IGNORECASE)
WH_PAT = re.compile(r"\b(White\s+House|Office\s+of\s+the\s+President|EOP|National\s+Security\s+Council)\b", re.IGNORECASE)
EXEC_PAT = re.compile(r"\bDepartment\s+of\b|\bDept\.?\s+of\b|\bAgency\b|\bAdministration\b|\bCommission\b|\bBoard\b", re.IGNORECASE)
JUDICIAL_PAT = re.compile(r"\bCourt\b|\bJudge\b|\bJustice\b", re.IGNORECASE)

# Principal extraction patterns
PRINCIPAL_PATTERNS = [
    re.compile(r"to\s+(?:U\.?S\.?\s+)?(?:Senator|Sen\.?)\s+([A-Z][A-Za-z.\-' ]+?)(?:\s+\(|,|;|$)"),
    re.compile(r"to\s+(?:U\.?S\.?\s+)?(?:Representative|Rep\.?)\s+([A-Z][A-Za-z.\-' ]+?)(?:\s+\(|,|;|$)"),
    re.compile(r"to\s+(?:the\s+)?Hon(?:orable)?\.?\s+([A-Z][A-Za-z.\-' ]+?)(?:\s+\(|,|;|$)"),
    re.compile(r"to\s+(?:U\.?S\.?\s+)?Senator\s+([A-Z][A-Za-z.\-' ]+)"),
    re.compile(r"for\s+(?:Sen(?:ator)?\.?|Rep(?:resentative)?\.?)\s+([A-Z][A-Za-z.\-' ]+)"),
]

AGENCY_PAT = re.compile(
    r"\b("
    r"Department\s+of\s+[A-Z][A-Za-z& ]+|"
    r"U\.?S\.?\s+Department\s+of\s+[A-Z][A-Za-z& ]+|"
    r"Office\s+of\s+[A-Z][A-Za-z& ]+|"
    r"Bureau\s+of\s+[A-Z][A-Za-z& ]+|"
    r"Federal\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*\s+(?:Commission|Bureau|Agency|Administration)"
    r")"
)


def parse_position(text: str):
    if not text:
        return None
    t = text.strip()
    if not t:
        return None
    # Detect chamber
    chamber = None
    if SENATE_PAT.search(t):
        chamber = "Senate"
    elif HOUSE_PAT.search(t):
        chamber = "House"
    elif WH_PAT.search(t):
        chamber = "Executive"
    elif JUDICIAL_PAT.search(t):
        chamber = "Judicial"
    elif EXEC_PAT.search(t):
        chamber = "Executive"
    # Role
    role = None
    role_conf = 0.0
    for pat, fam, conf in ROLE_PATTERNS:
        if re.search(pat, t, re.IGNORECASE):
            role = fam
            role_conf = conf
            break
    # Principal
    principal = None
    for pat in PRINCIPAL_PATTERNS:
        m = pat.search(t)
        if m:
            principal = m.group(1).strip().rstrip(",;")
            break
    if not principal:
        m = AGENCY_PAT.search(t)
        if m:
            principal = m.group(1).strip()
    confidence = role_conf
    if chamber:
        confidence = max(confidence, 0.4)
    if principal:
        confidence = min(1.0, confidence + 0.1)
    if not (chamber or role or principal):
        return None
    return chamber, role, principal, confidence


def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    args = ap.parse_args()
    con = duckdb.connect(args.db)
    log("Recreating revolving_door_positions")
    con.execute("""
        DROP TABLE IF EXISTS revolving_door_positions;
        CREATE TABLE revolving_door_positions (
            source VARCHAR,
            lobbyist_id BIGINT,
            house_file VARCHAR,
            filing_uuid VARCHAR,
            full_name VARCHAR,
            raw_text VARCHAR,
            chamber VARCHAR,
            role_family VARCHAR,
            principal_name VARCHAR,
            confidence DOUBLE
        );
    """)

    log("Reading senate covered_position rows")
    rows = con.execute("""
        SELECT filing_uuid, lobbyist_id, full_name, covered_position
        FROM senate_lobbyists
        WHERE covered_position IS NOT NULL AND length(trim(covered_position)) > 0
    """).fetchall()
    log(f"  {len(rows):,} senate rows")
    batch = []
    for fuid, lid, name, cp in rows:
        parsed = parse_position(cp)
        if parsed is None:
            continue
        ch, rf, pn, conf = parsed
        batch.append(("senate", lid, None, fuid, name, cp, ch, rf, pn, conf))
        if len(batch) >= 50000:
            con.executemany("INSERT INTO revolving_door_positions VALUES (?,?,?,?,?,?,?,?,?,?)", batch)
            batch = []
    if batch:
        con.executemany("INSERT INTO revolving_door_positions VALUES (?,?,?,?,?,?,?,?,?,?)", batch)
        batch = []

    log("Reading house covered_position rows")
    rows = con.execute("""
        SELECT house_file, full_name, covered_position
        FROM house_lobbyists
        WHERE covered_position IS NOT NULL AND length(trim(covered_position)) > 0
    """).fetchall()
    log(f"  {len(rows):,} house rows")
    for hf, name, cp in rows:
        parsed = parse_position(cp)
        if parsed is None:
            continue
        ch, rf, pn, conf = parsed
        batch.append(("house", None, hf, None, name, cp, ch, rf, pn, conf))
        if len(batch) >= 50000:
            con.executemany("INSERT INTO revolving_door_positions VALUES (?,?,?,?,?,?,?,?,?,?)", batch)
            batch = []
    if batch:
        con.executemany("INSERT INTO revolving_door_positions VALUES (?,?,?,?,?,?,?,?,?,?)", batch)

    con.execute("""
        CREATE INDEX IF NOT EXISTS idx_rdp_name ON revolving_door_positions(full_name);
        CREATE INDEX IF NOT EXISTS idx_rdp_principal ON revolving_door_positions(principal_name);
        ANALYZE;
    """)
    n = con.execute("SELECT COUNT(*) FROM revolving_door_positions").fetchone()[0]
    log(f"Done. {n:,} parsed positions")


if __name__ == "__main__":
    main()
