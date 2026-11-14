const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const ts=require('typescript');
const React=require('react');
const {renderToStaticMarkup}=require('react-dom/server');
require.extensions['.tsx']=(module,file)=>module._compile(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,file);
const {default:Panel,validScientificLevels}=require('../app/ScientificLevelsEvidence.tsx');
function levels(){return Object.fromEntries([2,3,4,5,6].map(level=>[String(level),{level,name:'Level '+level,status:'AWAITING_REVIEW',criteria:{protocol:'NOT_ASSESSED'},score:null,scientificValidation:'NOT_VERIFIED',fdaPrediction:'ABSTAIN'}]));}
test('all five scientific contracts render missing, unpublished and phase-appropriate states',()=>{
 const data=levels(); data[2].criteria.protocol='UNPUBLISHED'; data[6].criteria.protocol='NOT_YET_EXPECTED';
 const html=renderToStaticMarkup(React.createElement(Panel,{value:data}));
 for(const n of [2,3,4,5,6]) assert.match(html,new RegExp('Level '+n+':'));
 for(const state of ['UNPUBLISHED','NOT_YET_EXPECTED','NOT_ASSESSED','ABSTAIN','NOT_VALIDATED']) assert.ok(html.includes(state));
});
test('malformed provenance and false scientific predictions fail closed',()=>{
 for(const mutate of [d=>{d[2].score=100;},d=>{d[3].fdaPrediction='APPROVAL';},d=>{d[4].acceptedEvidence={safety:{reviewerId:{forged:true}}};},d=>{d[5].registryEvidenceInventory={population:{state:'OBSERVED',provenance:[]}};}]){
  const data=levels();mutate(data);assert.equal(validScientificLevels(data),false);
  assert.match(renderToStaticMarkup(React.createElement(Panel,{value:data})),/unavailable or not verified/);
 }
});
test('collected metadata shows receipt without manufacturing a reviewer',()=>{
 const data=levels(); data[2].registryEvidenceInventory={protocol:{state:'AVAILABLE_NOT_REVIEWED',observation:'registered design',provenance:{source:'https://clinicaltrials.gov/study/NCT04576949',sourceDate:'2026-01-15',retrievedAt:'2026-11-14T09:00:00Z',documentType:'SAVED_REGISTRY_SUMMARY',inputSha256:'a'.repeat(64)}}};
 const html=renderToStaticMarkup(React.createElement(Panel,{value:data}));
 assert.match(html,/AVAILABLE_NOT_REVIEWED/);assert.match(html,/NCT04576949/);assert.match(html,/2026-11-14T09:00:00Z/);assert.doesNotMatch(html,/Reviewer/);
});
test('descriptive arithmetic stays distinct from scientific score and FDA probability',()=>{
 const data=levels();data[3].criteria={effectSizeAndPrecision:'INCONCLUSIVE'};
 data[3].descriptiveCalculations={effectSizeAndPrecision:{status:'DESCRIPTIVE_CALCULATION_NOT_VALIDATED_ASSESSMENT',absoluteRiskDifference:0.1,riskRatio:2,scientificValidation:'NOT_VERIFIED',fdaPrediction:'ABSTAIN'}};
 const html=renderToStaticMarkup(React.createElement(Panel,{value:data}));
 assert.match(html,/10.00/);assert.match(html,/2.000/);assert.match(html,/No confidence interval or clinical significance inferred/);assert.match(html,/not an FDA probability/);
});
test('development branch cannot trigger automatic Vercel deployment',()=>{
 const config=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../vercel.json'),'utf8'));
 assert.equal(config.git.deploymentEnabled['codex/level1-6-explicit-scientific-readiness-20261114'],false);
 assert.equal(config.crons.length,2);
});
