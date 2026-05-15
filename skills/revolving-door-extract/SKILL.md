---
description: Extract structured revolving-door edges (lobbyist → member of Congress) from the free-text covered_position disclosures in Senate LDA filings. Each edge is sourced to its evidence text and filing_uuid. Use when investigating which K Street lobbyists are ex-Hill staffers and which members' offices supply the most lobbyists. Input: paths to senate_lobbyists.parquet and press.parquet.
---

You parse the messy, self-reported `covered_position` field on Senate lobbyist registrations
into structured `(lobbyist_id, bioguide_id, evidence_text)` edges that downstream queries can
join to filings, contributions, and press releases.

This is a novel capability — there is no public structured table of Hill alumni in K Street
that traces back to specific LDA records.

## Inputs

- `--lobbyists_parquet` — output of `lobbying-corpus-build` (`senate_lobbyists.parquet`).
- `--press_parquet` — output of `press-corpus-build` (`press.parquet`). Used to build the
  member surname → bioguide_id lookup.
- `--out` — destination parquet path.

## Algorithm

1. Build a unique-surname lookup from the press corpus. Only surnames that map to exactly one
   `bioguide_id` are kept. This avoids attributing every `Smith` to a single member.
2. For each lobbyist with non-blank `covered_position`, run a regex over the text looking for
   the pattern `(Sen|Senator|Rep|Representative|Cong[…])\.? + Name`.
3. Take the LAST token of the captured name as the surname.
4. If that surname is in the unique-surname lookup, emit an edge with the full evidence text
   and the lobbyist's `filing_uuid`.

## Step 1: Run the extractor

```bash
docker run --rm \
  -v "$(realpath <PARQUET_DIR>):/parquet:ro" \
  -v "$(realpath <OUT_DIR>):/out" \
  -v "$(realpath skills/revolving-door-extract/scripts):/scripts:ro" \
  lobbypress-analysis \
  python /scripts/extract.py \
    --lobbyists_parquet /parquet/senate_lobbyists.parquet \
    --press_parquet /parquet/press.parquet \
    --out /out/revolving_door_edges.parquet
```

## Step 2: Query it

```python
import polars as pl
e = pl.read_parquet("revolving_door_edges.parquet")
# Top 20 members whose offices supplied the most lobbyists
print(e.unique(subset=["lobbyist_id", "bioguide_id"])
       .group_by(["member_name", "party", "state", "chamber"])
       .len().sort("len", descending=True).head(20))
# Find specific evidence
print(e.filter(pl.col("member_name") == "Chuck Schumer")
       .select(["lobbyist_first", "lobbyist_last", "evidence_text", "filing_uuid"])
       .head(10))
```

## Caveats — must be flagged in any story

- `covered_position` is self-reported free text. Some lobbyists list a position they held for
  one month a decade ago; others omit it entirely.
- Surnames that map to current AND retired members of Congress (e.g., `Brown` → Shontel Brown
  + the historical Sherrod Brown / Scott Brown) will over-credit the *current* officeholder.
  Mitigate by re-running the extractor with an expanded historical bioguide list from
  congress.gov bulk data.
- The chamber attribution is the **current** member's chamber, not necessarily the chamber the
  lobbyist worked in.
- "Senator" and "Representative" appearances in the same record may produce two edges; the
  output is deliberately not deduplicated so downstream code can decide how to count.

## Why this is useful

- **Bulk attribution**: Quickly identify which member offices are the largest staffing
  pipeline to K Street.
- **Targeted reporting**: Drill into one member ("show me every lobbyist who claims to have
  worked for Sen. McConnell, with the specific filing and registrant").
- **Cross-corpus joins**: Combine these edges with `senate_filings` (income, client) to ask
  "how much lobbying revenue do former McConnell staffers move?"
