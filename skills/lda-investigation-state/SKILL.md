---
name: lda-investigation-state
description: Maintain a persistent, on-disk investigation state — open leads, closed leads, cold threads, significant entities — so agents working over multiple sessions don't lose track. Append-only by default; every state change is timestamped. Use at the start of every investigation session to read open leads, and after each finding to log evidence and significant entities.
license: MIT
compatibility: Requires Python 3.11+ stdlib only.
metadata:
  author: PressPass
  version: "1.0"
---

When investigating a corpus this large, you cannot rely on conversation context to remember which leads have been checked, which entities matter, or which threads went cold. This skill solves that with a small, deterministic CLI that reads/writes `research/investigation_state.json`.

Use this skill at the start of every session before any other lda-* skill: `python3 skills/lda-investigation-state/scripts/lead.py list`.

## Commands

```bash
python3 skills/lda-investigation-state/scripts/lead.py list           # open + recent
python3 skills/lda-investigation-state/scripts/lead.py list --all

python3 skills/lda-investigation-state/scripts/lead.py add \
  --title "STATE OF LOC NATION self-filed $20M/Q outlier" \
  --evidence "filing_uuid=842e03af-220d-407b-823e-cee25fcd50a2" \
  --tags data-quality,outlier

python3 skills/lda-investigation-state/scripts/lead.py log <id_prefix> \
  --note "Confirmed 15 amended filings 2024-2026; single individual"

python3 skills/lda-investigation-state/scripts/lead.py close <id_prefix> \
  --resolution "Filed FOIA with LDA office; awaiting response"

python3 skills/lda-investigation-state/scripts/lead.py cold <id_prefix> \
  --reason "Subject declined comment, no other angle"

# Significant entities (people, organizations, bills)
python3 skills/lda-investigation-state/scripts/lead.py entity-add \
  --kind person --name "Christina Clement" \
  --note "Self-filed registrant, claims 'Head of State Black USA'"

# Render the entire investigation as a briefing
python3 skills/lda-investigation-state/scripts/lead.py export > research/state.md
```

## Why this matters for the GAIN evaluation

The Investigation Organization dimension of the rubric specifically asks for skills that "track checked items, open leads, significant entities, and cold threads, preventing repetitive agent briefings across sessions." This skill is that mechanism.

The state file is plain JSON, hand-editable, and source-controlled (the .json is gitignored to keep the operational state out of public commits, but the export command produces a markdown briefing you can commit when a finding is ready to share).
