# Checkpoint 1 — Story angle brainstorm

## Initial observations (press parquet only)
- 141,332 releases total. 47,569 Senate / 93,641 House.
- 2022→2025 release count nearly tripled: 19,702 → 48,318. 2026 Q1 already 11,466 (annualizes to ~46K).
- Democrats outweigh Republicans 79K → 61K releases. Minority status may correlate with more messaging.
- Sen. Dick Durbin issued 788 releases in 2025 — >2/day on average.
- Top 20 prolific 2025 members are heavily Senate (Durbin, Grassley, Blumenthal, Warren, Heinrich, etc.). The House is more diffuse: 435 voices vs 100.
- Kimberlyn King-Hinds (MP, R) is in the top 20 — surprising for a non-state delegate.

## Chart candidates (ranked)
A. **AI lobbying explosion**: count of lobbying activities mentioning AI/"artificial intelligence" by quarter 2022→2026Q1. Likely shows hockey stick. Pair with top 10 clients.
B. **Revolving door**: distribution of "covered_position" text → identify "Chief of Staff to Sen. X", "LA Rep. Y" patterns. Count ex-Hill-staffer lobbyists. Show which senators/committees most-poached-from.
C. **Foreign client geography**: lobbying activities filed by clients with foreign_entities set. Top 15 countries, with quarter trend lines. (Or: top 15 foreign-affiliated clients.)
D. **Issue heatmap**: ALI code × quarter normalized to row-sum=1. Reveals shifting issue mix.
E. **Say-vs-Pay**: For a hot issue (AI / healthcare / immigration), join press release mention count to lobbying spend targeting that chamber. Per-member scatter.
F. **Bill mention coverage**: bills cited in `specific_issues/description` vs cited in press releases. "Most-lobbied, least-talked-about" bills.
G. **Press release volume leaderboard** Q1-2026, normalized per chamber + party.
H. **First-time registrant spikes**: new registrant counts per quarter; correlate with Trump-admin transition (Q1 2025).
I. **LD-203 contribution flows**: top honorees of lobbyist contributions. Show concentration.
J. **Foreign agent overlap**: filings with foreign_entities × top lobbying issues. Where do non-US interests focus?

## Final chart set (target 6 publication-ready)
1. AI lobbying boom (bar / line)
2. Revolving door — who's the most-poached member?
3. Issue heatmap with annotation callouts
4. Foreign lobbying country leaderboard with quarter-over-quarter delta
5. Say-vs-Pay scatter on the hottest issue (probably AI or healthcare)
6. Press release factory leaderboard Q1 2026 (per-day rate, party-coded)

## Skills to build
1. **lobbying-corpus-build** — ETL Senate JSON + House XML → parquet (already drafted as scripts)
2. **press-corpus-build** — JSONL → parquet (done)
3. **revolving-door-extract** — parse covered_position text → (lobbyist, ex-role, member/committee)
4. **issue-trend-detect** — DuckDB query helper that finds outlier quarters per issue code
5. **say-vs-pay-correlate** — joins press release mention counts to lobbying activities
6. **chart-eval** — score rendered PNG against fused VisEval+ChartMimic+Tufte rubric

## Strategy notes
- For "Novel Capability", revolving-door-extract + say-vs-pay-correlate are the most defensibly novel because they require both corpus joins.
- For "Verifiability", every chart's data file must trace each row to a `filing_uuid` / `bioguide_id` / press release URL.
- For "Reproducibility", every script runs `make data && make charts` in docker.
