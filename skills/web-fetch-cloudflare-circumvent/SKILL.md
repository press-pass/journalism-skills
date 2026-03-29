---
description: Fetch web content that may be blocked by Cloudflare. Cascades through WebFetch, curl, and Playwright until one succeeds.
---

You will be given a URL and an optional prompt describing what to extract from the page.

Follow this cascade to fetch the content, stopping as soon as one method succeeds:

## Step 1: Try WebFetch

Use the WebFetch tool with the provided URL and prompt. If it succeeds, return the result.

If WebFetch returns a 403, 503, or any error suggesting the request was blocked, proceed to Step 2.

## Step 2: Try curl

Run `curl -s <URL>` via the Bash tool. Inspect the response:
- If you get valid HTML content, process it according to the prompt and return the result.
- If you get a 403, a Cloudflare challenge page (look for "Just a moment..." or "Checking your browser"), or an empty response, proceed to Step 3.

## Step 3: Try Playwright

Use the Playwright MCP tools to load the page in a real browser:
1. Call `browser_navigate` with the URL.
2. Call `browser_snapshot` to capture the page content.
3. Process the snapshot according to the prompt and return the result.

## Output

After successfully fetching the content, apply the user's prompt to the content and return the result. If all three methods fail, report which methods were tried and what errors occurred.

URL and prompt: $ARGUMENTS
