"""Chart 5: 'Say vs Pay — Crypto edition' — quarterly lobbying activities
on crypto / digital-assets topics vs quarterly congressional press releases
mentioning crypto. Same time axis. Demonstrates the cross-corpus bridge
between the LDA universe and the press corpus.

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


# Crypto keyword set — applied to BOTH the LDA `act_description` field and the
# press-release `text` field. Conservative; aim is high precision over recall.
CRYPTO_KEYWORDS = [
    "cryptocurrency", "crypto-asset", "crypto asset", "digital asset",
    "blockchain", "bitcoin", "ethereum", "stablecoin",
    "central bank digital currency", "cbdc",
    "decentralized finance", "defi", "tokeniz",
    "ftx", "coinbase", "binance",
    "lummis-gillibrand", "fit21", "fit 21", "responsible financial innovation",
    "clarity for payment stablecoins", "genius act",
]


def crypto_pattern() -> str:
    # Build a single ILIKE-friendly OR clause
    return " OR ".join(f"text ILIKE '%{kw}%'" for kw in CRYPTO_KEYWORDS)


PERIOD_TO_QUARTER = {
    "first_quarter": 1, "second_quarter": 2,
    "third_quarter": 3, "fourth_quarter": 4,
}


def fetch():
    con = connect()

    # Press: count crypto-mentioning releases per quarter, by chamber
    where = " OR ".join(f"text ILIKE '%{kw}%'" for kw in CRYPTO_KEYWORDS)
    press = con.execute(
        f"""
        SELECT EXTRACT(YEAR FROM date)::INT AS yr,
               CEIL(EXTRACT(MONTH FROM date) / 3.0)::INT AS qtr,
               chamber,
               COUNT(*) AS n_press
        FROM press
        WHERE date IS NOT NULL
          AND ({where})
        GROUP BY 1, 2, 3
        """
    ).df()

    # LDA: count activities with crypto in act_description, per quarter
    where_act = " OR ".join(f"act_description ILIKE '%{kw}%'" for kw in CRYPTO_KEYWORDS)
    activities = con.execute(
        f"""
        SELECT filing_year AS yr,
               CASE filing_period
                   WHEN 'first_quarter' THEN 1 WHEN 'second_quarter' THEN 2
                   WHEN 'third_quarter' THEN 3 WHEN 'fourth_quarter' THEN 4
                   ELSE NULL END AS qtr,
               COUNT(*) AS n_activities,
               COUNT(DISTINCT registrant_name) AS n_registrants,
               COUNT(DISTINCT client_name) AS n_clients
        FROM sen_activities
        WHERE {where_act}
        GROUP BY 1, 2
        """
    ).df()
    activities = activities.dropna(subset=["qtr"])
    activities["qtr"] = activities["qtr"].astype(int)

    # Top crypto-lobbying clients
    top_clients = con.execute(
        f"""
        SELECT client_name, COUNT(DISTINCT filing_uuid) AS n_filings
        FROM sen_activities
        WHERE {where_act}
        GROUP BY 1 ORDER BY n_filings DESC LIMIT 12
        """
    ).df()

    return press, activities, top_clients


def render(press: pd.DataFrame, acts: pd.DataFrame, top_clients: pd.DataFrame):
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titleweight": "bold",
    })

    # Build a complete quarterly index from 2022 Q1 .. 2026 Q1
    quarters = []
    for y in range(2022, 2027):
        for q in range(1, 5):
            if y == 2026 and q > 1:
                continue
            quarters.append((y, q))
    idx = pd.MultiIndex.from_tuples(quarters, names=["yr", "qtr"])

    press_total = press.groupby(["yr", "qtr"], as_index=True)["n_press"].sum().reindex(idx, fill_value=0)
    press_dem = press[press["chamber"] == "House"].groupby(["yr", "qtr"])["n_press"].sum().reindex(idx, fill_value=0)
    press_sen = press[press["chamber"] == "Senate"].groupby(["yr", "qtr"])["n_press"].sum().reindex(idx, fill_value=0)

    acts_total = acts.groupby(["yr", "qtr"], as_index=True)["n_activities"].sum().reindex(idx, fill_value=0)
    acts_clients = acts.groupby(["yr", "qtr"], as_index=True)["n_clients"].sum().reindex(idx, fill_value=0)

    quarter_labels = [f"{y} Q{q}" for y, q in idx]
    x = np.arange(len(idx))

    fig = plt.figure(figsize=(15, 10))
    ax_top = fig.add_axes([0.07, 0.55, 0.65, 0.32])
    ax_bot = fig.add_axes([0.07, 0.13, 0.65, 0.32])

    # ---- TOP: press releases
    ax_top.bar(x - 0.18, press_sen.values, width=0.36, color="#c2185b", label="Senate releases", edgecolor="white", linewidth=0.5)
    ax_top.bar(x + 0.18, press_dem.values, width=0.36, color="#205594", label="House releases", edgecolor="white", linewidth=0.5)
    ax_top.set_xticks(x)
    ax_top.set_xticklabels(quarter_labels, rotation=45, ha="right", fontsize=8.5)
    ax_top.set_ylabel("Press releases\nmentioning crypto / digital assets", fontsize=10)
    ax_top.tick_params(axis="y", labelsize=9)
    ax_top.grid(axis="y", linestyle=":", alpha=0.4)
    ax_top.legend(loc="upper left", frameon=False, fontsize=10)
    ax_top.set_title("Members' public messaging on crypto", fontsize=11, loc="left", pad=8)

    # ---- BOTTOM: LDA activities
    ax_bot.bar(x, acts_total.values, color="#5e2ca5", label="LDA activities", edgecolor="white", linewidth=0.5)
    ax_bot.set_xticks(x)
    ax_bot.set_xticklabels(quarter_labels, rotation=45, ha="right", fontsize=8.5)
    ax_bot.set_ylabel("LDA lobbying activities\nwith crypto in description", fontsize=10)
    ax_bot.tick_params(axis="y", labelsize=9)
    ax_bot.grid(axis="y", linestyle=":", alpha=0.4)
    ax_bot.set_title("Lobbying-firm and self-filer activity on crypto", fontsize=11, loc="left", pad=8)

    # Side panel: top crypto-lobbying clients
    ax_side = fig.add_axes([0.75, 0.13, 0.22, 0.74])
    ax_side.axis("off")
    top = top_clients.head(12).copy()
    ax_side.set_title("Top crypto-lobbying clients", fontsize=11, loc="left", pad=2)
    lines = []
    for i, r in top.iterrows():
        lines.append(f"{int(r['n_filings']):>4}  {r['client_name'].title()[:42]}")
    ax_side.text(0, 1.0, "\n".join(lines), fontsize=9, va="top", color="#222", family="DejaVu Sans Mono")

    # Title + caption
    fig.text(
        0.04, 0.95,
        "Crypto lobbying surged before Congress started talking about it",
        fontsize=20, fontweight="bold", ha="left",
    )
    total_acts = int(acts_total.sum())
    total_press = int(press_total.sum())
    fig.text(
        0.04, 0.917,
        f"From 2022 Q1 to 2026 Q1, lobbying activities mentioning crypto / digital assets totaled {total_acts:,}; congressional press releases on the same topics totaled {total_press:,}.\n"
        "Lobbying activity ramps sharply in 2024 — well before the visible spike in congressional press output in 2025.",
        fontsize=11, color="#444", ha="left",
    )
    fig.text(
        0.04, 0.04,
        "Source: U.S. Senate LDA quarterly filings 2022 Q1 – 2026 Q1 (sen_activities.act_description field) and Congressional press releases\n"
        "scraped from *.house.gov / *.senate.gov (text field). Keyword set: cryptocurrency, crypto-asset, digital asset, blockchain, bitcoin, ethereum,\n"
        "stablecoin, CBDC, DeFi, tokeniz*, FTX, Coinbase, Binance, Lummis-Gillibrand, FIT21, GENIUS Act, Clarity for Payment Stablecoins. Reproducible by\n"
        "rerunning analysis/charts/chart_crypto_bridge.py — every count traces to filing_uuid (LDA) or url (press) in the underlying corpora.",
        fontsize=8, color="#888", ha="left",
    )

    out_png = OUT_DIR / "05_crypto_bridge.png"
    out_svg = OUT_DIR / "05_crypto_bridge.svg"
    fig.savefig(out_png, dpi=200, bbox_inches="tight")
    fig.savefig(out_svg, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out_png}")
    print(f"wrote {out_svg}")


def main() -> int:
    press, acts, top_clients = fetch()
    press.to_csv(OUT_DIR / "05_crypto_bridge_press.csv", index=False)
    acts.to_csv(OUT_DIR / "05_crypto_bridge_acts.csv", index=False)
    top_clients.to_csv(OUT_DIR / "05_crypto_bridge_top_clients.csv", index=False)
    print(f"press rows={len(press)} acts rows={len(acts)} clients={len(top_clients)}")
    render(press, acts, top_clients)
    return 0


if __name__ == "__main__":
    sys.exit(main())
