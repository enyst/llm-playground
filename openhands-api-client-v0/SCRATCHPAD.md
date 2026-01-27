# OpenHands API Client - Scratchpad

This document tracks findings, in-progress thoughts, and TODOs for improving the API client.

## Overview

The OpenHands Cloud API has two versions:
- **V0**: Legacy API (deprecated, scheduled for removal April 1, 2026)
- **V1**: New API using Software Agent SDK

Our current client targets V0. This scratchpad focuses on V0 completeness before migrating to V1.

## Source Locations

- **V0 API Implementation**: `~/repos/odie/openhands/server/routes/`
  - `manage_conversations.py` - Create/list/delete conversations, start/stop
  - `conversation.py` - Events, microagents, config, vscode-url, web-hosts
  - `trajectory.py` - Get trajectory
  - `settings.py` - Store/load settings
  - `git.py` - User info, repositories, installations
  - `files.py` - List files, upload, zip
  - `secrets.py` - Secrets management
  - `feedback.py` - Submit feedback

- **OpenAPI Spec**: `~/repos/oh-docs/openapi/openapi.json` (V0)
- **Official Docs**: [https://docs.openhands.dev/api-reference/](https://docs.openhands.dev/api-reference/)

## V0 API Endpoints - Coverage Status

### ✅ Implemented in Current Client

| Endpoint | Method | Client Method |
|----------|--------|--------------|
| `/api/conversations` | POST | `create_conversation()` |
| `/api/conversations` | GET | `list_conversations()` |
| `/api/conversations/{id}` | GET | `get_conversation()` |
| `/api/conversations/{id}/events` | GET | `get_events()` |
| `/api/conversations/{id}/trajectory` | GET | `get_trajectory()` |
| `/api/settings` | POST | `store_llm_settings()` |

### ✅ Implemented in This PR

| Endpoint | Method | Client Method |
|----------|--------|--------------|
| `/api/conversations/{id}` | DELETE | `delete_conversation()` |
| `/api/conversations/{id}/start` | POST | `start_conversation()` |
| `/api/conversations/{id}/stop` | POST | `stop_conversation()` |
| `/api/conversations/{id}/message` | POST | `send_message()` |
| `/api/conversations/{id}/list-files` | GET | `list_files()` |
| `/api/conversations/{id}/microagents` | GET | `get_microagents()` |
| `/api/conversations/{id}/vscode-url` | GET | `get_vscode_url()` |
| `/api/conversations/{id}/web-hosts` | GET | `get_web_hosts()` |
| `/api/conversations/{id}/config` | GET | `get_runtime_config()` |
| `/api/conversations/{id}/submit-feedback` | POST | `submit_feedback()` |
| `/api/settings` | GET | `get_settings()` |
| `/api/user/info` | GET | `get_user_info()` |

### ❌ Not Yet Implemented

| Endpoint | Method | Notes |
|----------|--------|-------|
| `/api/conversations/{id}/git/changes` | GET | Get git changes |
| `/api/conversations/{id}/git/diff` | GET | Get git diff |
| `/api/user/repositories` | GET | List user repositories |
| `/api/user/installations` | GET | List git provider installations |
| `/api/secrets` | GET/POST/DELETE | Manage secrets |

## Runtime URL Fallback

**Problem**: App host may return HTML maintenance page for certain endpoints.

**Solution**:
1. Get conversation details: `GET /api/conversations/{conversation_id}`
2. Extract `url` (runtime URL) and `session_api_key`
3. Call runtime directly with `X-Session-API-Key` header

```python
# Example fallback for trajectory
details = api.get_conversation(conversation_id)
runtime_url = details.get('url')
session_key = details.get('session_api_key')

# Direct runtime call
headers = {
    'Authorization': f'Bearer {api_key}',
    'X-Session-API-Key': session_key
}
response = requests.get(f"{runtime_url}/trajectory", headers=headers)
```

## Trajectory Download Challenges

**Size**: Trajectories can be very large (1000+ events, 10MB+ JSON)

**Strategies**:
1. **Count first**: Use `GET /events?reverse=true&limit=1` to get last event ID
2. **Paginate**: Download events in chunks if needed
3. **Summarize externally**: For very large trajectories, use OpenHands CLI

### Trajectory Summarization Flow

1. Download trajectory JSON to file
2. If too large for LLM context:
   - Run `openhands` CLI with summarization prompt
   - Use tmux for long-running sessions
3. Parse summary output

## Key Data Structures

### ConversationInfo (from get_conversation)

```json
{
  "conversation_id": "abc123",
  "title": "Fix bug #123",
  "status": "RUNNING|STOPPED|STARTING|ERROR|ARCHIVED",
  "runtime_status": "READY|ERROR",
  "created_at": "2024-01-01T00:00:00Z",
  "last_updated_at": "2024-01-01T00:00:00Z",
  "selected_repository": "owner/repo",
  "selected_branch": "main",
  "url": "https://runtime-xyz.example.com",
  "session_api_key": "session-key-here",
  "pr_number": ["123"]
}
```

### Event Structure

```json
{
  "id": 0,
  "source": "user|agent",
  "action": "message|run|read|write|...",
  "message": "...",
  "tool_call_metadata": {
    "model_response": {
      "model": "gpt-4-turbo"
    }
  }
}
```

### Trajectory Item (from trajectory endpoint)

Simplified representation of events for export/analysis.

## TODO List

### ✅ Completed
- [x] Add runtime URL fallback support to client
- [x] Add `get_settings()` method
- [x] Add `get_user_info()` method
- [x] Add `delete_conversation()` method
- [x] Add `start_conversation()` and `stop_conversation()` methods
- [x] Add `send_message()` method for ongoing conversations
- [x] Add `list_files()` method
- [x] Add `get_runtime_config()` method
- [x] Create trajectory download prompt for agents
- [x] Document trajectory summarization workflow
- [x] Update README with new methods

### 📋 Remaining
- [ ] Add git/changes and git/diff endpoints
- [ ] Add user/repositories and user/installations endpoints
- [ ] Add secrets management endpoints
- [ ] Add examples for common workflows
- [ ] Consider streaming support for large event downloads
- [ ] Add auto-detection of V1 vs V0 conversations

## Questions to Resolve

1. When does the runtime URL fallback become necessary? (Network partition? Maintenance?)
2. What's the max trajectory size we commonly see?
3. Should we add streaming support for large event downloads?
4. Should we auto-detect V1 vs V0 conversations?

## Notes from PR 105 (enyst/playground)

PR 105 introduced the initial API client. Key things it covers:
- Basic CRUD for conversations
- Event streaming with filtering
- LLM settings configuration
- GitHub commenting integration
- Polling mechanism

Things it doesn't have that we need:
- Runtime fallback
- User/settings retrieval
- File operations
- More conversation management (start/stop/delete)

## V1 API Preview

The V1 API uses different patterns:
- Conversations are UUIDs instead of short IDs
- Uses sandboxes instead of runtimes
- Events endpoint: `GET /api/v1/events/search?conversation_id__eq={id}`
- App conversations: `GET /api/v1/app-conversations`

We'll migrate to V1 after V0 is complete and stable.
