---
name: lobbying-bill-extract
description: Extract bill numbers (H.R., S., H.J.Res., S.J.Res., H.Res., S.Res.) and public-law citations from lobbying activity descriptions and press releases; emit a bill-mention table that joins both corpora. Use when a question is about a specific bill, or about which bills got the most lobbying attention in a period.
---

# Extract bill numbers from lobbying descriptions and press releases

Both lobbying activity descriptions (`senate_activities.description`,
`house_activities.description`) and press releases (`press_releases.text`)
mention specific bills. Pulling those mentions out lets you trace which bills
attract money, what members talk about, and where the two overlap.

## When to use

- "Who lobbied on the SAVE Act?"
- "Which bills got the most lobbying attention in Q1 2026?"
- "Show me press releases that mention a bill that was also being lobbied."

## Preconditions

`.context/db/lobbying.duckdb` exists (built by `lobbying-corpus-ingest`).

## How it works

`scripts/extract_bill_mentions.py` runs a deterministic regex over the three
text columns and writes two new tables:

- `bill_mentions_lobbying(filing_uuid, source, bill_id, bill_kind,
   bill_number, context, occurrences)`
- `bill_mentions_press(url, bill_id, bill_kind, bill_number, context,
   occurrences)`

`bill_id` is normalized to `<chamber>-<kind>-<number>-<congress>` where
congress is `118` for 2023-2024 mentions and `119` for 2025-2026 mentions.

The regex catches:
- `H.R. 1234`, `H. R. 1234`, `H.R.1234`, `HR 1234`
- `S. 1234`, `S 1234`
- `H.J.Res. 12`, `S.J.Res. 12`
- `H.Res. 5`, `S.Res. 5`
- `H. Con. Res. 7`, `S. Con. Res. 7`
- `Pub. L. 117-103` / `P.L. 117-103`

## Steps

```bash
python3 skills/lobbying-bill-extract/scripts/extract_bill_mentions.py \
  --db .context/db/lobbying.duckdb
```

Verifiability:

- `bill_mentions_lobbying.filing_uuid` joins to public LDA records.
- `bill_mentions_press.url` joins to the live press-release page.
- A reviewer can re-run the extraction; the regex is in
  `references/bill_regex.md`.

## Limits

- Mentions of named acts ("Inflation Reduction Act") without a bill number are
  not captured here — see `lobbying-press-link` for keyword joins.
- Congress assignment is derived from the filing's year only — bills
  reintroduced across Congresses will not be deduped.
