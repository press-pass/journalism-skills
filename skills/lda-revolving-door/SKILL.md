---
name: lda-revolving-door
description: Identify lobbyists who previously held senior staff jobs in a specific Member of Congress's office, and surface their current clients and issues. Materializes a deterministic `revolving_door` table by parsing the LDA `covered_position` text field against a public roster of legislators. Use when investigating ex-staff lobbying, K Street pipelines, or Member-specific influence networks in the GAIN dataset.
license: MIT
compatibility: Requires Python 3.11+, duckdb, pandas; requires lda-setup to have been run; needs HTTPS access to unitedstates.github.io for the legislator roster (cached after first fetch).
metadata:
  author: PressPass
  version: "1.0"
---

The Lobbying Disclosure Act requires every lobbyist to disclose any "covered
position" they held in the federal government, in free text. This skill turns
that 575K-row text field into a structured `revolving_door` table that other
skills can join against.

## Prerequisites
- `lda-setup` has been run; the investigation DB exists at `.context/db/investigation.duckdb`.

## Quick start

```bash
python3 skills/lda-revolving-door/scripts/extract_members.py
```

This:
1. Pulls a canonical roster of Members 2000-present from
   `https://unitedstates.github.io/congress-legislators/` (cached under `.context/cache/`).
2. Scans every Senate `covered_position` string with **three precision-first
   regex patterns**:
   - title + first + last (e.g. "Sen. Mitch McConnell")
   - "Office of <title> <first> <last>"
   - title + last + (state) (e.g. "Rep. Cassidy (LA-6)")
3. Disambiguates surname collisions by first-name prefix or state membership;
   single-name matches without disambiguation are dropped.
4. Writes table `revolving_door` to the investigation DB.

Output is deterministic — same input → same rows.

## How to use the materialized table

```sql
-- Top 15 former bosses by distinct lobbyist count
WITH dedup AS (
  SELECT DISTINCT bioguide, member_first, member_last, lobbyist_first, lobbyist_last
  FROM revolving_door
  WHERE lobbyist_first IS NOT NULL AND lobbyist_last IS NOT NULL
)
SELECT member_first || ' ' || member_last AS member,
       bioguide, COUNT(*) AS distinct_lobbyists
FROM dedup
GROUP BY 1, 2
ORDER BY distinct_lobbyists DESC
LIMIT 15;
```

Other useful joins:
- `revolving_door rd JOIN senate_filing f USING (filing_uuid)` — drill into the
  filings that gave rise to a match (gives client_name, issue, year).
- `JOIN senate_activity a USING (filing_uuid, act_idx)` — issue codes for
  each (lobbyist, former_boss) pair.

## Reproducibility

- Roster snapshot is cached in `.context/cache/`. To re-run with the latest
  roster, delete that directory.
- Every row in `revolving_door` carries `(filing_uuid, act_idx, lobbyist_idx)` so
  any finding can be traced back to the source Senate filing UUID.

## Limits & known caveats

- Precision > recall: we drop ambiguous matches. The table understates the
  true revolving door; do not interpret a missing match as "this lobbyist had
  no Hill experience."
- Covered-position fields are free text and sometimes describe non-Congressional
  roles (federal agencies, presidential staff). Those won't match, but the
  underlying lobbyist may still appear via a separate Member-staff stint listed
  in the same string.
- **Some covered_position strings list multiple people's roles** (e.g., team
  declarations on group filings). Our parser attributes any Member named in the
  string to the named lobbyist, which can over-attribute in those cases. Always
  spot-check a flagged person via the provenance file before publishing their
  name. For aggregate counts (top-20 list), the signal is still meaningful —
  it captures both "this lobbyist worked for X" and "this lobbyist's team includes
  someone who worked for X", and both describe an office's K-Street footprint.
- The roster covers Members who served 2000+. Earlier former Members will not match.
- The Senate file is the primary source; House LDA carries similar text but is
  largely redundant for individual lobbyists who file in both chambers.

## Findings note

After running, write findings (with anchored `filing_uuid`s) to
`research/findings_revolving_door.md`. Do not claim a person is a revolving-door
case without a specific filing UUID and quoted covered_position line as evidence.
