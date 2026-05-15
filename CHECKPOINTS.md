# Beirut workspace — checkpoints

Working branch: `spmartin823/beirut`. Update this file every meaningful step so a fresh agent can pick up after a context compaction.

## How to resume

```bash
cd /Users/SeamusMartin1/conductor/workspaces/journalism-skills/beirut
git checkout spmartin823/beirut

# 1. (one-time) Get the data zip and decompress
bash skills/lda-setup/scripts/fetch_data.sh

# 2. (one-time, ~2 min) Build the investigation DB
bash skills/lda-setup/scripts/build.sh

# 3. Build derived tables (revolving door + bill mentions, ~45 sec total)
python3 skills/lda-revolving-door/scripts/extract_members.py
python3 skills/lda-say-vs-pay/scripts/extract_bill_mentions.py

# 4. Render charts
python3 skills/lda-chart/scripts/chart_revolving_door.py
python3 skills/lda-chart/scripts/chart_foreign_issues.py
python3 skills/lda-chart/scripts/chart_say_vs_pay.py
python3 skills/lda-chart/scripts/chart_top_clients.py

# 5. Check investigation state
python3 skills/lda-investigation-state/scripts/lead.py list
```

Data zip + decompressed `data/` live in `.context/data/` (gitignored, ~10 GB total). The DuckDB file is also gitignored.

## Tables in `.context/db/investigation.duckdb`

| table | rows | what |
|---|---:|---|
| press | 141,332 | Congress press releases 2022-01 → 2026-03 |
| press_member | 536 | distinct members of Congress in press corpus |
| senate_filing | 418,170 | LDA filings (Senate side) |
| senate_activity | 799,192 | one row per lobbying activity in a Senate filing |
| senate_lobbyist | 2,121,863 | lobbyists named on Senate activities (incl. covered_position) |
| senate_govt_entity | 2,016,363 | government entities targeted |
| senate_foreign_entity | 3,627 | foreign entities tied to Senate filings |
| senate_contrib_report | 155,689 | LD-203 contribution reports |
| senate_contrib_pac | 22,379 | PACs named in contribution reports |
| senate_contrib_item | 636,833 | itemized contributions |
| house_filing | 409,640 | LD-1 / LD-2 House filings |
| house_activity | 785,026 | activities on House filings |
| house_lobbyist | 1,962,951 | lobbyists on House activities |
| house_foreign | 47,983 | foreign entities tied to House registrations |
| revolving_door | 330,051 | (lobbyist, former Member boss) pairs — built by `lda-revolving-door` |
| bill_mentions_lobby | ≈730K | (Senate filing_uuid, bill_id) — built by `lda-say-vs-pay` |
| bill_mentions_lobby_house | ≈730K | (House filing_id, bill_id) |
| bill_mentions_press | 18,127 | (press url, bill_id) |

## Findings (see `research/FINDINGS.md`)

1. **Revolving door** — 20 members have ≥14 distinct active ex-staff lobbyists 2024+. John Cornyn and Patty Murray top the list with 20 each.
2. **Foreign influence** — Country × policy-issue map: Australia/Defense (AUKUS), China/Trade, Israel/Defense.
3. **Say vs Pay** — HR3684 (Infrastructure Law) has 9,056 lobby filings, 13 press mentions. Many marquee laws follow the same pattern post-enactment.
4. **Top spenders** — Tech + Pharma dominate; year-over-year cadence remarkably stable.

Appendix A: Single self-filer reporting $20M/quarter as "Head of State Black USA" — open data-quality lead.

## Charts produced

- `research/charts/01_revolving_door_top_members.png` + `.svg` + `_provenance.md`
- `research/charts/02_foreign_principal_issues.png` + `.svg` + `_provenance.md`
- `research/charts/03_say_vs_pay.png` + `.svg` + `_provenance.md`
- `research/charts/04_top_clients.png` + `.svg` + `_provenance.md`

## Status log

- 2026-05-15 — Pipeline built (press + Senate + House loaded into DuckDB)
- 2026-05-15 — Eval frameworks captured in `research/eval_frameworks.md`
- 2026-05-15 — `revolving_door` materialized (330K pairs)
- 2026-05-15 — Chart 1 (revolving door) published
- 2026-05-15 — `bill_mentions_*` materialized
- 2026-05-15 — Charts 2 (foreign), 3 (say-vs-pay), 4 (top clients) published
- 2026-05-15 — `investigation_state` skill + 3 open leads + 3 entities seeded
- 2026-05-15 — FINDINGS.md, README updated, branch pushed

## Open (would do next)

- `lda-entity-resolve` — Normalize/dedupe organization+client names across House+Senate. Triple-counting of PhRMA is the canonical case.
- Bill-name extractor — Press releases mention bills by name ("Inflation Reduction Act") more than by number. Building a name → bill_id map (Congress.gov API) would close the say-vs-pay gap further.
- FEC join — Validate LD-203 contributions against FEC filings.
- Member committee enrichment — Pull committee assignments for each member; map "former staffer → former boss's current committee → industries lobbying that committee".
