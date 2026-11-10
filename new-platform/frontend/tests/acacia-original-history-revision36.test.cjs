"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const crypto=require("node:crypto");
const ts=require("typescript");
const React=require("react");
const {renderToStaticMarkup}=require("react-dom/server");
const data=require("../data/acacia-original-history-revision36.json");
const root=path.resolve(__dirname,"../../..");
const sourceDirectory=path.join(root,data.sourceDirectory);
const readJson=name=>JSON.parse(fs.readFileSync(path.join(sourceDirectory,name),"utf8"));

for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>mod._compile(
  ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
    module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
    jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true
  }}).outputText,file
);

test("displayed original versions match preserved exact NCT, dates, endpoint text and byte hashes",()=>{
  const comparison=readJson("validated_comparison.json");
  const receipt=readJson("public_browser_receipt.json");
  assert.equal(data.nct,"NCT06081894");
  assert.equal(data.protocol,"CY 6033");
  assert.equal(data.accessMethod,"STANDARD_PUBLIC_HISTORY_UI");
  assert.deepEqual(data.versions.map(v=>v.version),[26,27,29,30]);
  assert.deepEqual(data.versions.map(v=>v.primary.length),[1,2,2,2]);
  assert.deepEqual(data.versions.map(v=>v.enrollment.count),[420,500,500,500]);
  for(const version of data.versions){
    const bytes=fs.readFileSync(path.join(sourceDirectory,version.artifact));
    const body=JSON.parse(bytes.toString("utf8"));
    const protocol=body.study.protocolSection;
    const verified=comparison.versionData["v"+version.version];
    const originalReceipt=receipt.versions.find(v=>v.version===version.version);
    assert.equal(crypto.createHash("sha256").update(bytes).digest("hex"),version.sourceSha256);
    assert.equal(version.sourceSha256,verified.sourceSha256);
    assert.equal(version.sourceBytes,bytes.length);
    assert.equal(body.studyVersion,version.apiIndex);
    assert.equal(protocol.identificationModule.nctId,data.nct);
    assert.equal(protocol.identificationModule.orgStudyIdInfo.id,data.protocol);
    assert.equal(version.submitted,protocol.statusModule.lastUpdateSubmitDate);
    assert.equal(version.posted,protocol.statusModule.lastUpdatePostDateStruct.date);
    assert.equal(version.postingType,"ACTUAL");
    assert.equal(version.enrollment.type,"ESTIMATED");
    assert.deepEqual(version.enrollment,protocol.designModule.enrollmentInfo);
    assert.deepEqual(version.primary,protocol.outcomesModule.primaryOutcomes);
    assert.equal(version.secondaryCount,protocol.outcomesModule.secondaryOutcomes.length);
    assert.deepEqual(version.phase,protocol.designModule.phases);
    assert.equal(version.phaseIndependentReviewerVerified,false);
    assert.equal(version.sourceUrl,originalReceipt.sourceUrl);
    assert.equal(version.pageUrl,originalReceipt.pageUrl);
    assert.equal(version.retrievedAt,originalReceipt.retrievedAt);
    assert.equal(originalReceipt.httpStatus,200);
  }
  const indexBytes=fs.readFileSync(path.join(sourceDirectory,data.originalHistoryIndex.artifact));
  assert.equal(crypto.createHash("sha256").update(indexBytes).digest("hex"),data.originalHistoryIndex.sha256);
  assert.equal(data.originalHistoryIndex.sha256,receipt.index.sha256);
  assert.ok(receipt.indexAttempts.some(attempt=>attempt.httpStatus===403));
});

test("enriched source positions retain the existing worklist and all independent grading gates",()=>{
  const pilot=require("../data/acacia-pilot-prediction-workup-20261108.json");
  const existingPositions=pilot.criticalAssessmentEvidence.flatMap(assessment=>
    assessment.candidateMethodIndices.map(method=>assessment.id+":L"+method));
  assert.deepEqual(data.mappedExistingPositions,["4.2:L1","4.4:L1","8.2:L1"]);
  assert.ok(data.mappedExistingPositions.every(id=>existingPositions.includes(id)));
  assert.equal(existingPositions.length,18);
  assert.equal(pilot.scientificFramework.methodPositionsUnexamined,782);
  assert.equal(data.newlyMappedPositions,0);
  assert.equal(data.newlyCompletedScientificMethods,0);
  assert.equal(data.officialClinicalGrades,0);
  assert.equal(data.qualifiedPhaseSignoffs,0);
  assert.deepEqual(Object.values(data.fdaPredictions),["ABSTAIN","ABSTAIN","ABSTAIN"]);
  assert.equal(data.certainty,"NOT_VALIDATED");
  assert.equal(data.accuracy,"NOT_CALIBRATED");
});

test("expandable source panel distinguishes documentary recovery, population gaps and pending review",()=>{
  const Component=require("../app/predictions/assessment/PilotOriginalHistoryEvidence.tsx").default;
  const html=renderToStaticMarkup(React.createElement(Component));
  assert.equal((html.match(/<article /g)||[]).length,4);
  assert.equal((html.match(/<details/g)||[]).length,6);
  assert.match(html,/v26 · 1 primary endpoint/);
  assert.match(html,/v27 · 2 primary endpoints/);
  assert.match(html,/2025-05-15/);
  assert.match(html,/2025-05-20/);
  assert.match(html,/420/);
  assert.match(html,/ESTIMATED/);
  assert.match(html,/do not resolve the reported 516 versus 517/);
  assert.match(html,/final locked SAP/);
  assert.match(html,/independent review before a clinical integrity judgment or grade/);
  assert.match(html,/18 mapped source leads/);
  assert.match(html,/782 positions not source mapped/);
  assert.match(html,/0\/800/);
  assert.match(html,/NOT VALIDATED/);
  assert.match(html,/NOT CALIBRATED/);
  assert.match(html,/overflow-wrap:anywhere/);
  for(const version of data.versions){
    assert.ok(html.includes(version.sourceSha256));
    assert.ok(html.includes(version.sourceUrl));
    assert.ok(html.includes(version.pageUrl.replaceAll("&","&amp;")));
  }
  const queueSource=fs.readFileSync(path.join(__dirname,"../app/predictions/assessment/PilotResearchReviewQueue.tsx"),"utf8");
  assert.match(queueSource,/<PilotOriginalHistoryEvidence\/>/);
  assert.match(queueSource,/if\(nct!=="NCT06081894"\|\|pilot.nct!==nct\)return null/);
});
