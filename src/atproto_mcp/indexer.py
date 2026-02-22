"""txtai-powered semantic search indexer for AT Protocol content."""

import json
import logging
from pathlib import Path

from txtai import Embeddings

from atproto_mcp.config import Config
from atproto_mcp.parser import ContentChunk, encode_tags

logger = logging.getLogger(__name__)

_META_KEYS = ("source", "file_path", "title", "url", "nsid", "language")


class KnowledgeBase:
    """Semantic search index over AT Protocol documentation.

    Wraps a txtai Embeddings instance with helpers for indexing
    parsed content chunks and running filtered searches.
    """

    def __init__(self, config: Config) -> None:
        self._config = config
        self._embeddings: Embeddings | None = None
        self._chunks_by_uid: dict[str, ContentChunk] = {}
        self._lexicon_map: dict[str, ContentChunk] = {}

    def _init_embeddings(self) -> Embeddings:
        """Create a fresh txtai Embeddings instance."""
        return Embeddings(
            path=self._config.embedding_model,
            content=True,  # persist full text alongside vectors
        )

    def build(self, chunks: list[ContentChunk]) -> None:
        """Build the search index from scratch."""
        logger.info("Building index with %d chunks …", len(chunks))
        self._embeddings = self._init_embeddings()

        # Prepare documents as (id, text, tags) tuples for txtai
        documents: list[tuple[str, str, str | None]] = []
        for chunk in chunks:
            uid = chunk.uid
            self._chunks_by_uid[uid] = chunk
            if chunk.nsid:
                self._lexicon_map[chunk.nsid] = chunk
            documents.append((uid, chunk.text, encode_tags(chunk.tags)))

        self._embeddings.index(documents)

        self._save()
        self._save_chunk_meta(chunks)
        logger.info("Index built and saved (%d documents)", len(documents))

    def load(self) -> bool:
        """Load a previously saved index from disk. Returns True on success."""
        index_path = self._config.index_dir
        if not index_path.exists():
            logger.info("No existing index at %s", index_path)
            return False

        try:
            self._embeddings = self._init_embeddings()
            self._embeddings.load(str(index_path))
            self._load_chunk_meta()
            logger.info(
                "Loaded cached index (%d chunks, %d lexicons)",
                len(self._chunks_by_uid),
                len(self._lexicon_map),
            )
            return True
        except Exception:
            logger.warning("Failed to load cached index", exc_info=True)
            return False

    def _save(self) -> None:
        """Persist the txtai index to disk."""
        index_path = self._config.index_dir
        index_path.mkdir(parents=True, exist_ok=True)
        if self._embeddings:
            self._embeddings.save(str(index_path))

    def _save_chunk_meta(self, chunks: list[ContentChunk]) -> None:
        """Save chunk metadata alongside the index."""
        meta_path = self._config.index_dir / "chunk_meta.json"
        data = []
        for chunk in chunks:
            entry: dict[str, str | list[str]] = {"uid": chunk.uid}
            for key in _META_KEYS:
                entry[key] = getattr(chunk, key, "")
            entry["tags"] = chunk.tags
            if chunk.nsid and "raw_json" in chunk.metadata:
                entry["raw_json"] = chunk.metadata["raw_json"]
            data.append(entry)
        meta_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load_chunk_meta(self) -> None:
        """Reload chunk metadata from disk."""
        meta_path = self._config.index_dir / "chunk_meta.json"
        if not meta_path.exists():
            return

        data = json.loads(meta_path.read_text(encoding="utf-8"))
        for entry in data:
            stored_tags = entry.get("tags", [])
            # Backward compat: reconstruct source tag if tags are missing
            if not stored_tags and entry.get("source"):
                stored_tags = [f"source:{entry['source']}"]
            chunk = ContentChunk(
                text="",  # text is in txtai, we only need meta here
                source=entry.get("source", ""),
                file_path=entry.get("file_path", ""),
                title=entry.get("title", ""),
                url=entry.get("url", ""),
                nsid=entry.get("nsid", ""),
                language=entry.get("language", ""),
                metadata={"raw_json": entry["raw_json"]} if "raw_json" in entry else {},
                tags=stored_tags,
            )
            uid = entry.get("uid", chunk.uid)
            self._chunks_by_uid[uid] = chunk
            if chunk.nsid:
                self._lexicon_map[chunk.nsid] = chunk


    def search(
        self,
        query: str,
        *,
        source: str | None = None,
        tags: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, object]]:
        """Semantic search across the knowledge base.

        Args:
            query: Natural language search query.
            source: Optional source filter (atproto-website, bsky-docs, cookbook, lexicons).
            tags: Optional tag filters (e.g. ``["content_type:guide"]``).
            limit: Maximum number of results.

        Returns:
            List of result dicts with keys: uid, text, score, source, title,
            url, nsid, language, tags.
        """
        if not self._embeddings:
            return []

        tag_filters: list[str] = list(tags) if tags else []
        if source:
            tag_filters.append(f"source:{source}")

        if tag_filters:
            results = self._filtered_search(query, tag_filters, limit)
        else:
            results = self._embeddings.search(query, limit=limit)

        return self._enrich_results(
            list(results) if isinstance(results, list) else [],  # type: ignore[arg-type]
            source_filter=source,
        )[:limit]

    def _filtered_search(
        self,
        query: str,
        tag_filters: list[str],
        limit: int,
    ) -> list[object]:
        """Execute a tag-filtered semantic search using txtai SQL."""
        if not self._embeddings:
            return []  # pragma: no cover

        escaped_query = query.replace("'", "''")
        where_parts = [f"similar('{escaped_query}')"]
        for tag in tag_filters:
            escaped_tag = tag.replace("'", "''")
            where_parts.append(f"tags LIKE '%|{escaped_tag}|%'")
        where_clause = " AND ".join(where_parts)
        sql = f"SELECT id, text, score FROM txtai WHERE {where_clause} LIMIT {limit}"

        # Over-fetch ANN candidates so enough survive tag filtering
        ann_limit = max(limit * 5, 100)
        try:
            return self._embeddings.search(sql, limit=ann_limit)  # type: ignore[return-value]
        except Exception:
            logger.warning(
                "SQL-filtered search failed, falling back to unfiltered",
                exc_info=True,
            )
            fetch_limit = max(limit * 5, 50)
            return self._embeddings.search(query, limit=fetch_limit)  # type: ignore[return-value]

    def search_lexicons(self, query: str, limit: int = 10) -> list[dict[str, object]]:
        """Semantic search specifically within lexicons."""
        return self.search(
            query, source="lexicons", tags=["content_type:reference"], limit=limit
        )

    def search_bsky_api(self, query: str, limit: int = 10) -> list[dict[str, object]]:
        """Semantic search specifically within Bluesky API docs."""
        return self.search(query, source="bsky-docs", limit=limit)

    def _enrich_results(
        self,
        raw_results: list[object],
        source_filter: str | None = None,
    ) -> list[dict[str, object]]:
        """Enrich raw txtai results with chunk metadata."""
        enriched: list[dict[str, object]] = []
        for result in raw_results:
            if isinstance(result, dict):
                uid = result.get("id", "")
                text = result.get("text", "")
                score = result.get("score", 0.0)
            elif isinstance(result, (list, tuple)) and len(result) >= 2:
                uid = result[0]
                score = result[1]
                text = ""
            else:
                continue

            uid_str = str(uid)
            chunk = self._chunks_by_uid.get(uid_str)

            # Apply source filter on the metadata side
            if source_filter and chunk and chunk.source != source_filter:
                continue

            entry: dict[str, object] = {
                "uid": uid_str,
                "text": str(text)[:2000] if text else "",
                "score": float(str(score)),
                "source": chunk.source if chunk else "",
                "title": chunk.title if chunk else "",
                "url": chunk.url if chunk else "",
                "nsid": chunk.nsid if chunk else "",
                "language": chunk.language if chunk else "",
                "tags": chunk.tags if chunk else [],
            }
            enriched.append(entry)

        return enriched


    def get_lexicon(self, nsid: str) -> ContentChunk | None:
        """Retrieve a lexicon by its NSID."""
        return self._lexicon_map.get(nsid)

    def list_lexicons(self, namespace: str | None = None) -> list[dict[str, str]]:
        """List all indexed lexicons, optionally filtered by namespace prefix."""
        results: list[dict[str, str]] = []
        for nsid, chunk in sorted(self._lexicon_map.items()):
            if namespace and not nsid.startswith(namespace):
                continue
            results.append({
                "nsid": nsid,
                "title": chunk.title,
                "source": chunk.source,
            })
        return results

    def get_cookbook_example(self, name: str) -> ContentChunk | None:
        """Retrieve a cookbook example by project name."""
        for chunk in self._chunks_by_uid.values():
            if chunk.source == "cookbook" and chunk.file_path == name:
                return chunk
        return None

    def list_cookbook_examples(
        self, language: str | None = None
    ) -> list[dict[str, str]]:
        """List all cookbook examples, optionally filtered by language."""
        results: list[dict[str, str]] = []
        for chunk in self._chunks_by_uid.values():
            if chunk.source != "cookbook":
                continue
            if language and chunk.language.lower() != language.lower():
                continue
            results.append({
                "name": chunk.file_path,
                "title": chunk.title,
                "language": chunk.language,
                "url": chunk.url,
            })
        return sorted(results, key=lambda d: d["name"])

    @property
    def is_loaded(self) -> bool:
        return self._embeddings is not None

    @property
    def chunk_count(self) -> int:
        return len(self._chunks_by_uid)

    @property
    def lexicon_count(self) -> int:
        return len(self._lexicon_map)


def build_knowledge_base(config: Config, chunks: list[ContentChunk]) -> KnowledgeBase:
    """Build a new knowledge base from parsed content chunks."""
    kb = KnowledgeBase(config)
    kb.build(chunks)
    return kb


def load_or_build_knowledge_base(
    config: Config,
    chunks: list[ContentChunk] | None = None,
) -> KnowledgeBase:
    """Load a cached knowledge base, or build from chunks if unavailable."""
    kb = KnowledgeBase(config)
    if kb.load():
        return kb

    if chunks is None:
        raise RuntimeError(
            "No cached index and no chunks provided — cannot build knowledge base"
        )

    kb.build(chunks)
    return kb
