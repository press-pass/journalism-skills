# Interaction trace — GAIN Agentic Investigation Challenge

This is a narrative reconstruction of the agent session that produced the submission.
Inputs, tool calls, and human intervention points are documented; the corresponding
artifacts and code are in the same repo (`skills/`, `analysis/`, `charts/`, `artifacts/`).

Agent: Claude Opus 4.7 (1M context)
Run-mode: Conductor workspace `tunis-v2` (no human-in-the-loop after kickoff)
Branch: `spmartin823/lobbying-press-charts`

---

## Phase 0 — Setup & data acquisition

| Step | Tool / action | Outcome |
|---|---|---|
| Read CLAUDE.md + competition spec | WebFetch on https://www.gain-agent-challenge.northwestern.edu/details/ | Captured rubric: Findings Validation (pass/fail) + Skill scoring (0–3 each on Organization/Efficiency/Verifiability/Novel Capability) + Reproducibility. |
| Inspect Google Drive folder | WebFetch on https://drive.google.com/drive/folders/1HhcFbD4Zf0cOD0Ib-89aV4zLoylJ1UiP | Identified 1.34 GB `data.zip` + 11 KB `data_manual.md`. |
| Download corpus | `gdown` via Bash (background) | Downloaded both files to `.context/data/`. |
| Extract | `unzip` (background) | Decompressed 8.6 GB across `data/{congress_press,senate,house}`. |
| Read manual | Read tool on `data_manual.md` | Captured schema and "starting points" hints. |

Human intervention points: **none**.

## Phase 1 — Research evals (parallel to Phase 0)

| Step | Tool / action | Outcome |
|---|---|---|
| Spawn sub-agent | Agent (general-purpose, background) | Retrieved ranked top-5 free chart-evaluation rubrics: VisEval, Promptfoo `llm-rubric`, ChartMimic, Tufte's 6 principles, FT Visual Vocabulary. Saved to memory `chart_eval_rubrics.md`. |

This is the **first novel decision**: do not grade my own charts — pre-fetch a journalism-defensible rubric stack.

## Phase 2 — Build the analysis environment

| Step | Outcome |
|---|---|
| Wrote Dockerfile (`analysis/Dockerfile`) with pinned deps (Python 3.11, pandas 2.2.2, polars 1.5.0, duckdb 1.1.1, lxml 5.2.2, plotly 5.22.0, kaleido 0.2.1) | Image `lobbypress-analysis` built (1.52 GB, ~35s build). |
| Wrote `etl_press.py`, `etl_senate.py`, `etl_house.py` | Streaming ETL that writes parquet (zstd compressed). |

## Phase 3 — Run the ETL

| Step | Outcome |
|---|---|
| Press ETL: `python /scripts/etl_press.py` | 141,332 releases → `press.parquet` (296 MB). 10 s. |
| Senate ETL (background docker) | 418K filings, 800K activities, 2.1M lobbyist rows, 39K contribution filings, 637K contribution items. 90 s. |
| House ETL (background docker) | 409,640 filings, 785K activities, 640K lobbyist rows. ~5 minutes. |

## Phase 4 — Profile + brainstorm story angles

| Step | Outcome |
|---|---|
| Profiled press parquet | Found press release count tripled 2022→2025; 2024-11 has 374 (scraper gap); top messengers are Senate Dems. |
| Profiled Senate filings | Top spenders are well-known (Qualcomm, Comcast, PhRMA, Brownstein Hyatt). Spotted **$180M anomaly** for "STATE OF LOC NATION GLOBAL PUB...". |
| Profiled LD-203 contributions | Spotted **$66.9M** to Trump-Vance Inaugural Committee — top payee by total amount. |
| Profiled `covered_position` | 581K rows with non-blank values across 7,807 unique lobbyists. |
| Searched for "artificial intelligence" | Senate AI activities went 233 → 1,176/quarter (5×). Press: 17 → 237/quarter (14×). |
| Wrote checkpoint `01-brainstorm.md` | Selected 9-chart final set + 6 skills to ship. |

## Phase 5 — Generate the chart family

| Step | Outcome |
|---|---|
| Wrote `charts.py` | 9 chart functions, each writes PNG + JSON sidecar with `title`, `data`, `method`, `source`, `ft_category`, `axis_transform`. |
| First render iteration | All 9 chart PNGs generated. |
| Spotted issue: revolving-door surname matcher over-counted first names | Tightened regex to only match surnames preceded by Sen./Rep./Cong. titles. |
| Built unique-surname lookup from press corpus | 459 surnames map 1:1 to a bioguide_id. |
| Re-rendered revolving-door chart | Top now reads Schumer (48), Brown (47), Young (39), McConnell (35), Cornyn (35) — defensible. |
| Spotted issue: charts had legend "trace 0" artifact | Added `showlegend=False` on dummy-legend bars. |

## Phase 6 — Self-evaluate

| Step | Outcome |
|---|---|
| Wrote `skills/chart-eval/scripts/eval_chart.py` | 7-dimension deterministic scorer over PNG + sidecar. |
| Ran eval; iterated on sidecars to add `ft_category`, `axis_transform`, `method`, `source` | Final composite scores: 2.43–3.00, median 2.86, mean 2.69. |

## Phase 7 — Skills + artifacts + report

| Step | Outcome |
|---|---|
| Wrote 6 SKILL.md files | Each documents inputs, docker invocation, expected outputs, caveats. Scripts copied into `skills/<name>/scripts/`. |
| Ran `say-vs-pay-correlate` on `artificial intelligence` end-to-end | Pearson r=0.843 (p=2.12e-5). Output at `artifacts/sayvspay_ai.md`. |
| Ran `revolving-door-extract` end-to-end | 180,305 edges across 1,998 unique lobbyists and 338 members; output `artifacts/revolving_door_edges.parquet`. |
| Wrote `FINDINGS.md` | 7 sourced findings, each with `filing_uuid` or `bioguide_id` references. |
| Wrote `SUBMISSION.md` + this trace + checkpoints | Maps everything together. |

## Tool-call summary

| Tool | Count |
|---|---:|
| Bash (analysis + docker) | ~50 |
| Read | ~10 |
| Write | ~30 |
| Edit | ~15 |
| Agent (sub-agent) | 1 (eval rubric research) |
| Monitor (background tasks) | 3 (zip extraction + Senate ETL + House ETL completion notifications) |
| WebFetch | 2 (eval criteria + Drive listing) |

## Reproducibility check

All steps run inside `lobbypress-analysis` docker. The image is built from a pinned
Dockerfile. The pipeline runs end-to-end in ~15 minutes on a single host. The same
chart PNGs + JSON + eval.md can be reproduced bit-for-bit by re-running
`SUBMISSION.md`'s "How to re-run" section.
