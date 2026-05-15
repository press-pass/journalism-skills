---
name: lda-foreign-influence
description: Map foreign-tied lobbying by country and policy issue. Produces aggregate tables and reproducible charts from `senate_foreign_entity` × `senate_activity` joins. Surfaces what each country's principals pay K Street to lobby on. Use for investigating foreign influence, FARA-adjacent topics, or country-specific lobbying campaigns.
license: MIT
compatibility: Requires Python 3.11+, duckdb, matplotlib, numpy; requires lda-setup to have been run.
metadata:
  author: PressPass
  version: "1.0"
---

The LDA requires registrants to disclose foreign entities that own or substantially control their clients. This skill turns that disclosure into a country × issue panel that an agent can scan in a single query.

## Prerequisites
- `lda-setup` has been run.

## Use

```bash
# Render the heatmap (also writes provenance markdown)
python3 skills/lda-chart/scripts/chart_foreign_issues.py
```

For ad-hoc queries:

```sql
-- Top 5 issues for Israeli-tied lobbying
SELECT a.general_issue_code_display AS issue,
       COUNT(DISTINCT f.filing_uuid) AS filings
FROM senate_foreign_entity fe
JOIN senate_filing f USING (filing_uuid)
JOIN senate_activity a USING (filing_uuid)
WHERE fe.entity_country = 'IL'
GROUP BY 1 ORDER BY filings DESC LIMIT 5;
```

```sql
-- Foreign-tied clients lobbying on a specific issue
SELECT DISTINCT f.client_name, fe.entity_name, fe.entity_country, f.filing_year
FROM senate_foreign_entity fe
JOIN senate_filing f USING (filing_uuid)
JOIN senate_activity a USING (filing_uuid)
WHERE fe.entity_country = 'CN'
  AND a.general_issue_code_display = 'Trade (domestic/foreign)'
ORDER BY f.filing_year DESC;
```

## Notes

- Country codes follow the Senate-LDA encoding (ISO 3166-1 alpha-2 in `senate_foreign_entity`; FIPS 3-letter in `house_foreign`). The chart script translates both to human-readable names.
- Filings can have multiple foreign entities; each adds a row. `COUNT(DISTINCT filing_uuid)` is the right de-dupe.
- Tax-haven jurisdictions (BVI, Cayman, Luxembourg) appear when clients route ownership through holding companies; the skill includes them so they are visible, not invisible.
