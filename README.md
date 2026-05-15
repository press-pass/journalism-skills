# journalism-skills

Agentic skills for journalism.

## Install as a Claude Code plugin

```bash
claude plugin install journalism-skills@jskills
```

## Usage

Skills are namespaced under `journalism-skills`:

```
/journalism-skills:new-skill
```

## Skill output

All skill output is written to `skills/<skill-name>/skill-output/<skill-name>/<YYYY-MM-DD_HH-MM-SS>/` within the journalism-skills directory. This directory is gitignored.

## Development

Skills are cached when installed. Editing skill files won't take effect until you reinstall the plugin. From within a Claude session:

```
/plugin install journalism-skills@jskills
```

Note: `/reload-plugins` only reloads already-cached plugins — it won't pick up source file changes. You need to reinstall.

## Available skills

- **answer-questions** — Research and answer pipeline questions using web sources, and identify human sources for questions requiring interviews.
- **chart-eval** — Self-evaluate rendered charts against a fused Tufte + ChartMimic + FT Visual Vocabulary rubric. Deterministic (no LLM required).
- **enrich-stories** — Enrich all story leads by running discovery skills against each story in parallel.
- **find-photo-evidence** — Find photos with permissive licensing related to a given story.
- **geographic-source-discovery** — Discover trusted sources by mapping the civic and community landscape of the tenant's zip codes. No arguments needed.
- **generate-story-leads** — Find story leads by analyzing available sources for timely, outlier-driven local news.
- **identify-new-questions-from-article** — Read a story pitch and identify questions it does not yet address.
- **lobbying-corpus-build** — ETL Senate LDA JSON + House LDA XML into a unified parquet corpus. Foundation for cross-corpus lobbying analyses.
- **lobbying-charts** — Render 9 publication-quality charts (PNG + verifiable JSON sidecar) on lobbying + press release corpus.
- **new-skill** — Create a new skill by asking the user questions and generating a SKILL.md template.
- **press-corpus-build** — ETL the Congress press release JSONL corpus into a single parquet table keyed by bioguide_id.
- **revolving-door-extract** — Parse lobbyist `covered_position` free text into structured (lobbyist → member of Congress) edges with audit-ready evidence.
- **say-vs-pay-correlate** — Compute a quarterly Pearson correlation between press release mentions and lobbying activity descriptions for any keyword.
- **trusted-human-source-discovery** — Find human sources that can comment on a story.
- **trusted-source-discovery** — Scrapes RSS feeds supplied as an argument to discover sources for news articles.

## License

MIT — see [LICENSE](LICENSE).
