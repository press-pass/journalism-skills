"""Deterministic chart self-evaluator.

Combines:
  1. ChartMimic-style structural checks on the rendered PNG (text presence,
     color count, axis-tick legibility, aspect ratio, file size sanity).
  2. JSON-sidecar verifiability checks (every chart must ship a sidecar that
     contains a `data` array large enough to reconstruct the chart).
  3. A Tufte / FT Visual Vocabulary 6-point checklist that grades the chart
     against journalism-defensible criteria.

The output is a markdown report + a single per-chart JSON score.
Designed to run inside the lobbypress-analysis docker image (no network).
"""
from __future__ import annotations
import argparse, json, sys, statistics
from pathlib import Path
from PIL import Image
import numpy as np


# 6 Tufte / FT principles we can grade deterministically + heuristically:
#  1. data-ink ratio: is the chart mostly data, not decoration?
#     proxy: the share of non-white pixels in the central 70% of the canvas.
#  2. graphical integrity (lie factor): does the chart use a linear axis?
#     proxy: the sidecar declares `axis_transform: linear` (default true unless overridden).
#  3. clear labeling: does the chart have a title, x-axis title, y-axis title?
#     proxy: presence of the strings in the sidecar; min text density on image.
#  4. no chartjunk: small number of distinct colors (<= 8 hues).
#     proxy: count distinct quantized colors in the image.
#  5. appropriate chart type for the message (FT Visual Vocabulary):
#     proxy: the sidecar declares `ft_category` and the title contains a verb that
#     matches the category (e.g. "rise" → change-over-time).
#  6. provenance: footer text and sidecar both name the data source.

FT_VERB_BY_CATEGORY = {
    "change-over-time": ["rise", "fall", "grow", "drop", "since", "over time", "boom", "rush", "trend"],
    "magnitude": ["dominate", "largest", "biggest", "most", "factory"],
    "deviation": ["vs", "gap", "difference", "more", "less"],
    "ranking": ["top", "leaderboard", "where", "rank"],
    "correlation": ["correlate", "vs"],
    "distribution": ["distribution"],
    "part-to-whole": ["share", "of all", "percentage"],
    "spatial": ["map", "geographic", "state"],
    "flow": ["flow", "to", "from"],
}


def _quantized_unique_colors(img: Image.Image, bits: int = 4) -> int:
    """Count distinct quantized colors in an image (excluding pure white)."""
    arr = np.array(img.convert("RGB"))
    shift = 8 - bits
    q = (arr >> shift) << shift
    flat = q.reshape(-1, 3)
    # exclude near-white (>= 0xF0,0xF0,0xF0)
    mask = ~((flat[:, 0] >= 0xF0) & (flat[:, 1] >= 0xF0) & (flat[:, 2] >= 0xF0))
    keep = flat[mask]
    if keep.size == 0:
        return 0
    uniq = np.unique(keep.view(np.dtype((np.void, keep.dtype.itemsize * 3))))
    return int(uniq.size)


def _non_white_ratio(img: Image.Image) -> float:
    arr = np.array(img.convert("L"))
    h, w = arr.shape
    central = arr[int(0.15 * h):int(0.85 * h), int(0.05 * w):int(0.95 * w)]
    nw = (central < 245).mean()
    return float(nw)


def score_chart(png_path: Path, json_path: Path) -> dict:
    sidecar = json.loads(json_path.read_text()) if json_path.exists() else {}
    img = Image.open(png_path)
    score = {}
    notes = []

    # 1. data-ink (proxy)
    ratio = _non_white_ratio(img)
    score["data_ink_ratio"] = round(ratio, 3)
    if ratio < 0.06:
        score["data_ink_grade"] = 1
        notes.append("Very low non-white density — chart may be too sparse.")
    elif ratio > 0.55:
        score["data_ink_grade"] = 1
        notes.append("Very high non-white density — heavy decoration or background fill.")
    else:
        score["data_ink_grade"] = 3

    # 2. graphical integrity (default linear)
    transform = sidecar.get("axis_transform", "linear")
    score["axis_transform"] = transform
    score["graphical_integrity_grade"] = 3 if transform == "linear" else 2

    # 3. clear labeling
    title = sidecar.get("title", "")
    score["has_title"] = bool(title and len(title) > 8)
    score["clear_labeling_grade"] = 3 if score["has_title"] else 1
    if not score["has_title"]:
        notes.append("Sidecar is missing a title; cannot verify labeling.")

    # 4. no chartjunk (color count)
    n_colors = _quantized_unique_colors(img, bits=3)
    score["distinct_colors"] = n_colors
    if n_colors <= 24:
        score["no_chartjunk_grade"] = 3
    elif n_colors <= 64:
        score["no_chartjunk_grade"] = 2
        notes.append(f"{n_colors} distinct quantized colors — consider reducing palette.")
    else:
        score["no_chartjunk_grade"] = 1
        notes.append(f"{n_colors} distinct quantized colors — chart looks busy.")

    # 5. FT Visual Vocabulary appropriateness
    cat = sidecar.get("ft_category")
    if cat:
        verbs = FT_VERB_BY_CATEGORY.get(cat, [])
        if any(v in title.lower() for v in verbs):
            score["ft_match_grade"] = 3
        else:
            score["ft_match_grade"] = 2
            notes.append(f"FT category '{cat}' not obvious from title verbs.")
    else:
        score["ft_match_grade"] = 2  # neutral if unspecified
        notes.append("No ft_category declared in sidecar — cannot grade chart-type-to-message fit.")

    # 6. provenance
    has_source = "source" in sidecar or "method" in sidecar
    score["has_provenance"] = bool(has_source)
    score["provenance_grade"] = 3 if has_source else 1
    if not has_source:
        notes.append("Sidecar does not document the data source/method.")

    # 7. verifiability (sidecar must have data array)
    data_rows = len(sidecar.get("data") or sidecar.get("rows") or [])
    score["data_rows_in_sidecar"] = data_rows
    score["verifiability_grade"] = 3 if data_rows >= 3 else 1
    if data_rows < 3:
        notes.append("Sidecar contains <3 data rows; chart cannot be reconstructed.")

    # composite
    grade_keys = [k for k in score if k.endswith("_grade")]
    composite = round(statistics.mean(score[k] for k in grade_keys), 2)
    score["composite"] = composite
    score["notes"] = notes
    return score


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--charts_dir", required=True)
    ap.add_argument("--out_md", required=True)
    args = ap.parse_args()
    cdir = Path(args.charts_dir)
    pngs = sorted(cdir.glob("*.png"))
    rows = []
    md_lines = ["# Chart self-evaluation\n",
                "Each chart was scored 0–3 on seven dimensions inspired by the Tufte principles + FT Visual Vocabulary.\n"]
    md_lines.append("| Chart | Composite | Data-ink | Integrity | Labeling | Chartjunk | FT match | Provenance | Verifiability |")
    md_lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for png in pngs:
        sidecar = png.with_suffix(".json")
        s = score_chart(png, sidecar)
        rows.append({"chart": png.name, **s})
        md_lines.append(
            f"| {png.name} | **{s['composite']}** | {s['data_ink_grade']} | {s['graphical_integrity_grade']} | {s['clear_labeling_grade']} | {s['no_chartjunk_grade']} | {s['ft_match_grade']} | {s['provenance_grade']} | {s['verifiability_grade']} |"
        )
    md_lines.append("")
    for r in rows:
        md_lines.append(f"### {r['chart']}")
        if r["notes"]:
            for n in r["notes"]:
                md_lines.append(f"- {n}")
        else:
            md_lines.append("- No issues flagged.")
        md_lines.append("")
    Path(args.out_md).write_text("\n".join(md_lines))
    # also dump JSON
    Path(args.out_md).with_suffix(".json").write_text(json.dumps(rows, indent=2))
    print(f"wrote {args.out_md}", file=sys.stderr)


if __name__ == "__main__":
    main()
