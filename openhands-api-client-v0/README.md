# OpenHands Cloud API Client (V0)

A Python client for automating tasks with the OpenHands Cloud API V0 (legacy).

> **Note**: This client targets the V0 (legacy) API. V0 is deprecated (scheduled for
> removal April 1, 2026) but still widely used. For the V1 client, see
> [`../openhands-api-client-v1/`](../openhands-api-client-v1/).

## Quick Start

```python
from scripts.cloud_api import OpenHandsCloudAPI

api = OpenHandsCloudAPI()  # Uses OPENHANDS_API_KEY env var

# Create a conversation
result = api.create_conversation(
    initial_user_msg="Fix the bug in app.py",
    repository="owner/repo",
)
conv_id = result['conversation_id']

# Get summary
summary = api.get_conversation_summary(conv_id)
print(f"Events: {summary['event_count']}, Model: {summary['model']}")
```

## Files

- `scripts/cloud_api.py` - OpenHands Cloud API client library
- `scripts/llm_conversation.py` - CLI for LLM configuration and conversations
- `scripts/prompts/` - Jinja2 templates (new_conversation, arch_conversation, etc.)
- `SCRATCHPAD.md` - Development notes and API documentation

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENHANDS_API_KEY` | Yes | Your OpenHands Cloud API key |
| `OPENHANDS_APP_BASE` | No | Override base URL (default: `https://app.all-hands.dev`) |
| `GITHUB_TOKEN` | No | For GitHub issue commenting |
| `LLM_MODEL` | No | The LLM model to use. Required for `configure-llm` command. |
| `LLM_BASE_URL` | No | Custom LLM API base URL |
| `LLM_API_KEY` | No | LLM provider API key |

## API Client Methods

### Conversation Management
- `create_conversation()` - Start a new conversation
- `list_conversations()` - List all conversations (paginated)
- `get_conversation()` - Get conversation details
- `delete_conversation()` - Delete a conversation
- `start_conversation()` - Start the agent loop
- `stop_conversation()` - Stop a running conversation
- `send_message()` - Add a message to ongoing conversation

### Events & Trajectory
- `get_events()` - Get events with filtering/pagination
- `get_trajectory()` - Get full trajectory
- `get_last_event_id()` - Get count without full download
- `download_trajectory_to_file()` - Save trajectory to JSON file

### Settings & User Info
- `store_llm_settings()` - Configure LLM settings
- `get_settings()` - Load current settings
- `get_user_info()` - Get authenticated user info

### Runtime & Workspace
- `list_files()` - List files in workspace
- `get_runtime_config()` - Get runtime_id and session_id
- `get_vscode_url()` - Get VS Code URL
- `get_web_hosts()` - Get runtime hosts
- `get_microagents()` - Get loaded microagents

### Utilities
- `poll_until_stopped()` - Wait for conversation to complete
- `get_conversation_summary()` - Get status, event count, model, etc.
- `get_recent_model()` - Extract model from recent events
- `get_early_model()` - Extract model from early events
- `get_first_user_message()` - Get the initial prompt
- `submit_feedback()` - Submit feedback for conversation
- `post_github_comment()` - Post to GitHub issues

### Runtime Fallback (when main API unavailable)
- `get_trajectory_via_runtime()` - Get trajectory via runtime URL
- `get_events_via_runtime()` - Get events via runtime URL

## CLI Usage

```bash
cd openhands-api-client

# Configure LLM
python scripts/llm_conversation.py configure-llm

# Start conversation
python scripts/llm_conversation.py new-conversation \
  --repository owner/repo --branch main --poll

# Combined
python scripts/llm_conversation.py configure-and-start --repository owner/repo --poll
```

## Dependencies

```bash
pip install requests jinja2
```

---

## Curl Examples

This section provides curl examples for debugging or raw HTTP access.

No credentials are included here. Throughout, use:
- Authorization header: `Authorization: Bearer $OPENHANDS_API_KEY`
- Optional app base override: `OPENHANDS_APP_BASE` (defaults to `https://app.all-hands.dev`)

If an app-host endpoint returns a maintenance page or otherwise fails, you can use the conversation-specific runtime URL together with the `X-Session-API-Key` from conversation details. See “Runtime host fallback” below.

## Setup

- Export your API key: `export OPENHANDS_API_KEY=...`
- Optionally, set an alternate app base: `export OPENHANDS_APP_BASE=https://app.all-hands.dev`

## Create a new conversation

POST `/api/conversations` with an initial user message. Example:

```bash
curl -sS \
  -H "Authorization: Bearer $OPENHANDS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "initial_user_msg": "Read https://github.com/OpenHands/OpenHands/pull/10305. It fails CI, please fix."
  }' \
  "$OPENHANDS_APP_BASE/api/conversations"
```

Response includes:
- `conversation_id` – use this in subsequent calls
- `conversation_status`

You can compose a GUI link as:
```text
$OPENHANDS_APP_BASE/conversations/{conversation_id}
```

## Get conversation details

```bash
curl -sS \
  -H "Authorization: Bearer $OPENHANDS_API_KEY" \
  "$OPENHANDS_APP_BASE/api/conversations/{conversation_id}"
```

Details include:
- `title`
- `status`
- `url` (runtime API base for this conversation)
- `session_api_key` (required header for runtime-hosted endpoints)

## List your conversations (titles, ids, statuses)

```bash
curl -sS -H "Authorization: Bearer $OPENHANDS_API_KEY" \
  "$OPENHANDS_APP_BASE/api/conversations?limit=100"
```

- The response has `results` (array) and `next_page_id` (for pagination). Iterate with `page_id` if needed.
- Each result entry includes `conversation_id`, `title`, `status`, `created_at`, and possibly `url` and `session_api_key`.

## Count events in a conversation (lightweight)

Use the events endpoint in reverse to fetch only the latest event and infer the count:

```bash
curl -sS -H "Authorization: Bearer $OPENHANDS_API_KEY" \
  "$OPENHANDS_APP_BASE/api/conversations/{conversation_id}/events?reverse=true&limit=1"
```

Interpretation:
- If it returns one event with `id = N`, total events ≈ `N + 1` (event ids start at 0)
- If the `events` array is empty, count is 0

## Find the model used (from recent actions)

Check the latest few events for `tool_call_metadata.model_response.model`:

```bash
curl -sS -H "Authorization: Bearer $OPENHANDS_API_KEY" \
  "$OPENHANDS_APP_BASE/api/conversations/{conversation_id}/events?reverse=true&limit=20" \
  | jq -r '.events[] | .tool_call_metadata.model_response.model? // empty' | head -n 1
```

Notes:
- Model is present on action events initiated by the LLM (e.g., tool calls)
- Increase `limit` if the last N events don’t contain an action from the LLM

## Runtime host fallback

Sometimes the app host may return an HTML maintenance page for certain endpoints. If so:
1) Get the per-conversation runtime URL and session key from details:
   - `GET /api/conversations/{conversation_id}` → fields: `url`, `session_api_key`
2) Call the runtime endpoint and include `X-Session-API-Key`:

```bash
curl -sS \
  -H "Authorization: Bearer $OPENHANDS_API_KEY" \
  -H "X-Session-API-Key: {session_api_key}" \
  "{runtime_url}/events?reverse=true&limit=1"
```

This works similarly for `/trajectory` and other conversation-scoped endpoints hosted by the runtime.

## Python helper (optional)

A minimal helper script can simplify usage. Example interface:

```bash
python scripts/cloud_api.py new-conversation --message "..."
python scripts/cloud_api.py details --id {conversation_id}
python scripts/cloud_api.py trajectory --id {conversation_id} \
  --runtime-url {runtime_url} --session-key {session_api_key}
```

See `scripts/cloud_api.py` for a reference implementation (uses `$OPENHANDS_API_KEY`). The helper also detects maintenance pages and surfaces errors.

## Where endpoints are defined (OpenHands server source)

- Conversations (create/list/details/start/stop):
  - `openhands/server/routes/manage_conversations.py`
- Conversation events and microagents:
  - `openhands/server/routes/conversation.py` (e.g., `GET /api/conversations/{conversation_id}/events`)
- Trajectory endpoint:
  - `openhands/server/routes/trajectory.py` (e.g., `GET /api/conversations/{conversation_id}/trajectory`)
- Basic user info:
  - `openhands/server/routes/git.py` (e.g., `GET /api/user/info`)

## Tips

- To avoid downloading the full trajectory, prefer the reverse events trick to compute counts
- If an endpoint returns HTML (maintenance), retry later or use the runtime URL with `X-Session-API-Key`
- Use pagination (`next_page_id`) for large conversation lists
