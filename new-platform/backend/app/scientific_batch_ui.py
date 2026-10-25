"""Minimal same-origin scientific batch control panel (no embedded credentials)."""

from fastapi.responses import HTMLResponse


def render_batch_panel() -> HTMLResponse:
    html = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Scientific Assessment | Batch Imports</title>
<style>
:root {color-scheme:light; font: 15px/1.5 system-ui,Arial,sans-serif; background:#f4f7f5; color:#172e27}
*{box-sizing:border-box} body{margin:0} header{background:#153c30;color:white;padding:24px clamp(18px,5vw,64px)}
header h1{font-size:1.55rem;margin:0 0 4px} header p{margin:0;opacity:.82}
main{max-width:1100px;margin:22px auto;padding:0 18px;display:grid;gap:20px}
section{background:white;border:1px solid #d9e4df;border-radius:12px;padding:22px;box-shadow:0 2px 12px #0b221008}
h2{font-size:1.15rem;margin:0 0 12px} p{margin:8px 0;color:#42564e} label{display:block;font-weight:650;margin:12px 0 6px}
input,textarea{font:inherit;width:100%;border:1px solid #a5bcb2;padding:10px;border-radius:7px;background:#fff;color:#142920}
textarea{min-height:140px;resize:vertical} .row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
button{font:inherit;font-weight:650;padding:10px 15px;border:0;border-radius:7px;background:#17654d;color:white;cursor:pointer}
button.secondary{background:#e5eeea;color:#183a2d}button:disabled{opacity:.45;cursor:not-allowed}
small{color:#587166} .status{min-height:25px;color:#245c4a;white-space:pre-wrap}
.status.error{color:#a32929}.pill{display:inline-block;padding:3px 10px;border-radius:20px;background:#edf3ef;font-size:.82rem}
.muted{color:#5c7066}.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:16px 0}
.metric{padding:12px;background:#f3f7f4;border-radius:8px}.metric strong{display:block;font-size:1.3rem}
progress{width:100%;height:15px;accent-color:#17654d}#history{display:grid;gap:8px}#history button{width:100%;text-align:left;background:#eef4f0;color:#153b2c}
#history button.selected{outline:2px solid #28775f} #events{padding-left:22px}
#events li{margin:7px 0;overflow-wrap:anywhere} .layout{display:grid;grid-template-columns:1fr 1.45fr;gap:20px}
.science-domains{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:14px}
.science-domain{border:1px solid #d9e4df;border-radius:8px;padding:13px;background:#f8faf8}
.science-domain strong{display:block;margin:3px 0}
.science-domain small{display:block}
#science-details{min-height:26px;margin-top:10px;overflow-wrap:anywhere}
#science-source a{color:#14634a;overflow-wrap:anywhere}
#quantitative-results{margin:18px 0}
.evidence-ledger{margin:18px 0;padding:16px;border:1px solid #d9e4df;border-radius:9px;background:#f8fbf9}
.evidence-ledger h3{margin:0 0 8px}
.evidence-ledger details{border:1px solid #d9e4df;border-radius:7px;background:white;padding:12px;margin:8px 0}
.evidence-ledger summary{cursor:pointer;font-weight:650}
.evidence-ledger a{color:#14634a;overflow-wrap:anywhere}
.evidence-ledger li{padding:7px 0;overflow-wrap:anywhere}
.evidence-ledger small{display:block}
.readiness-grades{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:16px 0}
.readiness-grade{padding:16px;border:1px solid #d9e4df;background:#f7faf8;border-radius:10px;min-width:0}
.readiness-grade .letter{font-size:2rem;line-height:1.2;font-weight:750;margin:8px 0}
.readiness-grade strong{display:block}
.readiness-grade p{overflow-wrap:anywhere}
.readiness-requirements{border:1px solid #d9e4df;border-radius:8px;padding:12px;background:#fcfdfc;margin:12px 0}
.readiness-requirements summary{cursor:pointer;font-weight:650}
.readiness-requirements li{margin:10px 0;overflow-wrap:anywhere}
.readiness-requirements small{display:block}
@media(max-width:520px){.readiness-grades{grid-template-columns:1fr}}
.quant-summary{padding:14px;background:#f4f8f5;border:1px solid #d9e4df;border-radius:8px;line-height:1.55}
.quant-results{display:grid;gap:9px;margin:12px 0}
.quant-results details{border:1px solid #d9e4df;background:#fff;border-radius:8px;padding:12px}
.quant-results summary{cursor:pointer;font-weight:650}
.quant-analysis{padding:11px;margin:10px 0;background:#f6f9f7;border-radius:6px}
.quant-result{overflow-wrap:anywhere}
.investigation-summary{padding:12px 15px;border:1px solid #d9e4df;background:#f4f8f5;border-radius:8px;margin:14px 0}
.investigation-levels{display:grid;gap:8px;margin:12px 0}
.investigation-levels details{border:1px solid #d9e4df;border-radius:8px;padding:12px;background:#fafcfb}
.investigation-levels summary{cursor:pointer;font-weight:650;line-height:1.5}
.investigation-levels summary .level-state{font-weight:400;color:#517565;display:inline-block;margin-left:8px}
.investigation-levels ul{padding-left:20px;margin:10px 0}
.investigation-levels li{margin:5px 0;overflow-wrap:anywhere}
.field-path{font-size:.76rem;color:#587166;overflow-wrap:anywhere}
@media(max-width:760px){.science-domains{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:400px){.science-domains{grid-template-columns:1fr}}
@media(max-width:760px){.layout{grid-template-columns:1fr}.grid{grid-template-columns:repeat(2,1fr)}}
</style>
</head>
<body>
<header><h1>Scientific Assessment — Batch Imports</h1><p>Isolated review environment · ClinicalTrials.gov source records · No trading or scheduled scans</p></header>
<main>
<section>
<h2>Secure access</h2>
<p>Enter the internal API key for this isolated service. The key stays in this page's memory, is sent only in a request header, and is never saved in browser storage or a URL.</p>
<label for="key">Internal API key</label>
<input type="password" id="key" autocomplete="off" placeholder="Enter review-service key">
<div class="row" style="margin-top:12px"><button class="secondary" id="refresh">Refresh history</button><button class="secondary" id="clear">Clear key</button></div>
<div class="status" id="notice" role="status" aria-live="polite"></div>
<div class="status" id="recovery" role="status" aria-live="polite"></div>
</section>
<div class="layout">
<section>
<h2>Submit a controlled batch</h2>
<p>Enter 1–25 exact NCT IDs, one per line. Every line is validated before any new job is accepted. Duplicate and invalid IDs are rejected.</p>
<label for="ids">Clinical trial identifiers</label>
<textarea id="ids" spellcheck="false" placeholder="NCT04280705&#10;NCT02142738"></textarea>
<div class="row"><button id="submit">Start batch import</button><small>No automatic retries or scans</small></div>
<p><small>Submitting imports archival source records, not clinical efficacy scores. A running batch blocks simultaneous submissions.</small></p>
</section>
<section>
<h2>Import progress</h2>
<div class="row"><span class="pill" id="jobstatus">No job selected</span><span id="jobid" class="muted"></span></div>
<div class="grid">
<div class="metric">Processed<strong id="processed">0 / 0</strong></div>
<div class="metric">Imported<strong id="imported">0</strong></div>
<div class="metric">Already saved<strong id="exists">0</strong></div>
<div class="metric">Failed<strong id="failed">0</strong></div>
</div>
<progress id="bar" max="1" value="0" aria-label="Batch progress"></progress>
<h2 style="margin-top:20px">Trial results</h2>
<ol id="events"><li class="muted">Select a job to view its recorded results.</li></ol>
</section>
</div>
<section>
<h2>Scientific evidence assessment</h2>
<p>Inspect the six scientific domains for an exact archived clinical trial. Descriptive registry records are not independently verified efficacy, safety, or FDA evidence. Unverified domains display <strong>Not scored</strong>, not a zero or an invented probability.</p>
<label for="science-id">Exact ClinicalTrials.gov trial ID</label>
<div class="row">
<input id="science-id" style="flex:1;min-width:180px;width:auto" placeholder="NCT04280705" maxlength="11" autocomplete="off" spellcheck="false">
<button id="science-inspect">Inspect scientific evidence</button>
<button class="secondary" id="science-download" disabled>Download 20-stage review packet (JSON)</button>
</div>
<div class="status" id="science-status" role="status" aria-live="polite"></div>
<div id="science-details"></div>
<div id="science-source"></div>
<div class="science-domains" id="science-domains" aria-label="Six scientific evidence domains"></div>
<div id="readiness-grades" aria-live="polite"></div>
<div id="evidence-ledger" aria-live="polite"></div>
<div id="quantitative-results" aria-live="polite"></div>
<div id="investigation-20" aria-live="polite"></div>
</section>
<section><div class="row" style="justify-content:space-between"><h2>Recent batches</h2><small>Last 20 jobs, newest first</small></div><div id="history" class="muted">Authenticate to load history.</div></section>
</main>
<script>
"use strict";
const $ = (id) => document.getElementById(id);
let selectedId = null;
let refreshInProgress = false;
let pollTimer = null;
let posting = false;
let inspectedNct = null;
let downloadingPacket = false;
function notice(message, isError=false) {
  $("notice").textContent = message;
  $("notice").className = "status" + (isError ? " error" : "");
}
async function api(path, options={}) {
  const key = $("key").value;
  if (!key) throw new Error("Enter the internal API key first.");
  const resp = await fetch(path, {
    ...options, credentials:"omit", cache:"no-store",
    headers: {"x-pdufa-internal-key":key, ...(options.headers||{})}
  });
  if (!resp.ok) {
    if (resp.status === 401) throw new Error("Invalid internal API key.");
    if (resp.status === 403) throw new Error("Batch writing is disabled outside this review service.");
    if (resp.status === 409) throw new Error("Another batch is unfinished. Review its status before submitting a new one.");
    if (resp.status === 503) throw new Error("Review database or API is unavailable.");
    if (resp.status === 422) throw new Error("Invalid batch: check all NCT identifiers.");
    throw new Error("Request failed (HTTP " + resp.status + ").");
  }
  return resp.json();
}
function paintJob(job) {
  selectedId = job.id;
  $("jobstatus").textContent = job.status.replaceAll("_"," ");
  $("jobid").textContent = "Job " + job.id.slice(0,8);
  $("processed").textContent = job.processed + " / " + job.total;
  $("imported").textContent = job.imported;
  $("exists").textContent = job.already_exists;
  $("failed").textContent = job.failed;
  $("bar").max = job.total || 1; $("bar").value = job.processed;
  const list = $("events"); list.replaceChildren();
  if (!job.events.length) {
    const li = document.createElement("li");li.className="muted";
    li.textContent="No trial results recorded yet.";list.appendChild(li);
  }
  for (const event of job.events) {
    const li = document.createElement("li");
    li.textContent = event.index + ". " + event.nct_id + ": " + event.status
      + (event.error_type ? " (" + event.error_type
      + (event.http_status ? " HTTP " + event.http_status : "") + ")" : "");
    list.appendChild(li);
  }
}
async function loadSelected(id) {
  if (!id) return;
  try {
    const job = await api("/api/scientific-assessment/batches/"+encodeURIComponent(id));
    paintJob(job);
    if (!["queued","running"].includes(job.status)) {stopPolling();}
    else startPolling();
  } catch (err) { notice(err.message, true); }
}
function stopPolling(){if(pollTimer){clearInterval(pollTimer);pollTimer=null;}}
function startPolling(){if(!pollTimer)pollTimer=setInterval(()=>loadSelected(selectedId),4000);}
async function refreshHistory() {
  if (refreshInProgress) return;
  refreshInProgress = true;
  try {
    const diagnostics = await api("/api/scientific-assessment/batches-recovery-status");
    $("recovery").textContent = diagnostics.potentially_interrupted
      ? "Attention: an unfinished batch has not updated for over 60 minutes. Do not restart or retry it until the prior worker is confirmed stopped. Contact the review-service operator."
      : "";
    $("recovery").className = "status" + (diagnostics.potentially_interrupted ? " error" : "");
    const data = await api("/api/scientific-assessment/batches");
    const container=$("history");container.replaceChildren();
    if (!data.jobs.length){container.textContent="No batches submitted yet.";return;}
    for (const job of data.jobs) {
      const btn=document.createElement("button");btn.type="button";
      btn.textContent=new Date(job.created_at).toLocaleString()+" · "+job.status.replaceAll("_"," ")
          +" · "+job.processed+"/"+job.total+" trials";
      if(job.id===selectedId)btn.className="selected";
      btn.addEventListener("click",()=>loadSelected(job.id));
      container.appendChild(btn);
    }
    if (!selectedId) await loadSelected(data.jobs[0].id);
    notice("History updated.");
  } catch (err) {notice(err.message,true);}
  finally {refreshInProgress=false;}
}
const DOMAIN_LABELS = {
  trial_design:"Trial design", efficacy:"Efficacy", safety:"Safety",
  biology:"Biology", reliability:"Reliability", regulatory:"Regulatory"
};
function clearScience() {
  inspectedNct=null;
  $("science-download").disabled=true;
  $("science-status").textContent="";
  $("science-details").textContent="";
  $("science-source").replaceChildren();
  $("science-domains").replaceChildren();
  $("investigation-20").replaceChildren();
  $("quantitative-results").replaceChildren();
  $("readiness-grades").replaceChildren();
  $("evidence-ledger").replaceChildren();
}
async function downloadCapturedSourcePdf(documentMeta) {
  const nct=documentMeta.nctId;
  if(!inspectedNct || inspectedNct!==nct
      || $("science-id").value.trim()!==nct
      || !/^NCT\d{8}$/.test(nct)
      || !/^[a-f0-9]{32}$/.test(documentMeta.documentId)
      || !/^[a-f0-9]{64}$/.test(documentMeta.sha256)){
    throw new Error("Inspect this exact archived trial before downloading source bytes.");
  }
  const key=$("key").value;
  if(!key)throw new Error("Enter your internal review API key.");
  const url="/api/scientific-assessment/source-documents/"+nct+"/"+documentMeta.documentId;
  const response=await fetch(url,{method:"GET",credentials:"omit",cache:"no-store",
    headers:{"x-pdufa-internal-key":key}});
  if(!response.ok)throw new Error("Archived source unavailable or integrity check failed (HTTP "+response.status+").");
  if(response.headers.get("x-source-document-sha256")!==documentMeta.sha256)
    throw new Error("Source document digest metadata mismatch.");
  const array=await response.arrayBuffer();
  if(array.byteLength!==documentMeta.byteLength)
    throw new Error("Source document size mismatch.");
  if(!window.crypto || !window.crypto.subtle)
    throw new Error("Secure browser crypto is required to verify this document.");
  const hashed=await window.crypto.subtle.digest("SHA-256",array);
  const computed=Array.from(new Uint8Array(hashed))
    .map(byte=>byte.toString(16).padStart(2,"0")).join("");
  if(computed!==documentMeta.sha256)
    throw new Error("Source document byte checksum verification failed.");
  const href=URL.createObjectURL(new Blob([array],{type:"application/pdf"}));
  try{
    const a=document.createElement("a");a.href=href;a.download=documentMeta.filename;
    document.body.appendChild(a);a.click();a.remove();
  }finally{
    setTimeout(()=>URL.revokeObjectURL(href),20000);
  }
  $("science-status").textContent="Archived source PDF downloaded with matching SHA-256. Document authenticity and clinical contents remain unverified.";
  $("science-status").className="status";
}
function paintEvidenceLedger(data, status) {
  const root=$("evidence-ledger");root.replaceChildren();
  const section=document.createElement("section");section.className="evidence-ledger";
  const title=document.createElement("h3");
  title.textContent="Independent source evidence ledger";
  section.appendChild(title);
  if(status!=="candidate_inventory_loaded" || !data){
    const info=document.createElement("p");
    info.textContent=(status==="ledger_unavailable_or_invalid")
       ?"Evidence ledger unavailable or failed integrity validation. Existing scientific grades are unchanged."
       :"Independent evidence ledger not loaded for this trial.";
    section.appendChild(info);root.appendChild(section);return;
  }
  const intro=document.createElement("p");
  intro.textContent=(data.candidateCount||0)+" preidentified bibliographic citations · "
     +(data.entryCount||0)+" stored candidate revisions · "
     +(data.verifiedGateCount||0)+"/4 independently verified gates. "
     +"None of these candidates automatically change scientific grades.";
  section.appendChild(intro);
  const gates=document.createElement("details");gates.open=false;
  const gatesHeading=document.createElement("summary");
  gatesHeading.textContent="View required independent evidence gates";gates.appendChild(gatesHeading);
  const gateList=document.createElement("ul");
  for(const g of data.externalGateStatuses||[]){
    const li=document.createElement("li");
    li.textContent=g.label+" — "+(g.independentlyVerified?"Independently verified":"Needs independent review");
    gateList.appendChild(li);
  }
  gates.appendChild(gateList);section.appendChild(gates);
  function safeLink(parent,url,label){
    try{
      const parsed=new URL(url);
      if(parsed.protocol!=="https:"||parsed.username||parsed.password||!parsed.hostname)return;
      const link=document.createElement("a");
      link.href=parsed.href;link.target="_blank";link.rel="noopener noreferrer";
      link.textContent=label;parent.appendChild(link);
    }catch{}
  }
  const candidates=document.createElement("details");
  const candidateHeading=document.createElement("summary");
  candidateHeading.textContent="Preidentified published/agency citations ("+(data.candidateCount||0)+") — not adjudicated";
  candidates.appendChild(candidateHeading);
  const candidateList=document.createElement("ol");
  for(const item of data.identifiedSourceCandidates||[]){
    const li=document.createElement("li");
    safeLink(li,item.sourceUrl,item.title||item.sourceType||"Source citation");
    const meta=document.createElement("small");
    meta.textContent="Evidence gate: "+item.gateId+" · "+item.reviewStatus+" · Independently verified: NO";
    li.appendChild(meta);
    const caveat=document.createElement("small");caveat.textContent=item.caution||"Requires appraisal";
    li.appendChild(caveat);candidateList.appendChild(li);
  }
  if(!candidateList.children.length){
    const note=document.createElement("li");
    note.textContent="No preidentified independent citations for this archived trial.";
    candidateList.appendChild(note);
  }
  candidates.appendChild(candidateList);section.appendChild(candidates);
  const matrix=data.sourceReconciliation;
  if(matrix && Array.isArray(matrix.checks)){
    const reconciliation=document.createElement("details");
    const reconciliationHeading=document.createElement("summary");
    reconciliationHeading.textContent="Source reconciliation questions ("
       +matrix.unresolvedChecks+" open of "+matrix.totalChecks+") — not adjudicated";
    reconciliation.appendChild(reconciliationHeading);
    const summary=document.createElement("p");
    summary.textContent="These are unresolved analytical questions; source links and potential discrepancies are not independent clinical findings.";
    reconciliation.appendChild(summary);
    const worklist=document.createElement("ol");worklist.className="reconciliation-questions";
    for(const item of matrix.checks){
      const li=document.createElement("li");
      const heading=document.createElement("strong");
      heading.textContent="["+item.priority.toUpperCase()+"] "+item.title+" — OPEN";
      li.appendChild(heading);
      const q=document.createElement("p");q.textContent="Question: "+item.question;
      li.appendChild(q);
      if(item.observedDiscrepancy){
        const contrast=document.createElement("p");
        contrast.textContent="Potential discrepancy: "+item.observedDiscrepancy;
        li.appendChild(contrast);
      }
      const action=document.createElement("small");
      action.textContent="Required review: "+item.nextAction;
      li.appendChild(action);
      const urls=document.createElement("div");
      for(const url of item.sourceUrls||[]){
        safeLink(urls,url,"View source");
        urls.appendChild(document.createTextNode("  "));
      }
      li.appendChild(urls);
      worklist.appendChild(li);
    }
    reconciliation.appendChild(worklist);section.appendChild(reconciliation);
  }
  const ledger=document.createElement("details");
  const ledgerHeading=document.createElement("summary");
  ledgerHeading.textContent="Persistent source revision history ("+(data.entryCount||0)+")";
  ledger.appendChild(ledgerHeading);
  const entries=document.createElement("ol");
  for(const entry of data.entries||[]){
    const li=document.createElement("li");
    safeLink(li,entry.sourceUrl,entry.gateId+" · "+entry.sourceType);
    const info=document.createElement("small");
    info.textContent="Version "+entry.revision
        +" · "+entry.relationship+" · "+entry.reviewStatus
        +" · Entered by "+entry.recordedBy+" on "+entry.recordedAt;
    li.appendChild(info);
    const claim=document.createElement("p");claim.textContent=entry.claimText;
    li.appendChild(claim);
    const caution=document.createElement("small");
    caution.textContent="Uncertainty: "+entry.caution+" · SHA-256: "+entry.contentSha256;
    li.appendChild(caution);entries.appendChild(li);
  }
  if(!entries.children.length){
    const empty=document.createElement("li");empty.textContent="No persisted review candidates yet.";
    entries.appendChild(empty);
  }
  ledger.appendChild(entries);section.appendChild(ledger);
  const findings=data.reviewerFindings;
  if(findings){
    const notes=document.createElement("details");
    const title=document.createElement("summary");
    title.textContent="Source-linked reviewer statements ("+(findings.totalStatements||0)+
      ") · "+(findings.questionsWithConflictingStatements||0)+" questions disputed";
    notes.appendChild(title);
    const note=document.createElement("p");
    note.textContent="Reviewer names are self-declared. These assertions are NOT authenticated professional opinions, independent findings, or resolved evidence gates.";
    notes.appendChild(note);
    const list=document.createElement("ol");list.className="reviewer-statements";
    for(const item of findings.statements||[]){
      const li=document.createElement("li");
      const descriptor=document.createElement("strong");
      descriptor.textContent=item.questionId+" · "+item.findingType+
        " · version "+item.revision+" · not independently confirmed";
      li.appendChild(descriptor);
      const link=document.createElement("div");
      safeLink(link,item.sourceUrl,"View source");
      li.appendChild(link);
      for(const line of [
        "Source location: "+item.sourceLocator,
        "Claim: "+item.assertion,
        "Uncertainty: "+item.uncertainty,
        "Reviewer label: "+item.reviewerLabel+" (identity not authenticated)",
        "Recorded: "+item.reviewedAt+" · SHA-256: "+item.contentSha256,
      ]){
        const p=document.createElement("p");p.textContent=line;li.appendChild(p);
      }
      list.appendChild(li);
    }
    if(!list.children.length){
      const empty=document.createElement("li");
      empty.textContent="No reviewer source statements recorded yet. All questions remain open.";
      list.appendChild(empty);
    }
    notes.appendChild(list);section.appendChild(notes);
  }
  const captured=data.capturedSourceDocuments;
  if(captured && captured.nctId===inspectedNct){
    const docSection=document.createElement("details");
    docSection.className="captured-source-documents";
    const heading=document.createElement("summary");
    heading.textContent="Preserved source PDFs ("+(captured.sourceDocumentCount||0)
      +") — byte integrity checked, NOT scientifically verified";
    docSection.appendChild(heading);
    const caveat=document.createElement("p");
    caveat.textContent="Captured PDFs are curated file submissions, not independently authenticated publisher files. SHA-256 checks file consistency only; approval and clinical conclusions remain unscored.";
    docSection.appendChild(caveat);
    const list=document.createElement("ol");
    for(const item of captured.documents||[]){
      const li=document.createElement("li");
      const name=document.createElement("strong");
      name.textContent=item.gateId+" · "+item.sourceType+" · "+item.byteLength+" bytes";
      li.appendChild(name);
      const link=document.createElement("div");
      safeLink(link,item.sourceUrl,"Original source locator");
      li.appendChild(link);
      for(const line of ["Captured: "+item.capturedAt,
                         "SHA-256 bytes: "+item.sha256,
                         "Manifest SHA-256: "+item.manifestSha256,
                         "Publisher authorship verified: NO · Clinically adjudicated: NO"]){
        const p=document.createElement("small");p.textContent=line;li.appendChild(p);
      }
      const button=document.createElement("button");
      button.type="button";button.textContent="Download checked PDF";
      button.addEventListener("click",async()=>{
        button.disabled=true;
        try{await downloadCapturedSourcePdf(item);}
        catch(err){
          $("science-status").textContent=err.message;
          $("science-status").className="status error";
        }finally{button.disabled=false;}
      });
      li.appendChild(button);list.appendChild(li);
    }
    if(!list.children.length){
      const li=document.createElement("li");
      li.textContent="No PDF bytes have been archived yet. Source hyperlinks alone do not qualify as a captured document.";
      list.appendChild(li);
    }
    docSection.appendChild(list);section.appendChild(docSection);
  }
  const preflight=data.adjudicationPreflight;
  if(preflight && preflight.mode==="read_only_blocker_diagnostic"){
    const report=document.createElement("details");
    report.className="adjudication-preflight";
    const summary=document.createElement("summary");
    summary.textContent="Scientific adjudication blockers — "
      +preflight.questionsReadyForAdjudication+"/"
      +preflight.questionCount+" questions ready · "
      +preflight.questionsWithCurrentDisputes+" disputed";
    report.appendChild(summary);
    const caution=document.createElement("p");
    caution.textContent="Reviewer labels are unverified, cited document contents are not independently authenticated, and there is no final reviewer sign-off. Notes never resolve a question.";
    report.appendChild(caution);
    const blockers=document.createElement("ol");
    for(const reason of preflight.globalBlockers||[]){
      const item=document.createElement("li");
      const label=document.createElement("strong");label.textContent=reason.reason;
      item.appendChild(label);
      const action=document.createElement("small");
      action.textContent="Next: "+reason.nextAction;
      item.appendChild(action);blockers.appendChild(item);
    }
    report.appendChild(blockers);
    const title=document.createElement("p");
    title.textContent="Per-question audit status: "
      +preflight.questionsWithRecordedObservations+" with source-linked reviewer observations, "
      +preflight.questionsIndependentlyResolved+" independently resolved.";
    report.appendChild(title);
    const questions=document.createElement("ol");
    for(const item of preflight.questions||[]){
      const line=document.createElement("li");
      const heading=document.createElement("strong");
      heading.textContent=item.question+" — BLOCKED";
      line.appendChild(heading);
      const detail=document.createElement("small");
      detail.textContent=item.currentReviewerThreadCount+" current statement threads · "
        +item.distinctSourceCount+" linked sources · "
        +(item.conflictingCurrentStatements?"CONFLICTING STATEMENTS":"No current support/contradiction pair")
        +" · reviewer identity NOT authenticated";
      line.appendChild(detail);questions.appendChild(line);
    }
    report.appendChild(questions);section.appendChild(report);
  }
  const warning=document.createElement("p");
  warning.textContent="Source citations and audit entries are candidates, not independent adjudications. No FDA approval prediction or scientific verdict is assigned.";
  section.appendChild(warning);root.appendChild(section);
}
function paintReadinessGrades(data) {
  const root=$("readiness-grades");root.replaceChildren();
  if(!data || data.sourceStatus!=="archived_registry_input_audit_only"
      || !Array.isArray(data.requirements)
      || !data.analysisReadiness || !data.scientificReluctance)return;
  const heading=document.createElement("h3");
  heading.textContent="Two evidence grades — readiness and reluctance";
  root.appendChild(heading);
  const lead=document.createElement("p");
  lead.textContent="Both grades measure evidence availability and uncertainty—not whether the trial succeeded or whether FDA will approve the drug.";
  root.appendChild(lead);
  const cards=document.createElement("div");cards.className="readiness-grades";
  const first=document.createElement("div");first.className="readiness-grade";
  const firstTitle=document.createElement("strong");firstTitle.textContent="1. Analysis input readiness";first.appendChild(firstTitle);
  const firstLetter=document.createElement("div");firstLetter.className="letter";
  firstLetter.textContent=data.analysisReadiness.grade+" · "+data.analysisReadiness.coveragePercent+"% inputs";first.appendChild(firstLetter);
  const firstVerdict=document.createElement("p");
  firstVerdict.textContent="Full scientific conclusion: "+(data.analysisReadiness.readyForFullScientificConclusion?"READY":"NOT READY")
      +" · "+data.analysisReadiness.requirementsCovered+"/"+data.analysisReadiness.requirementsTotal
      +" evidence requirements documented.";
  first.appendChild(firstVerdict);
  const firstExplanation=document.createElement("p");
  firstExplanation.textContent="Letter grade is input coverage only. It is not a drug efficacy score.";
  first.appendChild(firstExplanation);cards.appendChild(first);
  const second=document.createElement("div");second.className="readiness-grade";
  const secondTitle=document.createElement("strong");secondTitle.textContent="2. Scientific reluctance";second.appendChild(secondTitle);
  const secondLetter=document.createElement("div");secondLetter.className="letter";
  secondLetter.textContent=data.scientificReluctance.grade+" · "+data.scientificReluctance.level;second.appendChild(secondLetter);
  const secondVerdict=document.createElement("p");
  secondVerdict.textContent="Reluctance to reach a scientific conclusion: "+data.scientificReluctance.reluctanceToConclude+".";
  second.appendChild(secondVerdict);
  const secondExplanation=document.createElement("p");
  secondExplanation.textContent="F means withhold a scientific conclusion because independent inputs are missing. It does NOT mean the clinical trial failed.";
  second.appendChild(secondExplanation);cards.appendChild(second);
  root.appendChild(cards);
  const requirements=document.createElement("details");requirements.className="readiness-requirements";
  const requirementsTitle=document.createElement("summary");
  requirementsTitle.textContent="Inspect all "+data.requirements.length+" evidence gates and missing inputs";
  requirements.appendChild(requirementsTitle);
  const items=document.createElement("ol");
  for(const gate of data.requirements){
    const li=document.createElement("li");
    const label=document.createElement("strong");
    label.textContent=gate.label+" — "+(gate.available?"Source available":"Missing / not independently verified");
    li.appendChild(label);
    const source=document.createElement("small");
    source.textContent="Evidence: "+gate.evidenceLevel
        +(gate.sourcePath?" · "+gate.sourcePath:"");
    li.appendChild(source);
    const next=document.createElement("small");
    next.textContent="Next: "+gate.nextAction;
    li.appendChild(next);items.appendChild(li);
  }
  requirements.appendChild(items);root.appendChild(requirements);
  const note=document.createElement("p");
  note.textContent="No FDA approval probability, efficacy verdict or verified scientific score is assigned by these grades.";
  root.appendChild(note);
}
function paintQuantitativeResults(data) {
  const root=$("quantitative-results");root.replaceChildren();
  if(!data || data.sourceStatus!=="registry_reported_not_independently_verified")return;
  const heading=document.createElement("h3");
  heading.textContent="Reported outcomes and safety — not independently verified";
  root.appendChild(heading);
  const summary=document.createElement("p");summary.className="quant-summary";
  summary.textContent="Registry-reported: "+data.outcomeCountTotal+" outcome measures, "
    +data.analysisCountTotal+" statistical analyses, "+data.reportedPValuesShown
    +" displayed p-values and "+data.reportedConfidenceIntervalsShown
    +" displayed confidence intervals. "
    +(data.truncated?"Display capped; inspect full registry source for omitted rows. ":"")
    +"No statistical-success grade, multiplicity adjustment, benefit-risk conclusion, "
    +"or FDA approval probability has been calculated.";
  root.appendChild(summary);
  const outcomes=document.createElement("div");outcomes.className="quant-results";
  if(!Array.isArray(data.outcomes)||!data.outcomes.length){
    const empty=document.createElement("p");empty.textContent="No numeric outcome measures were included in this archived registry snapshot.";
    root.appendChild(empty);
  } else for(const outcome of data.outcomes){
    const wrap=document.createElement("details");wrap.className="quant-result";
    const title=document.createElement("summary");
    title.textContent=(outcome.outcomeType||"UNCLASSIFIED")+" · "+(outcome.title||"Untitled outcome")
      +" · "+outcome.reportedAnalyses+" reported analyses";
    wrap.appendChild(title);
    const desc=document.createElement("p");
    desc.textContent="Unit: "+(outcome.unit||"not reported")
      +" · Time frame: "+(outcome.timeFrame||"not reported");
    wrap.appendChild(desc);
    const groups=document.createElement("p");
    groups.textContent="Registry group labels: "+(
      Array.isArray(outcome.groups)&&outcome.groups.length
      ? outcome.groups.map(x=>(x.id||"?")+": "+(x.title||"unnamed")).join(" · ")
      : "not documented"
    );
    wrap.appendChild(groups);
    const analyses=Array.isArray(outcome.analyses)?outcome.analyses:[];
    if(!analyses.length){
      const missing=document.createElement("p");missing.textContent="No reported comparative analyses in this outcome entry.";
      wrap.appendChild(missing);
    }
    for(const a of analyses){
      const item=document.createElement("div");item.className="quant-analysis";
      const lines=[
        "Method: "+(a.method||"not reported")+" · Parameter: "+(a.parameterType||outcome.parameterType||"not reported"),
        "Estimate: "+(a.reportedEstimate??"not reported")+" · Reported p-value: "+(a.pValueReported??"not reported"),
        "Confidence interval ("+(a.confidenceIntervalPercent??"?")+"%, "+(a.confidenceIntervalSides||"sides not specified")
          +"): "+(a.confidenceIntervalLower??"not reported")+" to "+(a.confidenceIntervalUpper??"not reported"),
        "Compared group IDs: "+(Array.isArray(a.groupIds)&&a.groupIds.length?a.groupIds.join(", "):"not reported"),
        "Archived JSON path: "+a.sourceFieldPath,
      ];
      for(const line of lines){
        const p=document.createElement("p");p.textContent=line;item.appendChild(p);
      }
      wrap.appendChild(item);
    }
    outcomes.appendChild(wrap);
  }
  root.appendChild(outcomes);
  const safety=data.safety||{};
  const safetyTitle=document.createElement("h4");safetyTitle.textContent="Reported adverse events";
  root.appendChild(safetyTitle);
  const counts=document.createElement("p");
  counts.textContent="Serious event terms: "+(safety.seriousEventTermCountTotal??0)
    +" · Other event terms: "+(safety.otherEventTermCountTotal??0)
    +" · Registry event groups: "+(safety.adverseEventGroupCount??0)
    +". Counts and denominators are displayed as reported; comparative risk is not inferred.";
  root.appendChild(counts);
  const serious=Array.isArray(safety.seriousEventTermsShown)?safety.seriousEventTermsShown:[];
  const safetyList=document.createElement("div");safetyList.className="quant-results";
  for(const event of serious){
    const card=document.createElement("details");
    const title=document.createElement("summary");title.textContent=event.term||"Unnamed serious adverse event";
    card.appendChild(title);
    for(const g of event.groupStats||[]){
      const p=document.createElement("p");
      p.textContent="Group "+(g.groupId||"?")+" · Affected: "+(g.numAffected??"unreported")
        +" · At risk: "+(g.numAtRisk??"unreported")
        +" · Events: "+(g.numEvents??"unreported");
      card.appendChild(p);
    }
    safetyList.appendChild(card);
  }
  root.appendChild(safetyList);
  const caveat=document.createElement("p");
  caveat.textContent="Archived posting only. These figures require denominator, trial-design, source-date, confidence interval, multiplicity, and independent-publication review.";
  root.appendChild(caveat);
}
function paintInvestigation20(data) {
  const root=$("investigation-20");
  root.replaceChildren();
  if(!data || data.status!=="source_coverage_only" || !Array.isArray(data.levels)
       || data.levels.length!==20) return;
  const heading=document.createElement("h3");
  heading.textContent="20-stage scientific investigation · source-coverage map";
  root.appendChild(heading);
  const summary=document.createElement("div");summary.className="investigation-summary";
  summary.textContent=(data.levelsWithSourceFields||0)+"/20 stages have some registry fields. "
      +(data.levelsRequiringExternalReview||0)+" stages require independent external review. "
      +"Scientifically verified: 0/20. FDA approval probability: Not calculated."
      +(data.retrievedAt ? " Archive retrieved: "+data.retrievedAt : "");
  root.appendChild(summary);
  const caution=document.createElement("p");
  caution.textContent="A recorded field does not mean the scientific question is answered. Expand a stage to inspect archived JSON field paths and unresolved evidence needs.";
  root.appendChild(caution);
  const list=document.createElement("div");list.className="investigation-levels";
  for(const level of data.levels){
    const details=document.createElement("details");
    const summaryNode=document.createElement("summary");
    const statusText=level.status==="external_review_required"
      ? "External review required"
      : level.status==="registry_fields_present" ? "Registry fields present" : "No registry evidence";
    summaryNode.textContent=String(level.level).padStart(2,"0")+" · "+level.title;
    const label=document.createElement("span");label.className="level-state";
    label.textContent=statusText+" · "+level.sourceEvidenceCount+"/"+level.sourceFieldCount+" fields";
    summaryNode.appendChild(label);
    details.appendChild(summaryNode);
    const caveat=document.createElement("p");caveat.textContent=level.caution;
    details.appendChild(caveat);
    if(Array.isArray(level.observations) && level.observations.length){
      const items=document.createElement("ul");
      for(const observed of level.observations){
        const li=document.createElement("li");
        const present=observed.present ? "Present in archive" : "Not available";
        li.textContent=observed.label+" — "+present
          +(observed.count!==undefined ? " · "+observed.count+" entries" : "")
          +(observed.value!==undefined ? " · "+String(observed.value) : "");
        const path=document.createElement("div");path.className="field-path";
        path.textContent=observed.fieldPath;li.appendChild(path);items.appendChild(li);
      }
      details.appendChild(items);
    } else {
      const empty=document.createElement("p");
      empty.textContent="No directly sufficient ClinicalTrials.gov field. Independent evidence and expert adjudication required.";
      details.appendChild(empty);
    }
    list.appendChild(details);
  }
  root.appendChild(list);
}
async function inspectScience() {
  const id = $("science-id").value.trim();
  clearScience();
  if(!/^NCT\d{8}$/.test(id)) {
    $("science-status").textContent="Enter an exact NCT identifier (NCT followed by eight digits).";
    $("science-status").className="status error";
    return;
  }
  $("science-inspect").disabled=true;
  $("science-status").textContent="Loading verified archive metadata...";
  $("science-status").className="status";
  try {
    const result=await api("/api/scientific-assessment?exact_id="+encodeURIComponent("TRIAL|"+id));
    const assessment=result.assessment||{};
    const evidence=result.registryEvidence;
    const archived=result.registryEvidenceStatus==="source_record_loaded" && evidence
        && evidence.nctId===id && evidence.verificationStatus==="source_record_only";
    if(archived && result.evidenceLedgerStatus==="candidate_inventory_loaded"
        && result.evidenceLedger){
      inspectedNct=id;
      $("science-download").disabled=false;
    }
    paintInvestigation20(result.investigation20);
    paintQuantitativeResults(result.quantitativeResults);
    paintReadinessGrades(result.readinessGrades);
    paintEvidenceLedger(result.evidenceLedger, result.evidenceLedgerStatus);
    const overall=assessment.overall_score;
    $("science-status").textContent="Evidence: "+(archived ? "archived source record, descriptive only" :
       result.registryEvidenceStatus==="record_not_found" ? "no archived record" :
       result.registryEvidenceStatus==="record_unavailable_or_invalid" ? "archived record unavailable or invalid" :
       "independent evidence not available")+
       " · Overall scientific score: "+(overall === null || overall === undefined ? "Not scored" : String(overall));
    if(archived) {
      const meta=evidence.metadata||{};
      const n=meta.enrollment;
      $("science-details").textContent="Registry status: "+(meta.overallStatus||"not reported")
        +" · Enrollment: "+(Number.isInteger(n) ? n : "not reported")
        +" · Primary endpoints listed: "+(Array.isArray(meta.primaryOutcomes)?meta.primaryOutcomes.length:0);
      const link=document.createElement("a");
      const expected="https://clinicaltrials.gov/study/"+id;
      link.href=expected;link.target="_blank";link.rel="noopener noreferrer";
      link.textContent="View source record on ClinicalTrials.gov";
      $("science-source").appendChild(link);
    }
    const domains=assessment.domains||{};
    for(const [key,label] of Object.entries(DOMAIN_LABELS)) {
      const domain=domains[key]||{};
      const card=document.createElement("div");
      card.className="science-domain";
      const name=document.createElement("strong");name.textContent=label;card.appendChild(name);
      const value=document.createElement("strong");
      value.textContent=(domain.verified && typeof domain.score==="number" && Number.isFinite(domain.score))
          ? domain.score.toFixed(2)+"/100" : "Not scored";
      card.appendChild(value);
      const coverage=document.createElement("small");
      coverage.textContent="Verified fields: "+(domain.verified_fields||0)+"/"+(domain.required_fields||0);
      card.appendChild(coverage);
      const missing=document.createElement("small");
      const fields=Array.isArray(domain.missing_fields)?domain.missing_fields:[];
      missing.textContent=fields.length?"Missing: "+fields.join(", ").replaceAll("_"," "):"All required fields verified";
      card.appendChild(missing);
      $("science-domains").appendChild(card);
    }
  } catch(err) {
    $("science-status").textContent=err.message;
    $("science-status").className="status error";
  } finally {$("science-inspect").disabled=false;}
}
async function downloadReviewPacket() {
  const nct=inspectedNct;
  if(downloadingPacket || !nct || $("science-id").value.trim()!==nct
     || !/^NCT\d{8}$/.test(nct)){
    $("science-status").textContent="Inspect an exact archived trial before downloading its review packet.";
    $("science-status").className="status error";
    return;
  }
  downloadingPacket=true;$("science-download").disabled=true;
  try {
    const packet=await api("/api/scientific-assessment/review-packet/"+nct);
    if(packet.nctId!==nct || packet.packetSchemaVersion!=="scientific-source-review-packet-v1"
       || packet.scientificConclusion!==null
       || !packet.packetIntegrity || !/^[0-9a-f]{64}$/.test(packet.packetIntegrity.digest)
       || packet.readyForFullScientificConclusion!==false){
      throw new Error("Scientific packet identity or evidence safety validation failed.");
    }
    const payload=JSON.stringify(packet,null,2);
    const blob=new Blob([payload],{type:"application/json;charset=utf-8"});
    const href=URL.createObjectURL(blob);
    try {
      const a=document.createElement("a");
      a.href=href;a.download=nct+"_scientific_review_packet.json";
      document.body.appendChild(a);a.click();a.remove();
    } finally {
      setTimeout(()=>URL.revokeObjectURL(href),2000);
    }
    $("science-status").textContent="Unadjudicated scientific review packet downloaded for "+nct
        +". Verify its SHA-256 integrity before any independent analysis.";
    $("science-status").className="status";
  } catch(err){
    $("science-status").textContent=err.message;
    $("science-status").className="status error";
  } finally {
    downloadingPacket=false;
    $("science-download").disabled=inspectedNct!==nct;
  }
}
$("science-inspect").addEventListener("click",inspectScience);
$("science-download").addEventListener("click",downloadReviewPacket);
$("refresh").addEventListener("click",refreshHistory);
$("clear").addEventListener("click",()=>{
  $("key").value="";stopPolling(); selectedId=null;
  $("history").textContent="Authenticate to load history.";
  $("recovery").textContent="";
  clearScience();
  $("events").replaceChildren();notice("Key cleared from the page.");});
$("submit").addEventListener("click",async()=>{
  if(posting)return;
  const ids=$("ids").value.trim().split(/\r?\n/).map(x=>x.trim()).filter(Boolean);
  if(ids.length<1||ids.length>25||ids.some(x=>!/^NCT\d{8}$/.test(x))
     ||new Set(ids).size!==ids.length){
    notice("Enter 1–25 distinct exact NCT identifiers, one per line.",true);return;
  }
  posting=true;$("submit").disabled=true;notice("Submitting batch...");
  try {
    const job=await api("/api/scientific-assessment/batches", {
      method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({nct_ids:ids})
    });
    paintJob(job);notice("Batch accepted. Progress will update automatically.");
    await refreshHistory();startPolling();
  } catch(err){notice(err.message,true);}
  finally{posting=false;$("submit").disabled=false;}
});
$("key").addEventListener("change",()=>{if($("key").value){refreshHistory();}});
</script>
</body></html>"""
    return HTMLResponse(
        content=html,
        headers={
            "Cache-Control": "no-store",
            "Content-Security-Policy": (
                "default-src 'none'; script-src 'unsafe-inline'; "
                "style-src 'unsafe-inline'; connect-src 'self'; "
                "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
            ),
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "no-referrer",
        },
    )
