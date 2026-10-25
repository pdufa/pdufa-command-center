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
</div>
<div class="status" id="science-status" role="status" aria-live="polite"></div>
<div id="science-details"></div>
<div id="science-source"></div>
<div class="science-domains" id="science-domains" aria-label="Six scientific evidence domains"></div>
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
  $("science-status").textContent="";
  $("science-details").textContent="";
  $("science-source").replaceChildren();
  $("science-domains").replaceChildren();
  $("investigation-20").replaceChildren();
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
    paintInvestigation20(result.investigation20);
    const archived=result.registryEvidenceStatus==="source_record_loaded" && evidence
        && evidence.nctId===id && evidence.verificationStatus==="source_record_only";
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
$("science-inspect").addEventListener("click",inspectScience);
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
