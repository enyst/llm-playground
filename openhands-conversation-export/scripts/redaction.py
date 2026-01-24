from __future__ import annotations

import re


REDACTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bghu_[A-Za-z0-9_]{20,}\b"), "<redacted-github-token>"),
    (re.compile(r"\bghp_[A-Za-z0-9_]{20,}\b"), "<redacted-github-token>"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"), "<redacted-github-token>"),
    (re.compile(r"(https?://)([^/@\s]+)@github\.com"), r"\1<redacted>@github.com"),
    (re.compile(r"(Authorization:\s*Bearer\s+)([^\s\"]+)", re.IGNORECASE), r"\1<redacted>"),
]


def redact_secrets(s: str) -> str:
    for pat, repl in REDACTION_PATTERNS:
        s = pat.sub(repl, s)
    return s
