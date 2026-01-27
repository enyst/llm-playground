# OpenHands Cloud API Client (V1)

A Python client for the OpenHands Cloud API V1.

> **Work in Progress**: This client is being developed. See [SCRATCHPAD.md](SCRATCHPAD.md) for development notes.

## V1 vs V0

V1 introduces significant architectural changes:

| Feature | V0 (Legacy) | V1 (Current) |
|---------|-------------|--------------|
| Conversations | Short IDs | UUIDs |
| Runtime | Direct URLs | Sandboxes with exposed_urls |
| Trajectory | JSON endpoint | Zip file download |
| Events | Pagination by ID | Search with filters |

## Files

- `scripts/cloud_api.py` - V1 API client (in development)
- `SCRATCHPAD.md` - Development notes and API documentation

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENHANDS_API_KEY` | Yes | Your OpenHands Cloud API key |
| `OPENHANDS_APP_BASE` | No | Override base URL (default: `https://app.all-hands.dev`) |

## Status

🚧 Under construction - see SCRATCHPAD.md for progress.
