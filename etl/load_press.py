"""Load congress press releases into duckdb.

Reads data/congress_press/**/*.jsonl, writes table `press` and `press_member`.
"""
import duckdb
import sys
from pathlib import Path

DATA = Path("/Users/SeamusMartin1/conductor/workspaces/journalism-skills/beirut/.context/data/data")
DB = Path("/Users/SeamusMartin1/conductor/workspaces/journalism-skills/beirut/.context/db/investigation.duckdb")
DB.parent.mkdir(parents=True, exist_ok=True)

con = duckdb.connect(str(DB))

# Use duckdb's native JSONL reader (union_by_name handles slight schema drift).
# Files are split across year subdirs + 2026 at root.
files = []
for yr_dir in sorted((DATA / "congress_press").iterdir()):
    if yr_dir.is_dir():
        files.extend(sorted(yr_dir.glob("*.jsonl")))
files.extend(sorted((DATA / "congress_press").glob("2026-*.jsonl")))
print(f"Loading {len(files)} press jsonl files...", file=sys.stderr)

# Build a single glob list. duckdb can take an array of file paths.
con.execute("DROP TABLE IF EXISTS press_raw")
con.execute(
    """
    CREATE TABLE press_raw AS
    SELECT * FROM read_json_auto(?, format='newline_delimited', union_by_name=true,
                                 ignore_errors=true, maximum_object_size=33554432)
    """,
    [[str(f) for f in files]],
)

n = con.execute("SELECT count(*) FROM press_raw").fetchone()[0]
print(f"Loaded {n} press releases", file=sys.stderr)

# Normalize: pull out nested member fields.
con.execute("DROP TABLE IF EXISTS press")
con.execute(
    """
    CREATE TABLE press AS
    SELECT
        url,
        title,
        CAST(date AS DATE) AS release_date,
        date_source,
        source,
        domain,
        scraper,
        member.bioguide_id AS bioguide_id,
        member.name AS member_name,
        member.party AS party,
        member.state AS state,
        member.chamber AS chamber,
        text AS body,
        length(text) AS body_len,
        collected_at,
        updated_at
    FROM press_raw
    """
)
print("Created press table", file=sys.stderr)

con.execute("CREATE INDEX IF NOT EXISTS idx_press_bioguide ON press(bioguide_id)")
con.execute("CREATE INDEX IF NOT EXISTS idx_press_date ON press(release_date)")

# Distinct members
con.execute("DROP TABLE IF EXISTS press_member")
con.execute(
    """
    CREATE TABLE press_member AS
    SELECT bioguide_id,
           any_value(member_name) AS name,
           any_value(party) AS party,
           any_value(state) AS state,
           any_value(chamber) AS chamber,
           count(*) AS n_releases,
           min(release_date) AS first_release,
           max(release_date) AS last_release
    FROM press
    WHERE bioguide_id IS NOT NULL
    GROUP BY bioguide_id
    """
)
m = con.execute("SELECT count(*) FROM press_member").fetchone()[0]
print(f"Created press_member ({m} unique members)", file=sys.stderr)

con.execute("DROP TABLE IF EXISTS press_raw")
con.close()
print("Done", file=sys.stderr)
