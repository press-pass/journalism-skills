---
description: Cross-reference a congressional press release (or member) against the LDA universe. Given a member name/bioguide_id, returns the lobbying activity targeting their chamber for the matching quarter, the top issues, the registrants, and the LD-203 contribution items going to that member's leadership PAC. Also resolves entity names mentioned in a press release back to LDA registrants/clients via deterministic fuzzy matching.
---

This is the **say vs. pay** bridge. Use it when a story claims that a member's
public messaging on a topic correlates with lobbying activity targeting their
chamber, or that a corporate name appearing in a press release also lobbied the
issuing member.

## When to use

- "Was company X lobbying Member Y in the same quarter Member Y press-released about issue Z?"
- "Did the donors named in this press release also appear in LDA contribution reports?"
- "Who lobbied this member the quarter they sponsored bill H.R. 1234?"

## How it works

The skill produces deterministic output by running SQL through DuckDB on the
indexed Parquet corpus. There are three modes:

### Mode A: member → lobbying snapshot

Inputs: `bioguide_id` (preferred) or `member_name + state + chamber`.

Outputs:
- All press releases by that member, with quarter labels
- For each quarter the member was active:
  - Total Senate LDA activities targeting the relevant chamber
  - Top 10 issue codes lobbied
  - Top 10 registrants lobbying that chamber
  - All LD-203 contribution items where `honoree_name` matches the member's
    leadership PAC (lookup table at `analysis/data/leadership_pacs.csv`)

Run:
```bash
docker compose -f analysis/docker/docker-compose.yml exec florence \
    python analysis/tools/bridge_member.py --bioguide H001075
```

### Mode B: press release → entity overlap

Inputs: a press-release URL or its text.

Outputs:
- Extracted organization mentions via `analysis/tools/extract_orgs.py`
  (uses lightweight rules + a known LDA-registrant lexicon — no LLM call
  on the body text)
- For each extracted org, the matching `sen_filings.client_name` or
  `sen_filings.registrant_name` row via `rapidfuzz` (token-set ratio ≥ 88)
- For each match, the LDA filing's issue codes and quarters

Run:
```bash
docker compose -f analysis/docker/docker-compose.yml exec florence \
    python analysis/tools/bridge_press.py --url https://...
```

### Mode C: issue-aligned correlation

Inputs: an issue keyword (e.g. "cryptocurrency", "Inflation Reduction Act").

Outputs:
- All press releases matching the keyword via ILIKE
- The most likely Senate ALI issue code (heuristic mapping in
  `analysis/data/keyword_to_ali.json`)
- Total lobbying spend on that ALI code by quarter
- Time-series correlation between press-release counts and lobbying spend

## Output rules (verifiability)

Every row in the output must carry:
- `filing_uuid` (Senate) or `filing_id` (House) for LDA-side claims
- `url` for press-release-side claims
- The exact SQL query used, so a reviewer can reproduce

When a fuzzy match is used, include the matched string AND the rapidfuzz
score. Reject matches below 88.

## Novel capability

Most off-the-shelf LDA tools give a single-table view. This skill resolves
entities **across** the press corpus and the LDA corpus, exposing the
correlated activity in one structured output — the bridge that traditional
research notebooks require manual SQL to build.
