"""OpenHands Cloud API client for automation tasks.

This client targets the V0 (legacy) OpenHands API. V0 is deprecated but still
widely used. For V1 API, see the app_server routes in the main OpenHands repo.

Key V0 endpoints:
- /api/conversations - Create, list, get, delete conversations
- /api/conversations/{id}/events - Get events with pagination
- /api/conversations/{id}/trajectory - Get full trajectory
- /api/settings - Store/load LLM settings
- /api/user/info - Get user information
"""

import os
import time
from pathlib import Path
from typing import Any, Optional

import requests


class OpenHandsCloudAPI:
    """Client for interacting with OpenHands Cloud API (V0).

    The client supports both the main app host and direct runtime access
    for fallback scenarios (e.g., maintenance windows).

    Attributes:
        api_key: The OpenHands API key
        base_url: Base URL for the OpenHands Cloud API
        session: Requests session with auth headers configured
    """

    def __init__(
        self, api_key: Optional[str] = None, base_url: str = 'https://app.all-hands.dev'
    ):
        """Initialize the API client.

        Args:
            api_key: OpenHands API key. If not provided, will use OPENHANDS_API_KEY env var.
            base_url: Base URL for the OpenHands Cloud API. Can also be set via OPENHANDS_APP_BASE.
        """
        self.api_key = api_key or os.getenv('OPENHANDS_API_KEY')
        if not self.api_key:
            raise ValueError(
                'API key is required. Set OPENHANDS_API_KEY environment variable or pass api_key parameter.'
            )

        self.base_url = os.getenv('OPENHANDS_APP_BASE', base_url).rstrip('/')
        self.session = requests.Session()
        self.session.headers.update(
            {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            }
        )

    def list_conversations(self, limit: int = 100) -> list[dict[str, Any]]:
        """List conversations with pagination.

        Args:
            limit: Page size (max 100)

        Returns:
            Flattened list of conversation summaries
        """
        results: list[dict[str, Any]] = []
        page_id: str | None = None
        while True:
            params: dict[str, Any] = {'limit': limit}
            if page_id:
                params['page_id'] = page_id
            r = self.session.get(f'{self.base_url}/api/conversations', params=params)
            r.raise_for_status()
            data = r.json()
            results.extend(data.get('results', []))
            page_id = data.get('next_page_id')
            if not page_id:
                break
        return results

    def get_last_event_id(self, conversation_id: str) -> int | None:
        """Return the latest event id using a minimal query."""
        payload = self.get_events(conversation_id, reverse=True, limit=1)
        events = payload.get('events', [])
        return events[0]['id'] if events else None

    def get_recent_model(self, conversation_id: str) -> str | None:
        """Inspect a small recent window for model metadata and return first found."""
        payload = self.get_events(conversation_id, reverse=True, limit=20)
        return self._get_model_from_events(payload.get('events', []))

    def get_first_user_message(self, conversation_id: str) -> str | None:
        """Fetch earliest handful of events and return the first user message text if present."""
        payload = self.get_events(conversation_id, start_id=0, limit=20)
        for e in payload.get('events', []):
            if e.get('source') == 'user':
                # Try 'message' then 'content'
                msg = e.get('message') or e.get('content')
                if isinstance(msg, str) and msg.strip():
                    return msg.strip()
        return None

    def get_early_model(self, conversation_id: str) -> str | None:
        """Inspect the earliest small window for the first model reference."""
        payload = self.get_events(conversation_id, start_id=0, limit=20)
        return self._get_model_from_events(payload.get('events', []))


    def _get_model_from_events(self, events: list[dict[str, Any]]) -> str | None:
        """Extract model name from a list of events, checking common locations."""
        for e in events:
            m = ((e.get('tool_call_metadata') or {}).get('model_response') or {}).get('model')
            if isinstance(m, str):
                return m
            for k in ('model', 'llm_model', 'provider_model', 'selected_model'):
                v = e.get(k)
                if isinstance(v, str):
                    return v
            meta = e.get('metadata') or e.get('meta') or {}
            for k in ('model', 'llm_model', 'provider_model'):
                v = meta.get(k)
                if isinstance(v, str):
                    return v
            args = e.get('args') or {}
            for k in ('model', 'llm_model'):
                v = args.get(k)
                if isinstance(v, str):
                    return v
        return None

    def store_llm_settings(
        self,
        llm_model: str,
        llm_base_url: Optional[str] = None,
        llm_api_key: Optional[str] = None,
    ) -> dict[str, Any]:
        """Store LLM settings for the Cloud account.

        Args:
            llm_model: The LLM model to use (e.g., "gpt-4", "claude-3-sonnet")
            llm_base_url: Base URL for the LLM API (optional)
            llm_api_key: API key for the LLM provider (optional)

        Returns:
            Response from the settings API
        """
        settings_data = {'llm_model': llm_model}

        if llm_base_url:
            settings_data['llm_base_url'] = llm_base_url
        if llm_api_key:
            settings_data['llm_api_key'] = llm_api_key

        response = self.session.post(
            f'{self.base_url}/api/settings', json=settings_data
        )
        response.raise_for_status()
        return response.json()

    def create_conversation(
        self,
        initial_user_msg: str,
        repository: Optional[str] = None,
        selected_branch: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create a new conversation.

        Args:
            initial_user_msg: The initial message to start the conversation
            repository: Git repository name in format "owner/repo" (optional)
            selected_branch: Git branch to use (optional)

        Returns:
            Response containing conversation_id and status
        """
        conversation_data = {'initial_user_msg': initial_user_msg}

        if repository:
            conversation_data['repository'] = repository
        if selected_branch:
            conversation_data['selected_branch'] = selected_branch

        response = self.session.post(
            f'{self.base_url}/api/conversations', json=conversation_data
        )
        response.raise_for_status()
        return response.json()

    def create_conversation_from_files(
        self,
        main_prompt_path: str,
        repository: Optional[str] = None,
        append_common_tail: bool = True,
        common_tail_path: str = 'scripts/prompts/common_tail.j2',
    ) -> dict[str, Any]:
        """Create a conversation by reading a prompt file and optional common tail.

        Args:
            main_prompt_path: Path to the main prompt file
            repository: Optional repo in format "owner/repo"
            append_common_tail: If True, append the common tail file contents
            common_tail_path: Path to the common tail file
        """
        main_text = Path(main_prompt_path).read_text()
        if append_common_tail and Path(common_tail_path).exists():
            tail = Path(common_tail_path).read_text()
            initial_user_msg = f'{main_text}\n\n{tail}'
        else:
            initial_user_msg = main_text
        return self.create_conversation(
            initial_user_msg=initial_user_msg,
            repository=repository,
        )

    def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        """Get conversation status and details.

        Args:
            conversation_id: The conversation ID

        Returns:
            Conversation details including status
        """
        response = self.session.get(
            f'{self.base_url}/api/conversations/{conversation_id}'
        )
        response.raise_for_status()
        return response.json()

    def get_trajectory(self, conversation_id: str) -> dict[str, Any]:
        """Get the trajectory (event history) for a conversation.

        Args:
            conversation_id: The conversation ID

        Returns:
            Trajectory data with events
        """
        response = self.session.get(
            f'{self.base_url}/api/conversations/{conversation_id}/trajectory'
        )
        response.raise_for_status()
        return response.json()

    def get_events(
        self,
        conversation_id: str,
        start_id: int = 0,
        end_id: Optional[int] = None,
        reverse: bool = False,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Get events from a conversation with filtering and pagination.

        Args:
            conversation_id: The conversation ID
            start_id: Starting ID in the event stream (default: 0)
            end_id: Ending ID in the event stream (optional)
            reverse: Whether to retrieve events in reverse order (default: False)
            limit: Maximum number of events to return, 1-100 (default: 20)

        Returns:
            Events data with pagination info

        Examples:
            # Get latest 50 events in reverse order
            api.get_events(conv_id, reverse=True, limit=50)

            # Get events in a specific range (e.g., events 800-900)
            api.get_events(conv_id, start_id=800, end_id=900, limit=100)

            # Find condensation events in recent history
            events = api.get_events(conv_id, start_id=800, end_id=900, limit=100)
            condensations = [e for e in events['events']
                           if e.get('source') == 'agent' and
                              e.get('action') == 'condensation']
        """
        # Clamp limit to [1, 100]
        limit = max(1, min(100, int(limit)))
        params = {
            'start_id': start_id,
            'reverse': str(reverse).lower(),
            'limit': limit,
        }
        if end_id is not None:
            params['end_id'] = end_id

        response = self.session.get(
            f'{self.base_url}/api/conversations/{conversation_id}/events',
            params=params,
        )
        response.raise_for_status()
        return response.json()

    def poll_until_stopped(
        self, conversation_id: str, timeout: int = 1200, poll_interval: int = 300
    ) -> dict[str, Any]:
        """Poll conversation until it stops or times out.

        Args:
            conversation_id: The conversation ID
            timeout: Maximum time to wait in seconds (default: 20 minutes)
            poll_interval: Time between polls in seconds (default: 5 minutes)

        Returns:
            Final conversation status
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                conversation = self.get_conversation(conversation_id)
                status = conversation.get('status', '').upper()

                if status == 'STOPPED':
                    return conversation

                # Also stop if conversation is in an error state
                if status in ['FAILED', 'ERROR', 'CANCELLED']:
                    print(f'⚠️  Conversation ended with status: {status}')
                    return conversation

                print(
                    f'Conversation {conversation_id} status: {status}. Waiting {poll_interval}s...'
                )
                time.sleep(poll_interval)

            except Exception as e:
                print(f'Error polling conversation {conversation_id}: {e}')
                print('Stopping polling due to error.')
                raise

        raise TimeoutError(
            f'Conversation {conversation_id} did not stop within {timeout} seconds'
        )

    def post_github_comment(
        self, repo: str, issue_number: int, comment: str, token: str
    ) -> None:
        """Post a comment to a GitHub issue.

        Args:
            repo: Repository in format owner/repo
            issue_number: Issue number
            comment: Comment text
            token: GitHub token
        """
        url = f'https://api.github.com/repos/{repo}/issues/{issue_number}/comments'
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json',
        }
        data = {'body': comment}

        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        print(f'✅ Posted comment to GitHub issue #{issue_number}')

    # =========================================================================
    # Additional V0 API Methods
    # =========================================================================

    def get_settings(self) -> dict[str, Any]:
        """Load current user settings.

        Returns:
            Settings object with LLM configuration and preferences.
            Note: API keys are masked (only shows if they're set, not values)
        """
        response = self.session.get(f'{self.base_url}/api/settings')
        response.raise_for_status()
        return response.json()

    def get_user_info(self) -> dict[str, Any]:
        """Get information about the authenticated user.

        Returns:
            User info including name, email, and linked git providers
        """
        response = self.session.get(f'{self.base_url}/api/user/info')
        response.raise_for_status()
        return response.json()

    def delete_conversation(self, conversation_id: str) -> dict[str, Any]:
        """Delete a conversation.

        Args:
            conversation_id: The conversation ID to delete

        Returns:
            Confirmation response
        """
        response = self.session.delete(
            f'{self.base_url}/api/conversations/{conversation_id}'
        )
        response.raise_for_status()
        return response.json()

    def start_conversation(
        self,
        conversation_id: str,
        git_provider: Optional[str] = None,
    ) -> dict[str, Any]:
        """Start the agent loop for a conversation.

        Args:
            conversation_id: The conversation ID
            git_provider: Git provider type (e.g., 'github', 'gitlab')

        Returns:
            Conversation response with status
        """
        payload = {}
        if git_provider:
            payload['providers_set'] = {git_provider: True}
        else:
            payload['providers_set'] = {}

        response = self.session.post(
            f'{self.base_url}/api/conversations/{conversation_id}/start',
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    def stop_conversation(self, conversation_id: str) -> dict[str, Any]:
        """Stop a running conversation.

        Args:
            conversation_id: The conversation ID

        Returns:
            Confirmation response
        """
        response = self.session.post(
            f'{self.base_url}/api/conversations/{conversation_id}/stop'
        )
        response.raise_for_status()
        return response.json()

    def send_message(self, conversation_id: str, message: str) -> dict[str, Any]:
        """Send a message to an existing conversation.

        Args:
            conversation_id: The conversation ID
            message: The message text to send

        Returns:
            Confirmation response
        """
        response = self.session.post(
            f'{self.base_url}/api/conversations/{conversation_id}/message',
            json={'message': message},
        )
        response.raise_for_status()
        return response.json()

    def list_files(
        self, conversation_id: str, path: Optional[str] = None
    ) -> list[str]:
        """List files in the conversation workspace.

        Args:
            conversation_id: The conversation ID
            path: Optional subdirectory path

        Returns:
            List of file paths
        """
        params = {}
        if path:
            params['path'] = path

        response = self.session.get(
            f'{self.base_url}/api/conversations/{conversation_id}/list-files',
            params=params,
        )
        response.raise_for_status()
        return response.json()

    def get_runtime_config(self, conversation_id: str) -> dict[str, Any]:
        """Get runtime configuration for a conversation.

        Returns runtime_id and session_id which can be used for direct
        runtime access when the main API is unavailable.

        Args:
            conversation_id: The conversation ID

        Returns:
            Dict with 'runtime_id' and 'session_id' keys
        """
        response = self.session.get(
            f'{self.base_url}/api/conversations/{conversation_id}/config'
        )
        response.raise_for_status()
        return response.json()

    def get_vscode_url(self, conversation_id: str) -> Optional[str]:
        """Get VS Code URL for a conversation (deprecated in V1).

        Args:
            conversation_id: The conversation ID

        Returns:
            VS Code URL or None if not available
        """
        response = self.session.get(
            f'{self.base_url}/api/conversations/{conversation_id}/vscode-url'
        )
        response.raise_for_status()
        data = response.json()
        return data.get('vscode_url')

    def get_web_hosts(self, conversation_id: str) -> Optional[list[str]]:
        """Get web hosts used by the runtime (deprecated in V1).

        Args:
            conversation_id: The conversation ID

        Returns:
            List of host URLs or None if not available
        """
        response = self.session.get(
            f'{self.base_url}/api/conversations/{conversation_id}/web-hosts'
        )
        response.raise_for_status()
        data = response.json()
        return data.get('hosts')

    def get_microagents(self, conversation_id: str) -> list[dict[str, Any]]:
        """Get microagents loaded for a conversation.

        Args:
            conversation_id: The conversation ID

        Returns:
            List of microagent objects with name, type, content, triggers
        """
        response = self.session.get(
            f'{self.base_url}/api/conversations/{conversation_id}/microagents'
        )
        response.raise_for_status()
        data = response.json()
        return data.get('microagents', [])

    def submit_feedback(
        self,
        conversation_id: str,
        feedback_type: str,
        feedback_text: str,
        event_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Submit feedback for a conversation.

        Args:
            conversation_id: The conversation ID
            feedback_type: Type of feedback (e.g., 'positive', 'negative')
            feedback_text: Feedback description
            event_id: Optional event ID the feedback relates to

        Returns:
            Confirmation response
        """
        payload = {
            'feedback_type': feedback_type,
            'feedback_text': feedback_text,
        }
        if event_id is not None:
            payload['event_id'] = event_id

        response = self.session.post(
            f'{self.base_url}/api/conversations/{conversation_id}/submit-feedback',
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    # =========================================================================
    # Runtime Fallback Support
    # =========================================================================

    def get_trajectory_via_runtime(
        self,
        conversation_id: str,
        timeout: int = 300,
    ) -> dict[str, Any]:
        """Get trajectory using direct runtime access (fallback).

        Use this when the main API returns errors or maintenance pages.
        Requires an active (running) conversation.

        Args:
            conversation_id: The conversation ID
            timeout: Request timeout in seconds (default: 5 minutes)

        Returns:
            Trajectory data with events

        Raises:
            ValueError: If runtime URL or session key not available
        """
        details = self.get_conversation(conversation_id)
        runtime_url = details.get('url')
        session_key = details.get('session_api_key')

        if not runtime_url or not session_key:
            raise ValueError(
                'Runtime URL or session key not available. '
                'Conversation may be stopped or archived.'
            )

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'X-Session-API-Key': session_key,
        }
        response = requests.get(
            f'{runtime_url}/trajectory',
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

    def get_events_via_runtime(
        self,
        conversation_id: str,
        start_id: int = 0,
        limit: int = 100,
        reverse: bool = False,
        timeout: int = 60,
    ) -> dict[str, Any]:
        """Get events using direct runtime access (fallback).

        Args:
            conversation_id: The conversation ID
            start_id: Starting event ID
            limit: Maximum events to return (1-100)
            reverse: Whether to return in reverse order
            timeout: Request timeout in seconds

        Returns:
            Events data with pagination info

        Raises:
            ValueError: If runtime URL or session key not available
        """
        details = self.get_conversation(conversation_id)
        runtime_url = details.get('url')
        session_key = details.get('session_api_key')

        if not runtime_url or not session_key:
            raise ValueError(
                'Runtime URL or session key not available. '
                'Conversation may be stopped or archived.'
            )

        limit = max(1, min(100, int(limit)))
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'X-Session-API-Key': session_key,
        }
        params = {
            'start_id': start_id,
            'limit': limit,
            'reverse': str(reverse).lower(),
        }
        response = requests.get(
            f'{runtime_url}/events',
            headers=headers,
            params=params,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def download_trajectory_to_file(
        self,
        conversation_id: str,
        output_path: Optional[str] = None,
        use_runtime_fallback: bool = False,
    ) -> str:
        """Download trajectory and save to a JSON file.

        Args:
            conversation_id: The conversation ID
            output_path: Output file path (default: trajectory_{id}.json)
            use_runtime_fallback: If True, use runtime URL instead of main API

        Returns:
            Path to the saved file
        """
        import json

        if output_path is None:
            output_path = f'trajectory_{conversation_id}.json'

        if use_runtime_fallback:
            trajectory = self.get_trajectory_via_runtime(conversation_id)
        else:
            trajectory = self.get_trajectory(conversation_id)

        with open(output_path, 'w') as f:
            json.dump(trajectory, f, indent=2, default=str)

        return output_path

    def get_conversation_summary(self, conversation_id: str) -> dict[str, Any]:
        """Get a summary of conversation state and statistics.

        Args:
            conversation_id: The conversation ID

        Returns:
            Dict with title, status, event count, model used, etc.
        """
        details = self.get_conversation(conversation_id)
        last_event_id = self.get_last_event_id(conversation_id)
        model = self.get_recent_model(conversation_id)
        first_msg = self.get_first_user_message(conversation_id)

        return {
            'conversation_id': conversation_id,
            'title': details.get('title'),
            'status': details.get('status'),
            'runtime_status': details.get('runtime_status'),
            'created_at': details.get('created_at'),
            'last_updated_at': details.get('last_updated_at'),
            'repository': details.get('selected_repository'),
            'branch': details.get('selected_branch'),
            'event_count': (last_event_id + 1) if last_event_id is not None else 0,
            'model': model,
            'first_message': first_msg[:200] if first_msg else None,
            'url': details.get('url'),
            'has_runtime': bool(details.get('url') and details.get('session_api_key')),
        }
