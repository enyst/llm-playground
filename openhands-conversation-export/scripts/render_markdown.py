#!/usr/bin/env python3
"""Render a conversation JSON export to a human-readable markdown transcript.

Output focuses on readability:
- Messages are shown plainly.
- Tool calls / tool results are wrapped in collapsed <details> blocks.
- Tool results are truncated (first N + last N characters).

Input format is the output of export_conversation.py.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
from typing import Any, Dict, List, Optional


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


def _get_text(event: Dict[str, Any]) -> str:
    # Prefer content for observations; message for chatty events.
    msg = event.get("message")
    content = event.get("content")
    if isinstance(content, str) and content.strip():
        return content
    if isinstance(msg, str) and msg.strip():
        return msg
    return ""


def _truncate(s: str, head: int, tail: int) -> str:
    s = redact_secrets(s)
    if len(s) <= head + tail + 20:
        return s
    removed = len(s) - (head + tail)
    return f"{s[:head]}...<truncated {removed} chars>...{s[-tail:]}"


def _fmt_ts(ts: Optional[str]) -> str:
    if not ts:
        return ""
    try:
        t = ts.replace("Z", "+00:00")
        d = dt.datetime.fromisoformat(t)
        return d.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    except Exception:  # noqa: BLE001
        return ts


def _safe_json(obj: Any) -> str:
    return redact_secrets(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True))


def render_event(
    event: Dict[str, Any],
    *,
    tool_call_by_id: Dict[int, Dict[str, Any]],
    head: int,
    tail: int,
) -> str:
    eid = event.get("id")
    ts = _fmt_ts(event.get("timestamp"))
    src = event.get("source")

    header = f"**{src}**" if src else "**event**"
    if ts:
        header += f" · {ts}"
    if isinstance(eid, int):
        header += f" · id={eid}"

    is_observation = "observation" in event
    is_tool_call = "action" in event

    if is_tool_call:
        action = event.get("action")
        args = event.get("args")
        summary_bits: List[str] = []
        if isinstance(action, str):
            summary_bits.append(action)
        if isinstance(args, dict):
            cmd = args.get("command")
            if isinstance(cmd, str):
                summary_bits.append(cmd.replace("\n", " ")[:120])
        summary = " · ".join(summary_bits) if summary_bits else "tool call"

        body: List[str] = []
        body.append(header)
        body.append("")
        body.append(f"<details>\n<summary>Tool call: {summary}</summary>\n")
        body.append("\n```json")
        body.append(
            _safe_json(
                {k: event.get(k) for k in ("action", "args", "timeout") if k in event}
            )
        )
        body.append("```\n</details>\n")
        return "\n".join(body)

    if is_observation:
        obs = event.get("observation")
        cause = event.get("cause")
        cause_txt = ""
        if isinstance(cause, int) and cause in tool_call_by_id:
            cause_evt = tool_call_by_id[cause]
            a = cause_evt.get("action")
            if isinstance(a, str):
                cause_txt = a
        summary = " / ".join(
            [p for p in [obs if isinstance(obs, str) else None, cause_txt or None] if p]
        )
        summary = summary or "tool result"

        content = _get_text(event)
        content = _truncate(content, head=head, tail=tail) if content else ""

        body: List[str] = []
        body.append(header)
        body.append("")
        body.append(f"<details>\n<summary>Tool result: {summary}</summary>\n")

        if content:
            body.append("\n```text")
            body.append(content.rstrip())
            body.append("```")

        extras = event.get("extras")
        if extras:
            body.append("\n```json")
            body.append(_safe_json(extras))
            body.append("```")

        body.append("\n</details>\n")
        return "\n".join(body)

    text = _get_text(event)
    if not text:
        return ""

    body = [header, "", text.strip(), ""]
    return "\n".join(body)


def render_markdown(payload: Dict[str, Any], *, head: int, tail: int) -> str:
    convo = payload.get("conversation") if isinstance(payload, dict) else None
    events = payload.get("events") if isinstance(payload, dict) else None

    if not isinstance(convo, dict) or not isinstance(events, list):
        raise ValueError("Input JSON does not look like an export_conversation.py payload")

    title = convo.get("title") or convo.get("conversation_id") or "Conversation"

    tool_calls: Dict[int, Dict[str, Any]] = {}
    for e in events:
        if isinstance(e, dict) and isinstance(e.get("id"), int) and "action" in e:
            tool_calls[int(e["id"])] = e

    out: List[str] = []
    out.append(f"# {title}\n")
    out.append("## Metadata\n")
    out.append(f"- Conversation ID: `{convo.get('conversation_id')}`")
    if convo.get("selected_repository"):
        out.append(f"- Repo: `{convo.get('selected_repository')}`")
    if convo.get("selected_branch"):
        out.append(f"- Branch: `{convo.get('selected_branch')}`")
    if convo.get("created_at"):
        out.append(f"- Created: `{convo.get('created_at')}`")
    if convo.get("last_updated_at"):
        out.append(f"- Last updated: `{convo.get('last_updated_at')}`")
    if convo.get("status"):
        out.append(f"- Status: `{convo.get('status')}`")
    out.append("")

    out.append("## Transcript\n")
    for e in events:
        if not isinstance(e, dict):
            continue
        chunk = render_event(e, tool_call_by_id=tool_calls, head=head, tail=tail)
        if chunk.strip():
            out.append(chunk)

    return "\n".join(out).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render conversation JSON to markdown")
    parser.add_argument("--in", dest="in_path", required=True)
    parser.add_argument("--out", dest="out_path", required=True)
    parser.add_argument("--head", type=int, default=100)
    parser.add_argument("--tail", type=int, default=100)
    args = parser.parse_args()

    with open(args.in_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    md = render_markdown(payload, head=args.head, tail=args.tail)

    os.makedirs(os.path.dirname(os.path.abspath(args.out_path)), exist_ok=True)
    with open(args.out_path, "w", encoding="utf-8") as f:
        f.write(md)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
