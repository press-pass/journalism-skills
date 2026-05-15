---
description: One-time bootstrap that loads the GAIN lobbying + press-release corpus into a local duckdb investigation database. Run before any other lda-* skill.
---

This skill builds `investigation.duckdb` from the raw GAIN dataset
(Congress press releases JSONL, Senate LDA JSON, House LDA XML). It is
idempotent — running it twice produces the same database. All downstream
skills (`lda-query`, `lda-revolving-door`, `lda-foreign-influence`,
`lda-say-vs-pay`) read from this database.

## Inputs

The skill expects the decompressed dataset at `$LDA_DATA_DIR` (defaults to
`.context/data/data/`). If the data is not present, the skill will tell the
user where to fetch it from
(`https://drive.google.com/drive/folders/1HhcFbD4Zf0cOD0Ib-89aV4zLoylJ1UiP`).

## What to do

1. Verify the data is present:

   ```bash
   ls "${LDA_DATA_DIR:-.context/data/data}"
   # Expect: congress_press/ senate/ house/
   ```

   If the directories are missing, tell the user to run `bash skills/lda-setup/scripts/fetch_data.sh` first.

2. Run the loader:

   ```bash
   bash skills/lda-setup/scripts/build.sh
   ```

   This runs `etl/load_press.py`, `etl/load_senate.py`, and `etl/load_house.py`
   sequentially and writes `.context/db/investigation.duckdb`.

3. Verify with the sanity check:

   ```bash
   python3 skills/lda-setup/scripts/sanity_check.py
   ```

   Expect 14 tables and ~141K press, ~418K senate filings, ~410K house filings.

4. Report the table inventory to the user as a summary table.

## Notes

- Build time is ~2 minutes on a 2024 MacBook Pro (parallel XML parse).
- Output DB is ~400 MB.
- Source data is gitignored (10+ GB).
- The build never overwrites raw data; it only reads.
