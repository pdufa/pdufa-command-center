const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const ts=require("typescript");
require.extensions[".ts"]=(module,filename)=>module._compile(
  ts.transpileModule(fs.readFileSync(filename,"utf8"),{
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}
  }).outputText,filename
);
const {bestFitTrend}=require("../lib/assessment-best-fit-trend.ts");

test("least-squares regression is a straight best fit, not connected monthly points",()=>{
  const fit=bestFitTrend([{x:2,y:5},{x:0,y:1},{x:1,y:3}]);
  assert.ok(fit);
  assert.equal(fit.slopePerX,2);
  assert.equal(fit.xStart,0);
  assert.equal(fit.xEnd,2);
  assert.equal(fit.yStart,1);
  assert.equal(fit.yEnd,5);
  assert.equal(fit.observations,3);
});

test("best fit smooths a fluctuating historical cumulative result, preserving raw values",()=>{
  const points=[
    {x:0,y:85.7},{x:1,y:93.3},{x:2,y:95.2},
    {x:3,y:96.6},{x:4,y:97.0},{x:5,y:93.3},
    {x:6,y:92.7},{x:7,y:93.7},{x:8,y:94.0},{x:9,y:94.3}
  ];
  const copy=JSON.stringify(points),fit=bestFitTrend(points);
  assert.ok(fit);
  assert.ok(Math.abs(fit.slopePerX)<1);
  assert.notEqual(fit.yStart,points[0].y);
  assert.notEqual(fit.yEnd,points.at(-1).y);
  assert.equal(JSON.stringify(points),copy); // Never change historical results.
});

test("no fabricated trend when only one month, duplicate x, bad values or missing values",()=>{
  assert.equal(bestFitTrend([]),null);
  assert.equal(bestFitTrend([{x:0,y:80}]),null);
  assert.equal(bestFitTrend([{x:0,y:80},{x:0,y:90}]),null);
  assert.equal(bestFitTrend([{x:0,y:80},{x:1,y:NaN}]),null);
  assert.equal(bestFitTrend([{x:0,y:80},{x:1,y:Infinity}]),null);
  assert.equal(bestFitTrend([{x:0,y:80},{x:1,y:110}]),null);
});

test("a stable historical series yields a flat trendline without false momentum",()=>{
  const fit=bestFitTrend([{x:0,y:90},{x:3,y:90},{x:8,y:90}]);
  assert.ok(fit);
  assert.equal(fit.slopePerX,0);
  assert.equal(fit.yStart,90);
  assert.equal(fit.yEnd,90);
});
