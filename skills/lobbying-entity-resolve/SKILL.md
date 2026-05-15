---
name: lobbying-entity-resolve
description: Build a canonical entity table that bridges Senate registrant_id, House senateID/houseID, and free-text organization/client names so a single organization can be tracked across both LDA disclosure systems. Use whenever a question asks about "all filings by <org>" or "total spending by <client>".
---

# Resolve lobbying entities across Senate and House LDA

The Senate and House publish the same LDA filings in different formats. The
Senate dataset has stable `registrant_id` / `client_id` integers. The House
dataset has free-text `organizationName` / `clientName` and a `senateID` of the
form `<senate_registrant_id>-<senate_client_id>`. This skill produces
deterministic mapping tables that bridge the two systems.

## When to use

- Counting filings per organization across both chambers
- Computing total lobbying spend per client across the corpus
- Auditing a House↔Senate discrepancy (different income reported, missing
  filings on one side, etc.)

## Preconditions

- `.context/db/lobbying.duckdb` exists (built by `lobbying-corpus-ingest`).

## How it works

`scripts/build_entity_tables.py` runs three deterministic passes:

1. **Senate↔House bridge.** Parse the House `senateID` column. Where the
   numeric prefix matches `senate_filings.registrant_id`, we have an exact
   match. Where it matches `registrant_house_id` we record the alternate path.

2. **Name normalization.** All client and organization names are uppercased,
   stripped of punctuation, and collapsed on whitespace. Duplicates collapse
   into a single canonical name.

3. **Cross-name aliases.** For names that don't match by ID, we use
   normalized-name equality across House `client_name_clean` and Senate
   `client.name` to attach aliases.

## Output tables (written back to the DuckDB)

```
entity_registrants(
  canonical_id BIGINT,           -- senate registrant_id, primary
  senate_registrant_id BIGINT,
  house_registrant_id BIGINT,
  canonical_name VARCHAR,
  normalized_name VARCHAR,
  n_senate_filings INTEGER,
  n_house_filings INTEGER
)

entity_clients(
  canonical_id BIGINT,           -- senate client_id, primary
  canonical_name VARCHAR,
  normalized_name VARCHAR,
  countries VARCHAR,             -- comma-separated
  n_senate_filings INTEGER,
  n_house_filings INTEGER
)

entity_name_alias(canonical_id BIGINT, alias VARCHAR, source VARCHAR)
```

## Verifiability

The `senate_registrant_id` and `house_registrant_id` columns join back to the
public LDA APIs:

- Senate: `https://lda.senate.gov/api/v1/registrants/<id>/`
- House:  `https://disclosurespreview.house.gov/?id=<id>`

For a name-only alias, the `entity_name_alias.source` column reports the
matching method (`senate_id`, `normalized_name`, etc.) so a reviewer can
re-derive it.

## Steps

```bash
python3 skills/lobbying-entity-resolve/scripts/build_entity_tables.py \
  --db .context/db/lobbying.duckdb
```

Sanity check:

```bash
duckdb .context/db/lobbying.duckdb -c "
  SELECT canonical_name, n_senate_filings, n_house_filings
  FROM entity_registrants
  ORDER BY (n_senate_filings + n_house_filings) DESC LIMIT 10;
"
```
