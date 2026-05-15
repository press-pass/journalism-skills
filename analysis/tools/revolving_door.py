"""Parse covered_position free-text into normalized role + source-office.

Runs over the entire Senate + House lobbyist corpora and emits a Parquet
table at /parquet/revolving_door.parquet. Optionally produces a Markdown
summary with top flows.

Deterministic: regex + curated dictionaries. No LLM calls.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from views import connect  # type: ignore


# ---------------- Role detection (most-senior wins) ----------------
# Order = priority (top is most senior)
ROLE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("MEMBER",          re.compile(r"\b(former\s+(member|representative|senator)|former\s+u\.?s\.?\s+representative|former\s+u\.?s\.?\s+senator)\b", re.I)),
    ("MEMBER",          re.compile(r"\b(member\s+of\s+congress|u\.?s\.?\s+(senator|representative|congressman|congresswoman))\b", re.I)),
    ("CHIEF_OF_STAFF",  re.compile(r"\b(chief\s+of\s+staff|cos)\b", re.I)),
    ("STAFF_DIRECTOR",  re.compile(r"\b(staff\s+director)\b", re.I)),
    ("LEG_DIRECTOR",    re.compile(r"\b(legislative\s+director|leg(\s|\.)?\s*director|\bld\b)", re.I)),
    ("COUNSEL",         re.compile(r"\b(chief\s+counsel|gen(eral)?\s+counsel|senior\s+counsel|counsel)\b", re.I)),
    ("LEG_ASSISTANT",   re.compile(r"\b(legislative\s+assistant|leg(\s|\.)?\s*assistant|\bla\b)", re.I)),
    ("LEG_CORRESPOND",  re.compile(r"\b(legislative\s+correspondent|\blc\b)", re.I)),
    ("PROF_STAFF",      re.compile(r"\b(professional\s+staff)\b", re.I)),
    ("PRESS_SEC",       re.compile(r"\b(press\s+sec(retary)?|comms?\s+director|communications\s+director)\b", re.I)),
    ("FLOOR_OPS",       re.compile(r"\b(floor\s+operations|floor\s+director)\b", re.I)),
    ("STAFF_ASSISTANT", re.compile(r"\b(staff\s+assistant)\b", re.I)),
    ("CONSULTANT",      re.compile(r"\b(consultant|advisor|adviser|specialist)\b", re.I)),
    ("OTHER_AIDE",      re.compile(r"\b(aide|deputy|associate)\b", re.I)),
]

# ---------------- Source-office detection ----------------
SENATE_COMMITTEE_RE = re.compile(
    r"(?:U\.?S\.?\s+)?Senate\s+([A-Z][A-Za-z,&'\.\-\s]+?)\s+Committee", re.I
)
HOUSE_COMMITTEE_RE = re.compile(
    r"(?:U\.?S\.?\s+)?House\s+([A-Z][A-Za-z,&'\.\-\s]+?)\s+Committee", re.I
)
JOINT_COMMITTEE_RE = re.compile(
    r"Joint\s+([A-Z][A-Za-z,&'\.\-\s]+?)\s+Committee", re.I
)
# Capture the actual member surname when present
MEMBER_RE = re.compile(
    r"\b(?:Sen\.?|Senator|Rep\.?|Representative|Congressman|Congresswoman)\s+"
    r"([A-Z][A-Za-z'\-]+(?:\s+[A-Z][A-Za-z'\-]+)*)"
)
# In some filings the member is referenced by ROLE — Member Office (Hoyer)
PAREN_MEMBER_RE = re.compile(
    r"(?:Member\s+Office|Office)\s*\(([A-Za-z'\-\s,\.]+)\)", re.I
)

AGENCY_KEYWORDS = {
    "USDA": ["USDA", "U.S. Department of Agriculture", "Department of Agriculture"],
    "USTR": ["USTR", "Trade Representative"],
    "DOC":  ["Department of Commerce", "U.S. Department of Commerce", "Commerce Department"],
    "DOD":  ["Department of Defense", "Pentagon", "DoD"],
    "DOE":  ["Department of Energy", "U.S. Department of Energy"],
    "DOI":  ["Department of the Interior", "U.S. Department of the Interior"],
    "DOJ":  ["Department of Justice", "U.S. Department of Justice"],
    "DOL":  ["Department of Labor", "U.S. Department of Labor"],
    "DOS":  ["Department of State", "U.S. Department of State", "State Department"],
    "DOT":  ["Department of Transportation", "U.S. Department of Transportation"],
    "ED":   ["Department of Education", "U.S. Department of Education"],
    "HHS":  ["Department of Health and Human Services", "HHS", "Health & Human Services", "Health and Human Services"],
    "HUD":  ["Department of Housing and Urban Development", "HUD"],
    "TREAS":["Department of the Treasury", "Treasury Department", "Treasury"],
    "EPA":  ["EPA", "Environmental Protection Agency"],
    "VA":   ["Department of Veterans Affairs", "Veterans Affairs"],
    "DHS":  ["Department of Homeland Security", "Homeland Security"],
    "FCC":  ["FCC", "Federal Communications Commission"],
    "FTC":  ["FTC", "Federal Trade Commission"],
    "SEC":  ["SEC", "Securities and Exchange"],
    "CFPB": ["CFPB", "Consumer Financial Protection Bureau"],
    "FDA":  ["FDA", "Food and Drug Administration"],
    "NIH":  ["NIH", "National Institutes of Health"],
    "CMS":  ["CMS", "Centers for Medicare"],
    "WH":   ["White House", "Executive Office of the President", "Office of the Vice President", "OMB", "National Security Council", "NEC"],
}


def detect_role(s: str) -> str:
    for label, rx in ROLE_PATTERNS:
        if rx.search(s):
            return label
    return "OTHER"


def detect_office(s: str) -> tuple[str, str | None]:
    """Return (office_type, office_name | None)."""
    # House/Senate committee?
    m = SENATE_COMMITTEE_RE.search(s)
    if m:
        return "SENATE_COMMITTEE", f"Senate {m.group(1).strip()} Committee"
    m = HOUSE_COMMITTEE_RE.search(s)
    if m:
        return "HOUSE_COMMITTEE", f"House {m.group(1).strip()} Committee"
    m = JOINT_COMMITTEE_RE.search(s)
    if m:
        return "JOINT_COMMITTEE", f"Joint {m.group(1).strip()} Committee"

    # Former Member of Congress?
    if re.search(r"\bformer\s+(member|representative|senator|congressman|congresswoman|u\.?s\.?\s+(rep|sen))\b", s, re.I):
        return "FORMER_MEMBER", None

    # White House / agency
    for agency, kw_list in AGENCY_KEYWORDS.items():
        for kw in kw_list:
            if re.search(rf"\b{re.escape(kw)}\b", s, re.I):
                return ("WH" if agency == "WH" else "AGENCY"), agency

    # Member office?
    m = MEMBER_RE.search(s)
    if m:
        surname = m.group(1).split()[-1]
        if re.search(r"\bRep\.?\b|\bRepresentative\b|\bCongress(man|woman)\b", s, re.I):
            return "HOUSE_MEMBER", surname
        if re.search(r"\bSen\.?\b|\bSenator\b", s, re.I):
            return "SENATE_MEMBER", surname

    m = PAREN_MEMBER_RE.search(s)
    if m:
        return "MEMBER_OFFICE", m.group(1).strip()

    return "OTHER", None


def parse_corpus(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    sen = con.execute(
        """
        SELECT 'SENATE' AS chamber, CAST(filing_uuid AS VARCHAR) AS filing_uuid,
               registrant_name, client_name,
               lobbyist_first, lobbyist_last, covered_position AS raw_text
        FROM sen_lobbyists
        WHERE covered_position IS NOT NULL
          AND length(covered_position) > 3
          AND covered_position NOT IN ('N/A', 'NA', 'See prior filing', 'see prior filing')
        """
    ).df()
    hs = con.execute(
        """
        SELECT 'HOUSE' AS chamber, CAST(filing_id AS VARCHAR) AS filing_uuid,
               NULL AS registrant_name, NULL AS client_name,
               first_name AS lobbyist_first, last_name AS lobbyist_last,
               covered_position AS raw_text
        FROM house_lobbyists
        WHERE covered_position IS NOT NULL
          AND length(covered_position) > 3
        """
    ).df()
    df = pd.concat([sen, hs], ignore_index=True)
    print(f"Parsing {len(df):,} lobbyist appearances...", file=sys.stderr)

    df["prior_role"] = df["raw_text"].astype(str).map(detect_role)
    offices = df["raw_text"].astype(str).map(detect_office)
    df["source_office_type"] = [o[0] for o in offices]
    df["source_office"] = [o[1] for o in offices]
    return df


def emit_summary(df: pd.DataFrame, out_md: str) -> None:
    out = Path(out_md)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Revolving-door extractor — top flows", ""]
    lines += [f"**Rows parsed:** {len(df):,}", ""]
    lines += ["## Role distribution", "", "| Role | Count |", "|---|---:|"]
    for role, n in df["prior_role"].value_counts().head(20).items():
        lines.append(f"| {role} | {n:,} |")
    lines += ["", "## Source-office types", "", "| Type | Count |", "|---|---:|"]
    for typ, n in df["source_office_type"].value_counts().head(20).items():
        lines.append(f"| {typ} | {n:,} |")
    lines += ["", "## Top Senate committees", "", "| Committee | Lobbyist appearances |", "|---|---:|"]
    sc = df[df["source_office_type"] == "SENATE_COMMITTEE"]["source_office"].value_counts().head(20)
    for k, v in sc.items():
        lines.append(f"| {k} | {v:,} |")
    lines += ["", "## Top House committees", "", "| Committee | Lobbyist appearances |", "|---|---:|"]
    hc = df[df["source_office_type"] == "HOUSE_COMMITTEE"]["source_office"].value_counts().head(20)
    for k, v in hc.items():
        lines.append(f"| {k} | {v:,} |")
    lines += ["", "## Top Senate member offices (by surname)", "", "| Member | Lobbyist appearances |", "|---|---:|"]
    sm = df[df["source_office_type"] == "SENATE_MEMBER"]["source_office"].value_counts().head(20)
    for k, v in sm.items():
        lines.append(f"| {k} | {v:,} |")
    lines += ["", "## Top House member offices (by surname)", "", "| Member | Lobbyist appearances |", "|---|---:|"]
    hm = df[df["source_office_type"] == "HOUSE_MEMBER"]["source_office"].value_counts().head(20)
    for k, v in hm.items():
        lines.append(f"| {k} | {v:,} |")
    lines += ["", "## Top agencies", "", "| Agency | Lobbyist appearances |", "|---|---:|"]
    ag = df[df["source_office_type"] == "AGENCY"]["source_office"].value_counts().head(20)
    for k, v in ag.items():
        lines.append(f"| {k} | {v:,} |")
    out.write_text("\n".join(lines))
    print(f"wrote {out}", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/parquet/revolving_door.parquet")
    ap.add_argument("--md")
    args = ap.parse_args()

    con = connect()
    df = parse_corpus(con)
    df.to_parquet(args.out, index=False)
    print(f"wrote {args.out} ({len(df):,} rows)", file=sys.stderr)
    if args.md:
        emit_summary(df, args.md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
