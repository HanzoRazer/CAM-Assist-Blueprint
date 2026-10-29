"""Versioned canonical JSON for governance digests.

Method ``canonical-json-sha256-v1`` hashes UTF-8 JSON with sorted keys and
compact separators. The digest field named by ``omit_key`` is removed only
from the object being hashed, not from nested objects.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

CANONICALIZATION = "canonical-json-sha256-v1"


def canonical_bytes(value: Any, *, omit_key: str | None = None) -> bytes:
    def walk(node: Any, omit: str | None) -> Any:
        if isinstance(node, dict):
            return {
                key: walk(item, None)
                for key, item in node.items()
                if key != omit
            }
        if isinstance(node, list):
            return [walk(item, None) for item in node]
        if isinstance(node, str) or isinstance(node, bool) or node is None or isinstance(node, int):
            return node
        raise TypeError(f"governance records cannot contain {type(node).__name__}")

    payload = walk(value, omit_key)
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def digest_of(value: Any, *, omit_key: str | None = None) -> str:
    return hashlib.sha256(canonical_bytes(value, omit_key=omit_key)).hexdigest()
