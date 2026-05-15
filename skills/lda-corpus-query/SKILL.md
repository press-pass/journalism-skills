---
description: Query the indexed Senate + House LDA + congressional press corpus via DuckDB SQL. Every result includes the filing_uuids/urls so claims are reproducible. Pushes filtering, aggregation, and text search down to deterministic SQL so the agent's main context stays focused on reasoning.
---

You will be given a question to answer against the LDA + congressional press
corpus. The corpus lives in DuckDB-readable Parquet files under
`/parquet/` inside the analysis container, indexed from the public source data
described in `analysis/EVAL_RUBRIC.md`'s sibling `data_manual.md`.

## When to use this skill

Use this skill whenever an answer requires aggregating, filtering, or joining
across:
- Congressional press releases (`/parquet/press/`)
- Senate LDA filings (`/parquet/senate/filings/`)
- Senate LDA lobbying activities (`/parquet/senate/activities/`)
- Senate LDA lobbyists (`/parquet/senate/lobbyists/`)
- Senate LDA government-entities-lobbied (`/parquet/senate/gov_entities/`)
- Senate LDA foreign entities (`/parquet/senate/foreign_entities/`)
- Senate LD-203 contribution items (`/parquet/senate/contrib_items/`)
- Senate LD-203 contribution reports (`/parquet/senate/contrib_reports/`)
- House LD-1/LD-2 filings (`/parquet/house/filings/`)
- House LD-2 lobbyist rows (`/parquet/house/lobbyists/`)
- House LD-2 issue rows (`/parquet/house/issues/`)
- House LD-2 federal-agency rows (`/parquet/house/agencies/`)
- Lookup constants (`/parquet/senate/constants/*.parquet`)

Do **not** load full JSON/XML in the agent's context — always write SQL.

## How to run

1. Make sure the Docker analysis service is up:
   ```bash
   docker compose -f analysis/docker/docker-compose.yml up -d
   ```
2. Open a SQL shell inside the container:
   ```bash
   docker compose -f analysis/docker/docker-compose.yml exec florence \
       python -m analysis.tools.dbshell
   ```
   Or run a one-off query:
   ```bash
   docker compose -f analysis/docker/docker-compose.yml exec florence \
       python analysis/tools/query.py --sql "SELECT COUNT(*) FROM press"
   ```

The two helper scripts above wire up views over every Parquet directory so
queries can use friendly names (`press`, `sen_filings`, `house_issues`, etc.)
without restating glob patterns.

## Output requirements (verifiability)

Every claim derived from this corpus must end with at minimum **one identifier
or URL** that a reviewer can paste into the relevant disclosure portal:

- For Senate LDA filings: include the `filing_uuid` AND the `url` column from
  `sen_filings`. The `url` is the public LDA URL.
- For Senate contribution items: include `filing_uuid` + `contribution_date`
  + `amount` + `payee_name` + `honoree_name`.
- For House filings: include `filing_id` (the XML filename stem) + the
  directory (e.g., `2025_1stQuarter_XML`). Public URL pattern is
  `https://disclosurespreview.house.gov/?id={filing_id}`.
- For press releases: include `url` + `date` + `bioguide_id`.

If a query returns aggregates without IDs, run a second query that pulls **at
least three concrete underlying records** so the editor can spot-check.

## Standard view names (already created by `analysis/tools/query.py`)

| View | Source path |
|---|---|
| `press` | `press/year=*/*.parquet` |
| `sen_filings` | `senate/filings/year=*/*.parquet` |
| `sen_activities` | `senate/activities/year=*/*.parquet` |
| `sen_lobbyists` | `senate/lobbyists/year=*/*.parquet` |
| `sen_gov_entities` | `senate/gov_entities/year=*/*.parquet` |
| `sen_foreign_entities` | `senate/foreign_entities/year=*/*.parquet` |
| `sen_contrib_items` | `senate/contrib_items/year=*/*.parquet` |
| `sen_contrib_reports` | `senate/contrib_reports/year=*/*.parquet` |
| `house_filings` | `house/filings/*.parquet` |
| `house_lobbyists` | `house/lobbyists/*.parquet` |
| `house_issues` | `house/issues/*.parquet` |
| `house_agencies` | `house/agencies/*.parquet` |
| `issue_codes` | `senate/constants/lobbying_activity_issues.parquet` |
| `gov_entities_catalog` | `senate/constants/government_entities.parquet` |
| `filing_types` | `senate/constants/filing_types.parquet` |
| `countries_catalog` | `senate/constants/countries.parquet` |

## Common recipes

### Top spenders by client (Q-reports only, dollar-weighted)
```sql
SELECT client_name, COUNT(*) AS n_filings, ROUND(SUM(income),0) AS total_income
FROM sen_filings
WHERE filing_type LIKE 'Q%' AND income IS NOT NULL
GROUP BY 1 ORDER BY total_income DESC LIMIT 25;
```

### Cross-corpus: a member's press output AND who lobbied them
```sql
WITH m AS (
  SELECT bioguide_id, MIN(member_name) AS member, MIN(state) AS state,
         MIN(chamber) AS chamber, MIN(party) AS party
  FROM press WHERE bioguide_id = :bioguide GROUP BY 1
)
SELECT m.member, m.chamber, COUNT(p.url) AS press_count
FROM m LEFT JOIN press p USING (bioguide_id);
```

### Press-release text search with bounded LIMIT
Always cap text searches at LIMIT 500 and pull only the columns needed; never
SELECT *.

```sql
SELECT url, date, member_name, party, state, title
FROM press
WHERE text ILIKE '%cryptocurrency%' AND year >= 2024
ORDER BY date DESC
LIMIT 200;
```

## Failure modes to flag

- **The "STATE OF LOC NATION GLOBAL PUBLIC BENEFIT CORPORAT" $180M row.** A
  single client showing 15 filings totaling $180M of income is almost
  certainly a parsing artifact (a Live Nation termination/amendment block).
  Always check `filing_type` before reporting.
- **Duplicate filings.** LDA amendments produce multiple rows for the same
  underlying period. Use `filing_type LIKE 'Q%'` and de-duplicate on
  `(client_id, registrant_id, filing_year, filing_period)` before summing
  income.
- **Member name collisions.** Two members named "Mike Collins" (R-GA, R-ME)
  share text in the press corpus. Always pin to `bioguide_id`.
- **Senate ↔ House same engagement.** The same client-registrant
  engagement appears in both `sen_filings` and `house_filings`. Join on
  `senateID` (House field) ↔ `senateID` (Senate UUID) before summing
  dollars across chambers.
