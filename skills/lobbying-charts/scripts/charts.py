"""Generate the finalist chart family.

Each chart writes a PNG + a small JSON sidecar that traces every datapoint to
a primary key (filing_uuid, bioguide_id, press release URL, etc.).

Run inside docker:
  python /scripts/charts.py --out_dir /charts
"""
from __future__ import annotations
import argparse, json, os
from pathlib import Path
import polars as pl
import plotly.graph_objects as go
import plotly.io as pio


# --- shared style ---
PRESSPASS_PRIMARY = "#0F172A"   # near-black
DEM_COLOR = "#1F77B4"
REP_COLOR = "#D62728"
IND_COLOR = "#7F7F7F"
ACCENT = "#FF7F0E"
NEUTRAL = "#9CA3AF"
PALETTE = ["#0F172A", "#1F77B4", "#D62728", "#2CA02C", "#FF7F0E", "#9467BD", "#8C564B"]


def base_layout(title: str, subtitle: str = "", height: int = 600, width: int = 1080) -> dict:
    return dict(
        title=dict(
            text=f"<b>{title}</b><br><span style='font-size:14px;color:#374151'>{subtitle}</span>",
            x=0.02, xanchor="left", y=0.95,
            font=dict(family="Helvetica, Arial", size=22, color=PRESSPASS_PRIMARY),
        ),
        font=dict(family="Helvetica, Arial", color=PRESSPASS_PRIMARY, size=13),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=70, r=40, t=110, b=110),
        height=height, width=width,
        xaxis=dict(showgrid=False, zeroline=False, color=PRESSPASS_PRIMARY, ticks="outside", tickcolor="#94A3B8"),
        yaxis=dict(gridcolor="#E5E7EB", zeroline=False, color=PRESSPASS_PRIMARY, ticks="outside", tickcolor="#94A3B8"),
        showlegend=False,
    )


def add_footer(fig: go.Figure, source_lines: list[str]):
    text = "<br>".join(source_lines)
    fig.add_annotation(
        text=text,
        xref="paper", yref="paper", x=0, y=-0.18,
        showarrow=False, font=dict(size=11, color="#475569"), align="left",
        xanchor="left", yanchor="top",
    )


def write_png(fig: go.Figure, out_path: Path, scale: int = 2):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_image(str(out_path), scale=scale)


def write_sidecar(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str))


# ---------- Chart 1: AI lobbying boom ----------
def chart_ai_boom(out: Path):
    a = pl.read_parquet("/parquet/senate_activities.parquet")
    period_order = {"first_quarter": 1, "second_quarter": 2, "third_quarter": 3, "fourth_quarter": 4}
    a = a.with_columns(pl.col("filing_period").replace_strict(period_order).alias("q"))
    ai = a.filter(pl.col("description").str.to_lowercase().str.contains("artificial intelligence"))
    q = ai.group_by(["filing_year", "q"]).agg(
        pl.len().alias("ai_n"),
        pl.col("client_name").n_unique().alias("clients"),
    ).sort(["filing_year", "q"])
    tot = a.group_by(["filing_year", "q"]).len().rename({"len": "total"})
    q = q.join(tot, on=["filing_year", "q"]).sort(["filing_year", "q"])
    q = q.with_columns(
        (pl.col("ai_n") / pl.col("total") * 100).alias("share_pct"),
        (pl.col("filing_year").cast(pl.Utf8) + " Q" + pl.col("q").cast(pl.Utf8)).alias("label"),
    )
    fig = go.Figure()
    fig.add_bar(
        x=q["label"], y=q["ai_n"],
        marker_color=PRESSPASS_PRIMARY, marker_line_width=0,
        hovertemplate="%{x}<br>%{y} AI activity records<extra></extra>",
        name="AI lobbying activities (Senate filings)",
    )
    # annotation: ChatGPT launch
    chatgpt_label = "2022 Q4"
    chatgpt_x_idx = q.with_row_index().filter(pl.col("label")==chatgpt_label)["index"][0]
    # share line
    fig.add_scatter(
        x=q["label"], y=q["share_pct"], yaxis="y2",
        mode="lines+markers", line=dict(color=ACCENT, width=3),
        marker=dict(size=8, color=ACCENT),
        hovertemplate="%{x}<br>%{y:.2f}%% of all activity<extra></extra>",
        name="% of all Senate lobbying activity",
    )
    # callouts
    annotations = [
        dict(x="2022 Q4", y=q.filter(pl.col("label")=="2022 Q4")["ai_n"][0],
             text="<b>Pre-ChatGPT baseline</b><br>~220 per quarter",
             showarrow=True, arrowhead=2, ax=-60, ay=-40, font=dict(size=11, color=PRESSPASS_PRIMARY)),
        dict(x="2023 Q4", y=q.filter(pl.col("label")=="2023 Q4")["ai_n"][0],
             text="<b>Post-ChatGPT surge</b><br>4× in one year",
             showarrow=True, arrowhead=2, ax=20, ay=-40, font=dict(size=11, color=PRESSPASS_PRIMARY)),
        dict(x="2026 Q1", y=q.filter(pl.col("label")=="2026 Q1")["ai_n"][0],
             text="<b>2026 Q1</b><br>1,176 activities<br>649 unique clients",
             showarrow=True, arrowhead=2, ax=-60, ay=-60, font=dict(size=11, color=PRESSPASS_PRIMARY)),
    ]
    lay = base_layout(
        "AI lobbying has multiplied 5× since ChatGPT",
        "Senate LDA activities whose description mentions 'artificial intelligence' (2022 Q1 – 2026 Q1)",
        height=620,
    )
    lay.update(
        annotations=annotations,
        yaxis=dict(title="Senate activity records mentioning AI", gridcolor="#E5E7EB", zeroline=False, color=PRESSPASS_PRIMARY),
        yaxis2=dict(title="Share of all Senate activity (%)", overlaying="y", side="right", color=ACCENT, gridcolor="rgba(0,0,0,0)"),
        xaxis=dict(tickangle=-35, showgrid=False, color=PRESSPASS_PRIMARY),
        showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0.02, font=dict(size=12)),
    )
    fig.update_layout(**lay)
    add_footer(fig, [
        "Source: Senate Lobbying Disclosure Act filings (lda.senate.gov), 2022 Q1 – 2026 Q1.",
        "Method: substring match for 'artificial intelligence' in lobbying_activities[].description. Each Senate filing can contain multiple activities; we count activities, not filings.",
        "Code: github.com/press-pass/journalism-skills (skill: lobbying-corpus-build)",
    ])
    write_png(fig, out / "01_ai_lobbying_boom.png")
    write_sidecar(out / "01_ai_lobbying_boom.json", {
        "title": "AI lobbying has multiplied 5x since ChatGPT",
        "data": q.to_dicts(),
        "method": "Senate LDA activities containing 'artificial intelligence' (case-insensitive) in description.",
        "source": "data/senate/{YEAR}/filings/filings_{YEAR}.json",
        "ft_category": "change-over-time",
        "axis_transform": "linear",
        "n_total_rows_scanned": int(a.height),
    })


# ---------- Chart 2: Issue heatmap, share of total ----------
def chart_issue_heatmap(out: Path):
    a = pl.read_parquet("/parquet/senate_activities.parquet")
    period_order = {"first_quarter": 1, "second_quarter": 2, "third_quarter": 3, "fourth_quarter": 4}
    a = a.with_columns(pl.col("filing_period").replace_strict(period_order).alias("q"))
    a = a.with_columns((pl.col("filing_year").cast(pl.Utf8) + "·Q" + pl.col("q").cast(pl.Utf8)).alias("ym"))
    by = a.group_by(["issue_code", "issue_code_display", "ym"]).len()
    tot = a.group_by("ym").len().rename({"len": "total"})
    by = by.join(tot, on="ym").with_columns((pl.col("len") / pl.col("total") * 100).alias("pct"))
    # top 12 by overall total
    top12 = (
        a.group_by(["issue_code", "issue_code_display"]).len()
         .sort("len", descending=True).head(12)["issue_code"].to_list()
    )
    by = by.filter(pl.col("issue_code").is_in(top12))
    # order x chronologically, y by overall rank
    ym_order = sorted(by["ym"].unique().to_list(), key=lambda s: (int(s[:4]), int(s[-1])))
    issue_order_df = (
        by.group_by("issue_code").agg(pl.col("len").sum().alias("s")).sort("s", descending=True)
    )
    issue_order = issue_order_df["issue_code"].to_list()
    # build matrix
    m = []
    labels = []
    for ic in issue_order:
        row = []
        for ym in ym_order:
            v = by.filter((pl.col("issue_code")==ic) & (pl.col("ym")==ym))["pct"]
            row.append(float(v[0]) if v.len() else 0.0)
        m.append(row)
        nm = by.filter(pl.col("issue_code")==ic)["issue_code_display"][0]
        labels.append(f"{ic} — {nm}")
    fig = go.Figure(go.Heatmap(
        z=m, x=ym_order, y=labels,
        colorscale=[
            [0, "#F8FAFC"], [0.2, "#CBD5E1"], [0.5, "#475569"], [1, "#0F172A"],
        ],
        colorbar=dict(title="% of activity"),
        hovertemplate="%{y}<br>%{x}: %{z:.2f}%%<extra></extra>",
    ))
    lay = base_layout(
        "Budget, Tax, and Health are persistently dominant lobbying issues",
        "Top 12 issue codes as a percentage of all Senate lobbying activity, by quarter",
        height=620, width=1180,
    )
    lay.update(
        xaxis=dict(tickangle=-35, showgrid=False, color=PRESSPASS_PRIMARY),
        yaxis=dict(autorange="reversed", color=PRESSPASS_PRIMARY, gridcolor="rgba(0,0,0,0)"),
    )
    fig.update_layout(**lay)
    add_footer(fig, [
        "Source: Senate LDA activities (lda.senate.gov), 2022 Q1 – 2026 Q1. Issue codes via constants/lobbying_activity_issues.json.",
        "Each cell = (activities tagged with that ALI code in the quarter) / (all Senate activities that quarter). Activities can be tagged with up to 9 codes; we count each tagging.",
    ])
    write_png(fig, out / "02_issue_heatmap.png")
    write_sidecar(out / "02_issue_heatmap.json", {
        "title": "Top 12 issue codes by quarter, % of activity",
        "ym_order": ym_order,
        "rows": [
            {"issue_code": ic, "label": labels[i], "pcts": m[i]} for i, ic in enumerate(issue_order)
        ],
        "method": "Top 12 issue codes selected by total activity count across all years; row-normalized to share-of-total.",
        "source": "data/senate/{YEAR}/filings/filings_{YEAR}.json + constants/lobbying_activity_issues.json",
        "ft_category": "magnitude",
        "axis_transform": "linear",
        "data": [
            {"issue_code": ic, "label": labels[i], "pcts_by_ym": dict(zip(ym_order, m[i]))} for i, ic in enumerate(issue_order)
        ],
    })


# ---------- Chart 3: Revolving door — most-poached members ----------
import re
MEMBER_PATTERNS = [
    re.compile(r"\bSen(?:ator)?\.?\s+([A-Z][A-Za-z\-\.']+(?:\s+[A-Z][A-Za-z\-\.']+){0,2})", re.IGNORECASE),
    re.compile(r"\bRep(?:resentative)?\.?\s+([A-Z][A-Za-z\-\.']+(?:\s+[A-Z][A-Za-z\-\.']+){0,2})", re.IGNORECASE),
    re.compile(r"\bCong(?:ressman|resswoman|ressmember)\.?\s+([A-Z][A-Za-z\-\.']+(?:\s+[A-Z][A-Za-z\-\.']+){0,2})", re.IGNORECASE),
]
COMMITTEE_PATTERNS = [
    re.compile(r"\bSenate\s+(?:Committee\s+on\s+)?([A-Z][\w\s,&\-]+?)\s+Committee", re.IGNORECASE),
    re.compile(r"\bHouse\s+(?:Committee\s+on\s+)?([A-Z][\w\s,&\-]+?)\s+Committee", re.IGNORECASE),
]


def _member_surname_lookup() -> dict:
    """Build a surname → (preferred display, chamber) lookup from the press corpus.

    Returns only surnames that uniquely identify a single member across all years
    of press releases. Ambiguous surnames (Smith, Johnson, etc.) are excluded.
    """
    p = pl.read_parquet("/parquet/press.parquet")
    members = (
        p.filter(pl.col("member_name").is_not_null())
         .select(["bioguide_id", "member_name", "party", "state", "chamber"])
         .unique()
    )
    # surname = last whitespace-separated token of member_name (stripped of suffixes)
    def surname(name: str) -> str:
        toks = [t for t in re.split(r"[\s.]+", name) if t]
        # drop suffixes
        while toks and toks[-1].lower() in {"jr", "sr", "ii", "iii", "iv"}:
            toks.pop()
        return (toks[-1] if toks else "").lower()
    rows = []
    for r in members.iter_rows(named=True):
        s = surname(r["member_name"] or "")
        if not s:
            continue
        rows.append((s, r["bioguide_id"], r["member_name"], r["party"], r["state"], r["chamber"]))
    df = pl.DataFrame(rows, schema=["surname", "bioguide_id", "member_name", "party", "state", "chamber"], orient="row")
    counts = df.group_by("surname").agg(pl.col("bioguide_id").n_unique().alias("n_members"))
    unique_surnames = counts.filter(pl.col("n_members") == 1)["surname"].to_list()
    lookup = {}
    for r in df.filter(pl.col("surname").is_in(unique_surnames)).iter_rows(named=True):
        lookup[r["surname"]] = (r["member_name"], r["party"], r["state"], r["chamber"])
    return lookup


def chart_revolving_door(out: Path):
    """Count how many distinct lobbyists list each member of Congress in their
    'covered_position' free-text disclosure.

    We restrict to surnames that uniquely identify a single member in the press
    corpus (2022–2026 Q1) to avoid double-counting common names like 'Smith'.
    """
    lookup = _member_surname_lookup()
    surnames = set(lookup)

    lo = pl.read_parquet("/parquet/senate_lobbyists.parquet")
    lo = lo.filter(pl.col("covered_position").str.strip_chars() != "")
    lo = lo.filter(~pl.col("covered_position").str.to_lowercase().is_in(["see prior filing", "n/a", "none", "n.a."]))
    uniq = lo.filter(pl.col("lobbyist_id").is_not_null())

    # Only capture surnames that appear AFTER an explicit title prefix.
    # The captured group is 1-3 capitalised words; we take the LAST as surname.
    title_re = re.compile(
        r"\b(?:Sen(?:ator)?|Rep(?:resentative)?|Cong(?:ressman|resswoman|ressmember)?)\.?\s+"
        r"([A-Z][A-Za-z'\-\.]+(?:\s+[A-Z][A-Za-z'\-\.]+){0,2})",
        re.IGNORECASE,
    )

    # Suffix/title tokens to skip when picking surname
    SUFFIX = {"jr", "sr", "ii", "iii", "iv"}

    edges = []  # (lobbyist_id, surname)
    for row in uniq.iter_rows(named=True):
        cp = row["covered_position"] or ""
        if not cp:
            continue
        for m in title_re.finditer(cp):
            grp = m.group(1).strip().rstrip(".,;:")
            toks = [t for t in re.split(r"[\s.]+", grp) if t]
            # strip trailing suffixes
            while toks and toks[-1].lower() in SUFFIX:
                toks.pop()
            if not toks:
                continue
            surname = toks[-1].lower()
            if surname in surnames:
                edges.append((row["lobbyist_id"], surname))
    if not edges:
        return
    edf = pl.DataFrame(edges, schema=["lobbyist_id", "surname"], orient="row").unique()
    counts = edf.group_by("surname").agg(pl.len().alias("n_lobbyists")).sort("n_lobbyists", descending=True)
    # enrich
    enriched = []
    for r in counts.iter_rows(named=True):
        nm, party, state, chamber = lookup[r["surname"]]
        enriched.append({
            "surname": r["surname"],
            "member_name": nm,
            "party": party,
            "state": state,
            "chamber": chamber,
            "n_lobbyists": r["n_lobbyists"],
        })
    edf = pl.DataFrame(enriched).head(20)
    # color by party
    colors = [DEM_COLOR if p == "Democrat" else REP_COLOR if p == "Republican" else IND_COLOR for p in edf["party"]]
    # display label
    labels = [
        f"{r['member_name']} ({r['party'][0]}-{r['state']}, {r['chamber'][0]})"
        for r in edf.iter_rows(named=True)
    ]
    fig = go.Figure()
    fig.add_bar(
        x=edf["n_lobbyists"], y=labels, orientation="h",
        marker_color=colors, marker_line_width=0,
        text=edf["n_lobbyists"], textposition="outside",
        textfont=dict(color=PRESSPASS_PRIMARY, size=11),
        hovertemplate="%{y}<br>%{x} distinct lobbyists list this member in their 'covered position'<extra></extra>",
        showlegend=False,
    )
    # legend dummies
    fig.add_bar(x=[None], y=[None], marker_color=DEM_COLOR, name="Democrat", showlegend=True)
    fig.add_bar(x=[None], y=[None], marker_color=REP_COLOR, name="Republican", showlegend=True)
    fig.add_bar(x=[None], y=[None], marker_color=IND_COLOR, name="Independent", showlegend=True)
    lay = base_layout(
        "Where K Street's Capitol Hill alumni worked",
        "Members of Congress whose offices supplied the most lobbyists currently registered with the Senate LDA",
        height=720, width=1180,
    )
    lay.update(
        yaxis=dict(autorange="reversed", color=PRESSPASS_PRIMARY),
        xaxis=dict(title="Distinct lobbyists naming this member in their 'covered_position' field", gridcolor="#E5E7EB", color=PRESSPASS_PRIMARY),
        margin=dict(l=320, r=80, t=110, b=110),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0.02, font=dict(size=12)),
    )
    fig.update_layout(**lay)
    add_footer(fig, [
        "Source: Senate LDA lobbyist records (lda.senate.gov), 2022 Q1 – 2026 Q1; Congress press corpus for member lookup.",
        "Method: build a surname → member lookup from the press corpus, keeping ONLY surnames that uniquely identify one bioguide_id. Match those surnames in lobbyist.covered_position text. Each lobbyist counted once per member referenced.",
        "Caveats: covered_position is self-reported. Some surnames still collide outside the press corpus; ambiguous matches are dropped, not redistributed.",
    ])
    write_png(fig, out / "03_revolving_door.png")
    write_sidecar(out / "03_revolving_door.json", {
        "title": "Where K Street's Capitol Hill alumni worked",
        "data": edf.to_dicts(),
        "method": "Unique-surname lookup from press corpus; substring match in lobbyist.covered_position; deduped per lobbyist_id.",
        "source": "data/senate/{YEAR}/filings/filings_{YEAR}.json + data/congress_press/**/*.jsonl",
        "ft_category": "ranking",
        "axis_transform": "linear",
        "n_unique_surnames_used": len(surnames),
    })


# ---------- Chart 4: AI press vs lobbying (say-vs-pay) ----------
def chart_ai_press_vs_lobby(out: Path):
    p = pl.read_parquet("/parquet/press.parquet")
    a = pl.read_parquet("/parquet/senate_activities.parquet")
    p = p.with_columns(
        pl.col("date").str.slice(0,4).cast(pl.Int64, strict=False).alias("y"),
        pl.col("date").str.slice(5,2).cast(pl.Int64, strict=False).alias("m"),
    )
    p = p.with_columns(((pl.col("m")-1)//3 + 1).alias("q"))
    period_order = {"first_quarter": 1, "second_quarter": 2, "third_quarter": 3, "fourth_quarter": 4}
    a = a.with_columns(pl.col("filing_period").replace_strict(period_order).alias("q")).rename({"filing_year": "y"})
    press_ai = p.filter(
        pl.col("text_lc").str.contains("artificial intelligence") |
        pl.col("title_lc").str.contains("artificial intelligence")
    ).group_by(["y", "q"]).len().rename({"len": "press_n"})
    lobby_ai = a.filter(pl.col("description").str.to_lowercase().str.contains("artificial intelligence")).group_by(["y", "q"]).len().rename({"len": "lobby_n"})
    j = press_ai.join(lobby_ai, on=["y", "q"], how="outer_coalesce").sort(["y", "q"]).fill_null(0)
    j = j.with_columns((pl.col("y").cast(pl.Utf8) + " Q" + pl.col("q").cast(pl.Utf8)).alias("label"))
    fig = go.Figure()
    fig.add_scatter(
        x=j["label"], y=j["lobby_n"], mode="lines+markers", line=dict(color=PRESSPASS_PRIMARY, width=3),
        marker=dict(size=9, color=PRESSPASS_PRIMARY), name="Senate lobbying activities mentioning AI",
        hovertemplate="%{x}<br>%{y} lobbying activities<extra></extra>",
    )
    fig.add_scatter(
        x=j["label"], y=j["press_n"], mode="lines+markers", line=dict(color=ACCENT, width=3),
        marker=dict(size=9, color=ACCENT), name="Press releases mentioning AI",
        hovertemplate="%{x}<br>%{y} press releases<extra></extra>",
    )
    fig.add_annotation(x="2022 Q4", y=j.filter(pl.col("label")=="2022 Q4")["lobby_n"][0],
                       text="<b>ChatGPT launches</b><br>Nov 30, 2022", showarrow=True, arrowhead=2, ax=0, ay=-50)
    lay = base_layout(
        "Lobbyists are mentioning AI five times as often as members of Congress",
        "Quarterly counts: Senate lobbying activities vs. House+Senate member press releases that name 'artificial intelligence'",
        height=600,
    )
    lay.update(
        xaxis=dict(tickangle=-35, color=PRESSPASS_PRIMARY),
        yaxis=dict(title="Count per quarter", gridcolor="#E5E7EB", color=PRESSPASS_PRIMARY),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0.02, font=dict(size=12)),
    )
    fig.update_layout(**lay)
    add_footer(fig, [
        "Sources: Senate LDA filings + Congress press release corpus (Congress Press / thescoop.org).",
        "Method: substring match 'artificial intelligence' (case-insensitive) over Senate activity descriptions and press-release text and titles.",
    ])
    write_png(fig, out / "04_ai_say_vs_pay.png")
    write_sidecar(out / "04_ai_say_vs_pay.json", {
        "title": "Lobbyists mention AI five times as often as members of Congress",
        "data": j.to_dicts(),
        "method": "Quarterly counts: Senate LDA activity descriptions vs press release text/title, both filtered by case-insensitive substring 'artificial intelligence'.",
        "source": "data/senate/{YEAR}/filings/filings_{YEAR}.json + data/congress_press/**/*.jsonl",
        "ft_category": "change-over-time",
        "axis_transform": "linear",
    })


# ---------- Chart 5: Foreign-affiliated lobbying ----------
def chart_foreign_affiliations(out: Path):
    f = pl.read_parquet("/parquet/senate_filings.parquet")
    fe = f.filter(pl.col("n_foreign_entities") > 0)
    fe = fe.with_columns(pl.col("foreign_entity_names").str.split("|").alias("fe_list"))
    fe = fe.explode("fe_list").filter(pl.col("fe_list").str.strip_chars() != "")
    top = fe.group_by("fe_list").agg(
        pl.len().alias("n_filings"),
        pl.col("client_name").n_unique().alias("clients"),
        pl.col("filing_year").min().alias("first_year"),
    ).sort("n_filings", descending=True).head(20)
    # short label
    short = top.with_columns(pl.col("fe_list").str.slice(0, 55).alias("name"))
    fig = go.Figure()
    fig.add_bar(
        x=short["n_filings"], y=short["name"], orientation="h",
        marker_color=PRESSPASS_PRIMARY, marker_line_width=0,
        hovertemplate="%{y}<br>%{x} filings declared this foreign affiliation<extra></extra>",
        text=short["n_filings"], textposition="outside", textfont=dict(color=PRESSPASS_PRIMARY, size=11),
    )
    lay = base_layout(
        "Foreign parents declared most often on Senate lobbying filings",
        "Top 20 foreign entities named in 'foreign_entities' across 4+ years of filings",
        height=720, width=1080,
    )
    lay.update(
        yaxis=dict(autorange="reversed", color=PRESSPASS_PRIMARY),
        xaxis=dict(title="Number of Senate filings", gridcolor="#E5E7EB", color=PRESSPASS_PRIMARY),
        margin=dict(l=320, r=80, t=110, b=110),
    )
    fig.update_layout(**lay)
    add_footer(fig, [
        "Source: Senate LDA filings, foreign_entities array. Each filing's foreign_entities list is exploded.",
        "Interpretation: counts how often a foreign-affiliated parent or owner is declared on US lobbying registrations & reports. Cross-reference with FARA filings for full picture.",
    ])
    write_png(fig, out / "05_foreign_entities.png")
    write_sidecar(out / "05_foreign_entities.json", {
        "title": "Top 20 foreign-affiliated parents declared on Senate lobbying filings",
        "data": top.to_dicts(),
        "method": "Senate filings.foreign_entities[] exploded and grouped; top 20 by filing count.",
        "source": "data/senate/{YEAR}/filings/filings_{YEAR}.json (foreign_entities field)",
        "ft_category": "ranking",
        "axis_transform": "linear",
    })


# ---------- Chart 6: Press release volume leaderboard, Q1 2026 ----------
def chart_press_leaderboard(out: Path):
    p = pl.read_parquet("/parquet/press.parquet")
    q1 = p.filter(pl.col("date").is_between(pl.lit("2026-01-01"), pl.lit("2026-03-31")))
    rate = q1.group_by(["bioguide_id", "member_name", "party", "state", "chamber"]).len()
    rate = rate.with_columns((pl.col("len") / 90).alias("per_day"))
    rate = rate.sort("len", descending=True).head(20)
    # color by party
    colors = []
    for party in rate["party"]:
        if party == "Republican":
            colors.append(REP_COLOR)
        elif party == "Democrat":
            colors.append(DEM_COLOR)
        else:
            colors.append(IND_COLOR)
    label = (
        rate.with_columns((pl.col("member_name") + " (" + pl.col("party").str.slice(0,1) + "-" + pl.col("state") + ")").alias("lbl"))["lbl"]
    )
    fig = go.Figure()
    fig.add_bar(
        x=rate["len"], y=label, orientation="h", marker_color=colors, marker_line_width=0,
        text=[f"{n} ({pd:.1f}/day)" for n, pd in zip(rate["len"], rate["per_day"])],
        textposition="outside", textfont=dict(size=11, color=PRESSPASS_PRIMARY),
        hovertemplate="%{y}<br>%{x} releases in Q1 2026 (%{customdata:.1f}/day)<extra></extra>",
        customdata=rate["per_day"], showlegend=False,
    )
    # legend dummies
    fig.add_bar(x=[None], y=[None], marker_color=DEM_COLOR, name="Democrat", showlegend=True)
    fig.add_bar(x=[None], y=[None], marker_color=REP_COLOR, name="Republican", showlegend=True)
    fig.add_bar(x=[None], y=[None], marker_color=IND_COLOR, name="Independent", showlegend=True)
    lay = base_layout(
        "Senate Democrats dominate the 2026 press-release factory",
        "Members of Congress with the most press releases issued, Q1 2026 (Jan 1 – Mar 31)",
        height=720, width=1080,
    )
    lay.update(
        yaxis=dict(autorange="reversed", color=PRESSPASS_PRIMARY),
        xaxis=dict(title="Number of press releases (Q1 2026)", gridcolor="#E5E7EB", color=PRESSPASS_PRIMARY),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0.02, font=dict(size=12)),
        margin=dict(l=280, r=120, t=110, b=110),
    )
    fig.update_layout(**lay)
    add_footer(fig, [
        "Source: Congress press release corpus (Congress Press / thescoop.org), 2026-01-01 to 2026-03-31.",
        "Method: count releases per (bioguide_id, member_name); normalize to per-day rate using 90-day quarter.",
    ])
    write_png(fig, out / "06_press_leaderboard.png")
    write_sidecar(out / "06_press_leaderboard.json", {
        "title": "Press-release leaderboard, Q1 2026",
        "data": rate.to_dicts(),
        "method": "Count of releases per (bioguide_id, member_name) for 2026-01-01 to 2026-03-31; per-day rate computed against 90-day quarter.",
        "source": "data/congress_press/2026-01.jsonl, 2026-02.jsonl, 2026-03.jsonl",
        "ft_category": "ranking",
        "axis_transform": "linear",
    })


# ---------- Chart 7: Cross-corpus reconciliation gap ----------
def chart_house_senate_gap(out: Path):
    sf = pl.read_parquet("/parquet/senate_filings.parquet")
    hf = pl.read_parquet("/parquet/house_filings.parquet")
    # House senate_id format is "<senate_registrant_id>-<filing_year>" or just registrant id; we'll dedupe to names
    s_clients = (
        sf.filter(pl.col("client_name") != "")
          .with_columns(pl.col("client_name").str.to_uppercase().str.strip_chars().alias("k"))
          .select(["filing_year", "k"]).unique()
    )
    h_clients = (
        hf.filter(pl.col("client_name") != "")
          .with_columns(pl.col("client_name").str.to_uppercase().str.strip_chars().alias("k"))
          .select(["filing_year", "k"]).unique()
    )
    # per-year overlap
    rows = []
    for y in [2022, 2023, 2024, 2025, 2026]:
        s = s_clients.filter(pl.col("filing_year") == y)["k"].to_list()
        h = h_clients.filter(pl.col("filing_year") == y)["k"].to_list()
        ss, hs = set(s), set(h)
        both = ss & hs
        rows.append({"year": y, "senate_only": len(ss - hs), "house_only": len(hs - ss), "both": len(both)})
    fig = go.Figure()
    years = [r["year"] for r in rows]
    fig.add_bar(x=years, y=[r["both"] for r in rows], name="In both Senate + House",
                marker_color=PRESSPASS_PRIMARY, marker_line_width=0,
                hovertemplate="%{x}<br>Both: %{y}<extra></extra>")
    fig.add_bar(x=years, y=[r["senate_only"] for r in rows], name="Senate filing only",
                marker_color=DEM_COLOR, marker_line_width=0,
                hovertemplate="%{x}<br>Senate-only: %{y}<extra></extra>")
    fig.add_bar(x=years, y=[r["house_only"] for r in rows], name="House filing only",
                marker_color=REP_COLOR, marker_line_width=0,
                hovertemplate="%{x}<br>House-only: %{y}<extra></extra>")
    lay = base_layout(
        "Hundreds of clients show up in only one chamber's lobbying disclosures",
        "Unique client names (uppercased exact match) per year, by which chamber's filings they appear in",
        height=560,
    )
    lay.update(
        barmode="stack",
        yaxis=dict(title="Unique client names", gridcolor="#E5E7EB", color=PRESSPASS_PRIMARY),
        xaxis=dict(title="Filing year", color=PRESSPASS_PRIMARY),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0.02, font=dict(size=12)),
    )
    fig.update_layout(**lay)
    add_footer(fig, [
        "Source: Senate LDA filings (lda.senate.gov) + House Clerk LD-2/LD-1 XML.",
        "Method: take unique client_name per year per chamber (uppercased, whitespace trimmed); intersect.",
        "Caveat: exact match misses variants like 'INC.' vs 'INC' and 'AND' vs '&'. The gap is an upper bound; entity resolution would reduce it.",
    ])
    write_png(fig, out / "07_house_senate_gap.png")
    write_sidecar(out / "07_house_senate_gap.json", {
        "title": "Clients appearing in only one chamber",
        "data": rows,
        "method": "Unique uppercase-stripped client_name per year per chamber; stack of intersection vs symmetric difference.",
        "source": "data/senate/{YEAR}/filings/filings_{YEAR}.json + data/house/{YEAR}_{QUARTER}_XML/*.xml",
        "ft_category": "part-to-whole",
        "axis_transform": "linear",
    })


# ---------- Chart 8: Trump-Vance inaugural contributions (LD-203) ----------
def chart_inaugural_money(out: Path):
    ci = pl.read_parquet("/parquet/senate_contrib_items.parquet")
    trump = ci.filter(pl.col("payee").str.to_uppercase().str.contains("TRUMP VANCE INAUGURAL"))
    by_reg = trump.group_by("registrant_name").agg(
        pl.col("amount").sum().alias("amount"),
        pl.len().alias("n_items"),
    ).sort("amount", descending=True).head(20)
    total = float(trump["amount"].sum())
    fig = go.Figure()
    fig.add_bar(
        x=by_reg["amount"] / 1_000_000, y=by_reg["registrant_name"],
        orientation="h", marker_color=PRESSPASS_PRIMARY, marker_line_width=0,
        text=[f"${v/1_000_000:.1f}M" for v in by_reg["amount"]], textposition="outside",
        textfont=dict(color=PRESSPASS_PRIMARY, size=11),
        hovertemplate="%{y}<br>$%{x:.2f}M<extra></extra>",
    )
    lay = base_layout(
        f"Lobbyist filers reported ${total/1_000_000:.0f}M to the Trump-Vance inaugural fund",
        "Top 20 LDA-registered organizations by total reported contribution to 'Trump Vance Inaugural Committee' (LD-203 filings, Q4 2024 – Q2 2025)",
        height=720, width=1180,
    )
    lay.update(
        yaxis=dict(autorange="reversed", color=PRESSPASS_PRIMARY),
        xaxis=dict(title="Total reported contribution (US$ millions)", gridcolor="#E5E7EB", color=PRESSPASS_PRIMARY),
        margin=dict(l=320, r=80, t=110, b=120),
    )
    fig.update_layout(**lay)
    add_footer(fig, [
        "Source: Senate LD-203 contribution items (lda.senate.gov/api/v1/contributions), 2024 Q3 – 2025 Q4.",
        "Method: substring match for 'TRUMP VANCE INAUGURAL' (case-insensitive) in the payee field. Amounts summed per registrant_name (the LDA-reporting entity).",
        "Note: LD-203 reports cover contributions BY lobbyists, their PACs, and their employers. For comparison, all payees containing 'BIDEN' summed to about $5.4M across the entire 5-year corpus.",
    ])
    write_png(fig, out / "08_inaugural_money.png")
    write_sidecar(out / "08_inaugural_money.json", {
        "title": "Lobbyist filers reported $67M to the Trump-Vance inaugural fund",
        "data": by_reg.to_dicts(),
        "total_dollars": total,
        "n_items": int(trump.height),
        "method": "LD-203 contribution_items where payee contains 'TRUMP VANCE INAUGURAL' (case-insensitive); summed by registrant_name.",
        "source": "data/senate/{YEAR}/contributions/contributions_{YEAR}.json",
        "ft_category": "ranking",
        "axis_transform": "linear",
    })


# ---------- Chart 9: New Senate registrations by quarter ----------
def chart_new_registrations(out: Path):
    f = pl.read_parquet("/parquet/senate_filings.parquet")
    rr = f.filter(pl.col("filing_type") == "RR")
    period_order = {"first_quarter": 1, "second_quarter": 2, "third_quarter": 3, "fourth_quarter": 4}
    rr = rr.with_columns(pl.col("filing_period").replace_strict(period_order).alias("q"))
    q = rr.group_by(["filing_year", "q"]).len().sort(["filing_year", "q"])
    q = q.with_columns((pl.col("filing_year").cast(pl.Utf8) + " Q" + pl.col("q").cast(pl.Utf8)).alias("label"))
    colors = []
    for r in q.iter_rows(named=True):
        # highlight Q1 2025 (Trump inauguration quarter)
        if r["filing_year"] == 2025 and r["q"] == 1:
            colors.append(ACCENT)
        else:
            colors.append(PRESSPASS_PRIMARY)
    fig = go.Figure()
    fig.add_bar(
        x=q["label"], y=q["len"], marker_color=colors, marker_line_width=0,
        hovertemplate="%{x}: %{y} new registrations<extra></extra>",
        text=q["len"], textposition="outside", textfont=dict(color=PRESSPASS_PRIMARY, size=11),
    )
    fig.add_annotation(
        x="2025 Q1", y=int(q.filter(pl.col("label") == "2025 Q1")["len"][0]),
        text="<b>Q1 2025: Trump inauguration</b><br>2,511 new Senate registrations<br>(+91% vs Q1 2022, +69% vs Q1 2023)",
        showarrow=True, arrowhead=2, ax=80, ay=-60, font=dict(size=12, color=PRESSPASS_PRIMARY),
        bgcolor="rgba(255,255,255,0.95)", bordercolor=ACCENT, borderwidth=1, borderpad=6,
    )
    lay = base_layout(
        "Trump 2.0 triggered the largest lobbying rush since 2022",
        "New Senate LDA lobbyist registrations (filing_type = RR) per quarter",
        height=620,
    )
    lay.update(
        xaxis=dict(tickangle=-35, color=PRESSPASS_PRIMARY),
        yaxis=dict(title="New registrations", gridcolor="#E5E7EB", color=PRESSPASS_PRIMARY),
    )
    fig.update_layout(**lay)
    add_footer(fig, [
        "Source: Senate LDA filings (lda.senate.gov), filing_type='RR' (new registrant–client engagements).",
        "Method: count of RR filings per (filing_year, filing_period). Q1 2026 is partial Senate data; 2026 Q1 = registrations filed Jan 1 – Mar 31, 2026.",
    ])
    write_png(fig, out / "09_new_registrations.png")
    write_sidecar(out / "09_new_registrations.json", {
        "title": "New Senate registrations by quarter",
        "data": q.to_dicts(),
        "method": "Senate filings with filing_type='RR' grouped by (filing_year, filing_period).",
        "source": "data/senate/{YEAR}/filings/filings_{YEAR}.json",
        "ft_category": "change-over-time",
        "axis_transform": "linear",
    })


CHARTS = {
    "ai_boom": chart_ai_boom,
    "issue_heatmap": chart_issue_heatmap,
    "revolving_door": chart_revolving_door,
    "ai_say_vs_pay": chart_ai_press_vs_lobby,
    "foreign": chart_foreign_affiliations,
    "press_leaderboard": chart_press_leaderboard,
    "house_senate_gap": chart_house_senate_gap,
    "inaugural_money": chart_inaugural_money,
    "new_registrations": chart_new_registrations,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out_dir", default="/charts")
    ap.add_argument("--charts", nargs="*", default=list(CHARTS.keys()))
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name in args.charts:
        if name not in CHARTS:
            print(f"unknown: {name}")
            continue
        print(f"[chart] {name}")
        CHARTS[name](out)
    print(f"wrote {len(args.charts)} charts -> {out}")


if __name__ == "__main__":
    main()
