"""Resolve pull-request reviews from a GitHub API client.

Candidate JSON is not an input. Login strings are display data. Enrollment
uses the numeric GitHub user id returned by the API. A later review by that
user supersedes an earlier approval, including a later comment. Pending
reviews and unread pages are not a partial approval history.
"""

from __future__ import annotations

from datetime import datetime, timezone
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


def _unavailable(message: str) -> None:
    from governance.kernel.evaluate import EvidenceUnavailable

    raise EvidenceUnavailable(message)


def _review_id(review: Mapping[str, Any]) -> int:
    identifier = review.get("id")
    if isinstance(identifier, bool) or not isinstance(identifier, int):
        _unavailable("review id missing")
    return identifier


def _submitted_at(review: Mapping[str, Any]) -> datetime:
    submitted = review.get("submitted_at")
    if not isinstance(submitted, str) or submitted == "":
        _unavailable("review timestamp missing")
    text = submitted[:-1] + "+00:00" if submitted.endswith("Z") else submitted
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        _unavailable("review timestamp invalid")
    if parsed.tzinfo is None:
        _unavailable("review timestamp naive")
    return parsed.astimezone(timezone.utc)


def _latest_id_for_user(reviews: list[Mapping[str, Any]], user_id: int) -> int:
    """Latest review for one user. Pending or unreadable rows fail closed.

    Applicable history is every review with this numeric GitHub user id.
    Ordering is submitted time, then review id. A later comment, dismissal,
    or change request supersedes an earlier approval.
    """
    seen: set[int] = set()
    ranked: list[tuple[datetime, int]] = []
    for review in reviews:
        identifier = _review_id(review)
        if identifier in seen:
            _unavailable("duplicate review id")
        seen.add(identifier)
        if _user_id(review) != user_id:
            continue
        if review.get("state") == "PENDING":
            _unavailable("pending review in history")
        state = review.get("state")
        if not isinstance(state, str) or state == "":
            _unavailable("review state missing")
        ranked.append((_submitted_at(review), identifier))
    if not ranked:
        _unavailable("review history missing")
    ranked.sort()
    return ranked[-1][1]


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
        latest_id = _latest_id_for_user(reviews, user_id)
        state = selected.get("state")
        if selected.get("dismissed") is True:
            state = "DISMISSED"
        if not isinstance(state, str):
            _unavailable("review state missing")
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
            "superseded": latest_id != _review_id(selected),
        }


class UrllibGitHubClient:
    """Minimal read-only GitHub REST client. The token stays off the command line."""

    def __init__(self, token: str, api_base: str = "https://api.github.com") -> None:
        self._token = token
        self._base = api_base.rstrip("/")

    def _get(self, url: str) -> Any:
        body, _headers = self._open(url)
        return body

    def _open(self, url: str) -> tuple[Any, str]:
        if not self._token:
            _unavailable("missing token")
        current = parse.urlparse(self._base)
        target = parse.urlparse(url)
        if target.scheme != current.scheme or target.netloc != current.netloc or target.username or target.password:
            _unavailable("review page left the api host")
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
                try:
                    payload = json.loads(response.read().decode("utf-8"))
                except json.JSONDecodeError:
                    _unavailable("invalid review list")
                header = response.headers.get("Link")
                return payload, header or ""
        except error.HTTPError as exc:
            exc.close()
            _unavailable(f"github api http {exc.code}")
        except error.URLError as exc:
            _unavailable("github api unavailable")
        raise AssertionError("unreachable")

    def _next_url(self, link_header: str) -> str | None:
        if link_header.strip() == "":
            return None
        found = None
        for part in link_header.split(","):
            url_part, _, params = part.strip().partition(";")
            url_part = url_part.strip()
            if not url_part.startswith("<") or ">" not in url_part:
                continue
            candidate = url_part[1 : url_part.index(">")]
            rels = []
            for param in params.split(";"):
                key, _, value = param.strip().partition("=")
                if key.strip() == "rel":
                    rels.append(value.strip().strip('"'))
            if "next" in rels:
                found = candidate
        if found is None:
            return None
        target = parse.urlparse(found)
        current = parse.urlparse(self._base)
        if target.scheme != current.scheme or target.netloc != current.netloc or target.username or target.password:
            _unavailable("review page left the api host")
        return found

    def list_reviews(self, repository: str, pull_number: int) -> list[Mapping[str, Any]]:
        owner, sep, name = repository.partition("/")
        if not sep or not owner or not name or "/" in name:
            raise GitHubApiError("invalid repository")
        try:
            number = int(pull_number)
        except (TypeError, ValueError):
            raise GitHubApiError("invalid pull number") from None
        if number <= 0:
            raise GitHubApiError("invalid pull number")
        url = (
            f"{self._base}/repos/{parse.quote(owner)}/{parse.quote(name)}"
            f"/pulls/{number}/reviews?per_page=100"
        )
        collected: list[Mapping[str, Any]] = []
        seen_urls: set[str] = set()
        while url:
            if url in seen_urls or len(seen_urls) >= 50:
                _unavailable("review page loop")
            seen_urls.add(url)
            body, link_header = self._open(url)
            if not isinstance(body, list):
                _unavailable("invalid review list")
            for item in body:
                if not isinstance(item, Mapping):
                    _unavailable("invalid review list")
                collected.append(item)
            url = self._next_url(link_header)
        return collected

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
