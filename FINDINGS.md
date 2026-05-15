# Florence-v1 — Findings report

This report summarizes four findings derived from the GAIN competition corpus
(Senate LDA filings, House LDA filings, Congressional press releases,
2022-01 → 2026-03). Each finding is tied to:
- A chart in `analysis/charts/output/`
- A reproducible SQL query through `analysis/tools/query.py`
- One or more `filing_uuid`s that resolve to public source documents on
  `lda.senate.gov` and `disclosurespreview.house.gov`

Reading order matches the four chart files (`01_*`, `02_*`, `03_*`, `04_*`).

---

## Finding 1 — Every disclosed donor to Trump's inauguration was already lobbying Congress

**Chart:** `analysis/charts/output/01_inaugural_donors.png`
**Data:** `analysis/charts/output/01_inaugural_donors.csv`
**Tool:** `python analysis/tools/contribution_trace.py --honoree-like "%trump%vance%inaugural%" --md analysis/findings/inaugural_trace.md --csv analysis/findings/inaugural_trace.csv`

LDA contribution reports (LD-203) filed in 2025 Q1 disclose **$18.05 million
in contributions from 30 lobbying-active corporations to the Trump-Vance
Inaugural Committee**. The list reads as a who's-who of federally regulated
industries:

- **Oil & gas:** Occidental Petroleum ($2M)
- **Big Tech:** Meta, Uber, Intuit, Qualcomm, Broadcom, IBM, Cognizant, ID.me, Instacart ($1M each except IBM $0.75M)
- **Crypto:** Crypto.com, Coinbase, Paradigm ($1M each)
- **Finance:** Goldman Sachs ($1M)
- **Pharma:** Eli Lilly ($500K)
- **Autos:** Stellantis (FCA US, $1M); Carrier ($1M)
- **Tobacco:** Altria ($1M)
- **Gambling:** DraftKings ($502K)
- **Energy / utilities:** Honeywell ($500K), Southern Co. ($100K), First Solar ($250K), Fluor ($250K), Oklo ($250K), Centene ($50K)

Every contribution row is verifiable via the `filing_uuid` column in the CSV.
The same registrants typically file Q-reports the same quarter showing
in-house or external lobbying spend; the chart's right rail reports those
2025 totals.

**Why it's newsworthy:** the disclosures show direct dollar amounts written
by companies whose primary federal interests are regulatory — and the
contributions sit publicly in the LDA system rather than being inferred from
campaign finance filings.

**Open questions** (for follow-up):
- Did each donor's lobbying activity rise in the quarters after the
  inauguration? (Cross-reference Q1 vs Q4 2025 spend.)
- Were any donors targets of contemporaneous regulatory or legislative
  action? (Cross-reference `sen_activities.issue_code` and bill mentions.)

---

## Finding 2 — Disclosed federal lobbying topped $6 billion in 2025 — a 22% jump over 2022

**Chart:** `analysis/charts/output/02_lobbying_surge.png`
**Data:** `analysis/charts/output/02_lobbying_surge_quarterly.csv` + `02_lobbying_surge_issues.csv`

Aggregating `COALESCE(income, expenses)` across all 2025 LD-2 quarterly
filings yields **$6.11 billion** — up from **$4.99 billion in 2022**, a
22.4% increase. The growth is not driven by a single industry; the top eight
issue codes (Health, Taxation, Budget, Defense, Trade, Energy/nuclear,
Finance, Medicare/Medicaid) all show 2025 totals at or above their 2022
baselines.

**Methodology** (important caveats):
- Spend = `COALESCE(income, expenses, 0)`. Income is reported by lobby firms
  who file on behalf of clients; expenses are reported by self-filers
  (companies lobbying for themselves). They don't double-count.
- Filings are de-duplicated per `(registrant, client, year, period)` — for
  amendments, the most recently posted filing wins. Without this step the
  total inflates by ~12% via amendment double-count.
- Issue mix attributes each filing's spend evenly across the issue codes
  listed in `lobbying_activities`.

**Why it's newsworthy:** lobbying activity is at an all-time high in the
2025 dataset, with the next 2026 Q1 already showing $0.69B (on pace for
$2.76B annual lobby-firm income alone). The slope is steeper than
inflation.

---

## Finding 3 — One in eight U.S. lobbying disclosures names a tax-haven parent

**Chart:** `analysis/charts/output/03_tax_havens.png`
**Data:** `analysis/charts/output/03_tax_havens_by_country.csv` + `03_tax_havens_by_year.csv` + `03_tax_havens_callouts.csv`

Of the **25 most-disclosed foreign parents** in LDA filings 2022 Q1 – 2026
Q1, four are tax-haven jurisdictions:
- **British Virgin Islands** (131 filings) — crypto subsidiaries (Avalanche, Tron)
- **Cayman Islands** (107 filings) — TikTok / ByteDance, Polygon Labs
- **Luxembourg** (92 filings) — NSO Group, ArcelorMittal, SES, Bakelite
- **Bermuda** — Norwegian Cruise Line Holdings, Paysafe

The tax-haven share of foreign disclosures was **9.2% in 2022** and jumped
to **12.3% in 2023**, holding around 12% through 2025. The proximate driver
of the 2023 jump is the crypto industry's surge in LDA filings, where
BVI/Cayman are the standard corporate-formation jurisdictions.

**Why it's newsworthy:** the LDA `foreign_entities` array discloses the
*beneficial* foreign-parent relationship for U.S. registrants and clients —
a relationship that doesn't surface in FARA or campaign finance data.
NSO Group (the Israeli spyware maker) shows Luxembourg parents (Omri Lavie,
Dufresne Holding); TikTok Inc. discloses chained Cayman parents
(`BYTEDANCE LTD (owns 100% of BYTEDANCE INC; 100% of TIKTOK LTD ...)`).

**Verification:** every row in `03_tax_havens_callouts.csv` is keyed to a
`filing_uuid` (in the parent table `sen_foreign_entities`). The tax-haven
list itself is a composite of OECD and Tax Justice Network designations,
documented in the chart source.

---

## Finding 4 — Senate Finance and House Energy & Commerce lead the K-Street pipeline

**Chart:** `analysis/charts/output/04_revolving_door.png`
**Data:** `analysis/charts/output/04_revolving_door_committees.csv` + `04_revolving_door_top_firms.csv`
**Tool:** `python analysis/tools/revolving_door.py --out /parquet/revolving_door.parquet --md analysis/findings/revolving_door.md`

The `revolving-door-extractor` skill parses the **1,106,432** free-text
`covered_position` strings on Senate and House LDA lobbyist records into
normalized prior-role + source-office buckets. The result is a graph from
**8,586 distinct ex-federal-staffers** to their current lobbying employers.

**Top feeders (distinct ex-staffers in current LDA filings):**
- Senate Finance Committee — 83, top firm Holland & Knight (4 alumni)
- House Energy & Commerce — 80, top firm Cornerstone Govt Affairs (3)
- Senate Judiciary — 75, top firm Brownstein Hyatt (3)
- Senate HELP — 46, top firm Johnson & Johnson Services (2; self-filer)
- Senate Appropriations — 46
- House Appropriations — 44
- House Financial Services — 41, top firm Mindset Advocacy (6)

431 lobbyists disclose prior service as a **member of Congress**.

**Why it's newsworthy:** committee-level revolving-door maps usually require
hand-curating dozens of CVs. This skill produces the same map at population
scale, deterministically, in seconds — opening the door to longitudinal
analysis (does this list change after every election?) and per-firm
spotlights (which Holland & Knight clients employ those 4 ex-Finance staff?).

**Verification:** every parsed row preserves the raw `covered_position`
string. The output Parquet is committed to `/parquet/revolving_door.parquet`
and survives via the Docker volume mount.

---

## Data-quality findings (worth flagging to editors)

- **"STATE OF LOC NATION GLOBAL PUBLIC BENEFIT CORPORAT" $180M anomaly.**
  A single client name with 15 filings totaling $180M of income. The
  truncated text is the artifact; almost certainly Live Nation
  termination/amendment filings. Do not report unverified.
- **Two "Mike Collins" in the press corpus.** Mike Collins (R-GA, House)
  and (a different individual handling) Senator Susan Collins (R-ME)
  press releases appear to share `bioguide_id`. Always pin queries to a
  fully resolved `bioguide_id` to avoid attribution errors.
- **LDA `expenses_method` is mostly `"C"`** (cumulative); a small minority
  is `"A"` (actual). Don't compare across method types without normalizing.
- **2026 Q1 is only partial.** Filings continue rolling in; current totals
  understate the quarter.
