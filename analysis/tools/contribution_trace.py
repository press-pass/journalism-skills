"""Trace every LD-203 contribution to a recipient, with co-temporal lobbying.

Run:
    python analysis/tools/contribution_trace.py \\
        --honoree "Trump Vance Inaugural Committee, Inc." \\
        --md analysis/findings/inaugural_trace.md \\
        --csv analysis/findings/inaugural_trace.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from views import connect  # type: ignore


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--honoree", action="append", default=[])
    ap.add_argument("--honoree-like", action="append", default=[])
    ap.add_argument("--year", type=int)
    ap.add_argument("--md")
    ap.add_argument("--csv")
    args = ap.parse_args()

    if not args.honoree and not args.honoree_like:
        raise SystemExit("Provide --honoree and/or --honoree-like")

    con = connect()

    clauses = []
    params: list = []
    for h in args.honoree:
        clauses.append("LOWER(ci.honoree_name) = LOWER(?)")
        params.append(h)
    for h in args.honoree_like:
        clauses.append("ci.honoree_name ILIKE ?")
        params.append(h)
    where = " OR ".join(f"({c})" for c in clauses)
    if args.year:
        where = f"({where}) AND ci.filing_year = ?"
        params.append(args.year)

    # First: get distinct contribution items.
    # Second: for each (registrant_id, year, quarter), compute total lobbying
    # income and a representative filing URL — separately, so we don't
    # multiply contributions by # of Q-reports in the period.
    sql = f"""
    WITH contribs AS (
        SELECT DISTINCT
            ci.filing_uuid AS contrib_filing_uuid,
            ci.filing_year,
            ci.registrant_id,
            ci.registrant_name,
            ci.contributor_name,
            ci.payee_name,
            ci.honoree_name,
            ci.amount,
            ci.contribution_date,
            ci.contribution_type_display,
            CEIL(EXTRACT(MONTH FROM ci.contribution_date) / 3.0)::INT AS quarter,
            cr.url AS contrib_url
        FROM sen_contrib_items ci
        LEFT JOIN sen_contrib_reports cr
            ON ci.filing_uuid = cr.filing_uuid
        WHERE {where}
    ),
    lobbying AS (
        SELECT
            f.registrant_id,
            f.filing_year,
            CASE f.filing_period
                WHEN 'first_quarter' THEN 1
                WHEN 'second_quarter' THEN 2
                WHEN 'third_quarter' THEN 3
                WHEN 'fourth_quarter' THEN 4
                ELSE NULL
            END AS quarter_int,
            SUM(f.income) AS quarter_income,
            SUM(f.expenses) AS quarter_expenses,
            ANY_VALUE(f.url) AS lobbying_filing_url,
            ANY_VALUE(f.filing_uuid) AS lobbying_filing_uuid,
            STRING_AGG(DISTINCT f.client_name, ' | ' ORDER BY f.client_name) AS clients
        FROM sen_filings f
        WHERE f.filing_type LIKE 'Q%'
        GROUP BY 1, 2, 3
    )
    SELECT
        c.contributor_name,
        c.registrant_name,
        c.payee_name,
        c.honoree_name,
        c.amount,
        c.contribution_date,
        c.contribution_type_display,
        c.contrib_filing_uuid,
        c.contrib_url,
        l.clients AS lobbying_clients,
        l.quarter_income,
        l.quarter_expenses,
        l.lobbying_filing_uuid AS sample_lobbying_filing_uuid,
        l.lobbying_filing_url AS sample_lobbying_filing_url
    FROM contribs c
    LEFT JOIN lobbying l
        ON c.registrant_id = l.registrant_id
       AND c.filing_year = l.filing_year
       AND c.quarter = l.quarter_int
    ORDER BY c.amount DESC NULLS LAST, c.contribution_date DESC
    """
    df = con.execute(sql, params).df()
    print(f"Found {len(df):,} matching rows ({df['amount'].sum():,.0f} total $)", file=sys.stderr)

    if args.csv:
        df.to_csv(args.csv, index=False)
        print(f"wrote {args.csv}", file=sys.stderr)

    # Summary: top issues this quarter for each donor
    issue_sql = f"""
    WITH contribs AS (
        SELECT DISTINCT ci.registrant_id, ci.registrant_name, ci.filing_year,
               CEIL(EXTRACT(MONTH FROM ci.contribution_date) / 3.0)::INT AS quarter
        FROM sen_contrib_items ci
        WHERE {where}
    )
    SELECT
        c.registrant_name,
        c.filing_year,
        c.quarter,
        a.issue_code,
        a.issue_display,
        COUNT(*) AS n_activities
    FROM contribs c
    JOIN sen_filings f
        ON c.registrant_id = f.registrant_id
       AND c.filing_year = f.filing_year
       AND CASE f.filing_period
            WHEN 'first_quarter' THEN 1 WHEN 'second_quarter' THEN 2
            WHEN 'third_quarter' THEN 3 WHEN 'fourth_quarter' THEN 4
            ELSE NULL END = c.quarter
    JOIN sen_activities a USING (filing_uuid)
    WHERE f.filing_type LIKE 'Q%'
    GROUP BY 1, 2, 3, 4, 5
    """
    issues_df = con.execute(issue_sql, params).df()

    if args.md:
        out = Path(args.md)
        out.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            f"# Contribution trace",
            "",
            f"Filters: honoree={args.honoree!r} like={args.honoree_like!r} year={args.year}",
            "",
            f"**Total rows:** {len(df):,}",
            f"**Total dollars:** ${df['amount'].sum():,.0f}",
            f"**Unique registrants:** {df['registrant_name'].nunique():,}",
            "",
            "## Top donors (LDA registrant view)",
            "",
            "| Registrant (LDA filer) | Contributor / payer | Total $ | Items |",
            "|---|---|---:|---:|",
        ]
        top = (
            df.groupby(["registrant_name", "contributor_name"], dropna=False)
            .agg(total=("amount", "sum"), n=("amount", "size"))
            .reset_index()
            .sort_values("total", ascending=False)
            .head(50)
        )
        for _, r in top.iterrows():
            lines.append(f"| {r['registrant_name']} | {r['contributor_name']} | ${r['total']:,.0f} | {int(r['n'])} |")
        lines += ["", "## Itemized receipts (top 100 by amount)", ""]
        lines += [
            "| Amount | Date | Contributor | Registrant | Payee | Honoree | LDA contrib URL | LDA Q-filing URL |",
            "|---:|---|---|---|---|---|---|---|",
        ]
        for _, r in df.head(100).iterrows():
            lines.append(
                "| ${:,.0f} | {} | {} | {} | {} | {} | [{} ]({}) | [{} ]({}) |".format(
                    r.get("amount", 0) or 0,
                    r.get("contribution_date") or "",
                    r.get("contributor_name") or "",
                    r.get("registrant_name") or "",
                    r.get("payee_name") or "",
                    r.get("honoree_name") or "",
                    str(r.get("contrib_filing_uuid") or "")[:8],
                    r.get("contrib_url") or "",
                    str(r.get("sample_lobbying_filing_uuid") or "")[:8] if r.get("sample_lobbying_filing_uuid") else "—",
                    r.get("sample_lobbying_filing_url") or "",
                )
            )
        if not issues_df.empty:
            lines += ["", "## Co-temporal lobbying issues (same registrant + same quarter)", ""]
            for reg, sub in issues_df.groupby("registrant_name"):
                lines.append(f"### {reg}")
                top_issues = sub.sort_values("n_activities", ascending=False).head(8)
                for _, r in top_issues.iterrows():
                    lines.append(
                        f"- {int(r['filing_year'])} Q{int(r['quarter'])} — `{r['issue_code']}` "
                        f"{r['issue_display']} ({int(r['n_activities'])} activities)"
                    )
                lines.append("")

        out.write_text("\n".join(lines))
        print(f"wrote {out}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
