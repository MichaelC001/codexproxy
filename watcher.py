#!/usr/bin/env python3
"""
Tail a Codex log file and mirror new lines to Telegram.

Usage:
  TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... LOG_FILE=/tmp/codex.log python watcher.py
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import httpx

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
LOG_FILE = Path(os.environ.get("LOG_FILE", "/tmp/codex.log"))
POLL_INTERVAL = float(os.environ.get("POLL_INTERVAL", "0.5"))

if not BOT_TOKEN or not CHAT_ID:
    raise SystemExit("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID.")


def send_message(text: str, client: httpx.Client) -> None:
    resp = client.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": text},
        timeout=10,
    )
    resp.raise_for_status()


def tail_file(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
    with path.open("r") as fh:
        fh.seek(0, os.SEEK_END)
        while True:
            line = fh.readline()
            if not line:
                time.sleep(POLL_INTERVAL)
                continue
            yield line.rstrip("\n")


def main() -> None:
    print(f"[watcher] mirroring {LOG_FILE} to Telegram chat {CHAT_ID}")
    with httpx.Client() as client:
        send_message("Watcher started. Streaming Codex output…", client)
        for line in tail_file(LOG_FILE):
            if not line.strip():
                continue
            try:
                send_message(line, client)
            except httpx.HTTPError as exc:
                print(f"[watcher] failed to send line: {exc}")
                time.sleep(2)


if __name__ == "__main__":
    main()
