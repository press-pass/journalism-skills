# Beirut workspace — checkpoints

Working branch: `spmartin823/beirut`. Update this file every meaningful step so a fresh agent
can pick up after a context compaction.

## How to resume

```bash
cd /Users/SeamusMartin1/conductor/workspaces/journalism-skills/beirut
git checkout spmartin823/beirut
duckdb .context/db/investigation.duckdb  # tables described below
```

Data zip + decompressed `data/` live in `.context/data/` (gitignored, ~10 GB total).
The duckdb file is also gitignored — to rebuild it from raw data:

```bash
python3 .context/etl/load_press.py
python3 .context/etl/load_senate.py
python3 .context/etl/load_house.py
```

## Tables in `.context/db/investigation.duckdb`

| table | rows | what |
|---|---|---|
| press | 141,332 | Congress press releases 2022-01 → 2026-03 |
| press_member | 536 | distinct members of Congress in press corpus |
| senate_filing | 418,170 | LDA filings (Senate side) |
| senate_activity | 799,192 | one row per lobbying activity in a Senate filing |
| senate_lobbyist | 2,121,863 | lobbyists named on Senate activities (incl. covered_position) |
| senate_govt_entity | 2,016,363 | government entities targeted |
| senate_foreign_entity | 3,627 | foreign entities tied to Senate filings |
| senate_contrib_report | 155,689 | LD-203 contribution reports |
| senate_contrib_pac | 22,379 | PACs named in contribution reports |
| senate_contrib_item | 636,833 | itemized contributions |
| house_filing | 409,640 | LD-1 / LD-2 House filings |
| house_activity | 785,026 | activities on House filings |
| house_lobbyist | 1,962,951 | lobbyists on House activities |
| house_foreign | 47,983 | foreign entities tied to House registrations |

## Status log

- 2026-05-15 — Pipeline built: press, Senate, House all loaded.
- 2026-05-15 — Eval frameworks captured in `research/eval_frameworks.md`.

## Next

- Build entity-resolution skill (registrant/client name normalization).
- Build "say vs. pay" skill: join press topic → quarterly lobbying spend.
- Generate 3–5 findings-driven charts with traceable source records.
