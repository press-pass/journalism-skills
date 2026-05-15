-- ============================================================
-- Cross-check queries to manually verify a small number of
-- claims against the public LDA records. Output the source
-- URLs so a reviewer can open them directly.
-- ============================================================

-- For each finding, emit a "spot-check" row with the public URL
-- to the filing on lda.senate.gov or disclosurespreview.house.gov

-- The State of Loc Nation $60M anomaly
.print "=== STATE OF LOC NATION GLOBAL PUBLIC BENEFIT CORP ==="
SELECT
  filing_uuid,
  filing_type,
  filing_period,
  income,
  expenses,
  registrant_name,
  'https://lda.senate.gov/filings/public/filing/' || filing_uuid || '/print/' AS public_url
FROM senate_filings
WHERE client_name LIKE 'STATE OF LOC%'
ORDER BY income DESC NULLS LAST LIMIT 5;

-- Nippon Steel — relevant to 2024-2025 US Steel acquisition story
.print "\n=== NIPPON STEEL CORPORATION ==="
SELECT
  filing_year, filing_period, income, registrant_name,
  'https://lda.senate.gov/filings/public/filing/' || filing_uuid || '/print/' AS public_url
FROM senate_filings
WHERE client_name = 'NIPPON STEEL CORPORATION' AND filing_year >= 2024
ORDER BY filing_year, filing_period;

-- Tencent America
.print "\n=== TENCENT AMERICA ==="
SELECT
  filing_year, filing_period, income, registrant_name,
  'https://lda.senate.gov/filings/public/filing/' || filing_uuid || '/print/' AS public_url
FROM senate_filings
WHERE client_name LIKE 'TENCENT%' AND filing_year >= 2024
ORDER BY filing_year, filing_period;
