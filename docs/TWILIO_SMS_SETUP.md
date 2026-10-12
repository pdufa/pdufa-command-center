# Set up real iPhone SMS alerts for PDUFA scans

## Current state

**Not active yet.** Scanner schedules remain removed. The Twilio provider
integration exists, but real texts require an SMS-enabled Twilio number,
applicable US messaging registration/verification and four GitHub Actions
secrets. An acknowledged provider API request does not prove device delivery.

A manually triggered single-text connectivity test is installed at
`.github/workflows/sms-delivery-test.yml`. It makes **no scan requests** and
has **no push or cron triggers**.

## 1. Create or open your Twilio account

Go to https://console.twilio.com/ . Choose an SMS-capable Twilio sender
number and complete the applicable sending registration or verification.
For SMS to US recipients, Twilio requires A2P 10DLC registration for
US local numbers, or Toll-Free Verification for toll-free senders. For
reliable production SMS, a paid account and completed verification/registration
may be needed. Twilio trial restrictions can block custom message bodies.

The phone you want to receive notifications on must be a mobile number,
not the Twilio *sender* number.

## 2. Store credentials PRIVATELY in GitHub

Visit the repository:
https://github.com/pdufa/pdufa-command-center/settings/secrets/actions

Choose **New repository secret** four times. Create these exact names:

- `TWILIO_ACCOUNT_SID` — your Twilio Account SID (starts with AC)
- `TWILIO_AUTH_TOKEN` — your Twilio Auth Token
- `TWILIO_FROM_NUMBER` — purchased and verified/registered SMS-capable
  Twilio number, E.164 format, e.g. +1 followed by ten digits
- `PDUFA_SMS_TO_NUMBER` — your iPhone's number, E.164 format

**Never paste your Twilio Auth Token into chat, documentation, an issue or
repository source code.** The GitHub secret values are supplied directly
to the action at run time. Use only a sender Twilio has authorized for SMS.

## 3. Run one safe test

Open:
https://github.com/pdufa/pdufa-command-center/actions/workflows/sms-delivery-test.yml

Select **Run workflow** on the main branch. The workflow checks that the
secrets exist and submits exactly **one** SMS:

`PDUFA Command Center SMS TEST. Reply in ChatGPT if this arrived.`

If the workflow displays `submitted_not_delivered`, Twilio accepted the
submission, but you must still confirm actual delivery on the phone.
If it fails, check the workflow's error and Twilio's Messaging Logs
and sender compliance status. Don't repeatedly click Run; failed/unknown
network submissions can cause duplicates.

## 4. Production scan messaging (not enabled yet)

When actual delivery is verified, the scan orchestrator will use
`scripts/run_scan_with_sms.py` and `scripts/scan_sms.py`.
For EACH separately executed scan it must submit two SMS messages:
one START before scanning and one END when the scan finishes (including
PARTIAL/FAILED and a reliable result summary). The SMS wrapper fails
closed when configuration or the START submission is unavailable.

At that stage, integrate the complete multi-source #2/#3/#4 scanner
with verified baselines, audited coverage and source updates. Do not
enable nightly workflows until all prerequisites are satisfied.

Official guidance:
- https://www.twilio.com/docs/usage/trials
- https://www.twilio.com/docs/messaging/quickstart
- https://www.twilio.com/docs/messaging/compliance/toll-free/console-onboarding
- https://www.twilio.com/docs/messaging/compliance/a2p-10dlc/quickstart
- https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets
