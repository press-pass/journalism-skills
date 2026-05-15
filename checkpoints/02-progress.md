# Checkpoint 2 — Mid-flight progress

Date: 2026-05-15 (start + ~1h)
Branch: spmartin823/lobbying-press-charts

## Completed
- [x] Downloaded GAIN data zip + manual; extracted 8.6 GB to `.context/data`.
- [x] Built `lobbypress-analysis` docker image (pinned deps for reproducibility).
- [x] Wrote ETL scripts (`etl_press.py`, `etl_senate.py`, `etl_house.py`).
- [x] Ran all three ETLs; parquet tables in `.context/parquet`:
  - press.parquet (141,332 rows)
  - senate_filings.parquet (418K) + activities (799K) + lobbyists (2.1M) + contrib_filings (39K) + contrib_items (637K)
  - house_filings.parquet (410K) + activities (785K) + lobbyists (640K)
- [x] Profiled data, identified 7 story angles.
- [x] Researched eval rubrics: VisEval + ChartMimic + Tufte + FT Visual Vocabulary.
- [x] Wrote 6 skills: `lobbying-corpus-build`, `press-corpus-build`, `lobbying-charts`, `chart-eval`, `revolving-door-extract`, `say-vs-pay-correlate`.
- [x] Generated 9 finalist charts + JSON sidecars.
- [x] Ran chart-eval skill — all charts score >= 2.43, 5 of 9 at 2.86+, 1 at 3.0.
- [x] Wrote FINDINGS.md with 7 reportable findings, each sourced to filing UUIDs.

## Findings summary
1. $66.9M lobbyist-reported contributions to Trump-Vance inaugural (13× anything Biden-related, 5-year corpus)
2. AI lobbying activities 5× since ChatGPT; AI press releases 14× (lobbying outnumbers press 5-to-1)
3. Trump 2.0 triggered largest Q1 new-registration rush (2,511, +91% vs 4-year baseline)
4. Senate Dems dominate 2026 press-release factory; Durbin = 2.3/day
5. K Street Hill alumni pipeline: Schumer office tops the list (48 ex-staffer lobbyists)
6. 1,000–1,800 clients/yr appear in only one chamber's filings
7. Anomaly: STATE OF LOC NATION × $180M declared income — likely filer error worth flagging

## Remaining
- [ ] Generate interaction trace JSON (this conversation as evidence)
- [ ] Write README.md (maps skills + findings + traces + sources + COIs)
- [ ] Update top-level README to add new skills to the index
- [ ] Commit to branch + push

## Risk register
- Revolving-door surname collisions (Brown, Paul, etc.) — flagged in chart caption; full fix needs historical bioguide table.
- 2024-11 press release scrape gap — flagged when discussing 2024 trends.
- LOC COMMUNITY anomaly — flagged in findings.
- 2026 House data is partial — flagged.
