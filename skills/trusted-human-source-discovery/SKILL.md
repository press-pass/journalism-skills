---
description: Find human sources that can comment on a story.
---

The best news stories include commentary from human sources. You will be given the full text of a story or a file path to the full text of a story. If a file path is provided, read it first. If no story is provided, ask the user for one.

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

Store your results as a JSON array with the 5 sources in `skill-output/trusted-human-source-discovery/<YYYY-MM-DD_HH-MM-SS>/` within the journalism-skills plugin directory. Each entry should have the following fields:

- `name`: string
- `title`: string
- `organization`: string
- `relevance`: string (why this person is a good source for this story)
- `contact`: object with fields `email`, `phone`, `twitter`, `linkedin`, and any other available handles

Story to process: $ARGUMENTS
