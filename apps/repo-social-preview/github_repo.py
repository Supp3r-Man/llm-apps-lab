"""Read a public repository's details from the GitHub API."""

import os
import re
from urllib.parse import urlparse

import requests

API = "https://api.github.com"
PART_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


class RepoLookupError(RuntimeError):
    pass


def parse_repo(text: str) -> tuple[str, str]:
    """Accept 'owner/name' or a github.com URL and return (owner, name)."""
    text = text.strip()
    if "github.com" in text:
        path = urlparse(text if "//" in text else f"https://{text}").path
        parts = [p for p in path.split("/") if p]
    else:
        parts = [p for p in text.split("/") if p]
    if len(parts) < 2:
        raise RepoLookupError("Enter a repository as owner/name or a github.com URL.")
    owner, name = parts[0], parts[1].removesuffix(".git")
    if not (PART_RE.match(owner) and PART_RE.match(name)):
        raise RepoLookupError("That does not look like a valid repository name.")
    return owner, name


def _headers(raw: bool = False) -> dict:
    headers = {
        "Accept": "application/vnd.github.raw+json" if raw else "application/vnd.github+json",
        "User-Agent": "repo-social-preview",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def clean_readme(markdown: str, limit: int = 1200) -> str:
    """Reduce a README to plain prose so it is useful as context and short."""
    text = re.sub(r"```.*?```", " ", markdown, flags=re.S)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)  # images and badges
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # links keep their label
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"^[#>*\-\s|]+", "", text, flags=re.M)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def fetch_repo(owner: str, name: str) -> dict:
    try:
        resp = requests.get(f"{API}/repos/{owner}/{name}", headers=_headers(), timeout=15)
        if resp.status_code == 404:
            raise RepoLookupError("Repository not found. Is it public?")
        if resp.status_code in (403, 429):
            raise RepoLookupError("GitHub rate limit reached. Set GITHUB_TOKEN or try again later.")
        if not resp.ok:
            raise RepoLookupError(f"GitHub returned {resp.status_code}.")
        repo = resp.json()
        readme_resp = requests.get(f"{API}/repos/{owner}/{name}/readme", headers=_headers(raw=True), timeout=15)
    except requests.RequestException as exc:
        raise RepoLookupError(f"Could not reach GitHub: {exc}") from exc
    readme = clean_readme(readme_resp.text) if readme_resp.ok else ""
    return {
        "full_name": repo["full_name"],
        "name": repo["name"],
        "description": repo.get("description") or "",
        "language": repo.get("language") or "",
        "topics": repo.get("topics") or [],
        "stars": repo.get("stargazers_count", 0),
        "readme_excerpt": readme,
    }
