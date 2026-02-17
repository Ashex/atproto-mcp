"""AT Protocol MCP Knowledge Base Server.

Provides semantic search over AT Protocol documentation, lexicons,
Bluesky API docs, and cookbook examples via the Model Context Protocol.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from mcp.server.fastmcp import FastMCP

from atproto_mcp import state
from atproto_mcp.config import Config
from atproto_mcp.fetcher import fetch_all
from atproto_mcp.indexer import KnowledgeBase
from atproto_mcp.parser import parse_all
from atproto_mcp.prompts import register_prompts
from atproto_mcp.resources import register_resources
from atproto_mcp.tools import register_tools

# Configure logging to stderr (stdout is reserved for MCP JSON-RPC)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Server lifespan — fetch repos, build/load index on startup."""
    config = Config.from_env()
    state.config = config

    logger.info("Starting AT Protocol MCP server")
    logger.info("Cache directory: %s", config.cache_dir)
    logger.info("Embedding model: %s", config.embedding_model)

    logger.info("Fetching source repositories …")
    shas = fetch_all(config)
    for name, sha in shas.items():
        logger.info("  %s: %s", name, sha)

    kb = KnowledgeBase(config)
    loaded = kb.load()

    if not loaded:
        logger.info("No cached index found — building from scratch …")
        chunks = parse_all(config)
        kb.build(chunks)
    else:
        logger.info(
            "Loaded cached index: %d chunks, %d lexicons",
            kb.chunk_count,
            kb.lexicon_count,
        )

    # Publish to shared state so tools/resources can access it
    state.kb = kb

    logger.info("Knowledge base ready")
    yield {}

    logger.info("Shutting down AT Protocol MCP server")


mcp = FastMCP(
    "atproto-knowledge-base",
    instructions=(
        "AT Protocol and Bluesky knowledge base. "
        "Search documentation, browse lexicon schemas, find cookbook examples, "
        "and query the Bluesky developer API docs. "
        "Use search_atproto_docs for general queries across all sources. "
        "Use get_lexicon / list_lexicons / search_lexicons for schema lookups. "
        "Use get_cookbook_example / list_cookbook_examples for implementation examples. "
        "Use search_bsky_api for Bluesky-specific API documentation."
    ),
    lifespan=app_lifespan,
)

register_tools(mcp)
register_resources(mcp)
register_prompts(mcp)


def main() -> None:
    """Entry point — run the MCP server over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
