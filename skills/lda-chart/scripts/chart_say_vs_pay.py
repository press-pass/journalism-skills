#!/usr/bin/env python3
"""Chart 3 — The "say vs pay" gap on specific bills.

A scatter plot, log-log, where each point is a Congressional bill that
appears in either lobbying activity descriptions or in the title/body of
a Congressional press release. X = total lobbying filings (Senate + House
LDA). Y = total press releases mentioning the bill. Bills in the top
quintile of lobbying activity but the bottom quintile of press coverage
are labelled and color-shifted: those are the "silently lobbied" bills.

A short curated annotation column on the right names what each labeled
bill actually is.
"""
import os
import sys
from pathlib import Path
import duckdb
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[3]
DB = Path(os.environ.get("LDA_DB_PATH", ROOT / ".context" / "db" / "investigation.duckdb"))
OUT = ROOT / "research" / "charts"
OUT.mkdir(parents=True, exist_ok=True)

mpl.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})

con = duckdb.connect(str(DB), read_only=True)

# Build the panel
rows = con.execute("""
WITH lobby AS (
  SELECT bill_id,
         COUNT(DISTINCT filing_uuid) AS senate_filings,
         (SELECT COUNT(DISTINCT filing_id) FROM bill_mentions_lobby_house h WHERE h.bill_id=l.bill_id) AS house_filings
  FROM bill_mentions_lobby l
  GROUP BY 1
),
press AS (
  SELECT bill_id, COUNT(*) AS press_mentions, COUNT(DISTINCT bioguide_id) AS press_members
  FROM bill_mentions_press
  GROUP BY 1
)
SELECT l.bill_id, l.senate_filings, l.house_filings, COALESCE(p.press_mentions,0) AS press_mentions, COALESCE(p.press_members,0) AS press_members
FROM lobby l
LEFT JOIN press p USING (bill_id)
WHERE (l.senate_filings + l.house_filings) >= 30
""").fetchall()
bills = [r[0] for r in rows]
lobby = np.array([r[1] + r[2] for r in rows])
press = np.array([r[3] for r in rows])

# Identify silently-lobbied bills: top 20% lobby + bottom 30% press
hi_lobby = np.quantile(lobby, 0.80)
lo_press = np.quantile(press, 0.30)
silent_mask = (lobby >= hi_lobby) & (press <= lo_press)

# Curated bill descriptions (research note — visible in chart for annotated bills)
BILL_LABELS = {
    "HR5376": "Inflation Reduction Act\n(2022 climate/health law)",
    "HR1": "For the People Act / current\nHR 1 ('America First' agenda)",
    "HR3684": "Bipartisan Infrastructure Law\n(implementation)",
    "HR2617": "FY23 Consolidated Approps\n(omnibus)",
    "HR2670": "FY24 NDAA\n(Defense Authorization)",
    "S1260": "USICA / CHIPS precursor\n(2022 competitiveness bill)",
    "HR4521": "America COMPETES Act",
    "HR7900": "FY23 NDAA\n(Defense Authorization)",
    "HR1319": "American Rescue Plan\n(implementation)",
    "HR7024": "Tax Relief for American\nFamilies and Workers Act",
    "S2587": "FY24 Defense Approps",
    "S4638": "FY25 NDAA",
    "HR8236": "FY23 Defense Approps",
    "S1939": "FAA Reauthorization",
    "S2226": "FY24 NDAA (Senate)",
    "HR4366": "FY24 Energy & Water Approps",
    "HR3838": "Lower Energy Costs Act",
    "HR4365": "SAFER Network Games Act / Approps",
    "S2296": "Veterans Programs Approps",
    "S2572": "FY26 Defense Approps (microelectronics)",
    "S4921": "FY25 DoD Approps (Senate)",
    "HR9029": "FY26 Labor/HHS/Ed Approps",
    "HR1165": "Data Privacy Act",
    "S4543": "FY23 NDAA (Inhofe NDAA)",
    "S1838": "Alzheimer's Care Act",
    "HR8255": "Satellite Streamlining Act",
    "S2605": "FY24 Energy & Water Approps",
    "HR5304": "FY26 Continuing Approps",
    "S2321": "Price Gouging Prevention Act",
}

fig = plt.figure(figsize=(16.5, 10.5))
fig.subplots_adjust(left=0.07, right=0.55, top=0.82, bottom=0.13)
ax = fig.add_subplot(111)

# Background scatter (all bills)
non_silent = ~silent_mask
ax.scatter(lobby[non_silent], np.maximum(press[non_silent], 0.5),
           s=14, color="#aab4c6", alpha=0.55, edgecolor="none")
# Silent ones
ax.scatter(lobby[silent_mask], np.maximum(press[silent_mask], 0.5),
           s=80, color="#c81d25", alpha=0.85, edgecolor="white", linewidth=0.8, zorder=4)
# HR1 explicitly (heavy press AND heavy lobby — control case)
for i, b in enumerate(bills):
    if b == "HR1":
        ax.scatter([lobby[i]], [press[i]], s=120, color="#1a9850", alpha=0.9,
                   edgecolor="white", linewidth=0.8, zorder=5)

ax.set_xscale("log")
ax.set_yscale("symlog", linthresh=1)
ax.set_xlim(20, lobby.max() * 1.4)
ax.set_ylim(0, press.max() * 4)
ax.set_xlabel("Lobbying filings naming the bill (Senate + House LDA, 2022 – 2026 Q1) →", fontsize=10.5, color="#444")
ax.set_ylabel("Press releases mentioning the bill (members of Congress, 2022 – 2026 Q1) →", fontsize=10.5, color="#444")

ax.grid(True, which="major", color="#e8e8ef", linewidth=0.6)
ax.grid(True, which="minor", color="#f4f4f7", linewidth=0.4)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.spines["left"].set_color("#cccccc")
ax.spines["bottom"].set_color("#cccccc")

# Diagonal "balance" guide: press ~ lobby / 100 (just a visual reference)
xs = np.array([20, lobby.max() * 1.5])
ax.plot(xs, xs / 100, ls="--", color="#888", linewidth=0.8, alpha=0.5, zorder=1)
ax.text(xs[1] * 0.95, xs[1] / 100 * 1.05, "press ≈ 1% of lobby filings",
        fontsize=8, color="#888", ha="right", alpha=0.8)

# Label points: silent bills + HR1 + HR5376 (the IRA, the iconic case)
ann_set = set(np.where(silent_mask)[0])
for must in ("HR1", "HR5376", "HR2670"):
    if must in bills:
        ann_set.add(bills.index(must))

# Label only the top 14 by lobby intensity to avoid clutter; offset to reduce overlap.
top_to_label = sorted(ann_set, key=lambda i: -lobby[i])[:14]
# Manually-tuned offsets for the most-likely-collision points
offsets = {
    "HR1": (10, 12),
    "HR5376": (-50, 18),
    "HR2670": (8, 12),
    "HR3684": (-58, 14),
    "HR2617": (8, -14),
    "HR4521": (-55, -14),
    "S2587": (8, 6),
    "HR8236": (8, -16),
    "S4638": (-50, 8),
    "S1939": (8, -14),
    "HR7900": (-48, -14),
    "HR4365": (8, 12),
}
for idx in top_to_label:
    b = bills[idx]
    dx, dy = offsets.get(b, (8, 6))
    ax.annotate(
        b,
        xy=(lobby[idx], max(press[idx], 0.5)),
        xytext=(dx, dy),
        textcoords="offset points",
        fontsize=9.5, color="#222", weight="bold",
        arrowprops=dict(arrowstyle="-", color="#888", linewidth=0.5, alpha=0.7),
    )

# Title & subtitle
fig.text(0.04, 0.945, "What gets lobbied in silence",
         fontsize=24, weight="bold", color="#13294B")
fig.text(0.04, 0.908,
    "Specific Congressional bills, plotted by how often they appear in lobbying-activity descriptions versus in members' own press releases.",
    fontsize=11.5, color="#444")
fig.text(0.04, 0.886,
    "Bills in the top 20% of lobbying activity but the bottom 30% of press coverage are highlighted in red — these are the bills K Street",
    fontsize=11.5, color="#444")
fig.text(0.04, 0.864,
    "spends the most lobbying on while members of Congress stay almost silent. The green dot is HR 1, the bill members talk about most.",
    fontsize=11.5, color="#444")

# Right-side legend describing each labeled bill
labels = [(bills[i], lobby[i], press[i]) for i in sorted(ann_set, key=lambda i: -lobby[i])]
legend_x = 0.57
fig.text(legend_x, 0.85, "Bills labeled in chart", fontsize=13, weight="bold", color="#13294B")
fig.text(legend_x, 0.823, "(red = silently lobbied; green = HR 1)", fontsize=9, color="#666", style="italic")
y = 0.79
for bill, lo, pr in labels[:14]:
    desc = BILL_LABELS.get(bill, "—")
    color = "#c81d25" if (lo >= hi_lobby and pr <= lo_press) else ("#1a9850" if bill == "HR1" else "#13294B")
    fig.text(legend_x, y, bill, fontsize=11, weight="bold", color=color)
    fig.text(legend_x + 0.06, y, desc.replace("\n", " "), fontsize=9.5, color="#333")
    fig.text(legend_x + 0.32, y, f"{int(lo):,} filings",
             fontsize=9, color="#666", weight="bold")
    fig.text(legend_x + 0.385, y, f"·  {int(pr)} press",
             fontsize=9, color="#666")
    y -= 0.043

# Source footer
fig.text(0.04, 0.05,
    "Source: Senate & House Lobbying Disclosure Act filings (lda.senate.gov, disclosurespreview.house.gov) and Congressional press releases (thescoop.org/congress-press), 2022 – 2026 Q1.",
    fontsize=8.5, color="#555")
fig.text(0.04, 0.034,
    "Bill numbers extracted by regex against activity descriptions and press release body text; normalized to canonical form (HR5376, S2587, HCONRES14).",
    fontsize=8.5, color="#555")
fig.text(0.04, 0.018,
    "Filter: bills with ≥30 lobbying filings included; 'silent' = top 20% lobby & bottom 30% press. Reproducer: skills/lda-say-vs-pay/.",
    fontsize=8.5, color="#555")
fig.text(0.96, 0.018, "PressPass · GAIN 2026", fontsize=8.5, color="#555", ha="right")

fig.savefig(OUT / "03_say_vs_pay.png", dpi=200)
fig.savefig(OUT / "03_say_vs_pay.svg")

# Provenance
prov = OUT / "03_say_vs_pay_provenance.md"
with prov.open("w") as f:
    f.write("# Chart 3 — Provenance\n\n")
    f.write("Reproducer: `python3 skills/lda-say-vs-pay/scripts/extract_bill_mentions.py && python3 skills/lda-chart/scripts/chart_say_vs_pay.py`\n\n")
    f.write(f"Silent threshold: lobby ≥ {int(hi_lobby):,} & press ≤ {int(lo_press)}.\n\n")
    f.write("## Every labeled point\n\n| Bill | Description | Senate lobby | House lobby | Press releases | Distinct press members |\n|---|---|---:|---:|---:|---:|\n")
    for idx in sorted(ann_set, key=lambda i: -lobby[i]):
        b = bills[idx]
        sen = con.execute("SELECT COUNT(DISTINCT filing_uuid) FROM bill_mentions_lobby WHERE bill_id=?", [b]).fetchone()[0]
        hou = con.execute("SELECT COUNT(DISTINCT filing_id) FROM bill_mentions_lobby_house WHERE bill_id=?", [b]).fetchone()[0]
        pm = con.execute("SELECT COUNT(*) FROM bill_mentions_press WHERE bill_id=?", [b]).fetchone()[0]
        pmem = con.execute("SELECT COUNT(DISTINCT bioguide_id) FROM bill_mentions_press WHERE bill_id=?", [b]).fetchone()[0]
        f.write(f"| **{b}** | {BILL_LABELS.get(b, '—')} | {sen:,} | {hou:,} | {pm} | {pmem} |\n")
    f.write("\n## Sample evidence: silent bill HR3684 (Bipartisan Infrastructure Law)\n\n")
    rs = con.execute("""
        SELECT DISTINCT f.filing_uuid, f.filing_year, f.client_name, substr(a.description, 1, 180) AS desc
        FROM bill_mentions_lobby b
        JOIN senate_filing f USING (filing_uuid)
        JOIN senate_activity a USING (filing_uuid, act_idx)
        WHERE b.bill_id = 'HR3684' AND f.filing_year = 2025
        LIMIT 5
    """).fetchall()
    for r in rs:
        f.write(f"- `{r[0]}` ({r[1]}) — *{r[2]}* — \"{r[3]}\"\n")

print(f"Wrote {OUT/'03_say_vs_pay.png'}", file=sys.stderr)
print(f"Wrote {prov}", file=sys.stderr)
con.close()
