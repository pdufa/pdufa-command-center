#!/usr/bin/env python3
"""Telegram notifications for verified PDUFA/RAAS job events.

GitHub Actions secrets: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.
Do not display secrets or Telegram request URLs in job output.
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

LABELS = {
    "pipeline-start": "▶️ PDUFA PIPELINE — LAUNCHING",
    "pipeline-end": "✅ PDUFA PIPELINE — COMPLETED",
    "raas-start": "▶️ RAAS ACCURACY — STARTED",
    "raas-end": "✅ RAAS ACCURACY — COMPLETED",
    "raas-evidence-change": "📄 RAAS — SAVED RESEARCH EVIDENCE CHANGED",
    "system-edit": "🛠 PDUFA SYSTEM — CODE UPDATED",
    "prediction-change": "📈 RAAS — VERIFIED PREDICTION CHANGE",
    "scan-start": "▶️ PDUFA / RAAS — SCAN STARTED",
    "scan-end": "✅ PDUFA / RAAS — SCAN COMPLETED",
    "test": "🔔 PDUFA / RAAS — TELEGRAM TEST",
}

def message(kind, status="", details="", url=""):
    if kind not in LABELS:
        raise ValueError("unknown event")
    label = LABELS[kind]
    if kind.endswith("-end") and status != "success":
        label = "❌ " + ("PDUFA PIPELINE" if kind == "pipeline-end" else ("RAAS ACCURACY" if kind == "raas-end" else "PDUFA / RAAS SCAN")) + " — FAILED / INCOMPLETE"
    parts = [label]
    if status:
        parts.append("Workflow status: " + status[:70])
    if details:
        parts.append(details.strip()[:700])
    if url.startswith("https://github.com/pdufa/pdufa-command-center/actions/") or url.startswith("https://github.com/pdufa/pdufa-command-center/commit/"):
        parts.append("Evidence: " + url)
    return "\n".join(parts)[:4096]

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", choices=sorted(LABELS), required=True)
    parser.add_argument("--status", default="")
    parser.add_argument("--details", default="")
    parser.add_argument("--url", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    msg = message(args.event, args.status, args.details, args.url)
    if args.dry_run:
        print(msg)
        return 0
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("::warning::Telegram not configured; set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID as GitHub Actions secrets.")
        return 1 if args.event == "test" else 0  # Manual test fails, scans never block.
    data = json.dumps({"chat_id": chat_id, "text": msg, "disable_web_page_preview": True}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.telegram.org/bot" + token + "/sendMessage",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            payload = json.load(response)
        if not payload.get("ok"):
            print("::warning::Telegram rejected notification; check bot credentials and chat permissions.")
            return 1
    except urllib.error.HTTPError as error:
        # Never display the exception URL: it contains the bot token.
        if error.code == 400:
            try:
                detail = str(json.load(error).get("description", "")).lower()
            except Exception:
                detail = ""
            if "chat not found" in detail:
                hint = "Chat not found: check TELEGRAM_CHAT_ID and press Start on YOUR newly created bot."
            elif "blocked by the user" in detail:
                hint = "Bot blocked by user: unblock it and press Start in Telegram."
            else:
                hint = "Bad request: check numeric chat ID and bot setup."
        elif error.code == 401:
            hint = "Unauthorized bot token: recopy the entire token from BotFather."
        elif error.code == 403:
            hint = "Bot cannot message this chat: check the selected chat and press Start/unblock the bot."
        elif error.code == 404:
            hint = "Telegram bot endpoint not found: verify the complete bot token."
        else:
            hint = "Telegram rejected the request."
        print(f"::warning::Telegram HTTP {error.code}: {hint}")
        return 1
    except Exception:
        # Never show exception text: it may contain the token-bearing URL.
        print("::warning::Telegram request failed (transport or parsing); details hidden to protect bot token.")
        return 1
    print("Telegram alert accepted by Telegram API.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
