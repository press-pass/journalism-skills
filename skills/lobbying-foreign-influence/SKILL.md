---
name: lobbying-foreign-influence
description: Surface foreign-funded lobbying by joining LDA `foreign_entities` and `client.country != US` records with quarterly spending. Use when a question is about a specific country's influence, foreign-owned subsidiaries, or year-over-year shifts in foreign lobbying.
---

# Foreign-influence lobbying

Maps foreign clients and foreign-entity disclosures across Senate and House
filings. Useful both as a standalone analysis (top foreign spenders by year)
and as input to FARA cross-referencing.

## When to use

- "How much did Chinese-owned entities spend on U.S. lobbying in 2024?"
- "Which foreign-funded clients lobbied on TikTok-related bills?"
- "Compare Saudi-linked lobbying 2022 vs. 2025."

## Preconditions

- `lobbying-corpus-ingest` populated.

## How it works

`scripts/build_foreign_influence.py` writes one table:

```
foreign_lobbying(
  source VARCHAR,                   -- 'senate' or 'house'
  filing_uuid VARCHAR,              -- senate filings
  house_file VARCHAR,               -- house filings
  filing_year INTEGER,
  filing_period VARCHAR,
  registrant_name VARCHAR,
  client_name VARCHAR,
  client_country VARCHAR,
  foreign_entity_text VARCHAR,
  detected_countries VARCHAR,       -- comma-separated ISO country names
  reported_income DOUBLE
)
```

Country detection uses the LDA `countries.json` lookup plus a curated
fallback list of common country and demonym strings (e.g. "Saudi" → Saudi
Arabia, "Korean" → Korea, "Taiwanese" → Taiwan).

## Steps

```bash
python3 skills/lobbying-foreign-influence/scripts/build_foreign_influence.py \
  --db .context/db/lobbying.duckdb
```

## Verifiability

Every row carries either `filing_uuid` or `house_file` and the original
`foreign_entity_text` so a reviewer can confirm the detected country.

## Limits

- Self-reported. A U.S. shell company lobbying for a foreign parent often
  shows `client_country = US` and only mentions the parent in
  `foreign_entity_text`.
- Single-mention country tagging is heuristic — multi-country foreign
  entities are still emitted, just comma-joined.
