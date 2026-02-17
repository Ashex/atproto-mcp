"""MCP resource definitions for browsable AT Protocol content."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from atproto_mcp.state import get_kb

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_resources(mcp: FastMCP) -> None:
    """Register MCP resources for browsable AT Protocol content."""

    @mcp.resource("atproto://lexicons")
    def list_all_lexicons() -> str:
        """List all available AT Protocol lexicons."""
        kb = get_kb()
        lexicons = kb.list_lexicons()
        return json.dumps(lexicons, indent=2)

    @mcp.resource("atproto://lexicon/{nsid}")
    def get_lexicon_resource(nsid: str) -> str:
        """Browse a specific AT Protocol lexicon by NSID."""
        kb = get_kb()
        chunk = kb.get_lexicon(nsid)
        if not chunk:
            return f"Lexicon '{nsid}' not found."

        raw_json = chunk.metadata.get("raw_json", "")
        if raw_json:
            try:
                parsed = json.loads(raw_json)
                return json.dumps(parsed, indent=2)
            except json.JSONDecodeError:
                pass
        return chunk.text

    @mcp.resource("atproto://cookbook")
    def list_all_cookbook_examples() -> str:
        """List all available AT Protocol cookbook examples."""
        kb = get_kb()
        examples = kb.list_cookbook_examples()
        return json.dumps(examples, indent=2)

    @mcp.resource("atproto://cookbook/{project}")
    def get_cookbook_resource(project: str) -> str:
        """Browse a specific cookbook example project."""
        kb = get_kb()
        chunk = kb.get_cookbook_example(project)
        if not chunk:
            return f"Cookbook example '{project}' not found."
        return chunk.text
