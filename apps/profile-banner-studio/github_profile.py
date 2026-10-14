"""Read public profile details from the GitHub API to prefill the banner form."""

import os
import re
from collections import Counter

import requests

API = "https://api.github.com"
HANDLE_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")


class GitHubLookupError(RuntimeError):
    pass


def _headers() -> dict:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-banner-studio"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _get(path: str, **params):
    try:
        resp = requests.get(f"{API}{path}", headers=_headers(), params=params, timeout=15)
    except requests.RequestException as exc:
        raise GitHubLookupError(f"Could not reach GitHub: {exc}") from exc
    if resp.status_code == 404:
        raise GitHubLookupError("No GitHub user with that handle.")
    if resp.status_code in (403, 429):
        raise GitHubLookupError("GitHub rate limit reached. Set GITHUB_TOKEN or try again later.")
    if not resp.ok:
        raise GitHubLookupError(f"GitHub returned {resp.status_code}.")
    return resp.json()


def lookup_profile(handle: str, max_languages: int = 4) -> dict:
    """Return name, bio and the most-used languages of a user's public, non-fork repos."""
    handle = handle.strip().lstrip("@")
    if not HANDLE_RE.match(handle):
        raise GitHubLookupError("That does not look like a valid GitHub handle.")
    user = _get(f"/users/{handle}")
    repos = _get(f"/users/{handle}/repos", sort="updated", per_page=50, type="owner")
    counts = Counter(r["language"] for r in repos if r.get("language") and not r.get("fork"))
    return {
        "handle": user["login"],
        "name": user.get("name") or user["login"],
        "bio": user.get("bio") or "",
        "languages": [lang for lang, _ in counts.most_common(max_languages)],
    }
