---
description: Query AI Access sources with many scrape items and create a PR adding dedicated scrapers for them in perform_scrape_for_source.
---

Call the `get_ai_access_sources` MCP tool to get all AI Access sources with more than 10 scrape items.

For each source returned, read its `aiAccessInstructions` and `sourceClientKey` to understand what data it accesses and how. Then:

1. Read `backend/api/services/source/source_service.py` to see the current `perform_scrape_for_source` function and its existing patterns (REDDIT, TWITTER, NYC_OPEN_DATA, AI_ACCESS).
2. For each source, determine if you can replace the generic AI Access scraping with a dedicated client that fetches the data directly (e.g., via an API, RSS feed, or structured web request). Skip sources whose instructions describe access patterns that cannot be replicated without Claude (e.g., "search the web for..." or "navigate through a complex UI").
3. For each source you can write a dedicated scraper for:
   a. Create a new client module in `backend/api/services/source/` that fetches the data.
   b. Add an `elif` branch in `perform_scrape_for_source` that checks `source.id == <source_id>` and calls your new client, creating ScrapeItem records from the response.
   c. Place the new branch **before** the generic `elif source.source_access_type == SourceAccessType.AI_ACCESS` branch so it takes priority.

4. Create a git branch, commit the changes, and open a PR. In the PR description, list each source ID and what dedicated scraper was added for it.

If no sources can be converted to dedicated scrapers, report which sources were found and why they could not be converted.
