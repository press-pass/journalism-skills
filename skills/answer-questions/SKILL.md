---
description: Research and answer all unanswered questions for story leads in the pipeline. Answers questions from public sources and identifies human sources for questions requiring interviews.
---

Use the MCP tools to get all story leads: call `get_story_leads`.

For each story lead that has questions with status "Pending" or "Approved":

### 1. Classify each question

Read the question and decide:

- **Public info**: The answer can be found from government data, news articles, public records, or other web sources.
- **Human source needed**: The question requires a person's perspective, insider knowledge, or an interview to answer properly.

### 2. Answer public-info questions

For each question that can be answered with public information:

1. Research the answer using web search, browsing official sources, and cross-referencing data.
2. Write a concise, factual answer (2-4 sentences) with specific data points when available.
3. Save the answer using the `answer_question` MCP tool with:
   - `questionId`: the question's ID
   - `answerText`: the researched answer
   - `answerSourcesJson`: array of `{"url": "...", "title": "..."}` for each source used

Prioritize authoritative sources: government databases, official reports, established news outlets.

### 3. Identify human sources for interview questions

For each question that requires a human source:

1. Identify the best person to answer this question. Consider:
   - People directly involved in or affected by the story
   - Subject matter experts with relevant credentials
   - Public officials or spokespeople with relevant authority
   - Advocates or community leaders connected to the topic
2. Research their contact information (email, phone, social media).
3. Save the human source using the `add_identified_source` MCP tool with:
   - `leadId`: the story lead's ID
   - `questionId`: the question's ID (so the editor knows which question this source addresses)
   - `name`, `title`, `organization`, `email`, `phone`, `socialHandlesJson`, `relevance`
4. Also save a partial answer using `answer_question` explaining what is known so far and that a human source has been identified for the full answer.

### 4. Summarize

After processing all questions, summarize:
- How many questions were answered from public sources
- How many human sources were identified
- Any questions that could not be addressed

Story lead to process (omit to process all): $ARGUMENTS
