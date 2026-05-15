"""Cross-corpus 'Say vs Pay' correlator.

For a user-supplied keyword (or list of keywords) compute, per quarter:

  - press_n: count of press releases mentioning ANY keyword (title or body)
  - lobby_n_senate: count of Senate LDA lobbying_activities whose description
    mentions ANY keyword (case-insensitive)
  - lobby_n_house: same for House XML descriptions

Outputs:
  --out_parquet: quarter-grain table
  --out_members_parquet: member-grain table with press_n + (optional) say-vs-pay rank
  --out_summary_md: markdown one-pager with the headline correlation
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path
import polars as pl
from scipy.stats import pearsonr  # type: ignore


def keyword_filter_press(p: pl.DataFrame, keywords: list[str]) -> pl.Expr:
    e = pl.lit(False)
    for kw in keywords:
        e = e | pl.col("text_lc").str.contains(kw.lower(), literal=True) | pl.col("title_lc").str.contains(kw.lower(), literal=True)
    return e


def keyword_filter_desc(df: pl.DataFrame, keywords: list[str]) -> pl.Expr:
    e = pl.lit(False)
    for kw in keywords:
        e = e | pl.col("description").str.to_lowercase().str.contains(kw.lower(), literal=True)
    return e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keywords", nargs="+", required=True,
                    help="One or more keywords. A record matches if it contains ANY (substring, case-insensitive).")
    ap.add_argument("--press_parquet", required=True)
    ap.add_argument("--senate_activities_parquet", required=True)
    ap.add_argument("--house_activities_parquet", required=True)
    ap.add_argument("--out_parquet", required=True)
    ap.add_argument("--out_members_parquet", default=None)
    ap.add_argument("--out_summary_md", default=None)
    args = ap.parse_args()

    print(f"keywords: {args.keywords}", file=sys.stderr)

    p = pl.read_parquet(args.press_parquet)
    p = p.with_columns(
        pl.col("date").str.slice(0, 4).cast(pl.Int64, strict=False).alias("year"),
        pl.col("date").str.slice(5, 2).cast(pl.Int64, strict=False).alias("month"),
    )
    p = p.with_columns(((pl.col("month") - 1) // 3 + 1).alias("q"))

    sa = pl.read_parquet(args.senate_activities_parquet)
    ha = pl.read_parquet(args.house_activities_parquet)
    period_order = {"first_quarter": 1, "second_quarter": 2, "third_quarter": 3, "fourth_quarter": 4}
    sa = sa.with_columns(pl.col("filing_period").replace_strict(period_order).alias("q")).rename({"filing_year": "year"})

    house_q_order = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}
    ha = ha.with_columns(pl.col("filing_quarter").replace_strict(house_q_order, default=None).alias("q")).rename({"filing_year": "year"})

    press_n = (
        p.filter(keyword_filter_press(p, args.keywords))
         .group_by(["year", "q"]).len().rename({"len": "press_n"})
    )
    lobby_senate_n = (
        sa.filter(keyword_filter_desc(sa, args.keywords))
          .group_by(["year", "q"]).len().rename({"len": "lobby_n_senate"})
    )
    lobby_house_n = (
        ha.filter(keyword_filter_desc(ha, args.keywords))
          .group_by(["year", "q"]).len().rename({"len": "lobby_n_house"})
    )

    out = press_n.join(lobby_senate_n, on=["year", "q"], how="full", coalesce=True)
    out = out.join(lobby_house_n, on=["year", "q"], how="full", coalesce=True)
    out = out.fill_null(0).sort(["year", "q"])
    out = out.with_columns(
        (pl.col("lobby_n_senate") + pl.col("lobby_n_house")).alias("lobby_n_total"),
        (pl.col("year").cast(pl.Utf8) + " Q" + pl.col("q").cast(pl.Utf8)).alias("label"),
    )

    out.write_parquet(args.out_parquet, compression="zstd")
    print(out, file=sys.stderr)

    # correlation
    if out.height >= 3:
        r, p_value = pearsonr(out["press_n"].to_list(), out["lobby_n_total"].to_list())
    else:
        r, p_value = float("nan"), float("nan")

    if args.out_members_parquet:
        per_member = (
            p.filter(keyword_filter_press(p, args.keywords))
             .group_by(["bioguide_id", "member_name", "party", "state", "chamber"]).len()
             .rename({"len": "press_n"})
             .sort("press_n", descending=True)
        )
        per_member.write_parquet(args.out_members_parquet, compression="zstd")

    if args.out_summary_md:
        lines = [
            f"# Say-vs-Pay: {', '.join(args.keywords)}",
            f"",
            f"- Quarterly Pearson r(press, lobbying) = **{r:.3f}** (p = {p_value:.3g})",
            f"- Total press releases mentioning any keyword: **{int(out['press_n'].sum())}**",
            f"- Total Senate activities matching: **{int(out['lobby_n_senate'].sum())}**",
            f"- Total House activities matching: **{int(out['lobby_n_house'].sum())}**",
            "",
            "## Quarterly counts",
            "| Quarter | Press releases | Senate activities | House activities |",
            "|---|---:|---:|---:|",
        ]
        for r2 in out.iter_rows(named=True):
            lines.append(f"| {r2['label']} | {r2['press_n']} | {r2['lobby_n_senate']} | {r2['lobby_n_house']} |")
        Path(args.out_summary_md).write_text("\n".join(lines) + "\n")
        print(f"wrote {args.out_summary_md}", file=sys.stderr)


if __name__ == "__main__":
    main()
