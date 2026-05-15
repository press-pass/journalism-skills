# Florence-v1 progress checkpoint

Branch: `florence-v1`. Workspace: `/Users/SeamusMartin1/conductor/workspaces/journalism-skills/florence-v1`.

## State: shipped

The submission map is in `SUBMISSION_README.md`. Findings in `FINDINGS.md`.

## Skills (all under `skills/`)
1. **lda-corpus-query** — DuckDB views over indexed Parquet corpus
2. **lda-press-bridge** — cross-corpus member snapshot tool
3. **inaugural-contribution-trace** — audit-trail tool for LD-203 contributions
4. **revolving-door-extractor** — parses 1.1M `covered_position` strings
5. **chart-quality-review** — scores charts against external rubrics

## Pipeline scripts
- `analysis/pipeline/01_index_press.py` — JSONL → Parquet
- `analysis/pipeline/02_index_senate.py` — JSON → Parquet (year-partitioned, 7 tables)
- `analysis/pipeline/03_index_house.py` — XML → Parquet (4 tables, parallelized)
- `analysis/pipeline/eda_basics.py`, `eda_drilldown.py` — initial EDA
- `analysis/tools/views.py`, `query.py`, `dbshell.py` — SQL CLI
- `analysis/tools/bridge_member.py` — member snapshot bridge
- `analysis/tools/contribution_trace.py` — contribution audit-trail
- `analysis/tools/revolving_door.py` — revolving-door parser
- `analysis/tools/chart_review.py` — chart QA

## Charts (all in `analysis/charts/output/`)
1. **01_inaugural_donors** — 30 lobbying-active corporations gave $18.05M to 2025 Trump-Vance Inaugural
2. **02_lobbying_surge** — quarterly $ from 2022 Q1 to 2026 Q1, 22% growth
3. **03_tax_havens** — top 25 disclosed foreign-parent countries, havens highlighted
4. **04_revolving_door** — committee-level K-Street pipeline (8,586 ex-staffers)
5. **05_crypto_bridge** — crypto LDA activities vs press releases over time

## Data state
- Raw data: `.context/data/Agentic Investigation Datasets/extracted/data/` (8.6 GB, gitignored)
- Indexed Parquet: `.context/parquet/` (gitignored)
  - `press/year=YYYY/*.parquet` — 141,332 press releases
  - `senate/{filings,activities,lobbyists,gov_entities,foreign_entities,contrib_reports,contrib_items}/year=YYYY/*.parquet`
  - `senate/constants/*.parquet`
  - `house/{filings,lobbyists,issues,agencies}/*.parquet`
  - `revolving_door.parquet`

## How to re-enter the workspace
```bash
cd /Users/SeamusMartin1/conductor/workspaces/journalism-skills/florence-v1
docker compose -f analysis/docker/docker-compose.yml up -d
docker compose -f analysis/docker/docker-compose.yml exec florence bash
```

## What to do next (if more time)
- Add a 6th chart on say-vs-pay for non-crypto topics
- Build `analysis/tools/bridge_press.py` (Mode B of lda-press-bridge —
  press-release-to-entity overlap)
- Run `chart-quality-review` with a vision-language model in the loop
- Verify a sample of the contributor names via cross-reference with FEC
