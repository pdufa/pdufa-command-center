# Set up real iPhone SMS alerts for PDUFA scans

## Current state

**SMS delivery is not active.** The existing 8 PM Pacific overnight scan
currently uses Gmail email notifications. Twilio messages require an
SMS-enabled Twilio number, applicable US messaging registration/verification,
and four GitHub Actions secrets. An acknowledged provider API request does
not prove actual handset delivery. The nightly scan stays email-only unless
the explicit verified-delivery opt-in is enabled.

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

## 4. Opt in to dual email + SMS only after delivery is proven

The staging code supports START and END email **and** SMS for the three
nightly clinical collectors (#2 PIPELINE, #3 PRE3, #4 GEM JR).

1. Confirm the **single** SMS test arrived on the intended handset.
2. Save the four Twilio/recipient secrets listed above in the repository.
3. In the repository GitHub Actions secrets, add `PDUFA_SMS_VERIFIED` with
   exact value `true` **only after** that delivery test. Keep it missing
   otherwise; email-only scanning is the default.
4. Deploy the reviewed scanner change to main and verify the next nightly
   run's notification audit for both channel receipts.

The opt-in uses the existing `run_scan_with_email.py` wrapper with
`--require-sms`. Both channels must acknowledge START before the scan
runs. It sends each END once, recording incomplete or failed delivery rather
than reporting success or automatically retrying ambiguous submissions.
The mode does not dispatch any extra scan or enable trading.

**Important:** This capability is presently in a review branch and is
not installed in production. Sender eligibility and handset delivery must
be independently verified. If SMS is opted in and START submission fails,
the clinical collector is deliberately blocked; remove the verified opt-in
secret to return to the existing email-only scan after diagnosing the issue.

Manual SMS test (no scans): `.github/workflows/sms-delivery-test.yml`
Existing nightly schedule: `.github/workflows/pdufa-nightly-pacific-start.yml`
No new or duplicate scheduler is created.

Official guidance:
- https://www.twilio.com/docs/usage/trials
- https://www.twilio.com/docs/messaging/quickstart
- https://www.twilio.com/docs/messaging/compliance/toll-free/console-onboarding
- https://www.twilio.com/docs/messaging/compliance/a2p-10dlc/quickstart
- https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets
