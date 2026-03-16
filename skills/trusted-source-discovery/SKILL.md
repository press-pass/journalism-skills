---
description: Scrapes RSS feeds supplied as an argument to discover sources for news articles.
allowed-tools: WebFetch
---

You will be given a comma-delimited list of RSS feed URLs. For each RSS feed:

1. Fetch the feed and extract all links contained within it that do not share a domain with the feed itself.
2. Collate these external links into groupings by their purpose (what news article category they are associated with).
3. Identify the best sources — those provided by the government or other trusted bodies that appear across many articles.
4. For each source, attempt to find an official API that contains the same information as the referenced link. Do not use 3rd-party copies of the data.

Output your results as a JSON array limited to the 20 best sources. Each entry should have the following fields:

- `source_type`: string (examples: `government_website`, `business_website`, `wordpress_post`, `nyc_open_data`, etc.)
- `source_access_type`: string (examples: `rss_feed`, `api_request`, `praw`, etc.)
- `source_client_key`: object containing an `api_key` field if needed, along with a `how_to_access` field with information about how to access the source programmatically.

Store your results in `skill-output/trusted-source-discovery/<YYYY-MM-DD_HH-MM-SS>/` within the journalism-skills plugin directory.

RSS feeds to process: $ARGUMENTS
