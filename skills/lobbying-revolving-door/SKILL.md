---
name: lobbying-revolving-door
description: Extract and structure prior-government-role text from lobbyist `covered_position` fields to surface revolving-door patterns. Use when a question asks about former staff, ex-members, or specific agency alumni now lobbying.
---

# Find revolving-door lobbyists

The LDA requires lobbyists to disclose prior covered positions. The text is
free-form — "Chief of Staff to Sen. Smith", "Counsel, House Energy &
Commerce", "Deputy Assistant Secretary, Treasury" — which is gold for finding
former staff now lobbying, but unusable without structure.

## When to use

- "Which Senate offices send the most staff into K Street?"
- "Who at Acme Lobbying Co. used to work at <agency>?"
- "Show me lobbyists who worked for a specific member."

## Preconditions

`.context/db/lobbying.duckdb` exists with `senate_lobbyists`
and `house_lobbyists` populated.

## How it works

`scripts/parse_covered_positions.py` runs deterministic regexes against the
free-text `covered_position` column to extract:

- prior **chamber** (`House`, `Senate`, `Executive`, `Judicial`, `Independent`)
- prior **role family** (Member, Chief of Staff, Legislative Director,
  Counsel, Assistant Secretary, Senior Advisor, etc.)
- prior **principal**: a member name or agency name when present
- a `confidence` score (0-1) for the parse

It writes a single table:

```
revolving_door_positions(
  lobbyist_id BIGINT,            -- for senate_lobbyists
  house_file VARCHAR,            -- nullable; alternate join for House-only
  full_name VARCHAR,
  source VARCHAR,                -- 'senate' or 'house'
  filing_uuid VARCHAR,
  raw_text VARCHAR,
  chamber VARCHAR,
  role_family VARCHAR,
  principal_name VARCHAR,
  confidence DOUBLE
)
```

## Steps

```bash
python3 skills/lobbying-revolving-door/scripts/parse_covered_positions.py \
  --db .context/db/lobbying.duckdb
```

## Verifiability

Every row has both `filing_uuid` (Senate) or `house_file` (House) plus
`raw_text` — a reviewer can audit the parse by comparing `principal_name` /
`role_family` / `chamber` against `raw_text` and the original filing.

## Limits

The parser is heuristic and stays conservative: when in doubt it returns
chamber/role only and leaves `principal_name` null. Confidence < 0.5 should be
treated as a lead, not a fact.
