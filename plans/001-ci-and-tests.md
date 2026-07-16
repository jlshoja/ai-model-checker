# Plan 001: Add CI and a verification baseline (tests + GitHub Actions)

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat 5515cf6..HEAD -- check_models.py tests providers.json .github/workflows`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: LOW
- **Depends on**: none
- **Category**: dx | tests
- **Planned at**: commit `5515cf6`, 2026-07-15
- **Issue**: (omit)

## Why this matters

This repository currently has no CI and a thin test surface (one unit test file). Adding GitHub Actions that run the test suite on PRs/commits and expanding the verification baseline ensures regressions are caught automatically and makes future refactors safe. CI also enables protected branches and gives confidence to rotate secrets and perform maintenance.

## Current state

- `check_models.py` — single-file CLI + providers implementation. (Orchestration, provider classes, helpers, and reporting live here.)
- `tests/test_providers.py` — unit tests that monkeypatch requests.Session; good structural pattern for new tests.
- `providers.json` — configuration used by the CLI.
- No `.github/workflows` directory currently exists.

Excerpts (confirm these exact snippets exist before proceeding):

- `check_models.py:336-339` — provider class registration:

  PROVIDER_CLASSES = {
      "openai": OpenAICompatibleProvider,
      "anthropic": AnthropicCompatibleProvider,
  }

- `tests/test_providers.py:62-76` — example test structure:

  def test_openai_fetch_and_plain_success(monkeypatch):
      cfg = ProviderConfig(name="p", type="openai", base_url="https://x", api_key="k")
      get_resp = DummyResp(status_code=200, json_data={"data": [{"id": "m1"}, {"id": "m2"}]})
      post_resp = DummyResp(status_code=200, json_data={"choices": [{"message": {"content": "OK"}}]})
      session = make_session(monkeypatch, get_resp, post_resp)
      monkeypatch.setattr('check_models.requests.Session', lambda: session)

      p = OpenAICompatibleProvider(cfg, timeout=5, test_prompt="hi", max_tokens=2)
      p.session = session
      models = p.fetch_models()
      assert models == ["m1", "m2"]

## Commands you will need

- Install deps (local/CI): `python -m pip install -r requirements.txt` → exit 0
- Run tests: `pytest -q` → all tests pass
- Lint/typecheck: no formal linter in repo; skip

## Scope

In scope (files you may create or modify):
- `.github/workflows/ci.yml` (create)
- `tests/test_cli_smoke.py` (create)
- `tests/conftest.py` (create)

Out of scope (do NOT touch):
- `check_models.py` (no functional changes in this plan)
- `providers.json` (do not change provider entries or keys)

## Git workflow

- Branch: `advisor/001-add-ci-tests`
- Commit per logical unit (workflow file separate from tests). Example message style: `ci: add github actions workflow for pytest` and `test: add CLI smoke tests with session stub`.
- Do NOT push or open a PR unless instructed.

## Steps

### Step 1: Add a minimal GitHub Actions workflow

Create `.github/workflows/ci.yml` with a single workflow that runs on `push` and `pull_request` and does the following:

- Uses `actions/checkout@v4`.
- Uses `actions/setup-python@v4` to set up Python 3.11 (or the runner's default latest stable; match local dev if necessary).
- Installs dependencies with `python -m pip install -r requirements.txt`.
- Runs `pytest -q`.

Verification: `act` (if available) or rely on reading the file. Locally run `pytest -q` → expected: existing tests pass (exit 0).

### Step 2: Add a conftest fixture for session stubbing

Create `tests/conftest.py` providing a reusable `session_stub` fixture that mirrors the pattern used in `tests/test_providers.py` (a small factory to produce DummyResp-based sessions). This avoids repeating monkeypatch logic in new tests.

Verify: `pytest -q` → existing tests still pass.

### Step 3: Add a CLI smoke test (no network) using the stub

Create `tests/test_cli_smoke.py` which:

- Uses the `session_stub` fixture to inject a stubbed `requests.Session` before importing or constructing `OpenAICompatibleProvider` / `AnthropicCompatibleProvider` as needed.
- Exercises `run_checks()` with a single provider built from an in-memory `ProviderConfig` and confirms `run_checks` returns ModelResult objects for the stubbed models. Use the structure of `tests/test_providers.py` as a template.

Specific test cases to add:

- `test_run_checks_plain_success`: simulate `fetch_models()` returning two model IDs and `post` returning a 200 JSON with `choices` — assert returned results contain two `WORKING` ModelResult entries.
- `test_run_checks_streaming_ttft`: simulate streaming iter_lines similar to existing streaming test and assert returned object's `ttft_ms` is not None.

Verify: `pytest -q` → all tests pass, including the new ones.

### Step 4: Update README (optional small doc entry)

Add one sentence to README under "Run it" describing the one-command test run: `pytest -q` and mention CI will run tests on PRs. Keep the change minimal.

Verify: `pytest -q` → still passes.

## Test plan

- New tests: `tests/test_cli_smoke.py` (2 tests described above).
- Use `tests/test_providers.py` as the pattern for structuring stubs and monkeypatches.
- Verification: `pytest -q` → exit 0 and tests include the new tests (use `pytest -q -k cli_smoke` to run just the new tests).

## Done criteria

- [ ] `python -m pip install -r requirements.txt` exits 0
- [ ] `pytest -q` exits 0 and includes the new tests
- [ ] `.github/workflows/ci.yml` exists and matches the created file in this plan
- [ ] Only files in-scope are modified (verify with `git status --porcelain`)
- [ ] `plans/README.md` status row updated for Plan 001

## STOP conditions

- The code at the locations in "Current state" doesn't match the excerpts above.
- `pytest -q` fails on existing tests before adding new files.
- Creating the workflow conflicts with repository policy or existing workflows in `.github/workflows` (unexpected files found).

## Maintenance notes

- The workflow is intentionally minimal. If the project later adopts poetry or a lockfile, update the workflow to install from the lockfile.
- A reviewer should ensure the test stubs do not accidentally import live network calls.
