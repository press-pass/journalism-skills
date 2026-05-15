---
name: lobbying-chart
description: Generate publication-quality matplotlib charts from CSV findings produced by other lobbying-* skills. Use whenever a finding needs a chart for a story, slide, or report — keeps style consistent and writes both PNG and SVG with embedded data source metadata.
---

# Generate charts from lobbying findings

Wraps matplotlib + a curated style for newsroom-quality charts. Reads CSVs
emitted by `lobbying-issue-spike` or any deterministic query and produces
PNG + SVG with a footer source line that cites `data_manual.md` and the
filing identifiers used.

## When to use

- "Make a bar chart of top spike issues for Q1 2026."
- "Plot foreign lobbying spend per country, 2022 vs 2025."
- "Time-series of HR 1234 mentions in press vs lobbying."

## Preconditions

- Input CSV file with at least the columns specified per chart type.

## Steps

```bash
python3 skills/lobbying-chart/scripts/chart.py \
  --kind bar \
  --in .context/findings/spikes_by_issue.csv \
  --x issue_name \
  --y abs_delta \
  --title "Largest QoQ lobbying spend deltas by issue (USD)" \
  --subtitle "Senate LDA filings, 2022–2026 Q1" \
  --source "Senate LDA via data_manual.md" \
  --out .context/charts/spike_issues.png
```

Outputs: PNG + matching .svg + a `.txt` metadata sidecar listing source columns
and any filter applied.

## Chart kinds

- `bar` — horizontal or vertical bar
- `line` — time-series (x must be parseable as date or int year)
- `scatter` — paired numeric columns
- `area_stacked` — stacked area on time series
- `slope` — two-point slope chart (good for "before vs after")

## Style

The Pretext-style sheet under `references/style.mplstyle` enforces:
- 16:9 layout, 1200 dpi for PNG
- Bold title, italic subtitle, footer source line
- No gridlines on bar; subtle gridlines on line/scatter
- Single-hue palette with a contrast color for the highlighted series

## Verifiability

The script writes a `.meta.json` next to each output documenting:
- input CSV path and content hash (sha256)
- columns and filters used
- git commit hash if the workspace is a git repo

So a reviewer can re-derive any chart from this metadata.
