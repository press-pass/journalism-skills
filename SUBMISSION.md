# GAIN Agentic Investigation Challenge — Submission

Submitter: Press Pass (Seamus Martin) — `seamus@presspass.ai`
Repo: https://github.com/press-pass/journalism-skills · branch `spmartin823/lobbying-press-charts`
Date: 2026-05-15

This file is the README the challenge requires: it maps the included skills, the supporting
findings, the location of interaction traces, all external data sources used, conflicts of
interest, and any flags for potential legal violations.

---

## 1. Skills

All skills live under `skills/<name>/` and follow the [Agent Skills](https://docs.anthropic.com/claude/docs/skills) specification (frontmatter + body). Six new skills shipped in this submission:

| Skill | Description | What scoring criterion it earns |
|---|---|---|
| [`lobbying-corpus-build`](skills/lobbying-corpus-build/SKILL.md) | ETL Senate JSON + House XML into unified parquet tables, keyed to filing_uuid / house_filing_id. | Efficiency (one docker invocation), Reproducibility (pinned image) |
| [`press-corpus-build`](skills/press-corpus-build/SKILL.md) | ETL Congress press JSONL into parquet keyed to bioguide_id. | Efficiency, Reproducibility |
| [`lobbying-charts`](skills/lobbying-charts/SKILL.md) | Render 9 finalist charts with provenance JSON sidecars. | Verifiability (every chart has its data + method) |
| [`chart-eval`](skills/chart-eval/SKILL.md) | Score charts on a fused Tufte + ChartMimic + FT Visual Vocabulary rubric, no LLM required. | Novel capability, Verifiability |
| [`revolving-door-extract`](skills/revolving-door-extract/SKILL.md) | Parse lobbyist `covered_position` free text into structured `(lobbyist_id, bioguide_id, evidence_text)` edges via unique-surname disambiguation. | Novel capability, Organization |
| [`say-vs-pay-correlate`](skills/say-vs-pay-correlate/SKILL.md) | Cross-corpus quarterly correlation of press release counts vs lobbying activity counts for any keyword. Reports Pearson r. | Novel capability, Verifiability |

These skills compose: `lobbying-corpus-build` + `press-corpus-build` produce parquet that
every other skill consumes. The other four skills are independent and can be run in any order.

## 2. Findings

[`FINDINGS.md`](FINDINGS.md) contains seven sourced findings. Each cites primary keys
(`filing_uuid`, `bioguide_id`, House filing IDs) so a panelist can verify by opening:

- https://lda.senate.gov/filings/public/filing/<filing_uuid>/print/ for any Senate filing
- https://lda.senate.gov/api/v1/contributions/<filing_uuid>/ for any LD-203 record
- The press release `url` in the press parquet for any release-based claim

### Headline findings

1. Lobbyist filers reported **$66.9M** to the Trump-Vance inaugural — ~13× the entire 5-year corpus of Biden-related payee amounts.
2. AI lobbying activities are up **5×** since ChatGPT; AI press releases are up **14×**.
3. **2,511** new Senate registrations in Q1 2025 — the largest single-quarter rush since 2022.
4. Senate Democrats produced **15 of the top 20** press releases in Q1 2026 despite minority status.
5. Sen. Chuck Schumer's office is the single largest pipeline of lobbyists' disclosed Hill alumni (48 distinct lobbyists).
6. **1,000–1,800 clients per year** appear in only one chamber's filings — a compliance + entity-resolution story.
7. **Anomaly:** `STATE OF LOC NATION GLOBAL PUB...` declared $180M of income across 15 quarterly filings — likely filer error worth referring to the Senate Office of Public Records.

## 3. Interaction traces

The full agent session log is captured at [`traces/session.md`](traces/session.md) — a
narrative reconstruction of the analysis. Per-skill scripted outputs were saved under
[`artifacts/`](artifacts/):

| Artifact | Source skill | Purpose |
|---|---|---|
| `artifacts/sayvspay_ai.md` + `.parquet` | `say-vs-pay-correlate` | Pearson r=0.843 (p=2.12e-5) press↔lobby AI correlation |
| `artifacts/sayvspay_ai_members.parquet` | `say-vs-pay-correlate` | Per-member AI press counts (2022–2026 Q1) |
| `artifacts/revolving_door_edges.parquet` | `revolving-door-extract` | 180,305 `(lobbyist, member, evidence_text)` edges over 1,998 unique lobbyists and 338 members |
| `artifacts/eval.md` + `.json` | `chart-eval` | Per-chart Tufte/FT/Provenance scores |
| `charts/*.png` + `*.json` | `lobbying-charts` | 9 publication-ready charts + sidecars |
| `checkpoints/00–02.md` | (manual) | Progress checkpoints (survive context compaction) |

## 4. External data sources used

The corpus is the **GAIN-provided** Senate LDA + House LDA + Congress Press release dataset.
No external/third-party data was joined into the analysis; every claim is sourced inside the
provided corpus.

The chart-eval rubric is informed by external rubrics (all free):

- [VisEval](https://github.com/microsoft/VisEval) (MIT, Microsoft Research, IEEE VIS 2024)
- [ChartMimic](https://github.com/ChartMimic/ChartMimic) (Apache-2.0, ICLR 2025)
- [FT Visual Vocabulary](https://github.com/Financial-Times/chart-doctor) (MIT)
- [Tufte's 6 principles of graphical integrity](https://faculty.cc.gatech.edu/~stasko/7450/16/Notes/tufte.pdf)
- [Promptfoo `llm-rubric`](https://www.promptfoo.dev/docs/configuration/expected-outputs/model-graded/llm-rubric/) (MIT) — for the future LLM-judge extension

The Docker image (`lobbypress-analysis`) pins Python 3.11 + pandas 2.2.2 + polars 1.5.0 + duckdb 1.1.1 + lxml 5.2.2 + pyarrow 17.0.0 + plotly 5.22.0 + kaleido 0.2.1. The Dockerfile is in `analysis/Dockerfile`.

## 5. Conflicts of interest

The submitter (Press Pass / Seamus Martin) has no financial relationship with any of the
registrants, clients, contribution payees, or members of Congress named in the findings.

## 6. Flags for potential legal violations

| Item | Notes |
|---|---|
| **`STATE OF LOC NATION GLOBAL PUB...` $180M filings** | 15 quarterly filings declaring $20M income each, with no expenses disclosed — possible filer error, possible disclosure spam. Filings should be inspected and referred to the Senate Office of Public Records if not legitimate. |
| **Trump-Vance Inaugural Committee contributions** | Disclosed amounts comply with LD-203 reporting rules on their face; flagging the **concentration** ($66.9M, 13× Biden-related total across the entire 5-year corpus) as a public-interest story, not as a compliance concern. |
| **Cross-chamber filing gaps** | ~1,000–1,800 clients per year appear in only one chamber's filings, suggesting some registrants are missing required co-filings (House LD-2 + Senate LD-2). Not a single-filing legal flag — rather a population-level compliance pattern. |

## 7. How to re-run the entire submission

```bash
# 1. Build the analysis image (5 minutes)
cd analysis && docker build -t lobbypress-analysis . && cd ..

# 2. Run all ETL (~10 minutes wall-clock; Senate + House parallel)
docker run --rm -v "$(pwd)/.context/data/Agentic Investigation Datasets/data:/data:ro" \
  -v "$(pwd)/.context/parquet:/parquet" \
  -v "$(pwd)/analysis/scripts:/scripts:ro" \
  lobbypress-analysis python /scripts/etl_press.py --press_root /data/congress_press --out /parquet/press.parquet
docker run --rm -d --name senate -v "$(pwd)/.context/data/Agentic Investigation Datasets/data:/data:ro" \
  -v "$(pwd)/.context/parquet:/parquet" -v "$(pwd)/analysis/scripts:/scripts:ro" \
  lobbypress-analysis python /scripts/etl_senate.py --senate_root /data/senate --out_dir /parquet
docker run --rm -d --name house -v "$(pwd)/.context/data/Agentic Investigation Datasets/data:/data:ro" \
  -v "$(pwd)/.context/parquet:/parquet" -v "$(pwd)/analysis/scripts:/scripts:ro" \
  lobbypress-analysis python /scripts/etl_house.py --house_root /data/house --out_dir /parquet
docker wait senate house

# 3. Generate all 9 charts (~30 seconds)
docker run --rm -v "$(pwd)/.context/parquet:/parquet:ro" \
  -v "$(pwd)/charts:/charts" -v "$(pwd)/analysis/scripts:/scripts:ro" \
  lobbypress-analysis python /scripts/charts.py --out_dir /charts

# 4. Score the charts
docker run --rm -v "$(pwd)/charts:/charts" \
  -v "$(pwd)/skills/chart-eval/scripts:/scripts:ro" \
  lobbypress-analysis bash -c "pip install --quiet pillow && python /scripts/eval_chart.py --charts_dir /charts --out_md /charts/eval.md"

# 5. (optional) Run say-vs-pay on any keyword
docker run --rm -v "$(pwd)/.context/parquet:/parquet:ro" \
  -v "$(pwd)/.context/out:/out" \
  -v "$(pwd)/skills/say-vs-pay-correlate/scripts:/scripts:ro" \
  lobbypress-analysis bash -c "pip install --quiet scipy && python /scripts/correlate.py \
    --keywords 'artificial intelligence' --press_parquet /parquet/press.parquet \
    --senate_activities_parquet /parquet/senate_activities.parquet \
    --house_activities_parquet /parquet/house_activities.parquet \
    --out_parquet /out/sayvspay.parquet --out_summary_md /out/sayvspay.md"
```

The total end-to-end runtime is **~15 minutes on a 2024 M3 MacBook Pro / OrbStack** — fully
reproducible from any machine with Docker.
