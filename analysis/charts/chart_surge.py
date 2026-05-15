"""Chart 2: 'The Surge' — total disclosed lobbying spend by quarter,
broken out by the top issue codes.

Data: sen_filings.income (lobby firm) + sen_filings.expenses (self-filer),
COALESCEd. De-duplicated to one row per (registrant, client, year, period)
so amendment filings don't double-count.

Output: PNG + SVG to analysis/charts/output/
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from views import connect  # type: ignore

OUT_DIR = Path(__file__).resolve().parent / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)


PERIOD_TO_QUARTER = {
    "first_quarter": 1, "second_quarter": 2,
    "third_quarter": 3, "fourth_quarter": 4,
}


def fetch() -> tuple[pd.DataFrame, pd.DataFrame]:
    con = connect()

    # 1) Quarterly total spend (deduplicated by (registrant_id, client_id,
    # filing_year, filing_period) — pick the LATEST amendment per group).
    quarterly = con.execute(
        """
        WITH dedup AS (
            SELECT
                filing_year,
                filing_period,
                registrant_id,
                client_id,
                FIRST_VALUE(COALESCE(income, expenses, 0))
                    OVER (PARTITION BY registrant_id, client_id, filing_year, filing_period
                          ORDER BY dt_posted DESC) AS spend,
                FIRST_VALUE(filing_uuid)
                    OVER (PARTITION BY registrant_id, client_id, filing_year, filing_period
                          ORDER BY dt_posted DESC) AS canonical_uuid,
                filing_uuid
            FROM sen_filings
            WHERE filing_type LIKE 'Q%'
        )
        SELECT
            filing_year,
            filing_period,
            SUM(spend) AS total_spend
        FROM dedup
        WHERE filing_uuid = canonical_uuid
        GROUP BY 1, 2
        ORDER BY 1, 2
        """
    ).df()
    quarterly["quarter"] = quarterly["filing_period"].map(PERIOD_TO_QUARTER)
    quarterly = quarterly.dropna(subset=["quarter"])
    quarterly["quarter"] = quarterly["quarter"].astype(int)
    quarterly["label"] = (
        quarterly["filing_year"].astype(int).astype(str)
        + " Q"
        + quarterly["quarter"].astype(int).astype(str)
    )
    quarterly = quarterly.sort_values(["filing_year", "quarter"]).reset_index(drop=True)

    # 2) Issue mix by year — top 8 issues plus "Other"
    issue_mix = con.execute(
        """
        WITH dedup AS (
            SELECT
                f.filing_year,
                f.filing_period,
                f.registrant_id,
                f.client_id,
                FIRST_VALUE(f.filing_uuid)
                    OVER (PARTITION BY f.registrant_id, f.client_id, f.filing_year, f.filing_period
                          ORDER BY f.dt_posted DESC) AS canonical_uuid,
                f.filing_uuid,
                COALESCE(f.income, f.expenses, 0) AS spend
            FROM sen_filings f
            WHERE f.filing_type LIKE 'Q%'
        ),
        canon AS (
            SELECT filing_year, filing_period, filing_uuid, spend
            FROM dedup WHERE filing_uuid = canonical_uuid
        ),
        issue_per_filing AS (
            SELECT DISTINCT c.filing_year, c.filing_period, c.filing_uuid, a.issue_code,
                   c.spend
            FROM canon c
            JOIN sen_activities a USING (filing_uuid)
            WHERE a.issue_code IS NOT NULL
        ),
        per_filing_spend AS (
            -- Split spend evenly across all issues listed on that filing
            SELECT
                filing_year,
                filing_period,
                issue_code,
                spend / NULLIF(COUNT(*) OVER (PARTITION BY filing_uuid), 0) AS allocated
            FROM issue_per_filing
        )
        SELECT
            filing_year,
            filing_period,
            issue_code,
            SUM(allocated) AS total_spend
        FROM per_filing_spend
        GROUP BY 1, 2, 3
        """
    ).df()
    issue_mix["quarter"] = issue_mix["filing_period"].map(PERIOD_TO_QUARTER)
    issue_mix = issue_mix.dropna(subset=["quarter"])
    issue_mix["quarter"] = issue_mix["quarter"].astype(int)

    # Resolve issue_code to display
    codes = con.execute("SELECT value AS issue_code, name AS issue_display FROM issue_codes").df()
    issue_mix = issue_mix.merge(codes, on="issue_code", how="left")

    return quarterly, issue_mix


# Pretty issue names + colors
ISSUE_NAMES = {
    "HCR": "Health",
    "TAX": "Taxation",
    "BUD": "Budget / appropriations",
    "DEF": "Defense",
    "TRD": "Trade",
    "ENG": "Energy / nuclear",
    "FIN": "Finance",
    "MMM": "Medicare / Medicaid",
    "TRA": "Transportation",
    "ENV": "Environment",
    "BAN": "Banking",
    "TEC": "Computer / Internet",
    "TEL": "Telecom",
    "GOV": "Government issues",
    "EDU": "Education",
    "LBR": "Labor / antitrust",
    "AGR": "Agriculture",
    "IMM": "Immigration",
    "MAN": "Manufacturing",
    "INS": "Insurance",
    "RET": "Retirement",
    "RES": "Natural resources",
    "PHA": "Pharma / health products",
    "SCI": "Science / technology",
    "ROD": "Roads / highways",
    "HOM": "Homeland security",
    "TOR": "Torts",
    "BNK": "Banking",
}


def render(quarterly: pd.DataFrame, issue_mix: pd.DataFrame) -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titleweight": "bold",
    })

    fig = plt.figure(figsize=(15, 10))

    # ---- TOP: total quarterly spend bar chart with growth annotations
    ax_top = fig.add_axes([0.07, 0.55, 0.88, 0.32])
    bars_x = np.arange(len(quarterly))
    colors = []
    for _, row in quarterly.iterrows():
        c = "#4d80b8" if int(row["filing_year"]) < 2025 else "#205594"
        if int(row["filing_year"]) == 2026:
            c = "#a3c7e8"
        colors.append(c)
    ax_top.bar(bars_x, quarterly["total_spend"] / 1e6, color=colors, edgecolor="white", linewidth=0.6)
    ax_top.set_xticks(bars_x)
    ax_top.set_xticklabels(quarterly["label"], rotation=45, ha="right", fontsize=9)
    ax_top.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"${int(x)}M"))
    ax_top.set_ylabel("Disclosed quarterly lobbying spend (USD millions)", fontsize=10)
    ax_top.grid(axis="y", linestyle=":", alpha=0.4)
    ax_top.tick_params(axis="y", labelsize=9)

    # Year separators
    yr_groups = quarterly.groupby("filing_year")
    for yr, group in yr_groups:
        x0 = group.index.min() - 0.5
        x1 = group.index.max() + 0.5
        mid = (x0 + x1) / 2
        ax_top.text(
            mid, ax_top.get_ylim()[1] * 0.95, str(int(yr)),
            ha="center", va="top", fontsize=10, color="#555", fontweight="bold",
        )

    # Annotate first vs last
    first_yr_total = quarterly[quarterly["filing_year"] == 2022]["total_spend"].sum()
    last_yr_total = quarterly[quarterly["filing_year"] == 2025]["total_spend"].sum()
    growth = (last_yr_total - first_yr_total) / first_yr_total * 100

    # Find index of 2025 Q4 (or whichever is the last 2025 quarter present)
    q4_idx_arr = quarterly.index[(quarterly["filing_year"] == 2025) & (quarterly["quarter"] == 4)]
    if len(q4_idx_arr):
        q4_idx = int(q4_idx_arr[0])
        ax_top.annotate(
            f"+{growth:.0f}% growth\n2022 → 2025",
            xy=(q4_idx, quarterly.loc[q4_idx, "total_spend"] / 1e6),
            xytext=(q4_idx - 8, quarterly.loc[q4_idx, "total_spend"] / 1e6 + 100),
            fontsize=11, fontweight="bold", color="#205594",
            arrowprops=dict(arrowstyle="->", color="#205594", lw=1.2),
            ha="center",
        )

    # ---- BOTTOM: stacked composition by issue area, by year
    ax_bot = fig.add_axes([0.07, 0.10, 0.62, 0.32])

    year_issue = (
        issue_mix.groupby(["filing_year", "issue_code"], as_index=False)["total_spend"].sum()
    )
    # Top 8 issues by total spend across all years
    top_codes = (
        year_issue.groupby("issue_code")["total_spend"].sum()
        .sort_values(ascending=False).head(8).index.tolist()
    )
    pivot = year_issue.pivot(index="filing_year", columns="issue_code", values="total_spend").fillna(0)
    other = pivot.drop(columns=top_codes, errors="ignore").sum(axis=1)
    pivot = pivot[top_codes].copy()
    pivot["Other"] = other
    pivot = pivot.loc[[2022, 2023, 2024, 2025]] / 1e6

    palette = ["#205594", "#4d80b8", "#5e2ca5", "#9b6dd3", "#0e8a52", "#3eb489",
               "#c2185b", "#e35a8b", "#bbbbbb"]
    bottom = np.zeros(len(pivot))
    for i, col in enumerate(pivot.columns):
        ax_bot.bar(
            pivot.index, pivot[col], bottom=bottom,
            color=palette[i % len(palette)], label=ISSUE_NAMES.get(col, col),
            edgecolor="white", linewidth=0.5,
        )
        bottom += pivot[col].values

    ax_bot.set_xticks(pivot.index)
    ax_bot.set_xticklabels([str(int(x)) for x in pivot.index], fontsize=10)
    ax_bot.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"${int(x)}M"))
    ax_bot.set_ylabel("Annual spend by lobbying issue (USD millions)", fontsize=10)
    ax_bot.tick_params(axis="y", labelsize=9)
    ax_bot.grid(axis="y", linestyle=":", alpha=0.4)
    ax_bot.set_title("Top 8 issues by lobbying spend, with everything else collapsed into 'Other'", fontsize=11, loc="left", pad=8)

    # Issue legend to the right of bottom panel
    handles, labels = ax_bot.get_legend_handles_labels()
    fig.legend(
        handles, labels,
        loc="upper left",
        bbox_to_anchor=(0.72, 0.42),
        frameon=False, fontsize=10, title="Top issues",
        title_fontsize=10,
    )

    # ---- Title + source
    total_2025_b = quarterly[quarterly["filing_year"] == 2025]["total_spend"].sum() / 1e9
    fig.text(
        0.07, 0.95,
        f"Federal lobbying activity hit ${total_2025_b:.1f} billion in 2025 — a {growth:.0f}% surge over 2022",
        fontsize=20, fontweight="bold", ha="left",
    )
    fig.text(
        0.07, 0.918,
        "Quarterly disclosed lobbying spend in the Senate LDA system, 2022 Q1 — 2026 Q1, and the issue-code mix that drove it.\n"
        "Figures sum lobby-firm fees (income) and self-filer in-house spend (expenses), which together cover the full disclosed market.",
        fontsize=11, ha="left", color="#444",
    )
    fig.text(
        0.07, 0.045,
        "Source: U.S. Senate LDA LD-2 quarterly filings, 2022 Q1 — 2026 Q1. Spend = COALESCE(income, expenses) per filing.\n"
        "Filings are de-duplicated per (registrant, client, year, period) — for amendments, the most-recently-posted filing wins.\n"
        "Issue mix attributes each filing's spend evenly across the issue codes it lists. Every $ is traceable to a filing_uuid.",
        fontsize=8, color="#888", ha="left",
    )

    out_png = OUT_DIR / "02_lobbying_surge.png"
    out_svg = OUT_DIR / "02_lobbying_surge.svg"
    fig.savefig(out_png, dpi=200, bbox_inches="tight")
    fig.savefig(out_svg, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out_png}")
    print(f"wrote {out_svg}")


def main() -> int:
    quarterly, issue_mix = fetch()
    quarterly.to_csv(OUT_DIR / "02_lobbying_surge_quarterly.csv", index=False)
    issue_mix.to_csv(OUT_DIR / "02_lobbying_surge_issues.csv", index=False)
    print(f"quarterly rows={len(quarterly)}, issue_mix rows={len(issue_mix)}")
    print(f"2022 total: ${quarterly[quarterly['filing_year']==2022]['total_spend'].sum()/1e9:.2f}B")
    print(f"2025 total: ${quarterly[quarterly['filing_year']==2025]['total_spend'].sum()/1e9:.2f}B")
    render(quarterly, issue_mix)
    return 0


if __name__ == "__main__":
    sys.exit(main())
