---
description: Read a story pitch and identify questions it does not yet address.
---

You will be given a story lead ID. First, call the `get_story_leads` MCP tool and find the lead matching the provided ID. Read its title, why it matters, sources, and existing questions to understand the story.

In a good article, who, what, where, why, and how are all answered. Oftentimes when writing an article, some of these questions will be left unanswered. Analyze the story lead and identify if any of these questions are unanswered.

For each unanswered question:

1. Identify which of the five W's (who, what, where, why, how) it falls under
2. State the specific question that remains unanswered
3. Call the `add_question` MCP tool with:
   - `leadId`: the story lead ID
   - `questionText`: the question text
   - `questionType`: which of the five W's it falls under
4. Research the answer using available tools
5. Call the `answer_question` MCP tool with:
   - `questionId`: the ID returned from the add_question call
   - `answerText`: the researched answer

After processing all questions, summarize what new questions were added and which were answered.

Story lead ID: $ARGUMENTS
