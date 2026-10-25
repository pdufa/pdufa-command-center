"""Single-operator Google login screen for the isolated scientific review service.

Google identity and a separately gated byte-only source archive; never reviewer sign-off.
Google ID tokens stay in page memory, are not written to cookies, URLs, or browser storage.
"""
from __future__ import annotations

from html import escape

_PAGE = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="referrer" content="no-referrer">
  <title>PDUFA · Scientific Review</title>
  <style nonce="__NONCE__">
    :root { color-scheme: light; font-family: system-ui,-apple-system,sans-serif; }
    body { margin:0; background:#f5f8fb; color:#15253a; }
    main { max-width:980px; margin:0 auto; padding:30px 18px 65px; }
    h1 { font-size:clamp(1.65rem,4vw,2.4rem); margin:8px 0; }
    h2 { font-size:1.15rem; margin:0 0 12px; }
    .eyebrow { color:#375677; font-size:.8rem; font-weight:700; letter-spacing:.11em; }
    .panel { padding:20px; margin:16px 0; background:#fff; border:1px solid #cedbe7; border-radius:14px; }
    .muted {color:#4d6175;line-height:1.5} .warning {color:#75410b}
    .status {font-weight:650;padding:12px 0} .hide {display:none}
    label {display:block;font-weight:650;margin:10px 0 6px}
    input {box-sizing:border-box;max-width:100%;width:310px;padding:11px;border:1px solid #879fb6;border-radius:8px;font-size:1rem}
    button {background:#153f62;color:#fff;border:0;border-radius:8px;padding:11px 15px;font-weight:650;cursor:pointer}
    button:disabled {background:#83919c;cursor:not-allowed}
    .grid {display:grid;grid-template-columns:repeat(auto-fit,minmax(165px,1fr));gap:12px}
    .metric {border:1px solid #d7e1e9;border-radius:10px;padding:13px}
    .metric strong {font-size:1.2rem;display:block}
    details {border:1px solid #d7e1e9;border-radius:10px;padding:10px 12px;margin:9px 0;background:white}
    summary {cursor:pointer;font-weight:650} ul {line-height:1.55}
    .footer {font-size:.83rem;color:#50647a}
    a {color:#0d517d}
    .source-links {padding-left:23px;overflow-wrap:anywhere}
    .priority {color:#634509;text-transform:uppercase;font-size:.78rem}
    .evidence-note {border-left:3px solid #ba8125;padding-left:12px}
  </style>
  <script nonce="__NONCE__" src="https://accounts.google.com/gsi/client" async defer></script>
</head>
<body>
<main>
  <div class="eyebrow">PDUFA · ISOLATED SCIENTIFIC REVIEW</div>
  <h1>Scientific Assessment</h1>
  <p class="muted">One-account, read-only scientific investigation. Login does not independently verify clinical findings, award a scientific score, or authorize FDA approval predictions.</p>
  <section class="panel" aria-label="Google operator sign-in">
    <h2>Sign in with your Google account</h2>
    <p class="muted">Only the Google account configured for this review workspace is accepted.</p>
    <div id="google-button"></div>
    <p class="status" id="signin-status" role="status">Preparing Google sign-in…</p>
    <button id="signout" type="button" class="hide">Sign out</button>
  </section>
  <section id="research" class="panel hide" aria-label="Scientific research">
    <h2>Archived-trial investigation</h2>
    <p class="muted">Read-only source review; no scanner, trading, or FS/FA preset modifications.</p>
    <label for="trial">ClinicalTrials.gov trial ID</label>
    <input id="trial" type="text" value="NCT02142738" maxlength="11" pattern="NCT[0-9]{8}" inputmode="text" autocomplete="off">
    <button type="button" id="load">Load scientific report</button>
    <p id="research-status" class="status" role="status"></p>
    <div id="report" class="hide">
      <div id="metrics" class="grid"></div>
      <h2 style="margin-top:24px">20-stage investigation</h2><div id="levels"></div>
      <h2 style="margin-top:24px">40 assessments · 8 scientific layers</h2><div id="layers"></div>
      <h2 style="margin-top:24px">Evidence reconciliation · unresolved questions</h2>
      <p class="muted evidence-note">These are review questions and candidate source links, not proven discrepancies or independently verified results. Opening a source does not resolve a scientific evidence gate.</p>
      <div id="evidence-questions"></div>
      <button id="worksheet" type="button">Show source-review acceptance criteria</button>
      <p id="worksheet-status" class="muted" role="status"></p>
      <div id="worksheet-criteria"></div>
      <section id="pdf-capture" class="hide" aria-label="Original document archive">
        <h2 style="margin-top:24px">Capture original PDF sources · pilot only</h2>
        <p class="muted evidence-note">Download the original document from its source website, then choose the PDF from your PC. The archive checks its bytes and SHA-256; it does not verify the document's scientific content or resolve any evidence question.</p>
        <label for="source-pdf-kind">Original document source</label>
        <select id="source-pdf-kind">
          <option value="protocol">ClinicalTrials.gov · Protocol and SAP</option>
          <option value="fda">FDA · 2016 approval letter</option>
        </select>
        <p><a id="source-pdf-link" href="https://cdn.clinicaltrials.gov/large-docs/38/NCT02142738/Prot_SAP_000.pdf" target="_blank" rel="noopener noreferrer">Open original PDF source</a></p>
        <label for="source-pdf-file">PDF from your computer (maximum 4 MB)</label>
        <input id="source-pdf-file" type="file" accept="application/pdf,.pdf">
        <p><button id="archive-pdf" type="button">Archive this PDF for source review</button></p>
        <p id="pdf-capture-status" class="muted" role="status"></p>
      </section>
      <h2 style="margin-top:24px">Stored original PDF snapshots</h2>
      <div id="captured-pdfs"></div>
    </div>
  </section>
  <p class="footer">Scientific review requires original dated sources and independent corroboration. One operator cannot generate two independent confirmations. <a href="/health">Service health</a></p>
</main>
<div id="config" data-google-client-id="__CLIENT_ID__" hidden></div>
<script nonce="__NONCE__">
(function () {
  "use strict";
  var token = null;
  var button = document.getElementById("google-button");
  var signin = document.getElementById("signin-status");
  var research = document.getElementById("research");
  var signout = document.getElementById("signout");
  var loadButton = document.getElementById("load");
  var currentReportId = null;
  var canArchivePdf = false;
  var clientId = document.getElementById("config").dataset.googleClientId;
  var capturePanel = document.getElementById("pdf-capture");
  var uploadButton = document.getElementById("archive-pdf");
  var uploadStatus = document.getElementById("pdf-capture-status");
  var sourceSelect = document.getElementById("source-pdf-kind");
  var sourceLink = document.getElementById("source-pdf-link");
  var sourceChoices = {
    protocol: {
      gateId: "protocol_sap", sourceType: "protocol_sap",
      sourceUrl: "https://cdn.clinicaltrials.gov/large-docs/38/NCT02142738/Prot_SAP_000.pdf"
    },
    fda: {
      gateId: "official_regulatory", sourceType: "official_agency_document",
      sourceUrl: "https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2016/125514Orig1s008,125514Orig1s012ltr.pdf"
    }
  };
  var report = document.getElementById("report");
  function element(tag, text, className) {
    var node = document.createElement(tag);
    if (text !== undefined) node.textContent = String(text);
    if (className) node.className = className;
    return node;
  }
  function metric(title, value) {
    var div = element("div", undefined, "metric");
    div.appendChild(element("span", title));
    div.appendChild(element("strong", value));
    return div;
  }
  function status(message) { signin.textContent = message; }
  function clear() {
    token = null;
    research.classList.add("hide");
    report.classList.add("hide");
    signout.classList.add("hide");
    capturePanel.classList.add("hide");
    currentReportId = null;
    canArchivePdf = false;
    document.getElementById("source-pdf-file").value = "";
    button.classList.remove("hide");
  }
  async function authorizedFetch(url) {
    if (!token) throw Error("Sign in first");
    var r = await fetch(url, {
      method:"GET", cache:"no-store", credentials:"omit",
      headers:{"Authorization":"Bearer " + token,"Accept":"application/json"}
    });
    if (r.status === 401 || r.status === 403) {
      clear();
      throw Error("Account not authorized or Google session expired (" + r.status + ")");
    }
    if (!r.ok) throw Error("Scientific API unavailable (" + r.status + ")");
    return r.json();
  }
  async function receivedGoogleCredential(credential) {
    var received = credential && credential.credential;
    if (typeof received !== "string" || received.length < 20) {
      status("Google did not return a valid identity token.");
      return;
    }
    token = received;
    status("Verifying your Google identity…");
    try {
      var identity = await authorizedFetch("/api/scientific-assessment/operator/me");
      if (identity.role !== "operator" || identity.maySignOff !== false) {
        clear(); throw Error("Unexpected operator permission response");
      }
      status("Signed in as the configured operator. Scientific findings remain unverified.");
      button.classList.add("hide");
      signout.classList.remove("hide");
      research.classList.remove("hide");
      canArchivePdf = identity.mayArchiveSourcePdf === true;
      capturePanel.classList.toggle("hide", !canArchivePdf);
      document.getElementById("load").focus();
      // The default archived historical pilot is read-only; no scan or grade write.
      loadButton.click();
    } catch (err) { clear(); status(String(err.message || err)); }
  }
  signout.addEventListener("click", function () {
    clear();
    if (window.google && google.accounts && google.accounts.id) google.accounts.id.disableAutoSelect();
    status("Signed out. Google identity tokens are not stored.");
  });
  document.getElementById("worksheet").addEventListener("click", async function () {
    var id = document.getElementById("trial").value.trim().toUpperCase();
    var button = document.getElementById("worksheet");
    var statusText = document.getElementById("worksheet-status");
    var target = document.getElementById("worksheet-criteria");
    target.replaceChildren();
    if (!/^NCT[0-9]{8}$/.test(id)) {
      statusText.textContent = "Enter an exact NCT ID first.";
      return;
    }
    button.disabled = true;
    statusText.textContent = "Loading the checksum-protected source review worksheet…";
    try {
      var packet = await authorizedFetch("/api/scientific-assessment/operator/worksheet/" +
        encodeURIComponent(id));
      var items = packet && packet.reconciliation && packet.reconciliation.checks;
      if (!Array.isArray(items) || packet.scientificallyVerified !== false ||
          packet.readyForFullScientificConclusion !== false) {
        throw Error("Worksheet is missing mandatory evidence-review safeguards");
      }
      items.forEach(function (item, index) {
        var detail = element("details");
        detail.appendChild(element("summary", (index + 1) + ". " + item.title +
          " · " + String(item.resolutionCriteria && item.resolutionCriteria.length || 0) + " required checks"));
        var ol = element("ol");
        (item.resolutionCriteria || []).forEach(function (criterion) {
          ol.appendChild(element("li", criterion));
        });
        detail.appendChild(ol);
        detail.appendChild(element("p",
          "Status: Open. Criteria verified: 0. Independent adjudication pending.", "evidence-note"));
        target.appendChild(detail);
      });
      statusText.textContent = items.length + " review questions loaded. " +
        "The packet SHA-256 is an integrity checksum only, not scientific verification.";
    } catch (err) {
      statusText.textContent = String(err.message || err);
    } finally { button.disabled = false; }
  });
  function currentSource() { return sourceChoices[sourceSelect.value] || sourceChoices.protocol; }
  function syncSource() { sourceLink.href = currentSource().sourceUrl; }
  sourceSelect.addEventListener("change", syncSource);
  syncSource();

  function hexSha256(bytes) {
    return crypto.subtle.digest("SHA-256", bytes).then(function (buffer) {
      return Array.from(new Uint8Array(buffer)).map(function (v) {
        return v.toString(16).padStart(2, "0");
      }).join("");
    });
  }

  function toBase64(bytes) {
    var chunks = [];
    for (var i = 0; i < bytes.length; i += 16384) {
      chunks.push(String.fromCharCode.apply(null, bytes.subarray(i, i + 16384)));
    }
    return btoa(chunks.join(""));
  }

  async function downloadCapturedPdf(item) {
    if (!token || !currentReportId) return;
    uploadStatus.textContent = "Rechecking archived document integrity before download…";
    try {
      var response = await fetch("/api/scientific-assessment/operator/source-documents/" +
        encodeURIComponent(currentReportId) + "/" + encodeURIComponent(item.documentId), {
          method: "GET", cache: "no-store", credentials: "omit",
          headers: {"Authorization": "Bearer " + token}
        });
      if (response.status === 401 || response.status === 403) {
        clear(); throw Error("Google operator authorization expired");
      }
      if (!response.ok) throw Error("Source PDF unavailable (" + response.status + ")");
      var bytes = new Uint8Array(await response.arrayBuffer());
      var digest = await hexSha256(bytes);
      if (digest !== item.sha256 ||
          digest !== response.headers.get("X-Source-Document-SHA256")) {
        throw Error("Downloaded PDF did not match stored source SHA-256");
      }
      var url = URL.createObjectURL(new Blob([bytes], {type: "application/pdf"}));
      var anchor = element("a");
      anchor.href = url;
      anchor.download = currentReportId + "_" + item.documentId + ".pdf";
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
      uploadStatus.textContent = "Verified archive bytes downloaded. Scientific content remains unverified.";
    } catch (err) { uploadStatus.textContent = String(err.message || err); }
  }

  uploadButton.addEventListener("click", async function () {
    var file = document.getElementById("source-pdf-file").files[0];
    var selectedTrial = document.getElementById("trial").value.trim().toUpperCase();
    if (!token || capturePanel.classList.contains("hide")) return;
    if (selectedTrial !== "NCT02142738" || currentReportId !== selectedTrial) {
      uploadStatus.textContent = "Load the archived KEYNOTE-024 pilot before capturing PDFs.";
      return;
    }
    if (!file || !file.name.toLowerCase().endsWith(".pdf")) {
      uploadStatus.textContent = "Choose the original PDF downloaded from its source.";
      return;
    }
    if (file.size < 32 || file.size > 4 * 1024 * 1024) {
      uploadStatus.textContent = "PDF must be at least 32 bytes and no more than 4 MB.";
      return;
    }
    uploadButton.disabled = true;
    uploadStatus.textContent = "Verifying file checksum and archiving immutable source bytes…";
    try {
      var bytes = new Uint8Array(await file.arrayBuffer());
      var header = String.fromCharCode.apply(null, bytes.subarray(0, 5));
      var trailer = String.fromCharCode.apply(null, bytes.subarray(Math.max(0, bytes.length - 1024)));
      if (header !== "%PDF-" || !trailer.includes("%%EOF")) {
        throw Error("Selected file lacks a valid PDF signature or ending");
      }
      var source = currentSource();
      var digest = await hexSha256(bytes);
      var response = await fetch("/api/scientific-assessment/operator/source-documents/NCT02142738", {
        method: "POST", cache: "no-store", credentials: "omit",
        headers: {"Authorization": "Bearer " + token, "Content-Type": "application/json", "Accept": "application/json"},
        body: JSON.stringify({
          gateId: source.gateId, sourceType: source.sourceType, sourceUrl: source.sourceUrl,
          sha256: digest, contentBase64: toBase64(bytes)
        })
      });
      var result = await response.json().catch(function () { return {}; });
      if (response.status === 401 || response.status === 403) {
        clear(); throw Error("Document archive authorization is unavailable (" + response.status + ")");
      }
      if (!response.ok) throw Error("PDF capture failed (" + response.status + "): " +
        String(result.detail || "Check document and try again"));
      if (result.sha256 !== digest || result.byteIntegrityChecked !== true ||
          result.documentContentScientificallyVerified !== false) {
        throw Error("PDF captured but server integrity receipt was unexpected");
      }
      uploadStatus.textContent = "PDF saved with SHA-256 byte check. No independent scientific verification was performed.";
      document.getElementById("source-pdf-file").value = "";
      loadButton.click();
    } catch (err) { uploadStatus.textContent = String(err.message || err); }
    finally { uploadButton.disabled = false; }
  });

  loadButton.addEventListener("click", async function () {
    var id = document.getElementById("trial").value.trim().toUpperCase();
    var msg = document.getElementById("research-status");
    report.classList.add("hide");
    currentReportId = null;
    document.getElementById("captured-pdfs").replaceChildren();
    document.getElementById("worksheet-criteria").replaceChildren();
    document.getElementById("worksheet-status").textContent = "";
    if (!/^NCT[0-9]{8}$/.test(id)) {
      msg.textContent = "Enter an exact NCT ID, such as NCT02142738.";
      return;
    }
    loadButton.disabled = true;
    msg.textContent = "Checking the archived scientific source…";
    try {
      var item = await authorizedFetch("/api/scientific-assessment/operator/research?exact_id=" +
        encodeURIComponent("TRIAL|" + id));
      var twenty = item.investigation20;
      var forty = item.investigation40;
      var grades = item.readinessGrades;
      var metrics = document.getElementById("metrics");
      var levels = document.getElementById("levels");
      var layers = document.getElementById("layers");
      var questions = document.getElementById("evidence-questions");
      var ledger = item.evidenceLedger;
      var worklist = ledger && ledger.sourceReconciliation;
      var documents = ledger && ledger.capturedSourceDocuments;
      metrics.replaceChildren(); levels.replaceChildren(); layers.replaceChildren(); questions.replaceChildren();
      metrics.appendChild(metric("Trial", id));
      metrics.appendChild(metric("Archive", item.registryEvidenceStatus || "not available"));
      metrics.appendChild(metric("Input coverage grade", grades && grades.analysisReadiness ? grades.analysisReadiness.grade : "Not available"));
      metrics.appendChild(metric("Reluctance grade", grades && grades.scientificReluctance ? grades.scientificReluctance.grade : "Not available"));
      metrics.appendChild(metric("Independently verified", "0 / 40"));
      metrics.appendChild(metric("Scientific score", "Not assigned"));
      currentReportId = id;
      capturePanel.classList.toggle("hide",
        !canArchivePdf || id !== "NCT02142738");
      metrics.appendChild(metric("Open evidence questions",
        worklist && Number.isInteger(worklist.unresolvedChecks) ? worklist.unresolvedChecks : "Not available"));
      metrics.appendChild(metric("Archived source PDFs",
        documents && Number.isInteger(documents.sourceDocumentCount) ? documents.sourceDocumentCount : "Not available"));
      if (twenty && Array.isArray(twenty.levels)) {
        twenty.levels.forEach(function (level) {
          var detail = element("details");
          detail.appendChild(element("summary", String(level.level) + ". " + level.title));
          detail.appendChild(element("p", "Source status: " + level.status));
          detail.appendChild(element("p", level.caution || "Independent review pending", "muted"));
          levels.appendChild(detail);
        });
      } else levels.appendChild(element("p", "Twenty-stage records are unavailable for this trial."));
      if (forty && Array.isArray(forty.layers)) {
        forty.layers.forEach(function (layer) {
          var detail = element("details");
          detail.appendChild(element("summary", layer.id.replaceAll("_", " ") + " · " + layer.assessments.length + " assessments"));
          var ul = element("ul");
          layer.assessments.forEach(function (a) {
            ul.appendChild(element("li", a.replaceAll("_", " ") + " · pending independent review"));
          });
          detail.appendChild(ul);
          layers.appendChild(detail);
        });
      } else layers.appendChild(element("p", "Forty-assessment inventory unavailable for this trial."));
      var capturedList = document.getElementById("captured-pdfs");
      if (documents && Array.isArray(documents.documents) && documents.documents.length) {
        documents.documents.forEach(function (item) {
          var entry = element("div", undefined, "panel");
          entry.appendChild(element("p",
            String(item.gateId || "source") + " · " + item.byteLength +
            " bytes · stored without independent content verification"));
          entry.appendChild(element("p", "SHA-256: " + String(item.sha256), "muted"));
          var downloadButton = element("button", "Download and recheck PDF bytes");
          downloadButton.type = "button";
          downloadButton.addEventListener("click", function () { downloadCapturedPdf(item); });
          entry.appendChild(downloadButton);
          capturedList.appendChild(entry);
        });
      } else capturedList.appendChild(element("p", "No source PDF bytes archived for this trial.", "muted"));
      if (worklist && Array.isArray(worklist.checks)) {
        worklist.checks.forEach(function (check, index) {
          var detail = element("details");
          detail.appendChild(element("summary", (index + 1) + ". " + check.title +
            " · " + String(check.priority || "review").toUpperCase() + " · OPEN"));
          detail.appendChild(element("p", "Evidence gate: " + String(check.gateId || "unknown"), "priority"));
          detail.appendChild(element("p", check.question || "Independent scientific review required"));
          if (check.observedDiscrepancy) {
            detail.appendChild(element("p", "Source-reconciliation concern: " + check.observedDiscrepancy, "evidence-note"));
          }
          detail.appendChild(element("p", "Next step: " + (check.nextAction || "Review dated original sources"), "muted"));
          if (Array.isArray(check.sourceUrls) && check.sourceUrls.length) {
            detail.appendChild(element("p", "Candidate sources (not independently verified):"));
            var links = element("ul", undefined, "source-links");
            check.sourceUrls.forEach(function (url) {
              try {
                var target = new URL(url);
                if (target.protocol !== "https:") return;
                var li = element("li");
                var a = element("a", target.hostname + target.pathname);
                a.href = target.href;
                a.target = "_blank";
                a.rel = "noopener noreferrer";
                li.appendChild(a);
                links.appendChild(li);
              } catch (err) { /* Skip malformed untrusted source URL */ }
            });
            detail.appendChild(links);
          } else detail.appendChild(element("p", "Source documents still need to be identified.", "muted"));
          questions.appendChild(detail);
        });
      } else questions.appendChild(element("p",
        "Evidence reconciliation inventory unavailable; no source is independently verified."));
      report.classList.remove("hide");
      msg.textContent = "Read-only source inventory loaded. Nothing has been scientifically approved or independently verified.";
    } catch (err) { msg.textContent = String(err.message || err); }
    finally { loadButton.disabled = false; }
  });
  window.addEventListener("load", function () {
    if (!clientId || !window.google || !google.accounts || !google.accounts.id) {
      status("Google sign-in is not available. Check the OAuth client and authorized JavaScript origin.");
      return;
    }
    try {
      google.accounts.id.initialize({
        client_id: clientId,
        callback: receivedGoogleCredential,
        auto_select: false,
        cancel_on_tap_outside: true
      });
      google.accounts.id.renderButton(button, {theme:"outline",size:"large",text:"signin_with",shape:"pill"});
      status("Choose your configured Google account to continue.");
    } catch (err) {
      status("Google sign-in initialization failed. Check the OAuth authorized origin.");
    }
  });
}());
</script>
</body>
</html>'''


def operator_html(client_id: str, nonce: str) -> str:
    """Escape injected config; no secret or identity token is embedded in HTML."""
    return _PAGE.replace("__NONCE__", escape(nonce, quote=True)).replace(
        "__CLIENT_ID__", escape(client_id, quote=True)
    )
