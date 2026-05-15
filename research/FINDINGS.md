# Findings — GAIN agentic investigation challenge

Investigation timeline: 2026-05-15 (single sprint).
Corpus: Senate LDA filings (2022-2026 Q1), House LDA filings, Congressional press releases (thescoop.org/congress-press).
Reproducer: `skills/lda-setup/scripts/build.sh` then each downstream skill.

Each claim below is anchored to specific filing UUIDs or press URLs visible in the chart provenance files.

---

## Finding 1 — Twenty members of Congress account for the densest revolving doors on K Street

**The number.** Across active Senate-LDA lobbyists who filed in 2024-Q1 through 2026-Q1, twenty current/former members of Congress each have **at least 14 distinct ex-aides** registered as paid lobbyists. The top two — John Cornyn (R-TX) and Patty Murray (D-WA) — each placed 20 former staffers into the lobbying corps.

**Where it lives.** Free-text `covered_position` field of `senate_lobbyist`. The LDA requires every lobbyist to disclose past federal-government roles in plain English; we parse 575,118 such strings against the unitedstates.io legislator roster.

**Why it's newsworthy.** Not the existence of the revolving door (well-known), but its quantification: a small set of offices function as recurring talent pipelines into the lobbying industry. For each member, our `revolving_door` table lets a journalist enumerate the actual people and their current clients.

**Evidence.**
- Chart: `research/charts/01_revolving_door_top_members.png`
- Per-bar provenance with filing UUIDs: `research/charts/01_revolving_door_provenance.md`
- Spot check: filing `4f33e46d-4018-4899-8926-c03bb9977ae2` (one of many) shows a former McConnell legislative aide now lobbying for clients on defense.

**Caveats.** Precision > recall. Lobbyists who omitted prior Hill roles, used ambiguous phrasing, or worked for pre-2000 members aren't captured. Our denominator is *Senate-LDA* covered positions; the House column carries similar text but is largely redundant for the same lobbyist universe.

---

## Finding 2 — Foreign-tied lobbying has a distinct policy signature per country

**The number.** Senate LDA `foreign_entities` fields tie 3,627 filings to non-US owners. Joined to lobbying activity, the issue mix is sharply country-specific:

| Country | Top issue | Filings |
|---|---|---:|
| Australia | **Defense** | 265 |
| UK | Taxation / Internal Revenue Code | 57 |
| Korea | Trade (domestic/foreign) | 60 |
| Japan | Trade | 33 |
| Germany | Trade | 29 |
| China | Trade | 44 |
| Israel | Defense | 28 |

Australia's defense dominance — 265 filings versus its 4th-place overall filing count — is the AUKUS pact in plain numbers.

**Where it lives.** `senate_foreign_entity` × `senate_activity`.

**Why it's newsworthy.** The country-by-country issue map is the kind of structured view that takes a desk-research analyst weeks; we render it in ~3 seconds from the materialized DB. A defense reporter looking for the Australian-tied filings now has a direct query to run.

**Evidence.**
- Chart: `research/charts/02_foreign_principal_issues.png`
- Spot-check filings per high-traffic cell: `research/charts/02_foreign_principal_provenance.md`

**Caveats.** Country codes mix ISO-2 (Senate) and FIPS-3 (House). Filings disclose foreign *ownership* of the client; they do not disclose that a foreign government directed the lobbying — a separate FARA filing would be required for that.

---

## Finding 3 — Some marquee laws are heavily lobbied in near-silence

**The number.** Of 25 bills with ≥1,000 combined House+Senate lobbying filings, two-thirds had **fewer than 100 press-release mentions** from members of Congress. The signature case: **HR 3684, the Bipartisan Infrastructure Law**, sits at 9,056 lobby filings but only 13 press releases from 6 distinct members during 2022-2026 Q1. The Inflation Reduction Act (HR 5376) follows the same pattern at a larger scale: 20,781 lobby filings, 53 press mentions across 43 members.

**Where it lives.** `bill_mentions_lobby` (Senate) + `bill_mentions_lobby_house` (House) + `bill_mentions_press` (member press releases). All three are materialized by `skills/lda-say-vs-pay/scripts/extract_bill_mentions.py`.

**Why it's newsworthy.** This is the cleanest "say vs pay" signal in the corpus: bills become law, then disappear from Congressional press cycles while implementation lobbying explodes. The structure of the asymmetry suggests that members' communications priorities track campaign salience more than constituent stakes. HR 1 (the marquee bill of the current Congress) is the green dot at the top right of Chart 3 — the only one where talking and lobbying are roughly proportional.

**Evidence.**
- Chart: `research/charts/03_say_vs_pay.png`
- Table of every labeled bill: `research/charts/03_say_vs_pay_provenance.md`
- Sample evidence for HR 3684 silent lobbying in 2025: 5 filing UUIDs in the provenance file.

**Caveats.** Press authors use bill *names* ("Inflation Reduction Act") more often than numbers. Our extractor measures the bill-number footprint specifically; the title-mention footprint would partially offset but not, on inspection, close the gap for HR 3684.

---

## Finding 4 — The top corporate spenders are dominated by Big Tech and Big Pharma; year-over-year cadence is remarkably stable

**The number.** Top 20 Senate LDA clients 2022-2025 by reported income spans **$8.4M to $22.2M** cumulative. Tech (Qualcomm, Microsoft, Comcast, Oracle, Meta, Apple, T-Mobile) and pharma (PhRMA, Gilead, Illumina) own 14 of 20 slots. AIPAC at $12.9M is the highest-grossing **foreign-policy advocacy** client.

Year-on-year quarter-by-quarter cadence is unusually flat: most top clients vary their reported spend by ≤15% across years. The standout exception is Illumina, which crashed from $5.97M in 2022 to $0.785M in 2025 (post-acquisition-of-Grail unwinding).

**Where it lives.** `senate_filing` with `filing_type LIKE 'Q_'`. We exclude single-quarter filings with income > $5M (a small set of self-filed outliers; see Appendix A).

**Why it's newsworthy.** Not the rank order (mostly public already) but the **stability** — paid lobbying spend looks more like a fixed overhead expense than a reactive campaign budget. That has implications for how to think about the lobbying market as a whole.

**Evidence.**
- Chart: `research/charts/04_top_clients.png`
- Provenance + spot checks: `research/charts/04_top_clients_provenance.md`

**Caveats.** Income is self-reported in $10,000 increments above $5,000. PhRMA appears in our top-20 *three times* — as "PHARMACEUTICAL RESEARCH AND MANUFACTURERS OF AMERICA", "PHARMACEUTICAL RESEARCH AND MANUFACTURERS OF AMERICA (PHRMA)", and "PHRMA". That triple entry is itself a known entity-resolution gap (TODO: build `lda-entity-resolve`).

---

## Appendix A — Data quality lead: STATE OF LOC NATION self-filed outlier

A single filer, **Christina Clement**, has submitted **fifteen Senate-LDA filings** since 2024-Q3 under registrant "LOC COMMUNITY ASSOCIATION" for client "STATE OF LOC NATION GLOBAL PUBLIC BENEFIT CORPORATION", reporting $20,000,000 in quarterly income on most. Covered-position text on her filings claims she is "President of Black USA and 2024 Presidential Candidate", "Head of State Black USA", and "Global Plenary Power". Lobbying activities cite "HR 40 and S 40" (reparations).

These filings distort top-spender lists for 2025 — when included, this single individual ranks #1 nationally at ~$60M annual income, 13× the next-largest client. We exclude income outliers > $5M/quarter from Chart 4.

Filings:
- `5000632b-e40b-4762-affc-551b46a40c91` (2024-Q3 registration, income null)
- `4d5b1cb0-0971-43b8-958b-d260e2be8af1` (2025-Q1 amendment, $20,000,000)
- `c2d195d2-8df2-4b75-8e95-7014cacd5e81` (2025-Q2, $20,000,000) — amended four more times
- `d60611b7-466e-46bd-aa78-110030874e67` (2026-Q1 amendment, $20,000,000)
- (and 10 more — query `senate_filing` where `client_name = 'STATE OF LOC NATION GLOBAL PUBLIC BENEFIT CORPORATION'`)

**Lead:** What is the Senate LDA office's verification process for declared income? A FOIA request to the Office of Public Records would be the next step. Tracked as open lead in `research/investigation_state.json`.

---

## Skills delivered

| Skill | Investigation Organization | Corpus Efficiency | Human Verifiability | Extended Capabilities |
|---|:-:|:-:|:-:|:-:|
| `lda-setup` | — | ★★★ | — | ★ |
| `lda-revolving-door` | — | ★★★ | ★★★ | ★★★ |
| `lda-say-vs-pay` | — | ★★★ | ★★★ | ★★★ |
| `lda-foreign-influence` | — | ★★ | ★★ | ★★ |
| `lda-chart` | — | ★★ | ★★★ | ★★ |
| `lda-investigation-state` | ★★★ | — | ★★ | ★★ |

All skills are reproducible (every script is deterministic; agents re-running them get identical output).

## Open leads (live in `investigation_state.json`)

1. Silent lobbying: HR3684 (Bipartisan Infrastructure Law) — 9,056 lobby filings vs 13 press mentions
2. Australia AUKUS lobby spike — 265 Senate filings on Defense by Australian-tied clients
3. STATE OF LOC NATION self-filed $20M/Q outlier — single individual, 15 amended filings

## Significant entities

- John Cornyn (R-TX, C001056) — 20 distinct former staffers active as lobbyists 2024+
- Patty Murray (D-WA, M001111) — 20 distinct former staffers active as lobbyists 2024+
- Mitch McConnell (R-KY, M000355) — 17 distinct former staffers active as lobbyists 2024+
- Christina Clement — self-filed registrant; 15 amended filings as "Head of State Black USA"
- HR 5376 / Inflation Reduction Act — 20,781 lobby filings, just 53 press mentions

## Conflicts of interest

None to declare. The investigator (Seamus Martin / PressPass) has no financial relationship with any of the named entities. PressPass is an independent journalism-skills toolkit project.

## Potential legal violations

This corpus is built from public records; we make no legal claim against any party. The data-quality outlier (Appendix A) raises questions about LDA verification practice but does not, on its face, establish a violation.
