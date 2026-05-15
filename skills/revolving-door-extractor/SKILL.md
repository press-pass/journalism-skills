---
description: Parse the free-text `covered_position` field on LDA filings into normalized prior-role + source-office buckets. The result is a directed graph of Hill offices → K Street firms / clients, surfacing the revolving-door pipeline at scale. Pure regex + lookup, no LLM call per row — runs over 2 million rows in seconds.
---

This skill turns the messiest, most semi-structured field in LDA filings —
`covered_position` — into a queryable table. Every lobbyist who held a federal
job in the prior 20 years must disclose their previous position in this
free-text field. The text is wildly inconsistent ("LD/Deputy Chief of Staff,
Representative Doc Hastings", "Chief Counsel, US Senate Commerce Committee",
"COS House Member Office (Pearce)") but follows a small number of patterns.

## When to use

- "Map the revolving door from Senate Commerce Committee to lobby firms."
- "Which member offices feed K Street most?"
- "How many former members of Congress lobby through {firm}?"
- "What share of {firm}'s lobbyists came from {agency}?"

## How to run

```bash
docker compose -f analysis/docker/docker-compose.yml exec florence \
    python analysis/tools/revolving_door.py \
        --out /parquet/revolving_door.parquet \
        --md analysis/findings/revolving_door.md
```

Inputs: none (reads `sen_lobbyists` and `house_lobbyists` parquet directly).

Outputs:
- A Parquet table at `/parquet/revolving_door.parquet` with one row per
  (filing, lobbyist, prior_role, source_office) tuple. Columns:
    - `filing_uuid` (Senate) or `filing_id` (House)
    - `lobbyist_first`, `lobbyist_last`
    - `registrant_name`, `client_name`
    - `prior_role` (normalized: CHIEF_OF_STAFF, LD, LA, COUNSEL, MEMBER, ...)
    - `source_office_type` (HOUSE_MEMBER, SENATE_MEMBER, HOUSE_COMMITTEE, SENATE_COMMITTEE, AGENCY, WH, FORMER_MEMBER, OTHER)
    - `source_office` (best-guess specific office, e.g., "Senate Commerce Committee")
    - `raw_text` (the original `covered_position` string, for audit)
- A Markdown summary at `--md` with top flows and counts.

## Parsing approach (deterministic)

1. **Role detection** — case-insensitive regex against a curated dictionary
   of titles. Multiple roles can match a single row; the most senior wins
   (Chief of Staff > Legislative Director > Legislative Assistant > Counsel >
   Staff Assistant). See `analysis/data/roles.json`.
2. **Source-office detection** — pattern groups for:
   - `Senate ([A-Z][a-z]+\s)+ Committee` → SENATE_COMMITTEE
   - `House ([A-Z][a-z]+\s)+ Committee` → HOUSE_COMMITTEE
   - `Sen(\.)? [A-Z][a-z]+` → SENATE_MEMBER (member name extracted)
   - `Rep(\.)? [A-Z][a-z]+` → HOUSE_MEMBER
   - `Former Member of Congress` → FORMER_MEMBER
   - Specific agencies enumerated (USDA, USTR, DOC, DOD, EPA, ...)
   - White House / OMB / NSC / EOP → WH
3. **Member-name resolution** — if a member name is detected, fuzzy match
   against the Press corpus' member roster to attach a `bioguide_id`.

## Verifiability

Every parsed row preserves the raw input string. Editors can sample any 20
rows and audit by eyeballing `(raw_text, prior_role, source_office)`. The
script also emits a confusion summary (rows where the detector fired in
multiple buckets) for review.

## Novel capability

The traditional approach is to read a few hundred high-profile lobbyists by
hand. This skill scales the same analysis to all ~2 million lobbyist
appearances across the Senate + House corpora and turns it into a graph that
can answer "which K Street firms employ the most former Senate Commerce
staff?" in one SQL query.
