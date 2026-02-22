"""Tests for the document tagging system."""

import re
import unittest

from atproto_mcp.config import Config
from atproto_mcp.indexer import KnowledgeBase
from atproto_mcp.parser import (
    ContentChunk,
    _build_bsky_docs_tags,
    _build_cookbook_tags,
    _build_lexicon_tags,
    _build_website_tags,
    _extract_path_topic,
    encode_tags,
)


# ---------------------------------------------------------------------------
# encode_tags
# ---------------------------------------------------------------------------


class EncodeTagsTests(unittest.TestCase):
    def test_empty_list_returns_empty_string(self) -> None:
        self.assertEqual(encode_tags([]), "")

    def test_single_tag(self) -> None:
        self.assertEqual(encode_tags(["source:lexicons"]), "|source:lexicons|")

    def test_multiple_tags_sorted(self) -> None:
        result = encode_tags(["content_type:guide", "source:bsky-docs", "domain:docs.bsky.app"])
        self.assertEqual(
            result,
            "|content_type:guide|domain:docs.bsky.app|source:bsky-docs|",
        )

    def test_deduplicates(self) -> None:
        result = encode_tags(["source:x", "source:x", "content_type:y"])
        self.assertEqual(result, "|content_type:y|source:x|")

    def test_pipe_delimited_format_enables_unambiguous_like(self) -> None:
        encoded = encode_tags(["source:lexicons", "source:lexicons-extra"])
        self.assertIn("|source:lexicons|", encoded)
        self.assertIn("|source:lexicons-extra|", encoded)
        # Make sure a naive substring match on "source:lexicons" doesn't
        # accidentally match "source:lexicons-extra" when using pipe delimiters.
        self.assertNotEqual(
            encoded.count("|source:lexicons|"),
            encoded.count("|source:lexicons"),  # would be 2 without pipes
        )


# ---------------------------------------------------------------------------
# Tag builder helpers
# ---------------------------------------------------------------------------


class WebsiteTagsTests(unittest.TestCase):
    def test_guide_content_type(self) -> None:
        tags = _build_website_tags("src/app/en/guides/overview.mdx")
        self.assertIn("source:atproto-website", tags)
        self.assertIn("content_type:guide", tags)
        self.assertIn("domain:atproto.com", tags)
        self.assertIn("topic:guides", tags)

    def test_spec_content_type(self) -> None:
        tags = _build_website_tags("src/app/en/specs/did.mdx")
        self.assertIn("content_type:spec", tags)
        self.assertIn("topic:specs", tags)

    def test_blog_content_type(self) -> None:
        tags = _build_website_tags("content/blog/2024-launch.md")
        self.assertIn("content_type:blog", tags)

    def test_lexicon_in_path_is_spec(self) -> None:
        tags = _build_website_tags("src/app/en/lexicon/overview.mdx")
        self.assertIn("content_type:spec", tags)


class BskyDocsTagsTests(unittest.TestCase):
    def test_guide_content_type(self) -> None:
        tags = _build_bsky_docs_tags("docs/advanced-guides/firehose.mdx")
        self.assertIn("source:bsky-docs", tags)
        self.assertIn("content_type:guide", tags)
        self.assertIn("domain:docs.bsky.app", tags)
        self.assertIn("topic:advanced-guides", tags)

    def test_blog_content_type(self) -> None:
        tags = _build_bsky_docs_tags("blog/2024-update.md")
        self.assertIn("content_type:blog", tags)

    def test_root_docs_topic(self) -> None:
        tags = _build_bsky_docs_tags("docs/starter-templates/overview.mdx")
        self.assertIn("topic:starter-templates", tags)


class LexiconTagsTests(unittest.TestCase):
    def test_record_type(self) -> None:
        lexicon = {"id": "app.bsky.feed.post", "defs": {"main": {"type": "record"}}}
        tags = _build_lexicon_tags("app.bsky.feed.post", lexicon)
        self.assertIn("source:lexicons", tags)
        self.assertIn("content_type:reference", tags)
        self.assertIn("domain:github.com", tags)
        self.assertIn("namespace:app.bsky.feed", tags)
        self.assertIn("lexicon_type:record", tags)

    def test_query_type(self) -> None:
        lexicon = {
            "id": "com.atproto.repo.listRecords",
            "defs": {"main": {"type": "query"}},
        }
        tags = _build_lexicon_tags("com.atproto.repo.listRecords", lexicon)
        self.assertIn("namespace:com.atproto.repo", tags)
        self.assertIn("lexicon_type:query", tags)

    def test_procedure_type(self) -> None:
        lexicon = {
            "id": "com.atproto.repo.createRecord",
            "defs": {"main": {"type": "procedure"}},
        }
        tags = _build_lexicon_tags("com.atproto.repo.createRecord", lexicon)
        self.assertIn("lexicon_type:procedure", tags)

    def test_subscription_type(self) -> None:
        lexicon = {
            "id": "com.atproto.sync.subscribeRepos",
            "defs": {"main": {"type": "subscription"}},
        }
        tags = _build_lexicon_tags("com.atproto.sync.subscribeRepos", lexicon)
        self.assertIn("lexicon_type:subscription", tags)

    def test_short_nsid_no_namespace(self) -> None:
        lexicon = {"id": "app.bsky", "defs": {"main": {"type": "record"}}}
        tags = _build_lexicon_tags("app.bsky", lexicon)
        self.assertNotIn(
            True,
            [t.startswith("namespace:") for t in tags],
            "Short NSID should not produce a namespace tag",
        )


class CookbookTagsTests(unittest.TestCase):
    def test_python_language(self) -> None:
        tags = _build_cookbook_tags("python")
        self.assertIn("source:cookbook", tags)
        self.assertIn("content_type:example", tags)
        self.assertIn("language:python", tags)

    def test_unknown_language_excluded(self) -> None:
        tags = _build_cookbook_tags("unknown")
        self.assertFalse(
            any(t.startswith("language:") for t in tags),
            "Unknown language should not produce a language tag",
        )

    def test_empty_language_excluded(self) -> None:
        tags = _build_cookbook_tags("")
        self.assertFalse(any(t.startswith("language:") for t in tags))


# ---------------------------------------------------------------------------
# _extract_path_topic
# ---------------------------------------------------------------------------


class ExtractPathTopicTests(unittest.TestCase):
    def test_strips_src_app_and_language(self) -> None:
        self.assertEqual(_extract_path_topic("src/app/en/guides/overview.mdx"), "guides")

    def test_strips_docs_prefix(self) -> None:
        self.assertEqual(
            _extract_path_topic("docs/advanced-guides/firehose.mdx"),
            "advanced-guides",
        )

    def test_single_file_returns_empty(self) -> None:
        self.assertEqual(_extract_path_topic("overview.mdx"), "")

    def test_content_prefix(self) -> None:
        self.assertEqual(_extract_path_topic("content/blog/post.md"), "blog")


# ---------------------------------------------------------------------------
# ContentChunk tags field
# ---------------------------------------------------------------------------


class ContentChunkTagsTests(unittest.TestCase):
    def test_default_tags_empty(self) -> None:
        chunk = ContentChunk(text="x", source="s", file_path="f", title="t")
        self.assertEqual(chunk.tags, [])

    def test_tags_preserved(self) -> None:
        tags = ["source:lexicons", "content_type:reference"]
        chunk = ContentChunk(
            text="x", source="s", file_path="f", title="t", tags=tags
        )
        self.assertEqual(chunk.tags, tags)


# ---------------------------------------------------------------------------
# Tag-filtered search via KnowledgeBase
# ---------------------------------------------------------------------------


class _FakeEmbeddings:
    """Minimal fake that simulates txtai Embeddings for tag-filtered SQL."""

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


class TagFilteredSearchTests(unittest.TestCase):
    def _make_kb(self) -> KnowledgeBase:
        kb = KnowledgeBase(Config())
        kb._embeddings = _FakeEmbeddings(
            [
                {
                    "id": "guide-1",
                    "text": "OAuth guide",
                    "score": 0.95,
                    "tags": "|content_type:guide|domain:atproto.com|source:atproto-website|topic:guides|",
                },
                {
                    "id": "lex-1",
                    "text": "createSession procedure",
                    "score": 0.90,
                    "tags": "|content_type:reference|domain:github.com|lexicon_type:procedure|namespace:com.atproto.server|source:lexicons|",
                },
                {
                    "id": "cook-1",
                    "text": "python OAuth example",
                    "score": 0.85,
                    "tags": "|content_type:example|domain:github.com|language:python|source:cookbook|",
                },
                {
                    "id": "blog-1",
                    "text": "federation launch blog",
                    "score": 0.80,
                    "tags": "|content_type:blog|domain:docs.bsky.app|source:bsky-docs|topic:blog|",
                },
            ]
        )
        kb._chunks_by_uid = {
            "guide-1": ContentChunk(
                text="",
                source="atproto-website",
                file_path="src/app/en/guides/oauth.mdx",
                title="OAuth Guide",
                tags=["source:atproto-website", "content_type:guide", "domain:atproto.com", "topic:guides"],
            ),
            "lex-1": ContentChunk(
                text="",
                source="lexicons",
                file_path="lexicons/com/atproto/server/createSession.json",
                title="com.atproto.server.createSession",
                nsid="com.atproto.server.createSession",
                tags=[
                    "source:lexicons",
                    "content_type:reference",
                    "domain:github.com",
                    "namespace:com.atproto.server",
                    "lexicon_type:procedure",
                ],
            ),
            "cook-1": ContentChunk(
                text="",
                source="cookbook",
                file_path="python-oauth-web-app",
                title="Cookbook: python-oauth-web-app",
                language="python",
                tags=["source:cookbook", "content_type:example", "domain:github.com", "language:python"],
            ),
            "blog-1": ContentChunk(
                text="",
                source="bsky-docs",
                file_path="blog/federation.md",
                title="Federation Launch",
                tags=["source:bsky-docs", "content_type:blog", "domain:docs.bsky.app", "topic:blog"],
            ),
        }
        return kb

    def test_source_filter_only(self) -> None:
        kb = self._make_kb()
        results = kb.search("OAuth", source="atproto-website", limit=10)
        sources = {r["source"] for r in results}
        self.assertEqual(sources, {"atproto-website"})

    def test_tag_filter_content_type(self) -> None:
        kb = self._make_kb()
        results = kb.search("OAuth", tags=["content_type:example"], limit=10)
        self.assertTrue(all("content_type:example" in r["tags"] for r in results))

    def test_source_plus_tag_filter(self) -> None:
        kb = self._make_kb()
        results = kb.search(
            "OAuth", source="lexicons", tags=["content_type:reference"], limit=10
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["nsid"], "com.atproto.server.createSession")

    def test_no_filter_returns_all(self) -> None:
        kb = self._make_kb()
        results = kb.search("OAuth", limit=10)
        self.assertEqual(len(results), 4)

    def test_unmatched_tag_returns_empty(self) -> None:
        kb = self._make_kb()
        results = kb.search("OAuth", tags=["content_type:nonexistent"], limit=10)
        self.assertEqual(len(results), 0)

    def test_search_lexicons_uses_tags(self) -> None:
        kb = self._make_kb()
        results = kb.search_lexicons("createSession", limit=10)
        self.assertTrue(len(results) >= 1)
        self.assertEqual(results[0]["source"], "lexicons")

    def test_tags_included_in_results(self) -> None:
        kb = self._make_kb()
        results = kb.search("OAuth", limit=1)
        self.assertIn("tags", results[0])
        self.assertIsInstance(results[0]["tags"], list)


# ---------------------------------------------------------------------------
# Metadata round-trip (save → load preserves tags)
# ---------------------------------------------------------------------------


class MetadataRoundTripTests(unittest.TestCase):
    def test_save_and_load_preserves_tags(self) -> None:
        import json
        import tempfile
        from pathlib import Path

        config = Config(cache_dir=Path(tempfile.mkdtemp()))
        kb = KnowledgeBase(config)
        config.index_dir.mkdir(parents=True, exist_ok=True)

        chunks = [
            ContentChunk(
                text="test content",
                source="lexicons",
                file_path="lexicons/test.json",
                title="test.lexicon",
                nsid="com.test.lexicon",
                tags=["source:lexicons", "content_type:reference", "namespace:com.test"],
                metadata={"raw_json": '{"id":"com.test.lexicon"}'},
            ),
        ]

        kb._save_chunk_meta(chunks)

        meta_path = config.index_dir / "chunk_meta.json"
        self.assertTrue(meta_path.exists())

        data = json.loads(meta_path.read_text())
        self.assertEqual(len(data), 1)
        self.assertEqual(
            data[0]["tags"],
            ["source:lexicons", "content_type:reference", "namespace:com.test"],
        )

    def test_load_without_tags_reconstructs_source(self) -> None:
        import json
        import tempfile
        from pathlib import Path

        config = Config(cache_dir=Path(tempfile.mkdtemp()))
        kb = KnowledgeBase(config)

        # Simulate old-format metadata without tags
        meta_path = config.index_dir / "chunk_meta.json"
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        old_data = [
            {
                "uid": "lexicons:com.old.lexicon",
                "source": "lexicons",
                "file_path": "lexicons/old.json",
                "title": "com.old.lexicon",
                "url": "",
                "nsid": "com.old.lexicon",
                "language": "",
            }
        ]
        meta_path.write_text(json.dumps(old_data))

        kb._load_chunk_meta()

        chunk = kb._chunks_by_uid.get("lexicons:com.old.lexicon")
        self.assertIsNotNone(chunk)
        self.assertIn("source:lexicons", chunk.tags)


if __name__ == "__main__":
    unittest.main()
