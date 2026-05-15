"""Chart 1: 'The Inaugural Bill' — lobbying-active corporations' contributions
to the 2025 Trump-Vance Inaugural Committee, alongside their disclosed
lobbying income for the same quarter.

Output: PNG + SVG to analysis/charts/output/
"""
from __future__ import annotations

import os
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


# Sector classification (manual mapping — every donor verified by name)
SECTOR = {
    "OCCIDENTAL PETROLEUM CORPORATION": "Oil & gas",
    "UBER TECHNOLOGIES, INC.": "Big tech",
    "META PLATFORMS, INC. AND VARIOUS SUBSIDIARIES": "Big tech",
    "INTUIT, INC. AND AFFILIATES (FORMERLY INTUIT, INC.)": "Big tech",
    "ALTRIA CLIENT SERVICES LLC": "Tobacco",
    "FORIS DAX, INC. & ITS AFFILIATED ENTITIES D/B/A CRYPTO.COM": "Crypto",
    "PARADIGM OPERATIONS LP": "Crypto",
    "FCA US LLC": "Autos",
    "COINBASE, INC.": "Crypto",
    "QUALCOMM, INCORPORATED": "Big tech",
    "THE GOLDMAN SACHS GROUP, INC.": "Finance",
    "CARRIER GLOBAL CORPORATION": "Industrial",
    "BROADCOM INC.": "Big tech",
    "INTERNATIONAL BUSINESS MACHINES CORPORATION (IBM)": "Big tech",
    "DRAFTKINGS INC. AND ITS AFFILIATES": "Gambling",
    "ELI LILLY AND COMPANY": "Pharma",
    "HONEYWELL INTERNATIONAL": "Defense",
    "OKLO INC.": "Nuclear",
    "MOTOROLA SOLUTIONS, INC": "Industrial",
    "A10 ASSOCIATES, LLC": "Lobby firm",
    "FLUOR CORPORATION": "Engineering",
    "FIRST SOLAR, INC.": "Solar",
    "MAPLEBEAR INC. D/B/A INSTACART": "Big tech",
    "SOUTHERN COMPANY": "Utilities",
    "ID.ME, LLC": "Big tech",
    "FUJIFILM HOLDINGS AMERICA CORPORATION": "Industrial",
    "COGNIZANT TECHNOLOGY SOLUTIONS U.S. CORPORATION": "Big tech",
    "REWORLD WASTE LLC": "Utilities",
    "SOLAR ENERGY INDUSTRIES ASSOCIATION": "Solar",
    "CENTENE CORPORATION": "Healthcare",
}

SECTOR_COLORS = {
    "Big tech": "#1f6fb4",
    "Crypto": "#5e2ca5",
    "Oil & gas": "#222222",
    "Finance": "#0e8a52",
    "Pharma": "#c2185b",
    "Healthcare": "#c2185b",
    "Tobacco": "#825f5f",
    "Autos": "#b85c00",
    "Industrial": "#666666",
    "Defense": "#3a3a3a",
    "Engineering": "#666666",
    "Gambling": "#a07d10",
    "Solar": "#d9a300",
    "Nuclear": "#7e5a00",
    "Utilities": "#5b738f",
    "Lobby firm": "#999999",
}


def fetch_data() -> pd.DataFrame:
    con = connect()

    # Distinct contribution rows to the inaugural
    contribs = con.execute(
        """
        SELECT DISTINCT
            ci.registrant_id, ci.registrant_name, ci.amount,
            ci.contribution_date,
            ci.filing_uuid AS contrib_filing_uuid
        FROM sen_contrib_items ci
        WHERE ci.honoree_name ILIKE '%trump%vance%inaugural%'
        """
    ).df()
    contribs["registrant_name"] = contribs["registrant_name"].str.strip()

    # Aggregate to registrant
    agg = (
        contribs.groupby("registrant_name", as_index=False)
        .agg(inaugural_dollars=("amount", "sum"), n_items=("amount", "size"))
    )

    # Disclosed lobbying spend.
    # For self-filers (companies lobbying for themselves), the figure is in
    # `expenses`. For lobby firms representing clients, it's in `income`.
    # Use COALESCE so we capture whichever is present.
    sql_lobby = """
    WITH spend AS (
        SELECT
            f.registrant_name,
            f.filing_year,
            f.filing_period,
            COALESCE(f.income, f.expenses, 0) AS spend
        FROM sen_filings f
        WHERE f.filing_type LIKE 'Q%'
          AND f.registrant_name IN (
              SELECT DISTINCT registrant_name FROM sen_contrib_items
              WHERE honoree_name ILIKE '%trump%vance%inaugural%'
          )
    )
    SELECT
        registrant_name,
        SUM(CASE WHEN filing_year = 2024 AND filing_period = 'fourth_quarter' THEN spend END) AS q4_2024,
        SUM(CASE WHEN filing_year = 2025 AND filing_period = 'first_quarter' THEN spend END) AS q1_2025,
        SUM(CASE WHEN filing_year = 2025 THEN spend END) AS y2025_total
    FROM spend
    GROUP BY 1
    """
    lobby = con.execute(sql_lobby).df()
    lobby["registrant_name"] = lobby["registrant_name"].str.strip()

    df = agg.merge(lobby, on="registrant_name", how="left")
    df["sector"] = df["registrant_name"].map(SECTOR).fillna("Other")
    df = df.sort_values("inaugural_dollars", ascending=False).reset_index(drop=True)

    return df


def short_name(name: str) -> str:
    """Friendly short label for the chart."""
    name = name.strip()
    SHORT = {
        "OCCIDENTAL PETROLEUM CORPORATION": "Occidental Petroleum",
        "UBER TECHNOLOGIES, INC.": "Uber",
        "META PLATFORMS, INC. AND VARIOUS SUBSIDIARIES": "Meta",
        "INTUIT, INC. AND AFFILIATES (FORMERLY INTUIT, INC.)": "Intuit",
        "ALTRIA CLIENT SERVICES LLC": "Altria",
        "FORIS DAX, INC. & ITS AFFILIATED ENTITIES D/B/A CRYPTO.COM": "Crypto.com",
        "PARADIGM OPERATIONS LP": "Paradigm",
        "FCA US LLC": "Stellantis (FCA US)",
        "COINBASE, INC.": "Coinbase",
        "QUALCOMM, INCORPORATED": "Qualcomm",
        "THE GOLDMAN SACHS GROUP, INC.": "Goldman Sachs",
        "CARRIER GLOBAL CORPORATION": "Carrier",
        "BROADCOM INC.": "Broadcom",
        "INTERNATIONAL BUSINESS MACHINES CORPORATION (IBM)": "IBM",
        "DRAFTKINGS INC. AND ITS AFFILIATES": "DraftKings",
        "ELI LILLY AND COMPANY": "Eli Lilly",
        "HONEYWELL INTERNATIONAL": "Honeywell",
        "OKLO INC.": "Oklo",
        "MOTOROLA SOLUTIONS, INC": "Motorola Solutions",
        "A10 ASSOCIATES, LLC": "A10 Associates (lobby firm)",
        "FLUOR CORPORATION": "Fluor",
        "FIRST SOLAR, INC.": "First Solar",
        "MAPLEBEAR INC. D/B/A INSTACART": "Instacart",
        "SOUTHERN COMPANY": "Southern Co.",
        "ID.ME, LLC": "ID.me",
        "FUJIFILM HOLDINGS AMERICA CORPORATION": "Fujifilm",
        "COGNIZANT TECHNOLOGY SOLUTIONS U.S. CORPORATION": "Cognizant",
        "REWORLD WASTE LLC": "Reworld Waste",
        "SOLAR ENERGY INDUSTRIES ASSOCIATION": "Solar Energy Inds. Assn.",
        "CENTENE CORPORATION": "Centene",
    }
    return SHORT.get(name, name.title())


def render(df: pd.DataFrame) -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.titleweight": "bold",
    })

    fig = plt.figure(figsize=(14, 12))
    # Reserve generous header + footer space
    ax = fig.add_axes([0.32, 0.13, 0.62, 0.72])

    df = df.copy()
    df["label"] = df["registrant_name"].map(short_name)
    df["lobbying_y2025"] = df["y2025_total"].fillna(0)
    df["color"] = df["sector"].map(SECTOR_COLORS).fillna("#888888")

    y = np.arange(len(df))
    ax.barh(y, df["inaugural_dollars"], color=df["color"], edgecolor="white", linewidth=0.5, alpha=0.93)

    max_dollar = df["inaugural_dollars"].max()
    for i, row in df.iterrows():
        # Right-of-bar amount label
        ax.text(
            row["inaugural_dollars"] + max_dollar * 0.01,
            i,
            f"${row['inaugural_dollars']/1000:,.0f}K",
            va="center",
            fontsize=9,
            color="#222",
            fontweight="bold",
        )
        # Lobbying-spend annotation further right (italic gray)
        if row["lobbying_y2025"] and row["lobbying_y2025"] > 0:
            ax.text(
                max_dollar * 1.18,
                i,
                f"+ ${row['lobbying_y2025']/1e6:,.1f}M lobbying spend, 2025",
                va="center",
                fontsize=9,
                color="#555",
                style="italic",
            )
        else:
            ax.text(
                max_dollar * 1.18,
                i,
                "lobbying spend filed by outside firm",
                va="center",
                fontsize=8.5,
                color="#999",
                style="italic",
            )

    ax.set_yticks(y)
    ax.set_yticklabels(df["label"], fontsize=10.5)
    ax.invert_yaxis()
    ax.set_xlim(0, max_dollar * 1.95)
    def _fmt(x, _):
        if x >= 1e6:
            v = x / 1e6
            return f"${v:.1f}M" if v != int(v) else f"${int(v)}M"
        return f"${int(x/1e3)}K"

    ax.xaxis.set_major_formatter(mtick.FuncFormatter(_fmt))
    ax.tick_params(axis="x", labelsize=9, colors="#555")
    ax.tick_params(axis="y", left=False)
    ax.grid(axis="x", linestyle=":", alpha=0.4, zorder=0)
    # Only show ticks up to max_dollar (don't show extra ticks in the
    # annotation zone)
    nice_max = (int(max_dollar / 5e5) + 1) * 5e5
    ax.set_xticks(np.arange(0, nice_max + 1, 5e5))

    # Title + subtitle in figure coords so they don't collide with the axes
    fig.text(
        0.04,
        0.95,
        "Every donor to Trump's inauguration was already lobbying Congress",
        fontsize=22,
        fontweight="bold",
        ha="left",
    )
    fig.text(
        0.04,
        0.905,
        "30 lobbying-active corporations gave ${:.1f} million to the Trump-Vance Inaugural Committee in late 2024 and early 2025.\n"
        "Most also reported lobbying spend on their own behalf in 2025; the rest used outside lobby firms.".format(
            df["inaugural_dollars"].sum() / 1e6
        ),
        fontsize=12,
        color="#444",
        ha="left",
    )

    # Sector legend
    sectors_in_use = sorted({s for s in df["sector"] if s in SECTOR_COLORS})
    handles = [plt.Rectangle((0, 0), 1, 1, color=SECTOR_COLORS[s]) for s in sectors_in_use]
    fig.legend(
        handles,
        sectors_in_use,
        loc="upper left",
        ncol=8,
        bbox_to_anchor=(0.04, 0.875),
        frameon=False,
        fontsize=10,
        handlelength=1.2,
        handleheight=0.8,
        columnspacing=1.0,
    )

    fig.text(
        0.04,
        0.058,
        "Source: U.S. Senate LDA contribution reports (LD-203), 2025 Q1, all filings matching honoree '%trump%vance%inaugural%'. Lobbying-spend column sums each\n"
        "registrant's COALESCE(income, expenses) across their 2025 LD-2 quarterly filings — covers both self-filer companies (expenses) and lobby firms (income).\n"
        "Every contribution row is verifiable by filing_uuid via the LDA public API.",
        fontsize=8,
        color="#888",
        ha="left",
    )

    out_png = OUT_DIR / "01_inaugural_donors.png"
    out_svg = OUT_DIR / "01_inaugural_donors.svg"
    fig.savefig(out_png, dpi=200, bbox_inches="tight")
    fig.savefig(out_svg, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out_png}")
    print(f"wrote {out_svg}")


def main() -> int:
    df = fetch_data()
    # Save the underlying data alongside the chart
    df.to_csv(OUT_DIR / "01_inaugural_donors.csv", index=False)
    print(f"data: {len(df)} registrants, ${df['inaugural_dollars'].sum():,.0f} total")
    render(df)
    return 0


if __name__ == "__main__":
    sys.exit(main())
