# Checkpoint 3 — Submission complete

Date: 2026-05-15 (end)
Branch: `spmartin823/lobbying-press-charts`
Remote: pushed to https://github.com/press-pass/journalism-skills

## Submission inventory

| Required artefact | Location | Status |
|---|---|---|
| Agent Skill(s) | `skills/lobbying-corpus-build/`, `press-corpus-build/`, `lobbying-charts/`, `chart-eval/`, `revolving-door-extract/`, `say-vs-pay-correlate/` | ✓ |
| Findings Report | `FINDINGS.md` (7 sourced findings, each citing filing_uuid/bioguide_id) | ✓ |
| Interaction Traces | `traces/session.md` + `checkpoints/00–03.md` + `artifacts/` (parquet + md) | ✓ |
| README.md | `SUBMISSION.md` (challenge-required) + repo `README.md` (skill list updated) | ✓ |
| Charts | `charts/*.png` (9 PNGs), `charts/*.json` (9 sidecars), `charts/eval.md` (chart-eval scoring) | ✓ |

## Tool chain reproducibility

```
docker build -t lobbypress-analysis analysis/
# All 6 skills run inside this image; pipeline reruns end-to-end in ~15 min.
```

## Self-evaluation summary

`charts/eval.md` produced these composite scores against the fused Tufte / ChartMimic / FT
Visual Vocabulary rubric:

| Chart | Score |
|---|---:|
| 01_ai_lobbying_boom.png | 2.86 |
| 02_issue_heatmap.png | 2.57 |
| 03_revolving_door.png | 2.86 |
| 04_ai_say_vs_pay.png | 2.43 |
| 05_foreign_entities.png | **3.00** |
| 06_press_leaderboard.png | 2.86 |
| 07_house_senate_gap.png | 2.43 |
| 08_inaugural_money.png | 2.86 |
| 09_new_registrations.png | 2.71 |
| **Mean** | **2.73** |

Three charts flagged for minor issues (color count slightly over the chartjunk threshold, low
non-white density on the sparse line chart). All have explicit `ft_category` + provenance.

## What was NOT done (transparency)

- No vision-LLM judge (VisEval Readability prompts) was run — only the deterministic ChartMimic-style
  + Tufte rubric. The skill explicitly notes how to plug in VisEval / Promptfoo for an LLM-judge
  pass.
- No FEC / FARA / Congress.gov join was performed. The findings stand on the GAIN corpus alone.
- The revolving-door surname disambiguation depends on the current press corpus and does NOT
  resolve historical members (Sherrod Brown vs Shontel Brown). This is documented in the
  affected chart and finding.
- The chart-eval skill is a floor, not a ceiling: composite 3.0 means basic hygiene passes,
  not that the chart tells the right story. Editorial review still required.

## Final commit
`a2577e3` — `feat: GAIN Agentic Investigation Challenge submission`

(Note: an initial commit erroneously picked up a stale `/tmp/commit_msg.txt` body from a sibling
workspace. Amended in place before push.)
