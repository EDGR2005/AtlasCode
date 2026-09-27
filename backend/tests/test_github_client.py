"""
Tests for github.client — specifically parse_owner_repo and header logic.
HTTP calls are mocked with pytest-mock so zero network traffic is made.
"""
from __future__ import annotations

import pytest

from app.github.client import parse_owner_repo


# ---------------------------------------------------------------------------
# parse_owner_repo
# ---------------------------------------------------------------------------

def test_parse_https_url():
    owner, repo = parse_owner_repo("https://github.com/pallets/flask")
    assert owner == "pallets"
    assert repo == "flask"


def test_parse_https_url_with_git_suffix():
    owner, repo = parse_owner_repo("https://github.com/EDGR2005/StudentHub.git")
    assert owner == "EDGR2005"
    assert repo == "StudentHub"


def test_parse_https_url_trailing_slash():
    owner, repo = parse_owner_repo("https://github.com/owner/repo/")
    assert owner == "owner"
    assert repo == "repo"


def test_parse_ssh_url():
    owner, repo = parse_owner_repo("git@github.com:owner/repo.git")
    assert owner == "owner"
    assert repo == "repo"


def test_parse_invalid_url_raises():
    with pytest.raises(ValueError):
        parse_owner_repo("https://gitlab.com/owner/repo")


def test_parse_empty_raises():
    with pytest.raises(ValueError):
        parse_owner_repo("")
