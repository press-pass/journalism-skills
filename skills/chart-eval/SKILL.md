---
description: Self-evaluate rendered charts against a fused Tufte + ChartMimic + FT Visual Vocabulary rubric. Deterministic — no LLM required. Use to validate chart submissions before publishing or before a competition. Input: a directory of PNG+JSON sidecar pairs.
---

You score a directory of finished charts on seven dimensions inspired by the most-cited free
rubrics in data journalism + visualization research. Output: a markdown table plus per-chart
JSON.

The rubric is deliberately deterministic (no LLM judge): the user can re-run it after every
chart change and the score is reproducible. For a higher-power evaluation, pipe the same PNGs
through a vision-LLM judge using [VisEval](https://github.com/microsoft/VisEval) or
[Promptfoo](https://promptfoo.dev) — but the deterministic pass catches the most obvious
problems in seconds.

## How it scores

| Dimension | Source | Signal |
|---|---|---|
| Data-ink ratio | Tufte | share of non-white pixels in the central 70% — too low or too high penalised |
| Graphical integrity (lie factor) | Tufte | requires `axis_transform: linear` in sidecar (or warns) |
| Clear labeling | Tufte / Knaflic | sidecar must declare a substantive title |
| No chartjunk | Tufte | distinct quantized colors ≤ ~24 |
| FT chart-type-to-message fit | FT Visual Vocabulary | optional `ft_category` field in sidecar must match a verb in the chart title |
| Provenance | NICAR best practice | sidecar must name the data source / method |
| Verifiability | GAIN scoring rubric | sidecar must contain ≥3 data rows so the chart can be reconstructed from JSON alone |

Each dimension is scored 0/1/2/3 (mostly 1 or 3 — there are few intermediate cases) and the
composite is the mean.

## Inputs

- `--charts_dir` — directory containing `*.png` + matching `*.json` sidecars. Default `/charts`.
- `--out_md` — markdown report path. Default `/charts/eval.md`.

## Step 1: Run the evaluator

```bash
docker run --rm \
  -v "$(realpath <CHARTS_DIR>):/charts" \
  -v "$(realpath skills/chart-eval/scripts):/scripts:ro" \
  lobbypress-analysis \
  bash -c "pip install --quiet pillow && python /scripts/eval_chart.py --charts_dir /charts --out_md /charts/eval.md"
```

The `pillow` install adds ~5 seconds; pre-install it in your docker image to skip.

## Step 2: Read the markdown report

```bash
cat <CHARTS_DIR>/eval.md
```

The first table gives a one-line scorecard per chart; the per-chart sections list specific
warnings.

## Step 3: Iterate

For every chart with `composite < 2.5`:

- Add a `title` and `method` field to the sidecar.
- Reduce colors to ≤ 7 categorical hues.
- Add an `ft_category` to the sidecar that matches the [FT Visual Vocabulary](https://github.com/Financial-Times/chart-doctor) (deviation / correlation / ranking / distribution / change-over-time / magnitude / part-to-whole / spatial / flow).
- Make sure the sidecar `data` array contains enough rows to redraw the chart.

Re-run the evaluator. Repeat until every chart has `composite >= 2.6`.

## Caveats — flag to the user before they trust the score

- This is a **floor**, not a ceiling. A 3.0 composite means the chart passes basic hygiene; it
  does not mean the chart tells the right story.
- The color-count heuristic is approximate — a soft gradient heatmap can register 60+
  quantized colors despite being well-designed. Override with a sidecar `palette_intentional: true`
  to bypass the check (not yet implemented; PR welcome).
- The FT verb match is a hint. A good chart can choose a title that doesn't include FT's keywords
  but still be appropriate. Use this as a sanity prompt, not a hard rule.
- The deterministic evaluator does NOT catch deceptive zero-suppressed axes, misleading
  aggregation, or genuine data lies. Always have a human edit pass.

## Rubric origins

This skill bundles three free, open-source frameworks:

- [VisEval (Microsoft Research, IEEE VIS 2024)](https://github.com/microsoft/VisEval) — readability/legality/validity prompts.
- [ChartMimic (ICLR 2025)](https://github.com/ChartMimic/ChartMimic) — deterministic text/layout/type/color scorers.
- [FT Visual Vocabulary (MIT)](https://github.com/Financial-Times/chart-doctor) — chart-type-to-message fit.
- [Tufte's 6 principles of graphical integrity](https://faculty.cc.gatech.edu/~stasko/7450/16/Notes/tufte.pdf).

Use the journalism-defensible names (Tufte, FT VV) when explaining the rubric to editors or
panelists.
