"""Deterministic CLI output encoding.

Every CAM Assist entry point that prints a non-ASCII character calls
`force_utf8_output()` before writing anything, so what reaches stdout does not
depend on the host console's or pipe's codepage.

Why this exists, precisely: on Windows a piped stdout defaults to the locale
codepage, cp1252. That codepage is not the problem by itself -- it encodes an
em-dash at 0x97 and a right single quote at 0x92 quite happily, which is why
most non-ASCII output in this repository never failed. It has no mapping at all
for U+2192, the arrow the capability report draws under each mapped match, so
writing that report raised UnicodeEncodeError and killed the process.

The fix is the encoding, never the character. No caller strips or bans
non-ASCII output to satisfy this; the stream is made able to carry what the
report already says.

Note that this is only one end of the pipe. A reader that decodes with the
locale encoding will still mangle correctly-written UTF-8 -- subprocess callers
have to pass `encoding="utf-8"` themselves. Both ends must agree, and this
module can only speak for the writing end.
"""

from __future__ import annotations

import sys


def force_utf8_output() -> None:
    """Reconfigure stdout and stderr to UTF-8, if they will allow it.

    Guarded three ways, because a CLI whose real work is fine must never die
    trying to adjust its own output stream:

      - `reconfigure` exists only on TextIOWrapper, not on every stream object
      - a caller may already have wrapped or replaced stdout
      - a detached or closed stream raises rather than reconfiguring

    Any of those degrades to the previous behaviour instead of raising. Call it
    before the first write, so no line escapes under the old encoding.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8")
        except (ValueError, OSError):
            # Already-detached or non-reconfigurable stream. Leave it alone.
            pass
