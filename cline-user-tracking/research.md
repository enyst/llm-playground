# Cline User Tracking — Comprehensive Analysis

Scope:
- Identify all telemetry, analytics, and tracking in the Cline codebase
- Enumerate the exact user-related data collected and when it is captured
- Show where that data is sent (domains/endpoints) with code evidence
- Provide GitHub permalinks (pinned to commit ba98b44504d81ea2a261a7a18bf894b4893579c3)

Repository analyzed: https://github.com/cline/cline (@ ba98b44504d8, 2025-11-10 UTC)

Executive summary:
- Cline collects usage and error telemetry primarily via PostHog, configured to send to data.cline.bot. Optional OpenTelemetry export can also be enabled via env vars and will send to a configured OTLP endpoint.
- Telemetry respects both the IDE’s global telemetry setting and the extension’s own telemetry preference. In CLI mode, telemetry is controlled via an env var.
- If a user signs in to a Cline account, telemetry can be associated with that account (email, displayName, internal id). Otherwise, events are associated to a machine-derived or generated distinct id.
- The code is designed to avoid collecting source code or full prompt text; many events record only counts, lengths, or keys (not values), and long error messages are truncated.


1) Telemetry architecture and destinations

- Telemetry service and providers
  - Telemetry service orchestrates event capture and metadata injection
    - Telemetry metadata included with every event: extension_version, platform and version, os_type, os_version, is_dev
      - TelemetryService.ts: [Telemetry metadata](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/TelemetryService.ts#L48-L62)
    - Central registry of event names (USER, TASK, UI, WORKSPACE, DICTATION)
      - TelemetryService.ts: [Event catalog](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/TelemetryService.ts#L85-L220)
    - Capture methods (regular and required) fan out to providers
      - TelemetryService.ts: [capture() and captureRequired()](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/TelemetryService.ts#L292-L311)

  - Provider factory supports PostHog and OpenTelemetry (fallback to no-op)
    - TelemetryProviderFactory.ts: [Factory and defaults](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/TelemetryProviderFactory.ts#L1-L68)

- PostHog configuration and target domain
  - Host is set to the Cline domain “https://data.cline.bot”; UI host is the PostHog cloud UI
    - posthog-config.ts: [Host config (data.cline.bot)](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/shared/services/config/posthog-config.ts#L37-L43)
  - PostHog telemetry provider sends events and can identify users
    - PostHogTelemetryProvider.ts: [capture() to PostHog](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/providers/posthog/PostHogTelemetryProvider.ts#L63-L81)
    - PostHogTelemetryProvider.ts: [identifyUser() (uuid, email, name, alias)](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/providers/posthog/PostHogTelemetryProvider.ts#L92-L113)
  - Error tracking also goes through PostHog with a separate API key
    - PostHogErrorProvider.ts: [error capture ("extension.error"), message capture, truncation, env tag](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/error/providers/PostHogErrorProvider.ts#L44-L91)
  - Exception event filter only forwards exceptions that appear to originate from Cline
    - PostHogClientProvider.ts: [before_send filter for $exception](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/providers/posthog/PostHogClientProvider.ts#L24-L61)
  - Feature flags are fetched via PostHog using the distinct id
    - PostHogFeatureFlagsProvider.ts: [getFeatureFlag/getFeatureFlagPayload](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/feature-flags/providers/PostHogFeatureFlagsProvider.ts#L31-L74)

- OpenTelemetry export (optional)
  - Controlled entirely by env vars; when enabled, events/metrics are exported to the configured OTLP endpoint (not set by default)
    - otel-config.ts: [Env-based configuration and validity checks](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/shared/services/config/otel-config.ts#L1-L64) and [validation](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/shared/services/config/otel-config.ts#L109-L142)
    - OpenTelemetryClientProvider.ts: [OTLP exporters setup (logs/metrics)](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/providers/opentelemetry/OpenTelemetryClientProvider.ts#L48-L115)

- Webview CSP allows connections to PostHog and Cline domains
  - WebviewProvider.ts: [connect-src includes *.posthog.com and *.cline.bot](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/core/webview/WebviewProvider.ts#L113)


2) Enabling/Disabling and association with user identity

- Respecting IDE and extension settings
  - TelemetryService.updateTelemetryState() checks host telemetry settings (VS Code) and per-user opt-in
    - TelemetryService.ts: [updateTelemetryState() + host gate](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/TelemetryService.ts#L254-L272)
  - Extension-level preference is stored and propagated
    - controller/index.ts: [updateTelemetrySetting() -> telemetryService.updateTelemetryState()](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/core/controller/index.ts#L332-L338)
  - On webview init, Cline applies the current telemetry preference
    - initializeWebview.ts: [apply telemetry opt-in on UI launch](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/core/controller/ui/initializeWebview.ts#L214-L217)
  - CLI mode uses POSTHOG_TELEMETRY_ENABLED env var
    - cli EnvService.GetTelemetrySettings(): [env-based enable/disable](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/cli/pkg/hostbridge/env.go#L107-L153)

- Distinct id and user association
  - A distinct id is initialized from node-machine-id or generated and stored in globalState; updated to Cline account id when user logs in
    - distinctId.ts: [ID derivation and fallback](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/logging/distinctId.ts#L16-L36), [setDistinctId/getDistinctId](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/logging/distinctId.ts#L52-L71)
  - When authenticated, Cline identifies account for telemetry (email, displayName, id) and resets feature flags
    - AuthService.ts: [sendAuthStatusUpdate -> telemetryService.identifyAccount() and feature flags reset](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/auth/AuthService.ts#L233-L264)
  - Telemetry provider’s identifyUser includes { uuid/email/name, alias: previous distinctId }
    - PostHogTelemetryProvider.ts: [identifyUser() payload](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/providers/posthog/PostHogTelemetryProvider.ts#L96-L113)


3) What data is tracked (by category)

Note: Most events include the Telemetry metadata: extension_version, platform/version, os_type/version, is_dev. Below focuses on additional properties.

- USER and AUTH
  - Start/success/failure/logout of auth, with provider name and reason
    - TelemetryService.ts: [AUTH events and methods](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/TelemetryService.ts#L341-L393)

- TASK lifecycle and messaging
  - task.created/restarted/completed with ulid and provider/model context; conversation_turn includes source, mode, token counts and totalCost if provided
    - TelemetryService.ts: [task.created|restarted|completed](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/TelemetryService.ts#L542-L572)
    - TelemetryService.ts: [conversation_turn + token usage structure](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/TelemetryService.ts#L582-L616)
    - TelemetryService.ts: [token usage event (counts only)](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/TelemetryService.ts#L623-L631)
  - Feedback, options selected/ignored, mode switch
    - TelemetryService.ts: [feedback/options/mode](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/TelemetryService.ts#L682-L707)

- Tool usage and MCP tools
  - Tool usage records tool name, autoApproved, success, provider/model and multi-root workspace context flags; can mark native tool calls
    - TelemetryService.ts: [tool_used + workspace context fields](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/TelemetryService.ts#L707-L740)
  - MCP tool calls record serverName, toolName, status, argumentKeys (not values), optional errorMessage
    - TelemetryService.ts: [mcp_tool_called (keys only)](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/TelemetryService.ts#L756-L777)

- Checkpoints and workspace telemetry
  - Checkpoint usage actions (shadow_git_initialized, commit_created, restored, diff_generated) with durations
    - TelemetryService.ts: [checkpoint events](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/TelemetryService.ts#L785-L801)
  - Workspace initialized/path resolved/search pattern and multi-root checkpoint stats (counts and booleans)
    - TelemetryService.ts: [workspace initialized/init_error](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/TelemetryService.ts#L1360-L1388)
    - TelemetryService.ts: [multi_root_checkpoint payload](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/TelemetryService.ts#L1404-L1420)
    - TelemetryService.ts: [path_resolved payload fields](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/TelemetryService.ts#L1436-L1452)
    - TelemetryService.ts: [workspace_search_pattern fields](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/TelemetryService.ts#L1468-L1484)

- Browser tool
  - Records viewport, remoteBrowser flags/host on start; actionCount, duration, actions[] on end; errors include errorType, errorMessage, optional context { action, url, isRemote, remoteBrowserHost, endpoint }
    - TelemetryService.ts: [browser start/end/error payloads](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/TelemetryService.ts#L847-L920)

- Terminal telemetry
  - Records success and method for terminal execution; capture reasons for failures, user interventions, and hang stages
    - TelemetryService.ts: [terminal events (execution/failure/intervention/hang)](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/TelemetryService.ts#L1298-L1344)

- UI interactions and model selection
  - Model selected/favorited and generic button clicks
    - TelemetryService.ts: [UI model/button events](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/TelemetryService.ts#L831-L839)
    - TelemetryService.ts: [model favorite toggled / button clicked](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/TelemetryService.ts#L999-L1015)

- Dictation (voice)
  - Start/stop/transcription completed/error; includes taskId (optional), durations, language, platform, success boolean
    - TelemetryService.ts: [dictation events and fields](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/TelemetryService.ts#L419-L466) and [completed/error variants](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/TelemetryService.ts#L487-L524)

- Mentions (context attachments)
  - Records mention types used and content lengths only; failures include errorType and truncated errorMessage; search results record queryLength (not query text), resultCount, type and isEmpty
    - TelemetryService.ts: [mention_used/failed/search_results with minimization](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/TelemetryService.ts#L1534-L1584)

- Model/provider errors and performance
  - Provider API errors truncate errorMessage to 500 chars; Gemini API performance: token counts, durations, cache stats, throughput
    - TelemetryService.ts: [provider_api_error + truncation](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/TelemetryService.ts#L1028-L1041)
    - TelemetryService.ts: [gemini_api_performance fields](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/TelemetryService.ts#L968-L987)

- Diff edit failures
  - Captures modelId, provider, errorType, isNativeToolCall
    - TelemetryService.ts: [diff_edit_failed payload](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/TelemetryService.ts#L812-L818)


4) Error tracking and destinations

- Error/event sending through PostHog with its own API key; exception autocapture disabled and filtered to Cline-origin errors
  - PostHogErrorProvider.ts: [logException/logMessage -> PostHog.capture()](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/error/providers/PostHogErrorProvider.ts#L44-L91)
  - PostHogClientProvider.ts: [before_send $exception filter](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/providers/posthog/PostHogClientProvider.ts#L24-L61)
  - posthog-config.ts: [errorTrackingApiKey and host=data.cline.bot](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/shared/services/config/posthog-config.ts#L31-L43)


5) Additional server calls to cline.bot related to user state

- Authentication and user info
  - The extension performs OAuth-like flows against api.cline.bot to obtain access/refresh tokens, then fetches the user profile; telemetry identify can use this info.
    - ClineAuthProvider.signIn(): [token exchange to /api/v1/auth/token](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/auth/providers/ClineAuthProvider.ts#L300-L339)
    - ClineAuthProvider.fetchRemoteUserInfo(): [GET /api/v1/users/me with Bearer workos:{token}](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/auth/providers/ClineAuthProvider.ts#L341-L359)
    - AuthService: [captureAuthStarted/Succeeded/Failed/LoggedOut](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/auth/AuthService.ts#L341-L393)

- Remote configuration for organizations
  - If logged in, Cline can query a remote configuration per organization from api.cline.bot; result can influence settings (e.g., telemetry enabled/disabled)
    - remote-config/fetch.ts: [GET /api/v1/organizations/{id}/remote-config (Bearer token)](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/core/storage/remote-config/fetch.ts#L1-L62)
    - remote-config/utils.ts: [telemetrySetting derived from remote config flag](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/core/storage/remote-config/utils.ts#L15-L18)

- MCP marketplace
  - Catalog fetched from Cline’s API; not user tracking per se, but included for completeness on network interactions with cline.bot
    - controller/index.ts: [GET {mcpBaseUrl}/marketplace -> cached](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/core/controller/index.ts#L720-L760)


6) Data minimization and privacy protections in code

- No code/prompt content captured in telemetry events; designs prefer counts and lengths
  - Mentions search records queryLength not the query text
    - TelemetryService.ts: [queryLength only](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/TelemetryService.ts#L1577-L1584)
  - MCP tool calls include only argumentKeys, not values
    - TelemetryService.ts: [argumentKeys only, not values](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/TelemetryService.ts#L756-L777)
  - Error messages truncated to a maximum of 500 characters
    - TelemetryService.ts: [MAX_ERROR_MESSAGE_LENGTH used in provider_api_error/mention_failed](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/TelemetryService.ts#L64-L67)

- Respect for host telemetry and extension setting; ability to opt out
  - PostHogTelemetryProvider honors telemetry level and opt-in; can fully opt-out
    - PostHogTelemetryProvider.ts: [isEnabled() + setOptIn() + getTelemetryLevel()](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/providers/posthog/PostHogTelemetryProvider.ts#L114-L139)

- CLI respects env var for telemetry on/off
  - env.go: [POSTHOG_TELEMETRY_ENABLED](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/cli/pkg/hostbridge/env.go#L107-L153)


7) Destination domains and endpoints (summary)

- Telemetry and error tracking: https://data.cline.bot (PostHog ingestion host configured by Cline)
  - posthog-config.ts: [host setting](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/shared/services/config/posthog-config.ts#L37-L43)
- Feature flags: fetched via PostHog client using distinct id (same host as above)
  - PostHogFeatureFlagsProvider.ts: [flag APIs via PostHog client](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/feature-flags/providers/PostHogFeatureFlagsProvider.ts#L45-L74)
- OpenTelemetry (optional): endpoint determined exclusively by env vars (OTLP); not set by default
  - otel-config.ts: [getValidOpenTelemetryConfig() null unless enabled + exporter configured](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/shared/services/config/otel-config.ts#L116-L142)
- Authentication and user APIs: https://api.cline.bot (auth, users/me, org remote-config)
  - ClineAuthProvider.ts: [token exchange + users/me](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/auth/providers/ClineAuthProvider.ts#L300-L359)
  - remote-config/fetch.ts: [/organizations/{id}/remote-config](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/core/storage/remote-config/fetch.ts#L1-L62)


Appendix: Additional references
- Telemetry service singleton and lazy init
  - telemetry/index.ts: [getTelemetryService() proxy](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/src/services/telemetry/index.ts#L25-L52)
- Public docs statement (for context; not code) that content is not collected
  - docs/more-info/telemetry.mdx: [Telemetry policy (docs)](https://github.com/cline/cline/blob/ba98b44504d81ea2a261a7a18bf894b4893579c3/docs/more-info/telemetry.mdx#L9-L25)
