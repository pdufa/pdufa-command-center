# WT → E*TRADE sandbox connection (non-trading)

The WT page offers a **sandbox-only OAuth 1.0a connectivity test** and the existing
SVRA/CAPR one-share limit-order **research drafts**. Nothing can place, preview,
cancel, or change a production E*TRADE order. There is deliberately no
`orders/place` or `orders/preview` implementation.

## Prerequisites

1. Apply for E*TRADE **retail Developer Platform sandbox** credentials at
   https://developer.etrade.com/getting-started .
   This is **not** the Equity Edge Online corporate API (which uses OAuth 2.0).
2. Add the following **server-side, encrypted Vercel environment variables**
   to the PDUFA Next.js project. Set appropriate production and preview targets.
   Do not paste the values in chat, commit them, put them in browser JS, or log them.

   - `ETRADE_SANDBOX_CONSUMER_KEY` — developer sandbox key
   - `ETRADE_SANDBOX_CONSUMER_SECRET` — developer sandbox consumer secret
   - `ETRADE_SANDBOX_COOKIE_KEY` — **64 hex characters / 32 random bytes**
     from a cryptographically secure generator (e.g. `openssl rand -hex 32`).

3. Redeploy for new environment variables to take effect.
4. Sign into the PDUFA website and visit `/wt`.
5. Click *Open E*TRADE sandbox authorization*. Complete the authorization on
   E*TRADE's official site; copy its short-lived verifier and paste it into WT.
6. Verify the **sandbox** sample-account list and use *Disconnect sandbox* to
   revoke the token upstream.

## Security and limitations

- E*TRADE retail OAuth 1.0a request/access-token endpoints:
  `https://api.etrade.com/oauth/{request_token,access_token,revoke_access_token}`.
  Sandbox consumer credentials constrain the returned tokens to the sandbox,
  and data calls are pinned to `https://apisb.etrade.com`.
- OAuth request token: 5-minute expiry. Short-lived access-token cookie:
  2-hour maximum; E*TRADE may invalidate it earlier (including midnight Eastern).
  No automatic renewal or background access.
- OAuth material is AES-256-GCM encrypted in HttpOnly SameSite cookies and
  bound to request vs access token role; app login is required to read it.
- The `/api/etrade-sandbox/accounts` endpoint returns only redacted,
  non-identifying sandbox **sample** account names/types/status, not API account keys.
- All mutating WT trading actions remain disabled. No live E*TRADE consumer keys,
  live account balances, live order preview, order approval or order placement
  are implemented.
- The present SVRA and CAPR recorded PDUFA dates (Nov 22, 2026) fall inside the
  existing 14-day pre-PDUFA *no-new-buy* rule as of Nov 11, 2026, so those
  research drafts have no executable limit price.
- E*TRADE sandbox returns stored example data that might not match requested
  tickers or a real balance. Never display sandbox output as real execution.
- **No secrets are currently present in Vercel for this optional integration.**
  They must be provisioned manually in Vercel before connecting.

## Provider documentation
- https://developer.etrade.com/getting-started/developer-guides
- https://apisb.etrade.com/docs/api/authorization/request_token.html
- https://apisb.etrade.com/docs/api/authorization/get_access_token.html
- https://apisb.etrade.com/docs/api/authorization/revoke_access_token.html
- https://apisb.etrade.com/docs/api/account/api-account-v1.html
