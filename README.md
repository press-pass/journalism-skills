# journalism-skills

Agentic skills for journalism.

## Install as a Claude Code plugin

```bash
claude plugin install journalism-skills@spmartin823/journalism-skills
```

Or test locally during development:

```bash
claude --plugin-dir ./journalism-skills
```

## Usage

Skills are namespaced under `journalism-skills`:

```
/journalism-skills:new-skill
```

## Skill output

All skill output is written to `skill-output/<skill-name>/<YYYY-MM-DD_HH-MM-SS>/` within the journalism-skills directory. This directory is gitignored.

## Available skills

- **new-skill** — Scaffolds a new skill by walking you through a series of questions.
