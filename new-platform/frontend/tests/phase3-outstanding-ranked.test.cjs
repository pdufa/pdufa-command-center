const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const root=path.resolve(__dirname,"..");
const read=file=>fs.readFileSync(path.join(root,file),"utf8");
const api=read("app/api/phase3-outstanding-ranked/route.ts");
const page=read("app/phase3-outstanding/page.tsx");
const backlog=read("app/raas-evidence-backlog/page.tsx");
const ledger=JSON.parse(read("public/phase3-unified-classifications-2026-11-05.json"));
test("Historic 762-trial source remains available for audit, not a current eligibility list",()=>{
 assert.equal(ledger.rows.length,762);
 assert.equal(new Set(ledger.rows.map(r=>r.nctId)).size,762);
 assert.match(api,/getMissingAudit/);
 assert.match(api,/parsed.length!==762/);
});
test("Old 762-trial pages redirect to current P3 post-data roster",()=>{
 assert.match(page,/redirect\("\/p3-post-data"\)/);
 assert.match(backlog,/redirect\("\/p3-post-data"\)/);
 for(const src of [page,backlog])assert.doesNotMatch(src,/fetch\(|buildTrialEvidenceBacklog|useEffect/);
});
