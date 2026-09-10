#!/usr/bin/env python3
"""Scaffold AGENTS.md and a pull-request template for a Git repository.

Writes two files:

* ``AGENTS.md`` at the repository root — agent operating contract, with the
  real repository name and the real default branch substituted throughout.
* ``.github/pull_request_template.md`` — only when no pull-request template
  already exists (any casing, in ``.github/``, the repo root, or ``docs/``).

Human-owned blocks (incidents, verification gates) are left as HTML-comment
TODOs. The scaffolder will not invent them.

Safety properties this CLI is built around:

1. ``--force`` without ``--yes`` refuses when stdin is not a TTY, *before*
   any file is written. A half-completed overwrite is worse than a refusal.
2. An existing pull-request template is never replaced and never duplicated,
   including when its filename casing or directory differs from the default.
3. The heading uses the origin remote's repository name, not the worktree
   directory name (worktrees are often named for the task).
4. If the default branch cannot be detected, the CLI refuses rather than
   writing ``main`` into a canonical file for a repo that does not use it.

Usage:
    python scripts/scaffold_agents_md.py [REPO]
    python scripts/scaffold_agents_md.py REPO --force --yes
    python scripts/scaffold_agents_md.py REPO --default-branch develop

Exit codes:
    0 — wrote, skipped existing files, or both
    1 — refused (undetectable default branch, headless --force, aborted prompt)
    2 — REPO is not a Git worktree, or a Git/IO error prevented the run
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

PR_TEMPLATE_NAME = "pull_request_template.md"
PR_TEMPLATE_SEARCH_DIRS = (".github", "", "docs")
TODO_MARKERS = ("<!-- INCIDENTS", "<!-- VERIFICATION GATES")


def _git(repo: Path, *args: str, timeout: int = 15) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def is_git_worktree(repo: Path) -> bool:
    if not repo.is_dir():
        return False
    result = _git(repo, "rev-parse", "--is-inside-work-tree")
    return result.returncode == 0 and result.stdout.strip() == "true"


def _ref_exists(repo: Path, ref: str) -> bool:
    return _git(repo, "show-ref", "--verify", "--quiet", ref).returncode == 0


def detect_default_branch(repo: Path, override: str | None) -> str | None:
    """Return the repository's default branch, or None if it cannot be known.

    Detection never falls back to the current branch or to ``init.defaultBranch``.
    Either of those would silently stamp a guessed name into a canonical file.
    """
    if override:
        name = override.strip()
        return name or None

    head = _git(repo, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
    if head.returncode == 0:
        ref = head.stdout.strip()
        prefix = "refs/remotes/origin/"
        if ref.startswith(prefix) and ref[len(prefix) :]:
            return ref[len(prefix) :]

    for remote_branch in ("main", "master"):
        if _ref_exists(repo, f"refs/remotes/origin/{remote_branch}"):
            return remote_branch

    for local_branch in ("main", "master"):
        if _ref_exists(repo, f"refs/heads/{local_branch}"):
            return local_branch

    return None


def repository_name_from_remote_url(url: str) -> str:
    """Last path component of a Git remote URL, without a trailing ``.git``."""
    cleaned = url.strip()
    if not cleaned:
        return ""

    if "://" in cleaned:
        parsed = urlparse(cleaned)
        path = unquote(parsed.path)
    elif ":" in cleaned and not cleaned.startswith("/"):
        # scp-like: git@host:org/name.git
        path = cleaned.split(":", 1)[1]
    else:
        path = cleaned

    path = path.rstrip("/")
    name = Path(path).name
    if name.endswith(".git"):
        name = name[: -len(".git")]
    return name


def detect_repository_name(repo: Path) -> str:
    origin = _git(repo, "config", "--get", "remote.origin.url")
    if origin.returncode == 0:
        name = repository_name_from_remote_url(origin.stdout)
        if name:
            return name
    return repo.resolve().name


def find_existing_pr_template(repo: Path) -> Path | None:
    """Return an existing PR template regardless of casing or conventional dir."""
    for relative in PR_TEMPLATE_SEARCH_DIRS:
        directory = repo / relative if relative else repo
        if not directory.is_dir():
            continue
        for child in directory.iterdir():
            if child.is_file() and child.name.casefold() == PR_TEMPLATE_NAME:
                return child
    return None


def render_agents_md(*, repo_name: str, default_branch: str) -> str:
    branch = default_branch
    origin_ref = f"origin/{branch}"
    return f"""# Agent instructions — {repo_name}

Canonical operating contract for coding agents in this repository.
Do not substitute a different playbook, and do not treat a worktree
directory name as the repository name.

## Branch from current `{branch}`. Always.

The default branch is `{branch}`. Every task starts from current `{branch}`:

1. Fetch and update `{origin_ref}`.
2. Create a task branch from that tip.
3. Do not commit, merge, or push to `{branch}` from an agent session.

```bash
git fetch origin {branch}
git switch --create <task-branch> {origin_ref}
```

## Self-check

Before you claim work is complete, this must be true:

```bash
git merge-base HEAD {origin_ref}
```

If `{origin_ref}` cannot be resolved, stop. Do not invent a different base
and do not fall back to another branch name.

## Incidents

Repository-specific failures the agent must not repeat. The scaffolder
does not invent these; a human fills them in.

<!-- INCIDENTS
TODO: document incidents the agent must not repeat.
-->

## Verification gates

Commands that must be run, not inferred, before a pull request is opened.

<!-- VERIFICATION GATES
TODO: list pytest / lint / typecheck / browser-verification commands.
-->
"""


def render_pr_template(*, default_branch: str) -> str:
    return f"""## Summary

<!-- What changed, and why. -->

## Target branch

This pull request targets `{default_branch}`.

## Verification

- [ ] Verification gates listed in `AGENTS.md` have been run
- [ ] No known incident from `AGENTS.md` was repeated

## Notes

<!-- Follow-ups, screenshots, leftover risk. -->
"""


def confirm_overwrite(path: Path, *, yes: bool) -> int | None:
    """Return an exit code to abort, or None to overwrite.

    The TTY check happens before ``input()`` so a closed stdin cannot raise
    ``EOFError`` after another file has already been written.
    """
    if yes:
        return None
    if not sys.stdin.isatty():
        print(
            f"error: {path.name} already exists; --force requires --yes "
            "when stdin is not a TTY (agent sessions close stdin)",
            file=sys.stderr,
        )
        return 1
    try:
        reply = input(f"{path.name} already exists. Overwrite? [y/N] ").strip().lower()
    except EOFError:
        print(
            f"error: {path.name} already exists; could not confirm overwrite",
            file=sys.stderr,
        )
        return 1
    if reply not in {"y", "yes"}:
        print("aborted", file=sys.stderr)
        return 1
    return None


def report_unfilled_todos(body: str) -> None:
    found = [marker for marker in TODO_MARKERS if marker in body]
    if not found:
        return
    print("Human-owned blocks are NOT DONE — fill them before treating the scaffold as complete:")
    for marker in found:
        print(f"  {marker}")


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Write AGENTS.md and a pull-request template for a Git repository. "
            "Refuses to guess an undetectable default branch."
        )
    )
    parser.add_argument(
        "repo",
        nargs="?",
        default=".",
        type=Path,
        help="Git worktree to scaffold (default: current directory)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite AGENTS.md if it already exists",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Do not prompt; required with --force when stdin is not a TTY",
    )
    parser.add_argument(
        "--default-branch",
        metavar="NAME",
        default=None,
        help="Default branch to write into the scaffold (skip detection)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo = args.repo.expanduser().resolve()

    if not is_git_worktree(repo):
        print(
            f"error: {repo} is not a Git worktree",
            file=sys.stderr,
        )
        return 2

    default_branch = detect_default_branch(repo, args.default_branch)
    if default_branch is None:
        print(
            "error: could not detect the default branch for this repository.\n"
            "Refusing to write AGENTS.md with a guessed branch name.\n"
            "Pass --default-branch NAME to set it explicitly.",
            file=sys.stderr,
        )
        return 1

    agents_path = repo / "AGENTS.md"
    if agents_path.exists() and not args.force:
        print(f"SKIP {agents_path.name} (already exists)")
        write_agents = False
    elif agents_path.exists() and args.force:
        abort = confirm_overwrite(agents_path, yes=args.yes)
        if abort is not None:
            return abort
        write_agents = True
    else:
        write_agents = True

    existing_template = find_existing_pr_template(repo)
    template_path = repo / ".github" / PR_TEMPLATE_NAME
    write_template = existing_template is None

    # All refusal checks have completed. Writes start only after this point.
    try:
        if write_agents:
            repo_name = detect_repository_name(repo)
            body = render_agents_md(repo_name=repo_name, default_branch=default_branch)
            agents_path.write_text(body, encoding="utf-8", newline="\n")
            print(f"WRITE {agents_path.name}")
            report_unfilled_todos(body)

        if write_template:
            template_path.parent.mkdir(parents=True, exist_ok=True)
            template_path.write_text(
                render_pr_template(default_branch=default_branch),
                encoding="utf-8",
                newline="\n",
            )
            print(f"WRITE {template_path.relative_to(repo)}")
        else:
            rel = existing_template.relative_to(repo) if existing_template else PR_TEMPLATE_NAME
            print(f"SKIP {rel} (already exists)")
    except OSError as exc:
        print(f"error: failed to write scaffold files: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
