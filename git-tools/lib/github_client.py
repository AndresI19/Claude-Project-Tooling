#!/usr/bin/env python3
"""
github_client.py — Authenticated GitHub API client (REST + GraphQL).
Pure library — no CLI. Token management lives in scripts/github_client.py.

Token resolution order:
  1. GH_TOKEN environment variable
  2. System keyring (GNOME Keyring / SecretService)
  3. gh CLI managed token (local dev fallback)
"""
import fcntl
import json
import os
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

import keyring
import requests

_LOCK_PATH = "/tmp/.gh-api.lock"


@contextmanager
def _api_lock():
    """Serialize concurrent GitHub API calls across processes via flock.

    Multiple scripts (or parallel tool invocations) hitting api.github.com at the
    same moment race on DNS resolution and can pile up against rate limits. A
    single flock-protected critical section turns those concurrent calls into a
    queue, making each call deterministic without needing retry logic.
    """
    with open(_LOCK_PATH, "w") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

_CONFIG_PATH = Path(__file__).parent.parent.parent / "resources" / ".config"


def load_config():
    """Load workspace defaults from resources/.config.

    Returns a dict with keys: owner, project_number, repo.
    Falls back to hardcoded defaults if the file is missing.
    """
    defaults = {"owner": "AndresI19", "project_number": 5, "repo": "AndresI19/RS-Agent-Planning"}
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH) as f:
            return {**defaults, **json.load(f)}
    return defaults

KEYRING_SERVICE = "rs-agent-planning"
KEYRING_USER    = "github_pat"
GRAPHQL_URL     = "https://api.github.com/graphql"
REST_BASE       = "https://api.github.com"


def get_token():
    token = os.environ.get("GH_TOKEN") or keyring.get_password(KEYRING_SERVICE, KEYRING_USER)
    if not token:
        try:
            result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
            if result.returncode == 0:
                token = result.stdout.strip()
        except FileNotFoundError:
            pass
    if not token:
        print("ERROR: GitHub token not found.")
        print("  Option 1: python3 scripts/github_client.py --set-token")
        print("  Option 2: gh auth login")
        print("  CI:        set the GH_TOKEN environment variable")
        sys.exit(1)
    return token


def _headers():
    return {
        "Authorization": f"Bearer {get_token()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _check_http(resp):
    if resp.status_code == 401:
        print("ERROR: GitHub token is invalid or has expired.")
        print("  Run: python3 scripts/github_client.py --set-token")
        sys.exit(1)
    if resp.status_code == 403:
        scopes = resp.headers.get("X-OAuth-Scopes", "")
        detail = f" (scopes: {scopes})" if scopes else ""
        print(f"ERROR: Insufficient token permissions{detail}.")
        print("  Ensure the token has 'repo' and 'project' access.")
        sys.exit(1)
    if not resp.ok:
        print(f"ERROR: GitHub API {resp.status_code} — {resp.request.method} {resp.url}")
        try:
            print(f"  {resp.json().get('message', resp.text[:300])}")
        except Exception:
            print(f"  {resp.text[:300]}")
        sys.exit(1)


def _check_graphql_errors(errors):
    for err in errors:
        err_type = err.get("type", "")
        msg      = err.get("message", "").lower()
        if err_type == "UNAUTHORIZED" or "bad credentials" in msg:
            print("ERROR: GitHub token is invalid or has expired.")
            print("  Run: python3 scripts/github_client.py --set-token")
            sys.exit(1)
        if err_type == "FORBIDDEN":
            print(f"ERROR: Insufficient token permissions — {err.get('message', '')}")
            sys.exit(1)
    print("ERROR: GitHub GraphQL errors:")
    for err in errors:
        print(f"  {err.get('message', err)}")
    sys.exit(1)


def graphql(query, variables=None):
    """Execute a GraphQL query or mutation. Returns the full response dict."""
    with _api_lock():
        resp = requests.post(
            GRAPHQL_URL,
            headers={**_headers(), "Content-Type": "application/json"},
            json={"query": query, "variables": variables or {}},
            timeout=30,
        )
    _check_http(resp)
    data = resp.json()
    if "errors" in data:
        _check_graphql_errors(data["errors"])
    return data


def rest(method, path, **kwargs):
    """Make a GitHub REST API call. Returns parsed JSON (or {} for 204 No Content)."""
    with _api_lock():
        resp = requests.request(
            method,
            f"{REST_BASE}{path}",
            headers=_headers(),
            timeout=30,
            **kwargs,
        )
    _check_http(resp)
    return {} if resp.status_code == 204 else resp.json()


def token_scopes():
    """Return the X-OAuth-Scopes header value, or '' for fine-grained PATs."""
    with _api_lock():
        resp = requests.get(f"{REST_BASE}/user", headers=_headers(), timeout=10)
    _check_http(resp)
    return resp.headers.get("X-OAuth-Scopes", "")
