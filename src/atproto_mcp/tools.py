"""MCP tool definitions for the AT Protocol knowledge base server."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from atproto_mcp.config import (
    SOURCE_ATPROTO_WEBSITE,
    SOURCE_BSKY_DOCS,
    SOURCE_COOKBOOK,
    SOURCE_LEXICONS,
)
from atproto_mcp.state import get_kb

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

_VALID_SOURCES = frozenset({
    SOURCE_ATPROTO_WEBSITE,
    SOURCE_BSKY_DOCS,
    SOURCE_COOKBOOK,
    SOURCE_LEXICONS,
})


def _format_search_results(results: list[dict[str, object]]) -> str:
    """Format search results into a readable text response."""
    if not results:
        return "No results found."

    lines: list[str] = []
    for i, result in enumerate(results, 1):
        title = result.get("title", "Untitled")
        source = result.get("source", "")
        url = result.get("url", "")
        nsid = result.get("nsid", "")
        score = result.get("score", 0.0)
        text = str(result.get("text", ""))

        header = f"## {i}. {title}"
        if nsid:
            header += f" ({nsid})"
        lines.append(header)
        lines.append(f"Source: {source} | Score: {score:.3f}")
        if url:
            lines.append(f"URL: {url}")

        snippet = text[:800] + "…" if len(text) > 800 else text
        lines.append(f"\n{snippet}\n")

    return "\n".join(lines)


def register_tools(mcp: FastMCP) -> None:
    """Register all MCP tools on the server."""

    @mcp.tool()
    def search_atproto_docs(
        query: str,
        source: str = "",
        limit: int = 10,
    ) -> str:
        """Search across all AT Protocol documentation, lexicons, Bluesky API docs, and cookbook examples.

        Use this tool to find information about AT Protocol concepts, endpoints,
        data structures, authentication, federation, and implementation patterns.

        Args:
            query: Natural language search query (e.g. "how to create a post",
                   "OAuth authentication flow", "what is a DID").
            source: Optional filter — restrict to a specific source:
                    "atproto-website" (protocol specs/guides from atproto.com),
                    "bsky-docs" (Bluesky API docs from docs.bsky.app),
                    "lexicons" (AT Protocol lexicon schemas),
                    "cookbook" (example projects and code).
                    Leave empty to search all sources.
            limit: Maximum number of results (1-20, default 10).
        """
        kb = get_kb()
        limit = max(1, min(20, limit))
        source_filter = source if source in _VALID_SOURCES else None
        results = kb.search(query, source=source_filter, limit=limit)
        return _format_search_results(results)

    @mcp.tool()
    def get_lexicon(nsid: str) -> str:
        """Retrieve a specific AT Protocol lexicon by its NSID.

        Returns the full lexicon schema including type definitions, properties,
        descriptions, and cross-references. Use this when you need the complete
        definition of a specific endpoint or record type.

        Args:
            nsid: The Namespaced Identifier (e.g. "app.bsky.feed.post",
                  "com.atproto.repo.createRecord", "chat.bsky.convo.sendMessage").
        """
        kb = get_kb()
        chunk = kb.get_lexicon(nsid)
        if not chunk:
            all_lexicons = kb.list_lexicons()
            suggestions = [
                lex["nsid"]
                for lex in all_lexicons
                if nsid.lower() in lex["nsid"].lower()
            ][:5]
            msg = f"Lexicon '{nsid}' not found."
            if suggestions:
                msg += "\n\nDid you mean one of these?\n" + "\n".join(
                    f"  - {s}" for s in suggestions
                )
            return msg

        parts = [chunk.text]
        raw_json = chunk.metadata.get("raw_json")
        if raw_json:
            try:
                parsed = json.loads(raw_json)
                parts.append(
                    f"\n\n## Raw JSON Schema\n```json\n{json.dumps(parsed, indent=2)}\n```"
                )
            except json.JSONDecodeError:
                pass

        return "\n".join(parts)

    @mcp.tool()
    def list_lexicons(namespace: str = "") -> str:
        """List all AT Protocol lexicons, optionally filtered by namespace prefix.

        Use this to discover available lexicons and their NSIDs before
        fetching specific ones with get_lexicon.

        Args:
            namespace: Optional namespace prefix to filter by
                       (e.g. "app.bsky.feed", "com.atproto.repo", "chat.bsky",
                       "tools.ozone"). Leave empty to list all.
        """
        kb = get_kb()
        lexicons = kb.list_lexicons(namespace=namespace if namespace else None)

        if not lexicons:
            if namespace:
                return f"No lexicons found with namespace prefix '{namespace}'."
            return "No lexicons indexed."

        lines = [f"Found {len(lexicons)} lexicon(s):\n"]
        for lex in lexicons:
            lines.append(f"  - {lex['nsid']}")

        return "\n".join(lines)

    @mcp.tool()
    def search_lexicons(query: str, limit: int = 10) -> str:
        """Search within AT Protocol lexicons using semantic search.

        Searches lexicon descriptions, property names, types, and definitions.
        More targeted than search_atproto_docs when you specifically need
        lexicon/schema information.

        Args:
            query: Search query (e.g. "post creation", "follow relationship",
                   "blob upload", "moderation labels").
            limit: Maximum results (1-20, default 10).
        """
        kb = get_kb()
        limit = max(1, min(20, limit))
        results = kb.search_lexicons(query, limit=limit)
        return _format_search_results(results)

    @mcp.tool()
    def get_cookbook_example(name: str) -> str:
        """Retrieve a specific AT Protocol cookbook example by project name.

        Returns the project README, file listing, and key source code files.
        Use this when you need implementation examples or starter code.

        Args:
            name: Project directory name (e.g. "python-bsky-post", "ts-bot",
                  "go-repo-export", "python-oauth-web-app").
                  Use list_cookbook_examples to discover available projects.
        """
        kb = get_kb()
        chunk = kb.get_cookbook_example(name)
        if not chunk:
            examples = kb.list_cookbook_examples()
            names = [ex["name"] for ex in examples]
            suggestions = [n for n in names if name.lower() in n.lower()][:5]
            msg = f"Cookbook example '{name}' not found."
            if suggestions:
                msg += "\n\nDid you mean one of these?\n" + "\n".join(
                    f"  - {s}" for s in suggestions
                )
            elif names:
                msg += "\n\nAvailable examples:\n" + "\n".join(
                    f"  - {n}" for n in names
                )
            return msg

        return chunk.text

    @mcp.tool()
    def list_cookbook_examples(language: str = "") -> str:
        """List all AT Protocol cookbook examples (starter projects and scripts).

        Use this to discover available example projects before fetching
        specific ones with get_cookbook_example.

        Args:
            language: Optional filter by language ("python", "go", "typescript",
                      "javascript"). Leave empty to list all.
        """
        kb = get_kb()
        examples = kb.list_cookbook_examples(
            language=language if language else None
        )

        if not examples:
            if language:
                return f"No cookbook examples found for language '{language}'."
            return "No cookbook examples indexed."

        lines = [f"Found {len(examples)} cookbook example(s):\n"]
        for ex in examples:
            lang_tag = f" [{ex['language']}]" if ex.get("language") else ""
            lines.append(f"  - {ex['name']}{lang_tag}")
            if ex.get("url"):
                lines.append(f"    {ex['url']}")

        return "\n".join(lines)

    @mcp.tool()
    def search_bsky_api(query: str, limit: int = 10) -> str:
        """Search Bluesky developer API documentation (docs.bsky.app).

        Searches guides, tutorials, and advanced topics specific to the
        Bluesky API. Use this for questions about Bluesky-specific features
        like the firehose, federation, moderation, or API usage patterns.

        Args:
            query: Search query (e.g. "firehose subscription", "custom feeds",
                   "authentication", "rate limits").
            limit: Maximum results (1-20, default 10).
        """
        kb = get_kb()
        limit = max(1, min(20, limit))
        results = kb.search_bsky_api(query, limit=limit)
        return _format_search_results(results)

    @mcp.tool()
    def refresh_sources() -> str:
        """Force re-fetch all AT Protocol source repositories and rebuild the search index.

        Use this when you suspect the documentation is outdated or when
        upstream repos have been updated. This operation may take several
        minutes as it clones repositories and rebuilds the embeddings index.
        """
        from atproto_mcp.fetcher import fetch_all
        from atproto_mcp.parser import parse_all
        from atproto_mcp.state import get_config

        config = get_config()
        kb = get_kb()

        shas = fetch_all(config, force=True)
        sha_summary = "\n".join(f"  {name}: {sha}" for name, sha in shas.items())

        chunks = parse_all(config)
        kb.build(chunks)

        return (
            f"Sources refreshed and index rebuilt.\n\n"
            f"Repository SHAs:\n{sha_summary}\n\n"
            f"Total chunks indexed: {kb.chunk_count}\n"
            f"Lexicons indexed: {kb.lexicon_count}"
        )
