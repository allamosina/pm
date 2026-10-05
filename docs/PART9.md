# Part 9: Structured AI board changes

Completed 2026-10-05. The backend supports AI changes; the sidebar remains Part 10.

## API

Authenticated `POST /api/chat` accepts:

```json
{
  "question": "Move the roadmap card to Done",
  "history": [
    {"role": "user", "content": "Which card covers the roadmap?"},
    {"role": "assistant", "content": "Align roadmap themes."}
  ]
}
```

Returns `{"reply":"...","board":{"columns":[],"cards":{},"revision":1}}` with the full authoritative board and `Cache-Control: no-store`.

Question/history text is limited to 4000 characters per message; history accepts at most 40 user/assistant messages. Client-supplied ownership, system messages, and extra fields are rejected. History is included only for that request and is never stored in SQLite or backend session state. Part 10 will keep it in browser memory and clear it on reload/logout.

The current board is read from SQLite for every call. Board text and history are explicitly treated as untrusted data. Only the authenticated identity determines ownership.

## Proposal contract and transaction

The exact generated OpenRouter response format is documented in [ai-response-schema.json](ai-response-schema.json), sourced from the Pydantic models in `backend/app/chat.py`.

A proposal contains a nonblank `reply` and `operations` (empty for reply-only, maximum 20):

| Type | Required fields beyond `type` |
| --- | --- |
| `create` | `column_id`, `title`, `details`, `position` (integer or null to append) |
| `edit` | `card_id`, `title`, `details` |
| `move` | `card_id`, `column_id`, `position` |

Operations run in order. Position is zero-based after removal of a moved card. New cards receive server UUIDs and cannot be referenced later in the same proposal; create them directly in their intended column. Delete/rename/ownership operations are unsupported. Titles/details use the existing manual API limits.

1. Read an authenticated board snapshot and revision, then release the read transaction.
2. Call the fixed OpenRouter model with the strict schema and parameter-compatible routing, without holding a database transaction during the network request.
3. Validate the entire JSON response locally. Recheck the session after the AI call.
4. In one write transaction, reject stale revisions, validate all IDs and sequential positions before the first SQL mutation, then reuse the manual create/edit/move functions.
5. Increment revision once for a changed batch (unchanged for no-op/reply-only), commit, and return the reply plus board. Any error rolls back the full batch and returns no success reply.

Database work runs in the thread pool so SQLite lock waits do not block async requests. Concurrent manual or AI writes invalidate older proposals, including reply-only results based on stale state.

Errors: 401 session missing/expired; 422 invalid client payload; 409 changed board; 429 provider rate limit; 503 missing configuration/database busy; 504 AI timeout; 502 invalid AI schema/references/positions or other provider failure. Provider authentication failures are 502, avoiding confusion with a user's session expiry.

## Verification

- Full backend suite initially passed **129 tests**, including 28 new chat cases.
- After adding sequential movement and simultaneous AI request checks, the chat suite passed **30 tests**; all **131 backend cases** have passed across these runs.
- Tests cover reply-only/no-op, current context/history, multi-card create/edit/move, empty-column and sequential moves, malformed/schema-invalid output, unknown/cross-user references, prevalidation before writes, injected partial-write rollback, stale manual edits, concurrent AI requests (one commit/one conflict), provider failures, and session invalidation during generation.
- Docker build and healthy startup passed; no dependencies or frontend source changed.
- Live authenticated container checks passed for reply-only (unchanged board) and two-card creation (one revision increment and persisted data). The following edit/move request returned schema-invalid output and HTTP 502; no success reply was returned.
- An isolated live edit/move check using the same client and schema, a temporary database, and disposable card succeeded without code changes. Verified the edited title/details and first position in Done. The earlier provider schema failure was not reproduced; its exact invalid fields were not retained, so no speculative fix was applied.
- Removed the disposable live account and cascading board data; SQLite foreign-key check passed. The diagnostic database was temporary and removed automatically. Existing accounts/boards were not changed.
- Python compile, JSON schema syntax, and `git diff --check` passed.

## Provider limitation

The successful live checks establish current connectivity and schema support, not guaranteed compliance on every response. Invalid/truncated output is rejected with no writes; the user can retry. No automatic retries, model substitution, or relaxed validation were introduced. OpenRouter itself notes that schema enforcement varies by provider: [Structured Outputs documentation](https://openrouter.ai/docs/guides/features/structured-outputs).

Manual API testing is available in `http://localhost:8000/docs` after signing in at the same host. The browser chat experience and session-history lifecycle tests are Part 10.
