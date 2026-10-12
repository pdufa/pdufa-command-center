# PDUFA Gmail Start + Finish Notification Setup

The PDUFA system uses **two emails for every independently run scan**:
one at START, one at END with a truthful result summary.

## Immediate one-email test already sent via ChatGPT

An email delivery test was accepted by the connected Gmail account,
sent to the same Gmail address. This validates the connected Gmail
send action, **not** GitHub Actions' ability to send later.

## To allow GitHub Actions to email autonomously

1. Go to the private secrets page:
   https://github.com/pdufa/pdufa-command-center/settings/secrets/actions
2. Create **three repository secrets** (New repository secret):
   - `PDUFA_GMAIL_USER`: a Gmail sender address you control.
   - `PDUFA_GMAIL_APP_PASSWORD`: the sender's Gmail application password,
     generated through Google Account security when available.
   - `PDUFA_ALERT_EMAIL`: the inbox that should receive scan notifications.
3. Never disclose the app password in chat, GitHub issues, logs or tracked
   code. App passwords generally require Google's 2-Step Verification
   and might be unavailable for some accounts; Gmail's ChatGPT connection
   does **not** transfer credentials to GitHub.
4. Visit the manual GitHub Action:
   https://github.com/pdufa/pdufa-command-center/actions/workflows/email-delivery-test.yml
   Select **Run workflow** on `main`. It submits one email with a test
   subject; it does not launch any scanner.
5. Confirm actual arrival in the recipient inbox. Email submitted status
   alone is not a guarantee of delivery.

## Scan wrapper usage (only when ready)

```bash
python scripts/run_scan_with_email.py --scan 2 --mode BASELINE \
  --status-file data/all_phase_scan_state.json --timeout-seconds 3000 -- \
  python scripts/all_phase_scan.py
```

This is just a demonstration of the notification wrapper with a saved
clinical collector. It **does not** establish full FDA/SEC/issuer/market
coverage and must report UNVERIFIED without a full-source verification gate.

When the complete multi-source scan is built, all #2/#3/#4 and separately
tracked source scans must call this wrapper. It writes notification audits
in `reports/scan_notifications`.

The end summary includes Pacific completion time, source-supported checked/due
counts, new and changed records, warnings, errors and the dashboard link.
Email submission failure before START blocks data collection; failure after
END causes the run to report a notification problem.

**Limit:** A host/runner crash can prevent code in a `finally` block
from running. A watchdog or external email queue is required for a strict
guarantee even after a hard shutdown.

There are no active nightly scan workflows at the moment.
