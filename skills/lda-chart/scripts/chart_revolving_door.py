#!/usr/bin/env python3
"""Chart 1 — Top members of Congress whose former senior staff have the
heaviest active lobbying footprint, 2024–2026 Q1.

Output:
  research/charts/01_revolving_door_top_members.png
  research/charts/01_revolving_door_top_members.svg
  research/charts/01_revolving_door_provenance.md (every filing UUID behind every bar)
"""
import duckdb
import os
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib as mpl

ROOT = Path(__file__).resolve().parents[3]
DB = Path(os.environ.get("LDA_DB_PATH", ROOT / ".context" / "db" / "investigation.duckdb"))
OUT = ROOT / "research" / "charts"
OUT.mkdir(parents=True, exist_ok=True)

mpl.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.titleweight": "bold",
    "axes.titlesize": 14,
    "axes.labelsize": 10,
    "figure.dpi": 130,
})

con = duckdb.connect(str(DB), read_only=True)

# (1) Top 20 former bosses by # distinct ACTIVE (2024-2026Q1) former-staff lobbyists.
# (2) Add # client engagements those staffers ran 2024+.
sql = """
WITH staff_active AS (
  SELECT DISTINCT
    rd.bioguide,
    rd.member_first || ' ' || rd.member_last AS member,
    rd.lobbyist_first,
    rd.lobbyist_last,
    f.filing_year
  FROM revolving_door rd
  JOIN senate_filing f USING (filing_uuid)
  WHERE rd.lobbyist_first IS NOT NULL AND rd.lobbyist_last IS NOT NULL
    AND f.filing_year >= 2024
),
member_lobbyist_pairs AS (
  SELECT bioguide, member, lobbyist_first, lobbyist_last
  FROM staff_active GROUP BY 1, 2, 3, 4
),
counts AS (
  SELECT bioguide, member, COUNT(*) AS active_lobbyists
  FROM member_lobbyist_pairs
  GROUP BY 1, 2
  ORDER BY active_lobbyists DESC
  LIMIT 20
),
-- For each of those members, count distinct clients those staffers represented in 2024+
clients_per_member AS (
  SELECT c.bioguide, c.member, COUNT(DISTINCT f.client_id) AS distinct_clients,
         COUNT(DISTINCT f.filing_uuid) AS filings
  FROM counts c
  JOIN revolving_door rd ON rd.bioguide = c.bioguide
  JOIN senate_filing f USING (filing_uuid)
  WHERE f.filing_year >= 2024
  GROUP BY 1, 2
)
SELECT c.member, c.bioguide, c.active_lobbyists, cl.distinct_clients, cl.filings
FROM counts c
LEFT JOIN clients_per_member cl USING (bioguide, member)
ORDER BY c.active_lobbyists DESC, cl.distinct_clients DESC
"""
rows = con.execute(sql).fetchall()
members = [r[0].title() for r in rows]
bioguides = [r[1] for r in rows]
n_lob = [r[2] for r in rows]
n_clients = [r[3] for r in rows]
n_filings = [r[4] for r in rows]

# --- Chart ---
fig = plt.figure(figsize=(11.5, 11))
# Use subplots_adjust for tight control
fig.subplots_adjust(left=0.18, right=0.96, top=0.83, bottom=0.10)
ax = fig.add_subplot(111)

y = list(range(len(members)))[::-1]  # top of list on top
bar_color = "#13294B"
ax.barh(y, n_lob, color=bar_color, height=0.7, alpha=0.93)

for i, (lb, cl, fl) in enumerate(zip(n_lob, n_clients, n_filings)):
    ax.text(lb + 0.35, y[i],
            f"{lb} staffers   ·   {cl} clients   ·   {fl:,} filings",
            va="center", fontsize=9.5, color="#444444", family="DejaVu Sans")

ax.set_yticks(y)
ax.set_yticklabels(members, fontsize=11)
ax.set_xlim(0, max(n_lob) * 2.0)
ax.tick_params(axis="x", which="both", bottom=False, labelbottom=False)
ax.tick_params(axis="y", which="both", left=False)
ax.set_xlabel("")
for s in ("top", "right", "bottom"):
    ax.spines[s].set_visible(False)
ax.spines["left"].set_color("#cccccc")
ax.grid(False)

# Title block (figure-level for clean placement)
fig.text(0.04, 0.95, "Whose former chiefs of staff fill K Street?",
         fontsize=22, weight="bold", color="#13294B")
fig.text(0.04, 0.905,
    "Members of Congress (current and former) whose ex-aides currently have the largest active",
    fontsize=11, color="#444444")
fig.text(0.04, 0.885,
    "Senate-side lobbying footprint, 2024-Q1 through 2026-Q1.",
    fontsize=11, color="#444444")

# Footer
fig.text(0.04, 0.055,
    "Source: Senate Lobbying Disclosure Act filings (lda.senate.gov), 2024-Q1 through 2026-Q1.",
    fontsize=8.5, color="#555555")
fig.text(0.04, 0.038,
    "Lobbyists matched to their former boss by parsing the LDA covered_position text against the unitedstates.io legislator roster",
    fontsize=8.5, color="#555555")
fig.text(0.04, 0.021,
    "(high-precision regex: full first+last, or last+state qualifier). Counts dedupe to distinct (first_name, last_name) pairs.",
    fontsize=8.5, color="#555555")
fig.text(0.96, 0.021, "PressPass · GAIN 2026",
         fontsize=8.5, color="#555555", ha="right")

fig.savefig(OUT / "01_revolving_door_top_members.png", dpi=200)
fig.savefig(OUT / "01_revolving_door_top_members.svg")
plt.close(fig)

# --- Provenance ---
prov = OUT / "01_revolving_door_provenance.md"
with prov.open("w") as f:
    f.write("# Chart 1 — Provenance\n\n")
    f.write("**Claim:** For each Member listed, the bar height equals the number of distinct "
            "people (first+last) appearing in the Senate-LDA `senate_lobbyist` table during "
            "2024–2026 Q1 whose `covered_position` text resolves to that Member via the rules in "
            "`skills/lda-revolving-door/scripts/extract_members.py`.\n\n")
    f.write("**Reproducer:** `python3 skills/lda-revolving-door/scripts/extract_members.py "
            "&& python3 skills/lda-chart/scripts/chart_revolving_door.py`\n\n")
    f.write("## Numbers in the chart\n\n| Rank | Member | Bioguide | Active lobbyists | Distinct clients | Filings |\n|---|---|---|---:|---:|---:|\n")
    for i, (m, b, nl, nc, nf) in enumerate(zip(members, bioguides, n_lob, n_clients, n_filings), 1):
        f.write(f"| {i} | {m} | {b} | {nl} | {nc} | {nf} |\n")
    f.write("\n## Spot-check filings (top 5 members, 3 filings each)\n\n")
    for b in bioguides[:5]:
        rows2 = con.execute(
            """
            SELECT DISTINCT f.filing_uuid, f.filing_year, f.client_name, sl.first_name, sl.last_name,
                   substr(sl.covered_position, 1, 160) AS covered_position
            FROM revolving_door rd
            JOIN senate_filing f USING (filing_uuid)
            JOIN senate_lobbyist sl USING (filing_uuid, act_idx, lobbyist_idx)
            WHERE rd.bioguide = ? AND f.filing_year >= 2024
            ORDER BY f.filing_year DESC
            LIMIT 3
            """,
            [b],
        ).fetchall()
        f.write(f"\n### {b}\n")
        for r in rows2:
            f.write(f"- `{r[0]}` ({r[1]}) — **{r[3]} {r[4]}** for *{r[2]}* — covered_position: \"{r[5]}\"\n")
print(f"Wrote {OUT/'01_revolving_door_top_members.png'}", file=sys.stderr)
print(f"Wrote {prov}", file=sys.stderr)
con.close()
