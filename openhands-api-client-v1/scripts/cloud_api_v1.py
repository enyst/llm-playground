#!/usr/bin/env python3
"""
OpenHands Cloud API V1 Client

SAFETY: This script is designed to make minimal API calls.
- Use limit=1 for list operations during testing
- No loops that hit the API
- Each function makes at most ONE API call
"""

import os
import json
import httpx
from datetime import datetime

# Configuration
API_KEY = os.environ.get("OPENHANDS_API_KEY")
BASE_URL = os.environ.get("OPENHANDS_APP_BASE", "https://app.all-hands.dev")
API_V1_URL = f"{BASE_URL}/api/v1"

def get_headers():
    """Get headers for API requests."""
    if not API_KEY:
        raise ValueError("OPENHANDS_API_KEY environment variable is not set")
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

def pretty_print(data, title=None):
    """Pretty print JSON data."""
    if title:
        print(f"\n{'='*60}")
        print(f" {title}")
        print(f"{'='*60}")
    print(json.dumps(data, indent=2, default=str))

# =============================================================================
# App Conversations
# =============================================================================

def search_app_conversations(limit: int = 1):
    """Search app conversations. ONE API call."""
    url = f"{API_V1_URL}/app-conversations/search"
    params = {"limit": limit}
    
    print(f"[API CALL] GET {url} params={params}")
    response = httpx.get(url, headers=get_headers(), params=params, timeout=30)
    response.raise_for_status()
    return response.json()

def get_app_conversation(conversation_id: str):
    """Get a single app conversation by ID. ONE API call.
    
    Uses the batch endpoint since single-ID endpoint may have issues.
    """
    url = f"{API_V1_URL}/app-conversations"
    params = {"ids": conversation_id}
    
    print(f"[API CALL] GET {url} params={params}")
    response = httpx.get(url, headers=get_headers(), params=params, timeout=30)
    response.raise_for_status()
    result = response.json()
    # Batch endpoint returns a list
    if result and len(result) > 0:
        return result[0]
    return None

def count_app_conversations():
    """Count all app conversations. ONE API call."""
    url = f"{API_V1_URL}/app-conversations/count"
    
    print(f"[API CALL] GET {url}")
    response = httpx.get(url, headers=get_headers(), timeout=30)
    response.raise_for_status()
    return response.json()

# =============================================================================
# Sandboxes
# =============================================================================

def search_sandboxes(limit: int = 1):
    """Search sandboxes. ONE API call."""
    url = f"{API_V1_URL}/sandboxes/search"
    params = {"limit": limit}
    
    print(f"[API CALL] GET {url} params={params}")
    response = httpx.get(url, headers=get_headers(), params=params, timeout=30)
    response.raise_for_status()
    return response.json()

# =============================================================================
# Sandbox Specs
# =============================================================================

def search_sandbox_specs(limit: int = 1):
    """Search sandbox specs. ONE API call."""
    url = f"{API_V1_URL}/sandbox-specs/search"
    params = {"limit": limit}
    
    print(f"[API CALL] GET {url} params={params}")
    response = httpx.get(url, headers=get_headers(), params=params, timeout=30)
    response.raise_for_status()
    return response.json()

# =============================================================================
# Events
# =============================================================================

def search_events(conversation_id: str, limit: int = 1):
    """Search events for a conversation. ONE API call."""
    url = f"{API_V1_URL}/conversation/{conversation_id}/events/search"
    params = {"limit": limit}
    
    print(f"[API CALL] GET {url} params={params}")
    response = httpx.get(url, headers=get_headers(), params=params, timeout=30)
    response.raise_for_status()
    return response.json()

def count_events(conversation_id: str):
    """Count events for a conversation. ONE API call."""
    url = f"{API_V1_URL}/conversation/{conversation_id}/events/count"
    
    print(f"[API CALL] GET {url}")
    response = httpx.get(url, headers=get_headers(), timeout=30)
    response.raise_for_status()
    return response.json()

# =============================================================================
# Agent Server Events
# =============================================================================

def agent_search_events(
    agent_server_url: str,
    session_api_key: str,
    conversation_id: str,
    limit: int = 1,
):
    """Search events for a conversation via agent server. ONE API call."""
    url = f"{agent_server_url}/api/conversations/{conversation_id}/events/search"
    params = {"limit": limit}
    headers = get_agent_server_headers(session_api_key)

    print(f"[API CALL] GET {url} params={params}")
    response = httpx.get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def agent_count_events(
    agent_server_url: str,
    session_api_key: str,
    conversation_id: str,
):
    """Count events for a conversation via agent server. ONE API call."""
    url = f"{agent_server_url}/api/conversations/{conversation_id}/events/count"
    headers = get_agent_server_headers(session_api_key)

    print(f"[API CALL] GET {url}")
    response = httpx.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


# =============================================================================
# Users
# =============================================================================

def get_current_user():
    """Get current authenticated user. ONE API call."""
    url = f"{API_V1_URL}/users/me"
    
    print(f"[API CALL] GET {url}")
    response = httpx.get(url, headers=get_headers(), timeout=30)
    response.raise_for_status()
    return response.json()

# =============================================================================
# Write Operations - Phase 2
# =============================================================================

def start_app_conversation(
    initial_message: str,
    selected_repository: str | None = None,
    selected_branch: str | None = None,
    title: str | None = None,
):
    """Start a new app conversation. ONE API call.
    
    WARNING: This creates a sandbox which may incur costs.
    """
    url = f"{API_V1_URL}/app-conversations"
    
    # Build the request payload
    payload = {
        "initial_message": {
            "role": "user",
            "content": [{"type": "text", "text": initial_message}],
            "run": True,  # Auto-run after sending
        }
    }
    
    if selected_repository:
        payload["selected_repository"] = selected_repository
    if selected_branch:
        payload["selected_branch"] = selected_branch
    if title:
        payload["title"] = title
    
    print(f"[API CALL] POST {url}")
    print(f"[PAYLOAD] {json.dumps(payload, indent=2)}")
    response = httpx.post(url, headers=get_headers(), json=payload, timeout=120)
    response.raise_for_status()
    return response.json()

def resume_sandbox(sandbox_id: str):
    """Resume a paused sandbox. ONE API call."""
    url = f"{API_V1_URL}/sandboxes/{sandbox_id}/resume"
    
    print(f"[API CALL] POST {url}")
    response = httpx.post(url, headers=get_headers(), timeout=60)
    response.raise_for_status()
    return response.json()

def pause_sandbox(sandbox_id: str):
    """Pause a running sandbox. ONE API call."""
    url = f"{API_V1_URL}/sandboxes/{sandbox_id}/pause"
    
    print(f"[API CALL] POST {url}")
    response = httpx.post(url, headers=get_headers(), timeout=60)
    response.raise_for_status()
    return response.json()

def download_trajectory(conversation_id: str, output_file: str | None = None):
    """Download conversation trajectory as zip. ONE API call."""
    url = f"{API_V1_URL}/app-conversations/{conversation_id}/download"
    
    print(f"[API CALL] GET {url}")
    response = httpx.get(url, headers=get_headers(), timeout=60)
    response.raise_for_status()
    
    if output_file:
        with open(output_file, "wb") as f:
            f.write(response.content)
        print(f"[SAVED] {output_file} ({len(response.content)} bytes)")
        return {"file": output_file, "size": len(response.content)}
    else:
        return {"size": len(response.content), "content_type": response.headers.get("content-type")}

def get_start_task(task_id: str):
    """Get start task status. ONE API call.
    
    The start task tracks the async process of creating a conversation.
    When status is READY, app_conversation_id will be populated.
    """
    url = f"{API_V1_URL}/app-conversations/start-tasks"
    params = {"ids": task_id}
    
    print(f"[API CALL] GET {url} params={params}")
    response = httpx.get(url, headers=get_headers(), params=params, timeout=30)
    response.raise_for_status()
    result = response.json()
    # Returns a list, get the first item
    if result and len(result) > 0:
        return result[0]
    return None

# =============================================================================
# Agent Server Operations - Phase 3
# These run against the sandbox's agent server URL, not the app server
# =============================================================================

def get_agent_server_headers(session_api_key: str):
    """Get headers for Agent Server requests."""
    return {
        "X-Session-API-Key": session_api_key,
        "Content-Type": "application/json",
    }

def agent_execute_bash(agent_server_url: str, session_api_key: str, command: str, cwd: str | None = None):
    """Execute a bash command in the sandbox. ONE API call."""
    url = f"{agent_server_url}/api/bash/execute_bash_command"
    headers = get_agent_server_headers(session_api_key)
    payload = {"command": command, "timeout": 30}
    if cwd:
        payload["cwd"] = cwd
    
    print(f"[API CALL] POST {url}")
    print(f"[PAYLOAD] {json.dumps(payload)}")
    response = httpx.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()

def agent_download_file(agent_server_url: str, session_api_key: str, path: str) -> bytes:
    """Download a file from the sandbox workspace. ONE API call.
    
    Path must be absolute (e.g., /workspace/project/file.txt).
    Returns raw bytes to support both text and binary files.
    """
    # Path must be absolute, keep the leading /
    if not path.startswith("/"):
        path = "/" + path
    url = f"{agent_server_url}/api/file/download{path}"
    headers = get_agent_server_headers(session_api_key)
    
    print(f"[API CALL] GET {url}")
    response = httpx.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.content

def agent_upload_file(agent_server_url: str, session_api_key: str, path: str, content: str):
    """Upload a file to the sandbox workspace. ONE API call.
    
    Uses multipart form upload as required by the Agent Server.
    """
    # Path must be absolute in the URL
    if not path.startswith("/"):
        path = "/" + path
    url = f"{agent_server_url}/api/file/upload{path}"
    headers = {"X-Session-API-Key": session_api_key}  # No Content-Type for multipart
    
    # Create multipart form data with actual filename
    filename = os.path.basename(path)
    files = {"file": (filename, content.encode(), "text/plain")}
    
    print(f"[API CALL] POST {url}")
    print(f"[CONTENT LENGTH] {len(content)} chars")
    response = httpx.post(url, headers=headers, files=files, timeout=30)
    response.raise_for_status()
    return response.json() if response.text else {"success": True}


# =============================================================================
# Main - Test ONE endpoint at a time
# =============================================================================

def run_test(name: str, func, *args, **kwargs):
    """Run a single test with error handling."""
    print(f"\n{'='*60}")
    print(f" TEST: {name}")
    print(f"{'='*60}")
    try:
        result = func(*args, **kwargs)
        print(json.dumps(result, indent=2, default=str))
        return result
    except httpx.HTTPStatusError as e:
        print(f"HTTP Error: {e.response.status_code}")
        print(f"Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None


if __name__ == "__main__":
    import sys
    
    if not API_KEY:
        print("ERROR: Set OPENHANDS_API_KEY environment variable")
        exit(1)
    
    print(f"Base URL: {BASE_URL}")
    print(f"API Key: {API_KEY[:10]}...{API_KEY[-4:]}")
    
    # Usage: python cloud_api_v1.py [test_name] [arg1] [arg2] ...
    # Read tests: search_conversations, count_conversations, get_conversation,
    #             search_sandboxes, search_sandbox_specs, get_user,
    #             search_events, count_events
    # Agent server tests: agent_search_events, agent_count_events, agent_bash,
    #                     agent_download, agent_upload
    # Write tests: start_conversation, resume_sandbox, pause_sandbox, download_trajectory
    
    test_name = sys.argv[1] if len(sys.argv) > 1 else "search_conversations"
    arg1 = sys.argv[2] if len(sys.argv) > 2 else None
    arg2 = sys.argv[3] if len(sys.argv) > 3 else None
    
    # Each test makes exactly ONE API call
    
    # === Read Operations ===
    if test_name == "search_conversations":
        run_test("Search App Conversations (limit=1)", search_app_conversations, limit=1)
    
    elif test_name == "count_conversations":
        run_test("Count App Conversations", count_app_conversations)
    
    elif test_name == "get_conversation":
        if not arg1:
            print("ERROR: Provide conversation_id as second argument")
            exit(1)
        run_test(f"Get App Conversation {arg1}", get_app_conversation, arg1)
    
    elif test_name == "search_sandboxes":
        run_test("Search Sandboxes (limit=1)", search_sandboxes, limit=1)
    
    elif test_name == "search_sandbox_specs":
        run_test("Search Sandbox Specs (limit=1)", search_sandbox_specs, limit=1)
    
    elif test_name == "get_user":
        run_test("Get Current User", get_current_user)
    
    elif test_name == "search_events":
        if not arg1:
            print("ERROR: Provide conversation_id as second argument")
            exit(1)
        run_test(f"Search Events for {arg1} (limit=5)", search_events, arg1, limit=5)
    
    elif test_name == "count_events":
        if not arg1:
            print("ERROR: Provide conversation_id as second argument")
            exit(1)
        run_test(f"Count Events for {arg1}", count_events, arg1)
    
    # === Write Operations (Phase 2) ===
    elif test_name == "start_conversation":
        # Usage: start_conversation "message" [repo] [branch]
        if not arg1:
            print("ERROR: Provide initial message as second argument")
            print("Usage: start_conversation 'Your message here' [owner/repo] [branch]")
            exit(1)
        repo = arg2
        branch = sys.argv[4] if len(sys.argv) > 4 else None
        run_test("Start App Conversation", start_app_conversation, arg1, repo, branch)
    
    elif test_name == "resume_sandbox":
        if not arg1:
            print("ERROR: Provide sandbox_id as second argument")
            exit(1)
        run_test(f"Resume Sandbox {arg1}", resume_sandbox, arg1)
    
    elif test_name == "pause_sandbox":
        if not arg1:
            print("ERROR: Provide sandbox_id as second argument")
            exit(1)
        run_test(f"Pause Sandbox {arg1}", pause_sandbox, arg1)
    
    elif test_name == "download_trajectory":
        if not arg1:
            print("ERROR: Provide conversation_id as second argument")
            exit(1)
        output_file = arg2 or f"trajectory_{arg1[:8]}.zip"
        run_test(f"Download Trajectory {arg1}", download_trajectory, arg1, output_file)
    
    elif test_name == "get_start_task":
        if not arg1:
            print("ERROR: Provide start_task_id as second argument")
            exit(1)
        run_test(f"Get Start Task {arg1}", get_start_task, arg1)
    
    # === Agent Server Operations (Phase 3) ===
    # These require: agent_server_url and session_api_key from a RUNNING sandbox
    elif test_name == "agent_search_events":
        # Usage: agent_search_events <agent_server_url> <session_api_key> <conversation_id>
        if len(sys.argv) < 5:
            print(f"ERROR: {test_name} <agent_server_url> <session_api_key> <conversation_id>")
            exit(1)
        agent_url = sys.argv[2]
        session_key = sys.argv[3]
        conversation_id = sys.argv[4]
        run_test(
            f"Agent Search Events {conversation_id} (limit=5)",
            agent_search_events,
            agent_url,
            session_key,
            conversation_id,
            limit=5,
        )

    elif test_name == "agent_count_events":
        # Usage: agent_count_events <agent_server_url> <session_api_key> <conversation_id>
        if len(sys.argv) < 5:
            print(f"ERROR: {test_name} <agent_server_url> <session_api_key> <conversation_id>")
            exit(1)
        agent_url = sys.argv[2]
        session_key = sys.argv[3]
        conversation_id = sys.argv[4]
        run_test(
            f"Agent Count Events {conversation_id}",
            agent_count_events,
            agent_url,
            session_key,
            conversation_id,
        )


    elif test_name == "agent_bash":
        # Usage: agent_bash <agent_server_url> <session_api_key> <command>
        if len(sys.argv) < 5:
            print("ERROR: agent_bash <agent_server_url> <session_api_key> <command>")
            exit(1)
        agent_url = sys.argv[2]
        session_key = sys.argv[3]
        command = sys.argv[4]
        run_test(f"Execute Bash: {command}", agent_execute_bash, agent_url, session_key, command)
    
    elif test_name == "agent_download":
        # Usage: agent_download <agent_server_url> <session_api_key> <path>
        if len(sys.argv) < 5:
            print("ERROR: agent_download <agent_server_url> <session_api_key> <path>")
            exit(1)
        agent_url = sys.argv[2]
        session_key = sys.argv[3]
        path = sys.argv[4]
        result = run_test(f"Download File: {path}", agent_download_file, agent_url, session_key, path)
        if result:
            print(f"\n--- File Content ({len(result)} bytes) ---")
            # Try to decode as UTF-8, show hex preview for binary
            try:
                text = result.decode("utf-8")
                print(text[:2000] if len(text) > 2000 else text)
            except UnicodeDecodeError:
                print(f"[Binary file, first 100 bytes hex]: {result[:100].hex()}")
    
    elif test_name == "agent_upload":
        # Usage: agent_upload <agent_server_url> <session_api_key> <path> <content>
        if len(sys.argv) < 6:
            print("ERROR: agent_upload <agent_server_url> <session_api_key> <path> <content>")
            exit(1)
        agent_url = sys.argv[2]
        session_key = sys.argv[3]
        path = sys.argv[4]
        content = sys.argv[5]
        run_test(f"Upload File: {path}", agent_upload_file, agent_url, session_key, path, content)
    
    else:
        print(f"Unknown test: {test_name}")
        print("\nRead Operations:")
        print("  search_conversations, count_conversations, get_conversation <id>")
        print("  search_sandboxes, search_sandbox_specs, get_user")
        print("  search_events <conv_id>, count_events <conv_id>")
        print("\nWrite Operations:")
        print("  start_conversation 'message' [repo] [branch]")
        print("  resume_sandbox <sandbox_id>")
        print("  pause_sandbox <sandbox_id>")
        print("  download_trajectory <conv_id> [output_file]")
        print("  get_start_task <task_id>")
        print("\nAgent Server Operations (Phase 3):")
        print("  agent_search_events <agent_server_url> <session_api_key> <conversation_id>")
        print("  agent_count_events <agent_server_url> <session_api_key> <conversation_id>")
        print("  agent_bash <agent_server_url> <session_api_key> <command>")
        print("  agent_download <agent_server_url> <session_api_key> <path>")
        print("  agent_upload <agent_server_url> <session_api_key> <path> <content>")
