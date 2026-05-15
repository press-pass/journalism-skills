---
description: Cross-corpus 'Say-vs-Pay' analysis. Given one or more keywords, compute per-quarter counts of (a) congressional press releases mentioning the keyword(s) and (b) Senate + House lobbying activity descriptions mentioning the same keyword(s). Also reports a Pearson correlation. Use when the user asks 'does what members talk about correlate with what's being lobbied on?' Input: keywords + parquet paths.
---

You quantify whether lobbying spend on an issue tracks the volume of congressional messaging on
the same issue. The skill is keyword-driven so the user can run it on AI, crypto, healthcare,
immigration, climate, or anything else they want to investigate.

## Inputs

- `--keywords` — one or more substrings, **case-insensitive**, matched literally (not regex).
  Records match if ANY keyword appears in the press release text/title or lobbying activity
  description.
- `--press_parquet`, `--senate_activities_parquet`, `--house_activities_parquet` — the parquet
  files produced by `press-corpus-build` + `lobbying-corpus-build`.
- `--out_parquet` — quarter-grain output.
- `--out_members_parquet` — optional, per-member press counts.
- `--out_summary_md` — optional, markdown one-pager with the headline correlation.

## Step 1: Run the correlator

```bash
docker run --rm \
  -v "$(realpath <PARQUET_DIR>):/parquet:ro" \
  -v "$(realpath <OUT_DIR>):/out" \
  -v "$(realpath skills/say-vs-pay-correlate/scripts):/scripts:ro" \
  lobbypress-analysis \
  bash -c "pip install --quiet scipy && python /scripts/correlate.py \
    --keywords 'artificial intelligence' 'machine learning' \
    --press_parquet /parquet/press.parquet \
    --senate_activities_parquet /parquet/senate_activities.parquet \
    --house_activities_parquet /parquet/house_activities.parquet \
    --out_parquet /out/sayvspay_ai.parquet \
    --out_members_parquet /out/sayvspay_ai_members.parquet \
    --out_summary_md /out/sayvspay_ai.md"
```

(Pre-install scipy in your image to skip the live install.)

## Step 2: Read the headline

The markdown summary names a Pearson r over the quarterly time series and shows the per-quarter
table. Useful sanity checks before drawing conclusions:

- r > 0.6: strong positive — lobbying and messaging move together.
- 0.2 < r < 0.6: weak co-movement — usually means both ride the same news cycle.
- r near 0 or negative: divergence — issues being heavily lobbied but rarely discussed (or vice
  versa). These are the **highest-value leads** for an investigation.

## Step 3: Drill into outlier members

```python
import polars as pl
m = pl.read_parquet("sayvspay_ai_members.parquet")
print(m.head(20))  # top messengers on the issue
```

Cross-reference these names against lobbyist meetings (via covered_position or LDA registrant
client lists) to find members whose offices are heavily lobbied on the issue but who *don't*
talk about it publicly.

## Caveats — must flag in stories

- Keyword search is a coarse proxy. "AI" sees both Microsoft AI and Allen Iverson; we
  default to `artificial intelligence` to mitigate. The user is responsible for choosing
  unambiguous keywords.
- A correlation does not mean causation. Both axes rise on hype cycles (ChatGPT moment, healthcare
  reform debate, banking crisis) and dropping that confound requires further analysis.
- Press release data has scraper gaps; check the monthly count series first (`press-corpus-build`
  Step 3) and exclude broken months before drawing trend lines.
- The lobbying counts include duplicate engagements (one client may file with both chambers).
  For a more rigorous denominator, join via `senateID`/`houseID` and count once per engagement.
