---
name: lda-chart
description: Render publication-quality charts from the lobbying+press investigation database. Each script consumes deterministic tables built by upstream skills and writes a PNG, an SVG, and a provenance.md tracing every bar/cell back to source records. Use when producing visualizations from the GAIN dataset that require source-traceable provenance.
license: MIT
compatibility: Requires Python 3.11+, duckdb, matplotlib, numpy.
metadata:
  author: PressPass
  version: "1.0"
---

This skill is the visualization layer. Each chart-rendering script is paired with a provenance markdown so a journalist (or editor, or judge) can audit any bar back to its underlying filings.

## Charts available

| Script | Output PNG | Topic |
|---|---|---|
| `chart_revolving_door.py` | `research/charts/01_revolving_door_top_members.png` | Top members whose ex-staff have the largest active K Street lobbying footprint |
| `chart_foreign_issues.py` | `research/charts/02_foreign_principal_issues.png` | Heatmap of foreign-tied lobbying by country × ALI issue |
| `chart_say_vs_pay.py` | `research/charts/03_say_vs_pay.png` | Scatter of bills by lobby filings vs press release mentions |
| `chart_amendment_storm.py` | `research/charts/04_amendment_storm.png` | Filings with the most amendments (planned) |

## Prerequisites
- `lda-setup` for tables `press`, `senate_*`, `house_*`
- `lda-revolving-door` for `revolving_door` (needed by chart 1)
- `lda-say-vs-pay` for `bill_mentions_*` (needed by chart 3)

## Use

```bash
python3 skills/lda-chart/scripts/chart_revolving_door.py
python3 skills/lda-chart/scripts/chart_foreign_issues.py
python3 skills/lda-chart/scripts/chart_say_vs_pay.py
```

Each script writes three files:
- `NN_<topic>.png` (200 dpi, publication-ready)
- `NN_<topic>.svg` (editable)
- `NN_<topic>_provenance.md` (every value → source filing_uuids)

## Design conventions

- Deep navy `#13294B` for primary bars / labels.
- Accent red `#c81d25` for "flagged" categories (silent bills, outliers).
- Accent green `#1a9850` for "controls" (HR 1 in chart 3 — the well-discussed bill).
- Sans-serif (DejaVu Sans).
- Always include a source line citing the underlying dataset URL and the reproducing script path.
- Never use 3-D, gradients-as-data, or chartjunk. Lie factor stays at 1.

## Adding a new chart

1. Write the SQL query that produces the rows you want.
2. Decide the chart form: bar (horizontal for long category labels), scatter for two continuous dimensions, heatmap for a 2D categorical grid.
3. Write `chart_<topic>.py` following the existing scripts as a template (figure size, title block, footer with source).
4. Emit `<topic>_provenance.md` with the SQL, the chart's underlying numeric table, and 3-5 spot-check rows tracing to filing_uuids.
