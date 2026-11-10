# FOCUS ticker news: Telnyx SMS delivery setup

**Current state: NOT ACTIVE as SMS.** The ChatGPT hourly FOCUS news check and
daily email intent are separate systems. This repository change only prepares
a dormant, manual-only **single SMS** delivery test and a guarded reusable
FOCUS-specific sender. It does not schedule an SMS send, bill Telnyx, change
any trial scores or predictions, or claim handset delivery. Existing Twilio
utilities remain unchanged and are not selected for new FOCUS alerts.

## 1. Obtain a Telnyx SMS sender

1. Visit https://portal.telnyx.com/ and sign in/create your account.
2. Set up billing, account verification, and a programmable Messaging Profile.
3. Purchase a separate SMS-capable outbound **sender** number, or use an
   SMS-capable number you already control in Telnyx. This is *not* the number
   receiving the news alerts.
4. Assign the sender to the Messaging Profile.
5. For US application-to-person messages, complete applicable **A2P 10DLC**
   brand/campaign registration (US local number) or **Toll-Free Verification**
   (toll-free number) before sending. Carrier approval may take time.
6. Create a private Telnyx API v2 key for messaging. Never paste that key into
   ChatGPT, source code, GitHub issues, commits, email or screenshots.

Official instructions:
- https://support.telnyx.com/en/articles/5664840-telnyx-10dlc-compliance
- https://support.telnyx.com/en/articles/5353868-toll-free-messaging
- https://support-v2.telnyx.com/en/articles/4287554-sms-setup-with-postman

## 2. Add private GitHub Actions secrets

At https://github.com/pdufa/pdufa-command-center/settings/secrets/actions
configure the following *repository secrets*; do not save values in the repo:

- `TELNYX_API_KEY` — your API v2 key
- `TELNYX_FROM_NUMBER` — the verified, Telnyx SMS-enabled sender in
  E.164 format (e.g. `+1XXXXXXXXXX`)
- `PDUFA_SMS_TO_NUMBER` — the user-approved destination in E.164 format,
  already supplied in the conversation; keep the actual number private
- `TELNYX_MESSAGING_PROFILE_ID` — optional; use if your Telnyx account
  requires explicit outbound profile selection

Do **not** create `PDUFA_TELNYX_SMS_VERIFIED` yet. The separate
`PDUFA_SMS_TO_NUMBER` secret may already be present from old Twilio tests,
but it must be independently confirmed to point at the intended handset.

## 3. Run a single, manual connectivity test

After registration is approved, go to:
https://github.com/pdufa/pdufa-command-center/actions/workflows/focus-telnyx-sms-test.yml

Select **Run workflow** for the `main` branch. The workflow invokes only
`python -m scripts.focus_telnyx_sms --test`. There is no schedule or push
trigger, and no clinical/financial scan runs. The test sends a single short
ASCII SMS with no personal or financial details.

A successful response means **submitted_not_delivered**, NOT that the handset
received it. Check the handset and Telnyx's delivery report. An uncertain
network result must not be retried blindly.

## 4. Enable actual FOCUS news alerts only after verified delivery

After confirming the test on the handset:

- Set GitHub secret `PDUFA_TELNYX_SMS_VERIFIED` to exactly `true` as the
  opt-in safeguard for the alert-sending path.
- The sender's `--alert` mode requires that flag and checks every requested
  ticker against the checked-out canonical FOCUS roster
  `new-platform/frontend/data/p3PostDataActive.json`.
- **Connecting actual news signals to this sender is still a separate,
  outstanding integration.** The hourly ChatGPT alert does not itself call a
  GitHub Action or the Telnyx API. Do not interpret the manual SMS test or
  the verified flag as live, automatic hourly SMS.

The alert sender only acknowledges provider submission. Delivery-status
callbacks, durable change/duplicate-event tracking, and the hourly FOCUS
news-to-SMS dispatch must be verified before we call real-time SMS complete.

Email is independently configured through the ChatGPT alert task using
the connected Gmail account; actual email delivery must also be verified.
