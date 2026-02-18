# atproto-mcp

MCP server providing a searchable knowledge base for the [AT Protocol](https://atproto.com/) ecosystem — protocol documentation, lexicon schemas, Bluesky developer API docs, and cookbook examples — powered by [txtai](https://github.com/neuml/txtai) semantic search.

## Data Sources

| Source | Repository | Description |
| -------- | ----------- | ------------- |
| **AT Protocol Website** | [bluesky-social/atproto-website](https://github.com/bluesky-social/atproto-website) | Protocol specs, guides, and blog posts from atproto.com |
| **Bluesky API Docs** | [bluesky-social/bsky-docs](https://github.com/bluesky-social/bsky-docs) | Developer docs from docs.bsky.app — tutorials, guides, advanced topics |
| **AT Protocol Lexicons** | [bluesky-social/atproto](https://github.com/bluesky-social/atproto/tree/main/lexicons) | JSON schemas defining all AT Protocol endpoints and record types |
| **Cookbook** | [bluesky-social/cookbook](https://github.com/bluesky-social/cookbook) | Example projects in Python, Go, TypeScript, and JavaScript |

## Tools

| Tool | Description |
| ------ | ------------- |
| `search_atproto_docs` | Semantic search across all documentation sources |
| `get_lexicon` | Retrieve a specific lexicon by NSID (e.g. `app.bsky.feed.post`) |
| `list_lexicons` | List all lexicons, optionally filtered by namespace |
| `search_lexicons` | Semantic search within lexicon schemas |
| `get_cookbook_example` | Get a specific cookbook example by project name |
| `list_cookbook_examples` | List all cookbook examples, optionally by language |
| `search_bsky_api` | Semantic search within Bluesky API docs |
| `refresh_sources` | Force re-fetch repos and rebuild the index |

## Prompts

| Prompt | Description |
| -------- | ------------- |
| `explain_lexicon` | Get a comprehensive explanation of a lexicon |
| `implement_feature` | Get implementation guidance with code examples |
| `debug_atproto` | Help debug AT Protocol / Bluesky API issues |
| `explore_namespace` | Explore all lexicons in a namespace |

## Installation

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Git (for cloning source repositories)

### Install from source

```bash
git clone https://github.com/ashex/atproto-mcp.git
cd atproto-mcp
uv sync
```

### Run with uvx

```bash
uvx atproto-mcp
```

## Configuration

### VS Code / Copilot

[![Install in VS Code](https://img.shields.io/badge/VS_Code-Install_ATproto_MCP-0098FF?style=flat-square&logo=visualstudiocode&logoColor=ffffff)](vscode:mcp/install?%7B%22name%22%3A%22atproto-mcp%22%2C%22type%22%3A%22stdio%22%2C%22command%22%3A%22uv%22%2C%22args%22%3A%5B%22atproto-mcp%22%5D%7D)

Add to `.vscode/mcp.json` in your workspace:

```json
{
  "mcpServers": {
    "atproto": {
      "command": "uvx",
      "args": [
        "atproto-mcp"
        ]
    }
  }
}
```

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "atproto": {
      "command": "uvx",
      "args": [
         "atproto-mcp"
      ]
    }
  }
}
```

## Environment Variables

| Variable | Default | Description |
| ---------- | --------- | ------------- |
| `ATPROTO_MCP_CACHE_DIR` | `~/.cache/atproto-mcp` | Where repos and the search index are stored |
| `ATPROTO_MCP_REFRESH_HOURS` | `24` | Hours before re-fetching repositories |
| `ATPROTO_MCP_EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Sentence-transformers model for embeddings |

## How It Works

On first launch, the server:

1. Shallow clones the repos into `~/.cache/atproto-mcp/repos/`
2. Parses MDX docs, lexicon schemas, and cookbook examples into text chunks
3. Indexes the chunks using txtai with the `all-MiniLM-L6-v2` sentence-transformer model (~80MB, runs locally)
4. Index is persisted in `~/.cache/atproto-mcp/index/` for subsequent starts

On subsequent launches, the cached index loads in seconds. Repos older than 24 hours are automatically refreshed with `git pull`.

## Development

```bash
# Install in development mode
uv sync

# Run the server locally (stdio)
uv run atproto-mcp

# Test with the MCP Inspector
uv run mcp dev src/atproto_mcp/server.py

# Run with debug logging
ATPROTO_MCP_CACHE_DIR=/tmp/atproto-mcp uv run atproto-mcp
```

## License

MIT
