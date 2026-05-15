# DuckDB schema for the GAIN lobbying corpus

Built by `scripts/build_db.py`. Every table has at least one column that joins
back to a public source-of-record so claims can be audited.

## senate_filings

| Column | Type | Source-of-record |
|---|---|---|
| filing_uuid | VARCHAR PK | https://lda.senate.gov/system/public/filing/<uuid>/print |
| filing_type | VARCHAR | code from `constants/filing_types.json` |
| filing_type_display | VARCHAR | human label |
| filing_year | INTEGER | |
| filing_period | VARCHAR | Q1..Q4, MM, YE, RR |
| dt_posted | TIMESTAMP | when posted to lda.senate.gov |
| income | DOUBLE | self-reported |
| expenses | DOUBLE | self-reported |
| registrant_id, registrant_name | BIGINT, VARCHAR | LDA registrant |
| client_id, client_name, client_state, client_country | | LDA client |
| termination_date | VARCHAR | for terminations |

## senate_activities

One row per lobbying activity inside a filing.

| Column | Type |
|---|---|
| filing_uuid | VARCHAR |
| activity_idx | INTEGER |
| general_issue_code | VARCHAR — 3-letter ALI code |
| description | VARCHAR — free text, often names bills/agencies |
| foreign_entity_issues | VARCHAR — JSON when present |

## senate_lobbyists

| filing_uuid | activity_idx | lobbyist_id | first_name | last_name | full_name |
| covered_position | VARCHAR — prior gov role text |
| new_lobbyist | BOOLEAN |

## senate_gov_entities

Which government agencies/chambers an activity targeted.

## senate_contribution_items

LD-203 contribution line items. Includes contributor, payee, honoree, amount,
contribution_type, date.

## house_filings

| house_file VARCHAR PK | original XML filename, joins to disclosurespreview.house.gov |
| doc_type | LD1 (registration) or LD2 (quarterly) |
| filing_period | Q1..Q4 or RR |
| filing_year | INTEGER |
| senate_id | VARCHAR — bridge to Senate filings |
| house_id | VARCHAR |
| organization_name | VARCHAR — registrant |
| client_name | VARCHAR |
| client_state, client_country | VARCHAR |
| income, expenses, method | VARCHAR (kept as text — House encodes ranges) |
| specific_issues | VARCHAR — concatenated free-text, often names bills |
| ali_codes | VARCHAR — comma-separated 3-letter codes |
| government_entities | VARCHAR — semicolon-separated |
| foreign_entities | VARCHAR — semicolon-separated |

## house_lobbyists

| house_file | first_name | last_name | suffix | covered_position | new_lobbyist |

## press_releases

| url VARCHAR | joins to the live page |
| title, date (DATE), date_source, source, domain, scraper |
| bioguide_id | VARCHAR — joins to Congress.gov |
| member_name, party, state, chamber |
| text TEXT — full body |

## Lookups

- `issue_codes(code, name)` — decode ALI codes
- `filing_types(code, name)` — decode Q1/MM/YE/etc.
- `government_entities_lookup(id, name)`
- `states_lookup(code, name)`
- `countries_lookup(code, name)`
