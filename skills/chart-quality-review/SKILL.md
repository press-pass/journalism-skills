---
description: Score a generated chart against four external rubrics (Andy Kirk TAE, Stephen Few effectiveness, Stephanie Evergreen 23-item checklist, Penn State 30-pt) before publication. Outputs a structured JSON scorecard and a Markdown summary with the auto-flagged anti-patterns. Designed to avoid self-evaluation drift in agent chart workflows.
---

Use this skill to gate every chart before it ships. The skill scores the
chart on four independent, externally-published rubrics — not the model's
own taste. Auto-flag any chart with score < 75% Evergreen, missing source
attribution, or detected Tufte chartjunk.

## When to use

- "Review this chart before I publish."
- "Is this finding-bar visualization good enough?"
- "Compare two design candidates head-to-head."

## How to run

```bash
docker compose -f analysis/docker/docker-compose.yml exec florence \
    python analysis/tools/chart_review.py \
        --chart analysis/charts/output/01_inaugural_donors.png \
        --code analysis/charts/chart_inaugural.py \
        --data analysis/charts/output/01_inaugural_donors.csv \
        --out analysis/findings/chart_review_01.json
```

Inputs:
- `--chart PATH` — rendered chart (PNG, SVG, or PDF). Required.
- `--code PATH` — the chart-generating Python file. Optional but helps the
  Evergreen detector check for "data-ink" violations.
- `--data PATH` — the underlying data (CSV/Parquet). Optional; enables a
  truthfulness check (do bar lengths match the values in the data?).
- `--out PATH` — output JSON path. Required.

## Rubric coverage

The script applies each rubric *deterministically* where it can, and lifts
the harder qualitative items into a structured prompt-template that a human
reviewer (or, optionally, a vision-language model) completes.

### 1. Kirk TAE gate (auto-fail)
- **Trustworthy:** source attribution must be present in the rendered image
  (OCR substring check for "Source:" or "source:").
- **Accessible:** color contrast ratios computed via WCAG 2.1 formula on
  text vs background; flag anything < 4.5.
- **Elegant:** detected if no overlapping text, no truncated labels.

### 2. Few effectiveness (1–5 per dimension)
Seven dimensions: Usefulness, Completeness, Perceptibility, Truthfulness,
Intuitiveness, Aesthetics, Engagement. Auto-scored 1–5 where deterministic
checks apply; remaining items emit a structured prompt for an editor.

### 3. Evergreen 23-item checklist (0/1/2 per item)
Five sections (Text, Arrangement, Color, Lines, Overall). The 23 items
are evaluated via:
- Pixel-level analysis (e.g., "no decorative drop shadows" → detect
  `BoxShadow` style in the SVG; "y-axis starts at zero" → parse axis limits).
- Static analysis of the Python chart code (where provided) for known
  anti-patterns: `style.use('seaborn-dark')`, `plt.pie(...)`, `3d=True`, etc.
- The remaining items become an editor checklist.

### 4. Penn State 30-pt (3 categories × 10)
- Effective Communication
- Creativity & Innovation
- Design & Aesthetics

These are subjective — the skill emits a prompt template for an editor.

## Output schema

```json
{
  "chart": "analysis/charts/output/01_inaugural_donors.png",
  "kirk_tae": {"trustworthy": "pass", "accessible": "pass", "elegant": "pass"},
  "few": {
    "usefulness": 5, "completeness": 5, "perceptibility": 4,
    "truthfulness": "pass", "intuitiveness": 4, "aesthetics": 4, "engagement": 4
  },
  "evergreen": {
    "text": [2,2,2,2,2,1], "arrangement": [2,2,2,2,2], "color": [2,1,2,2],
    "lines": [2,2,2,2], "overall": [2,2,1,2],
    "total": 39, "max": 46, "pct": 0.848
  },
  "penn_state": {"effective": null, "creativity": null, "design": null,
                 "editor_prompt": "..." },
  "flags": []
}
```

## Anti-patterns auto-flagged

- No `source:` line in OCR result
- Y-axis truncated (axis min > 0 on a continuous-zero metric)
- 3D effects, drop shadows, gradient fills, decorative icons in the SVG
- Rainbow categorical palette on ordinal data (heuristic: hue rotation > 270°)
- More than 8 categorical colors without a legend
- Labels rotated > 45° (rarely necessary; sign of cramped layout)
- Title is a noun phrase ("Lobbying spend") not a finding ("Lobbying spend hit $6B")

## Verifiability

Every scorecard is JSON. Every flag emits the exact pixel region or code
line that triggered it. The skill is reproducible: same inputs → same
scorecard.
