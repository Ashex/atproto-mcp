"""Configuration for the AT Protocol MCP server."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

_DEFAULT_CACHE_DIR = Path.home() / ".cache" / "atproto-mcp"

REPOS: dict[str, dict[str, str | list[str]]] = {
    "atproto-website": {
        "url": "https://github.com/bluesky-social/atproto-website.git",
        "branch": "main",
        "description": "AT Protocol website (atproto.com) — specs, guides, blog posts",
    },
    "cookbook": {
        "url": "https://github.com/bluesky-social/cookbook.git",
        "branch": "main",
        "description": "Bluesky cookbook — example projects and scripts",
    },
    "atproto": {
        "url": "https://github.com/bluesky-social/atproto.git",
        "branch": "main",
        "description": "AT Protocol monorepo — lexicon JSON schemas",
        "sparse_paths": ["lexicons"],
    },
    "bsky-docs": {
        "url": "https://github.com/bluesky-social/bsky-docs.git",
        "branch": "main",
        "description": "Bluesky developer docs (docs.bsky.app)",
    },
}

SOURCE_ATPROTO_WEBSITE = "atproto-website"
SOURCE_COOKBOOK = "cookbook"
SOURCE_LEXICONS = "lexicons"
SOURCE_BSKY_DOCS = "bsky-docs"


@dataclass(frozen=True)
class Config:
    """Server configuration, populated from environment variables."""

    cache_dir: Path = field(default_factory=lambda: _DEFAULT_CACHE_DIR)
    refresh_hours: int = 24
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    @classmethod
    def from_env(cls) -> Config:
        """Build configuration from environment variables."""
        cache_dir_str = os.environ.get("ATPROTO_MCP_CACHE_DIR")
        cache_dir = Path(cache_dir_str) if cache_dir_str else _DEFAULT_CACHE_DIR

        refresh_hours_str = os.environ.get("ATPROTO_MCP_REFRESH_HOURS", "24")
        try:
            refresh_hours = int(refresh_hours_str)
        except ValueError:
            refresh_hours = 24

        embedding_model = os.environ.get(
            "ATPROTO_MCP_EMBEDDING_MODEL",
            "sentence-transformers/all-MiniLM-L6-v2",
        )

        return cls(
            cache_dir=cache_dir,
            refresh_hours=refresh_hours,
            embedding_model=embedding_model,
        )

    @property
    def repos_dir(self) -> Path:
        return self.cache_dir / "repos"

    @property
    def index_dir(self) -> Path:
        return self.cache_dir / "index"

    @property
    def meta_dir(self) -> Path:
        return self.cache_dir / "meta"
