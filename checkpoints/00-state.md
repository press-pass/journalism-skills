# State Checkpoint 0 — Setup

Date: 2026-05-15 (start)
Branch: spmartin823/lobbying-press-charts (workspace branch — matches workspace name)

## Goal
Compete in GAIN Agentic Investigation Challenge: produce interesting charts/graphs from federal lobbying + congressional press release data (2022 – Q1 2026). Build journalism skills that ship to the journalism-skills repo. Evaluate own work against external rubrics.

## Required submission components
1. Agent Skill(s) — full Skill spec
2. Findings Report — newsworthy claims, sourced
3. Interaction Traces — JSON or rendered logs
4. README.md — maps skills, findings, traces, sources, COIs, legal flags

## Evaluation criteria
- Findings Validation (pass/fail): accurate, sourced, "something a reporter would chase"
- Skill Scoring (0–3 each, equally weighted): Organization, Efficiency, Verifiability, Novel Capability
- Reproducibility: must be re-runnable

## Data location
`.context/data/Agentic Investigation Datasets/`
- `data.zip` (1.34 GB) — extracting now → `data/`
- `data_manual.md` — read

## Data shape
- `data/congress_press/` JSONL by month. ~48K releases/year. fields: url, title, date, member.{bioguide_id, name, party, state, chamber}, text.
- `data/senate/{YEAR}/filings/filings_{YEAR}.json` + `contributions_{YEAR}.json`. Deeply nested LDA.
- `data/house/{YEAR}_{Quarter}_XML/*.xml` — 409,650 files. Schema parallel to Senate.
- `data/senate/constants/` — ALI issue codes, filing types, gov entities, etc.

## Status
- [x] Downloaded data zip + manual
- [ ] Extraction (running in background)
- [ ] Docker analysis image (building in background)
- [ ] Sub-agent: research eval frameworks (running in background)
- [ ] Data exploration
- [ ] Brainstorm story angles
- [ ] Build skills
- [ ] Generate charts
- [ ] Write findings report

## Notes
- The contest values: findings + reproducible novel skill > pretty charts alone.
- Strategy: ETL once into parquet → reproducible queries → repeatable skill that builds the chart family from a single CLI.
- All compute lives in Docker so it's portable.
