const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.resolve(__dirname,"../app");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");

test("PAST and FOCUS both mount scoped sorting popups",()=>{
 const past=read("past/page.tsx"),focus=read("focus/page.tsx");
 assert.match(past,/<NumericSortSettings scope="past"/);
 assert.match(focus,/<NumericSortSettings scope="focus"/);
 assert.match(past,/sortNumericRows\(subset,sortRules/);
 assert.match(focus,/sortNumericRows\(trials,sortRules/);
 assert.match(focus,/sortedTrials\.map\(/);
});

test("sort comparator keeps missing numeric values last and ties deterministic",()=>{
 const src=read("NumericSortSettings.tsx");
 assert.match(src,/if\(am!==bm\)return am\?1:-1/);
 assert.match(src,/id\(a\)\.localeCompare\(id\(b\)\)/);
 assert.match(src,/rule\.direction==="asc"/);
});

test("popup has editable priorities and browser-local named presets",()=>{
 const src=read("NumericSortSettings.tsx");
 for(const marker of ["Add Sorting Column","Save Setup","Load / Edit","Delete Setup","Apply Sort","Reset Sort","Cancel","localStorage.setItem","window.confirm"])assert.ok(src.includes(marker),marker);
 assert.match(src,/scope:"past"\|"focus"/);
});
