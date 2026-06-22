# Handoff

## Objective

Add an internal AI gateway integration to Aegis so server-side AI routing can switch providers without changing frontend or API handler code.

## Current Branch State

Initial runtime integration has been implemented:

- config fields for `internal_gateway`
- `internal_ai_gateway_client.py`
- `AI_PROVIDER=internal_gateway` routing in `ai_provider.py`
- assistant router support for internal gateway routing
- pi-agent provider/model fields in the gateway payload
- unit tests for chat, diagnose, log analysis, and unconfigured fallback

## Recommended Implementation Order

1. Add settings:
   - `INTERNAL_AI_GATEWAY_BASE_URL`
   - `INTERNAL_AI_GATEWAY_API_KEY`
   - `INTERNAL_AI_GATEWAY_MODEL`
   - `INTERNAL_AI_GATEWAY_TIMEOUT_SECONDS`
   - optional endpoint path settings

2. Implement a client with methods:
   - `chat(...)`
   - `diagnose(...)`
   - `log_analyze(...)`

3. Wire `AI_PROVIDER=internal_gateway` in `ai_provider.py`.

4. Keep existing OpenClaw and Ollama paths unchanged.

5. Run:

```bash
.venv/bin/python -m pytest code/backend/tests
```

## Watchouts

- Do not remove current rule fallback.
- Keep Python 3.9 syntax.
- Avoid adding SDK dependencies unless necessary; current code uses `urllib.request`.
- Keep secrets in `.env`, not committed files.
