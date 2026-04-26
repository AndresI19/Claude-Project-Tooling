#!/usr/bin/env python3
"""
github_client.py — Authenticated GitHub API client (REST + GraphQL).

Token resolution order:
  1. GH_TOKEN environment variable  (GitHub Actions / CI)
  2. System keyring                  (local development — SecretService/GNOME Keyring)

Manage the local token:
    python3 github_client.py --set-token
    python3 github_client.py --status

On 401 responses, all callers exit with a clear message directing the user to --set-token.
Fine-grained PATs (github_pat_*) do not advertise OAuth scopes — scope checks are skipped
for these tokens and permission errors surface as 403s at call time instead.
"""

import argparse
import getpass
import os
import subprocess
import sys

import keyring
import requests

KEYRING_SERVICE = "rs-agent-planning"
KEYRING_USER    = "github_pat"
GRAPHQL_URL     = "https://api.github.com/graphql"
REST_BASE       = "https://api.github.com"


def get_token():
    """Return a GitHub token. Resolution order:
      1. GH_TOKEN env var      — GitHub Actions / CI
      2. System keyring        — stored via --set-token
      3. gh auth token         — reuse the gh CLI's managed OAuth token (local dev)
    """
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
        print("  Option 1: python3 github_client.py --set-token  (store a PAT in keyring)")
        print("  Option 2: gh auth login                          (authenticate via gh CLI)")
        print("  CI:        set the GH_TOKEN / PROJECT_TOKEN secret")
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
        print("  Run: python3 github_client.py --set-token")
        sys.exit(1)
    if resp.status_code == 403:
        scopes = resp.headers.get("X-OAuth-Scopes", "")
        detail = f" (scopes: {scopes})" if scopes else ""
        print(f"ERROR: Insufficient token permissions{detail}.")
        print("  Ensure the token has 'repo' and 'project' access, then re-run --set-token.")
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
            print("  Run: python3 github_client.py --set-token")
            sys.exit(1)
        if err_type == "FORBIDDEN":
            print(f"ERROR: Insufficient token permissions — {err.get('message', '')}")
            print("  Ensure the token has 'repo' and 'project' access, then re-run --set-token.")
            sys.exit(1)
    print("ERROR: GitHub GraphQL errors:")
    for err in errors:
        print(f"  {err.get('message', err)}")
    sys.exit(1)


def graphql(query, variables=None):
    """Execute a GraphQL query or mutation. Returns the full response dict."""
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
    """Return the X-OAuth-Scopes header for the current token, or '' for fine-grained PATs."""
    resp = requests.get(f"{REST_BASE}/user", headers=_headers(), timeout=10)
    _check_http(resp)
    return resp.headers.get("X-OAuth-Scopes", "")


def main():
    parser = argparse.ArgumentParser(description="Manage the GitHub API token")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--set-token", action="store_true", help="Store a new PAT in the keyring")
    group.add_argument("--status",    action="store_true", help="Show current token status")
    args = parser.parse_args()

    if args.set_token:
        token = getpass.getpass("GitHub PAT: ").strip()
        if not token:
            print("ERROR: empty token")
            sys.exit(1)
        resp = requests.get(
            f"{REST_BASE}/user",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            timeout=10,
        )
        if resp.status_code == 401:
            print("ERROR: token is invalid or expired — not stored")
            sys.exit(1)
        keyring.set_password(KEYRING_SERVICE, KEYRING_USER, token)
        login  = resp.json().get("login", "?")
        scopes = resp.headers.get("X-OAuth-Scopes", "")
        scope_display = scopes if scopes else "fine-grained PAT (scopes not advertised)"
        print(f"Token stored. User: {login} | Scopes: {scope_display}")
        if scopes and "project" not in scopes:
            print("WARNING: 'project' scope missing — GitHub Projects V2 mutations will fail.")
        return

    scopes = token_scopes()
    scope_display = scopes if scopes else "fine-grained PAT (scopes not advertised)"
    print(f"Token OK | Scopes: {scope_display}")


if __name__ == "__main__":
    main()
