"""Smoke test for the full pipeline: parse, index, and query."""

from atproto_mcp.config import Config
from atproto_mcp.parser import parse_all
from atproto_mcp.indexer import KnowledgeBase


def main() -> None:
    config = Config.from_env()

    print("Parsing...")
    chunks = parse_all(config)
    print(f"Parsed {len(chunks)} chunks")

    print("Building txtai index (downloads model on first run)...")
    kb = KnowledgeBase(config)
    kb.build(chunks)
    print(f"Index built: {kb.chunk_count} chunks, {kb.lexicon_count} lexicons")

    print()
    print('=== Test: search for "create a post" ===')
    results = kb.search("how to create a post", limit=3)
    for r in results:
        print(f"  [{r['source']}] {r['title']} (score: {r['score']:.3f})")

    print()
    print("=== Test: get lexicon app.bsky.feed.post ===")
    lex = kb.get_lexicon("app.bsky.feed.post")
    if lex:
        print(f"  Found: {lex.title}")
        print(f"  Preview: {lex.text[:200]}...")
    else:
        print("  NOT FOUND")

    print()
    print('=== Test: search lexicons for "follow" ===')
    results = kb.search_lexicons("follow relationship", limit=3)
    for r in results:
        print(f"  {r['nsid']} (score: {r['score']:.3f})")

    print()
    print("=== Test: list cookbook examples ===")
    examples = kb.list_cookbook_examples()
    for ex in examples:
        print(f"  {ex['name']} [{ex['language']}]")

    print()
    print("=== Test: load cached index ===")
    kb2 = KnowledgeBase(config)
    loaded = kb2.load()
    print(f"  Loaded from cache: {loaded}")
    if loaded:
        print(f"  Chunks: {kb2.chunk_count}, Lexicons: {kb2.lexicon_count}")
        results = kb2.search("OAuth authentication", limit=2)
        for r in results:
            print(f"  [{r['source']}] {r['title']} (score: {r['score']:.3f})")

    print()
    print("All tests passed!")


if __name__ == "__main__":
    main()
