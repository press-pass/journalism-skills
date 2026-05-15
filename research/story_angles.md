# Story angle brainstorm

Each angle bundles: (1) a reusable skill, (2) a deterministic SQL recipe, (3) a candidate chart, (4) traceable source records.

## A1 — Revolving-door network (PICK)
**Claim:** Of all active lobbyists today, a measurable share previously held senior staff jobs for the very lawmakers their current clients want to influence.
**Skill:** `revolving-door` — parses `covered_position` text, normalizes to Member bioguide, builds `lobbyist → former_boss` table.
**Chart:** Sankey or top-N bar: top 20 former chiefs-of-staff now lobbying; for each, current client roster and issue.
**Trace:** Senate filing_uuids + lobbyist_id where covered_position matched.

## A2 — Say-vs-Pay (PICK)
**Claim:** Per-member, the topic mix in press releases diverges measurably from the lobbying-issue intensity targeting their chamber & committees.
**Skill:** `say-vs-pay` — joins press topic keywords to ALI issue codes via a kw→ALI lookup, computes member-level cosine distance.
**Chart:** Scatter: x = Σ press_releases on issue, y = Σ lobby_filings touching member's committee on issue, point=member.
**Trace:** Press URLs + senate_filing UUIDs that fed each bucket.

## A3 — Foreign principal map (PICK)
**Claim:** Country mix of foreign-tied lobbying shifts year-over-year. E.g., growth/decline of Chinese-tied filings 2022→2026.
**Skill:** `foreign-lobby` — builds country×year×issue panel from `senate_foreign_entity` + `house_foreign`, joins to filing income.
**Chart:** Small-multiples heatmap: country (top 15) × year, cell = filings, color = $ income.
**Trace:** All foreign_entity rows + parent filings.

## A4 — Amendment storms
**Claim:** Some filings are revised multiple times; amendment density correlates with politically contested matters.
**Skill:** `amendment-storm` — groups filings by (registrant, client, year, period) and counts amendments; flags top.
**Chart:** Top 10 most-amended filings, with bar showing # amendments + final income.

## A5 — Single-filer outliers (DATA QUALITY APPENDIX)
**Claim:** A handful of self-filed registrants distort top-spender lists because LDA permits self-reported income with no apparent verification.
**Skill:** `outlier-flag` — z-score income filings against issue/year peers.
**Chart:** Bar of top 5 outliers with side-by-side legitimate-peer median.
**Lead:** "STATE OF LOC NATION GLOBAL PUBLIC BENEFIT CORPORATION" reporting $20M/quarter (single individual "Rev Dr Christina Clement").

## Cross-cutting skills

- `investigation-state` — checklist/leads file persisted to disk; agents read before starting.
- `lda-entity-resolve` — normalize org/client names across House+Senate; resolve bioguide → state/chamber/committee.
- `chart-from-finding` — given (claim, SQL, columns, source_ids), render a publication chart + caption + provenance.
- `lda-query` — wraps duckdb with named query templates (top-N, time-series, joins). Cuts agent tokens spent on SQL.

## Outside data (open, public)

- Congress.gov bioguide member metadata (states, committee assignments)
- House Clerk member-committee assignment XML
- FEC contribution data — to validate LD-203 contribution flows

## Charts I will actually produce (final cut)

1. Foreign-tied lobbying by country, 2022→2026 (small multiples / heatmap)
2. Top revolving-door lobbyists (former Member staffers) by current client (annotated bar)
3. Say-vs-Pay scatter for top-100 press members vs lobbying-issue intensity
4. Amendment-storm bar
5. Optional outlier-flag appendix
