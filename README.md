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

## Mirror native Codex output to Telegram

If you prefer to run Codex natively and simply copy its output to Telegram, use `watcher.py` together with the `script` command:

1. Start the watcher (replace the chat id with yours):

   ```bash
   TELEGRAM_BOT_TOKEN="8125975910:AAEr_y0gK9mKKNTrr8ToxD8m5wyWfTrUaOw" \
   TELEGRAM_CHAT_ID="1367506843" \
   LOG_FILE="/tmp/codex.log" \
   /Users/michael/.globalenv/bin/python watcher.py
   ```

2. Launch Codex via `script`, which keeps the terminal experience identical while mirroring output to the log file:

   ```bash
   LOG_FILE="/tmp/codex.log"
   script -q -f "${LOG_FILE}" /opt/homebrew/bin/codex exec --json --color never -C /Users/michael/Documents/dropbox/code/aichat -
   ```

Now the watcher tails the log and forwards every new line to Telegram, while you continue using Codex directly in the terminal.
