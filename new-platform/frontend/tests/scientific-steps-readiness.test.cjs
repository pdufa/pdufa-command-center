const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");

const app=path.join(__dirname,"..","app");
const component=fs.readFileSync(path.join(app,"ScientificStepsReadiness.tsx"),"utf8");

test("shared readiness explicitly avoids claiming scientific activation",()=>{
 assert.match(component,/Integration pending/);
 assert.match(component,/Not live/);
 assert.match(component,/No score or FDA prediction is implied/);
});
for(const [name,cohort] of [["pool","POOL"],["focus","FOCUS"],["past","PAST"]]){
 test(name+" includes Steps 1-3 readiness with correct cohort",()=>{
  const source=fs.readFileSync(path.join(app,name,"page.tsx"),"utf8");
  assert.match(source,/ScientificStepsReadiness/);
  assert.ok(source.includes('cohort="'+cohort+'"'));
 });
}

test("exact trial guard matches NCT followed by eight digits and rejects mismatched identities",()=>{
 assert.ok(component.includes(String.raw`/^NCT\d{8}$/`));
 assert.match(component,/trial\.nctId===trial\.assessmentNctId/);
 assert.match(component,/const intake=exactTrial\?trial\?\.intake:undefined/);
});

test("FOCUS links each exact NCT to saved research without claiming an assessment",()=>{
 const source=fs.readFileSync(path.join(app,"focus","page.tsx"),"utf8");
 assert.ok(source.includes('href={"/analyze-now?nct="+encodeURIComponent(t.nct)}'));
 assert.match(source,/View exact-trial research history/);
});
test("scientific panel fails closed when FDA prediction is not ABSTAIN",()=>{
 assert.match(component,/intake\?\.fdaPrediction==="ABSTAIN"/);
 assert.match(component,/scientificScoreStatus==="NOT_VALIDATED"/);
 assert.match(component,/Array\.isArray\(intake\.missingEvidence\)/);
});

test("exact-program loader uses authenticated assessments and fails closed on identity mismatch",()=>{
 const source=fs.readFileSync(path.join(app,"ExactTrialScientificIntake.tsx"),"utf8");
 assert.match(source,/\/api\/assessments\?identity=/);
 assert.match(source,/record\.id!==programIdentity\|\|record\.nctId!==nctId/);
 assert.match(source,/!validIntake\(record\.levelOneIntake\)/);
 assert.match(source,/scientificValidation==="NOT_VERIFIED"/);
 assert.match(source,/scientificScoreStatus==="NOT_VALIDATED"/);
});

test("FOCUS trial rows expose explicit exact-program intake selector without auto-mapping",()=>{
 const source=fs.readFileSync(path.join(app,"focus","page.tsx"),"utf8");
 const loader=fs.readFileSync(path.join(app,"ExactTrialScientificIntake.tsx"),"utf8");
 assert.match(source,/<ExactTrialIntakeSelector cohort="FOCUS" nctId=\{t\.nct\}\/>/);
 assert.match(loader,/Multiple programs require explicit selection/);
 assert.match(loader,/programIdentity=\{selected\}/);
});

test("POOL exact-NCT review rows provide a guarded intake selector",()=>{
 const source=fs.readFileSync(path.join(app,"FunnelWorkspace.tsx"),"utf8");
 assert.match(source,/<ExactTrialIntakeSelector cohort="POOL" nctId=\{r\.nctId\}\/>/);
 assert.match(source,/section==="pool"/);
});

test("PAST requires explicit NCT and exact program before intake lookup",()=>{
 const source=fs.readFileSync(path.join(app,"past","page.tsx"),"utf8");
 assert.match(source,/Historical event-to-NCT linkage remains unverified/);
 assert.match(source,/<ExactTrialIntakeSelector cohort="PAST" nctId=\{verifiedNctByEvent\[r\.eventKey\]\}\/>/);
 assert.ok(source.includes(String.raw`/^NCT\d{8}$/`), "PAST must validate the exact NCT format");
});

test("exact-NCT discovery refuses ambiguous automatic selection",()=>{
 const source=fs.readFileSync(path.join(app,"ExactTrialScientificIntake.tsx"),"utf8");
 assert.match(source,/fetch\("\/api\/assessments"/);
 assert.match(source,/data\.status!=="COMPLETE"/);
 assert.match(source,/if\(values\.length===1\)/);
 assert.match(source,/Multiple programs share this NCT/);
});

test("NCT discovery clears previously selected program before re-query",()=>{
 const source=fs.readFileSync(path.join(app,"ExactTrialScientificIntake.tsx"),"utf8");
 assert.match(source,/setSelected\(""\);setIdentity\(""\);setMatches\(\[\]\)/);
});

test("overlapping NCT discovery responses cannot replace the latest lookup",()=>{
 const source=fs.readFileSync(path.join(app,"ExactTrialScientificIntake.tsx"),"utf8");
 assert.match(source,/const sequence=\+\+lookupSequence\.current/);
 assert.match(source,/if\(sequence!==lookupSequence\.current\)return/);
 assert.match(source,/if\(sequence===lookupSequence\.current\)setLookupStatus/);
});

test("changing trial NCT invalidates in-flight program lookup and selected identity",()=>{
 const source=fs.readFileSync(path.join(app,"ExactTrialScientificIntake.tsx"),"utf8");
 assert.match(source,/useEffect\(\(\)=>\{/);
 assert.match(source,/\+\+lookupSequence\.current;\s*setIdentity\(""\);setSelected\(""\);setMatches\(\[\]\)/);
 assert.match(source,/\},\[nctId\]\)/);
});


test("authenticated assessment proxy preserves exact identity, backend conflict status, and private caching",()=>{
 const route=fs.readFileSync(path.join(app,"api","assessments","route.ts"),"utf8");
 assert.match(route,/!authConfigured\(\)\s*\|\|\s*!hasSession\(/);
 assert.match(route,/status: 401/);
 assert.match(route,/identity\.length > 512/);
 assert.match(route,/status: 422/);
 assert.match(route,/encodeURIComponent\(identity\)/);
 assert.match(route,/status: response\.status/);
 assert.match(route,/Cache-Control": "private, no-store"/);
 assert.match(route,/headers: \{ "x-pdufa-internal-key": key \}/);
});


test("exact-trial intake explains rejected or unknown identities without exposing evidence",()=>{
 const source=fs.readFileSync(path.join(app,"ExactTrialScientificIntake.tsx"),"utf8");
 assert.match(source,/res\.status===404\?"Exact program not found/);
 assert.match(source,/res\.status===409\?"Exact program identity or evidence is not verified/);
 assert.match(source,/setIntake\(null\);setError\(""\)/);
});


test("exact assessment proxy refuses non-HTTPS backend and does not cache failed evidence",()=>{
 const route=fs.readFileSync(path.join(app,"api","assessments","route.ts"),"utf8");
 assert.match(route,/!base\?\.startsWith\("https:\/\/"\)\s*\|\|\s*!key/);
 assert.match(route,/status: 503/);
 assert.match(route,/cache: "no-store"/);
 assert.match(route,/signal: AbortSignal\.timeout\(45000\)/);
 assert.match(route,/if\s*\(!response\.ok\)\s*return NextResponse\.json/);
});


test("PAST comparison outcomes remain labeled unverified and separate from blind scoring",()=>{
 const source=fs.readFileSync(path.join(app,"past","page.tsx"),"utf8");
 assert.match(source,/Show historical comparison data \(unverified event match; exclude from blind scoring\)/);
 assert.match(source,/Unverified match: /);
 assert.match(source,/candidates\.length===1\?candidates\[0\]:null/);
 assert.match(source,/Ambiguous historical matches/);
 assert.match(source,/ticker and date, not by source-verified FDA event identity/);
 assert.match(source,/!reveal\?"Hidden"/);
});
