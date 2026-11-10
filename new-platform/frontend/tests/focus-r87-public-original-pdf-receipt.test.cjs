"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const crypto=require("node:crypto");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(mod,file)=>{
 const x=ts.transpileModule(fs.readFileSync(file,"utf8"),{
  compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
   jsx:ts.JsxEmit.ReactJS,esModuleInterop:true}});
 mod._compile(x.outputText,file);
};
const {R86_ORIGINAL_DOCUMENT_MANIFEST,inspectR86CurrentStudy}=
 require("../lib/focus-r86-original-document-inventory.ts");
const {selectR87PublicSourcePdf,digestR87PublicPdf,R87_MAX_SOURCE_PDF_BYTES}=
 require("../lib/focus-r87-public-original-pdf-receipt.ts");
const original=Buffer.from("%PDF-1.7\nmock source bytes; not a valid signed original\n","utf8");
function inventory(){
 const row=R86_ORIGINAL_DOCUMENT_MANIFEST.rows.find(r=>r.nct==="NCT06331299");
 assert.ok(row);
 const body={protocolSection:{identificationModule:{nctId:row.nct}},
  hasResults:false,documentSection:{largeDocumentModule:{largeDocs:[
   {typeAbbrev:"Prot",filename:"Prot_000.pdf",label:"Source protocol",
    date:"2025-08-06",uploadDate:"2026-09-01T15:17",
    size:original.length,hasProtocol:true,hasSap:false,hasIcf:false},
   {typeAbbrev:"ICF",filename:"ICF_000.pdf",date:"2025-08-06",
    size:original.length,hasIcf:true,hasSap:false,hasProtocol:false}
  ]}}};
 const result=inspectR86CurrentStudy(row,body);assert.ok(result);return result;
}
test("R87 selects only a whitelisted protocol or SAP PDF from official same-NCT inventory",()=>{
 const source=inventory();
 const s=selectR87PublicSourcePdf("NCT06331299","Prot_000.pdf",source);
 assert.ok(s);
 assert.equal(s.publicCdnUrl,
  "https://cdn.clinicaltrials.gov/large-docs/99/NCT06331299/Prot_000.pdf");
 assert.equal(s.registryReportedSize,original.length);
 assert.equal(s.registryUploadDate,"2026-09-01T15:17");
 assert.equal(s.originalClinicalSourceAuthenticated,false);
 assert.equal(s.FDAForecast,"ABSTAIN");
 assert.equal(selectR87PublicSourcePdf("NCT00000000","Prot_000.pdf",source),null);
 assert.equal(selectR87PublicSourcePdf("NCT06331299","ICF_000.pdf",source),null);
 assert.equal(selectR87PublicSourcePdf("NCT06331299","../Prot_000.pdf",source),null);
 assert.equal(selectR87PublicSourcePdf("NCT06331299","Prot_000.pdf?x=1",source),null);
 assert.equal(selectR87PublicSourcePdf("NCT06331299","Nope.pdf",source),null);
});
test("R87 hashes EXACT published bytes but never attests original signing",()=>{
 const selected=selectR87PublicSourcePdf("NCT06331299","Prot_000.pdf",inventory());
 assert.ok(selected);
 const d=digestR87PublicPdf(selected,original);
 assert.ok(d);
 assert.equal(d.pdfByteLength,original.byteLength);
 assert.equal(d.sha256,crypto.createHash("sha256").update(original).digest("hex"));
 assert.equal(d.publiclyHostedPdfBytesRead,true);
 assert.equal(d.originalSignedSapChronologyVerified,false);
 assert.equal(d.independentHumanReviewSigned,false);
 assert.equal(d.originalClinicalSourceAuthenticated,false);
 assert.equal(d.FDAForecast,"ABSTAIN");
});
test("R87 rejects incorrect PDF body magic, length and oversized source",()=>{
 const selected=selectR87PublicSourcePdf("NCT06331299","Prot_000.pdf",inventory());
 assert.ok(selected);
 assert.equal(digestR87PublicPdf(selected,Buffer.from("not-a-pdf".padEnd(original.length))),null);
 assert.equal(digestR87PublicPdf(selected,Buffer.from("%PDF-1.7")),null);
 const huge={...selected,registryReportedSize:R87_MAX_SOURCE_PDF_BYTES+1};
 assert.equal(digestR87PublicPdf(huge,original),null);
});
test("R87 public-source route rejects unknown NCT/filename and revalidates registry",()=>{
 const route=fs.readFileSync(path.join(root,
  "app/predictions/original-documents/checksum/route.ts"),"utf8");
 const client=fs.readFileSync(path.join(root,
  "app/predictions/original-documents/OriginalSourceDocumentsR86Client.tsx"),"utf8");
 assert.match(route,/NCT_OUTSIDE_LOCKED_FOCUS_ROSTER/);
 assert.match(route,/selectR87PublicSourcePdf/);
 assert.match(route,/digestR87PublicPdf/);
 assert.match(route,/redirect:"error"/);
 assert.match(route,/AbortSignal\.timeout/);
 assert.match(route,/PDF_DECLARED_BYTE_LENGTH_MISMATCH/);
 assert.match(route,/no-store/);
 assert.match(client,/hashPublicOriginal/);
 assert.match(client,/Public source byte SHA-256/);
 assert.match(client,/remain unverified/);
 assert.doesNotMatch(route,/method:"POST"|submitClinicalScore|setGrade\(/);
});
