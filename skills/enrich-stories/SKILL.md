---
description: Enrich all story leads by running discovery skills against each story in parallel.
---

First, call the `get_story_leads` MCP tool to get all story leads.

For each story lead, run the following skills as parallel background subagents:

1. `/journalism-skills:trusted-human-source-discovery <lead-id>`
2. `/journalism-skills:identify-new-questions-from-article <lead-id>`

Then, call the `get_story_leads_without_photos` MCP tool to get leads missing photo evidence.

For each of those leads, run as a parallel background subagent:

3. `/journalism-skills:find-photo-evidence <lead-id>`

Wait for all subagents to complete. Then summarize which stories were enriched and any that failed.
