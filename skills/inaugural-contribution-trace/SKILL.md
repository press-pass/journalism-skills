---
description: Audit-trail tool for LD-203 contributions to a specific committee or recipient (e.g., Trump Vance Inaugural Committee). Pulls every disclosed contribution item, joins each donor back to their LDA lobbying activity in the same quarter, and emits a reviewable receipt (filing_uuid, contribution_date, lobbying issues, target chamber) per contribution.
---

Use this when investigating a single contribution recipient (an inaugural
committee, a leadership PAC, a campaign committee). The skill walks every
contribution row, joins back to LDA filings on `registrant_id`, and produces
both a summary and an itemized receipt list that an editor can verify.

## When to use

- "Who gave to the 2025 Trump-Vance Inaugural Committee, and were they
  lobbying Congress at the same time?"
- "Which lobbyists' PACs gave to the NRSC in 2024?"
- "Trace every dollar reported under LDA going to {recipient}."

## How to run

```bash
docker compose -f analysis/docker/docker-compose.yml exec florence \
    python analysis/tools/contribution_trace.py \
        --honoree "Trump Vance Inaugural Committee, Inc." \
        --md analysis/findings/inaugural_trace.md \
        --csv analysis/findings/inaugural_trace.csv
```

Arguments:
- `--honoree STR` — exact honoree name match (case-insensitive). Repeatable.
- `--honoree-like STR` — `ILIKE` pattern (use `%` wildcards). Repeatable.
- `--year YYYY` — restrict to a filing year.
- `--md PATH` — write a Markdown report.
- `--csv PATH` — write a flat CSV with every contribution + lobbying row.

## Output structure

The Markdown report has these sections:
1. **Summary** — total dollars, donor count, top sectors.
2. **Donor itemization** — one row per (registrant, contribution date) with:
   - amount, contribution date, contribution type
   - link to LDA filing for the contribution report (`filing_uuid`)
   - registrant_id (cross-reference to lobbying side)
3. **Co-temporal lobbying activity** — for each donor, the issue codes
   they lobbied on in the same calendar quarter, the income they reported,
   and the agencies/chambers targeted.

## Why this matters (novel capability)

LDA contribution data and lobbying data are both public but live in
*separate* JSON files keyed by different IDs (contribution `filing_uuid` vs.
filing `filing_uuid`). The bridge is the `registrant.id` field. This skill
materializes that bridge as a reviewable receipt — the kind of work a
journalism intern normally builds by hand for a single story. The receipt
can be re-run any quarter against the live LDA API by changing the data
source.

## Verifiability

Every row in the CSV carries:
- `contribution_filing_uuid` (where the contribution was disclosed)
- `lobbying_filing_uuid` (the matching Q-report from the same registrant /
  same quarter, when available)
- `lobbying_filing_url` (public LDA URL)
- `contribution_date` (the actual cheque date, not the report date)

If a reviewer pastes any `filing_uuid` into
`https://lda.senate.gov/system/public/filings/{filing_uuid}` they should see
the exact source document.
