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

### General-purpose

- **answer-questions** — Research and answer pipeline questions using web sources, and identify human sources for questions requiring interviews.
- **enrich-stories** — Enrich all story leads by running discovery skills against each story in parallel.
- **find-photo-evidence** — Find photos with permissive licensing related to a given story.
- **geographic-source-discovery** — Discover trusted sources by mapping the civic and community landscape of the tenant's zip codes. No arguments needed.
- **generate-story-leads** — Find story leads by analyzing available sources for timely, outlier-driven local news.
- **identify-new-questions-from-article** — Read a story pitch and identify questions it does not yet address.
- **new-skill** — Create a new skill by asking the user questions and generating a SKILL.md template.
- **trusted-human-source-discovery** — Find human sources that can comment on a story.
- **trusted-source-discovery** — Scrapes RSS feeds supplied as an argument to discover sources for news articles.

### Lobbying-and-press investigation (GAIN 2026 challenge)

These skills run against the GAIN dataset (US House+Senate Lobbying Disclosure Act filings 2022-2026 Q1 + Congressional press releases). They share a local DuckDB built by `lda-setup`. See `research/FINDINGS.md` for the four findings the skills surfaced and `CHECKPOINTS.md` for the resume-from-cold-start guide.

- **lda-setup** — Bootstrap script that loads ~141K press releases, ~418K Senate filings, and ~410K House LDA filings into a local DuckDB. Idempotent; ~2 min to rebuild.
- **lda-revolving-door** — Parse the LDA `covered_position` text against the unitedstates.io legislator roster. Materializes a `revolving_door` table of (lobbyist → former Member boss) pairs.
- **lda-say-vs-pay** — Extract Congressional bill numbers from both lobbying activity descriptions and press release bodies; surface bills that are heavily lobbied but rarely discussed publicly.
- **lda-foreign-influence** — Country × policy-issue map of foreign-tied lobbying clients.
- **lda-chart** — Render publication-quality charts (PNG + SVG + provenance markdown) from the materialized tables.
- **lda-investigation-state** — Persistent on-disk leads/entities/cold-threads tracker that survives context compaction.

## License

MIT — see [LICENSE](LICENSE).
