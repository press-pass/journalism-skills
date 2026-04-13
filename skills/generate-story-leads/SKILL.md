---
description: Find story leads by analyzing available sources for timely, outlier-driven local news. Takes a comma-separated list of zip codes to search.
---

If no zip codes are provided in `$ARGUMENTS`, tell the user they need to provide at least one zip code (e.g. `/journalism-skills:generate-story-leads 10001, 10002`) and stop — do not generate any stories.

You will be given a comma-separated list of zip codes. Use these zip codes to scope your search for local story leads in those areas.

Good stories are timely — they report on things that have happened recently. They also typically discuss outliers — a building that has received a ton of complaints, a cop that is paid extremely high, or a business that is opening in a space that hasn't been occupied in a long time for example.

Take a look at the available sources and try to find story leads relevant to the provided zip codes. For each lead, call the `create_story_lead` MCP tool with:

- `title`: the headline of the story
- `zipCode`: the zip code this story is relevant to
- `sourceIds`: array of source ids which were used in the story lead
- `questionsJson`: array of questions the story asks
- `whyItMatters`: why this story matters to locals
- `importanceScore`: a subjective score of how important you think the story is for locals, out of 9

Generate 10-20 leads per invocation. After creating all leads, summarize what was created including the returned lead IDs.

Zip codes to search: $ARGUMENTS
