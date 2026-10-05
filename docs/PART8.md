# Part 8: OpenRouter connectivity

Completed 2026-10-05.

## Implementation

- `backend/app/openrouter.py`: async, non-streaming Chat Completions client using `https://openrouter.ai/api/v1/chat/completions`, fixed `openai/gpt-oss-120b`, and backend runtime `OPENROUTER_API_KEY`.
- Promoted existing `httpx2` 2.13.1 from test-only to runtime dependencies and updated `uv.lock`. This matched the current PyPI release when checked; no SDK is needed.
- Requests use low reasoning effort, excluded reasoning text, a 2048-token output limit, and `provider.require_parameters=true`. No automatic retries or model changes.
- Connection timeout: 10 seconds. Network operation timeout and total request deadline: 60 seconds.
- Safe errors distinguish missing configuration, rejected credentials, insufficient credits, denied requests, rate limits, provider/network failures, and timeouts. Raw provider bodies and credentials are not included in errors or logs.
- Checks HTTP errors and errors embedded in HTTP 200 responses. Rejects invalid JSON, missing/empty content, and incomplete or filtered completions.
- Optional `response_format` supports passing a JSON Schema. Parsing and validating AI board operations remains Part 9. No public AI route or chat UI was added.

## Verification

- Full backend suite: **101 passed** (68 existing plus 33 OpenRouter cases), 17.40 seconds. All AI tests use mocked HTTP; they need no real key or network.
- Coverage includes request/auth construction, model selection, compatible routing, structured-format forwarding, parsing, configuration and HTTP errors, embedded errors, transport failures, total timeout, truncated output, safe messages, and smoke-check success/failure.
- Docker build/static export and healthy startup: passed.
- Live check inside the running container: **passed**, `openai/gpt-oss-120b` returned exactly `4` for `2+2`.
- Initial live check reported missing configuration. The saved `.env` used `OPEN_ROUTER_API_KEY`; corrected the name to `OPENROUTER_API_KEY`, preserved its value, and recreated the container. The subsequent check succeeded.
- `.env` remains ignored by Git and excluded from the Docker build context. No key contents were printed.
- Python compilation and `git diff --check`: passed. Frontend source was unchanged; its test suites were not rerun.

Run the explicit live check (uses API credits):

```sh
docker compose exec -T app python -m app.check_openrouter
```

Compose injects the root `.env` at runtime. After editing it, run `docker compose up -d --force-recreate --wait` to reload it. Direct Python execution requires the variable in its environment; the client does not parse `.env` itself.

## Structured Outputs readiness

The public model endpoint listing was checked on 2026-10-05. Multiple providers advertised both `structured_outputs` and `response_format`, including CoreWeave, DeepInfra, Groq, and Cerebras. Support is per provider endpoint and can change. The client requires parameter-compatible routing and never silently switches models.

OpenRouter documents `response_format.type=json_schema`, a strict schema, and `provider.require_parameters=true`. Strict schema enforcement varies by provider, so Part 9 must validate every output locally before touching the database. No incompatibility was found in the current metadata; live board-schema tests remain Part 9. The Part 8 live call checked plain-text connectivity only.

Sources:

- [OpenRouter Structured Outputs](https://openrouter.ai/docs/guides/features/structured-outputs)
- [Model/provider endpoint metadata](https://openrouter.ai/api/v1/models/openai/gpt-oss-120b/endpoints)
- [OpenRouter error handling](https://openrouter.ai/docs/api_reference/errors-and-debugging)
- [httpx2 release metadata](https://pypi.org/pypi/httpx2/json)
