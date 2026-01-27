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

### Phase 1: Basic Read Operations
- [ ] Initialize client with API key
- [ ] Search app conversations
- [ ] Get app conversation by ID
- [ ] Search sandboxes
- [ ] Get sandbox by ID
- [ ] Search events

### Phase 2: Write Operations
- [ ] Start app conversation
- [ ] Update app conversation
- [ ] Delete app conversation
- [ ] Pause/resume sandbox
- [ ] Delete sandbox

### Phase 3: Agent Server Integration
- [ ] Get agent server URL from sandbox
- [ ] Download trajectory
- [ ] Download/upload files
- [ ] Bash command execution

### Phase 4: Utilities
- [ ] Conversation summary
- [ ] Polling for status changes
- [ ] Event streaming (if WebSocket supported)

## Questions to Verify

1. Is the `/api/v1/` prefix used on app.all-hands.dev?
2. How does authentication work for V1 vs V0? Same API key?
3. Can we use the same OPENHANDS_API_KEY for both?
4. How do we get the agent_server URL from a conversation?

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
