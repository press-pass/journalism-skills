---
name: lobbying-issue-spike
description: Detect quarter-over-quarter spikes in lobbying spend by ALI issue code, by client, or by registrant; output ranked, source-cited spike tables. Use when a question asks "what changed?" or "who suddenly cared about X?".
---

# Detect lobbying spend spikes by issue or client

Surfaces statistically anomalous quarter-over-quarter movements in Senate LDA
reported income, broken down by ALI issue code, client, or registrant.

## When to use

- "Which issues saw the biggest lobbying spike in Q1 2025?"
- "Which clients ramped up spending after a particular event?"
- "What story should I lead with for the next quarter's filings?"

## Preconditions

`.context/db/lobbying.duckdb` exists (built by `lobbying-corpus-ingest`).

## How it works

`scripts/detect_spikes.py` runs deterministic SQL aggregations against
`senate_filings` + `senate_activities` and emits ranked tables with:

- absolute QoQ delta in income
- percentage QoQ delta
- z-score relative to that entity's own historical mean/std
- N filings supporting the row (so single-filing flukes are flagged)

## Steps

```bash
python3 skills/lobbying-issue-spike/scripts/detect_spikes.py \
  --db .context/db/lobbying.duckdb \
  --out .context/findings/ \
  --min-income 250000 \
  --top 50
```

Outputs CSVs:

- `findings/spikes_by_issue.csv` — top spikes by ALI code per quarter
- `findings/spikes_by_client.csv` — top spikes by client per quarter
- `findings/spikes_by_registrant.csv` — top spikes by registrant per quarter

## Verifiability

Every spike row carries `filing_uuids` (concatenated) for the supporting
filings so a reviewer can pull each from the public Senate LDA API.

## Limits

- Uses self-reported `income` only. Clients with rounded "less than $5,000" or
  null income are excluded from the ranking but counted in N.
- Q1 2026 has no Q2 2026 comparison yet — those rows are emitted as one-side
  spikes with `direction=opening` so they're not mistaken for declines.
