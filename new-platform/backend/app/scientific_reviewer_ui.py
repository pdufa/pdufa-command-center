"""Independent reviewer portal; one Google account per real reviewer.

This page cannot provision itself, sign off on science, resolve evidence gates,
promote scores, or use the owner's Google operator session. Reviewer identities
and clinical qualifications must be separately administrator verified.
"""
from __future__ import annotations

from html import escape

_PAGE = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="referrer" content="no-referrer">
  <title>PDUFA · Independent scientific review</title>
  <style nonce="__NONCE__">
    :root{color-scheme:light;font-family:system-ui,-apple-system,sans-serif}
    body{margin:0;background:#f3f7fb;color:#172b40}
    main{max-width:990px;margin:auto;padding:30px 18px 64px}
    h1{font-size:clamp(1.6rem,4vw,2.35rem);margin:8px 0}
    h2{font-size:1.2rem} h3{font-size:1.05rem}
    .eyebrow{font-size:.8rem;letter-spacing:.12em;font-weight:700;color:#355978}
    .panel{background:#fff;border:1px solid #cad8e6;border-radius:12px;padding:20px;margin:16px 0}
    .muted{color:#53677b;line-height:1.55} .important{border-left:4px solid #b77c1b;padding-left:13px}
    .status{font-weight:650;padding:10px 0;white-space:pre-wrap}
    .hide{display:none} a{color:#13517f}
    button{background:#19476b;color:white;padding:11px 15px;border:0;border-radius:8px;font-weight:650;cursor:pointer}
    button:disabled{background:#8699a5;cursor:not-allowed}
    label{display:block;font-weight:650;margin:13px 0 6px}
    select,input[type=text],textarea{box-sizing:border-box;padding:10px;border:1px solid #8c9eb1;border-radius:7px;font:inherit;max-width:100%;width:100%}
    input[type=text]{max-width:320px} textarea{min-height:110px;resize:vertical}
    details{margin:10px 0;border:1px solid #dae2e9;border-radius:9px;padding:12px}
    summary{cursor:pointer;font-weight:650} ul{line-height:1.65}
    .source-row{padding:10px 0;border-bottom:1px solid #e2e8ed}
    .source-row button{margin-top:7px}
    .foot{font-size:.85rem;color:#526578}
  </style>
  <script nonce="__NONCE__" src="https://accounts.google.com/gsi/client" async defer></script>
</head>
<body>
<main>
  <div class="eyebrow">PDUFA · ISOLATED SCIENTIFIC REVIEW</div>
  <h1>Independent reviewer workspace</h1>
  <p class="muted important">
    This workspace requires a <strong>separate Google reviewer identity</strong>,
    prior administrator provisioning, and independently verified credentials.
    The scientific operator cannot serve as their own reviewer. Even two
    reviewer statements are not scientific sign-off.
  </p>
  <section class="panel" aria-label="Independent Google reviewer sign-in">
    <h2>Reviewer Google sign-in</h2>
    <div id="google-signin"></div>
    <p class="status" id="identity-status" role="status">Preparing Google sign-in…</p>
    <button id="signout" type="button" class="hide">Sign out</button>
  </section>
  <section id="review" class="panel hide" aria-label="Archived evidence review">
    <h2>Source-anchored scientific review</h2>
    <p class="muted">Only independently provisioned reviewer accounts can read these records or submit audited observations. No actions here resolve a gate or change a scientific grade.</p>
    <label for="trial">Exact trial ID</label>
    <input id="trial" type="text" maxlength="11" value="NCT02142738" autocomplete="off">
    <button type="button" id="load">Load verified source archive</button>
    <p id="review-status" class="status" role="status"></p>
    <section id="dossier" class="hide">
      <h2>Source records</h2>
      <div id="documents"></div>
      <h2>Eight independent-review questions</h2>
      <p class="muted important">Acceptance criteria are still open. SHA-256 validates archived bytes, not scientific conclusions, source authorship, prospective statistical planning, or reviewer independence.</p>
      <div id="questions"></div>
      <section id="observation" class="panel">
        <h2>Record an audited reviewer observation</h2>
        <p class="muted">Only a qualified allowlisted account can record this statement. It is not approval, adjudication, sign-off, or a PDUFA probability estimate.</p>
        <label for="question">Review question</label>
        <select id="question"></select>
        <label for="source">Archived source document</label>
        <select id="source"></select>
        <label for="decision">Observation type</label>
        <select id="decision">
          <option value="requires_review">Requires further review</option>
          <option value="supports_reconciliation">Supports a reconciliation hypothesis</option>
          <option value="disputes_reconciliation">Disputes a reconciliation hypothesis</option>
        </select>
        <label for="locator">Exact source locator (page, section or table)</label>
        <input id="locator" type="text" maxlength="200" placeholder="For example, page 29, Table 3">
        <label for="review-note">Finding, methods and unresolved limitations</label>
        <textarea id="review-note" maxlength="1500" placeholder="Explain the result and the conditions under which it is reliable."></textarea>
        <p><label><input id="uncertainty" type="checkbox"> I have disclosed the limitations and uncertainty of this observation.</label></p>
        <button id="submit-observation" type="button">Submit audited observation (not sign-off)</button>
        <p id="submission-status" class="status" role="status"></p>
      </section>
    </section>
  </section>
  <p class="foot">Operator workspace: <a href="/scientific/operator">Scientific Assessment</a>. This portal does not support reviewer self-registration, automatic credential verification, final decisions, score changes or trading orders.</p>
</main>
<div id="configuration" data-google-client-id="__CLIENT_ID__" hidden></div>
<script nonce="__NONCE__">
(function(){
  "use strict";
  var config=document.getElementById("configuration");
  var googleId=config.dataset.googleClientId;
  var token=null, currentTrial=null, currentQuestions=[], currentDocuments=[];
  var statusEl=document.getElementById("identity-status");
  var signout=document.getElementById("signout");
  var review=document.getElementById("review");
  var dossier=document.getElementById("dossier");
  var questionSelect=document.getElementById("question");
  var sourceSelect=document.getElementById("source");
  var reviewStatus=document.getElementById("review-status");
  var submissionStatus=document.getElementById("submission-status");

  function textElement(tag,text,cls){
    var item=document.createElement(tag);
    if(text!==undefined)item.textContent=String(text);
    if(cls)item.className=cls;
    return item;
  }
  function clear(){
    token=null; currentTrial=null; currentQuestions=[]; currentDocuments=[];
    review.classList.add("hide"); dossier.classList.add("hide");
    document.getElementById("documents").replaceChildren();
    document.getElementById("questions").replaceChildren();
    questionSelect.replaceChildren(); sourceSelect.replaceChildren();
    document.getElementById("review-note").value="";
    document.getElementById("locator").value="";
    document.getElementById("uncertainty").checked=false;
    signout.classList.add("hide");
    if(window.google && google.accounts && google.accounts.id){
      google.accounts.id.disableAutoSelect();
    }
  }
  async function authorizedRequest(path,opts){
    if(!token)throw Error("Sign in with the separately approved Google reviewer account");
    var settings=Object.assign({method:"GET",credentials:"omit",cache:"no-store"},opts||{});
    settings.headers=Object.assign({"Authorization":"Bearer "+token,"Accept":"application/json"},settings.headers||{});
    var response=await fetch(path,settings);
    if(response.status===401||response.status===403){
      clear();
      throw Error("Google reviewer identity is unapproved or the session expired ("+response.status+")");
    }
    if(!response.ok)throw Error("Review service returned HTTP "+response.status);
    return response;
  }
  async function onCredential(payload){
    clear();
    if(!payload||!payload.credential){statusEl.textContent="Google sign-in did not provide an ID token.";return;}
    token=payload.credential;
    statusEl.textContent="Checking the separate Google identity and reviewer credential status…";
    try{
      var response=await authorizedRequest("/api/scientific-assessment/reviewer/onboarding-status");
      var data=await response.json();
      if(data.identityVerified!==true||data.separateGoogleIdentity!==true
          ||data.maySignOff!==false||data.independentScientificAdjudicationImplemented!==false){
        throw Error("Reviewer identity policy failed validation");
      }
      if(data.roleAuthorized!==true||data.credentialsVerified!==true){
        statusEl.textContent="Google identity confirmed, but reviewer access has NOT been provisioned. An administrator must validate the reviewer identity and qualifications and enable their role. No self-registration or review access is granted.";
        token=null; return;
      }
      var permission=await (await authorizedRequest("/api/scientific-assessment/reviewer/me")).json();
      if(permission.roleAuthorized!==true||permission.credentialsVerified!==true
          ||permission.maySignOff!==false)throw Error("Reviewer credential policy failed");
      statusEl.textContent="Separate Google reviewer identity accepted. Audited observations enabled; independent scientific sign-off remains unavailable.";
      review.classList.remove("hide"); signout.classList.remove("hide");
      document.getElementById("load").click();
    }catch(error){
      clear();
      statusEl.textContent=String(error.message||error);
    }
  }
  signout.addEventListener("click",function(){
    clear();
    statusEl.textContent="Signed out. No reviewer token has been persisted.";
  });
  function populateSources(){
    sourceSelect.replaceChildren();
    var check=currentQuestions.find(function(item){return item.id===questionSelect.value;});
    if(!check)return;
    currentDocuments.forEach(function(doc){
      if((check.sourceUrls||[]).indexOf(doc.sourceUrl)===-1)return;
      var option=textElement("option",(doc.gateId||"source")+" · "+doc.documentId.slice(0,8)+
        " · "+doc.byteLength+" bytes");
      option.value=doc.sha256;
      sourceSelect.appendChild(option);
    });
    if(!sourceSelect.options.length){
      var placeholder=textElement("option","No archived PDF linked to this question");
      placeholder.value=""; sourceSelect.appendChild(placeholder);
    }
  }
  questionSelect.addEventListener("change",populateSources);
  async function downloadPdf(documentInfo){
    try{
      if(!currentTrial)throw Error("Load an exact trial first");
      submissionStatus.textContent="Retrieving hash-checked original PDF…";
      var response=await authorizedRequest("/api/scientific-assessment/reviewer/source-documents/"+
        encodeURIComponent(currentTrial)+"/"+encodeURIComponent(documentInfo.documentId));
      var bytes=new Uint8Array(await response.arrayBuffer());
      var digest=Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",bytes)))
        .map(function(b){return b.toString(16).padStart(2,"0");}).join("");
      if(digest!==documentInfo.sha256 ||
         digest!==response.headers.get("X-Source-Document-SHA256")){
        throw Error("PDF checksum did not match archived source manifest");
      }
      var url=URL.createObjectURL(new Blob([bytes],{type:"application/pdf"}));
      var a=textElement("a");a.href=url;a.download=currentTrial+"_"+documentInfo.documentId+".pdf";
      document.body.appendChild(a);a.click();a.remove();
      setTimeout(function(){URL.revokeObjectURL(url);},1000);
      submissionStatus.textContent="PDF bytes verified and downloaded; scientific content remains unverified.";
    }catch(error){submissionStatus.textContent=String(error.message||error);}
  }
  document.getElementById("load").addEventListener("click",async function(){
    if(!token)return;
    var id=document.getElementById("trial").value.trim().toUpperCase();
    if(!/^NCT[0-9]{8}$/.test(id)){reviewStatus.textContent="Exact NCT######## required";return;}
    currentTrial=null;currentQuestions=[];currentDocuments=[];
    dossier.classList.add("hide");reviewStatus.textContent="Inspecting archived science and PDF SHA-256 integrity…";
    try{
      var packet=await (await authorizedRequest("/api/scientific-assessment/reviewer/packet/"+id)).json();
      if(packet.nctId!==id || packet.scientificallyVerified!==false ||
         packet.readyForFullScientificConclusion!==false ||
         packet.fdaApprovalProbability!==null || packet.tradingEnabled!==false ||
         !packet.reconciliation || packet.reconciliation.independentlyResolvedCount!==0){
        throw Error("Review packet failed the unresolved-science contract");
      }
      var checks=packet.reconciliation.checks;
      var docs=packet.independentSourceLedger?.capturedSourceDocuments?.documents;
      if(!Array.isArray(checks)||!Array.isArray(docs))throw Error("Source review archive metadata missing");
      currentTrial=id;currentQuestions=checks;currentDocuments=docs;
      var documentArea=document.getElementById("documents");documentArea.replaceChildren();
      docs.forEach(function(item){
        if(!/^[a-f0-9]{32}$/.test(item.documentId)||!/^[a-f0-9]{64}$/.test(item.sha256)){
          throw Error("Invalid stored source identifiers");
        }
        var container=textElement("div",undefined,"source-row");
        container.appendChild(textElement("div",(item.sourceType||item.gateId)+
          " · "+item.byteLength+" bytes · unverified scientific content"));
        container.appendChild(textElement("div","SHA-256 "+item.sha256,"muted"));
        var download=textElement("button","Download original PDF and verify hash");
        download.type="button";
        download.addEventListener("click",function(){downloadPdf(item);});
        container.appendChild(download);documentArea.appendChild(container);
      });
      if(docs.length===0)documentArea.appendChild(textElement("p","No original PDFs archived.","muted"));
      var questionArea=document.getElementById("questions");questionArea.replaceChildren();
      questionSelect.replaceChildren();
      checks.forEach(function(check,i){
        if(check.resolved!==false||check.criteriaSatisfied!==0)throw Error("Review question unexpectedly adjudicated");
        var details=textElement("details");
        details.appendChild(textElement("summary",(i+1)+". "+check.title+" · OPEN"));
        details.appendChild(textElement("p",check.question||"Requires independent original-source review"));
        var list=textElement("ul");
        (check.resolutionCriteria||[]).forEach(function(rule){
          list.appendChild(textElement("li",rule));
        });
        details.appendChild(list);questionArea.appendChild(details);
        var option=textElement("option",check.title);option.value=check.id;
        questionSelect.appendChild(option);
      });
      populateSources();
      dossier.classList.remove("hide");
      reviewStatus.textContent=checks.length+" evidence questions open · "+docs.length+
        " PDFs archived · 0 independent evidence gates resolved. No scores or signoff.";
    }catch(error){
      currentTrial=null;currentQuestions=[];currentDocuments=[];
      dossier.classList.add("hide");reviewStatus.textContent=String(error.message||error);
    }
  });
  document.getElementById("submit-observation").addEventListener("click",async function(){
    if(!token||!currentTrial)return;
    var sha=sourceSelect.value,questionId=questionSelect.value;
    var locator=document.getElementById("locator").value.trim();
    var note=document.getElementById("review-note").value.trim();
    if(!/^[a-f0-9]{64}$/.test(sha)||!questionId||!locator||!note){
      submissionStatus.textContent="Choose a source linked to this question and enter a page/section and observation.";return;
    }
    if(!document.getElementById("uncertainty").checked){
      submissionStatus.textContent="Acknowledge uncertainty before submitting a reviewer statement.";return;
    }
    var button=document.getElementById("submit-observation");button.disabled=true;
    submissionStatus.textContent="Submitting a traceable reviewer statement, not scientific approval…";
    try{
      var body={
        nctId:currentTrial,questionId:questionId,sourceSha256:sha,
        decision:document.getElementById("decision").value,sourceLocator:locator,
        reviewNote:note,uncertaintyDisclosed:true
      };
      var response=await authorizedRequest("/api/scientific-assessment/reviewer/submissions",{
        method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)
      });
      var receipt=await response.json();
      if(receipt.auditRecorded!==true || receipt.adjudicated!==false ||
         receipt.sourceContentIndependentlyVerified!==false ||
         receipt.mayPromoteReadiness!==false||receipt.scientificScore!==null){
        throw Error("Reviewer statement receipt cannot be accepted as scientific sign-off");
      }
      submissionStatus.textContent="Audited source-review statement recorded. Scientific adjudication remains open.";
      document.getElementById("review-note").value="";
      document.getElementById("locator").value="";
      document.getElementById("uncertainty").checked=false;
    }catch(error){submissionStatus.textContent=String(error.message||error);}
    finally{button.disabled=false;}
  });
  window.addEventListener("load",function(){
    if(!window.google||!google.accounts||!google.accounts.id){
      statusEl.textContent="Google Identity Services could not load. Check OAuth client authorized JavaScript origin.";return;
    }
    google.accounts.id.initialize({client_id:googleId,callback:onCredential,auto_select:false});
    google.accounts.id.renderButton(document.getElementById("google-signin"),
      {theme:"outline",size:"large",text:"signin_with"});
    statusEl.textContent="Sign in using the separately provisioned reviewer Google account.";
  });
})();
</script>
</body>
</html>'''


def reviewer_html(client_id: str, nonce: str) -> str:
    if not client_id or not nonce:
        raise ValueError("Reviewer Google client configuration and CSP nonce required")
    return (_PAGE.replace("__NONCE__", escape(nonce, quote=True))
                 .replace("__CLIENT_ID__", escape(client_id, quote=True)))
