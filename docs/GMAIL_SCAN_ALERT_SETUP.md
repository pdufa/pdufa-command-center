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

## Independent END notifier for the completed #2/#3/#4 collector jobs

The clinical collection workflow is `.github/workflows/pdufa-one-time-clinical-scan.yml`.
Its original October 11, 2026 run `38195214610` finished all three GitHub jobs.
The one-time source scan had no automatic completion email step. Its reports
were partial because they excluded FDA, SEC, issuer, and full-market evidence.

A separate `.github/workflows/pdufa-clinical-scan-end-email.yml` listens to
`workflow_run: completed` on **PDUFA One-Time Clinical Scan**. It is a
watcher: changing it does **not** relaunch the collector. It sends three END
emails, using the collector's GitHub job outcome and each job's archived
`scan_execution_report.json`. The watcher sends even if individual collectors
failed or were canceled, provided GitHub emits the completion event.

**Set the three private repository Actions secrets above before expecting
automatic delivery.** Without them the watcher records an explicit FAILED
notification job. The connected ChatGPT Gmail account is not an Actions secret.

To test your GitHub email settings, manually run:
`https://github.com/pdufa/pdufa-command-center/actions/workflows/email-delivery-test.yml`

To request the three historical END summaries, manually run:
`https://github.com/pdufa/pdufa-command-center/actions/workflows/pdufa-clinical-scan-end-email.yml`
and enter run ID `38195214610`. Running this after separate email delivery
has already occurred can create duplicates. GitHub SMTP submission success
does not itself guarantee inbox arrival; check inbox, filters and spam.

Abrupt GitHub outages can still suppress the completion event; for a strict
delivery SLA, add an independent monitor and durable notification queue.
This notifier handles only the named source-only workflow; other collectors
require their own workflow_run routing before claiming full coverage.
