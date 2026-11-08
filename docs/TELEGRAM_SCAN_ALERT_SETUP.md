# Telegram scan notifications — activation

This branch prepares optional Telegram notifications for the **active** PDUFA Pipeline overnight GitHub Actions scan, and user-originated code/workflow edits on main. No GEM or GEM JR notifications are added.

## 1. Create a Telegram bot (phone)
1. Install and sign into Telegram for iPhone.
2. Open the official [@BotFather](https://t.me/BotFather) account and send `/newbot`.
3. Choose a display name (e.g., `PDUFA Source Alerts`) and a unique username ending in `bot`.
4. BotFather returns a **secret bot token**. Never commit or paste it into an issue or chat message.
5. In Telegram, open your new bot and press **Start** or send `/start`. Telegram bots cannot DM someone who has not started the conversation.

## 2. Get your private chat ID
You need the numeric ID of the private conversation between you and the bot. It is separate from the bot token. On iPhone, a convenience option is a third-party Telegram ID bot such as @userinfobot, if comfortable sharing your Telegram ID with that bot; otherwise query the official `getUpdates` Bot API **privately** after sending `/start` to your new bot. The `message.chat.id` in your bot's update is the correct ID. Do not put the bot token in a screenshot, URL posted in chat, or public GitHub logs. If your Telegram account has multiple connected bots, check the sender of the update.

## 3. Add two GitHub Actions repository secrets
Open **pdufa/pdufa-command-center → Settings → Secrets and variables → Actions → New repository secret**.

- `TELEGRAM_BOT_TOKEN` = the BotFather token
- `TELEGRAM_CHAT_ID` = your numeric private chat ID

Use repository secrets (not plain variables). Neither value belongs in a repository file or Vercel environment variable for this GitHub-Actions-only integration.

## 4. Enable and test
Merge the reviewed integration PR into `main` after secrets are configured. Then select **Actions → PDUFA Telegram send test → Run workflow**. It sends one actual test notification without running a scan. Confirm receipt in Telegram and allow Telegram iPhone push notifications.

## What is actually reported
- **Pipeline launching**: after the pre-scan validation job succeeds, before the real clinical collection begins. This is a launch notification, not proof the collector already fetched source records.
- **Pipeline final**: after the sequence's result job and dated RESULTS archive; any incomplete run or failed archive displays **FAILED / INCOMPLETE**, with a link to GitHub.
- **System edits**: human-triggered main branch commits affecting scan workflows, application code, or scripts. These are **code updates**, not proof Vercel deployed them.
- **Prediction change**: a supported message type is ready, but **not automatically triggered**. The current three-way independently verified forecast ledger has zero records and no approved model; only connect this after a source-verified before/after prediction audit exists. Do not infer prediction changes from retrospective data or a generic source refresh.

Missing bot credentials cause notification steps to skip with a warning without blocking scans; Telegram delivery failure also must not fail a clinical scan. The manual test fails on a delivery error, so problems are visible.

No bot credentials should appear in GitHub logs. Keep Telegram API failure exceptions masked because their request URLs embed the bot token.

RAAS is permanently retired; its former jobs and notifications must never be enabled. Historical records are read-only.
