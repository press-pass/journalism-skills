#!/usr/bin/env python3
"""Chart 2 — Foreign-tied lobbying by client country and policy issue.

A heatmap of the top 12 countries × top 12 ALI issue codes appearing on
Senate-LDA filings whose client reports foreign ownership/control.
"""
import os
import sys
from pathlib import Path
import duckdb
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.colors import LinearSegmentedColormap

ROOT = Path(__file__).resolve().parents[3]
DB = Path(os.environ.get("LDA_DB_PATH", ROOT / ".context" / "db" / "investigation.duckdb"))
OUT = ROOT / "research" / "charts"
OUT.mkdir(parents=True, exist_ok=True)

mpl.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
})

# Country code → display name (ISO 3166-1 alpha-2 used in senate_foreign_entity)
COUNTRY_NAMES = {
    "CN": "China", "GB": "United Kingdom", "CA": "Canada", "JP": "Japan",
    "DE": "Germany", "CH": "Switzerland", "NL": "Netherlands", "KR": "South Korea",
    "FR": "France", "AU": "Australia", "IL": "Israel", "VG": "Brit. Virgin Is.",
    "KY": "Cayman Islands", "SG": "Singapore", "IE": "Ireland", "LU": "Luxembourg",
    "DK": "Denmark", "SE": "Sweden", "HK": "Hong Kong", "NO": "Norway",
    "IT": "Italy", "BR": "Brazil", "RU": "Russia", "SA": "Saudi Arabia",
    "IN": "India", "TW": "Taiwan", "MX": "Mexico", "BE": "Belgium",
}

con = duckdb.connect(str(DB), read_only=True)

# Top countries (excluding NULL, dropping pure tax havens for visual clarity? — keep VG/KY in)
top_countries = [r[0] for r in con.execute("""
    SELECT entity_country
    FROM senate_foreign_entity
    WHERE entity_country IS NOT NULL
    GROUP BY 1
    ORDER BY COUNT(DISTINCT filing_uuid) DESC
    LIMIT 12
""").fetchall()]

# Top issues across that universe
top_issues = [r[0] for r in con.execute("""
    SELECT a.general_issue_code_display
    FROM senate_foreign_entity fe
    JOIN senate_activity a USING (filing_uuid)
    JOIN senate_filing f USING (filing_uuid)
    WHERE fe.entity_country IS NOT NULL
      AND a.general_issue_code_display IS NOT NULL
    GROUP BY 1
    ORDER BY COUNT(DISTINCT f.filing_uuid) DESC
    LIMIT 12
""").fetchall()]

# Build the matrix
mat = np.zeros((len(top_countries), len(top_issues)), dtype=int)
filings_per_cell = {}  # (country, issue) -> list of filing_uuid for provenance

for ci, country in enumerate(top_countries):
    rows = con.execute("""
        SELECT a.general_issue_code_display AS issue,
               COUNT(DISTINCT f.filing_uuid) AS n
        FROM senate_foreign_entity fe
        JOIN senate_activity a USING (filing_uuid)
        JOIN senate_filing f USING (filing_uuid)
        WHERE fe.entity_country = ? AND a.general_issue_code_display IS NOT NULL
        GROUP BY 1
    """, [country]).fetchall()
    issue_map = {r[0]: r[1] for r in rows}
    for ii, issue in enumerate(top_issues):
        mat[ci, ii] = issue_map.get(issue, 0)

# Plot
country_labels = [COUNTRY_NAMES.get(c, c) for c in top_countries]
issue_labels = [iss.replace("/", " /\n").replace(" (domestic/foreign)", "") for iss in top_issues]

fig = plt.figure(figsize=(13, 8))
fig.subplots_adjust(left=0.15, right=0.98, top=0.83, bottom=0.16)
ax = fig.add_subplot(111)

cmap = LinearSegmentedColormap.from_list("navy_white", ["#f7f7fc", "#3b5494", "#13294B"])
im = ax.imshow(mat, aspect="auto", cmap=cmap, vmin=0, vmax=np.percentile(mat, 99))

ax.set_xticks(range(len(top_issues)))
ax.set_xticklabels(issue_labels, rotation=35, ha="right", fontsize=9.5)
ax.set_yticks(range(len(top_countries)))
ax.set_yticklabels(country_labels, fontsize=10.5)

for ci in range(len(top_countries)):
    for ii in range(len(top_issues)):
        v = mat[ci, ii]
        if v == 0:
            continue
        color = "white" if v > np.percentile(mat, 60) else "#222222"
        ax.text(ii, ci, str(v), ha="center", va="center", fontsize=8.5, color=color)

ax.set_xticks(np.arange(len(top_issues)+1) - .5, minor=True)
ax.set_yticks(np.arange(len(top_countries)+1) - .5, minor=True)
ax.grid(which="minor", color="white", linewidth=2)
ax.tick_params(which="minor", bottom=False, left=False)
for s in ("top", "right", "bottom", "left"):
    ax.spines[s].set_visible(False)

fig.text(0.04, 0.93, "What foreign principals pay K Street to lobby on", fontsize=20, weight="bold", color="#13294B")
fig.text(0.04, 0.89,
    "Senate-LDA filings 2022-2026 Q1 where the client reports foreign ownership; cell = distinct filings",
    fontsize=11, color="#444444")
fig.text(0.04, 0.866,
    "by client's country of foreign control and ALI policy issue. The shape of each row is the lobbying agenda for that country's principals.",
    fontsize=11, color="#444444")

fig.text(0.04, 0.04,
    "Source: Senate LDA filings (lda.senate.gov); foreign_entities sub-record. Issue codes: ALI standard, mapped via senate/constants/lobbying_activity_issues.json.",
    fontsize=8.5, color="#555555")
fig.text(0.04, 0.022,
    "Tax-haven jurisdictions (BVI, Cayman) appear because some clients route ownership through holding companies. Filings join: foreign_entity → filing_uuid → activity.",
    fontsize=8.5, color="#555555")
fig.text(0.98, 0.022, "PressPass · GAIN 2026", fontsize=8.5, color="#555555", ha="right")

cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
cbar.set_label("Distinct filings", fontsize=9, color="#444444")

fig.savefig(OUT / "02_foreign_principal_issues.png", dpi=200)
fig.savefig(OUT / "02_foreign_principal_issues.svg")

# Provenance
prov = OUT / "02_foreign_principal_provenance.md"
with prov.open("w") as f:
    f.write("# Chart 2 — Provenance\n\n")
    f.write("Each cell is `COUNT(DISTINCT filing_uuid)` from a join of `senate_foreign_entity` × `senate_activity` "
            "filtered to top 12 countries × top 12 issues.\n\n")
    f.write("Reproducer: `python3 skills/lda-chart/scripts/chart_foreign_issues.py`\n\n")
    f.write("## Cell values\n\n| country | " + " | ".join(top_issues) + " |\n")
    f.write("|---|" + "|".join(["---:"]*len(top_issues)) + "|\n")
    for ci, c in enumerate(top_countries):
        cells = " | ".join(str(int(mat[ci, ii])) for ii in range(len(top_issues)))
        f.write(f"| {c} ({COUNTRY_NAMES.get(c, c)}) | {cells} |\n")
    # Spot-check: 3 filings per high-traffic cell
    f.write("\n## Spot checks (3 sample filings per high-traffic cell)\n\n")
    sample_cells = [(top_countries[ci], top_issues[ii], int(mat[ci, ii]))
                    for ci in range(len(top_countries)) for ii in range(len(top_issues))]
    sample_cells.sort(key=lambda t: -t[2])
    for country, issue, v in sample_cells[:10]:
        if v < 3:
            continue
        rows = con.execute(
            """
            SELECT DISTINCT f.filing_uuid, f.filing_year, f.client_name, fe.entity_name
            FROM senate_foreign_entity fe
            JOIN senate_activity a USING (filing_uuid)
            JOIN senate_filing f USING (filing_uuid)
            WHERE fe.entity_country = ? AND a.general_issue_code_display = ?
            LIMIT 3
            """, [country, issue],
        ).fetchall()
        f.write(f"\n### {COUNTRY_NAMES.get(country, country)} × {issue} (cell = {v})\n")
        for r in rows:
            f.write(f"- `{r[0]}` ({r[1]}) — client *{r[2]}* — foreign entity *{r[3]}*\n")

print(f"Wrote {OUT/'02_foreign_principal_issues.png'}", file=sys.stderr)
print(f"Wrote {prov}", file=sys.stderr)
con.close()
