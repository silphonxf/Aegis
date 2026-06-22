# Internal AI Gateway

## Goal

Build an internal AI gateway for Aegis so the backend can call one stable server-side AI interface while the gateway handles vendor-specific APIs such as OpenClaw, Ollama, OpenAI-compatible chat/completions, DeepSeek, Qwen, or future private models.

## Current State

Aegis currently routes AI calls through `code/backend/app/services/ai_provider.py`.

Existing provider modes:

- `AI_PROVIDER=openclaw`: calls `OpenClawClient`, currently shaped around a Responses-style endpoint.
- `AI_PROVIDER=ollama`: calls local Ollama through `offline_llm.py`.
- Other values fall back to local rule-based responses.

## Target Shape

Aegis should call an internal gateway using a stable API owned by this project. The gateway should normalize:

- authentication
- model names
- request payloads
- response text extraction
- JSON extraction for diagnosis/log analysis
- timeout and error handling
- fallback behavior
- audit-safe request/response metadata

## Key Files

- `code/backend/app/services/ai_provider.py`
- `code/backend/app/services/openclaw_client.py`
- `code/backend/app/services/offline_llm.py`
- `code/backend/app/core/config.py`
- `code/backend/app/schemas/ai.py`
- `code/backend/app/schemas/offline_ai.py`

## Initial API Proposal

Gateway base URL:

```text
INTERNAL_AI_GATEWAY_BASE_URL=https://ai-gateway.example.com
INTERNAL_AI_GATEWAY_API_KEY=...
INTERNAL_AI_GATEWAY_MODEL=...
AI_PROVIDER=internal_gateway
```

Gateway endpoints:

```text
POST /v1/chat
POST /v1/diagnose
POST /v1/log-analyze
GET  /healthz
```

The gateway can internally adapt to OpenClaw, Ollama, OpenAI-compatible providers, or other vendor APIs.

## Decisions

- Keep Aegis backend Python 3.9 compatible.
- Keep vendor-specific request formats out of API handlers.
- Prefer a dedicated gateway client over expanding `OpenClawClient` into a multi-provider client.
- Keep rule fallback in Aegis for resilience when the gateway is down.

## Next Steps

1. Add config fields for `internal_gateway`.
2. Add `internal_ai_gateway_client.py`.
3. Add provider branch in `ai_provider.py`.
4. Add tests for chat, diagnose, log analyze, and fallback paths.
5. Document `.env` examples and deployment expectations.

## Handoff

This thread tracks the design and implementation of an internal AI gateway integration for Aegis. Start by implementing the client and provider routing without changing frontend APIs.
