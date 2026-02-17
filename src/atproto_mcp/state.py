"""Shared application state populated during server lifespan."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from atproto_mcp.config import Config
    from atproto_mcp.indexer import KnowledgeBase

# Module-level references set during server lifespan.
# These are populated by server.py's app_lifespan() before any
# tools or resources are invoked.

kb: KnowledgeBase | None = None
config: Config | None = None


def get_kb() -> KnowledgeBase:
    """Get the active KnowledgeBase instance.

    Raises:
        RuntimeError: If the knowledge base hasn't been initialized yet.
    """
    if kb is None:
        raise RuntimeError("Knowledge base not initialized — server lifespan not started")
    return kb


def get_config() -> Config:
    """Get the active Config instance."""
    if config is None:
        from atproto_mcp.config import Config as ConfigCls

        return ConfigCls.from_env()
    return config
