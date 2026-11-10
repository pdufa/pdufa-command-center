"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>{
 const t=ts.transpileModule(fs.readFileSync(file,"utf8"),{
  compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
   jsx:ts.JsxEmit.ReactJS,esModuleInterop:true}});
 mod._compile(t.outputText,file);
};
const source=require("../data/focus-r70-abstract-publication-triage.json");
const {buildR70PublicationAbstractTriage,FOCUS_R70_PUBLICATION_TRIAGE}=
 require("../lib/focus-r70-publication-abstract-triage.ts");

test("R70 11 exact R69 publication candidates classified by abstract role, never clinical score",()=>{
 const x=FOCUS_R70_PUBLICATION_TRIAGE;
 assert.ok(x,"original R69 11 PMID source membership must validate");
 assert.equal(x.schema,"MAIN_R70_PUBLICATION_ABSTRACT_SOURCE_ROLE_NOT_SIGNED_SCIENCE");
 assert.equal(x.paperCount,11);
 assert.equal(x.exactNctReferences,7);
 assert.equal(x.abstractPrimaryReportCandidates,5);
 assert.equal(x.uniqueTrialsWithPrimaryReportCandidates,5);
 assert.equal(x.additionalSameTrialAnalyses,2);
 assert.equal(x.protocolPapers,1);
 assert.equal(x.phase2NotPhase3,1);
 assert.equal(x.earlierPhaseOtherCohort,1);
 assert.equal(x.backgroundNotPivotal,1);
 assert.equal(x.originalMissingPrimaryTrialCount,17);
 assert.equal(x.papers.length,11);
 assert.equal(new Set(x.papers.map(p=>p.pmid)).size,11);
 assert.equal(x.scienceScoresAssigned,0);
 assert.equal(x.signedScientificReviews,0);
 assert.equal(x.independentlyValidatedFDAForecasts,0);
 assert.equal(x.measuredForecastAccuracy,null);
 assert.equal(x.officialFutureFDAOutcome,"ABSTAIN");
 assert.equal(x.fullOriginalScientificStatisticalReviewCompleted,false);
 assert.equal(x.trialResultNotScoredOrCountedMultipleTimes,true);
 assert.equal(x.noProductionWritesOrModelTraining,true);
 assert.ok(x.papers.every(p=>p.evidenceBasis==="PUBMED_JOURNAL_TITLE_ABSTRACT_ONLY"&&
  p.articleFullTextMethodsIndependentlyAdjudicated===false&&
  p.originalPreunblindingSAPVerified===false&&p.qualifiedReviewerSigned===false&&
  p.scientificGrade===null&&p.officialFdaPrediction==="ABSTAIN"&&
  p.studyPrimaryDataFullyValidated===false));
});

test("The main ACACIA report counts once, two related analyses cannot be additional pivotal studies",()=>{
 const r=FOCUS_R70_PUBLICATION_TRIAGE;
 const acacia=r.papers.filter(x=>x.nct==="NCT06081894");
 assert.equal(acacia.length,3);
 assert.equal(acacia.filter(x=>x.potentialPivotalPrimaryResultFromAbstract).length,1);
 assert.equal(acacia.find(x=>x.pmid==="42663312").role,"PRIMARY_PHASE3_ABSTRACT");
 assert.deepEqual(new Set(acacia.filter(x=>x.role==="SAME_TRIAL_SECONDARY_ANALYSIS").map(x=>x.pmid)),
  new Set(["42667274","42663111"]));
});

test("RINGSIDE Phase 2, ESSENCE earlier phase and normative background cannot count as Phase 3 primary",()=>{
 const by=new Map(FOCUS_R70_PUBLICATION_TRIAGE.papers.map(x=>[x.pmid,x]));
 for(const [pmid,role] of [
   ["42848980","PHASE2_COMPONENT_NOT_PHASE3"],
   ["34105177","EARLIER_PHASE_OTHER_COHORT"],
   ["40098309","BACKGROUND_NOT_PIVOTAL"],
   ["41840328","PROTOCOL_ONLY"]
 ]){
   assert.equal(by.get(pmid).role,role);
   assert.equal(by.get(pmid).potentialPivotalPrimaryResultFromAbstract,false);
 }
 assert.deepEqual([...FOCUS_R70_PUBLICATION_TRIAGE.papers
   .filter(x=>x.potentialPivotalPrimaryResultFromAbstract)
   .map(x=>x.nct)].sort(),
   ["NCT05126758","NCT05662241","NCT06081894",
    "NCT06153693","NCT06343779"]);
});

test("Manual or injected source falsification never becomes a published approval probability",()=>{
 const altered=[
  x=>x.rows.push(x.rows[0]),
  x=>x.rows.pop(),
  x=>x.rows[0][1]="99999999",
  x=>x.rows[2][2]="PRIMARY_PHASE3_ABSTRACT",
  x=>x.rows[1][2]="PRIMARY_PHASE3_ABSTRACT",
  x=>x.rows[0][0]="NCT99999999",
  x=>x.rows[0][3]="",
  x=>x.basedOnR69Sha256="0".repeat(64),
  x=>x.fdaOutcomeForecast="APPROVE",
  x=>x.qualifiedReviewerSigned=true,
  x=>x.externalFullTextStatisticalReviewComplete=true,
  x=>x.independentlyVerifiedOriginalSignedProtocolSAP=true,
  x=>x.validatedOutcomes=5
 ];
 for(let i=0;i<altered.length;i++){
  const c=structuredClone(source);
  altered[i](c);
  assert.equal(buildR70PublicationAbstractTriage(c),null,
   "fabricated R70 source property "+i+" must fail closed");
 }
});

test("The source recovery page includes R70 article-level roles but not FDA forecast release",()=>{
 const read=s=>fs.readFileSync(path.join(root,s),"utf8");
 const board=read("app/predictions/evidence-gaps/EvidenceRecoveryBoardR68.tsx");
 const old=read("app/predictions/evidence-gaps/OriginalPublicationLeadsR69.tsx");
 const panel=read("app/predictions/evidence-gaps/PublicationEvidenceRoleR70.tsx");
 const css=read("app/predictions/evidence-gaps/PublicationEvidenceRoleR70.module.css");
 assert.match(board,/FOCUS_R70_PUBLICATION_TRIAGE/);
 assert.match(old,/PublicationEvidenceRoleR70/);
 assert.match(panel,/title and abstract/);
 assert.match(panel,/Full original methods/);
 assert.match(panel,/ABSTAIN/);
 assert.match(panel,/Signed grades: 0|Independently signed grades: 0/);
 assert.match(css,/@media\(max-width:470px\)/);
 assert.doesNotMatch(panel,/fetch\(|POST\s*\/api|signedClinicalSuccess|setGrade/);
});
