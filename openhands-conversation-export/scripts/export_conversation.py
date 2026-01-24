#!/usr/bin/env python3
"""Export an OpenHands Cloud conversation's events to JSON.

This script is intentionally dependency-free (stdlib-only).

It uses the Cloud management API:
  GET {base_url}/api/conversations/{conversation_id}
  GET {base_url}/api/conversations/{conversation_id}/events

If the app host returns an error page / non-JSON, it will fall back to the
conversation-specific runtime URL from the conversation details (and include
X-Session-API-Key).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Iterable, Optional, Tuple


DEFAULT_BASE_URL = "https://app.all-hands.dev"
MAX_LIMIT = 100


def _json_request(
    url: str,
    *,
    api_key: str,
    session_key: Optional[str] = None,
    timeout_s: int = 60,
) -> Any:
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Accept", "application/json")
    if session_key:
        req.add_header("X-Session-API-Key", session_key)

    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read()
            ctype = resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        raw = e.read() if hasattr(e, "read") else b""
        ctype = e.headers.get("Content-Type", "") if e.headers else ""
        raise RuntimeError(
            f"HTTP {e.code} for {url} (content-type={ctype!r} body_prefix={raw[:200]!r})"
        ) from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Request failed for {url} ({e})") from e

    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise RuntimeError(
            f"Non-JSON response for {url} (content-type={ctype!r} body_prefix={raw[:200]!r})"
        ) from e


def _build_url(base: str, path: str, params: Optional[Dict[str, Any]] = None) -> str:
    base = base.rstrip("/")
    path = path if path.startswith("/") else f"/{path}"
    url = f"{base}{path}"
    if params:
        q = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        url = f"{url}?{q}"
    return url


def get_conversation_details(
    *, base_url: str, conversation_id: str, api_key: str
) -> Dict[str, Any]:
    url = _build_url(base_url, f"/api/conversations/{conversation_id}")
    data = _json_request(url, api_key=api_key)
    if not isinstance(data, dict):
        raise RuntimeError(f"Expected dict for conversation details, got {type(data)}")
    return data


def iter_conversation_events(
    *,
    base_url: str,
    conversation_id: str,
    api_key: str,
    runtime_url: Optional[str],
    session_key: Optional[str],
    start_id: int = 0,
    limit: int = MAX_LIMIT,
    sleep_s: float = 0.0,
) -> Iterable[Dict[str, Any]]:
    limit = max(1, min(MAX_LIMIT, int(limit)))

    def fetch_page(page_start: int) -> Tuple[list[Dict[str, Any]], bool]:
        params = {"start_id": page_start, "limit": limit}
        url = _build_url(base_url, f"/api/conversations/{conversation_id}/events", params)
        try:
            payload = _json_request(url, api_key=api_key)
        except RuntimeError:
            if not runtime_url or not session_key:
                raise
            runtime_events_url = _build_url(
                runtime_url,
                "/events",
                {"start_id": page_start, "limit": limit},
            )
            payload = _json_request(
                runtime_events_url, api_key=api_key, session_key=session_key
            )

        events = payload.get("events") if isinstance(payload, dict) else None
        if not isinstance(events, list):
            raise RuntimeError(f"Unexpected events payload shape: {type(payload)}")
        has_more = bool(payload.get("has_more")) if isinstance(payload, dict) else False
        return events, has_more

    next_start = start_id
    while True:
        events, has_more = fetch_page(next_start)
        if not events:
            break

        for e in events:
            if isinstance(e, dict):
                yield e

        next_start = int(events[-1].get("id", next_start)) + 1
        if not has_more:
            break
        if sleep_s:
            time.sleep(sleep_s)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export OpenHands conversation events to JSON")
    parser.add_argument("--conversation-id", required=True)
    parser.add_argument(
        "--base-url",
        default=os.getenv("OPENHANDS_APP_BASE", DEFAULT_BASE_URL),
        help="OpenHands app base URL (default: https://app.all-hands.dev)",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output JSON file path",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=MAX_LIMIT,
        help="Events page size (1-100, default 100)",
    )
    parser.add_argument(
        "--sleep-s",
        type=float,
        default=0.0,
        help="Optional sleep between pages (seconds)",
    )

    args = parser.parse_args()

    api_key = os.getenv("OPENHANDS_API_KEY")
    if not api_key:
        print("OPENHANDS_API_KEY is required", file=sys.stderr)
        return 2

    details = get_conversation_details(
        base_url=args.base_url, conversation_id=args.conversation_id, api_key=api_key
    )
    runtime_url = details.get("url")
    session_key = details.get("session_api_key")

    events = list(
        iter_conversation_events(
            base_url=args.base_url,
            conversation_id=args.conversation_id,
            api_key=api_key,
            runtime_url=runtime_url,
            session_key=session_key,
            start_id=0,
            limit=args.limit,
            sleep_s=args.sleep_s,
        )
    )

    out_obj = {
        "exported_at": dt.datetime.now(tz=dt.timezone.utc).isoformat(),
        "base_url": args.base_url,
        "conversation": details,
        "events": events,
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out_obj, f, ensure_ascii=False, indent=2)

    print(
        f"Wrote {len(events)} events to {args.out} (status={details.get('status')!r}, title={details.get('title')!r})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
