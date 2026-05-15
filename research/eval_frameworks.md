# Evaluation Frameworks for the GAIN Challenge

## Primary Eval: GAIN Agentic Investigation Challenge

Source: https://www.gain-agent-challenge.northwestern.edu/details/

Two gates:
1. **Findings Validation** — claims accurate, traceable to specific records, genuine public interest (undisclosed relationships, timing anomalies, spending patterns). Fail this → no further ranking.
2. **Skill Usability** — 4 weighted dimensions, 0–3 each:
   - **Investigation Organization** — track checked items, open leads, significant entities, cold threads. Prevent repetitive briefings.
   - **Corpus Efficiency** — offload extraction/filter/index/aggregation to deterministic tools and cheap models. Reserve agent for reasoning.
   - **Human Verifiability** — anchor every claim to a specific source; present evidence for rapid review; auditable trace.
   - **Extended Agent Capabilities** — novel, investigation-specific utilities (entity resolvers, cross-reference, document-network traversal, domain parsers).

**Reproducibility cap:** Any skill that can't be re-executed cannot exceed 1/3 on any dimension.

Deliverables: skills validating against agentskills.io spec, findings report, full interaction traces, README mapping skills→findings→sources→COI.

## Secondary: chart-quality evals (for self-critique of viz output)

### Cairo's 5 qualities (The Truthful Art)
- Truthful — honest, accurate, no distortion
- Functional — appropriate chart form for the data
- Beautiful — visually engaging
- Insightful — reveals something non-obvious
- Enlightening — drives understanding/action

### Tufte's principles
- Lie Factor ≈ 1.0 (visual magnitude matches data magnitude)
- High data-ink ratio (remove chartjunk)
- Graphical integrity (no misleading scales, baselines, 3D effects)

### Penn State rubric (30 pts)
- Effective Communication (10)
- Creativity & Innovation (10)
- Design & Aesthetics (10)

## Application

Every chart we publish must:
1. Cite its underlying filing/release IDs (Human Verifiability)
2. Be re-generatable from a deterministic script (Reproducibility)
3. Be backed by an investigation skill that anyone can rerun
4. Make a claim that survives Findings Validation (not just descriptive aggregation; must point at something newsworthy)
