---
description: Find human sources that can comment on a story.
---

You will be given a story lead ID. First, call the `get_story_leads` MCP tool and find the lead matching the provided ID. Read its title, why it matters, and its questions to understand the story.

Using the story, identify 5 people who would be strong human sources to comment on the story. For each person, find their contact information:

- Full name
- Title / role
- Organization
- Email address
- Phone number
- Social media handles (X/Twitter, LinkedIn, etc.)

Prioritize people who are:
1. Directly involved in or affected by the story
2. Subject matter experts with relevant credentials
3. Public officials or spokespeople with relevant authority
4. Advocates or community leaders connected to the topic
5. Academics or researchers who study the topic

For each source, call the `add_source_for_question` MCP tool with:

- `leadId`: the story lead ID
- `questionId`: the ID of the question this source is best suited to address
- `name`: the person's full name
- `relevance`: why this person is a good source for this story
- `title`: their title or role
- `organization`: their organization
- `email`: their email address
- `phone`: their phone number
- `socialHandles`: object with their social media handles (e.g. `{"twitter": "@handle", "linkedin": "url"}`)

After creating all sources, summarize who was found and which questions they were linked to.

Story lead ID: $ARGUMENTS
