# ai-model-checker

Check which AI provider models **actually work** — not just listed — by sending real completion requests. Results go to the terminal, CSV/Excel, and optionally into an `opencode.json` config with only working models.

## Prerequisites

- Python 3.9+
- An `providers.xlsx` spreadsheet with your API keys and provider details (or manually edited `providers.json` + `.env`)

## Installation

```bash
cd ai-model-checker
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
```

## Folder Structure

```
ai-model-checker/
├── providers.xlsx          # Your provider list (API keys, base URLs, models)
├── providers.json          # Generated config (from providers.xlsx or manual)
├── .env                    # API keys (generated from providers.xlsx or manual)
├── check_models.py         # Main script — runs checks, outputs results
├── generate_config.py      # Standalone: generate .env + providers.json from Excel
├── make_excel.py           # Generates model research/benchmark Excel
├── run_check.bat           # Windows: one-click run (auto-setup venv + deps)
├── run_checks.bat          # Windows: generate from Excel + run checks
├── requirements.txt        # Python dependencies
└── results/
    └── models_report.xlsx  # Output: working/failed models with latency
```

## Configuration

### Option A: From providers.xlsx (recommended)

1. Open `providers.xlsx` in Excel/LibreOffice
2. Fill in rows with: Provider Name, Base URL, API Key, API Type, Known Models, etc.
3. Generate config files:

```bash
python check_models.py generate --xlsx providers.xlsx
```

This creates `.env` (API keys) and `providers.json` (provider endpoints).

### Option B: Manual config

Edit `providers.json` directly:
```json
{
  "providers": {
    "my_provider": {
      "type": "openai",
      "base_url": "https://api.example.com/v1",
      "api_key_env": "MY_PROVIDER_API_KEY"
    }
  },
  "test_prompt": "Reply OK only",
  "max_tokens": 10,
  "timeout_seconds": 30,
  "concurrency": 5
}
```

Then create `.env` with matching keys:
```
MY_PROVIDER_API_KEY=sk-xxxx
```

## Running

### Check all providers (terminal + Excel output)

```bash
python check_models.py check
```

Expected output:
```
2026-07-23 INFO === groq (openai) ===
2026-07-23 INFO found 5 model(s), testing with max 5 in parallel...
2026-07-23 INFO   [OK]   llama-3.3-70b    342ms
2026-07-23 INFO   [FAIL] unknown-model    500ms  Model not found
...
2026-07-23 INFO Summary: 4/5 models working
2026-07-23 INFO report written to results/models_report.csv
2026-07-23 INFO Excel report written to results/models_report.xlsx
```

### Check a single provider

```bash
python check_models.py check --providers groq
```

### Auto-update config from Excel before checking

```bash
python check_models.py check --auto-update --xlsx providers.xlsx
```

Regenerates `.env` and `providers.json` from the spreadsheet, then runs checks.

### Generate opencode.json with only working models

```bash
python check_models.py check --generate-config opencode.generated.json
```

### Merge working models into real opencode config

```bash
python check_models.py check --merge-opencode
```

Reads `~/.config/opencode/opencode.jsonc`, adds working models, writes back.

### Adjust concurrency / timeout

```bash
python check_models.py check --concurrency 10 --timeout 15
```

### Windows: one-click run

Double-click `run_check.bat` — handles venv creation, dependency install, and runs the checker. Forward any arguments:

```
run_check.bat --providers groq
```

### Windows: generate from Excel + run

Double-click `run_checks.bat` — generates config from `providers.xlsx`, then runs checks.

## Output Files

| File | Description |
|------|-------------|
| `results/models_report.xlsx` | Two sheets: **OK** (working models) and **FAILED** (with error messages) |
| `results/models_report.csv` | Same data as CSV |
| `opencode.generated.json` | OpenCode config with only working models (via `--generate-config`) |
| `~/.config/opencode/opencode.jsonc` | Updated in-place (via `--merge-opencode`) |

## Key Script: check_models.py

```
python check_models.py <command> [options]

Commands:
  check       Run model checks (default if no command given)
  generate    Generate .env + providers.json from providers.xlsx

Check options:
  --config PATH           providers.json path (default: providers.json)
  --env PATH              .env path (default: .env)
  --providers NAME [..]   Only check these providers
  --output PATH           CSV report output (default: results/models_report.csv)
  --concurrency N         Parallel requests per provider (default: from config)
  --timeout N             Per-request timeout in seconds (default: from config)
  --auto-update           Regenerate config from Excel before checking
  --xlsx PATH             providers.xlsx path (default: providers.xlsx)
  --generate-config PATH  Write opencode.json with working models
  --merge-opencode        Merge into real opencode config (~/.config/opencode/)
  --opencode-path PATH    Custom path to opencode config
  --write-opencode-env    Write .env next to opencode config (default: on with --merge-opencode)
  --no-write-opencode-env Skip that .env write

Generate options:
  --xlsx PATH             providers.xlsx path (default: providers.xlsx)
  --env-file PATH         .env output path (default: .env)
  --providers PATH        providers.json output path (default: providers.json)
  --output-dir DIR        Output directory (default: .)
```
