const test=require("node:test");const assert=require("node:assert/strict");const fs=require("node:fs");const path=require("node:path");
const root=path.resolve(__dirname,"..");const read=p=>fs.readFileSync(path.join(root,p),"utf8");
test("TOP 30-question pre-readout analysis retains only two documented predictions",()=>{
 const data=read("lib/phase3-top-questions.ts");
 assert.match(data,/PHASE3_QUESTION_COUNT=30/);
 assert.match(data,/NCT06641089/);
 assert.match(data,/number:1,heading:"Primary endpoint efficacy"/);
 assert.match(data,/number:2,heading:"Statistical reliability"/);
 assert.match(data,/Heading not yet defined/);
 assert.match(data,/predicted, NOT a reported result/);
});
test("TOP research case remains outside membership and CSV appends 30 question columns",()=>{
 const ui=read("app/Phase3TopAnalysis.tsx");
 assert.match(ui,/not included in TOP source counts/);
 assert.match(ui,/No surveys or ratings/);
 const csv=read("lib/raas-cap-screened-top-phase3.ts");
 assert.match(csv,/phase3AnalysisCsvHeaders\(\)/);
 assert.match(csv,/phase3AnalysisCsvValues\(row.nctId\)/);
 const page=read("app/Phase3SourceOnlySheets.tsx");
 assert.match(page,/<TopPhase3ResearchExample\/>/);
});

test("Q2 opens with large predicted PASS instead of reported result",()=>{
 const ui=read("app/Phase3TopAnalysis.tsx");
 assert.match(ui,/defaultOpen=\{q.number===2&&!!q.answer\}/);
 assert.match(ui,/fontSize:34/);
 assert.match(ui,/PREDICTED · NOT REPORTED/);
 assert.match(ui,/data-phase3-prediction=\{q.answer.prediction\}/);
});
