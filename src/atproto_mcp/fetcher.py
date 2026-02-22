"""Git-based content fetcher for AT Protocol repositories."""

import json
import logging
import time
from pathlib import Path

import git

from atproto_mcp.config import REPOS, Config

logger = logging.getLogger(__name__)


def _repo_path(config: Config, repo_name: str) -> Path:
    """Return the local filesystem path for a cloned repository."""
    return config.repos_dir / repo_name


def _meta_path(config: Config, repo_name: str) -> Path:
    """Return the metadata JSON path tracking clone timestamps and SHAs."""
    return config.meta_dir / f"{repo_name}.json"


def _read_meta(config: Config, repo_name: str) -> dict[str, object]:
    """Read repo metadata (last_fetched, sha) from disk."""
    path = _meta_path(config, repo_name)
    if path.exists():
        with open(path) as fh:
            return json.load(fh)  # type: ignore[no-any-return]
    return {}


def _write_meta(config: Config, repo_name: str, sha: str) -> None:
    """Persist repo metadata after a successful fetch."""
    config.meta_dir.mkdir(parents=True, exist_ok=True)
    path = _meta_path(config, repo_name)
    payload = {"sha": sha, "last_fetched": time.time()}
    with open(path, "w") as fh:
        json.dump(payload, fh)


def _is_stale(config: Config, repo_name: str) -> bool:
    """Check whether a repo's local clone is older than the refresh threshold."""
    meta = _read_meta(config, repo_name)
    last_fetched = meta.get("last_fetched")
    if last_fetched is None:
        return True
    age_hours = (time.time() - float(str(last_fetched))) / 3600
    return age_hours >= config.refresh_hours


def _clone_repo(
    config: Config,
    repo_name: str,
    repo_info: dict[str, str | list[str]],
    *,
    force: bool = False,
) -> str:
    """Clone or update a single repository. Returns the HEAD SHA."""
    dest = _repo_path(config, repo_name)
    branch = str(repo_info.get("branch", "main"))
    url = str(repo_info["url"])
    sparse_paths: list[str] | None = repo_info.get("sparse_paths")  # type: ignore[assignment]

    if dest.exists() and not force and not _is_stale(config, repo_name):
        # Already fresh — return cached SHA
        meta = _read_meta(config, repo_name)
        cached_sha = meta.get("sha", "unknown")
        logger.info("Repo %s is fresh (sha=%s), skipping fetch", repo_name, cached_sha)
        return str(cached_sha)

    config.repos_dir.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        logger.info("Updating repo %s from %s", repo_name, url)
        try:
            repo = git.Repo(dest)
            origin = repo.remotes.origin
            origin.fetch(depth=1)
            repo.git.reset("--hard", f"origin/{branch}")
            sha = repo.head.commit.hexsha
            _write_meta(config, repo_name, sha)
            logger.info("Updated %s to %s", repo_name, sha)
            return sha
        except git.GitCommandError:
            logger.warning("Failed to update %s, re-cloning", repo_name, exc_info=True)
            import shutil

            shutil.rmtree(dest, ignore_errors=True)

    logger.info("Cloning %s from %s (branch=%s)", repo_name, url, branch)

    if sparse_paths:
        # Sparse checkout — only fetch specific directories
        repo = git.Repo.init(dest)
        repo.git.remote("add", "origin", url)
        repo.git.config("core.sparseCheckout", "true")

        sparse_file = dest / ".git" / "info" / "sparse-checkout"
        sparse_file.parent.mkdir(parents=True, exist_ok=True)
        sparse_file.write_text("\n".join(sparse_paths) + "\n")

        repo.git.fetch("origin", branch, depth=1)
        repo.git.checkout(f"origin/{branch}", b=branch)
    else:
        repo = git.Repo.clone_from(
            url,
            dest,
            branch=branch,
            depth=1,
            single_branch=True,
        )

    sha = repo.head.commit.hexsha
    _write_meta(config, repo_name, sha)
    logger.info("Cloned %s at %s", repo_name, sha)
    return sha


def fetch_all(config: Config, *, force: bool = False) -> dict[str, str]:
    """Clone or update all configured repositories.

    Returns a mapping of repo_name → HEAD SHA.
    """
    results: dict[str, str] = {}
    for repo_name, repo_info in REPOS.items():
        try:
            sha = _clone_repo(config, repo_name, repo_info, force=force)
            results[repo_name] = sha
        except Exception:
            logger.error("Failed to fetch repo %s", repo_name, exc_info=True)
            results[repo_name] = "error"
    return results


def get_cached_shas(config: Config) -> dict[str, str]:
    """Get the cached HEAD SHAs for all repos without hitting the network."""
    shas: dict[str, str] = {}
    for repo_name in REPOS:
        meta = _read_meta(config, repo_name)
        shas[repo_name] = str(meta.get("sha", "unknown"))
    return shas


def needs_reindex(config: Config, old_shas: dict[str, str]) -> bool:
    """Check if any repo SHAs have changed since last index build."""
    current = get_cached_shas(config)
    return current != old_shas
