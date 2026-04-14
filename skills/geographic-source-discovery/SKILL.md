---
description: Discover trusted sources for news coverage by mapping the civic and community landscape of given zip codes. Takes a comma-separated list of zip codes.
---

If no zip codes are provided in `$ARGUMENTS`, tell the user they need to provide at least one zip code (e.g. `/journalism-skills:geographic-source-discovery 10001, 10002`) and stop.

You are a beat reporter building a source list for a new coverage area. Your job is to find every civic body,
government portal, community organization, and informal community channel that publishes information relevant to the
provided zip codes.

## Phase 1: Map the terrain

For each zip code, research the geographic and civic landscape:

1. **Identify the area**: What neighborhood(s), city, county, and state does this zip code cover?
2. **Map civic bodies**: What government entities have jurisdiction here? Search the web for:
   - City/town council or equivalent legislative body
   - Community boards or advisory councils
   - Local police precinct or sheriff's office
   - School district and school board
   - Zoning/planning board
   - Parks department (local)
   - Health department (local)
   - Housing authority
   - Any special districts (BIDs, land trusts, water districts, etc.)
3. **Map community organizations**: Search for:
   - Neighborhood associations and civic groups
   - Tenant unions and housing advocacy orgs
   - Mutual aid networks
   - Religious institutions that serve as community hubs
   - Local business associations and chambers of commerce
4. **Map informal community channels**: Search for:
   - Facebook groups for the neighborhood (search Facebook for "[neighborhood name] community", "[neighborhood name] residents", etc.)
   - Reddit communities (subreddits for the neighborhood, borough, or city)
   - Community newsletters or blogs

Write your findings to `skills/geographic-source-discovery/skill-output/geographic-source-discovery/<timestamp>/terrain-map.md`
in the journalism-skills directory before proceeding to Phase 2. This makes Phase 1 auditable.

## Phase 2: Find sources and access methods

For each entity discovered in Phase 1, find its digital presence and the best way to access its information
programmatically. For each one:

1. Find the entity's official website.
2. Look for structured data feeds in this priority order:
   - Public API (REST, GraphQL, SODA/Socrata, etc.)
   - RSS or Atom feed
   - iCal/ICS calendar feed (especially for meeting schedules)
   - Scrapable web page with regularly updated content
3. If none of the above exist, check for:
   - Email newsletter signup (note the signup URL)
   - Public Facebook page or group URL
   - Any other regularly updated public page
4. For Reddit communities, note the subreddit name — PRAW can access these.
5. For Facebook groups, note the group URL and whether it's public or private.

For each of the best sources, call the `add_source_from_source_discovery` MCP tool with:

- `name`: descriptive name of the source (e.g. "Brooklyn Community Board 6 Meeting Calendar")
- `aiAccessInstructions`: how to access the source programmatically — API endpoint, RSS URL, scraping instructions,
  or if manual-only, describe what a human would need to do to monitor it
- `whenItsImportant`: when this source produces newsworthy information (e.g. "when new zoning variances are filed",
  "when meeting agendas are posted before monthly meetings")
- `sourceClientKey`: object with `api_key` if needed and any other access metadata
- `isReferenceSource`: true if this is a large database useful for answering questions but unlikely to generate
  story leads on its own (e.g. tax records, Census data)

Do not create duplicate sources. If a source already exists in the system (check by searching for similar names in
existing story lead sources), skip it.

## What makes a good source

Prioritize sources that:
- Publish new information on a regular schedule (meeting minutes, permit filings, crime stats)
- Cover topics that directly affect residents (housing, safety, schools, transit, development)
- Are primary sources rather than aggregators (the community board itself, not a blog that summarizes their meetings)
- Have programmatic access, but don't skip valuable sources just because they require manual monitoring

## After creating all sources

Summarize what was created:
- How many sources were created, grouped by type (civic/government, community org, informal channel)
- Which zip codes have the best coverage and which have gaps
- Any notable sources that could only be saved with manual access instructions

Zip codes to search: $ARGUMENTS
