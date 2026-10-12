#!/usr/bin/env python3
"""Submit one real PDUFA SMS connectivity test; never run a clinical scan.

Intended for a manually dispatched GitHub Action with Twilio secrets.
Submission means accepted by Twilio, NOT delivered to the handset.
"""
import json
import sys

from scripts.scan_sms import SMSSettings, SMSSetupError, SMSSendError, submit_sms

MESSAGE = "PDUFA Command Center SMS TEST. Reply in ChatGPT if this arrived."


def main():
    try:
        settings = SMSSettings.from_env()
        result = submit_sms(settings, MESSAGE)
    except (SMSSetupError, SMSSendError, OSError, ValueError) as exc:
        print("SMS test FAILED or UNKNOWN:", type(exc).__name__, file=sys.stderr)
        return 1
    # Do not print phone numbers, authentication material, or sensitive data.
    print(json.dumps({
        "result": result["status"],
        "provider_message_id": result.get("provider_message_id", ""),
        "note": "Provider accepted submission; confirm delivery on your phone.",
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
