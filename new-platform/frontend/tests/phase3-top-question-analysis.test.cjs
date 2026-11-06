const test=require("node:test");const assert=require("node:assert/strict");const fs=require("node:fs");const path=require("node:path");
const root=path.resolve(__dirname,"..");const read=p=>fs.readFileSync(path.join(root,p),"utf8");
test("TOP 30-question pre-readout analysis retains 30 documented predictions",()=>{
 const data=read("lib/phase3-top-questions.ts");
 assert.match(data,/PHASE3_QUESTION_COUNT=30/);
 assert.match(data,/NCT06641089/);
 assert.match(data,/number:1,heading:"Primary endpoint efficacy"/);
 assert.match(data,/number:2,heading:"Statistical reliability"/);
 assert.match(data,/number:3,heading:"Safety and tolerability"/);
 assert.match(data,/score:75/);
 assert.match(data,/score:70/);
 assert.match(data,/score:80/);
 assert.match(data,/PHASE3_QUESTION_TITLES/);
 assert.match(data,/"number":30/);
 assert.match(data,/predicted, NOT a reported result/);
});
test("TOP research case remains outside membership and CSV appends 30 question columns",()=>{
 const ui=read("app/Phase3TopAnalysis.tsx");
 assert.match(ui,/not included in TOP source counts/);
 assert.match(ui,/RAAS surveys remain cancelled/);
 const csv=read("lib/raas-cap-screened-top-phase3.ts");
 assert.match(csv,/phase3AnalysisCsvHeaders\(\)/);
 assert.match(csv,/phase3AnalysisCsvValues\(row.nctId\)/);
 const page=read("app/Phase3SourceOnlySheets.tsx");
 assert.match(page,/<TopPhase3ResearchExample\/>/);
});

test("Q2 opens with large predicted PASS instead of reported result",()=>{
 const ui=read("app/Phase3TopAnalysis.tsx");
 assert.match(ui,/open=\{\(q.number===2\|\|q.number===3\)&&!!q.answer\}/);
 assert.match(ui,/fontSize:34/);
 assert.match(ui,/PREDICTED · NOT REPORTED/);
 assert.match(ui,/data-phase3-prediction=\{q.answer.prediction\}/);
});

test("Every completed question has a prediction-confidence score and CSV conveys it",()=>{
 const data=read("lib/phase3-top-questions.ts");
 const ui=read("app/Phase3TopAnalysis.tsx");
 assert.match(data,/score:number/);
 assert.match(data,/favorable-outcome score /);
 assert.match(data,/not calibrated/);
 assert.match(ui,/data-question-score=\{q.number\}/);
 assert.match(ui,/not a reported result or statistically calibrated probability/);
});

test("All 30 question headings have answers for IZAR-2 with subjective scores",()=>{
 const data=read("lib/phase3-top-questions.ts");
 const ui=read("app/Phase3TopAnalysis.tsx");
 const ids=[...data.matchAll(/"number":(\d+),"heading":/g)].map(x=>Number(x[1]));
 assert.equal(ids.length,27);
 assert.deepEqual(ids,Array.from({length:27},(_,i)=>i+4));
 assert.match(data,/Formal risankizumab superiority/);
 assert.match(data,/Cross-trial consistency/);
 assert.match(data,/Future PsA regulatory package/);
 assert.match(ui,/q.answer.score/);
});
