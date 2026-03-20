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

## Available skills

- **enrich-stories** — Enrich all story leads by running discovery skills against each story in parallel.
- **find-photo-evidence** — Find photos with permissive licensing related to a given story.
- **generate-story-leads** — Find story leads by analyzing available sources for timely, outlier-driven local news.
- **identify-new-questions-from-article** — Read a story pitch and identify questions it does not yet address.
- **new-skill** — Create a new skill by asking the user questions and generating a SKILL.md template.
- **trusted-human-source-discovery** — Find human sources that can comment on a story.
- **trusted-source-discovery** — Scrapes RSS feeds supplied as an argument to discover sources for news articles.
