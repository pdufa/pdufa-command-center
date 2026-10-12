#!/usr/bin/env python3
"""Submit exactly one EMAIL test through configured GitHub SMTP credentials."""
import json
import sys

from scripts.scan_email import (
    EmailSettings, EmailSetupError, EmailSendError, DASHBOARD, send_email
)


def main():
    try:
        settings = EmailSettings.from_env()
        result = send_email(
            settings,
            "[PDUFA] GitHub email channel delivery test",
            "PDUFA Command Center - Github email channel test.\n\n"
            "If this arrives, Gmail SMTP submission from the repository works.\n"
            "This test did NOT launch #2/#3/#4 scanning.\n\n"
            "Your future scan notifications are two emails per scan:\n"
            "START when collecting begins, END with actual results when it finishes.\n\n"
            "Dashboard: " + DASHBOARD + "\n"
        )
    except (EmailSetupError, EmailSendError, ValueError) as exc:
        print("Test email NOT confirmed submitted: " + type(exc).__name__,
              file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
