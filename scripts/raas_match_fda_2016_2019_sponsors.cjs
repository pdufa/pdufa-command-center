#!/usr/bin/env node
"use strict";
/**
 * Conservative retrospective FDA sponsor-name -> current issuer-registry
 * crosswalk. An exact *name* match is a research lead, not evidence that
 * the issuer held US commercialization rights at the historical action,
 * traded at the time, or had $300M-$10B market cap.
 */
const fs=require("node:fs"),path=require("node:path");
const root=path.resolve(__dirname,"..");
function rows(csv){
 if(typeof csv!=="string")throw Error("RAAS_CSV_INVALID");
 const out=[],row=[];let cell="",quoted=false;
 for(let i=0;i<csv.length;i++){
  const c=csv[i],next=csv[i+1];
  if(c==='"'){
   if(quoted&&next==='"'){cell+='"';i++;}
   else quoted=!quoted;
  } else if(c===","&&!quoted){row.push(cell);cell="";}
  else if((c==="\n"||c==="\r")&&!quoted){
   if(c==="\r"&&next==="\n")i++;
   row.push(cell);cell="";
   if(row.some(x=>x.trim()))out.push(row.slice());
   row.length=0;
  }else cell+=c;
 }
 if(quoted)throw Error("RAAS_CSV_UNCLOSED_QUOTE");
 if(cell||row.length){row.push(cell);out.push(row);}
 if(!out.length)throw Error("RAAS_CSV_EMPTY");
 const hdr=out.shift();
 if(new Set(hdr).size!==hdr.length)throw Error("RAAS_CSV_DUPLICATE_COLUMN");
 return out.map(cells=>Object.fromEntries(hdr.map((name,i)=>[name,cells[i]??""])));
}
function norm(s){
 if(typeof s!=="string")return "";
 let parts=s.normalize("NFKD").toLowerCase().replace(/&/g," and ")
  .replace(/[^a-z0-9]+/g," ").trim().split(/\s+/).filter(Boolean);
 const ending=new Set(["inc","incorporated","corp","corporation","co","company",
 "ltd","limited","llc","plc","sa","ag","nv"]);
 while(parts.length>1&&ending.has(parts[parts.length-1]))parts.pop();
 return parts.join(" ");
}
function crosswalk(discovery,registryCsv){
 if(!discovery||discovery.scope!=="FDA_DRUGS_AT_FDA_2016_2019_APPROVAL_DISCOVERY_NOT_PDUFA_CENSUS"||
  !Array.isArray(discovery.candidates))throw Error("RAAS_FDA_DISCOVERY_INVALID");
 const registry=rows(registryCsv);
 if(!registry.length||registry.some(r=>!Object.hasOwn(r,"ticker")||!Object.hasOwn(r,"company")||
  !Object.hasOwn(r,"status")))throw Error("RAAS_COMPANY_REGISTRY_INVALID");
 const map=new Map();
 for(const r of registry){
  if(r.status!=="OK"||!/^[A-Z][A-Z0-9.-]{0,11}$/.test(r.ticker))continue;
  const n=norm(r.company);
  if(!n)continue;
  if(!map.has(n))map.set(n,new Set());
  map.get(n).add(r.ticker);
 }
 const results=[],seen=new Set();
 for(const c of discovery.candidates){
  if(!c||typeof c.id!=="string"||seen.has(c.id)||
   c.status!=="FDA_APPROVAL_DISCOVERY_ONLY"||
   !/^20(16|17|18|19)-\d{2}-\d{2}$/.test(c.actualApprovalDate)||
   !c.fdaRecordUrl?.startsWith("https://api.fda.gov/"))throw Error("RAAS_FDA_CANDIDATE_INVALID");
  seen.add(c.id);
  const normalized=norm(c.sponsorName),tickerSet=map.get(normalized)||new Set();
  const matches=[...tickerSet].sort();
  results.push({fdaCandidateId:c.id,applicationNumber:c.applicationNumber,
   actionDate:c.actualApprovalDate,year:c.year,sponsor:c.sponsorName,
   productNames:c.productNames,sourceUrl:c.fdaRecordUrl,
   candidateTicker:matches.length===1?matches[0]:null,
   status:matches.length===1?"EXACT_NAME_PUBLIC_REGISTRY_LEAD":
    matches.length>1?"AMBIGUOUS_MULTIPLE_CURRENT_TICKERS":"NO_EXACT_CURRENT_ISSUER_MATCH",
   historicalIssuerVerified:false,commercialRightsVerified:false,
   historicalListingVerified:false,historicalMarketCapVerified:false,
   pdufaTargetFirstPublicVerified:false,phase3ReadoutFirstPublicVerified:false,
   approvalOnlyNotOutcomeUniverse:true});
 }
 const matched=results.filter(x=>x.status==="EXACT_NAME_PUBLIC_REGISTRY_LEAD");
 return {scope:"FDA_2016_2019_APPROVAL_SPONSOR_CURRENT_REGISTRY_NAME_RESEARCH",
  source:"data/company_registry.csv + openFDA original-approval discovery",
  status:"RESEARCH_LEADS_NOT_HISTORICAL_ELIGIBILITY",
  totalFdaActionLeads:results.length,exactCurrentNameLeads:matched.length,
  distinctMatchedCurrentTickers:new Set(matched.map(x=>x.candidateTicker)).size,
  ambiguous:results.filter(x=>x.status==="AMBIGUOUS_MULTIPLE_CURRENT_TICKERS").length,
  noExactMatch:results.filter(x=>x.status==="NO_EXACT_CURRENT_ISSUER_MATCH").length,
  byYear:Object.fromEntries([2016,2017,2018,2019].map(y=>[y,{
   fdaActionLeads:results.filter(x=>x.year===y).length,
   exactCurrentNameLeads:matched.filter(x=>x.year===y).length}])),
  caveats:[
   "Only exact normalized sponsor names are matched. Subsidiaries, licensees, mergers and ADR structures require manual historical issuer/rights verification.",
   "Current registry listings DO NOT prove 2016–2019 historical listings or capitalization.",
   "FDA action dates are not PDUFA targets and approval-only leads omit failed regulatory outcomes.",
   "All rows remain ineligible for a historically validated RAAS entry/exit backtest or metric score."],
  rows:results};
}
if(require.main===module){
 try{
  const input=process.env.RAAS_FDA_BACKFILL_OUTPUT||
   path.join(root,"raas-fda-2016-2019-discovery.json");
  const out=process.env.RAAS_FDA_CROSSWALK_OUTPUT||
   path.join(root,"raas-fda-2016-2019-issuer-crosswalk.json");
  const d=JSON.parse(fs.readFileSync(input,"utf8"));
  const reg=fs.readFileSync(path.join(root,"data/company_registry.csv"),"utf8");
  const x=crosswalk(d,reg);
  fs.writeFileSync(out,JSON.stringify(x,null,2)+"\n");
  const summary={status:x.status,totalFdaActionLeads:x.totalFdaActionLeads,
   exactCurrentNameLeads:x.exactCurrentNameLeads,
   distinctMatchedCurrentTickers:x.distinctMatchedCurrentTickers,
   ambiguous:x.ambiguous,noExactMatch:x.noExactMatch,byYear:x.byYear};
  process.stdout.write(JSON.stringify(summary)+"\n");
  if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,
   "### Conservatively matched FDA approval discovery to present-day issuer names\n\n"+
   JSON.stringify(summary)+"\n\nHistorical issuer/rights and historical cap remain NOT VERIFIED.\n");
 } catch(e) {
  process.stderr.write("RAAS_CROSSWALK_FAILED_"+String(e.message).replace(/[^A-Z0-9_]/g,"_")+"\n");
  process.exitCode=1;
 }
}
module.exports={rows,norm,crosswalk};
