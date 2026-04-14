---
description: Scrapes RSS feeds supplied as an argument to discover sources for news articles.
---

You will be given a comma-delimited list of RSS feed URLs. For each RSS feed:

1. Fetch the feed and extract all links contained within it that do not share a domain with the feed itself.
2. Identify the best sources. Good sources appear in many articles or are the _only_ source in an article. Try to find
   sources that could spawn an article all on their own. 
3. If the source is a social media site (i.e. Reddit, Instagram etc.) follow the link to the social media site
   to find more reliable sources on that page.
3. For each source, attempt to find an official API that contains the same information as the referenced link. Do not 
   use 3rd-party copies of the data. 

For each of the 20 best sources, call the `add_source_from_source_discovery` MCP tool with:

- `name`: descriptive name of the source
- `aiAccessInstructions`: how to access the source programmatically (API endpoint, scraping instructions, etc.)
- `whenItsImportant`: when this source is newsworthy
- `sourceClientKey`: object with `api_key` if needed and any other access metadata
- `isReferenceSource`: is this source just a huge database that we can't get story leads from? Examples include 311 
  complaints, tax records, etc.

After creating all sources, summarize what was created including the returned source IDs.

RSS feeds to process: $ARGUMENTS
