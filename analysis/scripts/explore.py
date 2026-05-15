"""Quick exploration queries used to find chart angles. Run with --query NAME."""
from __future__ import annotations
import argparse, sys, json
import polars as pl


def query_press_calendar():
    p = pl.read_parquet("/parquet/press.parquet")
    p = p.with_columns(pl.col("date").str.slice(0, 7).alias("ym"))
    return p.group_by("ym").len().sort("ym")


def query_ai_quarterly():
    a = pl.read_parquet("/parquet/senate_activities.parquet")
    ai_q = a.filter(
        pl.col("description").str.to_lowercase().str.contains("artificial intelligence")
    ).group_by(["filing_year", "filing_period"]).agg(pl.len().alias("ai_n"), pl.col("client_name").n_unique().alias("clients"))
    total_q = a.group_by(["filing_year", "filing_period"]).len().rename({"len": "total"})
    return ai_q.join(total_q, on=["filing_year", "filing_period"]).sort(["filing_year", "filing_period"])


def query_revolving_dedup():
    lo = pl.read_parquet("/parquet/senate_lobbyists.parquet")
    lo = lo.filter(pl.col("covered_position").str.strip_chars() != "")
    lo = lo.filter(~pl.col("covered_position").str.to_lowercase().is_in(["see prior filing", "n/a"]))
    # unique lobbyists (id) ever recorded with covered_position
    uniq = lo.unique(subset=["lobbyist_id"]).filter(pl.col("lobbyist_id").is_not_null())
    return uniq


def query_top_clients():
    a = pl.read_parquet("/parquet/senate_activities.parquet")
    return a.filter(pl.col("filing_year") == 2025).group_by("client_name").agg(
        pl.col("income").sum().alias("sum_income_filing"),
        pl.len().alias("n_activities"),
    ).sort("n_activities", descending=True).head(50)


def query_party_release_rate():
    p = pl.read_parquet("/parquet/press.parquet")
    p = p.filter(pl.col("date").str.starts_with("2025"))
    members = p.group_by(["bioguide_id", "member_name", "party", "state", "chamber"]).len()
    return members.sort("len", descending=True)


def query_foreign_top():
    f = pl.read_parquet("/parquet/senate_filings.parquet")
    fe = f.filter(pl.col("n_foreign_entities") > 0)
    # explode foreign_entity_names by pipe
    fe = fe.with_columns(pl.col("foreign_entity_names").str.split("|").alias("fe_list"))
    out = fe.explode("fe_list").filter(pl.col("fe_list").str.strip_chars() != "")
    return out.group_by("fe_list").agg(
        pl.len().alias("n_filings"),
        pl.col("registrant_name").n_unique().alias("n_registrants"),
        pl.col("filing_year").min().alias("first_year"),
    ).sort("n_filings", descending=True).head(30)


def query_state_loc_nation():
    f = pl.read_parquet("/parquet/senate_filings.parquet")
    return f.filter(pl.col("client_name").str.contains("STATE OF LOC NATION")).select(
        ["filing_uuid", "filing_year", "filing_period", "registrant_name", "client_name", "income", "expenses", "filing_document_url"]
    )


def query_ld203_top_payee():
    ci = pl.read_parquet("/parquet/senate_contrib_items.parquet")
    return ci.filter(pl.col("amount").is_not_null()).group_by("payee").agg(
        pl.col("amount").sum().alias("total"),
        pl.len().alias("n_items"),
    ).sort("total", descending=True).head(25)


QUERIES = {
    "press_calendar": query_press_calendar,
    "ai_quarterly": query_ai_quarterly,
    "revolving_dedup": query_revolving_dedup,
    "top_clients": query_top_clients,
    "party_rate": query_party_release_rate,
    "foreign_top": query_foreign_top,
    "state_loc": query_state_loc_nation,
    "ld203_top_payee": query_ld203_top_payee,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True, choices=list(QUERIES))
    ap.add_argument("--limit", type=int, default=200)
    args = ap.parse_args()
    out = QUERIES[args.query]()
    if isinstance(out, pl.DataFrame):
        pl.Config.set_tbl_rows(args.limit)
        pl.Config.set_tbl_cols(30)
        pl.Config.set_fmt_str_lengths(120)
        print(out)
    else:
        print(out)


if __name__ == "__main__":
    main()
