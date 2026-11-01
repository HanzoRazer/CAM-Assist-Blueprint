"""Resolve pull-request reviews from a GitHub API client.

Candidate JSON is not an input. Login strings are display data. Enrollment
uses the numeric GitHub user id returned by the API.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Protocol
from urllib import error, parse, request

_LOGIN = __import__("re").compile(r"^[A-Za-z0-9-]+\Z")
_EVIDENCE_KIND = "github_pull_request_review"
PERMISSION_RANK = {
    "none": 0,
    "read": 1,
    "triage": 2,
    "write": 3,
    "maintain": 4,
    "admin": 5,
}


class GitHubApiError(Exception):
    """The evidence service returned an unusable response."""


class ReviewClient(Protocol):
    def list_reviews(self, repository: str, pull_number: int) -> list[Mapping[str, Any]]:
        """Return review objects for one pull request."""

    def reviewer_permission(self, repository: str, login: str) -> str:
        """Return the permission name GitHub reports for ``login``."""


def permission_satisfies(actual: str | None, required: str) -> bool:
    if actual not in PERMISSION_RANK or required not in PERMISSION_RANK:
        return False
    return PERMISSION_RANK[actual] >= PERMISSION_RANK[required]


def _user_id(review: Mapping[str, Any]) -> int | None:
    user = review.get("user")
    if not isinstance(user, Mapping):
        return None
    value = user.get("id")
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _login(review: Mapping[str, Any]) -> str | None:
    user = review.get("user")
    if not isinstance(user, Mapping):
        return None
    login = user.get("login")
    if not isinstance(login, str) or _LOGIN.fullmatch(login) is None:
        return None
    return login


def _sort_key(review: Mapping[str, Any]) -> tuple[str, int]:
    submitted = review.get("submitted_at")
    stamp = submitted if isinstance(submitted, str) else ""
    identifier = review.get("id")
    number = identifier if isinstance(identifier, int) and not isinstance(identifier, bool) else 0
    return stamp, number


class GitHubEvidenceResolver:
    """Build evaluator payloads from API reviews for one repository and pull request."""

    def __init__(
        self,
        client: ReviewClient,
        *,
        repository: str,
        pull_number: int,
    ) -> None:
        self._client = client
        self._repository = repository
        self._pull_number = pull_number

    def __call__(self, evidence_id: str) -> dict[str, Any]:
        from governance.kernel.evaluate import EvidenceUnavailable

        try:
            reviews = list(self._client.list_reviews(self._repository, self._pull_number))
        except EvidenceUnavailable:
            raise
        except Exception as exc:
            raise EvidenceUnavailable("review list failed") from exc
        selected = None
        for review in reviews:
            if str(review.get("id")) == evidence_id:
                selected = review
                break
        if selected is None:
            return {"available": False}
        user_id = _user_id(selected)
        login = _login(selected)
        if user_id is None or login is None:
            return {"available": False}
        latest_id = None
        for review in sorted(reviews, key=_sort_key):
            if _user_id(review) == user_id:
                latest_id = review.get("id")
        state = selected.get("state")
        if selected.get("dismissed") is True:
            state = "DISMISSED"
        if not isinstance(state, str):
            return {"available": False}
        try:
            permission = self._client.reviewer_permission(self._repository, login)
        except EvidenceUnavailable:
            raise
        except Exception as exc:
            raise EvidenceUnavailable("permission lookup failed") from exc
        commit_id = selected.get("commit_id")
        return {
            "available": True,
            "commit_id": commit_id if isinstance(commit_id, str) else "",
            "github_user_id": user_id,
            "identity": str(user_id),
            "kind": _EVIDENCE_KIND,
            "login": login,
            "permission": permission if isinstance(permission, str) else "",
            "pull_number": self._pull_number,
            "repository": self._repository,
            "review_state": state,
            "superseded": latest_id != selected.get("id"),
        }


class UrllibGitHubClient:
    """Minimal read-only GitHub REST client. The token stays off the command line."""

    def __init__(self, token: str, api_base: str = "https://api.github.com") -> None:
        self._token = token
        self._base = api_base.rstrip("/")

    def _get(self, url: str) -> Any:
        if not self._token:
            from governance.kernel.evaluate import EvidenceUnavailable

            raise EvidenceUnavailable("missing token")
        req = request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self._token}",
                "User-Agent": "cam-assist-governance",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with request.urlopen(req, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            raise GitHubApiError(str(exc.code)) from exc
        except error.URLError as exc:
            from governance.kernel.evaluate import EvidenceUnavailable

            raise EvidenceUnavailable("github api unavailable") from exc

    def list_reviews(self, repository: str, pull_number: int) -> list[Mapping[str, Any]]:
        owner, sep, name = repository.partition("/")
        if not sep or not owner or not name or "/" in name:
            raise GitHubApiError("invalid repository")
        url = f"{self._base}/repos/{parse.quote(owner)}/{parse.quote(name)}/pulls/{int(pull_number)}/reviews"
        body = self._get(url)
        if not isinstance(body, list):
            raise GitHubApiError("invalid review list")
        return [item for item in body if isinstance(item, Mapping)]

    def reviewer_permission(self, repository: str, login: str) -> str:
        if _LOGIN.fullmatch(login) is None:
            raise GitHubApiError("invalid login")
        owner, sep, name = repository.partition("/")
        if not sep:
            raise GitHubApiError("invalid repository")
        url = (
            f"{self._base}/repos/{parse.quote(owner)}/{parse.quote(name)}"
            f"/collaborators/{parse.quote(login)}/permission"
        )
        body = self._get(url)
        if not isinstance(body, Mapping):
            raise GitHubApiError("invalid permission")
        permission = body.get("permission")
        if not isinstance(permission, str):
            raise GitHubApiError("invalid permission")
        return permission
