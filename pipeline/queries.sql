-- =====================================================================
-- Investigation queries. Each writes a small CSV under .context/findings/
-- so a reviewer can open the file and audit it row-by-row. Every row
-- carries a source-of-record column (filing_uuid, house_file, or URL).
-- =====================================================================

-- F1. Top 25 lobbying clients in 2025 by total reported income (Q1-Q4)
-- Excludes obvious sovereign-citizen fake filings; see f1b output and
-- FINDINGS Section "Data quality" for the LOC Community Association case.
COPY (
  SELECT
    client_name,
    SUM(income) AS total_income_2025_usd,
    COUNT(DISTINCT filing_uuid) AS n_filings,
    STRING_AGG(DISTINCT registrant_name, ' | ') AS registrants,
    STRING_AGG(filing_uuid, ',') AS filing_uuids
  FROM senate_filings
  WHERE filing_year = 2025 AND filing_type LIKE 'Q%' AND income IS NOT NULL AND income > 0
    AND client_name NOT LIKE 'STATE OF LOC%'
  GROUP BY client_name
  ORDER BY total_income_2025_usd DESC
  LIMIT 25
) TO '.context/findings/f1_top25_clients_2025.csv' (HEADER, DELIMITER ',');

-- F1b. Data-quality finding: sovereign-citizen "LOC Nation" $20M-per-quarter filings
COPY (
  SELECT
    f.filing_uuid, f.filing_type, f.filing_period, f.income, f.expenses,
    f.registrant_name, f.client_name, f.dt_posted,
    'https://lda.senate.gov/filings/public/filing/' || f.filing_uuid || '/print/' AS public_url
  FROM senate_filings f
  WHERE f.client_name LIKE 'STATE OF LOC%'
  ORDER BY income DESC NULLS LAST
) TO '.context/findings/f1b_loc_nation_filings.csv' (HEADER);

-- F2. Top 20 issue codes by total spend, 2022-2025 vs 2026Q1 growth
COPY (
  WITH per_year AS (
    SELECT
      a.general_issue_code AS code,
      ic.name AS issue,
      f.filing_year,
      SUM(f.income) AS spend
    FROM senate_filings f
    JOIN senate_activities a USING (filing_uuid)
    LEFT JOIN issue_codes ic ON ic.code = a.general_issue_code
    WHERE f.filing_type LIKE 'Q%' AND f.income IS NOT NULL AND f.income > 0
    GROUP BY 1,2,3
  )
  SELECT code, issue, filing_year, spend
  FROM per_year
  WHERE code IS NOT NULL
  ORDER BY filing_year, spend DESC
) TO '.context/findings/f2_spend_by_issue_year.csv' (HEADER);

-- F3. Foreign-client lobbying by detected country, 2022-2025
COPY (
  SELECT
    detected_countries,
    filing_year,
    COUNT(*) AS n_filings,
    SUM(reported_income) AS total_income_usd
  FROM foreign_lobbying
  WHERE detected_countries IS NOT NULL AND filing_year IS NOT NULL
    AND source = 'senate'
  GROUP BY 1,2
  HAVING total_income_usd > 0
  ORDER BY filing_year DESC, total_income_usd DESC
) TO '.context/findings/f3_foreign_spend_by_country_year.csv' (HEADER);

-- F4. Top revolving-door lobbyists (highest-confidence parses)
COPY (
  SELECT
    full_name,
    chamber,
    role_family,
    principal_name,
    AVG(confidence) AS avg_confidence,
    COUNT(DISTINCT filing_uuid) AS n_senate_filings,
    COUNT(DISTINCT house_file) AS n_house_filings,
    STRING_AGG(DISTINCT raw_text, ' || ') AS raw_examples
  FROM revolving_door_positions
  WHERE confidence >= 0.7
  GROUP BY full_name, chamber, role_family, principal_name
  HAVING n_senate_filings + n_house_filings >= 5
  ORDER BY n_senate_filings + n_house_filings DESC
  LIMIT 50
) TO '.context/findings/f4_revolving_door_top.csv' (HEADER);

-- F5. Most-lobbied bills in 2025 (by # of distinct clients)
COPY (
  SELECT
    bill_id,
    bill_kind,
    bill_number,
    COUNT(DISTINCT f.client_id) AS n_clients,
    COUNT(DISTINCT bm.filing_uuid) AS n_filings,
    SUM(f.income) AS total_income_supporting,
    STRING_AGG(DISTINCT f.client_name, ' | ') AS sample_clients
  FROM bill_mentions_lobbying bm
  JOIN senate_filings f ON f.filing_uuid = bm.filing_uuid
  WHERE bm.source = 'senate' AND bm.filing_year = 2025 AND bm.bill_kind IN ('HR', 'S')
  GROUP BY 1,2,3
  HAVING n_clients >= 8
  ORDER BY n_clients DESC
  LIMIT 30
) TO '.context/findings/f5_top_bills_lobbied_2025.csv' (HEADER);

-- F6. Bills that show up in both press releases AND lobbying for same year
COPY (
  WITH p AS (
    SELECT bill_id, COUNT(DISTINCT url) AS n_press, MIN(date) AS first_press
    FROM bill_mentions_press WHERE filing_year = 2025 GROUP BY 1
  ), l AS (
    SELECT bill_id, COUNT(DISTINCT filing_uuid) AS n_lobby
    FROM bill_mentions_lobbying WHERE filing_year = 2025 AND source = 'senate' GROUP BY 1
  )
  SELECT p.bill_id, p.n_press, l.n_lobby, p.first_press
  FROM p JOIN l USING (bill_id)
  WHERE p.bill_id LIKE '119-%' OR p.bill_id LIKE '118-%'
  ORDER BY l.n_lobby + p.n_press DESC
  LIMIT 40
) TO '.context/findings/f6_bills_press_and_lobbying_2025.csv' (HEADER);

-- F7. Quarterly trajectory of lobbying spend total (all years)
COPY (
  SELECT
    filing_year,
    filing_period,
    SUM(income) AS total_income_usd,
    COUNT(DISTINCT filing_uuid) AS n_filings,
    COUNT(DISTINCT client_id) AS n_clients
  FROM senate_filings
  WHERE filing_type LIKE 'Q%' AND filing_period IN ('first_quarter','second_quarter','third_quarter','fourth_quarter')
    AND income IS NOT NULL AND income > 0
  GROUP BY filing_year, filing_period
  ORDER BY filing_year,
    CASE filing_period WHEN 'first_quarter' THEN 1 WHEN 'second_quarter' THEN 2 WHEN 'third_quarter' THEN 3 ELSE 4 END
) TO '.context/findings/f7_quarterly_total_spend.csv' (HEADER);

-- F8. New registrants per quarter (lobbying entry rate)
COPY (
  SELECT
    filing_year,
    filing_period,
    COUNT(DISTINCT registrant_id) AS new_registrants,
    COUNT(DISTINCT client_id) AS new_clients
  FROM senate_filings
  WHERE filing_type = 'RR'
  GROUP BY 1, 2
  ORDER BY 1, 2
) TO '.context/findings/f8_new_registrations_per_quarter.csv' (HEADER);

-- F9. Press-release activity by chamber + party + month
COPY (
  SELECT
    EXTRACT(YEAR FROM date) AS year,
    EXTRACT(MONTH FROM date) AS month,
    chamber,
    party,
    COUNT(*) AS n_releases
  FROM press_releases
  WHERE date IS NOT NULL AND party IS NOT NULL
  GROUP BY 1,2,3,4
  ORDER BY 1,2
) TO '.context/findings/f9_press_by_party_month.csv' (HEADER);

-- F10. House↔Senate income discrepancies (same senate_id, big delta)
COPY (
  WITH paired AS (
    SELECT
      h.house_file,
      h.organization_name,
      h.client_name,
      h.filing_year,
      h.filing_period,
      h.income AS house_income,
      s.income AS senate_income,
      s.filing_uuid
    FROM house_filings h
    JOIN senate_filings s
      ON s.registrant_id = h.senate_registrant_id
     AND s.filing_year = h.filing_year
     AND CASE h.filing_period
            WHEN 'Q1' THEN 'first_quarter'
            WHEN 'Q2' THEN 'second_quarter'
            WHEN 'Q3' THEN 'third_quarter'
            WHEN 'Q4' THEN 'fourth_quarter'
         END = s.filing_period
     AND lower(s.client_name) = lower(h.client_name)
    WHERE h.income IS NOT NULL AND s.income IS NOT NULL
      AND h.filing_year >= 2024
  )
  SELECT *, ABS(house_income - senate_income) AS abs_diff
  FROM paired
  WHERE ABS(house_income - senate_income) > 50000
  ORDER BY abs_diff DESC
  LIMIT 50
) TO '.context/findings/f10_house_senate_discrepancies.csv' (HEADER);

-- F11. PACs honoring members: top members by total contribution count
COPY (
  SELECT
    honoree_name,
    COUNT(*) AS n_contributions,
    SUM(amount) AS total_amount_usd,
    COUNT(DISTINCT registrant_id) AS n_distinct_registrants
  FROM senate_contribution_items
  WHERE honoree_name IS NOT NULL AND amount IS NOT NULL AND filing_year >= 2024
  GROUP BY 1
  ORDER BY total_amount_usd DESC
  LIMIT 30
) TO '.context/findings/f11_top_honoree_members.csv' (HEADER);
