"""Console-safe text.

A commitment record may carry an organisation name or a cited source in a non-English
script that a legacy console cannot encode. For terminal output this module folds printable
ASCII through, drops combining marks and renders anything else as `<U+XXXX>`, so a report
is always writable. JSON output is ASCII-escaped by the encoder instead.
"""

from __future__ import annotations

import unicodedata


def fold(text: str) -> str:
    """Return printable ASCII: combining marks dropped, non-ASCII rendered as <U+XXXX>."""
    out = []
    for ch in unicodedata.normalize("NFKD", text):
        cp = ord(ch)
        if 32 <= cp < 127 or ch in "\n\t":
            out.append(ch)
        elif unicodedata.combining(ch):
            continue
        else:
            out.append("<U+%04X>" % cp)
    return "".join(out)
