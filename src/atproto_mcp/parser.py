"""Content parser for AT Protocol documentation sources.

Parses MDX docs, lexicon JSON files, and cookbook examples into
structured text chunks suitable for indexing.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from atproto_mcp.config import (
    SOURCE_ATPROTO_WEBSITE,
    SOURCE_BSKY_DOCS,
    SOURCE_COOKBOOK,
    SOURCE_LEXICONS,
    Config,
)

logger = logging.getLogger(__name__)


@dataclass
class ContentChunk:
    """A single document chunk ready for indexing."""

    text: str
    source: str  # atproto-website | bsky-docs | cookbook | lexicons
    file_path: str  # relative path within the repo
    title: str
    url: str = ""
    nsid: str = ""  # for lexicons only
    language: str = ""  # for cookbook examples (python, go, typescript, etc.)
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def uid(self) -> str:
        """Unique identifier for this chunk."""
        if self.nsid:
            return f"{self.source}:{self.nsid}"
        return f"{self.source}:{self.file_path}:{self.title}"


# Regex to strip JSX/MDX component tags like <ExplainerUnit>, <Tabs>, etc.
_JSX_OPEN_CLOSE = re.compile(r"</?[A-Z][A-Za-z0-9]*(?:\s[^>]*)?\s*/?>", re.MULTILINE)
_JSX_SELF_CLOSE = re.compile(r"<[A-Z][A-Za-z0-9]*\s[^>]*/\s*>", re.MULTILINE)
_IMPORT_STMT = re.compile(r"^import\s+.*$", re.MULTILINE)
_EXPORT_STMT = re.compile(r"^export\s+.*$", re.MULTILINE)
_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _strip_mdx(content: str) -> str:
    """Strip JSX components, imports, and exports from MDX content."""
    content = _FRONTMATTER.sub("", content)
    content = _IMPORT_STMT.sub("", content)
    content = _EXPORT_STMT.sub("", content)
    content = _JSX_OPEN_CLOSE.sub("", content)
    content = _JSX_SELF_CLOSE.sub("", content)
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content.strip()


def _extract_frontmatter(content: str) -> dict[str, str]:
    """Extract YAML-ish frontmatter key-value pairs."""
    match = _FRONTMATTER.search(content)
    if not match:
        return {}
    fm: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            fm[key.strip()] = value.strip().strip("\"'")
    return fm


def _chunk_by_headings(
    text: str,
    file_path: str,
    source: str,
    base_title: str,
    url: str = "",
    min_chunk_len: int = 50,
) -> list[ContentChunk]:
    """Split markdown text by H2/H3 headings into chunks."""
    heading_pattern = re.compile(r"^(#{2,3})\s+(.+)$", re.MULTILINE)
    chunks: list[ContentChunk] = []

    matches = list(heading_pattern.finditer(text))

    if not matches:
        # No subheadings — treat entire content as one chunk
        cleaned = text.strip()
        if len(cleaned) >= min_chunk_len:
            chunks.append(
                ContentChunk(
                    text=cleaned,
                    source=source,
                    file_path=file_path,
                    title=base_title,
                    url=url,
                )
            )
        return chunks

    preamble = text[: matches[0].start()].strip()
    if len(preamble) >= min_chunk_len:
        chunks.append(
            ContentChunk(
                text=preamble,
                source=source,
                file_path=file_path,
                title=base_title,
                url=url,
            )
        )

    for i, match in enumerate(matches):
        heading_title = match.group(2).strip()
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section_text = text[start:end].strip()

        if len(section_text) >= min_chunk_len:
            chunks.append(
                ContentChunk(
                    text=section_text,
                    source=source,
                    file_path=file_path,
                    title=f"{base_title} > {heading_title}",
                    url=url,
                )
            )

    return chunks


def parse_atproto_website(config: Config) -> list[ContentChunk]:
    """Parse the atproto-website repo (atproto.com MDX content)."""
    repo_dir = config.repos_dir / "atproto-website"
    chunks: list[ContentChunk] = []

    content_dirs = [
        repo_dir / "src" / "app",
        repo_dir / "src" / "mdx",
        repo_dir / "content",
        repo_dir / "docs",
    ]

    mdx_files: list[Path] = []
    for content_dir in content_dirs:
        if content_dir.exists():
            mdx_files.extend(content_dir.rglob("*.mdx"))
            mdx_files.extend(content_dir.rglob("*.md"))

    for pattern in ["*.mdx", "*.md"]:
        mdx_files.extend(repo_dir.glob(pattern))

    seen: set[Path] = set()
    for mdx_file in mdx_files:
        if mdx_file in seen:
            continue
        seen.add(mdx_file)

        try:
            raw = mdx_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            logger.warning("Could not read %s", mdx_file)
            continue

        fm = _extract_frontmatter(raw)
        title = fm.get("title", mdx_file.stem.replace("-", " ").title())
        rel_path = str(mdx_file.relative_to(repo_dir))

        url = _atproto_website_url(rel_path)

        cleaned = _strip_mdx(raw)
        if len(cleaned) < 50:
            continue

        file_chunks = _chunk_by_headings(
            cleaned, rel_path, SOURCE_ATPROTO_WEBSITE, title, url
        )
        chunks.extend(file_chunks)

    logger.info(
        "Parsed %d chunks from atproto-website (%d files)", len(chunks), len(seen)
    )
    return chunks


def _atproto_website_url(rel_path: str) -> str:
    """Reconstruct atproto.com URL from a file path."""
    # e.g. src/app/en/guides/overview.mdx → https://atproto.com/guides/overview
    path = rel_path.replace("src/app/", "").replace("src/mdx/", "")
    path = re.sub(r"^[a-z]{2}/", "", path)
    path = re.sub(r"\.(mdx|md)$", "", path)
    path = re.sub(r"/(index|page)$", "", path)
    return f"https://atproto.com/{path}"


def parse_bsky_docs(config: Config) -> list[ContentChunk]:
    """Parse the bsky-docs repo (docs.bsky.app Docusaurus content)."""
    repo_dir = config.repos_dir / "bsky-docs"
    chunks: list[ContentChunk] = []

    docs_dir = repo_dir / "docs"
    blog_dir = repo_dir / "blog"

    # Collect MDX/MD files from docs/ (excluding auto-generated API docs)
    mdx_files: list[Path] = []
    for search_dir in [docs_dir, blog_dir]:
        if search_dir.exists():
            for f in search_dir.rglob("*.mdx"):
                # Skip auto-generated API reference — redundant with raw lexicons
                if "/api/" not in str(f):
                    mdx_files.append(f)
            for f in search_dir.rglob("*.md"):
                if "/api/" not in str(f):
                    mdx_files.append(f)

    for mdx_file in mdx_files:
        try:
            raw = mdx_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            logger.warning("Could not read %s", mdx_file)
            continue

        fm = _extract_frontmatter(raw)
        title = fm.get("title", mdx_file.stem.replace("-", " ").title())
        rel_path = str(mdx_file.relative_to(repo_dir))

        url = _bsky_docs_url(rel_path)
        cleaned = _strip_mdx(raw)
        if len(cleaned) < 50:
            continue

        file_chunks = _chunk_by_headings(
            cleaned, rel_path, SOURCE_BSKY_DOCS, title, url
        )
        chunks.extend(file_chunks)

    logger.info("Parsed %d chunks from bsky-docs (%d files)", len(chunks), len(mdx_files))
    return chunks


def _bsky_docs_url(rel_path: str) -> str:
    """Reconstruct docs.bsky.app URL from a file path."""
    # docs/advanced-guides/firehose.mdx → https://docs.bsky.app/docs/advanced-guides/firehose
    path = re.sub(r"\.(mdx|md)$", "", rel_path)
    path = re.sub(r"/index$", "", path)
    return f"https://docs.bsky.app/{path}"


def parse_lexicons(config: Config) -> list[ContentChunk]:
    """Parse AT Protocol lexicon JSON files from the atproto repo."""
    repo_dir = config.repos_dir / "atproto"
    lexicons_dir = repo_dir / "lexicons"
    chunks: list[ContentChunk] = []

    if not lexicons_dir.exists():
        logger.warning("Lexicons directory not found at %s", lexicons_dir)
        return chunks

    for json_file in sorted(lexicons_dir.rglob("*.json")):
        try:
            raw = json_file.read_text(encoding="utf-8")
            lexicon = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            logger.warning("Could not parse lexicon %s", json_file)
            continue

        nsid = lexicon.get("id", "")
        if not nsid:
            continue

        rel_path = str(json_file.relative_to(repo_dir))
        text = _format_lexicon(lexicon)
        title = nsid

        chunks.append(
            ContentChunk(
                text=text,
                source=SOURCE_LEXICONS,
                file_path=rel_path,
                title=title,
                nsid=nsid,
                url=f"https://github.com/bluesky-social/atproto/blob/main/{rel_path}",
                metadata={"raw_json": raw},
            )
        )

    logger.info("Parsed %d lexicons", len(chunks))
    return chunks


def _format_lexicon(lexicon: dict) -> str:  # type: ignore[type-arg]
    """Format a lexicon JSON into a readable text representation."""
    nsid = lexicon.get("id", "unknown")
    defs = lexicon.get("defs", {})
    main_def = defs.get("main", {})

    lines = [f"# Lexicon: {nsid}"]
    lines.append(f"Type: {main_def.get('type', 'unknown')}")

    description = main_def.get("description", "")
    if description:
        lines.append(f"Description: {description}")

    def_type = main_def.get("type", "")

    if def_type == "record":
        record = main_def.get("record", {})
        _format_object_type(record, lines, indent=0)
    elif def_type in ("query", "procedure"):
        # Parameters
        params = main_def.get("parameters", {})
        if params:
            lines.append("\nParameters:")
            _format_object_type(params, lines, indent=1)
        # Input
        input_schema = main_def.get("input", {})
        if input_schema:
            lines.append("\nInput:")
            encoding = input_schema.get("encoding", "")
            if encoding:
                lines.append(f"  Encoding: {encoding}")
            schema = input_schema.get("schema", {})
            if schema:
                _format_object_type(schema, lines, indent=1)
        # Output
        output_schema = main_def.get("output", {})
        if output_schema:
            lines.append("\nOutput:")
            encoding = output_schema.get("encoding", "")
            if encoding:
                lines.append(f"  Encoding: {encoding}")
            schema = output_schema.get("schema", {})
            if schema:
                _format_object_type(schema, lines, indent=1)
        # Errors
        errors = main_def.get("errors", [])
        if errors:
            lines.append("\nErrors:")
            for err in errors:
                err_name = err.get("name", "unknown")
                err_desc = err.get("description", "")
                lines.append(f"  - {err_name}: {err_desc}")
    elif def_type == "subscription":
        message = main_def.get("message", {})
        if message:
            lines.append(f"\nMessage schema: {message.get('schema', {}).get('type', 'unknown')}")

    # Named sub-definitions
    for def_name, def_value in defs.items():
        if def_name == "main":
            continue
        lines.append(f"\n## {nsid}#{def_name}")
        def_desc = def_value.get("description", "")
        if def_desc:
            lines.append(f"Description: {def_desc}")
        lines.append(f"Type: {def_value.get('type', 'unknown')}")
        if def_value.get("type") == "object":
            _format_object_type(def_value, lines, indent=1)

    return "\n".join(lines)


def _format_object_type(
    schema: dict,  # type: ignore[type-arg]
    lines: list[str],
    indent: int = 0,
) -> None:
    """Format an object type schema into readable text lines."""
    prefix = "  " * indent
    required = schema.get("required", [])
    properties = schema.get("properties", {})

    if required:
        lines.append(f"{prefix}Required: {', '.join(required)}")

    for prop_name, prop_def in properties.items():
        prop_type = prop_def.get("type", "")
        prop_desc = prop_def.get("description", "")
        ref = prop_def.get("ref", "")
        refs = prop_def.get("refs", [])

        type_str = prop_type or ref or (f"union[{', '.join(refs)}]" if refs else "unknown")
        req_mark = "*" if prop_name in required else ""
        desc_str = f" — {prop_desc}" if prop_desc else ""

        constraints: list[str] = []
        for key in ["maxLength", "maxGraphemes", "minimum", "maximum", "format", "default"]:
            if key in prop_def:
                constraints.append(f"{key}={prop_def[key]}")
        constraint_str = f" ({', '.join(constraints)})" if constraints else ""

        lines.append(f"{prefix}  {prop_name}{req_mark}: {type_str}{constraint_str}{desc_str}")


def parse_cookbook(config: Config) -> list[ContentChunk]:
    """Parse the cookbook repo — one chunk per example project."""
    repo_dir = config.repos_dir / "cookbook"
    chunks: list[ContentChunk] = []

    if not repo_dir.exists():
        logger.warning("Cookbook directory not found at %s", repo_dir)
        return chunks

    # Each top-level directory with a README is a cookbook example
    for item in sorted(repo_dir.iterdir()):
        if not item.is_dir() or item.name.startswith("."):
            continue

        readme = _find_readme(item)
        if not readme:
            continue

        try:
            readme_text = readme.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        project_name = item.name
        title = f"Cookbook: {project_name}"
        language = _detect_language(item)

        source_files = _list_source_files(item)
        file_listing = "\n".join(f"  - {f}" for f in source_files[:30])

        text = f"# {title}\n"
        text += f"Language: {language}\n"
        text += f"URL: https://github.com/bluesky-social/cookbook/tree/main/{project_name}\n\n"
        if file_listing:
            text += f"Files:\n{file_listing}\n\n"
        text += readme_text

        # Also include key source file contents (small files only)
        for src_file in source_files[:5]:
            src_path = item / src_file
            if src_path.stat().st_size < 10000:  # < 10KB
                try:
                    src_content = src_path.read_text(encoding="utf-8", errors="replace")
                    text += f"\n\n--- {src_file} ---\n{src_content}"
                except OSError:
                    pass

        chunks.append(
            ContentChunk(
                text=text,
                source=SOURCE_COOKBOOK,
                file_path=project_name,
                title=title,
                language=language,
                url=f"https://github.com/bluesky-social/cookbook/tree/main/{project_name}",
            )
        )

    logger.info("Parsed %d cookbook examples", len(chunks))
    return chunks


def _find_readme(directory: Path) -> Path | None:
    """Find a README file in a directory (case-insensitive)."""
    for name in ["README.md", "readme.md", "README.MD", "README", "readme"]:
        path = directory / name
        if path.exists():
            return path
    return None


def _detect_language(project_dir: Path) -> str:
    """Detect the primary programming language of a cookbook project."""
    extensions: dict[str, str] = {
        ".py": "python",
        ".go": "go",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".jsx": "javascript",
        ".rs": "rust",
        ".swift": "swift",
        ".kt": "kotlin",
    }
    counts: dict[str, int] = {}
    for f in project_dir.rglob("*"):
        if f.is_file() and f.suffix in extensions:
            lang = extensions[f.suffix]
            counts[lang] = counts.get(lang, 0) + 1

    if not counts:
        return "unknown"
    return max(counts, key=counts.get)  # type: ignore[arg-type]


def _list_source_files(project_dir: Path) -> list[str]:
    """List relevant source files in a cookbook project (excluding deps/build)."""
    skip_dirs = {
        "node_modules",
        "__pycache__",
        ".git",
        "vendor",
        "dist",
        "build",
        ".next",
        "venv",
        ".venv",
    }
    source_extensions = {
        ".py", ".go", ".ts", ".tsx", ".js", ".jsx", ".rs", ".swift",
        ".kt", ".json", ".yaml", ".yml", ".toml", ".html", ".css",
        ".md", ".mdx",
    }
    files: list[str] = []
    for f in sorted(project_dir.rglob("*")):
        if f.is_file() and not any(d in f.parts for d in skip_dirs):
            if f.suffix in source_extensions:
                files.append(str(f.relative_to(project_dir)))
    return files


def parse_all(config: Config) -> list[ContentChunk]:
    """Parse all content sources and return combined chunks."""
    chunks: list[ContentChunk] = []

    parsers = [
        ("atproto-website", parse_atproto_website),
        ("bsky-docs", parse_bsky_docs),
        ("lexicons", parse_lexicons),
        ("cookbook", parse_cookbook),
    ]

    for name, parser_fn in parsers:
        try:
            result = parser_fn(config)
            chunks.extend(result)
            logger.info("Source '%s': %d chunks", name, len(result))
        except Exception:
            logger.error("Failed to parse source '%s'", name, exc_info=True)

    logger.info("Total chunks parsed: %d", len(chunks))
    return chunks
