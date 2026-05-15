---
description: Generate a publication-quality chart family (PNGs + JSON sidecars) summarizing the most newsworthy patterns in the LDA + Congress press release corpuses. Each chart traces every datapoint to its source record. Use after running lobbying-corpus-build and press-corpus-build. Optional input: which charts to render (default = all).
---

You produce a single deterministic command that renders ~9 publication-ready charts from the
parquet corpus and writes a JSON sidecar per chart documenting the underlying query, source
fields, and a row-by-row data dump. Each chart can stand alone in a story or be slotted into
a wider report.

The chart family was tuned for the GAIN Agentic Investigation Challenge with help from a fused
[VisEval](https://github.com/microsoft/VisEval) + ChartMimic + Tufte rubric (`chart-eval`).

## Inputs

- `--out_dir` — where to write `*.png` + `*.json`. Default: `/charts` (inside the docker).
- `--charts` — optional space-separated list. Defaults to all nine:
  `ai_boom`, `issue_heatmap`, `revolving_door`, `ai_say_vs_pay`, `foreign`,
  `press_leaderboard`, `house_senate_gap`, `inaugural_money`, `new_registrations`.

The parquet corpus must already exist (run `lobbying-corpus-build` + `press-corpus-build` first).

## Step 1: Render the charts

```bash
docker run --rm \
  -v "$(realpath <PARQUET_DIR>):/parquet:ro" \
  -v "$(realpath <OUT_DIR>):/charts" \
  -v "$(realpath skills/lobbying-charts/scripts):/scripts:ro" \
  lobbypress-analysis \
  python /scripts/charts.py --out_dir /charts
```

Total runtime: ~30 seconds. Each chart prints `[chart] <name>` as it renders.

## Step 2: What each chart shows

| File | Title | Key claim |
|---|---|---|
| `01_ai_lobbying_boom.png` | AI lobbying has multiplied 5× since ChatGPT | Senate LDA activities mentioning "artificial intelligence" went from ~220/quarter (pre-ChatGPT) to ~1,180/quarter (2026 Q1). |
| `02_issue_heatmap.png` | Budget, Tax, Health persistently dominant | Top-12 ALI issue codes by quarter as a share of all activity. |
| `03_revolving_door.png` | Where K Street's Hill alumni worked | Members of Congress whose offices most often appear in lobbyists' `covered_position` field. |
| `04_ai_say_vs_pay.png` | Lobbyists mention AI 5× more than Congress | Quarterly side-by-side: AI-mentioning Senate activities vs. press releases. |
| `05_foreign_entities.png` | Foreign parents on Senate filings | Top 20 foreign-affiliated parents declared in `foreign_entities`. |
| `06_press_leaderboard.png` | Senate Democrats dominate the press-release factory | Q1 2026 press release counts per member, party-coded. |
| `07_house_senate_gap.png` | Clients in only one chamber | Stacked bar: how many client names appear only in Senate, only in House, or both. |
| `08_inaugural_money.png` | $67M to Trump-Vance Inaugural | LD-203 contributions to the inaugural committee, top 20 LDA filers. |
| `09_new_registrations.png` | Trump 2.0 triggered the largest lobbying rush since 2022 | New Senate registrations (filing_type='RR') per quarter, Q1 2025 highlighted. |

## Step 3: Verify provenance with the JSON sidecars

For every PNG there is a matching `*.json` with:

```json
{
  "title": "...",
  "data": [ {row 1...}, {row 2...} ],
  "method": "...",
  "source": "..."
}
```

Use these for fact-checking. Every claim in a story should cite at least the `filing_uuid` or
`bioguide_id` (Senate side) or `house_filing_id` + `filing_dir` (House side) for the cited row.

## Step 4: (optional) Run the chart-eval skill

Pipe each PNG through `chart-eval` to get a Tufte/FT-Visual-Vocabulary score before publishing:

```bash
# See: skills/chart-eval/SKILL.md
```

## Caveats — make sure they're in the published version

- The keyword "AI" matcher uses *only* the substring `artificial intelligence` (case-insensitive)
  to avoid the noise of two-letter "AI" matches. The trend is conservative — actual coverage is
  higher.
- The revolving-door chart uses surnames that uniquely identify a current member in the press
  corpus. Common surnames (e.g., `Brown`) can aggregate work for historical members of the same
  name (e.g., Sherrod Brown) and are flagged in the chart caption.
- `08_inaugural_money.png` counts only `LD-203` contributions where the `payee` string contains
  `TRUMP VANCE INAUGURAL` and may miss alternate spellings or affiliated PACs.
- `07_house_senate_gap.png` uses exact uppercase string match for client names; the gap is an
  upper bound — true entity resolution would reduce it.
