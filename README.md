# Codex Proxy

Extremely simple bridge that forwards Telegram messages to a local Codex CLI process and sends the Codex response back to Telegram.

> ⚠️ This prototype is single-user/single-chat, does zero validation, and is meant only for local tinkering.

## Setup

Install dependencies with the shared interpreter:

```bash
/Users/michael/.globalenv/bin/pip install -r requirements.txt
```

Export the required environment variable(s) before running:

```bash
export TELEGRAM_BOT_TOKEN="8125975910:AAEr_y0gK9mKKNTrr8ToxD8m5wyWfTrUaOw"
# optional overrides
# export CODEX_BIN="/opt/homebrew/bin/codex"
# export CODEX_CWD="/Users/you/path/to/project"
```

## Run

```bash
/Users/michael/.globalenv/bin/python proxy.py
```

- The script spawns `codex exec --json` and keeps it running.
- Any Telegram text message is written to Codex stdin (after trimming).
- Codex JSONL output is loosely parsed and forwarded back to the most recent chat.

Use `/stop` (Ctrl+C) in the terminal to terminate the proxy; Codex is shut down automatically.
