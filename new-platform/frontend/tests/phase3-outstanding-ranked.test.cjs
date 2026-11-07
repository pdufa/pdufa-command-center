const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const root=path.resolve(__dirname,"..");
const read=file=>fs.readFileSync(path.join(root,file),"utf8");
const ledger=JSON.parse(read("public/phase3-unified-classifications-2026-11-05.json"));

test("Historic 762-NCT research source is preserved for audit, not an active roster",()=>{
 assert.equal(ledger.rows.length,762);
 assert.equal(new Set(ledger.rows.map(r=>r.nctId)).size,762);
});

test("Retired 762-NCT ranking page and API do not publish outdated trial exports",()=>{
 const page=read("app/phase3-outstanding/page.tsx");
 const api=read("app/api/phase3-outstanding-ranked/route.ts");
 assert.match(page,/redirect\("\/p3-post-data"\)/);
 assert.match(api,/RETIRED_COHORT/);
 assert.match(api,/status:410/);
 assert.doesNotMatch(api,/format==="trials.csv"/);
});
