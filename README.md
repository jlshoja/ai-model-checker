# ai-model-checker

A general, provider-agnostic tool to find out which AI models **actually work**
before you add them to `opencode.json` (or any other config). Listing a model
via `/models` doesn't mean it's usable — this tool does a real completion call
against every model and records the result.

## Supported provider types

| type        | list endpoint   | test endpoint    | auth header(s)                        |
|-------------|-----------------|------------------|----------------------------------------|
| `openai`    | `GET /models`   | `POST /chat/completions` | `Authorization: Bearer <key>`   |
| `anthropic` | `GET /models`*  | `POST /messages` | `x-api-key`, `anthropic-version`      |

\* if the router doesn't expose `/models`, add the model IDs manually — see below.

This already covers OpenAI-compatible routers like BlueSminds, NaraRouter, and
OpenRouter, and is ready for Anthropic-compatible routers like AgentRouter.
Adding a new provider *type* later just means adding one more class that
implements `fetch_models()` / `test_model()` in `check_models.py`.

## Setup

```bash
cd ai-model-checker
pip install -r requirements.txt
cp .env.example .env
# then edit .env and paste your real API keys
```

Edit `providers.json` to add/remove providers. Each provider needs:

```json
"my_provider": {
  "type": "openai",
  "base_url": "https://example.com/v1",
  "api_key_env": "MY_PROVIDER_API_KEY"
}
```

`api_key_env` is just the name of the environment variable in `.env` that
holds the key — the tool reads it via `python-dotenv`.

## Run it

```bash
# check every provider in providers.json
python check_models.py

# check just one provider
python check_models.py --providers bluesminds

# also generate an opencode.json containing only the working models
python check_models.py --generate-config opencode.generated.json

# tune concurrency / timeout
python check_models.py --concurrency 10 --timeout 15

# run tests locally
pytest -q
```

CI runs tests on PRs automatically.

Output:

- `results/models_report.csv` — one row per model tested, with status,
  latency, best-effort category (`coding` / `reasoning` / `vision` / `fast` /
  `general`), and the raw error message for failures.
- `opencode.generated.json` (optional, via `--generate-config`) — ready to
  merge into your real `opencode.json`, containing only models that passed.

## Providers without a `/models` endpoint

Some Anthropic-compatible routers don't expose a model list. In that case
`fetch_models()` returns an empty list and that provider is skipped with a
warning. The simplest fix: hardcode the model IDs you want tested by adding a
small `known_models` array to that provider in `providers.json` and a couple
of lines in `load_provider_configs` to use it instead of calling the API —
happy to wire that up if/when you hit this case.

## Adding a new provider type

1. Subclass `BaseProvider` in `check_models.py`.
2. Implement `fetch_models()` and `test_model()`.
3. Register the class in the `PROVIDER_CLASSES` dict.
4. Add `"type": "your_type"` entries to `providers.json`.

## Roadmap (from the original spec)

- [x] OpenAI-compatible providers
- [x] Anthropic-compatible providers
- [x] CSV report
- [x] Auto-generate opencode config from working models
- [x] Response-time measurement (`latency_ms`)
- [x] Basic model categorization
- [ ] First-token latency for streaming responses (needs streaming support)
- [ ] Config-driven "known_models" fallback for providers with no `/models`
