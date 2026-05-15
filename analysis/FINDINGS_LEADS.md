# Florence-v1: candidate findings from initial EDA

Each lead below is anchored to a SQL query against the Parquet indexes; the
queries live in `analysis/pipeline/eda_basics.py` and `eda_drilldown.py`. The
ones marked **★** are the strongest stories I'm building charts around.

## ★ 1. The Inauguration Bill (2025 Trump-Vance Inaugural)
LDA-disclosed corporate contributions to the *Trump Vance Inaugural Committee, Inc.* total **$7.35M from 14 disclosures**, with the canonical megadonor list:

| Contributor (LDA registrant or its client) | Amount |
|---|---|
| Occidental Petroleum | $2,000,000 (2 items) |
| Goldman Sachs | $1,000,000 (2 items) |
| Uber, Intuit, Altria, Paradigm, Carrier, Broadcom, Meta, Crypto.com, FCA, Coinbase, Qualcomm | $1,000,000 each |
| IBM | $750,000 |
| DraftKings | $502,000 |
| Eli Lilly, Honeywell | $500,000 |
| Fluor, First Solar, Oklo | $250,000 |

**Verifiable:** every contributor is in `sen_contrib_items` with a real `filing_uuid` and `contribution_date`. Cross-reference: every donor is *also* in `sen_filings` lobbying Congress that quarter.

## ★ 2. The 35 % surge
Total reported lobbying income in the Senate LDA data rose from **$2.06B (2022)** to **$2.79B (2025)** — a 35.4 % jump. 2026 Q1 alone is $691M, on pace to top $2.7B again.

## ★ 3. Tax-haven foreign parent trail
A surprising share of "foreign" LDA filings disclose ownership in **tax havens**, not operational economies:

| Country | Filings 2022-2026 | Note |
|---|---|---|
| British Virgin Islands | 131 | crypto (Avalanche, Tron) heavy |
| Cayman Islands | 107 | TikTok, Polygon, fund subsidiaries |
| Luxembourg | 92 | NSO Group, ArcelorMittal, SES, Bakelite |
| Bermuda | n/a | Norwegian Cruise, Paysafe |

Tax-haven country share rose ~3× from 2022 (~9 % of disclosures) to 2025. The crypto industry's reliance on BVI subsidiaries shows up clearly in the disclosed parents.

## ★ 4. Revolving door (covered-position concordance)
Top **`covered_position`** patterns reveal which Hill offices most often feed K-Street:
- Senate Commerce Committee (Deputy SD/GC, Chief Counsel)
- House Financial Services Committee (Senior Counsel)
- Top member offices (Hoyer, Hastings, Cantor, Costa, Cardoza, Torricelli, McCollum)
- 1,543 lobbyist filings list "Former Member of Congress" as the covered position.

## 5. The party-volume gap in House messaging
House Democrats out-press-release House Republicans **17,961 vs 11,795** in 2025 — and the gap has widened every year since 2022 (9,725 vs 5,871).

## 6. Most-lobbied agencies
Aside from House (687K) and Senate (679K activities targeted), the top non-Hill targets are:
- White House Office (43,057)
- HHS (35,108)
- Commerce (30,715)
- USDA (30,478)
- Energy (28,271)

## 7. The $180M "STATE OF LOC NATION GLOBAL PUBLIC BENEFIT CORPORAT" anomaly
A client with 15 filings and a $180M reported income — almost certainly a data-quality artifact (likely Live Nation termination filings). Flagged for verification, not a story until verified.

## 8. Crypto industry consolidation in lobbying
Coinbase, Crypto.com (FORIS DAX), Paradigm, Avalanche, Polygon, Tron, DraftKings all show up either in the inaugural contribution list or in tax-haven foreign disclosures. The crypto policy push is visible across both files.

## 9. Top inaugural-donor sectors
Energy (Oxy, Fluor, First Solar), Big Tech (Meta, IBM, Microsoft-class, Broadcom, Qualcomm), Finance (Goldman, Intuit), Pharma (Lilly), Defense (Honeywell), Crypto (Coinbase, Crypto.com), Cars (FCA, Carrier) and Tobacco (Altria). Effectively every regulated industry wrote a check.

---

**Charts I'm prioritizing:** #1, #2, #3, #4 — they're the most narratively
distinct and the most cleanly sourced.
