# Canned queries against the GAIN DuckDB

Every query returns rows that include a source-of-record column so claims can
be traced back to a public filing.

## Top spenders by issue, by year

```sql
SELECT
  filing_year,
  issue_codes.name AS issue,
  client_name,
  SUM(income) AS reported_income_usd,
  COUNT(*) AS n_filings
FROM senate_filings f
JOIN senate_activities a USING (filing_uuid)
LEFT JOIN issue_codes ON issue_codes.code = a.general_issue_code
WHERE filing_type LIKE 'Q%' AND income > 0
GROUP BY 1,2,3
HAVING reported_income_usd > 1000000
ORDER BY filing_year, issue, reported_income_usd DESC;
```

## Senate ↔ House reconciliation

```sql
SELECT
  s.filing_year, s.client_name AS senate_client, h.client_name AS house_client,
  s.income, s.expenses, h.income AS h_income, h.expenses AS h_expenses,
  s.filing_uuid, h.house_file
FROM senate_filings s
JOIN house_filings h ON h.senate_id = (
    /* registrant_id in House XML maps to senate's senate_registrant_id when present */
    s.registrant_id::VARCHAR
)
WHERE s.filing_year = h.filing_year;
```

## Press releases mentioning a client around the time it was lobbying

```sql
WITH client_quarters AS (
  SELECT DISTINCT client_name, filing_year, filing_period
  FROM senate_filings WHERE client_name = 'Boeing'
)
SELECT pr.date, pr.member_name, pr.title, pr.url
FROM press_releases pr
WHERE pr.text ILIKE '%boeing%'
ORDER BY pr.date;
```

## Revolving-door lobbyists

```sql
SELECT full_name, covered_position, count(*) AS n_filings
FROM senate_lobbyists
WHERE covered_position IS NOT NULL AND length(covered_position) > 0
GROUP BY 1,2
ORDER BY n_filings DESC
LIMIT 50;
```

## Issue-code spike detection per quarter

```sql
WITH per_q AS (
  SELECT filing_year, filing_period, a.general_issue_code,
         SUM(income) AS income_q
  FROM senate_filings f JOIN senate_activities a USING (filing_uuid)
  WHERE filing_type LIKE 'Q%' AND income > 0
  GROUP BY 1,2,3
)
SELECT *, income_q - LAG(income_q) OVER (
  PARTITION BY general_issue_code ORDER BY filing_year, filing_period
) AS qoq_delta
FROM per_q ORDER BY general_issue_code, filing_year, filing_period;
```
