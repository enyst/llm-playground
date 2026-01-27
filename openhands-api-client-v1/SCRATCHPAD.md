# OpenHands API Client V1 - Scratchpad

This document tracks findings for the V1 API client implementation.

## Architecture Overview

V1 introduces a new architecture with two distinct servers:

### 1. App Server (V1)
- **Prefix**: `/api/v1/`
- **Purpose**: Manages app conversations, sandboxes, and high-level operations
- **Source**: `openhands/app_server/`
- **Base URL**: `https://app.all-hands.dev/api/v1/`

### 2. Agent Server
- **Prefix**: `/api/` (within sandbox)
- **Purpose**: Runs within each sandbox, handles events, files, bash commands
- **Source**: `openhands/agent_server/` (in software-agent-sdk repo)
- **Base URL**: Dynamic, obtained from sandbox's `exposed_urls`

## Key Differences from V0

| Aspect | V0 | V1 |
|--------|----|----|
| Conversation IDs | Short alphanumeric | UUIDs (32 hex chars) |
| Runtime | Direct runtime URLs | Sandboxes with exposed_urls |
| Events | `/api/conversations/{id}/events` | `/api/v1/conversation/{id}/events/search` |
| Start conversation | Create + separate start | Single `POST /api/v1/app-conversations` |
| Trajectory | `/api/conversations/{id}/trajectory` | `/api/v1/app-conversations/{id}/download` (returns zip) |

## V1 App Server Endpoints

### App Conversations (`/api/v1/app-conversations/`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/search` | GET | Search/list conversations with filters |
| `/count` | GET | Count conversations matching filters |
| `/` | GET | Batch get conversations by IDs |
| `/` | POST | Start a new conversation |
| `/{id}` | GET | Get conversation details |
| `/{id}` | PATCH | Update conversation |
| `/{id}` | DELETE | Delete conversation |
| `/{id}/skills` | GET | Get loaded skills |
| `/{id}/download` | GET | Download trajectory as zip |

### Sandboxes (`/api/v1/sandboxes/`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/search` | GET | Search/list sandboxes |
| `/` | GET | Batch get sandboxes by IDs |
| `/` | POST | Start a new sandbox |
| `/{id}/pause` | POST | Pause sandbox |
| `/{id}/resume` | POST | Resume sandbox |
| `/{id}` | DELETE | Delete sandbox |

### Events (`/api/v1/conversation/{id}/events/`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/search` | GET | Search events with filters |
| `/count` | GET | Count events |
| `/` | GET | Batch get events by IDs |

## Agent Server Endpoints (within sandbox)

These run at the `AGENT_SERVER` URL from sandbox's `exposed_urls`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/conversations/{id}/events/search` | GET | Search events |
| `/api/conversations/{id}/events/count` | GET | Count events |
| `/api/conversations/{id}/pause` | POST | Pause conversation |
| `/api/conversations/{id}/run` | POST | Run/resume conversation |
| `/api/file/download/{path}` | GET | Download file from workspace |
| `/api/file/upload/{path}` | POST | Upload file to workspace |
| `/api/file/download-trajectory/{id}` | GET | Download trajectory |
| `/api/bash/start_bash_command` | POST | Start bash command |
| `/api/bash/execute_bash_command` | POST | Execute bash command |
| `/api/vscode/url` | GET | Get VS Code URL |
| `/api/git/changes/{path}` | GET | Get git changes |
| `/api/git/diff/{path}` | GET | Get git diff |

## Data Models

### AppConversation
```json
{
  "id": "uuid",
  "title": "string",
  "sandbox_id": "string",
  "sandbox_status": "RUNNING|STARTING|PAUSED|ERROR|MISSING",
  "execution_status": "IDLE|RUNNING|PAUSED|WAITING_FOR_CONFIRMATION|FINISHED|ERROR|STUCK",
  "conversation_url": "string (runtime URL)",
  "session_api_key": "string",
  "selected_repository": "owner/repo",
  "selected_branch": "string",
  "git_provider": "github|gitlab|...",
  "created_at": "datetime",
  "updated_at": "datetime",
  "trigger": "string",
  "pr_number": ["string"],
  "public": "boolean",
  "sub_conversation_ids": ["uuid"]
}
```

### SandboxInfo
```json
{
  "id": "string",
  "status": "RUNNING|STARTING|PAUSED|ERROR|MISSING",
  "sandbox_spec_id": "string",
  "exposed_urls": [
    {
      "name": "AGENT_SERVER|VSCODE|...",
      "url": "string"
    }
  ],
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

## Implementation Plan

### Phase 1: Basic Read Operations ✅ COMPLETE
- [x] Initialize client with API key
- [x] Search app conversations (`GET /api/v1/app-conversations/search`)
- [x] Count app conversations (`GET /api/v1/app-conversations/count`) → Returns: 604
- [x] Get app conversation by ID (uses batch endpoint `?ids=`)
- [x] Search sandboxes (`GET /api/v1/sandboxes/search`)
- [x] Search events (`GET /api/v1/conversation/{id}/events/search`)
- [x] Count events (`GET /api/v1/conversation/{id}/events/count`)
- [x] Get current user (`GET /api/v1/users/me`)

### Phase 2: Write Operations ✅ COMPLETE
- [x] Start app conversation (`POST /api/v1/app-conversations`) → Returns start task
- [x] Get start task status (`GET /api/v1/app-conversations/start-tasks?ids=`)
- [x] Pause sandbox (`POST /api/v1/sandboxes/{id}/pause`)
- [x] Resume sandbox (`POST /api/v1/sandboxes/{id}/resume`)
- [ ] Update app conversation (`PATCH /api/v1/app-conversations/{id}`)
- [ ] Delete app conversation (`DELETE /api/v1/app-conversations/{id}`)
- [ ] Delete sandbox (`DELETE /api/v1/sandboxes/{id}`)

### Phase 3: Agent Server Integration
- [ ] Get agent server URL from sandbox's `exposed_urls`
- [ ] Download trajectory (`GET /api/v1/app-conversations/{id}/download`)
- [ ] Download/upload files via Agent Server
- [ ] Bash command execution via Agent Server

### Phase 4: Utilities
- [ ] Conversation summary
- [ ] Polling for status changes
- [ ] Event streaming (if WebSocket supported)

## Verified Answers

1. **Is the `/api/v1/` prefix used on app.all-hands.dev?** ✅ YES
2. **How does authentication work for V1 vs V0?** Same `Authorization: Bearer {API_KEY}` header
3. **Can we use the same OPENHANDS_API_KEY for both?** ✅ YES - same key works
4. **How do we get the agent_server URL from a conversation?**
   - Get conversation → `sandbox_id`
   - Get sandbox → `exposed_urls` array
   - Find entry where `name == "AGENT_SERVER"` → `url`
   - Note: `exposed_urls` is `null` when sandbox is PAUSED

## Observations from Testing

### Conversation Structure
- IDs are 32-char hex UUIDs (no dashes in API, but stored as UUID internally)
- `sandbox_status`: RUNNING, STARTING, PAUSED, ERROR, MISSING
- `execution_status`: Only populated when sandbox is RUNNING
- `conversation_url` and `session_api_key`: Only available when sandbox is RUNNING

### Sandbox Structure
- `session_api_key`: Available even when PAUSED (for authentication)
- `exposed_urls`: Only available when RUNNING
- `sandbox_spec_id`: Docker image reference (e.g., `ghcr.io/openhands/agent-server:7c91cbe-python`)

### Events
- Events contain full conversation configuration including:
  - LLM config (model, base_url, API keys - redacted)
  - Agent config (system prompt, condenser settings)
  - Workspace config
  - Secret registry (all secrets redacted with `**********`)
- First event is typically `ConversationStateUpdateEvent` with full state

### Web Client Config
- Requires authentication (contrary to router code - must be enforced by middleware)
- Returns 401 without auth

### Start Conversation Flow
1. `POST /api/v1/app-conversations` with `initial_message` → Returns `AppConversationStartTask` with `status: WORKING`
2. Poll `GET /api/v1/app-conversations/start-tasks?ids={task_id}` until `status: READY`
3. When ready, extract `app_conversation_id`, `sandbox_id`, `agent_server_url`
4. Agent automatically processes the initial message when `run: true`

### Endpoint Quirks
- Single-ID GET endpoints (e.g., `/app-conversations/{id}`) may return empty body
- Use batch endpoints instead (e.g., `/app-conversations?ids={id}`)
- Download trajectory may return 500 during service issues

### Test Conversation (2026-01-27)
- **Conversation ID**: `bb6a1b39c0d44d4db931e53d59897c77`
- **Sandbox ID**: `22Cnn1FqUu17shZhJ7b5Ka`
- **Message**: "Hello! This is a V1 API test..."
- **Response**: "Hello! I can see your message loud and clear, and I'm ready to help."
- **Title** (set by agent): "✅ V1 API Greeting Confirmation Test"
- **Cost**: ~$0.024

## Testing Notes

- **Be nice to the API**: No loops, bound polling, double-check scripts
- Test one endpoint at a time
- Save responses for reference
- Use `limit=1` for list operations during testing

## Source References

- V1 App Server: `~/repos/odie/openhands/app_server/`
- V1 Router: `~/repos/odie/openhands/app_server/v1_router.py`
- App Conversation Router: `~/repos/odie/openhands/app_server/app_conversation/app_conversation_router.py`
- Sandbox Router: `~/repos/odie/openhands/app_server/sandbox/sandbox_router.py`
- Event Router: `~/repos/odie/openhands/app_server/event/event_router.py`
- Agent Server OpenAPI: `~/repos/oh-docs/openapi/agent-sdk.json`
