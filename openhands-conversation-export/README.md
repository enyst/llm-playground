# OpenHands conversation export

Utilities to export an OpenHands Cloud conversation (events/trajectory) to JSON and render it into a human-readable Markdown transcript.

## Quick start

From the repo root (`llm-playground/`):

```bash
export OPENHANDS_API_KEY=...  # required

# 1) Fetch full, raw event stream (can be large)
python openhands-conversation-export/scripts/export_conversation.py \
  --conversation-id 2c6ec633e00c4c5da99601de500e5752 \
  --out openhands-conversation-export/conversations/2c6ec633e00c4c5da99601de500e5752.raw.json

# 2) Create a truncated JSON (recommended for committing)
python openhands-conversation-export/scripts/truncate_json.py \
  --input-path openhands-conversation-export/conversations/2c6ec633e00c4c5da99601de500e5752.raw.json \
  --output-path openhands-conversation-export/conversations/2c6ec633e00c4c5da99601de500e5752.truncated.json

# 3) Render markdown transcript
python openhands-conversation-export/scripts/render_markdown.py \
  --input-path openhands-conversation-export/conversations/2c6ec633e00c4c5da99601de500e5752.truncated.json \
  --output-path openhands-conversation-export/conversations/2c6ec633e00c4c5da99601de500e5752.md
```

Notes:
- The exporter will automatically fall back to the per-conversation runtime URL (requires `session_api_key`) if `app.all-hands.dev` returns errors.
- Tool calls / tool results are rendered inside collapsed `<details>` blocks.

## Example output

- Example transcript (rendered markdown):
  - [Discussion on WS reliability and /events source of truth](./conversations/2c6ec633e00c4c5da99601de500e5752.md)

