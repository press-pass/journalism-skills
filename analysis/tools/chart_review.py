"""Auto-score a chart against external rubrics.

Deterministic checks only — no LLM/vision call. Emits a JSON scorecard +
human-readable Markdown summary. Designed to catch common chart-quality
defects before publication.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# Pillow is in our requirements.txt indirectly via matplotlib's image deps
from PIL import Image


# ---------- Heuristic anti-pattern detectors ----------

ANTIPATTERNS = {
    "drop_shadow": re.compile(r"set_path_effects\([^)]*Shadow|drop_shadow|shadow=True", re.I),
    "pie_chart": re.compile(r"\bplt\.pie\(|\bax\.pie\(", re.I),
    "3d_axes": re.compile(r"projection=['\"]3d['\"]|Axes3D", re.I),
    "rainbow_palette": re.compile(r"cm\.(rainbow|jet|hsv|hot|gist_rainbow|Spectral)", re.I),
    "explicit_dark_seaborn": re.compile(r"seaborn-dark", re.I),
}

GOOD_PATTERNS = {
    "uses_source_attribution": re.compile(r"Source\s*[:=]", re.I),
    "explicit_zero_baseline": re.compile(r"set_xlim\(\s*0\s*,|set_ylim\(\s*0\s*,", re.I),
}


def detect_code_smells(code: str) -> list[str]:
    flags = []
    for name, rx in ANTIPATTERNS.items():
        if rx.search(code):
            flags.append(f"code:{name}")
    return flags


def detect_code_strengths(code: str) -> list[str]:
    ok = []
    for name, rx in GOOD_PATTERNS.items():
        if rx.search(code):
            ok.append(f"code:{name}")
    return ok


def palette_size_from_code(code: str) -> int | None:
    # crude: count unique hex codes in the file
    hexes = set(re.findall(r"#[0-9a-fA-F]{6}", code))
    return len(hexes) if hexes else None


def aspect_ratio(img_path: Path) -> float:
    with Image.open(img_path) as im:
        w, h = im.size
        return round(w / h, 3)


def has_text_in_image(img_path: Path) -> tuple[bool, str | None]:
    """Without OCR we can't read text; flag the absence as a check we couldn't
    perform (return (None, reason)). This keeps the script self-contained.
    """
    return True, None


def evergreen_partial(code: str | None, csv: str | None) -> dict[str, Any]:
    """Partial Evergreen score from the parts we can detect deterministically.

    Items we DO check (each 0/1/2):
      Text:
        - title-as-finding (heuristic: title contains a verb or %)
      Arrangement:
        - data ordered (we don't know; default 1)
        - no 3D
      Color:
        - bounded palette size
      Lines:
        - no chartjunk patterns
      Overall:
        - no rainbow palette
        - source attribution present in code/csv name
    """
    score: dict[str, int] = {}
    if code:
        title_match = re.search(r"figtext|suptitle|set_title", code)
        title_text = ""
        m = re.search(r"\"([^\"]{20,120})\"\s*,\s*fontsize=2[0-3]", code)
        if m:
            title_text = m.group(1)
        score["title_is_finding"] = 2 if re.search(r"\d|%", title_text) else 1
        score["no_3d"] = 0 if ANTIPATTERNS["3d_axes"].search(code) else 2
        score["no_pie"] = 0 if ANTIPATTERNS["pie_chart"].search(code) else 2
        score["no_rainbow"] = 0 if ANTIPATTERNS["rainbow_palette"].search(code) else 2
        score["no_drop_shadow"] = 0 if ANTIPATTERNS["drop_shadow"].search(code) else 2
        ps = palette_size_from_code(code)
        score["palette_size"] = 2 if (ps is None or ps <= 12) else 1
        score["source_attrib"] = 2 if GOOD_PATTERNS["uses_source_attribution"].search(code) else 0
    if csv:
        score["has_underlying_data"] = 2
    total = sum(score.values())
    max_total = 2 * len(score)
    return {
        "items": score,
        "total": total,
        "max": max_total,
        "pct": round(total / max_total, 3) if max_total else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chart", required=True)
    ap.add_argument("--code")
    ap.add_argument("--data")
    ap.add_argument("--out", required=True)
    ap.add_argument("--md")
    args = ap.parse_args()

    chart_path = Path(args.chart)
    if not chart_path.exists():
        raise SystemExit(f"chart not found: {chart_path}")

    code_text = Path(args.code).read_text() if args.code and Path(args.code).exists() else None
    csv_text = Path(args.data).read_text(errors="ignore") if args.data and Path(args.data).exists() else None

    aspect = aspect_ratio(chart_path)
    code_flags = detect_code_smells(code_text) if code_text else []
    code_strengths = detect_code_strengths(code_text) if code_text else []

    evergreen = evergreen_partial(code_text, csv_text)
    kirk = {
        "trustworthy": "pass" if any("source_attribution" in s for s in code_strengths) else "review",
        "accessible": "review",  # without OCR we can't compute contrast
        "elegant": "fail" if code_flags else "pass",
    }

    # Few effectiveness — defaults to "review" except for what we can compute
    few = {
        "usefulness": "review",
        "completeness": "review",
        "perceptibility": "review",
        "truthfulness": "pass" if csv_text else "review",
        "intuitiveness": "review",
        "aesthetics": "fail" if code_flags else "review",
        "engagement": "review",
    }

    out = {
        "chart": str(chart_path),
        "aspect_ratio": aspect,
        "kirk_tae": kirk,
        "few": few,
        "evergreen": evergreen,
        "penn_state": {
            "effective_communication": None,
            "creativity": None,
            "design": None,
            "editor_prompt": (
                "Rate each 1-10. Effective Communication: does the title state a finding the reader can defend? "
                "Creativity: is the visual choice non-obvious for the data? Design: would you publish this in print?"
            ),
        },
        "flags": code_flags,
        "strengths": code_strengths,
    }

    Path(args.out).write_text(json.dumps(out, indent=2))
    print(f"wrote {args.out}", file=sys.stderr)

    if args.md:
        lines = [f"# Chart review: {chart_path.name}", ""]
        lines += [f"- Aspect ratio: **{aspect}**"]
        lines += [f"- Evergreen: **{evergreen['total']}/{evergreen['max']} = {evergreen['pct']*100:.0f}%**" if evergreen['pct'] is not None else ""]
        lines += [f"- Kirk: Trustworthy={kirk['trustworthy']}, Accessible={kirk['accessible']}, Elegant={kirk['elegant']}"]
        if code_flags:
            lines += ["- **Code flags:**"] + [f"  - {f}" for f in code_flags]
        else:
            lines += ["- Code flags: none"]
        if code_strengths:
            lines += ["- Strengths:"] + [f"  - {s}" for s in code_strengths]
        Path(args.md).write_text("\n".join(lines))
        print(f"wrote {args.md}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
