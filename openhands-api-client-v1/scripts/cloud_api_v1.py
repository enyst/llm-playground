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
    """Get a single app conversation by ID. ONE API call."""
    url = f"{API_V1_URL}/app-conversations/{conversation_id}"
    
    print(f"[API CALL] GET {url}")
    response = httpx.get(url, headers=get_headers(), timeout=30)
    response.raise_for_status()
    return response.json()

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
    
    # Usage: python cloud_api_v1.py [test_name] [conversation_id]
    # Tests: search_conversations, count_conversations, get_conversation,
    #        search_sandboxes, search_sandbox_specs, get_user,
    #        search_events, count_events
    
    test_name = sys.argv[1] if len(sys.argv) > 1 else "search_conversations"
    conv_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Each test makes exactly ONE API call
    if test_name == "search_conversations":
        run_test("Search App Conversations (limit=1)", search_app_conversations, limit=1)
    
    elif test_name == "count_conversations":
        run_test("Count App Conversations", count_app_conversations)
    
    elif test_name == "get_conversation":
        if not conv_id:
            print("ERROR: Provide conversation_id as second argument")
            exit(1)
        run_test(f"Get App Conversation {conv_id}", get_app_conversation, conv_id)
    
    elif test_name == "search_sandboxes":
        run_test("Search Sandboxes (limit=1)", search_sandboxes, limit=1)
    
    elif test_name == "search_sandbox_specs":
        run_test("Search Sandbox Specs (limit=1)", search_sandbox_specs, limit=1)
    
    elif test_name == "get_user":
        run_test("Get Current User", get_current_user)
    
    elif test_name == "search_events":
        if not conv_id:
            print("ERROR: Provide conversation_id as second argument")
            exit(1)
        run_test(f"Search Events for {conv_id} (limit=1)", search_events, conv_id, limit=1)
    
    elif test_name == "count_events":
        if not conv_id:
            print("ERROR: Provide conversation_id as second argument")
            exit(1)
        run_test(f"Count Events for {conv_id}", count_events, conv_id)
    
    else:
        print(f"Unknown test: {test_name}")
        print("Available: search_conversations, count_conversations, get_conversation,")
        print("           search_sandboxes, search_sandbox_specs, get_user,")
        print("           search_events, count_events")
