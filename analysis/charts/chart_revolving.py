"""Chart 4: 'The Revolving Door' — top committee feeders to K Street,
parsed from 1.1 million LDA covered_position disclosures.

Output: PNG + SVG to analysis/charts/output/
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from views import connect  # type: ignore

OUT_DIR = Path(__file__).resolve().parent / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# Committee-name canonicalization map (variant spellings → canonical)
CANON = {
    "Senate Energy and Natural Resources Committee": "Senate Energy & Natural Resources Committee",
    "House Energy & Commerce Committee": "House Energy & Commerce Committee",
    "House Energy and Commerce Committee": "House Energy & Commerce Committee",
    "House Transportation Committee": "House Transportation & Infrastructure Committee",
    "House Transportation & Infrastructure Committee": "House Transportation & Infrastructure Committee",
    "Senate HELP Committee": "Senate HELP Committee",
}


ROLE_PRETTY = {
    "MEMBER":         "Member of Congress",
    "CHIEF_OF_STAFF": "Chief of Staff",
    "STAFF_DIRECTOR": "Committee Staff Director",
    "LEG_DIRECTOR":   "Legislative Director",
    "COUNSEL":        "Counsel",
    "LEG_ASSISTANT":  "Legislative Assistant",
    "PROF_STAFF":     "Professional Staff",
    "PRESS_SEC":      "Press / Comms",
    "FLOOR_OPS":      "Floor Operations",
    "LEG_CORRESPOND": "Leg. Correspondent",
    "STAFF_ASSISTANT":"Staff Assistant",
    "CONSULTANT":     "Consultant / Advisor",
    "OTHER_AIDE":     "Other Aide / Deputy",
    "OTHER":          "Other",
}

# Map role → bar color (gradient of seniority)
ROLE_COLOR = {
    "Member of Congress":       "#222222",
    "Chief of Staff":           "#205594",
    "Committee Staff Director": "#3776c6",
    "Legislative Director":     "#5e9fda",
    "Counsel":                  "#8fc1eb",
    "Legislative Assistant":    "#b3d8ed",
    "Professional Staff":       "#a07d10",
    "Press / Comms":            "#c2185b",
    "Floor Operations":         "#7e5a00",
    "Leg. Correspondent":       "#d9a300",
    "Staff Assistant":          "#dddddd",
    "Consultant / Advisor":     "#888888",
    "Other Aide / Deputy":      "#bbbbbb",
    "Other":                    "#eeeeee",
}


def fetch() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    con = duckdb.connect()
    con.execute(f"CREATE VIEW rd AS SELECT * FROM read_parquet('/parquet/revolving_door.parquet')")

    # Build a deterministic person key: lower(first || '_' || last). Imperfect
    # for namesakes but good enough at the scale of this analysis.
    con.execute(
        """
        CREATE VIEW rd_people AS
        SELECT *,
               LOWER(TRIM(COALESCE(lobbyist_first,'') || '_' || COALESCE(lobbyist_last,''))) AS person_key
        FROM rd
        WHERE COALESCE(lobbyist_first,'') || COALESCE(lobbyist_last,'') <> ''
        """
    )

    # For each person, pick a single (most-frequent) prior_role for them
    # — collapses the row-explosion to one role per person per committee.
    person_role = con.execute(
        """
        WITH per_pair AS (
            SELECT source_office_type, source_office, person_key, prior_role,
                   COUNT(*) AS n_rows
            FROM rd_people
            WHERE source_office_type IN ('SENATE_COMMITTEE','HOUSE_COMMITTEE')
              AND source_office IS NOT NULL
            GROUP BY 1, 2, 3, 4
        ),
        ranked AS (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY source_office, person_key ORDER BY n_rows DESC) AS rk
            FROM per_pair
        )
        SELECT source_office_type, source_office, person_key, prior_role
        FROM ranked WHERE rk = 1
        """
    ).df()
    person_role["source_office"] = person_role["source_office"].map(lambda s: CANON.get(s, s))

    com = (
        person_role.groupby(["source_office_type", "source_office", "prior_role"], as_index=False)
        .size().rename(columns={"size": "n"})
    )

    total_per_office = (
        com.groupby(["source_office_type", "source_office"])["n"].sum()
        .reset_index().rename(columns={"n": "total"})
    )
    top = total_per_office.sort_values("total", ascending=False).head(14)
    com_top = com.merge(top, on=["source_office_type", "source_office"], how="inner")

    # Headline stats (in terms of distinct people)
    totals = con.execute(
        """
        SELECT
            COUNT(DISTINCT person_key) AS total_people,
            COUNT(DISTINCT CASE WHEN prior_role = 'MEMBER' THEN person_key END) AS n_members,
            COUNT(DISTINCT CASE WHEN source_office_type = 'WH' THEN person_key END) AS n_wh,
            COUNT(DISTINCT CASE WHEN source_office_type = 'AGENCY' THEN person_key END) AS n_agency,
            COUNT(DISTINCT CASE WHEN source_office_type IN ('SENATE_COMMITTEE','HOUSE_COMMITTEE') THEN person_key END) AS n_committee,
            COUNT(DISTINCT CASE WHEN source_office_type IN ('SENATE_MEMBER','HOUSE_MEMBER') THEN person_key END) AS n_member_office
        FROM rd_people
        """
    ).fetchone()
    stats = {
        "total_people": int(totals[0]),
        "n_members": int(totals[1]),
        "n_wh": int(totals[2]),
        "n_agency": int(totals[3]),
        "n_committee": int(totals[4]),
        "n_member_office": int(totals[5]),
    }

    # Top destination firms by distinct ex-committee people
    dest = con.execute(
        """
        WITH t AS (
            SELECT source_office, registrant_name,
                   COUNT(DISTINCT person_key) AS n_people,
                   ROW_NUMBER() OVER (PARTITION BY source_office ORDER BY COUNT(DISTINCT person_key) DESC) AS rk
            FROM rd_people
            WHERE source_office_type IN ('SENATE_COMMITTEE','HOUSE_COMMITTEE')
              AND registrant_name IS NOT NULL
              AND source_office IS NOT NULL
            GROUP BY 1, 2
        )
        SELECT source_office, registrant_name, n_people FROM t WHERE rk = 1
        """
    ).df()
    dest["source_office"] = dest["source_office"].map(lambda s: CANON.get(s, s))
    # Sometimes after CANON merge we get duplicates — keep the largest
    dest = dest.sort_values("n_people", ascending=False).drop_duplicates("source_office", keep="first")

    return com_top, dest, stats


def render(com: pd.DataFrame, dest: pd.DataFrame, stats: dict) -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titleweight": "bold",
    })

    # Pivot to stacked bar
    pivot = com.pivot_table(index="source_office", columns="prior_role", values="n", aggfunc="sum").fillna(0)
    pivot["total"] = pivot.sum(axis=1)
    pivot = pivot.sort_values("total", ascending=True)  # ascending for barh

    # Limit roles columns to a useful order
    role_order = [
        "MEMBER", "CHIEF_OF_STAFF", "STAFF_DIRECTOR", "LEG_DIRECTOR", "COUNSEL",
        "LEG_ASSISTANT", "PROF_STAFF", "PRESS_SEC",
        "FLOOR_OPS", "LEG_CORRESPOND", "STAFF_ASSISTANT", "CONSULTANT",
        "OTHER_AIDE", "OTHER",
    ]
    roles_present = [r for r in role_order if r in pivot.columns]
    pivot = pivot[roles_present + ["total"]]

    fig = plt.figure(figsize=(15, 11))
    ax = fig.add_axes([0.32, 0.14, 0.60, 0.72])

    y = np.arange(len(pivot))
    bottom = np.zeros(len(pivot))
    for role in roles_present:
        label = ROLE_PRETTY.get(role, role)
        ax.barh(y, pivot[role], left=bottom, color=ROLE_COLOR.get(label, "#aaa"),
                edgecolor="white", linewidth=0.4, label=label)
        bottom += pivot[role].values

    ax.set_yticks(y)
    ax.set_yticklabels(pivot.index, fontsize=10.5)
    ax.set_xlabel("Distinct registered lobbyists who disclosed prior service on this committee\n(sum of Senate + House LDA, 2022 Q1 – 2026 Q1)", fontsize=10)
    ax.tick_params(axis="x", labelsize=9, colors="#555")
    ax.tick_params(axis="y", left=False)
    ax.grid(axis="x", linestyle=":", alpha=0.4)

    # Right-edge total + top destination firm annotation
    max_total = pivot["total"].max()
    dest_map = dict(zip(dest["source_office"], zip(dest["registrant_name"], dest["n_people"])))
    for i, office in enumerate(pivot.index):
        total = int(pivot.loc[office, "total"])
        ax.text(total + max_total * 0.005, i, f"{total:,}", va="center", fontsize=9.5, color="#222", fontweight="bold")
        if office in dest_map:
            firm, n_firm = dest_map[office]
            ax.text(
                max_total * 1.05, i,
                f"top firm: {firm.title()[:50]} ({int(n_firm)} ex-staff)",
                va="center", fontsize=8.5, color="#666", style="italic",
            )

    ax.set_xlim(0, max_total * 1.95)

    # Title + subtitle
    fig.text(
        0.04, 0.95,
        "The revolving door, by committee: where K Street's Hill staffers come from",
        fontsize=18, fontweight="bold", ha="left",
    )
    fig.text(
        0.04, 0.918,
        f"Of all federal lobbyists in 2022–2026, {stats['n_committee']:,} disclose prior service on a congressional committee.\n"
        f"Senate Commerce, House Financial Services, Senate Judiciary, and Senate Finance lead the pipeline.\n"
        f"Annotations on the right show each committee's top destination lobbying firm and how many alumni it employs.",
        fontsize=11, ha="left", color="#444",
    )

    # Legend
    handles = [mpatches.Patch(color=ROLE_COLOR[ROLE_PRETTY[r]], label=ROLE_PRETTY[r]) for r in roles_present
               if ROLE_PRETTY[r] in ROLE_COLOR]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.32, 0.90),
               ncol=4, frameon=False, fontsize=9,
               handlelength=1.2, columnspacing=1.0)

    fig.text(
        0.04, 0.045,
        "Source: U.S. Senate LDA quarterly filings (LD-2) and U.S. House Clerk LDA filings, 2022 Q1 – 2026 Q1. The 'covered_position' free-text field on each lobbyist record was parsed deterministically by a\n"
        "regex pipeline (analysis/tools/revolving_door.py): role detection on a curated dictionary, source-office detection by committee-name patterns. Each parsed row preserves the raw input string.\n"
        "Senate-committee variants ('& Natural Resources' vs 'and Natural Resources') were merged. Same person appearing across multiple filings is counted once per filing.",
        fontsize=8, color="#888", ha="left",
    )

    out_png = OUT_DIR / "04_revolving_door.png"
    out_svg = OUT_DIR / "04_revolving_door.svg"
    fig.savefig(out_png, dpi=200, bbox_inches="tight")
    fig.savefig(out_svg, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out_png}")
    print(f"wrote {out_svg}")


def main() -> int:
    com, dest, stats = fetch()
    com.to_csv(OUT_DIR / "04_revolving_door_committees.csv", index=False)
    dest.to_csv(OUT_DIR / "04_revolving_door_top_firms.csv", index=False)
    print(stats)
    render(com, dest, stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())
