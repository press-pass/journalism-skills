# Chart evaluation rubric for Florence-v1

External, well-regarded rubrics applied to every chart we publish. Aim is to
avoid self-eval drift. Each chart should pass the **Trustworthy / Accessible /
Elegant** gate (Kirk) before drilling into the more granular checks.

## 1. Andy Kirk — Trustworthy / Accessible / Elegant (gate)
- **Trustworthy:** transparent about source + method; accurate; reproducible
- **Accessible:** effort proportional to insight; data-ink ratio respected
- **Elegant:** seamless design; nothing visually jarring

Source: https://us.sagepub.com/sites/default/files/upm-binaries/75674_Kirk_Data_Visualisation.pdf

## 2. Stephen Few — Effectiveness Profile (1–5 each, 7 dimensions)
- Usefulness, Completeness, Perceptibility, Truthfulness, Intuitiveness, Aesthetics, Engagement

Source: https://www.perceptualedge.com/articles/visual_business_intelligence/data_visualization_effectiveness_profile.pdf

## 3. Stephanie Evergreen — Data Viz Checklist (23 items, 0/1/2)
Sections: Text, Arrangement, Color, Lines, Overall. Target ≥ 90% of points.

Source: https://stephanieevergreen.com/updated-data-visualization-checklist/

## 4. Penn State Award (contest-style, 30 pts total)
- Effective Communication (10)
- Creativity & Innovation (10)
- Design & Aesthetics (10)

Source: https://libraries.psu.edu/about/departments/research-informatics-and-publishing/data-learning-center/data-visualization-1

## 5. Munzner — Four-Level Nested Model (academic, validation)
Domain → data/task abstraction → visual encoding → algorithm. Used to defend
"why this chart type?" decisions.

Source: https://www.cs.ubc.ca/~tmm/papers.html

## LLM-based runnable evaluators

- **Microsoft VisEval** — Validity / Legality / Readability. `pip install vis-evaluator`. https://github.com/microsoft/VisEval
- **Microsoft LIDA SEVQ** — 6 sub-scores via vision LLM. https://github.com/microsoft/lida

## Anti-patterns (auto-reject)
- 3D pies, gradient fills, drop shadows, decorative icons (Tufte chartjunk)
- Truncated or dual y-axes that distort change
- Rainbow color for ordinal data, categorical color for sequential data
- No clear one-sentence takeaway in the title (Pudding rule)
- No source line / provenance
- Encoding mismatch (length when position works, color when order matters)

## Pre-publish workflow for each chart
1. Self-score with Evergreen checklist (≥ 90% required)
2. Run our `chart-quality-review` skill (see skills/) for an automated second opinion
3. Final pass against Penn State 3-category rubric
4. Confirm Kirk TAE gate — Trustworthy is non-negotiable for journalism
