"""Chart 3: 'Tax-haven highway' — disclosed foreign parents in LDA filings,
comparing tax-haven jurisdictions vs operational economies, with the
crypto-and-spyware names called out.

Data: sen_foreign_entities

Output: PNG + SVG to analysis/charts/output/
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from views import connect  # type: ignore

OUT_DIR = Path(__file__).resolve().parent / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# Conservative tax-haven list from OECD + Tax Justice Network composite
TAX_HAVENS = {
    "Virgin Islands (British)", "Cayman Islands", "Bermuda", "Bahamas",
    "Luxembourg", "Isle of Man", "Jersey", "Guernsey", "Liechtenstein",
    "Panama", "Curacao", "Mauritius", "Marshall Islands", "Gibraltar",
    "Monaco", "Andorra", "Saint Kitts and Nevis", "Anguilla",
    "Barbados", "Cyprus", "Malta", "Cook Islands",
}

# Color groups
COLOR_HAVEN = "#c2185b"
COLOR_OECD = "#205594"
COLOR_OTHER = "#888888"

CALLOUTS = [
    ("Virgin Islands (British)", "BVI — crypto subsidiaries"),
    ("Cayman Islands", "Cayman — TikTok, Polygon"),
    ("Luxembourg", "Luxembourg — NSO Group, ArcelorMittal"),
    ("Bermuda", "Bermuda — Norwegian Cruise, Paysafe"),
]


def fetch() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    con = connect()

    # 1) Filings per country (all years summed)
    by_country = con.execute(
        """
        SELECT foreign_entity_country AS country,
               COUNT(*) AS n_filings,
               COUNT(DISTINCT client_name) AS n_clients,
               COUNT(DISTINCT foreign_entity_name) AS n_entities
        FROM sen_foreign_entities
        WHERE foreign_entity_country IS NOT NULL
        GROUP BY 1
        ORDER BY n_filings DESC
        """
    ).df()

    # 2) Tax-haven share by year
    by_year = con.execute(
        f"""
        SELECT filing_year,
               COUNT(*) AS n_total,
               SUM(CASE WHEN foreign_entity_country IN ({','.join(['?'] * len(TAX_HAVENS))}) THEN 1 ELSE 0 END) AS n_haven
        FROM sen_foreign_entities
        WHERE foreign_entity_country IS NOT NULL
        GROUP BY 1 ORDER BY 1
        """,
        list(TAX_HAVENS),
    ).df()
    by_year["haven_share"] = by_year["n_haven"] / by_year["n_total"]

    # 3) Sample callouts: which entities make BVI/Cayman/Lux/Bermuda interesting
    callouts = con.execute(
        f"""
        SELECT foreign_entity_country AS country,
               foreign_entity_name,
               client_name,
               foreign_ownership_pct,
               foreign_contribution,
               filing_year
        FROM sen_foreign_entities
        WHERE foreign_entity_country IN ({','.join(['?'] * 4)})
          AND foreign_entity_name IS NOT NULL
        ORDER BY foreign_contribution DESC NULLS LAST
        """,
        ["Virgin Islands (British)", "Cayman Islands", "Luxembourg", "Bermuda"],
    ).df()

    return by_country, by_year, callouts


def render(by_country: pd.DataFrame, by_year: pd.DataFrame, callouts: pd.DataFrame) -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titleweight": "bold",
    })

    fig = plt.figure(figsize=(15, 11))

    # ---- LEFT/MAIN: horizontal bar of top 25 countries, with havens highlighted
    ax_main = fig.add_axes([0.31, 0.10, 0.42, 0.78])
    top = by_country.head(25).copy()
    top["is_haven"] = top["country"].isin(TAX_HAVENS)
    top["color"] = top["is_haven"].map({True: COLOR_HAVEN, False: COLOR_OECD})

    y = np.arange(len(top))
    ax_main.barh(y, top["n_filings"], color=top["color"], edgecolor="white", linewidth=0.5)
    ax_main.set_yticks(y)
    ax_main.set_yticklabels(top["country"], fontsize=10)
    ax_main.invert_yaxis()
    ax_main.set_xlabel("Number of LDA filings disclosing a foreign parent\nin this country, 2022 Q1 – 2026 Q1", fontsize=10)
    ax_main.tick_params(axis="x", labelsize=9)
    ax_main.grid(axis="x", linestyle=":", alpha=0.4)
    for i, row in top.iterrows():
        ax_main.text(
            row["n_filings"] + 4, i, f"{int(row['n_filings'])}",
            va="center", fontsize=8.5, color="#333",
        )

    # ---- RIGHT/TOP: trend lines — tax-haven share by year
    ax_trend = fig.add_axes([0.78, 0.55, 0.20, 0.33])
    valid = by_year[by_year["filing_year"].between(2022, 2025)]
    ax_trend.plot(valid["filing_year"], valid["haven_share"] * 100,
                  marker="o", color=COLOR_HAVEN, linewidth=2.4)
    for _, row in valid.iterrows():
        ax_trend.text(
            row["filing_year"], row["haven_share"] * 100 + 1,
            f"{row['haven_share']*100:.0f}%",
            ha="center", fontsize=9, fontweight="bold", color=COLOR_HAVEN,
        )
    ax_trend.set_xticks(valid["filing_year"])
    ax_trend.set_xticklabels(valid["filing_year"].astype(int), fontsize=9)
    ax_trend.set_ylabel("Tax-haven share of\ndisclosed foreign parents", fontsize=9.5)
    ax_trend.set_ylim(0, max(35, valid["haven_share"].max() * 100 + 8))
    ax_trend.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{int(x)}%"))
    ax_trend.tick_params(axis="y", labelsize=8)
    ax_trend.grid(axis="y", linestyle=":", alpha=0.4)
    ax_trend.set_title("Tax-haven share jumped in 2023 and held", fontsize=10, loc="left")

    # ---- RIGHT/BOTTOM: callout examples
    ax_call = fig.add_axes([0.78, 0.10, 0.20, 0.32])
    ax_call.axis("off")
    examples = (
        callouts.dropna(subset=["foreign_entity_name", "client_name"])
        .head(40)
        .drop_duplicates(subset=["client_name", "country"])
        .head(12)
    )
    ax_call.set_title("Who's behind these names?", fontsize=10, loc="left", pad=2)
    text_lines = []
    for _, r in examples.iterrows():
        ent = r["foreign_entity_name"].title()[:34]
        cli = r["client_name"].title()[:34]
        country = r["country"]
        country_short = {
            "Virgin Islands (British)": "BVI", "Cayman Islands": "Cayman",
            "Luxembourg": "Luxembourg", "Bermuda": "Bermuda",
        }.get(country, country[:8])
        text_lines.append(f"• [{country_short}]  {cli}\n        ← parent: {ent}")
    ax_call.text(0, 0.97, "\n\n".join(text_lines), fontsize=8, va="top", color="#333", linespacing=1.0)

    # ---- Title + caption
    fig.text(
        0.04, 0.96,
        "One in eight U.S. lobbying disclosures names a tax-haven parent",
        fontsize=20, fontweight="bold", ha="left",
    )
    fig.text(
        0.04, 0.925,
        "Four tax-haven jurisdictions — British Virgin Islands, Cayman Islands, Luxembourg, and Bermuda — sit inside the\n"
        "top 25 most-disclosed foreign parents on LDA filings, outranking economies like Israel, Singapore, Hong Kong and India.",
        fontsize=11, ha="left", color="#444",
    )

    # Legend
    haven_p = mpatches.Patch(color=COLOR_HAVEN, label="Tax-haven jurisdictions (OECD / Tax Justice Network composite)")
    oecd_p = mpatches.Patch(color=COLOR_OECD, label="Other countries")
    fig.legend(handles=[haven_p, oecd_p], loc="upper left", bbox_to_anchor=(0.31, 0.92),
               frameon=False, fontsize=10)

    fig.text(
        0.04, 0.04,
        "Source: U.S. Senate LDA filings 2022 Q1 – 2026 Q1, foreign_entities array on each filing. A filing can list multiple foreign parents; each row counted once.\n"
        "Tax-haven list: BVI, Cayman, Bermuda, Bahamas, Luxembourg, Isle of Man, Jersey, Guernsey, Liechtenstein, Panama, Curacao, Mauritius, Marshall Islands, Gibraltar,\n"
        "Monaco, Andorra, St Kitts & Nevis, Anguilla, Barbados, Cyprus, Malta, Cook Islands. Each underlying disclosure is verifiable by filing_uuid via the LDA public API.",
        fontsize=8, color="#888", ha="left",
    )

    out_png = OUT_DIR / "03_tax_havens.png"
    out_svg = OUT_DIR / "03_tax_havens.svg"
    fig.savefig(out_png, dpi=200, bbox_inches="tight")
    fig.savefig(out_svg, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out_png}")
    print(f"wrote {out_svg}")


def main() -> int:
    by_country, by_year, callouts = fetch()
    by_country.to_csv(OUT_DIR / "03_tax_havens_by_country.csv", index=False)
    by_year.to_csv(OUT_DIR / "03_tax_havens_by_year.csv", index=False)
    callouts.to_csv(OUT_DIR / "03_tax_havens_callouts.csv", index=False)
    print(f"countries: {len(by_country)}")
    print(by_year)
    render(by_country, by_year, callouts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
