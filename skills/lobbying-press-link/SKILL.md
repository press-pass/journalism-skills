---
name: lobbying-press-link
description: Link a Congressional press release to the lobbying filings most likely to be relevant — by client/registrant name mentions, by ALI issue code overlap with the member's chamber and committees, and by quarter alignment. Use when a question asks "who lobbied around <press release>?" or "did this member's press releases echo any lobbying campaign?".
---

# Link press releases to lobbying filings

Press releases and LDA filings live in separate corpora. This skill builds
deterministic join rows so a single press release can be examined alongside
the lobbying that was happening at the same time on the same topic, on the
same chamber, by clients explicitly mentioned in the release.

## When to use

- "Did anyone lobby Sen. X in the same quarter she put out this release?"
- "Show press releases mentioning Boeing during the quarter Boeing lobbied
   on aviation safety."
- "Build a 'say vs. pay' table for member <bioguide_id> in 2024."

## Preconditions

- `lobbying-corpus-ingest` has populated `senate_filings`,
  `senate_activities`, `press_releases`.
- `lobbying-entity-resolve` has populated `entity_clients` and
  `entity_name_alias` (optional but improves recall).

## How it works

`scripts/build_press_links.py` writes a single `press_lobbying_links` table
that joins:

- a press-release `url`
- a Senate `filing_uuid`
- the matching `client_id` (or registrant_id)
- a `match_method` column: `client_name_exact`, `client_name_alias`,
   `registrant_name`, `issue_code_quarter`, or `bill_id`
- a `match_confidence` 0..1

It looks for:

1. **Direct name mentions** — case-insensitive substring of `client_name` (or
   any alias from `entity_name_alias`) within the press release `text`,
   restricted to client names longer than 5 characters to avoid false hits
   on acronyms.
2. **Issue + quarter alignment** — when the press release date falls within a
   Senate filing's reported quarter and the member's chamber matches one of
   the filing's `government_entities`, a low-confidence link is emitted.
3. **Bill mentions** — joins via `bill_mentions_press.bill_id` ↔
   `bill_mentions_lobbying.bill_id` (requires `lobbying-bill-extract`).

## Steps

```bash
python3 skills/lobbying-press-link/scripts/build_press_links.py \
  --db .context/db/lobbying.duckdb
```

## Verifiability

Every link row has:
- `url` (press release source-of-record)
- `filing_uuid` (Senate LDA source-of-record)
- `match_method` and the matching substring or bill_id

So a reviewer can open both records and confirm the link.

## Limits

- Direct name mentions miss aliases not in `entity_name_alias` (e.g.
  "Boeing Co." vs "The Boeing Company") — `lobbying-entity-resolve` helps.
- Issue + quarter alignment alone is weak evidence; treat as a lead.
