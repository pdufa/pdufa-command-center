#!/usr/bin/env python3
"""Fail-closed Telnyx SMS sender for FOCUS alerts. No scheduler is installed here.

--test is a one-time, explicitly manual message. --alert is usable only
after a verified handset test and is restricted to the canonical FOCUS roster.
An API submission is NOT evidence that a text reached the handset.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
from urllib import request

API_URL = "https://api.telnyx.com/v2/messages"
E164 = re.compile(r"^\+[1-9]\d{6,14}$")
TICKER = re.compile(r"^[A-Z][A-Z0-9.]{0,9}$")
MAX_SMS_LENGTH = 153
FOCUS_ROSTER = Path(__file__).resolve().parents[1] / "new-platform/frontend/data/p3PostDataActive.json"
TEST_TEXT = "PDUFA FOCUS Telnyx SMS TEST. This is a one-time setup message. Please confirm receipt."


class TelnyxSetupError(RuntimeError):
    """Configuration or eligibility is missing; no SMS is attempted."""


class TelnyxSubmissionError(RuntimeError):
    """Provider submission failed/unknown; do not automatically retry."""


@dataclass(frozen=True)
class Settings:
    api_key: str
    from_number: str
    to_number: str
    messaging_profile_id: str = ""

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        e = os.environ if env is None else env
        key = str(e.get("TELNYX_API_KEY", "")).strip()
        sender = str(e.get("TELNYX_FROM_NUMBER", "")).strip()
        recipient = str(e.get("PDUFA_SMS_TO_NUMBER", "")).strip()
        profile = str(e.get("TELNYX_MESSAGING_PROFILE_ID", "")).strip()
        if not key or not sender or not recipient:
            raise TelnyxSetupError("Missing required private Telnyx SMS configuration")
        if not E164.fullmatch(sender) or not E164.fullmatch(recipient) or sender == recipient:
            raise TelnyxSetupError("Invalid E.164 sender or destination")
        if len(key) > 512 or len(profile) > 128:
            raise TelnyxSetupError("Invalid configuration length")
        return cls(key, sender, recipient, profile)


def focus_tickers(roster_path: Path = FOCUS_ROSTER) -> set[str]:
    """No custom ticker list may override the repository's canonical FOCUS roster."""
    try:
        doc = json.loads(roster_path.read_text(encoding="utf-8"))
        rows = doc["records"]
        if not isinstance(rows, list) or not rows:
            raise ValueError("Missing canonical FOCUS records")
        values = {str(row["ticker"]).strip().upper() for row in rows}
        if not values or any(not TICKER.fullmatch(t) for t in values):
            raise ValueError("Invalid canonical FOCUS tickers")
        return values
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise TelnyxSetupError("Canonical FOCUS roster unavailable") from exc


def ascii_message(text: str) -> str:
    clean = "".join(c if 32 <= ord(c) < 127 else " " for c in text)
    clean = " ".join(clean.split())
    if not clean:
        raise ValueError("Empty SMS")
    if len(clean) > MAX_SMS_LENGTH:
        clean = clean[:MAX_SMS_LENGTH - 3].rstrip() + "..."
    return clean


def alert_text(ticker: str, priority: str, headline: str) -> str:
    ticker = ticker.strip().upper()
    priority = priority.strip().upper()
    if not TICKER.fullmatch(ticker) or priority not in {"CRITICAL", "HIGH", "MEDIUM"}:
        raise ValueError("Invalid FOCUS ticker or alert priority")
    return ascii_message(f"FOCUS {priority}: {ticker} - {headline}. Details: https://pdufa-new-dashboard.vercel.app/news")


def submit_once(settings: Settings, message: str, *, opener=request.urlopen) -> dict[str, str]:
    """Exactly one API submission. Timeout/unknown response MUST NOT be retried blindly."""
    if not message.isascii() or not 1 <= len(message) <= MAX_SMS_LENGTH:
        raise ValueError("One ASCII SMS segment is required")
    body = {
        "from": settings.from_number,
        "to": settings.to_number,
        "text": message,
    }
    if settings.messaging_profile_id:
        body["messaging_profile_id"] = settings.messaging_profile_id
    req = request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": "Bearer " + settings.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with opener(req, timeout=20) as resp:
            status = resp.status
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        # A timeout may occur AFTER the provider accepted the request.
        # Never automatically retry, nor log credentials, phone numbers or provider response.
        raise TelnyxSubmissionError("Telnyx submission failed or status is unknown") from exc
    record = payload.get("data") if isinstance(payload, dict) else None
    message_id = record.get("id") if isinstance(record, dict) else None
    if status not in (200, 201, 202) or not isinstance(message_id, str) or not message_id:
        raise TelnyxSubmissionError("Telnyx did not acknowledge a message ID")
    return {"status": "submitted_not_delivered", "provider_message_id": message_id}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--test", action="store_true", help="Submit a single manual test SMS")
    mode.add_argument("--alert", action="store_true", help="Submit a vetted FOCUS ticker alert")
    parser.add_argument("--ticker", default="")
    parser.add_argument("--priority", default="")
    parser.add_argument("--headline", default="")
    args = parser.parse_args(argv)
    try:
        settings = Settings.from_env()
        if args.test:
            msg = ascii_message(TEST_TEXT)
        else:
            if os.getenv("PDUFA_TELNYX_SMS_VERIFIED", "").lower() != "true":
                raise TelnyxSetupError("Handset test not verified: alert SMS disabled")
            if args.ticker.strip().upper() not in focus_tickers():
                raise TelnyxSetupError("Ticker absent from canonical FOCUS roster")
            msg = alert_text(args.ticker, args.priority, args.headline)
        result = submit_once(settings, msg)
    except (TelnyxSetupError, TelnyxSubmissionError, ValueError) as exc:
        print("FOCUS SMS not confirmed:", type(exc).__name__, file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
