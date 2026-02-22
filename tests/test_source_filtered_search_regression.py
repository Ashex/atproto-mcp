"""Regression tests for source-filtered semantic search."""

from __future__ import annotations

import unittest

from atproto_mcp.config import Config
from atproto_mcp.indexer import KnowledgeBase
from atproto_mcp.parser import ContentChunk


class _FakeEmbeddings:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def search(self, query: str, limit: int = 10) -> list[dict[str, object]]:
        return self._rows[:limit]


class SourceFilteredSearchRegressionTests(unittest.TestCase):
    def test_search_lexicons_returns_source_filtered_results(self) -> None:
        kb = KnowledgeBase(Config())

        kb._embeddings = _FakeEmbeddings(
            [
                {"id": "a", "text": "lexicon schema", "score": 0.9},
                {"id": "b", "text": "lexicon schema", "score": 0.8},
            ]
        )
        kb._chunks_by_uid = {
            "a": ContentChunk(
                text="",
                source="bsky-docs",
                file_path="docs/a.md",
                title="A",
            ),
            "b": ContentChunk(
                text="",
                source="lexicons",
                file_path="lexicons/b.json",
                title="B",
                nsid="com.atproto.lexicon.schema",
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
                {"id": "x", "text": "dns txt", "score": 0.7},
                {"id": "y", "text": "dns txt", "score": 0.6},
            ]
        )
        kb._chunks_by_uid = {
            "x": ContentChunk(
                text="",
                source="lexicons",
                file_path="lexicons/x.json",
                title="X",
            ),
            "y": ContentChunk(
                text="",
                source="atproto-website",
                file_path="specs/y.mdx",
                title="En > DNS TXT Method",
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
