"""Mode A of lda-press-bridge: member → lobbying snapshot.

Given a bioguide_id (or member_name + state + chamber), emit a JSON / Markdown
report mapping that member's press output against the Senate LDA universe in
the same quarter, and any LD-203 contributions naming them.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from views import connect  # type: ignore


def resolve_member(con, bioguide: str | None, name: str | None, state: str | None, chamber: str | None) -> dict:
    if bioguide:
        row = con.execute(
            """
            SELECT bioguide_id, MIN(member_name) AS member_name, MIN(state) AS state,
                   MIN(chamber) AS chamber, MIN(party) AS party,
                   COUNT(*) AS n_releases, MIN(date) AS first_release, MAX(date) AS last_release
            FROM press WHERE bioguide_id = ?
            GROUP BY 1
            """,
            [bioguide],
        ).fetchone()
        if row is None:
            raise SystemExit(f"bioguide_id {bioguide!r} not found in press corpus")
        keys = ["bioguide_id", "member_name", "state", "chamber", "party", "n_releases", "first_release", "last_release"]
        return dict(zip(keys, row))

    where = ["member_name = ?"]
    params: list = [name]
    if state:
        where.append("state = ?")
        params.append(state)
    if chamber:
        where.append("chamber = ?")
        params.append(chamber)
    rows = con.execute(
        f"""
        SELECT bioguide_id, MIN(member_name), MIN(state), MIN(chamber), MIN(party), COUNT(*)
        FROM press WHERE {' AND '.join(where)} GROUP BY 1 ORDER BY 6 DESC
        """,
        params,
    ).fetchall()
    if not rows:
        raise SystemExit(f"No member matched: name={name!r} state={state!r} chamber={chamber!r}")
    if len(rows) > 1:
        print("Multiple candidates — pass --bioguide for one of:", file=sys.stderr)
        for r in rows:
            print(f"  {r[0]} {r[1]} ({r[2]}-{r[4]}, {r[5]} releases)", file=sys.stderr)
        raise SystemExit(2)
    r = rows[0]
    keys = ["bioguide_id", "member_name", "state", "chamber", "party", "n_releases"]
    return dict(zip(keys, r))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bioguide")
    ap.add_argument("--name")
    ap.add_argument("--state")
    ap.add_argument("--chamber", choices=["House", "Senate"])
    ap.add_argument("--quarters", type=int, default=4, help="N most recent quarters to show")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.bioguide and not args.name:
        raise SystemExit("Provide --bioguide or --name (+ optional --state --chamber)")

    con = connect()
    m = resolve_member(con, args.bioguide, args.name, args.state, args.chamber)

    # Press output by quarter
    press_qtr = con.execute(
        """
        SELECT
            EXTRACT(YEAR FROM date)::INT AS year,
            CEIL(EXTRACT(MONTH FROM date) / 3.0)::INT AS quarter,
            COUNT(*) AS n_press
        FROM press
        WHERE bioguide_id = ?
        GROUP BY 1, 2 ORDER BY 1 DESC, 2 DESC
        LIMIT ?
        """,
        [m["bioguide_id"], args.quarters],
    ).fetchall()

    # Top issues lobbied at member's chamber across the same period
    chamber_name = "SENATE" if m["chamber"] == "Senate" else "HOUSE OF REPRESENTATIVES"
    snapshot = []
    for (y, q, n_press) in press_qtr:
        top_issues = con.execute(
            """
            SELECT ge.issue_code, a.issue_display, COUNT(DISTINCT ge.filing_uuid) AS n_filings
            FROM sen_gov_entities ge
            JOIN sen_activities a USING (filing_uuid, issue_code)
            WHERE ge.gov_entity_name = ?
              AND a.filing_year = ?
            GROUP BY 1, 2 ORDER BY n_filings DESC LIMIT 10
            """,
            [chamber_name, y],
        ).fetchall()
        top_registrants = con.execute(
            """
            SELECT registrant_name, COUNT(DISTINCT filing_uuid) AS n_filings
            FROM sen_gov_entities
            WHERE gov_entity_name = ? AND filing_year = ?
            GROUP BY 1 ORDER BY n_filings DESC LIMIT 10
            """,
            [chamber_name, y],
        ).fetchall()
        # LD-203 contributions where honoree_name contains the member's last name
        last_name = m["member_name"].split()[-1] if m["member_name"] else ""
        contribs = con.execute(
            """
            SELECT registrant_name, contributor_name, payee_name, honoree_name,
                   amount, contribution_date, filing_uuid
            FROM sen_contrib_items
            WHERE filing_year = ?
              AND (honoree_name ILIKE ?
                OR payee_name ILIKE ?)
            ORDER BY amount DESC LIMIT 20
            """,
            [y, f"%{last_name}%", f"%{last_name}%"],
        ).fetchall()
        snapshot.append(
            {
                "year": y,
                "quarter": q,
                "press_count": n_press,
                "chamber_targeted": chamber_name,
                "top_issues": [
                    {"issue_code": r[0], "issue_display": r[1], "filings": r[2]} for r in top_issues
                ],
                "top_registrants": [{"name": r[0], "filings": r[1]} for r in top_registrants],
                "contrib_matches": [
                    {
                        "registrant": r[0],
                        "contributor": r[1],
                        "payee": r[2],
                        "honoree": r[3],
                        "amount": r[4],
                        "date": str(r[5]) if r[5] else None,
                        "filing_uuid": r[6],
                    }
                    for r in contribs
                ],
            }
        )

    result = {"member": {k: (str(v) if hasattr(v, "isoformat") else v) for k, v in m.items()}, "snapshots": snapshot}
    if args.json:
        print(json.dumps(result, default=str, indent=2))
        return 0

    # Markdown summary
    print(f"# {m['member_name']} ({m['state']}-{m['party'][0] if m['party'] else '?'}, {m['chamber']})")
    print(f"bioguide: `{m['bioguide_id']}` — {m['n_releases']} releases")
    for s in snapshot:
        print(f"\n## {s['year']} Q{s['quarter']} — {s['press_count']} press releases, chamber targeted: {s['chamber_targeted']}")
        if s["top_issues"]:
            print("\n**Top issues lobbied at chamber (year-wide):**")
            for r in s["top_issues"]:
                print(f"- {r['issue_code']} {r['issue_display']}: {r['filings']} filings")
        if s["top_registrants"]:
            print("\n**Top registrants lobbying chamber:**")
            for r in s["top_registrants"]:
                print(f"- {r['name']}: {r['filings']} filings")
        if s["contrib_matches"]:
            print(f"\n**LD-203 contributions matching '{m['member_name'].split()[-1]}':**")
            for r in s["contrib_matches"]:
                print(
                    f"- ${r['amount']:.0f} from {r['registrant']} → {r['honoree']} "
                    f"(payee {r['payee']}) on {r['date']} `filing_uuid={r['filing_uuid']}`"
                )
    return 0


if __name__ == "__main__":
    sys.exit(main())
