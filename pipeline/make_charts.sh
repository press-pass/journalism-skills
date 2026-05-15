#!/usr/bin/env bash
# Generate all charts for the GAIN findings report.
# Run after queries.sql has produced the CSVs.

set -euo pipefail

SRC="Senate LDA + House Clerk LDA + Congress.gov press scrape (data_manual.md, GAIN corpus)"
CHART="python3 skills/lobbying-chart/scripts/chart.py"

mkdir -p .context/charts

# Chart 1: Top 25 lobbying clients in 2025
$CHART --kind bar \
  --in .context/findings/f1_top25_clients_2025.csv \
  --out .context/charts/c1_top25_clients_2025.png \
  --x client_name --y total_income_2025_usd \
  --title "Top 25 lobbying clients by total 2025 reported income" \
  --subtitle "Senate LDA quarterly filings, 2025" \
  --source "$SRC" --money --top 25

# Chart 2: Spend by issue, top 10 issues over 2022-2025
python3 -c "
import pandas as pd
df = pd.read_csv('.context/findings/f2_spend_by_issue_year.csv')
df = df[df['filing_year'] <= 2025]  # 2026 is Q1-only — exclude from full-year chart
top_codes = df.groupby('issue')['spend'].sum().nlargest(8).index.tolist()
out = df[df['issue'].isin(top_codes)].copy()
out.to_csv('.context/charts/_top_issues.csv', index=False)
"
$CHART --kind line \
  --in .context/charts/_top_issues.csv \
  --out .context/charts/c2_top_issues_over_time.png \
  --x filing_year --y spend --group-col issue \
  --title "Top 8 lobbying issues by yearly spend, 2022–2025" \
  --subtitle "Senate LDA quarterly filings, full-year totals" \
  --source "$SRC" --money

# Chart 3: Foreign lobbying by country (2025)
python3 -c "
import pandas as pd
df = pd.read_csv('.context/findings/f3_foreign_spend_by_country_year.csv')
df_2025 = df[df['filing_year']==2025].copy()
df_2025 = df_2025.assign(country=df_2025['detected_countries'].str.split(',').str[0])
agg = df_2025.groupby('country', as_index=False)['total_income_usd'].sum().nlargest(20, 'total_income_usd')
agg.to_csv('.context/charts/_foreign_2025.csv', index=False)
"
$CHART --kind bar \
  --in .context/charts/_foreign_2025.csv \
  --out .context/charts/c3_foreign_2025_top20.png \
  --x country --y total_income_usd \
  --title "Top 20 foreign-funded U.S. lobbying tracks, 2025" \
  --subtitle "Detected via client.country + foreign_entity_issues in Senate LDA filings" \
  --source "$SRC" --money --top 20

# Chart 4: Revolving door — most-active by chamber
python3 -c "
import pandas as pd
df = pd.read_csv('.context/findings/f4_revolving_door_top.csv')
agg = df.groupby('chamber', as_index=False).agg(n_filings=('n_senate_filings','sum'))
agg.to_csv('.context/charts/_rev_door_chamber.csv', index=False)
"
$CHART --kind bar \
  --in .context/charts/_rev_door_chamber.csv \
  --out .context/charts/c4_revolving_door_chamber.png \
  --x chamber --y n_filings \
  --title "Where the highest-confidence revolving-door lobbyists came from" \
  --subtitle "Parsed from LDA covered_position text; confidence ≥ 0.7; 5+ filings each" \
  --source "$SRC"

# Chart 5: Quarterly spend total trajectory
python3 -c "
import pandas as pd
df = pd.read_csv('.context/findings/f7_quarterly_total_spend.csv')
quarter_map = {'first_quarter':1, 'second_quarter':2, 'third_quarter':3, 'fourth_quarter':4}
df['q_idx'] = df['filing_period'].map(quarter_map)
df['period_label'] = df['filing_year'].astype(str) + ' Q' + df['q_idx'].astype(str)
df['date'] = pd.to_datetime(df['filing_year'].astype(str) + '-' + (df['q_idx']*3-2).astype(str) + '-01')
df.to_csv('.context/charts/_quarterly.csv', index=False)
"
$CHART --kind area_stacked \
  --in .context/charts/_quarterly.csv \
  --out .context/charts/c5_quarterly_total.png \
  --x date --y total_income_usd \
  --title "Total quarterly lobbying spend, 2022 Q1–2025 Q4" \
  --subtitle "Sum of reported Senate LDA income per quarter" \
  --source "$SRC" --money

# Chart 6: Top bills lobbied in 2025 (bar)
$CHART --kind bar \
  --in .context/findings/f5_top_bills_lobbied_2025.csv \
  --out .context/charts/c6_top_bills_2025.png \
  --x bill_id --y n_clients \
  --title "Top 30 bills by distinct lobbying clients, 2025" \
  --subtitle "Bill numbers extracted from senate_activities.description" \
  --source "$SRC" --top 30

# Chart 7: Press release activity by month/party
python3 -c "
import pandas as pd
df = pd.read_csv('.context/findings/f9_press_by_party_month.csv')
df['date'] = pd.to_datetime(dict(year=df['year'].astype(int), month=df['month'].astype(int), day=1))
df = df[df['year'] >= 2022]
agg = df.groupby(['date', 'party'], as_index=False)['n_releases'].sum()
agg.to_csv('.context/charts/_press_party.csv', index=False)
"
$CHART --kind line \
  --in .context/charts/_press_party.csv \
  --out .context/charts/c7_press_by_party_month.png \
  --x date --y n_releases --group-col party \
  --title "Congressional press releases by month and party, 2022–2026 Q1" \
  --subtitle "Scraped from *.house.gov and *.senate.gov" \
  --source "$SRC"

# Chart 8: Bills present in BOTH press releases and lobbying
$CHART --kind scatter \
  --in .context/findings/f6_bills_press_and_lobbying_2025.csv \
  --out .context/charts/c8_bills_press_v_lobby.png \
  --x n_press --y n_lobby --label-col bill_id \
  --title "Bills mentioned in both press releases and lobbying filings, 2025" \
  --subtitle "Each dot is a single bill; axes count distinct press URLs vs. distinct LDA filings" \
  --source "$SRC"

# Chart 9: New registrations per quarter
python3 -c "
import pandas as pd
df = pd.read_csv('.context/findings/f8_new_registrations_per_quarter.csv')
qmap = {'first_quarter':1,'second_quarter':2,'third_quarter':3,'fourth_quarter':4}
df = df[df['filing_period'].isin(qmap)]
df['q_idx'] = df['filing_period'].map(qmap)
df['date'] = pd.to_datetime(df['filing_year'].astype(str) + '-' + (df['q_idx']*3-2).astype(str) + '-01')
df.to_csv('.context/charts/_new_reg.csv', index=False)
"
$CHART --kind line \
  --in .context/charts/_new_reg.csv \
  --out .context/charts/c9_new_registrations.png \
  --x date --y new_registrants \
  --title "New Senate LDA registrations per quarter, 2022 Q1–2026 Q1" \
  --subtitle "Filing_type = 'RR' (initial registration)" \
  --source "$SRC"

# Chart 10: HR-1 lobbying — top clients
$CHART --kind bar \
  --in .context/findings/f12_hr1_top_clients.csv \
  --out .context/charts/c10_hr1_top_clients.png \
  --x client_name --y hr1_supporting_income \
  --title "Top 25 lobbying clients whose 2025 filings mention H.R. 1 (119th)" \
  --subtitle "Filings include H.R. 1 in the activity description; income is total filing income" \
  --source "$SRC" --money --top 25

echo "Charts written to .context/charts/"
ls -la .context/charts/*.png
