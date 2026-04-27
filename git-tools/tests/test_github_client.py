"""Tests for lib/github_client.py (load_config, error checkers) and
lib/prs.py (get_repo_full_name URL parsing)."""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

import github_client
from github_client import load_config, _check_http, _check_graphql_errors
from prs import get_repo_full_name


# ── load_config ────────────────────────────────────────────────────────────────

class TestLoadConfig:
    def test_returns_defaults_when_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(github_client, "_CONFIG_PATH", tmp_path / "missing.json")
        result = load_config()
        assert result["owner"] == "AndresI19"
        assert result["project_number"] == 5
        assert "repo" in result

    def test_file_overrides_defaults(self, tmp_path, monkeypatch):
        cfg = tmp_path / ".config"
        cfg.write_text(json.dumps({"owner": "OtherUser", "project_number": 99}))
        monkeypatch.setattr(github_client, "_CONFIG_PATH", cfg)
        result = load_config()
        assert result["owner"] == "OtherUser"
        assert result["project_number"] == 99

    def test_file_preserves_unspecified_defaults(self, tmp_path, monkeypatch):
        cfg = tmp_path / ".config"
        cfg.write_text(json.dumps({"project_number": 42}))
        monkeypatch.setattr(github_client, "_CONFIG_PATH", cfg)
        result = load_config()
        assert result["project_number"] == 42
        assert result["owner"] == "AndresI19"       # untouched default
        assert result["repo"] == "AndresI19/RS-Agent-Planning"

    def test_empty_file_uses_all_defaults(self, tmp_path, monkeypatch):
        cfg = tmp_path / ".config"
        cfg.write_text("{}")
        monkeypatch.setattr(github_client, "_CONFIG_PATH", cfg)
        result = load_config()
        assert result["owner"] == "AndresI19"
        assert result["project_number"] == 5

    def test_returns_dict_with_required_keys(self, tmp_path, monkeypatch):
        monkeypatch.setattr(github_client, "_CONFIG_PATH", tmp_path / "missing.json")
        result = load_config()
        assert {"owner", "project_number", "repo"} <= result.keys()


# ── _check_http ────────────────────────────────────────────────────────────────

def _make_response(status_code, body=None, headers=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = status_code < 400
    resp.headers = headers or {}
    resp.request = MagicMock(method="GET")
    resp.url = "https://api.github.com/test"
    resp.text = body or ""
    if body and body.startswith("{"):
        try:
            resp.json.return_value = json.loads(body)
        except json.JSONDecodeError:
            resp.json.side_effect = ValueError
    else:
        resp.json.side_effect = ValueError
    return resp


class TestCheckHttp:
    def test_200_passes_silently(self):
        _check_http(_make_response(200))  # must not raise

    def test_204_passes_silently(self):
        _check_http(_make_response(204))

    def test_401_exits(self):
        with pytest.raises(SystemExit):
            _check_http(_make_response(401))

    def test_403_exits(self):
        with pytest.raises(SystemExit):
            _check_http(_make_response(403))

    def test_404_exits(self):
        with pytest.raises(SystemExit):
            _check_http(_make_response(404, body='{"message": "Not Found"}'))

    def test_500_exits(self):
        with pytest.raises(SystemExit):
            _check_http(_make_response(500))

    def test_403_prints_scopes_when_present(self, capsys):
        resp = _make_response(403, headers={"X-OAuth-Scopes": "repo,read:org"})
        with pytest.raises(SystemExit):
            _check_http(resp)
        assert "scopes: repo,read:org" in capsys.readouterr().out

    def test_403_no_scopes_header_still_exits(self, capsys):
        resp = _make_response(403)
        with pytest.raises(SystemExit):
            _check_http(resp)
        out = capsys.readouterr().out
        assert "Insufficient" in out


# ── _check_graphql_errors ──────────────────────────────────────────────────────

class TestCheckGraphqlErrors:
    def test_unauthorized_type_exits(self):
        with pytest.raises(SystemExit):
            _check_graphql_errors([{"type": "UNAUTHORIZED", "message": "Bad credentials"}])

    def test_bad_credentials_in_message_exits(self):
        with pytest.raises(SystemExit):
            _check_graphql_errors([{"message": "bad credentials for user"}])

    def test_forbidden_type_exits(self):
        with pytest.raises(SystemExit):
            _check_graphql_errors([{"type": "FORBIDDEN", "message": "Not allowed"}])

    def test_generic_error_exits(self):
        with pytest.raises(SystemExit):
            _check_graphql_errors([{"message": "Some other GraphQL error"}])

    def test_unauthorized_prints_token_hint(self, capsys):
        with pytest.raises(SystemExit):
            _check_graphql_errors([{"type": "UNAUTHORIZED", "message": "Bad credentials"}])
        assert "invalid or has expired" in capsys.readouterr().out

    def test_multiple_errors_all_reported(self, capsys):
        errors = [{"message": "Error one"}, {"message": "Error two"}]
        with pytest.raises(SystemExit):
            _check_graphql_errors(errors)
        out = capsys.readouterr().out
        assert "Error one" in out
        assert "Error two" in out


# ── get_repo_full_name (prs.py) ────────────────────────────────────────────────

class TestGetRepoFullName:
    def _mock_run(self, url, returncode=0):
        result = MagicMock()
        result.returncode = returncode
        result.stdout = url + "\n"
        return result

    @patch("prs.subprocess.run")
    def test_ssh_url_with_dot_git(self, mock_run):
        mock_run.return_value = self._mock_run("git@github.com:AndresI19/RS-Agent-Planning.git")
        assert get_repo_full_name(Path("/fake/repo")) == "AndresI19/RS-Agent-Planning"

    @patch("prs.subprocess.run")
    def test_https_url_with_dot_git(self, mock_run):
        mock_run.return_value = self._mock_run("https://github.com/AndresI19/RS-Agent-Planning.git")
        assert get_repo_full_name(Path("/fake/repo")) == "AndresI19/RS-Agent-Planning"

    @patch("prs.subprocess.run")
    def test_https_url_without_dot_git(self, mock_run):
        mock_run.return_value = self._mock_run("https://github.com/AndresI19/RS-Agent-Planning")
        assert get_repo_full_name(Path("/fake/repo")) == "AndresI19/RS-Agent-Planning"

    @patch("prs.subprocess.run")
    def test_non_github_url_returns_none(self, mock_run):
        mock_run.return_value = self._mock_run("https://gitlab.com/user/repo.git")
        assert get_repo_full_name(Path("/fake/repo")) is None

    @patch("prs.subprocess.run")
    def test_failed_git_command_returns_none(self, mock_run):
        mock_run.return_value = self._mock_run("", returncode=128)
        assert get_repo_full_name(Path("/fake/repo")) is None

    @patch("prs.subprocess.run")
    def test_org_repo_name_preserved(self, mock_run):
        mock_run.return_value = self._mock_run("git@github.com:some-org/my-repo.git")
        assert get_repo_full_name(Path("/fake/repo")) == "some-org/my-repo"
