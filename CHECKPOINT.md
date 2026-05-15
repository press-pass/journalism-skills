# Florence-v1 progress checkpoint

Branch: `florence-v1`. Workspace: `/Users/SeamusMartin1/conductor/workspaces/journalism-skills/florence-v1`.

## What's done
1. **Rubric pinned** — `analysis/EVAL_RUBRIC.md`. Five external rubrics (Kirk, Few, Evergreen, Penn State, Munzner) + two runnable LLM evaluators (Microsoft VisEval, LIDA SEVQ).
2. **Data downloaded + extracted** — `.context/data/Agentic Investigation Datasets/extracted/data/`. 8.6 GB of press releases, Senate JSON, House XML covering 2022-01 → 2026-03.
3. **Docker environment built** — `analysis/docker/`. `florence-analysis:latest` runs with `docker compose -f analysis/docker/docker-compose.yml exec florence ...`. Mounts data read-only at `/data`, writes Parquet to `/parquet`.
4. **Indexed all three corpora to Parquet** — outputs in `.context/parquet/`:
   - `press/year=YYYY/*.parquet` — 141,332 press releases across 536 members
   - `senate/filings/year=YYYY/data.parquet` — 418,170 LDA filings
   - `senate/activities/year=YYYY/data.parquet` — 799,192 issue-line activities
   - `senate/lobbyists/year=YYYY/data.parquet` — 2,121,863 lobbyist appearances
   - `senate/gov_entities/year=YYYY/data.parquet` — 2,016,363 gov-entity-lobbied rows
   - `senate/foreign_entities/year=YYYY/data.parquet` — 3,627 foreign-entity rows
   - `senate/contrib_reports/year=YYYY/data.parquet` — 155,689 reports
   - `senate/contrib_items/year=YYYY/data.parquet` — 636,833 contribution line items
   - `senate/constants/*.parquet` — 8 lookup tables
   - `house/filings/*.parquet` — 405,650 LD-1/LD-2 filings parsed
   - `house/lobbyists/*.parquet` — ~1.9M lobbyist appearances
   - `house/issues/*.parquet` — ~745k issue rows w/ specific_issues text
   - `house/agencies/*.parquet` — ~1.96M federal-agency-lobbied rows

## Next
- EDA to find chart angles
- Build skills (`skills/lobbying-corpus-query`, `skills/entity-bridge-lda-press`, `skills/chart-quality-review`)
- Build final charts
- Findings report + README map

## How to re-enter the workspace
```bash
cd /Users/SeamusMartin1/conductor/workspaces/journalism-skills/florence-v1
docker compose -f analysis/docker/docker-compose.yml up -d
docker compose -f analysis/docker/docker-compose.yml exec florence bash
# Parquet is at /parquet inside the container
```
