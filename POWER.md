---
name: "atproto"
displayName: "AT Protocol Docs & Lexicons"
description: "Search AT Protocol docs, lexicons, Bluesky API docs, and cookbook examples with atproto-mcp"
keywords: ["atproto", "bluesky", "lexicon", "mcp", "api docs", "cookbook", "federation", "firehose"]
---

# Onboarding

## Step 1: Verify runtime tools

Before using this power, ensure one of these is available:

- `uvx` (recommended): verify with `uvx --version`
- `python` + `pip`: verify with `python --version`

## Step 2: Configure environment (optional)

You can customize cache/index behavior with environment variables:

- `ATPROTO_MCP_CACHE_DIR`
- `ATPROTO_MCP_REFRESH_HOURS`
- `ATPROTO_MCP_EMBEDDING_MODEL`

## Best Practices

- Start broad with `search_atproto_docs`, then narrow with `get_lexicon` and `search_bsky_api`.
- Use `list_lexicons` to discover valid NSIDs before requesting a full schema.
- Use `list_cookbook_examples` before `get_cookbook_example` when you need language-specific starter code.
- Use `refresh_sources` when you suspect upstream docs changed.

## Suggested Workflows

### Explore a namespace

1. Run `list_lexicons` with a namespace prefix (for example `app.bsky.feed`).
2. Fetch target schemas with `get_lexicon`.
3. Cross-check implementation details with `search_atproto_docs`.

### Build a feature

1. Search concepts and endpoint behavior with `search_atproto_docs`.
2. Inspect canonical schemas with `get_lexicon`.
3. Find implementation references with cookbook tools.
