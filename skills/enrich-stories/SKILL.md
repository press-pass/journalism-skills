---
description: Enrich all story leads by running discovery skills against each story in parallel.
---

Call `mcp__presspass__get_story_leads` to retrieve all story leads from the database.

For each story lead, run the following skills as parallel background subagents, passing the lead ID and title as arguments (formatted as `<leadId> <title>`):

1. `/journalism-skills:trusted-human-source-discovery <leadId> <title>`
2. `/journalism-skills:find-photo-evidence <title>`
3. `/journalism-skills:identify-new-questions-from-article <leadId> <title>`

After all file-based enrichment completes, run `/journalism-skills:answer-questions` to research and answer all pending pipeline questions.

Wait for all subagents to complete. Then summarize which stories were enriched and any that failed.
