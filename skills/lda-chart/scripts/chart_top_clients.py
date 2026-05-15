#!/usr/bin/env python3
"""Chart 4 — Top corporate lobbying clients 2022-2025 with year-by-year cadence.

Reads `senate_filing.income` (the canonical $$$ disclosure) for quarterly
LD-2 filings only. Excludes single-filer anomalies (income > $5M/quarter).

Output:
  research/charts/04_top_clients.png
  research/charts/04_top_clients_provenance.md
"""
import os
import sys
from pathlib import Path
import duckdb
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl

ROOT = Path(__file__).resolve().parents[3]
DB = Path(os.environ.get("LDA_DB_PATH", ROOT / ".context" / "db" / "investigation.duckdb"))
OUT = ROOT / "research" / "charts"
OUT.mkdir(parents=True, exist_ok=True)

mpl.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})

con = duckdb.connect(str(DB), read_only=True)

# Top 20 clients by total 2022-2025 income, with per-year breakdown
rows = con.execute("""
SELECT client_name,
       SUM(CAST(income AS DOUBLE))/1e6 AS m_total,
       SUM(CASE WHEN filing_year=2022 THEN CAST(income AS DOUBLE) ELSE 0 END)/1e6 AS m22,
       SUM(CASE WHEN filing_year=2023 THEN CAST(income AS DOUBLE) ELSE 0 END)/1e6 AS m23,
       SUM(CASE WHEN filing_year=2024 THEN CAST(income AS DOUBLE) ELSE 0 END)/1e6 AS m24,
       SUM(CASE WHEN filing_year=2025 THEN CAST(income AS DOUBLE) ELSE 0 END)/1e6 AS m25
FROM senate_filing
WHERE filing_type LIKE 'Q_' AND filing_year BETWEEN 2022 AND 2025
  AND CAST(income AS DOUBLE) BETWEEN 1 AND 5000000
GROUP BY 1
ORDER BY m_total DESC
LIMIT 20
""").fetchall()

# Industry tag (manual curation — for color coding)
INDUSTRY = {
    "QUALCOMM INCORPORATED": "Tech",
    "COMCAST CORPORATION": "Tech / Telecom",
    "PHARMACEUTICAL RESEARCH AND MANUFACTURERS OF AMERICA": "Pharma",
    "PHARMACEUTICAL RESEARCH AND MANUFACTURERS OF AMERICA (PHRMA)": "Pharma",
    "PHRMA": "Pharma",
    "ALTRIA CLIENT SERVICES LLC": "Tobacco",
    "AMERICAN ISRAEL PUBLIC AFFAIRS COMMITTEE": "Foreign-policy advocacy",
    "MICROSOFT CORPORATION": "Tech",
    "T-MOBILE USA, INC.": "Telecom",
    "GILA RIVER INDIAN COMMUNITY": "Tribal government",
    "ILLUMINA, INC.": "Biotech",
    "GILEAD SCIENCES, INC.": "Pharma",
    "GENERAL DYNAMICS": "Defense contractor",
    "ORACLE CORPORATION": "Tech",
    "BUSINESS ROUNDTABLE": "Trade association",
    "FEDEX CORPORATION": "Logistics",
    "INDUSTRIAL ENERGY CONSUMERS OF AMERICA": "Trade association",
    "META PLATFORMS, INC.": "Tech",
    "APPLE INC.": "Tech",
    "APOLLO GLOBAL MANAGEMENT": "Finance",
    "AMERICAN HEALTH CARE ASSOCIATION": "Healthcare",
    "RAI SERVICES COMPANY": "Tobacco",
    "THE BLACKSTONE GROUP": "Finance",
    "PARTNERSHIP TO ADDRESS GLOBAL EMISSIONS, INC.": "Energy / climate",
    "CHRO ASSOCIATION (FKA HR POLICY ASSOCIATION)": "Trade association",
}
IND_COLOR = {
    "Tech": "#1f77b4",
    "Tech / Telecom": "#1f77b4",
    "Telecom": "#1f77b4",
    "Pharma": "#c81d25",
    "Biotech": "#c81d25",
    "Tobacco": "#5e2d8e",
    "Foreign-policy advocacy": "#13294B",
    "Tribal government": "#bfa97b",
    "Defense contractor": "#3a6b35",
    "Trade association": "#777777",
    "Logistics": "#d97706",
    "Finance": "#0c6e64",
    "Healthcare": "#cc2a4c",
    "Energy / climate": "#5b8f3a",
}

def short_name(n):
    n2 = n.replace(" INCORPORATED", "").replace(", INC.", "").replace("CORPORATION", "Corp.")
    n2 = n2.replace("PHARMACEUTICAL RESEARCH AND MANUFACTURERS OF AMERICA", "PhRMA (org)")
    n2 = n2.replace("AMERICAN ISRAEL PUBLIC AFFAIRS COMMITTEE", "AIPAC")
    n2 = n2.replace("CHRO ASSOCIATION (FKA HR POLICY ASSOCIATION)", "CHRO Association (fka HR Policy)")
    n2 = n2.replace("AMERICAN HEALTH CARE ASSOCIATION", "American Health Care Assn.")
    n2 = n2.replace("INDUSTRIAL ENERGY CONSUMERS OF AMERICA", "Industrial Energy Consumers of Am.")
    n2 = n2.replace("PARTNERSHIP TO ADDRESS GLOBAL EMISSIONS, INC.", "Partnership to Address Global Emissions")
    n2 = n2.replace("RAI SERVICES COMPANY", "RAI Services (Reynolds American)")
    n2 = n2.replace("ALTRIA CLIENT SERVICES LLC", "Altria Client Services")
    n2 = n2.replace("GILA RIVER INDIAN COMMUNITY", "Gila River Indian Community")
    n2 = n2.replace("THE BLACKSTONE GROUP", "The Blackstone Group")
    n2 = n2.replace("META PLATFORMS", "Meta Platforms")
    n2 = n2.replace("APOLLO GLOBAL MANAGEMENT", "Apollo Global Management")
    n2 = n2.replace("BUSINESS ROUNDTABLE", "Business Roundtable")
    n2 = n2.replace("FEDEX", "FedEx").replace("APPLE", "Apple").replace("GILEAD SCIENCES", "Gilead Sciences")
    n2 = n2.replace("GENERAL DYNAMICS", "General Dynamics").replace("ORACLE", "Oracle")
    n2 = n2.replace("MICROSOFT", "Microsoft").replace("COMCAST", "Comcast")
    n2 = n2.replace("QUALCOMM", "Qualcomm").replace("ILLUMINA", "Illumina")
    n2 = n2.replace("T-MOBILE USA", "T-Mobile USA")
    return n2.title()

# Render: horizontal stacked bar 2022→2025
fig = plt.figure(figsize=(14, 10))
fig.subplots_adjust(left=0.34, right=0.97, top=0.83, bottom=0.13)
ax = fig.add_subplot(111)

names = [short_name(r[0]) for r in rows]
totals = np.array([r[1] for r in rows])
years_M = np.array([[r[2], r[3], r[4], r[5]] for r in rows])  # M per year
industries = [INDUSTRY.get(r[0], "?") for r in rows]
colors = [IND_COLOR.get(i, "#666666") for i in industries]

y = np.arange(len(names))[::-1]
year_colors = ["#cfd7e6", "#aab7cf", "#7c8eb4", "#3b5494"]  # 22→25, getting darker
left = np.zeros(len(rows))
for yi, ycol in enumerate(year_colors):
    vals = years_M[:, yi]
    ax.barh(y, vals, left=left, color=ycol, height=0.7, label=str(2022 + yi),
            edgecolor="white", linewidth=0.4)
    left = left + vals

# Annotate total at end
for i, total in enumerate(totals):
    ax.text(total + 0.3, y[i], f"${total:.1f}M",
            va="center", fontsize=10, weight="bold", color="#222")

ax.set_yticks(y)
# Render each yticklabel with the industry as a smaller subtext beneath
yt_labels = [f"{n}" for n in names]
ax.set_yticklabels(yt_labels, fontsize=10.5)
# Add industry text just to the right of the y-tick area (negative xdata coords)
# Use figure transforms: each industry annotation as fig.text alongside y-axis ticks
# Instead, draw industry name in the bar (left-aligned, small italic)
for i, ind in enumerate(industries):
    ax.text(0.1, y[i] - 0.32, ind, fontsize=7.8, color=colors[i],
            va="top", ha="left", style="italic")
ax.set_xlim(0, totals.max() * 1.25)
ax.set_xlabel("Reported lobbying income, USD millions (Senate LD-2 filings, sum 2022 – 2025)", fontsize=10.5, color="#444")
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.spines["left"].set_color("#cccccc")
ax.spines["bottom"].set_color("#cccccc")
ax.legend(title="Year", loc="lower right", fontsize=9, frameon=False, ncol=4)
ax.grid(axis="x", color="#eeeeee", linewidth=0.6)
ax.tick_params(axis="y", which="both", left=False)

fig.text(0.04, 0.95, "Who pays K Street the most",
         fontsize=22, weight="bold", color="#13294B")
fig.text(0.04, 0.91,
    "Top 20 clients of registered Senate lobbyists by total reported income, 2022 – 2025.",
    fontsize=11.5, color="#444")
fig.text(0.04, 0.886,
    "Bars stack the four years; industry pill on the left identifies the sector.",
    fontsize=11.5, color="#444")

fig.text(0.04, 0.05,
    "Source: Senate Lobbying Disclosure Act filings (lda.senate.gov), quarterly LD-2 filings only. Excludes single-quarter filings with income > $5M (a small set of self-filed outliers; see appendix in CHECKPOINTS.md).",
    fontsize=8.5, color="#555")
fig.text(0.04, 0.034,
    "Income is self-reported. ~24% of LD-2 filings omit an income figure; those are excluded here. Reproducer: skills/lda-chart/scripts/chart_top_clients.py.",
    fontsize=8.5, color="#555")
fig.text(0.04, 0.018,
    "Industry labels are manual classification by the journalist. PhRMA appears twice because two name variants exist in the dataset — that's a known entity-resolution gap.",
    fontsize=8.5, color="#555")
fig.text(0.97, 0.018, "PressPass · GAIN 2026", fontsize=8.5, color="#555", ha="right")

fig.savefig(OUT / "04_top_clients.png", dpi=200)
fig.savefig(OUT / "04_top_clients.svg")

# Provenance
prov = OUT / "04_top_clients_provenance.md"
with prov.open("w") as f:
    f.write("# Chart 4 — Provenance\n\n")
    f.write("Top 20 LDA clients by total reported income, 2022-2025, quarterly LD-2 only.\n\n")
    f.write("| Rank | Client | 2022 | 2023 | 2024 | 2025 | Total ($M) | Industry |\n")
    f.write("|---|---|---:|---:|---:|---:|---:|---|\n")
    for i, r in enumerate(rows, 1):
        f.write(f"| {i} | {r[0]} | {r[2]:.2f} | {r[3]:.2f} | {r[4]:.2f} | {r[5]:.2f} | {r[1]:.2f} | {INDUSTRY.get(r[0], '?')} |\n")
    f.write("\n## Spot-check filings (top 3 clients, 3 sample filings each)\n\n")
    for r in rows[:3]:
        f.write(f"\n### {r[0]}\n")
        rs = con.execute(
            """
            SELECT filing_uuid, filing_year, filing_period, registrant_name, income
            FROM senate_filing
            WHERE client_name = ? AND filing_type LIKE 'Q_'
              AND CAST(income AS DOUBLE) BETWEEN 1 AND 5000000
            ORDER BY filing_year DESC, filing_period
            LIMIT 3
            """,
            [r[0]],
        ).fetchall()
        for s in rs:
            f.write(f"- `{s[0]}` ({s[1]} {s[2]}) — registrant *{s[3]}* — ${float(s[4]):,.0f}\n")

print(f"Wrote {OUT/'04_top_clients.png'}", file=sys.stderr)
print(f"Wrote {prov}", file=sys.stderr)
con.close()
