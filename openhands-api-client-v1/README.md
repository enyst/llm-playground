# OpenHands Cloud API Client (V1)

A Python client for the OpenHands Cloud API V1.

## V1 Architecture

V1 uses a **two-tier architecture**:

1. **App Server** (`/api/v1/...`) - Orchestrates conversations and sandboxes
2. **Agent Server** (inside sandbox) - Executes commands, file operations

```
┌─────────────────────────────────────────────────────────────┐
│  App Server (app.all-hands.dev/api/v1/)                     │
│  - Conversation lifecycle (create, list, delete)            │
│  - Sandbox management (start, pause, resume)                │
│  - Event storage and retrieval                              │
│  - User info                                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ exposed_urls['AGENT_SERVER']
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Agent Server (dynamic URL per sandbox)                     │
│  - File upload/download                                     │
│  - Bash command execution                                   │
│  - VS Code access                                           │
│  - Git operations                                           │
└─────────────────────────────────────────────────────────────┘
```

## V1 vs V0

| Feature | V0 (Legacy) | V1 (Current) |
|---------|-------------|--------------|
| Conversations | Short alphanumeric IDs | UUIDs (32 hex chars) |
| Runtime | Direct runtime URLs | Sandboxes with `exposed_urls` |
| Trajectory | JSON endpoint | Zip file download |
| Events | Pagination by ID | Search with filters |
| Status | Deprecated (removal: April 2026) | Current |

## Quick Start

```bash
cd openhands-api-client-v1
python3 -m venv .venv
source .venv/bin/activate
pip install httpx

# Set your API key
export OPENHANDS_API_KEY="sk-oh-your-key-here"

# Run tests (each makes ONE API call)
python scripts/cloud_api_v1.py search_conversations
python scripts/cloud_api_v1.py count_conversations
python scripts/cloud_api_v1.py get_user
python scripts/cloud_api_v1.py search_sandboxes
python scripts/cloud_api_v1.py search_events <conversation_id>
```

## Files

- `scripts/cloud_api_v1.py` - V1 API client
- `SCRATCHPAD.md` - Development notes and detailed API documentation

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENHANDS_API_KEY` | Yes | Your OpenHands Cloud API key (prefix: `sk-oh-`) |
| `OPENHANDS_APP_BASE` | No | Override base URL (default: `https://app.all-hands.dev`) |

## API Endpoints

### App Conversations (`/api/v1/app-conversations/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/search` | List conversations with filters |
| GET | `/count` | Count conversations |
| GET | `/{id}` | Get conversation details |
| POST | `/` | Start new conversation |
| PATCH | `/{id}` | Update conversation |
| DELETE | `/{id}` | Delete conversation |
| GET | `/{id}/skills` | Get loaded skills |
| GET | `/{id}/download` | Download trajectory (zip) |

### Sandboxes (`/api/v1/sandboxes/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/search` | List sandboxes |
| GET | `?id=...` | Batch get sandboxes |
| POST | `/` | Start new sandbox |
| POST | `/{id}/pause` | Pause sandbox |
| POST | `/{id}/resume` | Resume sandbox |
| DELETE | `/{id}` | Delete sandbox |

### Events (`/api/v1/conversation/{id}/events/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/search` | Search events with filters |
| GET | `/count` | Count events |
| GET | `?id=...` | Batch get events |

### Users (`/api/v1/users/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/me` | Get current user info |

## Authentication

All endpoints use Bearer token authentication:

```
Authorization: Bearer sk-oh-your-api-key
```

Same API key works for both V0 and V1 endpoints.

## Status

- ✅ Phase 1: Read operations (complete)
- 🚧 Phase 2: Write operations (in progress)
- 📋 Phase 3: Agent Server integration
- 📋 Phase 4: Utilities
