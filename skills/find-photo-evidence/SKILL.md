---
description: Find photos with permissive licensing related to a given article.
---

You will be given a news article or a file path to one. If a file path is provided, read it first. If no article is provided, ask the user for one.

Search the open internet and social media to find photos that are licensed in a way that allows use in the provided news article. Focus on:

1. Creative Commons licensed images (CC0, CC-BY, CC-BY-SA)
2. Public domain images
3. Government-produced images (which are typically public domain)
4. Wire service or stock photos with open licenses

For each photo found, provide:

- `url`: direct link to the image or its hosting page
- `description`: what the photo depicts
- `license`: the specific license (e.g., CC-BY-4.0, Public Domain, US Government Work)
- `attribution`: the required attribution text if any
- `source`: where the photo was found (e.g., Wikimedia Commons, Flickr, government website)
- `relevance`: why this photo is relevant to the article

Store your results as a JSON array in `skill-output/find-photo-evidence/<YYYY-MM-DD_HH-MM-SS>/` within the journalism-skills plugin directory.

Article to process: $ARGUMENTS
