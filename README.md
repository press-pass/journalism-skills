# journalism-skills — GAIN Agentic Investigation Challenge submission (belo-horizonte-v1)

Agentic skills for investigative journalism, plus a worked submission to the
[GAIN Agentic Investigation Challenge](https://www.gain-agent-challenge.northwestern.edu/details/).

The corpus the challenge ships (Senate + House LDA filings and Congressional
press releases, 2022 – 2026 Q1) is large and structurally heterogeneous. The
investigation strategy in this branch:

1. **Push the heavy lifting to deterministic tools.** A single
   `lobbying-corpus-ingest` skill turns 8.6 GB of raw JSON + XML + JSONL into
   a queryable DuckDB database in ~80 seconds via PyArrow bulk-load. All
   downstream skills query that DB instead of re-parsing the corpus.
2. **Keep every claim sourced.** Every analytic row carries its original
   `filing_uuid`, House XML `house_file`, or press-release `url` so an
   evaluator can audit any finding by pulling the original public record.
3. **Compose narrow, re-runnable skills.** Eight new skills, each with one
   job — ingest, entity resolution, anomaly detection, bill extraction,
   covered-position parsing, press↔lobbying joins, foreign-influence tagging,
   chart rendering. A single `run_pipeline.sh` glues them together.

## Install as a Claude Code plugin

```bash
claude plugin install journalism-skills@jskills
```

## GAIN deliverables

| Deliverable | Location |
|---|---|
| **Agent skills** | [`skills/`](./skills/) — see *Skills index* below |
| **Findings report** | [`FINDINGS.md`](./FINDINGS.md) |
| **Interaction traces** | `.context/traces/` (gitignored — see *Reproducing the run* below) |
| **README** (this file) | links every skill → finding → trace |

## Skills index — GAIN submission

| Skill | What it does |
|---|---|
| [`lobbying-corpus-ingest`](skills/lobbying-corpus-ingest) | Parse Senate JSON, House XML, press JSONL → normalized DuckDB |
| [`lobbying-entity-resolve`](skills/lobbying-entity-resolve) | Bridge Senate `registrant_id` / `client_id` to House `senateID`, plus name aliases |
| [`lobbying-issue-spike`](skills/lobbying-issue-spike) | Quarter-over-quarter spike detection by ALI issue / client / registrant |
| [`lobbying-bill-extract`](skills/lobbying-bill-extract) | Regex bills (H.R., S., resolutions, public laws) out of lobbying descriptions + press releases |
| [`lobbying-revolving-door`](skills/lobbying-revolving-door) | Parse free-text `covered_position` into structured prior-role rows |
| [`lobbying-press-link`](skills/lobbying-press-link) | Deterministic press-release ↔ lobbying-filing joins (name + bill_id + quarter) |
| [`lobbying-foreign-influence`](skills/lobbying-foreign-influence) | Tag foreign-funded lobbying via `client.country` + foreign-entity disclosures |
| [`lobbying-chart`](skills/lobbying-chart) | Render newsroom-quality charts from CSV with source-line footer + `.meta.json` audit sidecar |

Plus the existing journalism skills (`generate-story-leads`,
`trusted-source-discovery`, `verify-email`, `find-photo-evidence`,
`answer-questions`, etc.) preserved from `main`.

## Reproducing the run

Requirements: Python ≥ 3.11, DuckDB CLI ≥ 1.5, `duckdb`, `pyarrow`, `pandas`,
`matplotlib` Python packages.

```bash
# 1. Decompress the GAIN corpus into data/ (matches data_manual.md layout)
unzip data.zip -d data_root/

# 2. Build the DuckDB database (~80s on an 8-core M-series mac)
python3 skills/lobbying-corpus-ingest/scripts/build_db.py \
  --data-root data_root/data --db lobbying.duckdb --workers 8

# 3. Run the full analysis pipeline
DB=lobbying.duckdb OUT=findings bash .context/findings/run_pipeline.sh

# 4. Materialize finding CSVs and charts
duckdb lobbying.duckdb < .context/findings/queries.sql
bash .context/charts/make_charts.sh
```

Every script is idempotent: re-running drops and rebuilds the tables it owns.

## External data sources used

This run uses only the GAIN corpus plus the publicly documented LDA filing
codes (`data/senate/constants/*.json`) bundled with the corpus. No other
external data is queried during the run. The finding write-ups link out to
`lda.senate.gov` and `disclosurespreview.house.gov` for verification only.

## Conflicts of interest

None. The author has no current employer or consulting relationship with any
lobbying client, registrant, or member of Congress represented in the corpus.

## Legal / ethical notes

All data used is public-record: LDA filings published under 2 U.S.C. §§ 1603,
1604 and member press releases on official `*.house.gov` / `*.senate.gov`
pages. No login, paywall, or scraped private content. Findings flag self-
reported data quality issues (null / rounded incomes, name inconsistencies)
rather than presenting them as ground truth.

---

## Original journalism-skills (preserved from `main`)

Skills are namespaced under `journalism-skills`:

```
/journalism-skills:new-skill
```

### Skill output

All skill output is written to `skills/<skill-name>/skill-output/<skill-name>/<YYYY-MM-DD_HH-MM-SS>/` within the journalism-skills directory. This directory is gitignored.

### Development

Skills are cached when installed. Editing skill files won't take effect until you reinstall the plugin. From within a Claude session:

```
/plugin install journalism-skills@jskills
```

Note: `/reload-plugins` only reloads already-cached plugins — it won't pick up source file changes. You need to reinstall.

### Available skills

- **answer-questions** — Research and answer pipeline questions using web sources, and identify human sources for questions requiring interviews.
- **enrich-stories** — Enrich all story leads by running discovery skills against each story in parallel.
- **find-photo-evidence** — Find photos with permissive licensing related to a given story.
- **geographic-source-discovery** — Discover trusted sources by mapping the civic and community landscape of the tenant's zip codes. No arguments needed.
- **generate-story-leads** — Find story leads by analyzing available sources for timely, outlier-driven local news.
- **identify-new-questions-from-article** — Read a story pitch and identify questions it does not yet address.
- **new-skill** — Create a new skill by asking the user questions and generating a SKILL.md template.
- **trusted-human-source-discovery** — Find human sources that can comment on a story.
- **trusted-source-discovery** — Scrapes RSS feeds supplied as an argument to discover sources for news articles.
- **verify-email** — Verify whether email addresses are reachable without sending an email.
- **web-fetch-cloudflare-circumvent** — Fetch web content that may be blocked by Cloudflare.

## License

MIT — see [LICENSE](LICENSE).
