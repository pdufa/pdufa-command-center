"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>{
 const output=ts.transpileModule(fs.readFileSync(file,"utf8"),{
  compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
    jsx:ts.JsxEmit.ReactJS,esModuleInterop:true}});
 mod._compile(output.outputText,file);
};
const original=require("../data/focus-r70-verified-pubmed-metadata-source.json");
const {buildR70SourceArticleView,FOCUS_R70_ARTICLE_SOURCE}=
 require("../lib/focus-r70-pubmed-article-source.ts");

test("11 original NLM article records: 8 exact-NCT mentions vs 3 only PubMed databank links",()=>{
 const x=FOCUS_R70_ARTICLE_SOURCE;
 assert.ok(x,"source-locked original R69 and NLM article data must pass");
 assert.equal(x.schema,"MAIN_R70_NLM_ORIGINAL_ARTICLE_METADATA_REVIEW_ONLY");
 assert.equal(x.sourceArchiveRun,42729546458);
 assert.equal(x.sourceArchiveArtifact,13724930108);
 assert.equal(x.originalPubmedRecordsRetrieved,11);
 assert.equal(x.trialsWithListedReferences,7);
 assert.equal(x.primaryMissingCurrentRegistryTrials,17);
 assert.equal(x.originalNctStudyLinkedByPubmedDatabase,11);
 assert.equal(x.exactNctMentionedInTitleOrAbstract,8);
 assert.equal(x.exactNctOnlyLinkedByDatabank,3);
 assert.equal(x.studies.length,7);
 assert.equal(x.studies.reduce((n,s)=>n+s.articles.length,0),11);
 assert.equal(x.independentlyAdjudicatedPivotalPrimaryPublications,0);
 assert.equal(x.originalFullTextHumanReviews,0);
 assert.equal(x.signedStatisticalScienceGrades,0);
 assert.equal(x.validatedFDAForecasts,0);
 assert.equal(x.measuredAccuracy,null);
 assert.equal(x.futureFDAOutcome,"ABSTAIN");
 assert.equal(x.sourceOnlyNoHistoricalOutcomeOrProductionWrites,true);
 for(const s of x.studies)for(const r of s.articles){
  assert.equal(r.pubmedUrl,"https://pubmed.ncbi.nlm.nih.gov/"+r.pmid+"/");
  assert.equal(r.isPhase3PivotalEfficacyIndependentlyAdjudicated,false);
  assert.equal(r.isFullTextIndependentlyReviewed,false);
  assert.equal(r.hasVerifiedOriginalPreUnblindingSAP,false);
  assert.equal(r.scientificGrade,null);
  assert.equal(r.qualifiedReviewerSigned,false);
  assert.equal(r.futureFdaOutcome,"ABSTAIN");
 }
});

test("Phase II RINGSIDE and casimersen manuscripts cannot count as pivotal phase III",()=>{
 const groups=new Map(FOCUS_R70_ARTICLE_SOURCE.studies.map(s=>[s.nct,s.articles]));
 const ringside=groups.get("NCT04871282")[0];
 assert.equal(ringside.pmid,"42848980");
 assert.equal(ringside.pubmedDatabankOnlyExactNct,true);
 assert.ok(ringside.pubmedPublicationTypes.includes("Clinical Trial, Phase II"));
 assert.ok(ringside.metadataCautions.some(x=>x.includes("Phase 2 component")));
 assert.equal(ringside.isPhase3PivotalEfficacyIndependentlyAdjudicated,false);
 const casimersen=groups.get("NCT02500381").find(x=>x.pmid==="34105177");
 assert.ok(casimersen.pubmedPublicationTypes.includes("Clinical Trial, Phase I"));
 assert.ok(casimersen.pubmedPublicationTypes.includes("Clinical Trial, Phase II"));
 assert.equal(casimersen.pubmedDatabankOnlyExactNct,true);
 const background=groups.get("NCT02500381").find(x=>x.pmid==="40098309");
 assert.match(background.title,/typically developing children/);
 assert.equal(background.articleTextExplicitExactNct,false);
 assert.equal(background.pubmedDatabankOnlyExactNct,true);
 assert.equal(groups.get("NCT02500381").length,2);
});

test("Original PubMed Phase 3 and protocol indexing remains source text not validated science",()=>{
 const groups=new Map(FOCUS_R70_ARTICLE_SOURCE.studies.map(s=>[s.nct,s.articles]));
 const capr=groups.get("NCT05126758")[0];
 assert.equal(capr.pmid,"42526472");
 assert.equal(capr.articleTextExplicitExactNct,true);
 assert.ok(capr.pubmedPublicationTypes.includes("Clinical Trial, Phase III"));
 assert.ok(capr.metadataCautions.some(x=>x.includes("PubMed indexed Phase III")));
 const protocol=groups.get("NCT05662241").find(x=>x.pmid==="41840328");
 assert.ok(protocol.metadataCautions.some(x=>x.includes("protocol/methods")));
 assert.equal(protocol.isPhase3PivotalEfficacyIndependentlyAdjudicated,false);
 const aficamten=groups.get("NCT06081894");
 assert.equal(aficamten.length,3);
 assert.equal(aficamten.filter(x=>x.isPhase3PivotalEfficacyIndependentlyAdjudicated).length,0);
});

test("Mutated PMID, article text flag, source sha, duplicate or fake grade keys fail closed",()=>{
 const edits=[
  d=>d.entries.pop(),
  d=>d.entries[0][1]="99999999",
  d=>d.entries[0][0]="NCT99999999",
  d=>d.entries[0][5]=true,
  d=>d.entries[0][6]=false,
  d=>d.entries[0][7]=["Clinical Trial, Phase X"],
  d=>d.entries[0][8]=["PROGNOSTIC_FDA_APPROVAL"],
  d=>d.entries[0][4]="not-a-doi",
  d=>d.originalResearchSha256="a".repeat(64),
  d=>d.originalPubmedXmlSha256="a".repeat(64),
  d=>d.validatedForecasts=23,
  d=>d.entries.push(structuredClone(d.entries[0]))
 ];
 edits.forEach((edit,i)=>{
  const d=structuredClone(original);edit(d);
  assert.equal(buildR70SourceArticleView(d),null,
    "tampered PubMed source metadata "+i+" must not display");
 });
});

test("R70 metadata/abstract evidence UI is inside the existing R69 and R68 search",()=>{
 const get=f=>fs.readFileSync(path.join(root,f),"utf8");
 const board=get("app/predictions/evidence-gaps/EvidenceRecoveryBoardR68.tsx");
 const parent=get("app/predictions/evidence-gaps/OriginalPublicationLeadsR69.tsx");
 const panel=get("app/predictions/evidence-gaps/OriginalPubmedArticleMetadataR70.tsx");
 const css=get("app/predictions/evidence-gaps/OriginalPubmedArticleMetadataR70.module.css");
 assert.match(board,/FOCUS_R70_ARTICLE_SOURCE/);
 assert.match(board,/exactNctOnlyLinkedByDatabank/);
 assert.match(parent,/<OriginalPubmedArticleMetadataR70/);
 assert.match(panel,/ClinicalTrials\.gov/);
 assert.match(panel,/PubMed indexed publication types/);
 assert.match(panel,/ABSTAIN/);
 assert.match(panel,/NOT SCIENTIFICALLY ADJUDICATED/);
 assert.match(css,/@media\(max-width:470px\)/);
 assert.doesNotMatch(panel,/fetch\(|signClinicalReview|setClinicalScore|POST\s*\/api/);
});
