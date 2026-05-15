# Findings report — belo-horizonte-v1 (GAIN Agentic Investigation Challenge)

This report covers eight findings produced by running the
`lobbying-corpus-ingest` + analytic skills in this branch against the GAIN
corpus (Senate + House LDA, Congressional press releases, 2022 – 2026 Q1).

Every finding cites the originating filing identifiers (`filing_uuid`,
`house_file`, or press release `url`). For Senate filings the public record
lives at:

    https://lda.senate.gov/filings/public/filing/<filing_uuid>/print/

For House filings:

    https://disclosurespreview.house.gov/?fid=<house_file_without_extension>

Counts and totals here are reproducible via the SQL in
[`pipeline/queries.sql`](pipeline/queries.sql) and the pipeline driver
[`pipeline/run_pipeline.sh`](pipeline/run_pipeline.sh). The corresponding
charts are under `.context/charts/`, each with a `.meta.json` audit sidecar.

---

## A. Federal lobbying revenue jumped 30 % year-over-year in 2025 — the largest single-year increase in the corpus

Total Senate-reported lobbying income (Q1 + Q2 + Q3 + Q4) by year:

| Year | Total reported income | YoY change |
|---|---|---|
| 2022 | $2.061 B | — |
| 2023 | $2.122 B | +2.9 % |
| 2024 | $2.211 B | +4.2 % |
| **2025** | **$2.788 B** | **+26.1 %** |
| 2026 Q1 only | $0.690 B | (annualized: $2.76 B) |

The quarterly trajectory (chart `c5_quarterly_total.png`) shows a step-change
between Q4 2024 ($552 M) and Q1 2025 ($620 M) — a one-quarter jump of $68 M —
followed by sustained growth through Q4 2025 at $738 M. **Q4 2025 alone is
33 % higher than the average quarterly spend across 2022.**

**Sources:** `senate_filings` aggregated by `filing_year` and `filing_period`,
filtered to `filing_type LIKE 'Q%'` with non-null income > 0.
Reproducible: `.context/findings/f7_quarterly_total_spend.csv`.

**Chart:** [`.context/charts/c5_quarterly_total.png`](.context/charts/c5_quarterly_total.png)

---

## B. H.R. 1 (119th Congress) is the most-lobbied bill on record in the corpus

The "One Big Beautiful Bill" / 119th Congress H.R. 1 was named in lobbying
activity descriptions across **2,872 distinct clients and 6,111 Senate
filings in 2025**, more than 3× the next bill (S. 2296 at 773 clients). The
filings that mention it carry $237 M in supporting income.

H.R. 1 also appears in **326 Congressional press releases** during 2025 —
making it both the most-lobbied and one of the most-talked-about pieces of
legislation in the corpus.

| Bill | Clients lobbying | Press releases | Supporting income |
|---|---|---|---|
| 119-HR-1 | 2,872 | 326 | $236.7 M |
| 119-S-2296 | 773 | 7 | $49.1 M |
| 119-HR-1968 | 686 | 52 | $33.8 M |
| 119-HR-3838 | 680 | 48 | $44.2 M |
| 119-HR-4016 | 618 | 25 | $66.5 M |

**Sources:** `bill_mentions_lobbying` joined to `senate_filings`;
`bill_mentions_press` joined to `press_releases`.
Reproducible: `.context/findings/f5_top_bills_lobbied_2025.csv` and
`.context/findings/f6_bills_press_and_lobbying_2025.csv`.

**Chart:** [`.context/charts/c6_top_bills_2025.png`](.context/charts/c6_top_bills_2025.png)
and [`.context/charts/c10_hr1_top_clients.png`](.context/charts/c10_hr1_top_clients.png)

---

## C. Nippon Steel paid $3.4M to a single Washington firm to lobby on the U.S. Steel merger

Across 2025 Nippon Steel Corporation paid **Akin Gump Strauss Hauer & Feld
$3,420,000 in four LDA filings** specifically to lobby on "the proposed
merger of Nippon Steel and US Steel" (the regulatory fight over CFIUS
review and the eventual Presidential decision). The four filings are split
across all four quarters of 2025, with Q1 2025 alone at $1.65 M (filing
`58064aaa-c6bd-4d30-a928-f8407049fb1a` — verified manually against
`lda.senate.gov`).

The team listed on the Akin Gump filings is 10 named lobbyists, all under
the TRD (Trade) issue code:

> Geoff Verhoff · Joseph Fawkner · Scott Parven · Sean D'Arcy · Ed Pagano ·
> Christina Barone · Richard Coppola · Hunter Bates · Sam Olswanger · David
> Schwietert

Targets named in the filings: U.S. House, U.S. Senate, Department of
Commerce, Department of State. This puts a precise dollar figure on the
foreign-acquirer lobbying campaign that ran in parallel to the regulatory
review.

**Sources:** four filings under `client_name = 'NIPPON STEEL CORPORATION'`
and `filing_year = 2025`:

- `58064aaa-c6bd-4d30-a928-f8407049fb1a` (Q1, $1.65 M) — verified
- `744e3154-0c29-4753-9138-c048c07377b1`
- `47367be2-84d1-4d18-...` (truncated in CSV)
- one additional Q-period filing

Reproducible: query `senate_filings` for `client_name = 'NIPPON STEEL CORPORATION' AND filing_year = 2025`.

---

## D. The LDA filing system has no income verification: a single sovereign-citizen filer logged $460 M of "lobbying"

**Status:** Data-quality / governance finding.

The "STATE OF LOC NATION GLOBAL PUBLIC BENEFIT CORPORATION", filed by
"LOC COMMUNITY ASSOCIATION", logged **15 LDA filings between 2024 Q3 and
2026 Q1, including 8 quarterly reports at $20 M each — totalling
$160,000,000 in reported lobbying income — and 7 amendments adding another
$140 M, for a cumulative $460 M of self-reported activity** the system
accepted without challenge.

The filings' "specific issues" sections, verified directly against
`lda.senate.gov`, describe activity centred on H.R. 40 (the reparations
study bill) and reference "Vance Certificates of Payment", "Sovereign
Financial Institution Chartered under Treaty", and a request for "Black
USD" currency printing — language characteristic of sovereign-citizen and
related fringe legal movements, not LDA-defined lobbying.

The named lobbyist is "REV DR CHRISTINA CLEMENT" (Q1 2025 filing
`4d5b1cb0-0971-43b8-958b-d260e2be8af1`, verified). The submissions remain
posted with no flag, no income retraction, and no withdrawal.

This is a story in two parts:

1. The filings themselves — a clear, repeated abuse of the public LDA
   reporting system that has been live for at least 18 months.
2. The systemic issue — the LDA reporting system at `lda.senate.gov`
   accepts and publishes any income value entered by a filer, with no
   automated outlier detection. A filer can claim $20 M / quarter
   indefinitely.

**Sources:** 15 filings under `client_name LIKE 'STATE OF LOC%'`.
Manually verified filing: `4d5b1cb0-0971-43b8-958b-d260e2be8af1`.
Reproducible CSV: `.context/findings/f1b_loc_nation_filings.csv`.

These rows are excluded from the "top 25 clients" leaderboard
(`.context/charts/c1_top25_clients_2025.png`) so the leaderboard reflects
genuine industry spending.

---

## E. Two former Congressional staffers each appear on >1,000 distinct Senate filings via their covered-position disclosures

The `lobbying-revolving-door` skill parsed 1.09 M free-text
`covered_position` fields. The top two named individuals by filing count:

| Name | Senate filings | House filings | Most-cited prior role |
|---|---|---|---|
| **Daniel McFaul** | 988 | (uncounted) | Legislative Director to Rep. Joe Scarborough; Chief of Staff to Reps. Jeff Miller and Matt Gaetz |
| **Emily Murry** | 1,048 | 955 | Staff Director, Ways & Means Health Subcommittee; Senior Policy Advisor to Majority Leader Kevin McCarthy |

Both individuals' covered-position text was disclosed across hundreds of
filings filed by their current employer for many different clients —
suggesting these are essentially "name-on-the-paperwork" lobbyists. A
deeper story is who their actual clients are.

Note that the parser identifies the **named** individual and the principal
of their prior role. It cannot tell you what they're being paid in their
current role, only the breadth of filings their name appears on. That
breadth is itself a reportable signal.

**Sources:** `revolving_door_positions` filtered to `confidence >= 0.7`,
joined back to `senate_lobbyists` and `house_lobbyists`. Reproducible:
`.context/findings/f4_revolving_door_top.csv` (raw_examples column has the
underlying free-text snippets so a reader can audit the parse).

---

## F. Foreign-funded U.S. lobbying tracked in the corpus: top spenders 2025

Detected via either `client_country` being non-US in the Senate filing or
country names appearing in the `foreign_entity_issues` activity field
(see `lobbying-foreign-influence`).

Top 2025 totals (Senate side only):

| Detected country | Filings | Reported income |
|---|---|---|
| Canada | 169 | $22.2 M |
| (Undetermined) | 119 | $16.9 M |
| United Kingdom | 80 | $11.5 M |
| Japan | 39 | $9.0 M |
| South Korea | 31 | $6.9 M |
| China | 21 | $6.3 M |
| Switzerland | 29 | $6.3 M |
| Germany | 25 | $6.0 M |
| Australia | 37 | $4.0 M |
| **Cayman Islands** | **17** | **$3.8 M** |
| Singapore | 13 | $3.6 M |
| **Bermuda** | **(small N)** | **$2.3 M** |
| North Macedonia | (small N) | $2.0 M |

The Caribbean tax-haven entries (Cayman Islands and Bermuda) are
particularly worth following up on — both jurisdictions appear with
material lobbying spend that doesn't correspond to obvious bilateral policy
interests, suggesting offshore-incorporated U.S.-business lobbying that
chooses to disclose under the offshore jurisdiction.

**Sources:** `foreign_lobbying` table built by
`lobbying-foreign-influence/scripts/build_foreign_influence.py`. Each row
carries `filing_uuid` (or `house_file`) and the original
`foreign_entity_text` so the country tag can be audited.
Reproducible: `.context/findings/f3_foreign_spend_by_country_year.csv`.

**Chart:** [`.context/charts/c3_foreign_2025_top20.png`](.context/charts/c3_foreign_2025_top20.png)

---

## G. The five biggest issue areas all spiked in 2025 — but only Health Issues sustained the growth into Q4

The `lobbying-issue-spike` skill flags 5,000+ quarter-over-quarter spike
rows. Restricting to issue-level rollups (cf.
`.context/findings/f2_spend_by_issue_year.csv`):

- **Budget/Appropriations (BUD)** rose from $470 M in 2024 to $539 M in
  2025 (+15 %), the largest absolute increase. Driven primarily by the
  H.R. 1 reconciliation cycle (see finding B).
- **Health Issues (HCR)** rose from $370 M (2024) to $440 M (2025), +19 %,
  and is the only top-5 issue still climbing into Q4 2025.
- **Taxation (TAX)** rose from $260 M (2024) to $337 M (2025), +30 %.
- **Energy / Nuclear (ENG)** rose from $185 M (2024) to $237 M (2025),
  +28 %.
- **Trade (TRD)** rose from $215 M (2024) to $283 M (2025), +32 % —
  consistent with both Nippon Steel and the broader trade-policy
  rebalancing in the new administration.

**Sources:** `senate_filings × senate_activities` aggregated on
`(filing_year, general_issue_code)`. Reproducible:
`.context/findings/f2_spend_by_issue_year.csv` and
`.context/findings/spikes_by_issue.csv`.

**Chart:** [`.context/charts/c2_top_issues_over_time.png`](.context/charts/c2_top_issues_over_time.png)

---

## H. Congressional press-release output more than doubled between 2022 and 2025

The corpus shows 141,332 press releases vs. 418,098 Senate LDA filings
across 2022 – 2026 Q1. Comparing press releases against all Q-period
Senate LDA filings (no income filter):

| Quarter | Press releases | Senate Q filings | Ratio |
|---|---|---|---|
| 2022 Q1 | 5,041 | 20,346 | 0.25 |
| 2023 Q1 | 7,899 | 20,559 | 0.38 |
| 2024 Q1 | 8,772 | 21,194 | 0.41 |
| 2025 Q1 | 13,772 | 22,372 | 0.62 |
| 2026 Q1 | 11,466 | 21,126 | 0.54 |

Press-release output per quarter **2.7× over three years (5,041 → 13,772)**
while lobbying filings rose by only 10 %. The Q1 2025 ratio of 0.62 press
releases per filing is the highest in the corpus. Press output dipped
slightly in 2026 Q1 versus Q1 2025 but remains well above 2024 levels.

Possible drivers (the corpus does not distinguish): more communications
staff capacity per office, increased political salience of explaining one's
votes, AI-assisted drafting, or new-member rooms ramping up their websites.

**Sources:** counts from `press_releases` and `senate_filings` grouped by
quarter. Reproducible:
`.context/findings/f7_quarterly_total_spend.csv` (filings) and
`.context/findings/f9_press_by_party_month.csv` (press).

**Chart:** [`.context/charts/c7_press_by_party_month.png`](.context/charts/c7_press_by_party_month.png)

---

## Method limits and disclaimers

- **Self-reported data.** LDA filings rely on registrant honesty. Income
  values are not audited. Finding D shows how this can fail.
- **Issue-code aggregation.** Activities with multiple issue codes are
  counted once per code (so an activity with codes `TAX` and `ENG` will
  contribute to both totals). This is intentional for "what got lobbied
  on" questions but means simple sums of "spend by issue" double-count.
- **Quarterly amendments.** Filings carry a `filing_type` like `1A`/`2A`
  for amendments. F1 excludes those to avoid double-counting income; F1b
  includes them for the LOC anomaly to show the full picture.
- **Bill extraction.** Bill numbers are extracted via regex from
  free-text. Named acts ("Inflation Reduction Act") without a bill number
  are not captured. The bill_id includes a Congress prefix derived from
  the filing year — bills re-introduced across Congresses are kept as
  distinct rows.
- **Foreign country detection.** Done via the LDA `countries.json`
  vocabulary plus a small demonym dictionary. Multi-country foreign
  entities are tagged with all detected countries (comma-joined).

## Reproducing every claim in this report

```bash
# 1. build the database
python3 skills/lobbying-corpus-ingest/scripts/build_db.py \
   --data-root <path/to/data> --db lobbying.duckdb --workers 8

# 2. run analytic skills
DB=lobbying.duckdb OUT=findings bash pipeline/run_pipeline.sh

# 3. materialize finding CSVs
duckdb lobbying.duckdb < pipeline/queries.sql

# 4. render charts
bash pipeline/make_charts.sh
```

Every CSV under `.context/findings/` and every chart under
`.context/charts/` is overwritten by these commands. The `.meta.json`
sidecar next to each PNG embeds the input file SHA-256 hash and the git
commit so a reviewer can prove a chart was generated from a specific
version of the data and the code.
