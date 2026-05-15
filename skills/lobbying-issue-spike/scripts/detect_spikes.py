#!/usr/bin/env python3
"""Detect quarter-over-quarter spikes in lobbying income."""
from __future__ import annotations
import argparse
import os
import time
import duckdb


def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


SPIKE_BY_ISSUE = """
WITH q AS (
  SELECT
    f.filing_year, f.filing_period,
    a.general_issue_code AS issue_code,
    SUM(f.income) AS income,
    COUNT(*) AS n_filings,
    STRING_AGG(f.filing_uuid, ',') AS filing_uuids
  FROM senate_filings f
  JOIN senate_activities a USING (filing_uuid)
  WHERE f.filing_type LIKE 'Q%'
    AND f.filing_period IN ('first_quarter','second_quarter','third_quarter','fourth_quarter')
    AND f.income IS NOT NULL AND f.income > 0
    AND a.general_issue_code IS NOT NULL
  GROUP BY 1,2,3
), ordered AS (
  SELECT *,
    DENSE_RANK() OVER (PARTITION BY issue_code ORDER BY filing_year,
      CASE filing_period
        WHEN 'first_quarter' THEN 1
        WHEN 'second_quarter' THEN 2
        WHEN 'third_quarter' THEN 3
        WHEN 'fourth_quarter' THEN 4 END) AS q_idx
  FROM q
), with_lag AS (
  SELECT *,
    LAG(income) OVER (PARTITION BY issue_code ORDER BY q_idx) AS prev_income,
    AVG(income) OVER (PARTITION BY issue_code) AS hist_mean,
    STDDEV_POP(income) OVER (PARTITION BY issue_code) AS hist_std
  FROM ordered
)
SELECT
  filing_year, filing_period, issue_code,
  ic.name AS issue_name,
  income, prev_income,
  income - prev_income AS abs_delta,
  CASE WHEN prev_income > 0 THEN (income - prev_income) / prev_income ELSE NULL END AS pct_delta,
  CASE WHEN hist_std > 0 THEN (income - hist_mean) / hist_std ELSE NULL END AS z_score,
  n_filings, filing_uuids
FROM with_lag
LEFT JOIN issue_codes ic ON ic.code = with_lag.issue_code
WHERE income >= ? AND prev_income IS NOT NULL
ORDER BY abs_delta DESC
LIMIT ?;
"""

SPIKE_BY_CLIENT = """
WITH q AS (
  SELECT
    f.filing_year, f.filing_period,
    f.client_id, f.client_name,
    SUM(f.income) AS income,
    COUNT(*) AS n_filings,
    STRING_AGG(f.filing_uuid, ',') AS filing_uuids
  FROM senate_filings f
  WHERE f.filing_type LIKE 'Q%'
    AND f.filing_period IN ('first_quarter','second_quarter','third_quarter','fourth_quarter')
    AND f.income IS NOT NULL AND f.income > 0
    AND f.client_id IS NOT NULL
  GROUP BY 1,2,3,4
), ordered AS (
  SELECT *,
    DENSE_RANK() OVER (PARTITION BY client_id ORDER BY filing_year,
      CASE filing_period
        WHEN 'first_quarter' THEN 1
        WHEN 'second_quarter' THEN 2
        WHEN 'third_quarter' THEN 3
        WHEN 'fourth_quarter' THEN 4 END) AS q_idx
  FROM q
), with_lag AS (
  SELECT *,
    LAG(income) OVER (PARTITION BY client_id ORDER BY q_idx) AS prev_income,
    AVG(income) OVER (PARTITION BY client_id) AS hist_mean,
    STDDEV_POP(income) OVER (PARTITION BY client_id) AS hist_std
  FROM ordered
)
SELECT
  filing_year, filing_period, client_id, client_name,
  income, prev_income,
  income - prev_income AS abs_delta,
  CASE WHEN prev_income > 0 THEN (income - prev_income) / prev_income ELSE NULL END AS pct_delta,
  CASE WHEN hist_std > 0 THEN (income - hist_mean) / hist_std ELSE NULL END AS z_score,
  n_filings, filing_uuids
FROM with_lag
WHERE income >= ? AND prev_income IS NOT NULL
ORDER BY abs_delta DESC
LIMIT ?;
"""

SPIKE_BY_REGISTRANT = """
WITH q AS (
  SELECT
    f.filing_year, f.filing_period,
    f.registrant_id, f.registrant_name,
    SUM(f.income) AS income,
    COUNT(*) AS n_filings,
    STRING_AGG(f.filing_uuid, ',') AS filing_uuids
  FROM senate_filings f
  WHERE f.filing_type LIKE 'Q%'
    AND f.filing_period IN ('first_quarter','second_quarter','third_quarter','fourth_quarter')
    AND f.income IS NOT NULL AND f.income > 0
    AND f.registrant_id IS NOT NULL
  GROUP BY 1,2,3,4
), ordered AS (
  SELECT *,
    DENSE_RANK() OVER (PARTITION BY registrant_id ORDER BY filing_year,
      CASE filing_period
        WHEN 'first_quarter' THEN 1
        WHEN 'second_quarter' THEN 2
        WHEN 'third_quarter' THEN 3
        WHEN 'fourth_quarter' THEN 4 END) AS q_idx
  FROM q
), with_lag AS (
  SELECT *,
    LAG(income) OVER (PARTITION BY registrant_id ORDER BY q_idx) AS prev_income,
    AVG(income) OVER (PARTITION BY registrant_id) AS hist_mean,
    STDDEV_POP(income) OVER (PARTITION BY registrant_id) AS hist_std
  FROM ordered
)
SELECT
  filing_year, filing_period, registrant_id, registrant_name,
  income, prev_income,
  income - prev_income AS abs_delta,
  CASE WHEN prev_income > 0 THEN (income - prev_income) / prev_income ELSE NULL END AS pct_delta,
  CASE WHEN hist_std > 0 THEN (income - hist_mean) / hist_std ELSE NULL END AS z_score,
  n_filings, filing_uuids
FROM with_lag
WHERE income >= ? AND prev_income IS NOT NULL
ORDER BY abs_delta DESC
LIMIT ?;
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-income", type=float, default=250_000)
    ap.add_argument("--top", type=int, default=50)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    con = duckdb.connect(args.db, read_only=True)

    for name, sql in (
        ("spikes_by_issue.csv", SPIKE_BY_ISSUE),
        ("spikes_by_client.csv", SPIKE_BY_CLIENT),
        ("spikes_by_registrant.csv", SPIKE_BY_REGISTRANT),
    ):
        log(f"Computing {name}")
        rel = con.execute(sql, [args.min_income, args.top])
        path = os.path.join(args.out, name)
        rel.df().to_csv(path, index=False)
        log(f"  wrote {path}")


if __name__ == "__main__":
    main()
