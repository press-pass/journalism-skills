"""Index Senate LDA filings and contributions into Parquet, one year at a time.

Outputs (year-partitioned where appropriate):
  /parquet/senate/filings/year=YYYY/data.parquet
  /parquet/senate/activities/year=YYYY/data.parquet
  /parquet/senate/lobbyists/year=YYYY/data.parquet
  /parquet/senate/gov_entities/year=YYYY/data.parquet
  /parquet/senate/foreign_entities/year=YYYY/data.parquet
  /parquet/senate/contrib_reports/year=YYYY/data.parquet
  /parquet/senate/contrib_items/year=YYYY/data.parquet
  /parquet/senate/constants/*.parquet
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import duckdb

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
PARQUET_DIR = Path(os.environ.get("PARQUET_DIR", "/parquet"))


def process_filings_year(con: duckdb.DuckDBPyConnection, year: int, src_json: Path, out_root: Path) -> None:
    con.execute("DROP TABLE IF EXISTS raw_filings")
    con.execute(
        f"""
        CREATE TABLE raw_filings AS
        SELECT * FROM read_json_auto('{src_json}', maximum_object_size=2000000000, format='array', sample_size=-1, ignore_errors=true)
        """
    )

    # Filings
    target = out_root / f"filings/year={year}"
    target.mkdir(parents=True, exist_ok=True)
    con.execute(
        f"""
        COPY (
        SELECT
            filing_uuid,
            filing_type,
            filing_type_display,
            filing_year::INTEGER AS filing_year,
            filing_period,
            filing_period_display,
            CAST(dt_posted AS TIMESTAMP) AS dt_posted,
            income::DOUBLE AS income,
            expenses::DOUBLE AS expenses,
            expenses_method,
            registrant.id AS registrant_id,
            registrant.name AS registrant_name,
            registrant.country_display AS registrant_country,
            registrant.contact_name AS registrant_contact,
            registrant.house_registrant_id AS registrant_house_id,
            client.id AS client_id,
            client.name AS client_name,
            client.general_description AS client_description,
            client.client_government_entity AS client_is_gov,
            client.client_self_select AS client_self_select,
            client.state_display AS client_state,
            client.country_display AS client_country,
            url,
            filing_document_url
        FROM raw_filings
        ) TO '{target}/data.parquet' (FORMAT PARQUET)
        """
    )
    n_filings = con.execute("SELECT COUNT(*) FROM raw_filings").fetchone()[0]

    # Activities (flat)
    con.execute("DROP TABLE IF EXISTS sen_act")
    con.execute(
        """
        CREATE TABLE sen_act AS
        SELECT
            r.filing_uuid,
            r.filing_year::INTEGER AS filing_year,
            r.filing_period,
            r.registrant.id AS registrant_id,
            r.registrant.name AS registrant_name,
            r.client.id AS client_id,
            r.client.name AS client_name,
            r.income::DOUBLE AS income,
            r.expenses::DOUBLE AS expenses,
            act.general_issue_code AS issue_code,
            act.general_issue_code_display AS issue_display,
            act.description AS act_description,
            act.foreign_entity_issues AS foreign_entity_issues,
            act.lobbyists AS lobbyists,
            act.government_entities AS government_entities
        FROM raw_filings r,
             UNNEST(r.lobbying_activities) t(act)
        """
    )
    target = out_root / f"activities/year={year}"
    target.mkdir(parents=True, exist_ok=True)
    con.execute(
        f"""
        COPY (
            SELECT filing_uuid, filing_year, filing_period, registrant_id, registrant_name,
                   client_id, client_name, income, expenses,
                   issue_code, issue_display, act_description, foreign_entity_issues
            FROM sen_act
        ) TO '{target}/data.parquet' (FORMAT PARQUET)
        """
    )
    n_acts = con.execute("SELECT COUNT(*) FROM sen_act").fetchone()[0]

    # Lobbyists
    target = out_root / f"lobbyists/year={year}"
    target.mkdir(parents=True, exist_ok=True)
    con.execute(
        f"""
        COPY (
            SELECT
                a.filing_uuid,
                a.filing_year,
                a.registrant_id,
                a.registrant_name,
                a.client_id,
                a.client_name,
                a.issue_code,
                lb.lobbyist.id AS lobbyist_id,
                lb.lobbyist.prefix_display AS lobbyist_prefix,
                lb.lobbyist.first_name AS lobbyist_first,
                lb.lobbyist.middle_name AS lobbyist_middle,
                lb.lobbyist.last_name AS lobbyist_last,
                lb.lobbyist.suffix_display AS lobbyist_suffix,
                lb.lobbyist.nickname AS lobbyist_nickname,
                lb.covered_position AS covered_position,
                lb.new AS is_new_lobbyist
            FROM sen_act a, UNNEST(a.lobbyists) t(lb)
        ) TO '{target}/data.parquet' (FORMAT PARQUET)
        """
    )
    n_lob = con.execute(
        f"SELECT COUNT(*) FROM read_parquet('{target}/data.parquet')"
    ).fetchone()[0]

    # Gov entities
    target = out_root / f"gov_entities/year={year}"
    target.mkdir(parents=True, exist_ok=True)
    con.execute(
        f"""
        COPY (
            SELECT
                a.filing_uuid, a.filing_year, a.registrant_id, a.registrant_name,
                a.client_id, a.client_name, a.issue_code,
                ge.id AS gov_entity_id,
                ge.name AS gov_entity_name
            FROM sen_act a, UNNEST(a.government_entities) t(ge)
        ) TO '{target}/data.parquet' (FORMAT PARQUET)
        """
    )
    n_ge = con.execute(
        f"SELECT COUNT(*) FROM read_parquet('{target}/data.parquet')"
    ).fetchone()[0]

    # Foreign entities
    target = out_root / f"foreign_entities/year={year}"
    target.mkdir(parents=True, exist_ok=True)
    con.execute(
        f"""
        COPY (
            SELECT
                r.filing_uuid,
                r.filing_year::INTEGER AS filing_year,
                r.registrant.id AS registrant_id,
                r.registrant.name AS registrant_name,
                r.client.id AS client_id,
                r.client.name AS client_name,
                fe.name AS foreign_entity_name,
                fe.country AS foreign_entity_country_code,
                fe.country_display AS foreign_entity_country,
                fe.contribution::DOUBLE AS foreign_contribution,
                fe.ownership_percentage::DOUBLE AS foreign_ownership_pct
            FROM raw_filings r,
                 UNNEST(r.foreign_entities) t(fe)
        ) TO '{target}/data.parquet' (FORMAT PARQUET)
        """
    )
    n_fe = con.execute(
        f"SELECT COUNT(*) FROM read_parquet('{target}/data.parquet')"
    ).fetchone()[0]

    print(
        f"  {year} filings={n_filings:,} activities={n_acts:,} lobbyists={n_lob:,} gov_entities={n_ge:,} foreign_entities={n_fe:,}"
    )

    # Cleanup big tables
    con.execute("DROP TABLE raw_filings")
    con.execute("DROP TABLE sen_act")


def process_contribs_year(con: duckdb.DuckDBPyConnection, year: int, src_json: Path, out_root: Path) -> None:
    con.execute("DROP TABLE IF EXISTS raw_contribs")
    con.execute(
        f"""
        CREATE TABLE raw_contribs AS
        SELECT * FROM read_json_auto('{src_json}', maximum_object_size=2000000000, format='array', sample_size=-1, ignore_errors=true)
        """
    )

    target = out_root / f"contrib_reports/year={year}"
    target.mkdir(parents=True, exist_ok=True)
    con.execute(
        f"""
        COPY (
            SELECT
                filing_uuid,
                filing_type,
                filing_year::INTEGER AS filing_year,
                filing_period,
                CAST(dt_posted AS TIMESTAMP) AS dt_posted,
                filer_type,
                filer_type_display,
                no_contributions::BOOLEAN AS no_contributions,
                registrant.id AS registrant_id,
                registrant.name AS registrant_name,
                lobbyist.id AS lobbyist_id,
                lobbyist.first_name AS lobbyist_first,
                lobbyist.last_name AS lobbyist_last,
                url
            FROM raw_contribs
        ) TO '{target}/data.parquet' (FORMAT PARQUET)
        """
    )
    n_rep = con.execute("SELECT COUNT(*) FROM raw_contribs").fetchone()[0]

    target = out_root / f"contrib_items/year={year}"
    target.mkdir(parents=True, exist_ok=True)
    con.execute(
        f"""
        COPY (
            SELECT
                r.filing_uuid,
                r.filing_year::INTEGER AS filing_year,
                r.registrant.id AS registrant_id,
                r.registrant.name AS registrant_name,
                r.lobbyist.id AS lobbyist_id,
                r.lobbyist.first_name AS lobbyist_first,
                r.lobbyist.last_name AS lobbyist_last,
                it.contribution_type AS contribution_type,
                it.contribution_type_display AS contribution_type_display,
                it.contributor_name AS contributor_name,
                it.payee_name AS payee_name,
                it.honoree_name AS honoree_name,
                it.amount::DOUBLE AS amount,
                CAST(it.date AS DATE) AS contribution_date
            FROM raw_contribs r,
                 UNNEST(r.contribution_items) t(it)
        ) TO '{target}/data.parquet' (FORMAT PARQUET)
        """
    )
    n_items = con.execute(
        f"SELECT COUNT(*) FROM read_parquet('{target}/data.parquet')"
    ).fetchone()[0]

    print(f"  {year} contrib_reports={n_rep:,} contrib_items={n_items:,}")
    con.execute("DROP TABLE raw_contribs")


def main() -> None:
    src = DATA_DIR / "senate"
    out_root = PARQUET_DIR / "senate"
    out_root.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    con.execute("PRAGMA threads=6")
    con.execute("SET memory_limit='32GB'")
    con.execute("SET temp_directory='/parquet/.duckdb_tmp'")
    con.execute("SET preserve_insertion_order=false")

    filing_files = sorted(src.glob("*/filings/filings_*.json"))
    contrib_files = sorted(src.glob("*/contributions/contributions_*.json"))

    print("=== Filings ===")
    for p in filing_files:
        m = re.search(r"filings_(\d{4})\.json", p.name)
        if m:
            process_filings_year(con, int(m.group(1)), p, out_root)

    print("=== Contributions ===")
    for p in contrib_files:
        m = re.search(r"contributions_(\d{4})\.json", p.name)
        if m:
            process_contribs_year(con, int(m.group(1)), p, out_root)

    # Constants
    print("=== Constants ===")
    constants_dir = src / "constants"
    if constants_dir.exists():
        out_const = out_root / "constants"
        out_const.mkdir(parents=True, exist_ok=True)
        for f in constants_dir.glob("*.json"):
            try:
                con.execute(
                    f"COPY (SELECT * FROM read_json_auto('{f}', format='array')) TO '{out_const}/{f.stem}.parquet' (FORMAT PARQUET)"
                )
                n = con.execute(
                    f"SELECT COUNT(*) FROM read_parquet('{out_const}/{f.stem}.parquet')"
                ).fetchone()[0]
                print(f"  {f.name}: {n}")
            except Exception as e:
                print(f"  skipped {f.name}: {e}")


if __name__ == "__main__":
    main()
