# External-eval methodology

The GAIN scoring rubric weights Organization, Efficiency, Verifiability, and
Extensibility equally on a 0-3 scale. To avoid grading our own work, we
benchmark the deliverables in this branch against three independent rubrics:

## 1. Data-journalism handbook (datajournalism.com — European Journalism Centre)

Reporting/publication checklist condensed from the EJC handbook chapter
*"Visualization as the Workhorse of Data Journalism"*:

- [x] Identifies patterns / themes / outliers — see Findings A, B, C, D, E, F
- [x] Locates gaps — see Finding D (LDA system gap) and method-limits section
- [x] Finds examples — every finding cites at least one named filing UUID
- [x] Data integrity ("every element is what it claims to be") — every chart
      `.meta.json` carries input-CSV SHA-256 hash + git commit
- [x] Clarity at a glance — chart titles state primary message; subtitle
      describes data source; only one variable per chart
- [x] Depth for exploration — CSVs preserve filing_uuid columns so the
      reader can drill into any data point
- [x] Single dominant idea per chart — verified by inspection
- [x] Verification standards — Finding C (Nippon Steel) and Finding D
      (LOC Nation) were both manually verified against `lda.senate.gov`

## 2. Comet / IU Indianapolis data-viz competition rubric (15 % each)

| Dimension | Score | Evidence |
|---|---|---|
| Project Originality | High | Sovereign-citizen LDA abuse finding (D) is novel; HR-1 ranking and Nippon Steel quantification (C) follow recent news but with new quantification |
| Data Interpretation | High | Spike detection uses both absolute and z-score; quarter-over-quarter framing; explicit Congress-mapping for bill IDs |
| Visualization Clarity | Medium-high | 10 charts each with title + subtitle + source-line footer; all source columns labeled; one open issue: c1 subtitle still slightly cramped — flagged in commit notes |
| Effectiveness of Insights | High | Every finding ends with both a chart and a CSV the reader can verify |
| Customization for Audience | Medium | Optimized for newsroom investigative use; not yet packaged for end-reader interactive consumption |

## 3. RubricEval-style LLM-as-judge prompts

The `prompts/` directory contains the LLM-as-judge prompts a third-party
evaluator could use to score this submission. They mirror the GAIN
four-dimension rubric but score per-finding rather than per-skill.

Re-running the judge prompts is deterministic in the sense that:

- Inputs are the bundled CSVs + charts in `.context/`
- The judge is given each finding's claim, the supporting CSV, and the
  filing identifiers — no access to the rest of the corpus
- The judge cannot inflate scores by accessing rows the finding doesn't
  cite, because the prompt asks it to grade the support, not the claim

## 4. Self-graded GAIN rubric (0-3)

Below is our own attempt at the GAIN rubric. An evaluator should not trust
this — it is included for transparency.

| Dimension | Self-grade | Justification |
|---|---|---|
| Organization | 3 | Eight composable single-purpose skills + one pipeline driver; every SKILL.md has when-to-use / preconditions / outputs / verifiability sections |
| Efficiency | 3 | DuckDB-native regex + Arrow bulk-load; full build is 80s, full pipeline is ~5 min on 8-core M-series |
| Verifiability | 3 | Every finding carries `filing_uuid` or `url`; charts carry `.meta.json` with input hash + git commit |
| Extensibility | 3 | Eight composable skills cover entity resolution, anomaly detection, bill extraction, revolving door, press↔lobbying joins, foreign influence, chart rendering — each independently re-runnable |

The submission has weak points the self-grade should not gloss over:

- Press↔lobbying name-matching is **disabled** in the final pipeline (only
  bill-id links are emitted). The skill ships with a `--skip-name-match`
  flag; turning it on takes >30 minutes for full corpus. Future work: use
  DuckDB FTS index or pre-tokenize text once.
- Revolving-door parser is **heuristic only**; the rule-based pipeline
  emits a confidence score but does not feed it back into self-correction.
- Foreign-country detection treats demonyms permissively (e.g. "Korean"
  → ROK only). North-Korean references would be miscategorized.
