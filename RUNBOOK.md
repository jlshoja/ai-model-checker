# RUNBOOK — ai-model-checker

Step-by-step checklist for running the tool from scratch.

---

## Step 1: One-time setup

```bash
cd ai-model-checker
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Verify:
```
(.venv) > python --version
Python 3.11+
(.venv) > pip list | findstr openpyxl
openpyxl    3.x.x
```

---

## Step 2: Prepare providers.xlsx

Open `providers.xlsx` in Excel. Each row = one provider.

Required columns:
| Column | Example |
|--------|---------|
| Provider Name | Groq |
| Base URL | https://api.groq.com/openai/v1 |
| API Key | gsk_xxxxx |
| OpenAI Compatible | Yes |
| Anthropic Compatible | No |
| Recommended Models | llama-3.3-70b-versatile, deepseek-r1-distill-llama-70b |
| Priority | High |

Optional columns:
| Column | Purpose |
|--------|---------|
| Known Models | Comma-separated fallback list if /models endpoint unavailable |
| Rate Limit | Informational |
| Anthropic Version | For Anthropic-type providers (default: 2023-06-01) |

---

## Step 3: Generate config files

```bash
python check_models.py generate --xlsx providers.xlsx
```

Expected output:
```
Reading providers from: providers.xlsx
Found 12 providers in Excel file
Generated .env file: .env
Generated providers.json: providers.json

Done! You can now run:
  python check_models.py --config providers.json --env .env
```

Verify files created:
- `.env` — contains `GROQ_API_KEY=gsk_xxxxx` etc.
- `providers.json` — contains provider entries with base_url, api_key_env, known_models

---

## Step 4: Run checks

### Full check (all providers)

```bash
python check_models.py check
```

Expected output:
```
2026-07-23 14:30:01 INFO === groq (openai) ===
2026-07-23 14:30:02 INFO found 5 model(s), testing with max 5 in parallel...
2026-07-23 14:30:03 INFO   [OK]   llama-3.3-70b-versatile    342ms
2026-07-23 14:30:04 INFO   [OK]   deepseek-r1-distill-llama-70b    521ms
2026-07-23 14:30:04 INFO   [FAIL] unknown-model    480ms  Model not found
2026-07-23 14:30:05 INFO === openrouter (anthropic) ===
...
2026-07-23 14:31:15 INFO Summary: 28/35 models working
2026-07-23 14:31:15 INFO report written to results/models_report.csv
2026-07-23 14:31:15 INFO Excel report written to results/models_report.xlsx
```

Check results:
- Open `results/models_report.xlsx` — Sheet "OK" = working models, Sheet "FAILED" = broken ones
- Each row shows: provider, model, status, latency_ms, ttft_ms, category, error

### Single provider check

```bash
python check_models.py check --providers groq
```

### Auto-update + check (re-reads providers.xlsx first)

```bash
python check_models.py check --auto-update --xlsx providers.xlsx
```

---

## Step 5: Generate opencode config (optional)

```bash
python check_models.py check --generate-config opencode.generated.json
```

Creates `opencode.generated.json` with only working models, formatted for OpenCode.

Or merge directly into your real opencode config:

```bash
python check_models.py check --merge-opencode
```

This reads `~/.config/opencode/opencode.jsonc`, adds working models, and writes back.

---

## Common Failures and Fixes

### "no API key found for provider 'X' — skipping"

**Cause:** The env var named in `providers.json` (`api_key_env`) doesn't exist in `.env`.

**Fix:** Check `.env` for the matching variable name. Re-generate from Excel:
```bash
python check_models.py generate --xlsx providers.xlsx
```

### "config file not found: providers.json"

**Cause:** Wrong directory or file missing.

**Fix:** Run from the `ai-model-checker` folder, or specify path:
```bash
python check_models.py check --config C:\path\to\providers.json
```

### "no providers with valid API keys found"

**Cause:** `.env` file is empty or keys don't match `api_key_env` values in `providers.json`.

**Fix:**
1. Open `.env` — verify keys are present (not placeholders)
2. Open `providers.json` — verify `api_key_env` values match `.env` variable names exactly

### "HTTP 401 Unauthorized" / "HTTP 403 Forbidden"

**Cause:** API key is invalid or expired.

**Fix:**
1. Log into the provider's dashboard
2. Generate a new API key
3. Update `.env` or re-generate from `providers.xlsx`

### "HTTP 429 Rate limited"

**Cause:** Too many concurrent requests.

**Fix:** Lower concurrency:
```bash
python check_models.py check --concurrency 2
```

### "Connection timeout" / "Read timeout"

**Cause:** Provider is slow or unreachable.

**Fix:** Increase timeout:
```bash
python check_models.py check --timeout 60
```

Or check provider status page.

### "Excel file not found: providers.xlsx"

**Cause:** Wrong path or file not in expected location.

**Fix:** Specify the full path:
```bash
python check_models.py check --auto-update --xlsx C:\path\to\providers.xlsx
```

### "openpyxl not installed"

**Cause:** Missing dependency.

**Fix:**
```bash
pip install openpyxl
```

### Results show all models as FAILED

**Cause:** Network issue, VPN blocking, or all providers down.

**Fix:**
1. Check internet connection
2. Test one provider manually: `python check_models.py check --providers groq`
3. Check provider status pages

---

## Where to Look if Something Goes Wrong

| What | Where |
|------|-------|
| Detailed logs | Terminal output (real-time) |
| Full results | `results/models_report.xlsx` |
| CSV results | `results/models_report.csv` |
| Provider config | `providers.json` |
| API keys | `.env` |
| Source config | `providers.xlsx` |
| OpenCode config | `~/.config/opencode/opencode.jsonc` |

---

## Quick Reference Commands

```bash
# First-time setup
python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt

# Generate config from Excel
python check_models.py generate --xlsx providers.xlsx

# Run all checks
python check_models.py check

# Run single provider
python check_models.py check --providers groq

# Auto-update + run
python check_models.py check --auto-update

# Generate opencode config
python check_models.py check --generate-config opencode.generated.json

# Merge into real opencode
python check_models.py check --merge-opencode

# Adjust performance
python check_models.py check --concurrency 10 --timeout 20
```
