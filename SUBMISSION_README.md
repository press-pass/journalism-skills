# Florence-v1 — GAIN Agent Challenge submission

This is the submission map for the **florence-v1** entry in the GAIN Agent
Challenge. It is intended to satisfy the four submission components defined
on the [Challenge details page](https://www.gain-agent-challenge.northwestern.edu/details/):

1. **Agent Skill(s)** — five reusable skills under `skills/`
2. **Findings Report** — `FINDINGS.md` at the repo root
3. **Interaction Traces** — the analysis pipeline + the chart-generation
   scripts themselves serve as interaction traces (each captures the inputs,
   tool calls, intermediate artifacts, and outputs)
4. **README.md** (this file) — map of skills, findings, data sources,
   conflicts of interest, legal flags

---

## 1. Skills

| Skill | Location | Purpose | Rubric dimensions it scores on |
|---|---|---|---|
| `lda-corpus-query` | `skills/lda-corpus-query/` | DuckDB SQL views over the indexed Parquet corpus. Pushes filtering, aggregation, and text search to deterministic tools so the agent's main context stays focused on reasoning. | Corpus Efficiency, Human Verifiability |
| `lda-press-bridge` | `skills/lda-press-bridge/` | Cross-corpus member snapshot tool: joins press output, lobbying targeting their chamber, and LD-203 contributions to their leadership PAC. | Investigation Organization, Novel Capability Extension |
| `inaugural-contribution-trace` | `skills/inaugural-contribution-trace/` | Audit-trail tool for LD-203 contributions to a specific recipient. Joins each donor back to their LDA lobbying activity in the same quarter. | Human Verifiability, Novel Capability Extension |
| `revolving-door-extractor` | `skills/revolving-door-extractor/` | Parses 1.1M `covered_position` free-text strings into normalized role + source-office buckets. Builds the Hill-office → K-Street graph. | Novel Capability Extension, Corpus Efficiency |
| `chart-quality-review` | `skills/chart-quality-review/` | Scores a generated chart against four external rubrics (Kirk TAE, Few effectiveness, Evergreen 23-item checklist, Penn State 30-pt). Designed to avoid self-evaluation drift. | Investigation Organization, Human Verifiability |

Each `SKILL.md` follows the journalism-skills plugin format
(`description:` frontmatter + skill body). All five skills can be loaded
via the existing `journalism-skills` plugin (`.claude-plugin/plugin.json`).

## 2. Findings

See **`FINDINGS.md`** for the four substantive findings:

1. Every disclosed donor to Trump's 2025 inauguration was already lobbying Congress ($18.05M from 30 corporations)
2. Disclosed federal lobbying topped $6.1B in 2025 — a 22% jump over 2022
3. One in eight U.S. lobbying disclosures names a tax-haven parent
4. Senate Finance and House Energy & Commerce lead the K-Street revolving-door pipeline

Plus four data-quality flags worth knowing.

## 3. Interaction traces / reproducibility

The complete analysis pipeline is committed and runs from scratch:

| Stage | Script | Output |
|---|---|---|
| Build container | `analysis/docker/Dockerfile`, `docker-compose.yml`, `requirements.txt` | `florence-analysis:latest` image |
| Index press releases | `analysis/pipeline/01_index_press.py` | `/parquet/press/` |
| Index Senate LDA | `analysis/pipeline/02_index_senate.py` | `/parquet/senate/` |
| Index House LDA | `analysis/pipeline/03_index_house.py` | `/parquet/house/` (parallel parse of 409K XMLs) |
| EDA | `analysis/pipeline/eda_basics.py`, `eda_drilldown.py` | console + `analysis/FINDINGS_LEADS.md` |
| Parse revolving door | `analysis/tools/revolving_door.py` | `/parquet/revolving_door.parquet`, `analysis/findings/revolving_door.md` |
| Trace contributions | `analysis/tools/contribution_trace.py` | `analysis/findings/inaugural_trace.{md,csv}` |
| Chart 1 — Inaugural | `analysis/charts/chart_inaugural.py` | `analysis/charts/output/01_inaugural_donors.{png,svg,csv}` |
| Chart 2 — Surge | `analysis/charts/chart_surge.py` | `02_lobbying_surge.{png,svg}` + 2 CSVs |
| Chart 3 — Tax havens | `analysis/charts/chart_tax_havens.py` | `03_tax_havens.{png,svg}` + 3 CSVs |
| Chart 4 — Revolving door | `analysis/charts/chart_revolving.py` | `04_revolving_door.{png,svg}` + 2 CSVs |
| Chart QA | `analysis/tools/chart_review.py` | `analysis/findings/chart_review_*.{json,md}` |

To reproduce from a fresh checkout:

```bash
# 1. Download the data per the challenge instructions, then extract:
mkdir -p .context/data/Agentic\ Investigation\ Datasets/extracted
unzip data.zip -d .context/data/Agentic\ Investigation\ Datasets/extracted
# 2. Build and run the analysis container:
docker compose -f analysis/docker/docker-compose.yml build
docker compose -f analysis/docker/docker-compose.yml up -d
# 3. Index:
docker compose -f analysis/docker/docker-compose.yml exec florence \
    python analysis/pipeline/01_index_press.py
docker compose -f analysis/docker/docker-compose.yml exec florence \
    python analysis/pipeline/02_index_senate.py
docker compose -f analysis/docker/docker-compose.yml exec florence \
    python analysis/pipeline/03_index_house.py
# 4. Generate findings + charts:
docker compose -f analysis/docker/docker-compose.yml exec florence \
    python analysis/tools/revolving_door.py --out /parquet/revolving_door.parquet --md analysis/findings/revolving_door.md
docker compose -f analysis/docker/docker-compose.yml exec florence \
    python analysis/tools/contribution_trace.py --honoree-like "%trump%vance%inaugural%" --md analysis/findings/inaugural_trace.md --csv analysis/findings/inaugural_trace.csv
docker compose -f analysis/docker/docker-compose.yml exec florence \
    python analysis/charts/chart_inaugural.py
docker compose -f analysis/docker/docker-compose.yml exec florence \
    python analysis/charts/chart_surge.py
docker compose -f analysis/docker/docker-compose.yml exec florence \
    python analysis/charts/chart_tax_havens.py
docker compose -f analysis/docker/docker-compose.yml exec florence \
    python analysis/charts/chart_revolving.py
```

End-to-end runtime on a 2024 MacBook Pro (M-series, OrbStack): ~30 minutes
for the full pipeline.

## 4. Data sources

All data is **public**. The complete corpus is described in `analysis/EVAL_RUBRIC.md`'s sibling document `data_manual.md` (shipped with the competition).

| Dataset | Source | Files | License |
|---|---|---|---|
| Congressional press releases | thescoop.org/congress-press/ (scraped from `*.house.gov` / `*.senate.gov`) | 141,332 records | Public records (released by Members) |
| Senate LDA filings & contributions | [Senate LDA API](https://lda.senate.gov/api/v1/) | 418,170 filings + 155,689 contribution reports | Public records (federal law) |
| House LDA registrations & quarterly reports | [House Clerk Lobbying Disclosure](https://disclosurespreview.house.gov/) | 405,650 XML files | Public records (federal law) |

External datasets that **could** enrich the work (not used in this
submission but referenced as starting points):
- Congress.gov bulk data — bills, votes, committee assignments
- FEC — campaign finance ground-truth
- FARA — foreign agents
- Federal Register — regulatory outcomes

## 5. Conflicts of interest

None declared. The submitter is not employed by, contracted to, or
holding equity in any of the corporations, lobbying firms, or committees
named in the findings.

## 6. Legal flags

- All data is **public record** — no private information is included.
- Tax-haven categorization (Finding 3) uses a composite of OECD and
  Tax Justice Network designations, both of which are public lists. Naming
  a corporate parent as domiciled in a tax-haven jurisdiction is a
  factual descriptor of the filing; it does not imply any specific
  legal violation.
- The "Mike Collins" data-quality flag in `FINDINGS.md` is a *defensive*
  callout (do not attribute releases without resolving bioguide_id);
  no actual person is accused of wrongdoing.

## 7. Branch & repo hygiene

This work lives on branch **`florence-v1`** of the
`press-pass/journalism-skills` repository. The branch contains:

- `skills/` — 5 new skills (in addition to the upstream 12)
- `analysis/` — Dockerized pipeline, tools, charts
- `analysis/charts/output/` — committed chart artifacts (PNG, SVG, CSV)
- `FINDINGS.md`, `SUBMISSION_README.md`, `CHECKPOINT.md` — submission artifacts
- The 1.34 GB raw data lives in `.context/data/`, gitignored — re-download
  via the challenge link as shown above.

## 8. Self-evaluation against the GAIN rubric

Each skill was designed to score deliberately on each of the four equally-
weighted dimensions:

| Dimension | How florence-v1 addresses it |
|---|---|
| **Investigation Organization** | `CHECKPOINT.md` survives compaction; `FINDINGS.md` lists open questions per finding; `analysis/FINDINGS_LEADS.md` separates strong vs weak leads. |
| **Corpus Efficiency** | Raw 8.6 GB → indexed Parquet ≈ 1 GB. DuckDB views in `analysis/tools/views.py` mean the agent writes SQL, not Python iterations. The revolving-door extractor processes 1.1M rows deterministically without a single LLM call. |
| **Human Verifiability** | Every chart ships with its source CSV and per-row `filing_uuid`. The Skill docs include "Output rules (verifiability)" sections. The `chart-quality-review` skill auto-flags missing source attribution. |
| **Novel Capability Extension** | `lda-press-bridge` resolves entities across two formerly disjoint corpora; `inaugural-contribution-trace` materializes the contribution↔lobbying bridge as a receipt; `revolving-door-extractor` turns the messiest LDA field into a queryable graph. |
