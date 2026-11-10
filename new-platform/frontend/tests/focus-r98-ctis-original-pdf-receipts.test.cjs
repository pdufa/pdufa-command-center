"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(mod,file)=>{
 const t=ts.transpileModule(fs.readFileSync(file,"utf8"),{
  compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,esModuleInterop:true,jsx:ts.JsxEmit.ReactJS}});
 mod._compile(t.outputText,file);
};
const receipt=require("../data/focus-r98-ctis-original-pdf-byte-receipts-20261110.json");
const {R98_ACACIA_CTIS_ORIGINAL_PDF_RECEIPTS,buildR98AcaciaOriginalPdfReceipts}=
 require("../lib/focus-r98-ctis-original-pdf-receipts.ts");
test("R98 four exact source byte receipts are bound to CY6033 original CTIS identity and unchanged signed-science gate",()=>{
 const x=R98_ACACIA_CTIS_ORIGINAL_PDF_RECEIPTS;
 assert.ok(x);
 assert.equal(x.nct,"NCT06081894");
 assert.equal(x.euct,"2023-505797-15-00");
 assert.equal(x.protocol,"CY 6033");
 assert.equal(x.originalPdfFilesAvailable,4);
 assert.equal(x.originalTotalBytesSourceVerified,1729556);
 assert.equal(x.originalPdfFilesPermanentlyArchived,0);
 assert.equal(x.originalDocumentsScientificallyPageReviewed,0);
 assert.equal(x.finalProspectiveSapSignaturesAuthenticated,0);
 assert.equal(x.independentScienceSignoffs,0);
 assert.equal(x.ACACIAOriginalGatesUnresolved,4);
 assert.equal(x.launchOriginalGatesUnresolved,7);
 assert.equal(x.FDAForecast,"ABSTAIN");
 assert.deepEqual(x.originalDocuments.map(x=>x.key),[
  "am4-protocol","am4-protocol-greek","am3-synopsis","protocol-addendum-a"]);
 assert.ok(x.originalDocuments.every(x=>
  /^[a-f0-9]{64}$/u.test(x.sha256)&&
  x.originalSourceUrl.startsWith("https://euclinicaltrials.eu/ctis-public-api/documents/2023-505797-15-00/")&&
  x.originalTextReviewed===false&&x.independentSignedApproval===false));
});
test("R98 rejects faked original signed SAP, byte hash, source hostname, archive, and source count",()=>{
 const edits=[
  r=>{r.sponsorProtocol="CY 6032";},
  r=>{r.nct="NCT00000000";},
  r=>{r.originalReadbacksSucceeded=3;},
  r=>{r.originalPublicPdfFileBytesRetrievedInPreview=999;},
  r=>{r.exactDocuments[0].originalPdfSha256="0".repeat(64);},
  r=>{r.exactDocuments[0].ctisUUID=r.exactDocuments[1].ctisUUID;},
  r=>{r.exactDocuments[0].originalDocumentUrl="https://wrong.example/protocol.pdf";},
  r=>{r.exactDocuments[0].originalPdfPageTextInspected=true;},
  r=>{r.exactDocuments[0].preUnblindingAuthorizationVerified=true;},
  r=>{r.exactDocuments[0].documentSignatureCryptographicallyAuthenticated=true;},
  r=>{r.exactDocuments[0].verifiedPdfHeader=false;},
  r=>{r.exactDocuments[0].archiveStatus="DURABLY_ARCHIVED";},
  r=>{r.sourceBytesPersistedInRepository=true;},
  r=>{r.sourcePdfTextExtractedAndReviewed=true;},
  r=>{r.trueSignatureOfFinalSAPAuthenticated=true;},
  r=>{r.qualifiedScienceReviewsSigned=1;},
  r=>{r.FDAForecast="APPROVED";},
  r=>{r.exactDocuments.pop();}
 ];
 for(const edit of edits){
  const r=structuredClone(receipt);
  edit(r);
  assert.equal(buildR98AcaciaOriginalPdfReceipts(r),null);
 }
});
test("R98 dashboard labels source byte receipts accurately and does not confer independent medical approval",()=>{
 const page=fs.readFileSync(path.join(root,
  "app/predictions/scientific-reconciliation/priority-gates/page.tsx"),"utf8");
 assert.match(page,/R98_ACACIA_CTIS_ORIGINAL_PDF_RECEIPTS/);
 assert.match(page,/4 byte-verified source receipts/);
 assert.match(page,/permanently archived/);
 assert.match(page,/NOT COMPLETED/);
 assert.match(page,/Signed prospective SAP: NOT VERIFIED/);
 assert.match(page,/FDA forecast: ABSTAIN/);
});
