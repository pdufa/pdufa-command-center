"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const reports=path.resolve(__dirname,"../../../reports/phase-first-2026-11-06");
const csv=fs.readFileSync(path.join(reports,"active-258-190-official-refresh-20261106.csv"),"utf8");
const audit=JSON.parse(fs.readFileSync(path.join(reports,"active-258-190-official-coverage-20261106.json"),"utf8"));
function splitCsvRow(line){
 const cells=[];let quoted=false,cell="";
 for(let i=0;i<line.length;i++){
  const c=line[i];
  if(c==='"'){if(quoted&&line[i+1]==='"'){cell+='"';i++;}else quoted=!quoted;}
  else if(c===','&&!quoted){cells.push(cell);cell="";}
  else cell+=c;
 }
 assert.equal(quoted,false,"Unterminated CSV field");
 cells.push(cell);return cells;
}
const rows=csv.replace(/^\uFEFF/,"").trimEnd().split(/\r?\n/).map(splitCsvRow);
test("archived official source refresh preserves 258 exact NCT identities and all 190 cells",()=>{
 assert.equal(rows.length,259);
 assert.ok(rows.every(r=>r.length===190));
 assert.equal(rows[0][0],"NCT");
 const ids=rows.slice(1).map(r=>r[0]);
 assert.ok(ids.every(id=>/^NCT\d{8}$/.test(id)));
 assert.equal(new Set(ids).size,258);
 assert.equal(audit.rows.length,258);
 assert.deepEqual(ids.slice().sort(),audit.rows.map(r=>r.nctId).sort());
});
test("archived live source audit retains missing evidence and does not manufacture clinical grades",()=>{
 assert.equal(audit.totals.trials,258);
 assert.equal(audit.totals.expectedCells,258*190);
 assert.equal(audit.totals.questionSlots,258*30);
 assert.equal(audit.totals.documentedQuestions+audit.totals.predictedQuestions+audit.totals.unscoredQuestions,258*30);
 assert.equal(audit.totals.documentedQuestions,2790);
 assert.equal(audit.totals.unscoredQuestions,4889);
 assert.equal(audit.totals.raasScoredTrials,0);
 assert.equal(audit.perQuestion.length,30);
 assert.ok(audit.rows.every(r=>r.documentedQuestions+r.predictedQuestions+r.unscoredQuestions===30));
 assert.ok(audit.rows.every(r=>r.missingQuestionNumbers.every(n=>Number.isInteger(n)&&n>=1&&n<=30)));
 assert.equal(audit.perQuestion.reduce((n,q)=>n+q.unscored,0),audit.totals.unscoredQuestions);
 assert.equal(audit.checkedAt.startsWith("2026-11-06T"),true);
 assert.ok(audit.limitations.some(s=>s.includes("not 190 independently verified")));
});
