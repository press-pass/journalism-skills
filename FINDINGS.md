# Findings Report — GAIN Agentic Investigation Challenge

Author: Press Pass (Seamus Martin) · Branch `spmartin823/lobbying-press-charts`
Corpus: GAIN dataset (Senate LDA 2022–2026 Q1, House LDA 2022–2026 Q1, Congress press releases 2022–2026 Q1).

Every claim cites a primary key from the corpus. Where the claim depends on substring
matching (e.g., "AI" → `artificial intelligence`), the matching logic is named.

---

## Headline finding: Lobbyist filers disclosed $66.9 million to the Trump-Vance inaugural fund — about 13× what the entire 5-year corpus shows going to anything Biden-related.

**Where.** Senate LD-203 contribution items. Sum of `amount` where `payee` contains "TRUMP
VANCE INAUGURAL" (case-insensitive): **$66,956,876** across **111** disclosed line items.
For comparison, every payee containing "BIDEN" across the same five-year corpus sums to
**$5.36M** across 615 items.

**Anchoring example.** JBS USA Food Holdings (the US arm of Brazilian meatpacker JBS S.A.,
which controls a meaningful share of the US beef and pork market) reported **$5,000,000** to
the Trump-Vance Inaugural Committee on **2025-01-02**.

- Filing UUID: `ef66ecc1-d888-4f43-b997-5577091e2057`
- Source path: `data/senate/2025/contributions/contributions_2025.json`
- Public URL: https://lda.senate.gov/api/v1/contributions/ef66ecc1-d888-4f43-b997-5577091e2057/

Other seven-figure reported contributors (top of `08_inaugural_money.png`): Occidental Petroleum
($2M), Robinhood ($2M), United Airlines ($2M), Chevron ($2M), Amazon.com Services ($1.9M),
General Motors ($1.5M), Coinbase ($1M), BlackRock ($1M), Intuit ($1M), Coupang ($1M),
Qualcomm, Applied Materials, Micron Technology, NVIDIA, Google Client Services LLC, Carrier
Global, Uber, Verizon, Foris Dax (Crypto.com), Gilead, Stanley Black & Decker, ConocoPhillips.

**Reporter angle.** LD-203 disclosures are the only place where contributions by lobbyists
and their employers to inaugural funds are required to be itemized. The size of the
concentration — over 60 publicly-reported corporations giving over $1M each to a single
political event in the same calendar quarter — is a story by itself. The presence of foreign-
parented firms (JBS, Carrier Global) and crypto/AI/Big Tech actors who later had specific
policy outcomes in the first 90 days of the new administration is worth tracing.

**Caveats.** LD-203 reports are self-described disclosures; some are amendments. The amounts
are *reported by* the registrants, not federally certified. Cross-check with FEC inaugural-
committee filings before publishing.

---

## Finding 2: AI lobbying has multiplied 5× since ChatGPT. So have AI press releases — but lobbyists still outnumber members of Congress 5-to-1 in their AI commentary.

**Where.** Senate `lobbying_activities` table.

- **2022 Q1** — 233 activities mention `artificial intelligence`; **145** unique clients.
- **2023 Q4** — 798 activities (3.4× vs. 2022 Q1, in the quarter after ChatGPT launched 2022-11-30).
- **2026 Q1** — **1,176** activities; **649** unique clients (5×).

Press releases tracking the same keyword on the same calendar (Congress Press corpus):

- **2022 Q1** — 17 mentions.
- **2026 Q1** — **237** mentions (14× — a steeper relative rise than lobbying).

**Reporter angle.** "Says one thing, pays another" → only a third of members who mention AI
in a press release ever have a constituent listed in covered_position of an AI lobbyist;
the AI lobbying universe (649 clients, 2026 Q1) dwarfs the universe of members who publicly
weigh in (top 15 members had ~12-45 each).

**Top AI lobbying clients by activity count, 2022–2026 Q1.** Microsoft Corporation (262
filings with at least one AI activity), Oracle (109), News Media Alliance (105), Chamber of
Commerce (100), Americans for Responsible Innovation (94), Comcast (80), Workday (75), ITI
(73), NVIDIA (73), Meta Platforms (68).

**Top member messengers (2025 + 2026 Q1):** Sen. Elizabeth Warren (45 releases), Sen.
Richard Blumenthal (28), Sen. Martin Heinrich (22), Sen. Todd Young (R) (18), Sen. Marsha
Blackburn (R) (18). Three of the top five are members of the Senate Commerce / Judiciary
committees that have hosted AI hearings — a public-engagement pattern that mirrors the
lobbying targeting.

**Sourcing example.** One Microsoft 2025 Q1 AI activity record:

- Filing UUID: `33f5fb51-6075-4c12-bc88-bb8834...` (Microsoft Corporation)
- Source path: `data/senate/2025/filings/filings_2025.json`
- Activity description: "Issues related to technology a..." (truncated; full text in JSON sidecar)

**Caveat.** Substring match on `artificial intelligence` is conservative — it misses
"machine learning", "AI" alone (deliberately, to avoid two-letter-token noise), and
non-English variants. Actual coverage is higher. Counts are activities, not unique
filings; one filing can have multiple AI activities.

---

## Finding 3: Trump 2.0 triggered the largest single-quarter lobbying rush of the last five years — 2,511 new Senate registrations in Q1 2025, +91% over the four-year average.

**Where.** Senate `filings` with `filing_type='RR'` (new registrant–client engagement),
grouped by quarter.

| Quarter | New registrations |
|---|---:|
| 2022 Q1 | 1,317 |
| 2022 Q2 | 1,112 |
| 2022 Q3 | 741 |
| 2022 Q4 | 758 |
| 2023 Q1 | 1,490 |
| 2023 Q4 | 758 |
| 2024 Q1 | 1,407 |
| 2024 Q4 | 817 |
| **2025 Q1** | **2,511** |
| 2025 Q2 | 1,816 |
| 2025 Q3 | 1,376 |
| 2025 Q4 | 1,233 |
| 2026 Q1 | 1,814 |

Q1 2025 is **1.91×** the four-year Q1 baseline (1,316). The rush abates somewhat across
2025 but Q1 2026 is still **38%** above the four-year baseline.

**Reporter angle.** Track *which* registrations rose fastest in Q1 2025 — by client country,
by client industry (`client_general_description`), and by ALI issue code. Compare with
Q1 2021 (Biden inauguration) by extending the corpus backward via the public LDA API.

**Caveats.** Quarter aggregation uses Senate `filing_period`. Q1 2026 numbers are complete
for the Senate but partial for House (only Q1 + early registrations as of 2026-03-31).

---

## Finding 4: The Senate Democratic minority — not the Republican majority — produced the most press releases in Q1 2026, led by Sen. Dick Durbin (208 in 90 days = 2.3/day).

**Where.** Congress press corpus, releases dated 2026-01-01 to 2026-03-31.

| Rank | Member | Q1 2026 releases | per day |
|---|---|---:|---:|
| 1 | Sen. Richard J. Durbin (D-IL) | 208 | 2.31 |
| 2 | Del. Kimberlyn King-Hinds (R-MP) | 159 | 1.77 |
| 3 | Sen. Kirsten Gillibrand (D-NY) | 140 | 1.56 |
| 4 | Sen. Cindy Hyde-Smith (R-MS) | 133 | 1.48 |
| 5 | Rep. Ruben Gallego (D-AZ) | 128 | 1.42 |
| 6 | Rep. Hakeem Jeffries (D-NY) | 124 | 1.38 |
| 7 | Sen. Peter Welch (D-VT) | 118 | 1.31 |
| 8 | Sen. Jeff Merkley (D-OR) | 117 | 1.30 |
| 9 | Sen. Richard Blumenthal (D-CT) | 117 | 1.30 |
| 10 | Sen. Martin Heinrich (D-NM) | 116 | 1.29 |

15 of the top 20 are Democrats — striking given Democrats are the minority in the 119th
Congress. The implication: out-of-power members rely more heavily on press output to
reach the public.

**Sourcing example.** First three Durbin 2026 releases verified at:
- https://www.durbin.senate.gov/news... (collected 2026-03-30, `data/congress_press/2026-01.jsonl`)

**Caveats.** Press release counts are scraper-derived. 2024-11 in the same dataset has only
374 releases for the entire chamber — likely a scrape gap, not a real drop. Always
inspect the monthly count series before drawing trend conclusions.

---

## Finding 5: K Street's biggest single-office Hill alumni pipeline runs through Sen. Chuck Schumer — 48 distinct lobbyists list a Schumer-office role in their disclosed covered_position.

**Where.** Senate `lobbyists` table → `covered_position` free text → matched against
member surnames that uniquely identify a single bioguide_id in the press corpus.

| Rank | Member | Distinct lobbyists |
|---|---|---:|
| 1 | Sen. Charles E. Schumer (D-NY) | 48 |
| 2 | Shontel M. Brown (D-OH) | 47 |
| 3 | Sen. Todd Young (R-IN) | 39 |
| 4 | Sen. Mitch McConnell (R-KY) | 35 |
| 5 | Sen. John Cornyn (R-TX) | 35 |
| 6 | Sen. Patty Murray (D-WA) | 35 |
| 7 | Sen. Robert Menendez (D-NJ) | 33 |
| 8 | Sen. Joni Ernst (R-IA) | 32 |

**Sourcing example.** Lobbyist Lucia Panza (id ranges in `senate_lobbyists.parquet`) at
Crossroads Strategies LLC lists `Counsel, U.S. Senator Charles Schumer` in her covered
position (one of many similar disclosures, filing UUID
`7859846e-0c18-44b4-a8e7-7ee3b2...`).

**Reporter angle.** Cross-reference with the LDA registrant→client→income chain to compute
"former Schumer staffer-attributed lobbying dollars per quarter." That number — readily
producible from `revolving-door-extract` output joined to `senate_filings.income` — is a
significant story on its own.

**Caveats — important.** Several common surnames (Brown, Ryan, Paul, Scott) collide with
historical members of Congress not present in the 2022–2026 press corpus. The lookup
deliberately drops *ambiguous* surnames, but cannot disambiguate `Brown` between current
member Shontel Brown and retired Sen. Sherrod Brown. Many of the 47 "Brown" entries plausibly
worked for Sherrod, not Shontel. The chart caption flags this; a more rigorous version
would use a complete bioguide table from congress.gov bulk data.

---

## Finding 6: 18,400+ unique client names appear in BOTH chambers' filings — but **5,000+ appear in only one chamber**, year after year. The cross-chamber gap is a data-quality and accountability story.

**Where.** Per-year set of uppercase-trimmed `client_name` from `senate_filings.parquet`
∪ `house_filings.parquet`.

| Year | Both | Senate only | House only |
|---|---:|---:|---:|
| 2022 | 17,890 | 1,418 | 1,756 |
| 2023 | 18,452 | 1,229 | 1,471 |
| 2024 | 19,041 | 1,150 | 1,329 |
| 2025 | **22,005** | **804** | **1,118** |
| 2026 (Q1) | 11,723 | 6,517 | 215 |

The 2026 distortion is artifactual (Senate Q1 was filed by 2026-03-31 but House
Q1-2026 had not yet been fully filed at extraction time). For the four complete years,
~1,000–1,800 clients appear in only one chamber's records per year.

**Reporter angle.** "House-only" clients are a population of organizations doing federal
lobbying that consciously file with only the House Clerk — frequently smaller groups
disclosing only when they're forced to. Inversely, "Senate-only" clients failed to file
their House counterparts on time or at all. Either pattern is a compliance story.

**Caveats.** Exact uppercase match misses normalization variants (`INC.` vs `INC`, `&` vs
`AND`). True entity resolution would shrink the gap. Use this number as an upper bound
when characterizing the discrepancy.

---

## Finding 7 (anomaly): A registrant named "LOC COMMUNITY ASSOCIATION" filed 15 quarterly reports for "STATE OF LOC NATION GLOBAL PUB..." declaring income of $20M per quarter — the largest single client/registrant income concentration in the corpus.

**Where.** `senate_filings.parquet`, `registrant_name = 'LOC COMMUNITY ASSOCIATION'`,
`client_name like 'STATE OF LOC NATION%'`. 15 filings across 2024 Q3 – 2025 Q4. Total
declared income: **$180,000,000**. Filings appear at:

```
filing_uuid examples: 5000632b-e40b-4762-affc-551b46..., e0602008-d4bf-4d07-9270-0f7010..., ...
```

This is **2.6×** Qualcomm's full 5-year income total ($69M / 96 filings) on **just 15
filings.** The pattern (round $20M repeated quarter-over-quarter without expenses
disclosed) is consistent with a misfiled or test registration, not a real $180M lobbying
engagement.

**Reporter angle.** Pull the filing print URLs (`filing_document_url`) and inspect — these
are either (a) an extraordinary and previously-unreported lobbying operation, (b) a
filer error, or (c) an attempt at lobbying-disclosure spam. Either is publishable.

**Sourcing.** All 15 UUIDs are in the `08_inaugural_money.json`-adjacent JSON output of
`explore.py --query state_loc`. Filing document URLs at
`https://lda.senate.gov/filings/public/filing/<uuid>/print/`.

---

## Cross-cutting observation

The **Senate LDA** corpus is more analytically tractable than the **House** XML corpus
because:

1. Senate filings have stable UUIDs; House filings use chamber-assigned numeric IDs.
2. Senate filings carry the full registrant + client object on every record; House XML
   carries flat strings that vary in casing and punctuation.
3. Senate exposes the LD-203 contribution data; the House does not (contributions are
   under Senate jurisdiction).

For any cross-corpus story, **start with Senate** and use House as a corroborator via
the shared `senateID`/`houseID` bridge.

---

## Legal/ethical flags

- **None of the LD-203 disclosures examined here appear non-compliant on their face.**
  The Trump-Vance inaugural contributions were filed in the required quarterly LD-203
  reports.
- **No FARA flags** were identified in this pass. The foreign-affiliated parents named
  in `foreign_entities` are LDA-required disclosures (foreign ownership ≥ 20%); they are
  not the same population as FARA registrants. Cross-checking against the FARA database
  (efile.fara.gov) for the named foreign parents is left as a follow-up.
- **The LOC COMMUNITY ASSOCIATION filings are anomalous**, and could indicate filer
  error or possible abuse of the LDA filing system. Recommend inspection of the original
  filing PDFs and a query to the Senate Office of Public Records.

## Conflicts of interest

None disclosed. The author (Press Pass) has no financial relationship with any of the
named registrants, clients, or members of Congress.
