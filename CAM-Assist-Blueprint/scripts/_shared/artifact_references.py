"""Portable artifact reference paths.

Canonical rule: every relative reference is stored and resolved relative to
the directory of the file that declares it.

    stored = relative_reference(declaring_file, target_file)
    target = resolve_declared_reference(declaring_file, stored)

Serialized references use forward slashes. There is no repository-root
fallback and no process-cwd resolution. Existence is not required merely
to resolve a string.
"""

from __future__ import annotations

import os
import posixpath
from pathlib import Path

__all__ = [
    "normalize_reference_string",
    "relative_reference",
    "resolve_declared_reference",
    "resolve_from_directory",
]


def normalize_reference_string(reference: str) -> str:
    """Normalize a stored reference string to POSIX form.

    Backslashes become slashes. ``.`` and ``..`` are collapsed. The resolver
    is not a validator: blank or non-string values are the owning validator's
    concern.
    """
    if not isinstance(reference, str):
        raise TypeError("declared reference must be a string")
    return posixpath.normpath(reference.replace("\\", "/"))


def _collapse_path(path: Path) -> Path:
    """Collapse ``.`` / ``..`` without consulting the filesystem or cwd."""
    return Path(posixpath.normpath(Path(path).as_posix()))


def relative_reference(declaring_file: Path, target_file: Path) -> str:
    """Return a portable reference from ``declaring_file`` to ``target_file``.

    The stored value is relative to ``declaring_file.parent``, uses forward
    slashes, and is not an absolute path under normal in-repo usage.
    """
    declaring_file = Path(declaring_file)
    target_file = Path(target_file)
    rel = os.path.relpath(os.fspath(target_file), start=os.fspath(declaring_file.parent))
    serialized = Path(rel).as_posix().replace("\\", "/")
    if serialized == ".":
        return "."
    return posixpath.normpath(serialized)


def resolve_from_directory(base_dir: Path, reference: str) -> Path:
    """Resolve a declared reference against an explicit directory.

    The canonical rule uses ``declaring_file.parent``. Bundle ``--base`` is an
    explicit operator override of that directory, not a repository-root
    fallback. Target existence is not required.
    """
    return _collapse_path(Path(base_dir) / normalize_reference_string(reference))


def resolve_declared_reference(declaring_file: Path, reference: str) -> Path:
    """Resolve ``reference`` relative to the declaring file's directory."""
    return resolve_from_directory(Path(declaring_file).parent, reference)
