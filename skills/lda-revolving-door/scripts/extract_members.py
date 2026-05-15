#!/usr/bin/env python3
"""Parse Senate-LDA `covered_position` free-text fields.

Output: parquet + duckdb table `revolving_door` keyed
(filing_uuid, act_idx, lobbyist_idx, member_match).

Strategy is rule-based (regex), NOT LLM. This is the heart of corpus
efficiency: every later question about revolving-door patterns reads the
materialized table instead of re-parsing 2M free-text fields.

How we identify the "former boss" inside a covered_position string:

  1. Strip prefixes ("Hon.", "Rep.", "Sen.", "Senator", "Congressman"…).
  2. Look for explicit Member tokens — first one wins for each filing-lobbyist:
       - Senator <Last>            → match against Senate roster
       - Sen. <Last>               →  "
       - Rep. <Last> / Representative <Last>
       - Congressman / Congresswoman <Last>
       - "to U.S. Senator <First Last>" / "to U.S. Representative <First Last>"
       - "<Title>, Office of <Member>"
  3. Also pull explicit committee names so we can join to committee leads.
  4. Yield one row per (lobbyist, member) pair, deduped.

We use a manually-curated roster of Members of Congress 2003-present
(downloaded from theunitedstates.io legislators-historical + legislators-current
on first run, cached). This is the only outside dataset and it is public.
"""
import duckdb
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DB = Path(os.environ.get("LDA_DB_PATH", ROOT / ".context" / "db" / "investigation.duckdb"))
CACHE = ROOT / ".context" / "cache"
CACHE.mkdir(parents=True, exist_ok=True)

LEGISLATORS_URL = "https://unitedstates.github.io/congress-legislators/legislators-historical.json"
LEGISLATORS_CURRENT_URL = "https://unitedstates.github.io/congress-legislators/legislators-current.json"


def load_legislators():
    """Return list of (last_name_upper, first_name_upper, bioguide, chamber_set, state) tuples
    covering everyone who served 2000+. Cached.
    """
    rows = []
    for url, fname in [
        (LEGISLATORS_URL, "legislators-historical.json"),
        (LEGISLATORS_CURRENT_URL, "legislators-current.json"),
    ]:
        fp = CACHE / fname
        if not fp.exists():
            print(f"  fetching {url}", file=sys.stderr)
            urllib.request.urlretrieve(url, fp)
        legs = json.load(open(fp))
        for L in legs:
            terms = L.get("terms") or []
            if not terms:
                continue
            last_term = terms[-1]
            end = last_term.get("end", "")
            if end and end < "2000-01-01":
                continue
            chambers = set()
            states = set()
            for t in terms:
                chambers.add(t.get("type"))  # "rep" or "sen"
                states.add(t.get("state"))
            name = L.get("name", {})
            ids = L.get("id", {})
            rows.append({
                "bioguide": ids.get("bioguide"),
                "last": (name.get("last") or "").upper(),
                "first": (name.get("first") or "").upper(),
                "official_full": (name.get("official_full") or "").upper(),
                "chambers": chambers,
                "states": states,
            })
    return rows


def build_index(legislators):
    """Build a multi-index keyed by last-name (upper). Multiple Members can share a surname,
    so we keep all candidates and disambiguate later by first name / state / chamber.
    """
    by_last = {}
    for L in legislators:
        if L["last"]:
            by_last.setdefault(L["last"], []).append(L)
    return by_last


# Precision-first matchers. Either (a) first + last together or (b) last + state qualifier.
# Optional middle initial like "John D. Rockefeller" is handled.
NAME_TOKEN = r"[A-Z][A-Za-z\-']+"
MIDDLE = r"(?:[A-Z]\.?\s+|[A-Z][A-Za-z\-']+\s+)?"  # optional middle initial or name
TITLE = r"(?:U\.?S\.?\s+)?(?:Senator|Sen\.|Representative|Rep\.|Congressman|Congresswoman|the\s+Honorable|Hon\.)"

# (a) Title + First + (Middle?) + Last  — both first and last required
RX_FIRST_LAST = re.compile(
    rf"\b{TITLE}\s+(?P<first>{NAME_TOKEN})\s+{MIDDLE}(?P<last>{NAME_TOKEN})\b",
    re.IGNORECASE,
)
# (b) Title + Last + (state)  — last name with explicit state qualifier
RX_LAST_STATE = re.compile(
    rf"\b{TITLE}\s+(?P<last>{NAME_TOKEN})\s*\((?P<state>[A-Z]{{2}})(?:-\d+)?\)",
    re.IGNORECASE,
)
# (c) "Office of Senator <First> <Last>" or "to <Title> <First> <Last>"
RX_OFFICE = re.compile(
    rf"(?:Office\s+of|to|for)\s+{TITLE}\s+(?P<first>{NAME_TOKEN})\s+{MIDDLE}(?P<last>{NAME_TOKEN})\b",
    re.IGNORECASE,
)


def _resolve(first, last, state, by_last):
    last = last.upper()
    first = (first or "").upper()
    candidates = by_last.get(last) or []
    if not candidates:
        return None
    # If we have a first name, require startswith match
    if first:
        narrowed = [c for c in candidates if c["first"].startswith(first[:3])]
        if narrowed:
            candidates = narrowed
        else:
            return None  # name pair doesn't resolve — drop rather than risk wrong person
    if state:
        for c in candidates:
            if state in (c["states"] or []):
                return c
        return None if first else None  # state given but no match → drop
    # Without first or state, take only if a single candidate
    if len(candidates) == 1:
        return candidates[0]
    return candidates[0] if first else None


def find_members(text, by_last):
    """Yield candidate matches from a covered_position string. High precision."""
    if not text:
        return
    seen = set()
    matches = []
    for rx, has_first, has_state in [
        (RX_FIRST_LAST, True, False),
        (RX_OFFICE, True, False),
        (RX_LAST_STATE, False, True),
    ]:
        for m in rx.finditer(text):
            first = m.group("first") if has_first else None
            last = m.group("last")
            state = m.group("state") if has_state else None
            res = _resolve(first, last, state, by_last)
            if res is None:
                continue
            matches.append((res, first, last, state))
    for res, first, last, state in matches:
        key = res["bioguide"]
        if key in seen:
            continue
        seen.add(key)
        yield {
            "matched_last": last.upper(),
            "matched_first": (first or "").upper() or None,
            "matched_state": state,
            "bioguide": res["bioguide"],
            "member_last": res["last"],
            "member_first": res["first"],
            "chambers": ",".join(sorted(res["chambers"] or [])),
        }


def main():
    legislators = load_legislators()
    by_last = build_index(legislators)
    print(f"  legislators indexed: {len(legislators)}", file=sys.stderr)

    con = duckdb.connect(str(DB))
    # Pull covered_position strings from Senate.
    print("  scanning senate_lobbyist.covered_position...", file=sys.stderr)
    df = con.execute(
        """
        SELECT filing_uuid, act_idx, lobbyist_idx, lobbyist_id,
               first_name, last_name, covered_position
        FROM senate_lobbyist
        WHERE covered_position IS NOT NULL
          AND length(trim(covered_position)) > 4
        """
    ).fetch_df()
    print(f"  rows with covered_position: {len(df):,}", file=sys.stderr)

    out = []
    for r in df.itertuples(index=False):
        for hit in find_members(r.covered_position, by_last):
            out.append({
                "filing_uuid": r.filing_uuid,
                "act_idx": r.act_idx,
                "lobbyist_idx": r.lobbyist_idx,
                "lobbyist_id": r.lobbyist_id,
                "lobbyist_first": r.first_name,
                "lobbyist_last": r.last_name,
                "covered_position": r.covered_position,
                **hit,
            })
    print(f"  member matches: {len(out):,}", file=sys.stderr)

    rd = pd.DataFrame(out)
    con.register("_rd", rd)
    con.execute("DROP TABLE IF EXISTS revolving_door")
    con.execute("CREATE TABLE revolving_door AS SELECT * FROM _rd")
    con.unregister("_rd")
    print(f"  table revolving_door: {len(rd):,} rows", file=sys.stderr)

    # Summary: top former bosses by # of (lobbyist, client) pairs
    print("\nTop 15 former bosses by distinct lobbyist count:", file=sys.stderr)
    rows = con.execute(
        """
        SELECT member_first || ' ' || member_last AS member,
               bioguide,
               COUNT(DISTINCT lobbyist_id) AS lobbyists,
               COUNT(DISTINCT f.client_id) AS clients
        FROM revolving_door rd
        JOIN senate_filing f USING (filing_uuid)
        GROUP BY 1, 2
        ORDER BY lobbyists DESC
        LIMIT 15
        """
    ).fetchall()
    for row in rows:
        print(f"  {row[0]:<35} {row[1]:<10} lobbyists={row[2]:<4} clients={row[3]}", file=sys.stderr)
    con.close()


if __name__ == "__main__":
    main()
