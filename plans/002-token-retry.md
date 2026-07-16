# Plan 002: Make token-parameter handling robust (retry with alternate param)

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. Update the status row for this plan in
> `plans/README.md` when finished.
>
> **Drift check (run first)**: `git diff --stat 5515cf6..HEAD -- check_models.py tests`.
> If `check_models.py` has changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: plans/001-ci-and-tests.md (recommended but not strictly required)
- **Category**: correctness
- **Planned at**: commit `5515cf6`, 2026-07-15

## Why this matters

The current heuristic in `check_models.py` chooses between the `max_tokens` and
`max_completion_tokens` request parameter based on `classify_model(model) == 'reasoning'`.
If this heuristic misclassifies a model, the test request may fail with a
400/parameter error and a working model will be reported as FAILED. Making the
client retry with the alternate parameter name when the response indicates an
unknown/unsupported parameter reduces false negatives and increases accuracy.

## Current state

- `check_models.py` — single-file implementation containing `_test_model_plain` in
  `OpenAICompatibleProvider` which sets `token_key` based on `classify_model(model)` and
  posts to `/chat/completions` with that key (see lines ~145-156 and 158-176).

Excerpts (confirm before starting):

- `check_models.py:145-156`:

  token_key = "max_completion_tokens" if classify_model(model) == "reasoning" else "max_tokens"
  payload = {
      "model": model,
      "messages": [{"role": "user", "content": self.test_prompt}],
      token_key: self.max_tokens,
  }

- `check_models.py:158-176` — current retry loop: one retry on 429, otherwise return FAILED on non-200.

Design constraints and conventions to follow (from repo):

- Tests use `requests.Session` monkeypatching and `DummyResp` pattern (see `tests/test_providers.py`) — add tests following that pattern.
- Do not change public CLI behavior or output CSV/JSON shapes in this plan; the change is internal to request construction and error handling.

## Commands you will need

- Run tests: `pytest -q` → all tests pass (including new ones)
- Install deps: `python -m pip install -r requirements.txt` → exit 0

## Scope

In scope:
- `check_models.py` (small focused edits only)
- `tests/test_providers.py` (add tests at bottom) or new test file `tests/test_token_param.py`

Out of scope:
- Any other modules or packaging changes

## Git workflow

- Branch: `advisor/002-token-retry`
- Commit message examples: `fix(provider): retry with alternate token param on param-related 400` and `test(provider): add token-param fallback tests`.

## Steps

### Step 1: Add targeted retry logic for parameter-related 400 errors (OpenAI-compatible)

Edit `OpenAICompatibleProvider._test_model_plain` (in `check_models.py`) as follows:

- Keep the existing 429 retry behavior unchanged.
- When a non-200 response is returned (after the existing 429 handling):
  1. Extract the error via existing `_extract_error(resp)` as today.
  2. If the status code is 400 (or 422) OR the extracted error message contains text indicating an unknown parameter (e.g. contains the substring `"max_tokens"` or `"max_completion_tokens"` or the word `unknown`), then attempt one additional request using the *alternate* token key: if the original used `max_tokens`, retry with `max_completion_tokens` and vice versa.
  3. If the retry returns 200, treat the model as WORKING and log at INFO that a retry succeeded with the alternate key (do not change the CSV schema). If the retry returns non-200, return FAILED as before, but include both attempts' short notes in the error field (keep it concise).

Implementation notes (exact changes):

- Local variable `token_key` stays first-determined as today.
- Build the `payload` as today.
- After receiving `resp` with non-200 (and not a handled 429), call `_extract_error(resp)` into `err`.
- If `resp.status_code in (400, 422)` OR any of the substrings `max_tokens` or `max_completion_tokens` appear in `err.lower()`, compute `alt_key = "max_completion_tokens" if token_key == "max_tokens" else "max_tokens"` and build `alt_payload` identical except using `alt_key` for the token count.
- Perform a second POST with `alt_payload`. If the second POST returns 200 and contains `choices`, return WORKING. Otherwise, return FAILED with an error string like `"first=HTTP 400: msg...; retry=HTTP 400: msg..."` (truncate each msg to 160 chars).

**Verify**: Run `pytest -q` → tests pass (existing + new). Also run `python -c "from check_models import OpenAICompatibleProvider, ProviderConfig; print('import ok')"` to ensure import doesn't break.

### Step 2: Add unit tests covering the fallback behavior

Create new tests (either append to `tests/test_providers.py` or create `tests/test_token_param.py`) with the following cases:

- `test_plain_param_retry_on_400`: Simulate a first POST response with status 400 and JSON error referencing the used param (e.g., `{"error": {"message": "unknown field 'max_tokens'"}}`), and simulate the retry POST returning 200 with `{"choices": [...]}`. Assert final ModelResult.status == `WORKING`.

- `test_plain_param_retry_fails`: Simulate first POST 400 with unknown-param message and retry POST 400 with another error. Assert final status == `FAILED` and that `r.error` includes both attempts (or at least indicates a retry occurred).

Test structure notes:

- Reuse `DummyResp` and `make_session` patterns already in `tests/test_providers.py` for constructing stubbed sessions and responses.
- Use `monkeypatch.setattr('check_models.requests.Session', lambda: session)` as in existing tests.

**Verify**: `pytest -q` → the two new tests pass and existing tests still pass.

### Step 3: Update logging message (non-behavioral)

If retry succeeds with alternate key, log an INFO message: `logger.info("%s: retried with alternate token key '%s' and succeeded for model %s", self.cfg.name, alt_key, model)`.

Verify: Running the relevant unit test with `-s` shows the log line, but tests should not assert on logs.

## Test plan

- New tests: `test_plain_param_retry_on_400`, `test_plain_param_retry_fails`.
- Pattern: follow `tests/test_providers.py` structure.
- Verification: `pytest -q` → all tests pass.

## Done criteria

- [ ] `python -m pip install -r requirements.txt` exits 0
- [ ] `pytest -q` exits 0 and includes the two new tests
- [ ] No changes outside the in-scope files
- [ ] `plans/README.md` status row updated for Plan 002

## STOP conditions

- The code excerpts do not match live `check_models.py`.
- `pytest -q` fails on existing tests before changes.
- Implementing the retry requires changing provider-level public behavior or output shape (stop and consult). This plan only changes client-side retry logic and logs.

## Maintenance notes

- This change reduces false negatives by trying the alternate token parameter. If new provider types surface that require different parameter keys, consider a configurable mapping in `providers.json` (out of scope for this plan).
- A reviewer should ensure the retry does not create spurious extra API calls when a request legitimately fails for other reasons.
