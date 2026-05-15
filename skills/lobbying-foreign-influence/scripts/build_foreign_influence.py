#!/usr/bin/env python3
"""Build foreign_lobbying table joining foreign-client + foreign-entity disclosures."""
from __future__ import annotations
import argparse
import json
import re
import time
from pathlib import Path
import duckdb


def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


# Curated demonym -> country mapping
DEMONYM = {
    "Chinese": "China", "Korean": "Republic of Korea", "Taiwanese": "Taiwan",
    "Japanese": "Japan", "Saudi": "Saudi Arabia", "Emirati": "United Arab Emirates",
    "Qatari": "Qatar", "Russian": "Russia", "Ukrainian": "Ukraine",
    "Indian": "India", "Pakistani": "Pakistan", "Israeli": "Israel",
    "Iranian": "Iran", "Turkish": "Turkey", "Egyptian": "Egypt",
    "German": "Germany", "French": "France", "Spanish": "Spain", "Italian": "Italy",
    "British": "United Kingdom", "Irish": "Ireland", "Dutch": "Netherlands",
    "Swiss": "Switzerland", "Mexican": "Mexico", "Canadian": "Canada",
    "Brazilian": "Brazil", "Argentine": "Argentina", "Australian": "Australia",
    "Singaporean": "Singapore", "Indonesian": "Indonesia", "Vietnamese": "Vietnam",
    "Thai": "Thailand", "Filipino": "Philippines", "Hungarian": "Hungary",
    "Polish": "Poland",
}


def build_country_patterns(con):
    rows = con.execute("SELECT name FROM countries_lookup WHERE name IS NOT NULL").fetchall()
    pats = []
    for (name,) in rows:
        if len(name) < 4:  # skip "US", "UK"
            continue
        # word-boundary match
        pats.append((re.compile(r"\b" + re.escape(name) + r"\b", re.IGNORECASE), name))
    for demo, country in DEMONYM.items():
        pats.append((re.compile(r"\b" + re.escape(demo) + r"\b", re.IGNORECASE), country))
    return pats


def detect_countries(text: str, patterns) -> str:
    if not text:
        return None
    hits = set()
    for pat, country in patterns:
        if pat.search(text):
            hits.add(country)
    return ",".join(sorted(hits)) if hits else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    args = ap.parse_args()
    con = duckdb.connect(args.db)
    patterns = build_country_patterns(con)
    log(f"Loaded {len(patterns)} country/demonym patterns")

    log("Recreating foreign_lobbying")
    con.execute("""
        DROP TABLE IF EXISTS foreign_lobbying;
        CREATE TABLE foreign_lobbying (
            source VARCHAR,
            filing_uuid VARCHAR,
            house_file VARCHAR,
            filing_year INTEGER,
            filing_period VARCHAR,
            registrant_name VARCHAR,
            client_name VARCHAR,
            client_country VARCHAR,
            foreign_entity_text VARCHAR,
            detected_countries VARCHAR,
            reported_income DOUBLE
        );
    """)

    log("Senate side: client.country != US OR activity.foreign_entity_issues IS NOT NULL")
    rows = con.execute("""
        SELECT f.filing_uuid, f.filing_year, f.filing_period,
               f.registrant_name, f.client_name, f.client_country,
               STRING_AGG(a.foreign_entity_issues, ' | ') AS foreign_text,
               f.income
        FROM senate_filings f
        LEFT JOIN senate_activities a USING (filing_uuid)
        WHERE (f.client_country IS NOT NULL AND upper(f.client_country) NOT IN ('US','UNITED STATES OF AMERICA'))
           OR a.foreign_entity_issues IS NOT NULL
        GROUP BY f.filing_uuid, f.filing_year, f.filing_period,
                 f.registrant_name, f.client_name, f.client_country, f.income
    """).fetchall()
    log(f"  {len(rows):,} candidate Senate filings")
    batch = []
    for fuid, yr, per, reg, cli, cc, ft, income in rows:
        countries = detect_countries(ft or "", patterns) or (cc if cc and cc.upper() not in ("US", "UNITED STATES OF AMERICA") else None)
        if not countries:
            continue
        batch.append(("senate", fuid, None, yr, per, reg, cli, cc, ft, countries, income))
    if batch:
        con.executemany("INSERT INTO foreign_lobbying VALUES (?,?,?,?,?,?,?,?,?,?,?)", batch)
    log(f"  inserted {len(batch):,} Senate rows")

    log("House side")
    rows = con.execute("""
        SELECT h.house_file, h.filing_year, h.filing_period,
               h.organization_name, h.client_name, h.client_country,
               STRING_AGG(a.foreign_entity_issues, ' | ') AS foreign_text,
               h.income
        FROM house_filings h
        LEFT JOIN house_activities a USING (house_file)
        WHERE (h.client_country IS NOT NULL AND upper(h.client_country) NOT IN ('USA','UNITED STATES'))
           OR a.foreign_entity_issues IS NOT NULL
        GROUP BY h.house_file, h.filing_year, h.filing_period,
                 h.organization_name, h.client_name, h.client_country, h.income
    """).fetchall()
    log(f"  {len(rows):,} candidate House filings")
    batch = []
    for hf, yr, per, reg, cli, cc, ft, income in rows:
        countries = detect_countries(ft or "", patterns) or (cc if cc and cc.upper() not in ("USA", "UNITED STATES") else None)
        if not countries:
            continue
        batch.append(("house", None, hf, yr, per, reg, cli, cc, ft, countries, income))
    if batch:
        con.executemany("INSERT INTO foreign_lobbying VALUES (?,?,?,?,?,?,?,?,?,?,?)", batch)
    log(f"  inserted {len(batch):,} House rows")

    con.execute("""
        CREATE INDEX IF NOT EXISTS idx_fl_countries ON foreign_lobbying(detected_countries);
        CREATE INDEX IF NOT EXISTS idx_fl_year ON foreign_lobbying(filing_year);
        ANALYZE;
    """)
    log("Done.")


if __name__ == "__main__":
    main()
