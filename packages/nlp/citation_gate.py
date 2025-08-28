import re
from typing import Optional


_PATTERN = re.compile(r"\[(\d+)\]$")


def citation_gate(text: str, max_id: int) -> str:
    """Keep only sentences that end with [1..max_id]. Drop the rest.

    Returns empty string if nothing valid remains.
    """
    if not text or max_id <= 0:
        return ""

    # Split into sentences by punctuation (., !, ? or Bengali danda '।') while retaining markers
    # We will do a simple split and trim.
    # Note: This is heuristic and should be good enough for enforcing the gate.
    parts = re.split(r"(?<=[\.!?।])\s+", text.strip())

    kept = []
    for sent in parts:
        s = sent.strip()
        if not s:
            continue
        m = _PATTERN.search(s)
        if not m:
            continue
        try:
            n = int(m.group(1))
        except Exception:
            continue
        if 1 <= n <= max_id:
            kept.append(s)

    return (" " .join(kept)).strip()
