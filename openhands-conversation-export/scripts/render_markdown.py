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
    args = event.get("args")
    if isinstance(args, dict):
        c = args.get("content")
        if isinstance(c, str) and c.strip():
            return c

    content = event.get("content")
    if isinstance(content, str) and content.strip():
        return content

    msg = event.get("message")
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


def is_chat_message(event: Dict[str, Any]) -> bool:
    if event.get("source") not in {"user", "agent"}:
        return False
    if event.get("action") != "message":
        return False
    return bool(_get_text(event).strip())


def is_noise_event(event: Dict[str, Any]) -> bool:
    src = event.get("source")
    action = event.get("action")
    obs = event.get("observation")

    # Environment state-change events are usually noisy and add little value.
    if src == "environment" and obs == "agent_state_changed":
        return True

    # User recall events are internal plumbing (not user-authored messages).
    if src == "user" and action == "recall":
        return True

    # Agent system prompt injection is rarely useful in a transcript.
    if src == "agent" and action == "system":
        return True

    # Misc empty environment observations.
    if src == "environment" and (obs in {None, "null"}) and not _get_text(event).strip():
        return True

    # Pure agent state toggles.
    if src == "environment" and action == "change_agent_state":
        return True

    return False


def render_chat_message(event: Dict[str, Any]) -> str:
    eid = event.get("id")
    ts = _fmt_ts(event.get("timestamp"))
    src = event.get("source")
    role = "User" if src == "user" else "Assistant" if src == "agent" else str(src)

    header_bits = [role]
    if ts:
        header_bits.append(ts)
    if isinstance(eid, int):
        header_bits.append(f"id={eid}")

    text = _get_text(event).strip()
    return "\n".join([f"### {' · '.join(header_bits)}", "", text, ""])


def render_tool_event(event: Dict[str, Any], *, tool_call_by_id: Dict[int, Dict[str, Any]], head: int, tail: int) -> str:
    eid = event.get("id")
    ts = _fmt_ts(event.get("timestamp"))
    src = event.get("source") or "event"

    header_bits: List[str] = [f"{src}"]
    if ts:
        header_bits.append(ts)
    if isinstance(eid, int):
        header_bits.append(f"id={eid}")

    if "action" in event and event.get("action") is not None:
        action = event.get("action")
        if isinstance(action, str):
            header_bits.append(f"action={action}")

        body: List[str] = []
        body.append(f"#### {' · '.join(header_bits)}")
        body.append("")
        body.append("```json")
        body.append(
            _safe_json({k: event.get(k) for k in ("action", "args", "timeout") if k in event})
        )
        body.append("```")
        body.append("")
        return "\n".join(body)

    if "observation" in event and event.get("observation") is not None:
        obs = event.get("observation")
        cause = event.get("cause")
        if isinstance(obs, str):
            header_bits.append(f"observation={obs}")
        if isinstance(cause, int):
            header_bits.append(f"cause={cause}")
            cause_evt = tool_call_by_id.get(cause)
            cause_action = (cause_evt or {}).get("action")
            if isinstance(cause_action, str):
                header_bits.append(f"cause_action={cause_action}")

        content = _get_text(event)
        content = _truncate(content, head=head, tail=tail) if content else ""

        body = []
        body.append(f"#### {' · '.join(header_bits)}")
        if content:
            body.append("")
            body.append("```text")
            body.append(content.rstrip())
            body.append("```")

        extras = event.get("extras")
        if extras:
            body.append("")
            body.append("```json")
            body.append(_safe_json(extras))
            body.append("```")

        body.append("")
        return "\n".join(body)

    # Fallback: unknown event shape
    text = _get_text(event)
    if not text:
        return ""
    text = _truncate(text, head=head, tail=tail)
    return "\n".join([f"#### {' · '.join(header_bits)}", "", "```text", text.rstrip(), "```", ""]) 


def render_tools_block(events: List[Dict[str, Any]], *, tool_call_by_id: Dict[int, Dict[str, Any]], head: int, tail: int) -> str:
    if not events:
        return ""

    lines: List[str] = []
    lines.append(f"<details>\n<summary>Tool calls / results ({len(events)} events)</summary>\n")
    for e in events:
        chunk = render_tool_event(e, tool_call_by_id=tool_call_by_id, head=head, tail=tail)
        if chunk.strip():
            lines.append(chunk)
    lines.append("</details>\n")
    return "\n".join(lines)


def render_markdown(payload: Dict[str, Any], *, head: int, tail: int) -> str:
    convo = payload.get("conversation") if isinstance(payload, dict) else None
    events = payload.get("events") if isinstance(payload, dict) else None

    if not isinstance(convo, dict) or not isinstance(events, list):
        raise ValueError("Input JSON does not look like an export_conversation.py payload")

    title = convo.get("title") or convo.get("conversation_id") or "Conversation"

    tool_calls: Dict[int, Dict[str, Any]] = {}
    for e in events:
        if not isinstance(e, dict) or not isinstance(e.get("id"), int):
            continue
        action = e.get("action")
        if action is None or action == "message":
            continue
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

    preamble_tools: List[Dict[str, Any]] = []
    pending_tools: List[Dict[str, Any]] = []
    seen_first_message = False

    for e in events:
        if not isinstance(e, dict):
            continue
        if is_noise_event(e):
            continue

        if is_chat_message(e):
            if not seen_first_message:
                tools_block = render_tools_block(
                    preamble_tools, tool_call_by_id=tool_calls, head=head, tail=tail
                )
                if tools_block.strip():
                    out.append(tools_block)
                seen_first_message = True
            else:
                tools_block = render_tools_block(
                    pending_tools, tool_call_by_id=tool_calls, head=head, tail=tail
                )
                if tools_block.strip():
                    out.append(tools_block)
                pending_tools = []

            out.append(render_chat_message(e))
            continue

        if seen_first_message:
            pending_tools.append(e)
        else:
            preamble_tools.append(e)

    tools_block = render_tools_block(
        pending_tools, tool_call_by_id=tool_calls, head=head, tail=tail
    )
    if tools_block.strip():
        out.append(tools_block)

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
