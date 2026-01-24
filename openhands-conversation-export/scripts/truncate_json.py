#!/usr/bin/env python3
"""Create a truncated copy of a conversation JSON export.

This is meant to make large tool outputs easier to commit and work with.

Truncation strategy:
- For any string longer than --max-len, replace it with:
    first --head chars + "...<truncated N chars>..." + last --tail chars
"""

from __future__ import annotations

import argparse
import json
import os
import re
from typing import Any


SENSITIVE_KEYS = {
    "session_api_key",
    "api_key",
    "llm_api_key",
}

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


def truncate_str(s: str, *, max_len: int, head: int, tail: int) -> str:
    s = redact_secrets(s)
    if len(s) <= max_len:
        return s
    if head + tail >= max_len:
        head = max(0, max_len // 2)
        tail = max(0, max_len - head)
    removed = len(s) - (head + tail)
    return f"{s[:head]}...<truncated {removed} chars>...{s[-tail:]}"


def truncate_obj(obj: Any, *, max_len: int, head: int, tail: int) -> Any:
    if isinstance(obj, str):
        return truncate_str(obj, max_len=max_len, head=head, tail=tail)
    if isinstance(obj, list):
        return [truncate_obj(v, max_len=max_len, head=head, tail=tail) for v in obj]
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if k in SENSITIVE_KEYS and isinstance(v, str) and v:
                out[k] = "<redacted>"
                continue
            out[k] = truncate_obj(v, max_len=max_len, head=head, tail=tail)
        return out
    return obj


def main() -> int:
    parser = argparse.ArgumentParser(description="Truncate long strings in JSON")
    parser.add_argument("--in", dest="in_path", required=True)
    parser.add_argument("--out", dest="out_path", required=True)
    parser.add_argument("--max-len", type=int, default=5000)
    parser.add_argument("--head", type=int, default=100)
    parser.add_argument("--tail", type=int, default=100)
    args = parser.parse_args()

    with open(args.in_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    truncated = truncate_obj(data, max_len=args.max_len, head=args.head, tail=args.tail)

    os.makedirs(os.path.dirname(os.path.abspath(args.out_path)), exist_ok=True)
    with open(args.out_path, "w", encoding="utf-8") as f:
        json.dump(truncated, f, ensure_ascii=False, indent=2)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
