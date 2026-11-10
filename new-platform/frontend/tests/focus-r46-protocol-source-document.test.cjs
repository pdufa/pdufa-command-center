"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),
 fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>{
 const x=ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
  target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
  jsx:ts.JsxEmit.ReactJS,esModuleInterop:true}});
 mod._compile(x.outputText,file);
};
const pin=require("../data/focus-r46-current-protocol-document-index.json");
const {FOCUS_R46_DOCUMENTS,validateR46CurrentDocuments}=require("../lib/focus-r46-current-protocol-documents.ts");
const clone=x=>structuredClone(x);

test("R46 exact original document receipt keeps 29/23 and 12 trials/23 source files",()=>{
 const p=FOCUS_R46_DOCUMENTS;
 assert.ok(p);
 assert.equal(p.rows.length,29);
 assert.equal(p.rows.filter(t=>t.attachments!==null).length,12);
 assert.equal(p.rows.filter(t=>t.attachments===null).length,17);
 assert.equal(p.rows.flatMap(t=>t.attachments||[]).length,23);
 assert.equal(p.counts.provisionalApplications,23);
 assert.equal(p.originalResearchReceiptSha256,"05e7dbe734795018503e7b3751ff1b0b93fa34311ba5183d6c96ab9f0cac0614");
 assert.equal(p.counts.independentlyVerifiedLockedSap,0);
 assert.equal(p.counts.qualifiedIndependentScientificGrades,0);
 assert.equal(p.counts.independentlyValidatedFdaForecasts,0);
 assert.equal(p.originalFirstPublicDocumentDateVerified,false);
 assert.equal(p.officialFutureFdaPrediction,"ABSTAIN");
 assert.equal(p.numericalFdaProbability,null);
});
test("priority CAPR and COGT lack current attached SAP, SVRA has both",()=>{
 const p=FOCUS_R46_DOCUMENTS;
 assert.equal(p.rows.find(t=>t.nct==="NCT05126758").attachments,null);
 assert.equal(p.rows.find(t=>t.nct==="NCT05208047").attachments,null);
 const s=p.rows.find(t=>t.nct==="NCT04544293");
 assert.equal(s.attachments.length,2);
 assert.ok(s.attachments.some(x=>x.kind==="SAP"));
 assert.equal(s.lockedSapVerified,false);
});
test("combined protocol/SAP attachment is supported but not validated",()=>{
 const p=FOCUS_R46_DOCUMENTS;
 const r=p.rows.find(t=>t.nct==="NCT04716231");
 assert.equal(r.attachments.length,1);
 assert.equal(r.attachments[0].kind,"Prot_SAP");
 assert.equal(r.firstPublicationVerified,false);
});
test("receipt, member, publication date, forged clinical grade and prediction refuse validation",()=>{
 const changes=[
  v=>v.originalResearchReceiptSha256="0".repeat(64),
  v=>v.sourceArtifactId=0,
  v=>v.counts.documentEntries=22,
  v=>v.counts.provisionalApplications=22,
  v=>v.originalLockedSapAndMultiplicityVerified=true,
  v=>v.documentBodiesReviewed=true,
  v=>v.counts.independentlyVerifiedLockedSap=1,
  v=>v.clinicalReviewerSigned=true,
  v=>v.officialFutureFdaPrediction="APPROVAL",
  v=>v.numericalFdaProbability=.9,
  v=>v.attached[0].nct="NCT99999999",
  v=>v.attached[1].nct=v.attached[0].nct,
  v=>v.attached[0].documents[0].filename="../../bad.pdf",
  v=>v.attached[0].documents[0].registryDocumentDate="after approval",
  v=>v.attached[0].documents.pop()
 ];
 changes.forEach((change,i)=>{
  const copy=clone(pin);change(copy);
  assert.equal(validateR46CurrentDocuments(copy),null,"tamper "+i);
 });
});
test("R46 PREDICTIONS UI displays current document inventory without medical writes",()=>{
 const page=fs.readFileSync(path.join(root,"app/predictions/page.tsx"),"utf8");
 const ui=fs.readFileSync(path.join(root,"app/predictions/FocusProtocolDocumentIndexR46.tsx"),"utf8");
 assert.ok(page.includes("<FocusProtocolDocumentIndexR46/>"));
 assert.match(ui,/Original locked version unverified/);
 assert.match(ui,/document dates/);
 assert.match(ui,/All future official/);
 assert.doesNotMatch(ui,/fetch\(|submitClinicalGrade|POST\s*\/api/);
});
