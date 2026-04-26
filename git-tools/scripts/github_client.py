#!/usr/bin/env python3
"""
github_client.py — Token management CLI for the GitHub API client.

Usage:
    python3 github_client.py --set-token   # store a new PAT in the system keyring
    python3 github_client.py --status      # show current token status and scopes
"""
import argparse
import getpass
import os
import sys

import keyring
import requests

LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")
sys.path.insert(0, LIB)
import github_client as _lib


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
            f"{_lib.REST_BASE}/user",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            timeout=10,
        )
        if resp.status_code == 401:
            print("ERROR: token is invalid or expired — not stored")
            sys.exit(1)
        keyring.set_password(_lib.KEYRING_SERVICE, _lib.KEYRING_USER, token)
        login  = resp.json().get("login", "?")
        scopes = resp.headers.get("X-OAuth-Scopes", "")
        scope_display = scopes if scopes else "fine-grained PAT (scopes not advertised)"
        print(f"Token stored. User: {login} | Scopes: {scope_display}")
        if scopes and "project" not in scopes:
            print("WARNING: 'project' scope missing — GitHub Projects V2 mutations will fail.")
        return

    scopes = _lib.token_scopes()
    scope_display = scopes if scopes else "fine-grained PAT (scopes not advertised)"
    print(f"Token OK | Scopes: {scope_display}")


if __name__ == "__main__":
    main()
