const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const path=require("node:path");
const ts=require("typescript");
const source=fs.readFileSync(path.join(__dirname,"../lib/medical-intelligence-registry-results.ts"),"utf8");
const compiled=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const moduleObj={exports:{}};
vm.runInNewContext(compiled,{module:moduleObj,exports:moduleObj.exports});
const {parseRegistryResults}=moduleObj.exports;
const trial=(nct="NCT04544293")=>({protocolSection:{identificationModule:{nctId:nct}},resultsSection:{
 outcomeMeasuresModule:{outcomeMeasures:[{type:"PRIMARY",title:"Change in biomarker",unitOfMeasure:"percentage points",timeFrame:"Week 24",groups:[{id:"OG000",title:"Active arm"},{id:"OG001",title:"Placebo"}],analyses:[{groupIds:["OG000","OG001"],pValue:"0.0007",statisticalMethod:"ANCOVA",paramType:"MEAN_DIFFERENCE",paramValue:6,ciNumSides:"TWO_SIDED",ciPctValue:95,ciLowerLimit:2.8,ciUpperLimit:9.1}]}]},
 adverseEventsModule:{eventGroups:[{id:"EG1",title:"Active arm",seriousNumAffected:4,seriousNumAtRisk:103,otherNumAffected:50,otherNumAtRisk:103},{id:"EG2",title:"Placebo",seriousNumAffected:7,seriousNumAtRisk:100}],seriousEvents:[{term:"Example event"}]}
}});
test("Registry p-values and groups must come from exact NCT API payload",()=>{
 const report=parseRegistryResults(trial(),"NCT04544293");
 assert.equal(report.nct,"NCT04544293");
 assert.equal(report.outcomes[0].title,"Change in biomarker");
 assert.equal(report.outcomes[0].analyses[0].reportedPValue,"0.0007");
 assert.equal(report.outcomes[0].analyses[0].confidenceInterval,"95% CI 2.8 to 9.1");
 assert.deepEqual([...report.outcomes[0].analyses[0].comparisons],["Active arm","Placebo"]);
 assert.equal(report.events.length,2);
 assert.equal(report.events[0].seriousAffected,4);
 assert.equal(report.events[1].otherAffected,null);
 assert.equal(report.seriousEventTerms,1);
 assert.equal(report.nonSeriousEventTerms,0);
 assert.throws(()=>parseRegistryResults(trial(),"NCT00000000"),/mismatch/);
});
test("No posted result cannot become fabricated p-value or clean safety",()=>{
 const r=parseRegistryResults({protocolSection:{identificationModule:{nctId:"NCT04544293"}}},"NCT04544293");
 assert.equal(r.resultsPosted,false);
 assert.equal(r.outcomes.length,0);
 assert.equal(r.events.length,0);
 assert.ok(r.limitations.some(x=>x.includes("p-value")));
});
test("Missing p value remains missing even for a posted outcome",()=>{
 const payload=trial();
 payload.resultsSection.outcomeMeasuresModule.outcomeMeasures[0].analyses=[{groupIds:["OG000","OG001"]}];
 const r=parseRegistryResults(payload,"NCT04544293");
 assert.equal(r.outcomes[0].analyses[0].reportedPValue,null);
 assert.equal(r.outcomes[0].analyses[0].confidenceInterval,null);
});
