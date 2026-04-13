---
description: Find photos with permissive licensing related to a given story.
---

You will be given a story lead ID. First, call the `get_story_leads` MCP tool and find the lead matching the provided ID. Read its title and why it matters to understand the story.

Search the open internet and social media to find photos that are licensed in a way that allows use in this news story. Focus on:

1. Creative Commons licensed images (CC0, CC-BY, CC-BY-SA)
2. Public domain images
3. Government-produced images (which are typically public domain)
4. Wire service or stock photos with open licenses

Once you have found photos, call the `save_photo_evidence` MCP tool with:

- `leadId`: the story lead ID
- `photos`: array of photo objects, each with:
  - `url`: direct link to the image or its hosting page
  - `description`: what the photo depicts
  - `license`: the specific license (e.g., CC-BY-4.0, Public Domain, US Government Work)
  - `attribution`: the required attribution text if any
  - `source`: where the photo was found (e.g., Wikimedia Commons, Flickr, government website)
  - `relevance`: why this photo is relevant to the story

After saving, report how many photos were saved and how many had broken links.

Story lead ID: $ARGUMENTS
