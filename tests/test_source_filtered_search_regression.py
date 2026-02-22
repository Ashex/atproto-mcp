"""Regression tests for source-filtered semantic search."""

from __future__ import annotations

import re
import unittest

from atproto_mcp.config import Config
from atproto_mcp.indexer import KnowledgeBase
from atproto_mcp.parser import ContentChunk


class _FakeEmbeddings:
    """Minimal fake that simulates txtai Embeddings for testing.

    Handles both plain semantic queries and SQL queries with tag-based
    WHERE clauses so that ``KnowledgeBase._filtered_search`` works.
    """

    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def search(self, query: str, limit: int = 10) -> list[dict[str, object]]:
        query_str = str(query).strip()
        if query_str.lower().startswith("select"):
            return self._sql_search(query_str, limit)
        return [
            {"id": r["id"], "text": r.get("text", ""), "score": r.get("score", 0.0)}
            for r in self._rows[:limit]
        ]

    def _sql_search(self, sql: str, _limit: int) -> list[dict[str, object]]:
        like_matches = re.findall(
            r"tags\s+LIKE\s+'%\|([^|]+)\|%'", sql, re.IGNORECASE
        )
        limit_match = re.search(r"LIMIT\s+(\d+)", sql, re.IGNORECASE)
        result_limit = int(limit_match.group(1)) if limit_match else _limit

        filtered: list[dict[str, object]] = []
        for row in self._rows:
            tags_str = str(row.get("tags", ""))
            if all(f"|{tag}|" in tags_str for tag in like_matches):
                filtered.append(
                    {
                        "id": row["id"],
                        "text": row.get("text", ""),
                        "score": row.get("score", 0.0),
                    }
                )
        return filtered[:result_limit]


class SourceFilteredSearchRegressionTests(unittest.TestCase):
    def test_search_lexicons_returns_source_filtered_results(self) -> None:
        kb = KnowledgeBase(Config())

        kb._embeddings = _FakeEmbeddings(
            [
                {
                    "id": "a",
                    "text": "lexicon schema",
                    "score": 0.9,
                    "tags": "|content_type:guide|domain:docs.bsky.app|source:bsky-docs|",
                },
                {
                    "id": "b",
                    "text": "lexicon schema",
                    "score": 0.8,
                    "tags": "|content_type:reference|domain:github.com|namespace:com.atproto.lexicon|source:lexicons|",
                },
            ]
        )
        kb._chunks_by_uid = {
            "a": ContentChunk(
                text="",
                source="bsky-docs",
                file_path="docs/a.md",
                title="A",
                tags=["source:bsky-docs", "content_type:guide", "domain:docs.bsky.app"],
            ),
            "b": ContentChunk(
                text="",
                source="lexicons",
                file_path="lexicons/b.json",
                title="B",
                nsid="com.atproto.lexicon.schema",
                tags=[
                    "source:lexicons",
                    "content_type:reference",
                    "domain:github.com",
                    "namespace:com.atproto.lexicon",
                ],
            ),
        }

        results = kb.search_lexicons("com.atproto.lexicon.schema record type", limit=1)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["source"], "lexicons")
        self.assertEqual(results[0]["nsid"], "com.atproto.lexicon.schema")

    def test_search_atproto_website_source_filter_returns_matching_rows(self) -> None:
        kb = KnowledgeBase(Config())

        kb._embeddings = _FakeEmbeddings(
            [
                {
                    "id": "x",
                    "text": "dns txt",
                    "score": 0.7,
                    "tags": "|content_type:reference|domain:github.com|source:lexicons|",
                },
                {
                    "id": "y",
                    "text": "dns txt",
                    "score": 0.6,
                    "tags": "|content_type:spec|domain:atproto.com|source:atproto-website|topic:specs|",
                },
            ]
        )
        kb._chunks_by_uid = {
            "x": ContentChunk(
                text="",
                source="lexicons",
                file_path="lexicons/x.json",
                title="X",
                tags=["source:lexicons", "content_type:reference", "domain:github.com"],
            ),
            "y": ContentChunk(
                text="",
                source="atproto-website",
                file_path="specs/y.mdx",
                title="En > DNS TXT Method",
                tags=[
                    "source:atproto-website",
                    "content_type:spec",
                    "domain:atproto.com",
                    "topic:specs",
                ],
            ),
        }

        results = kb.search(
            "lexicon schema record DNS TXT _lexicon authority resolution PDS serving",
            source="atproto-website",
            limit=1,
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["source"], "atproto-website")
        self.assertEqual(results[0]["title"], "En > DNS TXT Method")


if __name__ == "__main__":
    unittest.main()
