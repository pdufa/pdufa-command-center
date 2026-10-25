"""Single Google-operator sign-in page for the isolated scientific review backend.

A successful Google login proves the configured operator identity only.
It does not provision reviewer credentials or independently verify evidence.
"""
from __future__ import annotations

import html
import os
import re
import secrets

from fastapi.responses import HTMLResponse

_GOOGLE_CLIENT_RE = re.compile(r"^[0-9]+-[A-Za-z0-9_-]+[.]apps[.]googleusercontent[.]com$")


def operator_signin_page() -> HTMLResponse:
    mode = os.getenv("PDUFA_SCIENTIFIC_ACCESS_MODE", "").strip()
    email = os.getenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL", "").strip()
    client_id = os.getenv("PDUFA_SCIENTIFIC_GOOGLE_CLIENT_ID", "").strip()
    enabled = mode == "single_operator" and bool(email) and bool(_GOOGLE_CLIENT_RE.fullmatch(client_id))
    nonce = secrets.token_urlsafe(24)
    status = ("Use your authorized Google account to verify operator access."
              if enabled else "Google operator sign-in is not completely configured.")
    google_elements = (
        '<div id="g_id_onload" data-client_id="' + html.escape(client_id, quote=True)
        + '" data-callback="handleCredentialResponse" data-auto_prompt="false"></div>'
        + '<div class="g_id_signin" data-type="standard" data-size="large"'
        + ' data-theme="outline" data-text="signin_with" data-shape="rectangular"></div>'
        if enabled else ""
    )
    script = (
        '<script src="https://accounts.google.com/gsi/client" async defer></script>'
        if enabled else ""
    )
    page = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PDUFA Scientific Operator</title>
<style>
:root{color-scheme:light;font-family:system-ui,-apple-system,Segoe UI,Arial,sans-serif}
body{background:#f6f8f9;color:#16242c;margin:0;padding:32px 16px}
main{max-width:590px;background:white;border:1px solid #d6dfe3;border-radius:12px;padding:28px;margin:auto}
h1{font-size:1.5rem;margin-top:0}p{line-height:1.55}
small{color:#5d6971}#result{min-height:2.5em;margin:18px 0;white-space:pre-line}
.notice{border-top:1px solid #dbe2e6;margin-top:28px;padding-top:18px}
a{color:#0e537a}
</style>
</head>
<body>
<main>
<h1>PDUFA Scientific Assessment</h1>
<p>Single-account scientific operator sign-in</p>
<p id="result" role="status" aria-live="polite">__STATUS__</p>
__GOOGLE_ELEMENTS__
<section class="notice">
<strong>Scientific integrity:</strong>
<p>Operator access permits identity verification only. It does not certify scientific
evidence, grant professional reviewer credentials, approve results, or turn one
person's review into two independent reviews.</p>
<small>Isolated Scientific Assessment service · No scanner or trading actions</small>
</section>
</main>
__SCRIPT__
<script nonce="__NONCE__">
window.handleCredentialResponse = async function(response) {
  const result = document.getElementById("result");
  result.textContent = "Verifying Google identity…";
  if (!response || typeof response.credential !== "string") {
    result.textContent = "Google did not return a valid identity token.";
    return;
  }
  try {
    const request = await fetch("/api/scientific-assessment/operator/me", {
      method: "GET",
      headers: { "Authorization": "Bearer " + response.credential },
      cache: "no-store",
      credentials: "omit"
    });
    if (!request.ok) {
      result.textContent = request.status === 403
        ? "This Google account is not the configured operator."
        : "Sign-in verification failed (" + request.status + ").";
      return;
    }
    const verified = await request.json();
    if (verified.identityVerified !== true || verified.role !== "operator") {
      result.textContent = "Sign-in verification was incomplete.";
      return;
    }
    result.textContent = "Google operator identity verified. Scientific reviewer permissions and independent evidence verification remain separate.";
  } catch (_) {
    result.textContent = "Could not reach the Scientific Assessment service. Try again.";
  }
};
</script>
</body></html>"""
    page = (page.replace("__STATUS__", html.escape(status))
            .replace("__GOOGLE_ELEMENTS__", google_elements)
            .replace("__SCRIPT__", script)
            .replace("__NONCE__", nonce))
    return HTMLResponse(
        content=page,
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": (
                "default-src 'none'; base-uri 'none'; form-action 'none'; "
                "frame-ancestors 'none'; "
                "script-src 'nonce-" + nonce + "' https://accounts.google.com/gsi/client; "
                "style-src 'unsafe-inline' https://accounts.google.com/gsi/style; "
                "frame-src https://accounts.google.com; "
                "connect-src 'self' https://accounts.google.com; "
                "img-src data: https://accounts.google.com; "
            ),
        },
    )
