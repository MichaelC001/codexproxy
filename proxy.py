#!/usr/bin/env python3
"""
Minimal Codex <-> Telegram proxy.

Usage:
  TELEGRAM_BOT_TOKEN=<token> python proxy.py

Optional environment variables:
  CODEX_BIN  (default: /opt/homebrew/bin/codex)
  CODEX_CWD  (default: current working directory)
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
from pathlib import Path
from typing import Optional

from telegram import Update
from telegram.ext import Application, ApplicationBuilder, ContextTypes, JobQueue, MessageHandler, filters


TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CODEX_BIN = os.environ.get("CODEX_BIN", "/opt/homebrew/bin/codex")
CODEX_CWD = Path(os.environ.get("CODEX_CWD", os.getcwd()))

if not TELEGRAM_TOKEN:
    raise SystemExit("Missing TELEGRAM_BOT_TOKEN environment variable.")

message_queue: "queue.Queue[Optional[str]]" = queue.Queue()
active_chat_id: Optional[int] = None


def start_codex_process() -> subprocess.Popen:
    """Spawn codex exec --json and return the handle."""
    cmd = [
        CODEX_BIN,
        "exec",
        "--json",
        "--color",
        "never",
        "-C",
        str(CODEX_CWD),
        "-",
    ]
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    if not proc.stdin or not proc.stdout:
        raise RuntimeError("Failed to start codex process with pipes.")
    return proc


def codex_reader(proc: subprocess.Popen) -> None:
    """Read codex stdout JSONL and push extracts into the queue."""
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            message = extract_text_from_codex_event(obj)
        except json.JSONDecodeError:
            message = line
            print(f"[proxy] non-json line: {line}", flush=True)
        else:
            print(f"[proxy] codex event: {json.dumps(obj, ensure_ascii=False)}", flush=True)
        if message:
            message_queue.put(message)
    message_queue.put("Codex process exited. Restart the proxy to continue.")
    message_queue.put(None)


def extract_text_from_codex_event(obj: dict) -> Optional[str]:
    """Best-effort extraction of human-readable text from Codex JSON."""
    event_type = obj.get("type")
    if event_type == "response.create":
        content = obj.get("response", {}).get("content", [])
        chunks = []
        for item in content:
            if item.get("type") == "output_text" and isinstance(item.get("text"), str):
                chunks.append(item["text"])
        return "\n".join(chunks) if chunks else None
    if event_type == "event_msg":
        payload = obj.get("payload", {})
        text = payload.get("text") or payload.get("message")
        if isinstance(text, str):
            return text
    # Fallback to compact JSON string.
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:  # pragma: no cover - defensive
        return str(obj)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Telegram message handler: relay text to codex stdin."""
    global active_chat_id
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()
    if not text:
        return
    active_chat_id = update.effective_chat.id
    await update.message.reply_text("➡️ Sent to Codex…")
    proc = context.bot_data.get("codex_proc")
    stdin = proc.stdin if proc else None
    if not stdin:
        await update.message.reply_text("Codex process unavailable.")
        return
    stdin.write(text + "\n")
    stdin.flush()


async def pump_codex_queue(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send buffered codex messages to Telegram."""
    global active_chat_id
    if active_chat_id is None:
        return
    while True:
        try:
            message = message_queue.get_nowait()
        except queue.Empty:
            break
        if message is None:
            return
        try:
            await context.bot.send_message(chat_id=active_chat_id, text=message)
        except Exception as exc:  # pragma: no cover - log and continue
            print(f"[proxy] failed to send message: {exc}", flush=True)


def main() -> None:
    proc = start_codex_process()
    reader_thread = threading.Thread(target=codex_reader, args=(proc,), daemon=True)
    reader_thread.start()

    job_queue = JobQueue()
    application: Application = ApplicationBuilder().token(TELEGRAM_TOKEN).job_queue(job_queue).build()
    application.bot_data["codex_proc"] = proc

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.job_queue.run_repeating(pump_codex_queue, interval=1.0, first=1.0)

    try:
        application.run_polling()
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    main()
