---
description: Find Congressional bills that are heavily lobbied but rarely mentioned in members' own press releases ("silent lobbying"). Materializes a `bill_mentions_lobby` / `bill_mentions_lobby_house` / `bill_mentions_press` table by extracting normalized bill IDs from activity descriptions and press-release text with precision-first regex.
---

The Senate-LDA `lobbying_activities[].description`, the House-LDA `specific_issues/description`, and the Congressional press release body all reference specific bills by number ("H.R. 5376", "S. Res. 12", "H.J. Res. 5"). This skill extracts those mentions deterministically and joins them across the two corpora — the cross-corpus join is the entire point.

## Prerequisites
- `lda-setup` has been run.

## Quick start

```bash
python3 skills/lda-say-vs-pay/scripts/extract_bill_mentions.py
```

What you get:
- `bill_mentions_lobby` — 1 row per (Senate filing_uuid, act_idx, bill_id)
- `bill_mentions_lobby_house` — 1 row per (House filing_id, act_idx, bill_id)
- `bill_mentions_press` — 1 row per (press url, bill_id)

A `bill_id` is normalized to canonical form: `HR5376`, `S47`, `HRES8`, `SJRES5`, `HCONRES14`. The leading chamber letter must be followed by a literal period **or** an explicit kind word (`Res`, `J.Res.`, `Con.Res.`). This rejects spurious matches like "S 2022" (a year reference).

## How to use the materialized tables

```sql
-- Bills heavily lobbied but rarely talked about
WITH lobby AS (
  SELECT bill_id,
         COUNT(DISTINCT filing_uuid) AS senate_filings,
         (SELECT COUNT(DISTINCT filing_id) FROM bill_mentions_lobby_house h WHERE h.bill_id = l.bill_id) AS house_filings
  FROM bill_mentions_lobby l GROUP BY 1
),
press AS (
  SELECT bill_id, COUNT(*) AS press_mentions, COUNT(DISTINCT bioguide_id) AS press_members
  FROM bill_mentions_press GROUP BY 1
)
SELECT bill_id, senate_filings + house_filings AS lobby_filings,
       COALESCE(press_mentions, 0) AS press_mentions
FROM lobby LEFT JOIN press USING (bill_id)
WHERE senate_filings + house_filings >= 1000
ORDER BY lobby_filings DESC;
```

## Limits

- Bills introduced in older Congresses with the same number can appear ambiguous; the corpus's date range (2022-2026 Q1) generally limits this to one or two Congresses, but the skill does not attempt to disambiguate Congress.
- Press release authors often reference bills by name, not number ("Inflation Reduction Act" rather than "HR 5376"). That's a known gap; this skill measures the bill-number footprint specifically.
- Bills with low filing volume (<30) are excluded from charts by default; raw tables still contain them.

## Reproducibility

The extractor is pure regex — same input text always produces the same `bill_id`. Source records are anchored: every row carries the parent filing_uuid / press url.
