# Notes

## Why A Gateway

Directly integrating each model vendor into Aegis would spread provider-specific behavior across the backend. A gateway keeps Aegis stable and lets the server team switch providers without changing product-facing APIs.

## Required Behaviors

- Chat should return:
  - `conversation_id`
  - `summary`
  - `reply`
  - optional `suggestions`
  - optional raw provider metadata

- Diagnose should return:
  - `summary`
  - `severity`
  - `suggestions`

- Log analysis should return:
  - `summary`
  - `severity`
  - `matched_rules`
  - `suggestions`
  - `excerpt`

## Error Strategy

The gateway client should raise a dedicated client error on:

- missing base URL
- HTTP errors
- timeout/connect failures
- non-JSON responses where JSON is required
- missing required fields

`ai_provider.py` should catch that error and preserve the existing local fallback behavior.

## Compatibility

Implementation must stay Python 3.9 compatible:

- Use `Optional[T]` instead of `T | None`.
- Use `Tuple[...]` instead of `tuple[...]` where syntax compatibility matters.
- Avoid Python 3.10+ standard-library-only APIs.

## 2026-06-19 Implementation Note

First gateway target is `pi-agent`. Aegis sends `provider=pi-agent` and the configured model to the internal gateway. The gateway remains responsible for adapting to the actual pi-agent runtime or API shape.

Configured Aegis provider:

```text
AI_PROVIDER=internal_gateway
INTERNAL_AI_GATEWAY_PROVIDER=pi-agent
INTERNAL_AI_GATEWAY_MODEL=pi-agent
```
