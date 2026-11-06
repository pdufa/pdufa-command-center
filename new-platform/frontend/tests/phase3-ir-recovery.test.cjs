const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const ts=require('typescript');
require.extensions['.ts']=(mod,file)=>mod._compile(ts.transpileModule(fs.readFileSync(file,'utf8'),{
 compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}
}).outputText,file);
const audit=require('../app/api/phase3-missing-data-audit/route.ts');
const csvRoute=require('../app/api/phase3-unified-190-columns/route.ts');
const ir=require('../data/phase3CompanyWebsiteEvidence20261105.json');
const endpoints=require('../data/phase3EndpointAdjudications20261105.json');
const ledger=require('../public/phase3-unified-classifications-2026-11-05.json');
const research=require('../lib/phase3-ir-research.ts');
function parseCsv(text){
 const rows=[];let row=[],cell='',quoted=false;
 for(let i=0;i<text.length;i++){
  const c=text[i];if(i===0&&c==='\uFEFF')continue;
  if(c==='"'){if(quoted&&text[i+1]==='"'){cell+='"';i++;}else quoted=!quoted;}
  else if(c===','&&!quoted){row.push(cell);cell='';}
  else if(c==='\n'&&!quoted){row.push(cell.replace(/\r$/,''));rows.push(row);row=[];cell='';}
  else cell+=c;
 }
 return rows;
}
test('actual audit and 190-column CSV reconcile all 762 identities and all 30 questions',async()=>{
 const response=await audit.GET(new Request('http://local/api/audit'));
 assert.equal(response.status,200);const report=await response.json();
 const csv=await csvRoute.GET(new Request('http://local/api/export'));
 assert.equal(csv.status,200);const rows=parseCsv(await csv.text());
 assert.equal(rows.length,763);assert.ok(rows.every(r=>r.length===190));
 assert.deepEqual(new Set(rows.slice(1).map(r=>r[0])),new Set(ledger.rows.map(r=>r.nctId)));
 const sums={predicted:0,observed:0,sourceFacts:0,unscored:0};
 for(let i=0;i<30;i++){
  const statuses=rows.slice(1).map(r=>r[40+i*5]);
  const expected={predicted:statuses.filter(s=>s==='PREDICTED_PRE_READOUT').length,
   observed:statuses.filter(research.isObservedStatus).length,
   sourceFacts:statuses.filter(research.isSourceFactStatus).length,
   unscored:statuses.filter(s=>research.requiresResearchStatus(s)||s==='NOT_PUBLICLY_DISCLOSED').length};
  const q=report.perQuestion[i];
  assert.deepEqual(expected,{predicted:q.predictions,observed:q.observed,sourceFacts:q.sourceFacts,unscored:q.unscored});
  for(const key in sums)sums[key]+=expected[key];
  assert.equal(Object.values(expected).reduce((a,b)=>a+b),762);
  assert.equal(q.notPubliclyAvailable,0);
 }
 for(const key in sums)assert.equal(report.assessment[key],sums[key]);
 assert.equal(report.assessment.predicted,61);assert.equal(report.assessment.trialsWithNumericalPredictions,4);
 assert.deepEqual(report.endpointOutcomes,{PRIMARY_ENDPOINT_MET:46,PRIMARY_ENDPOINT_NOT_MET:8,NO_BINARY_PASS_FAIL:3});
 assert.equal(report.fields.missingAdjudicatedEndpoint,705);
 assert.equal(report.fields.investorRelationsRegulatoryTrialLinks,20);
 assert.equal(report.fields.investorRelationsFDAApplicationPrograms,11);
 assert.equal(report.fields.unverifiedPDUFADate,753); // approval dates never become goal dates
 const ardelyx=report.investorRelationsCoverage.find(c=>c.ticker==='ARDX');
 assert.equal(ardelyx.matchedTrials,7);assert.equal(ardelyx.trials.length,10);
 assert.equal(ardelyx.trialsRequiringInvestigation,10);
 const t3=rows.find(r=>r[0]==='NCT02621892');
 assert.match(t3[40+16*5+3],/p=0.27/); // secondary failure survives primary success
 const accel=rows.find(r=>r[0]==='NCT07382167');
 assert.equal(accel[40+28*5],'DOCUMENTED_SOURCE_FACT');
 assert.equal(accel[16],'');
 assert.equal(rows.find(r=>r[0]==='NCT02727751')[20],'NON_BINARY_ENDPOINT');
 for(const nct of ['NCT02621892','NCT02686138','NCT03427125','NCT03824587','NCT02675998','NCT02727751','NCT07382167']){
  const r=rows.find(r=>r[0]===nct);
  for(let i=0;i<30;i++){assert.equal(r[40+i*5+1],'');assert.equal(r[40+i*5+2],'');}
 }
});
test('new evidence has unique exact-NCT question keys and explicit dates, scope and correction blockers',()=>{
 assert.ok(research.irResearchIntegrity(new Set(ledger.rows.map(r=>r.nctId))));
 assert.equal(ir.assessmentRecords.filter(r=>r.nctId.startsWith('NCT')&&ir.records.find(t=>t.nctId===r.nctId)?.ticker==='ARDX').length,48);
 assert.equal(ir.assessmentRecords.length,111);
 assert.equal(new Set(endpoints.records.map(r=>r.nctId)).size,endpoints.records.length);
 assert.equal(endpoints.totalReviewed,endpoints.records.length);
 for(const [key,count] of Object.entries(endpoints.counts))assert.equal(count,endpoints.records.filter(r=>r.endpointOutcome===key).length);
 for(const r of ir.assessmentRecords){assert.ok(r.publicationDate&&r.sourceUrl&&r.evidenceScope);assert.equal(r.score,undefined);}
 assert.equal(ir.assessmentRecords.filter(r=>r.classification==='REQUIRES_INTERPRETATION').length,4);
 assert.equal(research.isObservedStatus('DOCUMENTED_SOURCE_FACT'),false);
 assert.equal(research.isSourceFactStatus('REQUIRES_INTERPRETATION'),false);
 assert.equal(research.irResearchIntegrity(new Set(['NCT00000000'])),false);
});

test('BioCryst drug and country distinctions survive efficacy and regulatory overlays',async()=>{
 const response=await csvRoute.GET(new Request('http://local/export'));
 const rows=parseCsv(await response.text());
 const opus=rows.find(r=>r[0]==='NCT02303626'),japan=rows.find(r=>r[0]==='NCT03873116');
 assert.equal(opus[20],'FAIL_DOCUMENTED_PRIMARY_ENDPOINT');
 assert.equal(opus[14],'NOT_VERIFIED');
 assert.equal(japan[14],'NOT_VERIFIED');
 assert.match(japan[21],/specific to 150 mg/);
 const apex=rows.find(r=>r[0]==='NCT03485911');
 assert.equal(apex[14],'FDA_APPROVED_HISTORICAL');
 assert.equal(apex[16],'');
 assert.equal(apex[40+3*5],'DOCUMENTED_SOURCE_FACT');
 for(const nct of ['NCT02303626','NCT03485911','NCT03873116']){
  const r=rows.find(r=>r[0]===nct);
  for(let q=0;q<30;q++){assert.equal(r[40+q*5+1],'');assert.equal(r[40+q*5+2],'');}
 }
});
