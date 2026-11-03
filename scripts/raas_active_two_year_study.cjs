#!/usr/bin/env node
"use strict";
/**
 * ACTIVE 2024–2025 PDUFA historical window study. The 2016–2025
 * scripts and evidence are archival. Never treat old examples or unverified
 * 2024–2025 retrospective archive dates as approved trading opportunities.
 *
 * This script intentionally retains the original 30 + 30 issuer-disjoint
 * minimum rather than substituting the 3,828 calendar-window rows for
 * independent companies. FDA 2024–2025 outcome census remains unaudited.
 */
const fs=require("node:fs"),path=require("node:path");
const legacy=require("./raas_alpaca_ten_year_study.cjs");
const prior=require("./raas_alpaca_historical_price_study.cjs");
const root=path.resolve(__dirname,"..");
const CONFIG="new-platform/frontend/data/raas-active-study-config.json";
const INTAKE="new-platform/frontend/data/raas-active-2024-2025-pdufa-intake.json";
const ARCHIVE="data/historical_assessed_decisions.csv";
const VENUES="new-platform/frontend/data/raas-alpaca-venue-exceptions.json";
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const validUrl=s=>typeof s==="string"&&/^https:\/\/[^\s/]+\.[^\s/]+/i.test(s);
const date=s=>typeof s==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&
 !Number.isNaN(Date.parse(s+"T00:00:00Z"))&&new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
function verifyConfig(config){
 if(!config||config.schemaVersion!==1||
  config.scope!=="RAAS_ACTIVE_2024_2025_TWO_YEAR_PDUFA_STUDY"||
  config.status!=="RESEARCH_ONLY_NOT_VALIDATED"||
  config.startDate!=="2024-01-01"||config.endDate!=="2025-12-31"||
  JSON.stringify(config.years)!=="[2024,2025]"||
  config.studyDurationYears!==2||config.trainYear!==2024||config.holdoutYear!==2025||
  config.requiredFullCensusYears!==2||
  config.historicalMarketCapUsdMillionsMin!==300||
  config.historicalMarketCapUsdMillionsMax!==10000||
  config.entryLeadCalendarDaysMin!==4||config.entryLeadCalendarDaysMax!==90||
  config.exitLeadCalendarDaysMin!==3||
  config.minimumIndependentTrainIssuers!==30||
  config.minimumIndependentHoldoutIssuers!==30||
  config.sourceIntake!==INTAKE||config.priorTenYearArchive!==
   "new-platform/frontend/data/raas-ten-year-pdufa-intake.json")
  throw Error("RAAS_TWO_YEAR_ACTIVE_SCOPE_INVALID");
 return config;
}
function discoveryQueue(csv,config){
 verifyConfig(config);
 const all=legacy.candidateQueue(csv);
 const selected=all.filter(x=>x.pdufaDate>=config.startDate&&x.pdufaDate<=config.endDate);
 if(selected.some(x=>x.evidenceStatus!=="ARCHIVE_CANDIDATE_NOT_SOURCE_VERIFIED"))
  throw Error("RAAS_TWO_YEAR_ARCHIVE_PROMOTED_TO_SOURCE_REVIEWED");
 return selected;
}
function reviewIntake(intake,config){
 verifyConfig(config);
 if(intake?.schemaVersion!==1||intake.scope!=="RAAS_2024_2025_PDUFA_POINT_IN_TIME_INTAKE"||
  intake.studyStartDate!==config.startDate||intake.studyEndDate!==config.endDate||
  !Array.isArray(intake.yearAudits)||intake.yearAudits.length!==2||
  !Array.isArray(intake.records))
  throw Error("RAAS_TWO_YEAR_INTAKE_INVALID");
 const years=config.years.map(y=>{
  const matches=intake.yearAudits.filter(a=>a.year===y);
  if(matches.length!==1||
   !["NOT_AUDITED","FULL_EVENT_CENSUS_AUDITED"].includes(matches[0].status)||
   (matches[0].status==="FULL_EVENT_CENSUS_AUDITED"&&!validUrl(matches[0].sourceUrl)))
   throw Error("RAAS_TWO_YEAR_CENSUS_YEAR_INVALID");
  const a=matches[0];
  return {year:y,complete:a.status==="FULL_EVENT_CENSUS_AUDITED"&&validUrl(a.sourceUrl),
   sourceUrl:validUrl(a.sourceUrl)?a.sourceUrl:null};
 });
 const seen=new Set(),accepted=[],rejected=[];
 for(const r of intake.records){
  // Reject/stop on out-of-period records, rather than quietly incorporating
  // ten-year source leads into the 2024–2025 active cohort.
  if(!date(r?.pdufaDate)||r.pdufaDate<config.startDate||r.pdufaDate>config.endDate)
   throw Error("RAAS_TWO_YEAR_OUT_OF_PERIOD_EVENT_FORBIDDEN");
  const k=r?.ticker+"|"+r?.programId+"|"+r?.pdufaDate;
  if(seen.has(k)||!legacy.validRecord(r)){
   rejected.push({caseId:r?.caseId??null,reason:"MISSING_OR_DUPLICATE_POINT_IN_TIME_SOURCE_EVIDENCE"});
  }else{seen.add(k);accepted.push(r);}
 }
 return {years,complete:years.every(y=>y.complete),accepted,rejected};
}
function selectResearchWindow(rows,censusComplete,config){
 verifyConfig(config);
 const eligible=rows.filter(x=>x.status==="POINT_IN_TIME_PRICE_RESEARCH");
 const holdoutIssuers=new Set(eligible.filter(x=>x.year===config.holdoutYear).map(x=>x.ticker));
 const cells=new Map();
 for(const r of eligible){
  if(![config.trainYear,config.holdoutYear].includes(r.year))
   throw Error("RAAS_TWO_YEAR_WINDOW_OUT_OF_SCOPE");
  const key=r.entryLeadDays+"|"+r.exitLeadDays;
  if(!cells.has(key))cells.set(key,{train:[],holdout:[]});
  if(r.year===config.trainYear&&!holdoutIssuers.has(r.ticker))cells.get(key).train.push(r);
  if(r.year===config.holdoutYear)cells.get(key).holdout.push(r);
 }
 const compared=[...cells.entries()].map(([k,v])=>{
  const [entryLeadDays,exitLeadDays]=k.split("|").map(Number);
  const train=legacy.summary(legacy.independent(v.train));
  const holdout=legacy.summary(legacy.independent(v.holdout));
  return {entryLeadDays,exitLeadDays,train,holdout,
   enoughIndependentIssuers:train.n>=config.minimumIndependentTrainIssuers&&
    holdout.n>=config.minimumIndependentHoldoutIssuers};
 }).sort((a,b)=>Number(b.enoughIndependentIssuers)-Number(a.enoughIndependentIssuers)||
  (b.train.medianPct??-Infinity)-(a.train.medianPct??-Infinity));
 const hasSample=compared.some(x=>x.enoughIndependentIssuers);
 return {status:!censusComplete?"BLOCKED_INCOMPLETE_2024_2025_EVENT_CENSUS":
  !hasSample?"BLOCKED_INSUFFICIENT_2024_2025_ISSUER_DISJOINT_HOLDOUT":
  "RESEARCH_COMPARISON_REQUIRES_INDEPENDENT_VALIDATION",
  winner:null,approvedTradingWindow:null,
  issuerSplit:"2024 training; 2025 issuer-disjoint untouched holdout",
  separateIssuersRequired:{train:30,holdout:30},
  comparedGridCells:compared.length,
  researchComparison:hasSample?compared.find(x=>x.enoughIndependentIssuers):null,
  note:"Never declare an optimized T-90..T-3 trading window or numeric RAAS grade from an incomplete cohort, backfilled outcomes or provisional price calculations."};
}
async function execute({config=JSON.parse(read(CONFIG)),intake=JSON.parse(read(INTAKE)),
 csv=read(ARCHIVE),venueExceptions=JSON.parse(read(VENUES)).records,
 key,secret,request=fetch,fetchDiscoveryPrices=true}={}){
 const policy=verifyConfig(config),audit=reviewIntake(intake,policy);
 const candidates=discoveryQueue(csv,policy),byEvent=new Map(),statuses=[];
 for(const c of [...candidates,...audit.accepted]){
  const k=c.ticker+"|"+(c.pdufaDate||"");
  if(!byEvent.has(k))byEvent.set(k,{ticker:c.ticker,pdufaDate:c.pdufaDate});
 }
 const exceptions=venueExceptions.filter(x=>x.notUSListedForEvent===true&&
  x.status==="FOREIGN_LISTING_NOT_COVERED_BY_ALPACA_US_STOCK_FEED"&&
  validUrl(x.sourceUrl)&&date(x.eventDate));
 const priceData=new Map();
 if(key&&secret){
  for(const [eventKey,event] of byEvent){
   const outside=exceptions.find(v=>v.ticker===event.ticker&&v.eventDate===event.pdufaDate);
   if(outside){
    statuses.push({ticker:event.ticker,pdufaDate:event.pdufaDate,
     status:"OUTSIDE_ALPACA_US_STOCK_FEED",sourceUrl:outside.sourceUrl});
    continue;
   }
   if(!fetchDiscoveryPrices&&!audit.accepted.some(x=>
    x.ticker===event.ticker&&x.pdufaDate===event.pdufaDate))continue;
   try{
    const bars=await prior.downloadBars({ticker:event.ticker,
     scheduledEventDate:event.pdufaDate,
     firstBarDate:prior.minusDays(event.pdufaDate,100),
     lastBarDate:event.pdufaDate},key,secret,request);
    if(bars.length<20)throw Error("RAAS_TWO_YEAR_INSUFFICIENT_BARS");
    priceData.set(eventKey,bars);
    statuses.push({ticker:event.ticker,pdufaDate:event.pdufaDate,
     status:"ADJUSTED_SIP_PRICE_ROWS_COLLECTED_RESEARCH_ONLY",sessions:bars.length});
   }catch(e){
    statuses.push({ticker:event.ticker,pdufaDate:event.pdufaDate,
     status:"HISTORIC_PRICE_SOURCE_UNAVAILABLE",
     reason:String(e.message).replace(/[^A-Z0-9_]/g,"_").slice(0,100)});
   }
  }
 }
 const grid=[];
 for(const caseRecord of audit.accepted){
  const bars=priceData.get(caseRecord.ticker+"|"+caseRecord.pdufaDate);
  if(bars)grid.push(...legacy.grid(caseRecord,bars));
 }
 const arithmetic=grid.filter(w=>w.status==="POINT_IN_TIME_PRICE_RESEARCH");
 const ranking=selectResearchWindow(grid,audit.complete,policy);
 const years=Object.fromEntries(policy.years.map(y=>[y,{
  archiveCandidates:candidates.filter(x=>x.pdufaDate.startsWith(String(y))).length,
  auditedComplete:audit.years.find(x=>x.year===y)?.complete??false,
  sourceReviewedCases:audit.accepted.filter(x=>x.pdufaDate.startsWith(String(y))).length,
  provisionalPriceWindows:arithmetic.filter(x=>x.year===y).length
 }]));
 const status=!key||!secret?"BLOCKED_MISSING_ALPACA_CREDENTIALS":
  !audit.complete?"INCOMPLETE_2024_2025_CENSUS_RESEARCH_ONLY":ranking.status;
 return {schemaVersion:1,scope:policy.scope,status,
  studyStartDate:policy.startDate,studyEndDate:policy.endDate,studyDurationYears:2,
  trainingYear:2024,holdoutYear:2025,years,
  researchOnly:true,finalValidation:"NOT_VALIDATED",
  archiveOutsideActiveScope:"2016-2023_RESEARCH_PRESERVED_EXCLUDED_FROM_ACTIVE_COHORT",
  dataFeed:"ALPACA_SIP_1DAY_ADJUSTMENT_ALL_DISCOVERY_ONLY",
  source:"data/historical_assessed_decisions.csv (candidate events; dates unverified)",
  discoveryCandidates:candidates.length,
  sourceReviewedIntakeCases:audit.accepted.length,rejectedIntake:audit.rejected,
  fullYearCensusAudited:audit.years.filter(x=>x.complete).length,
  requiredFullYearCensusAudits:2,
  independentTradingCasesValidated:0,approvedRaasMetricCalibrations:0,
  approvedTradingWindow:null,
  priceResearchEventsCollected:priceData.size,
  historicAdjustedPriceBarsCollected:[...priceData.values()].reduce((n,x)=>n+x.length,0),
  provisionalWindowArithmeticRows:arithmetic.length,
  blockedWindowRows:grid.length-arithmetic.length,
  priceSourceFailures:statuses.filter(x=>x.status==="HISTORIC_PRICE_SOURCE_UNAVAILABLE").length,
  nonUSVenueGaps:statuses.filter(x=>x.status==="OUTSIDE_ALPACA_US_STOCK_FEED").length,
  priceStatuses:statuses,
  priceRows:[...priceData.entries()].flatMap(([k,bars])=>bars.map(b=>({
   eventKey:k,session:b.date,adjustedClose:b.close,adjustedOpen:b.open,
   feed:"SIP",adjustment:"all",source:"Alpaca historical 1Day price, not verified trade"}))),
  candidateWindows:grid,
  selection:ranking,
  caveats:["2024–2025 is the ACTIVE two-year window; legacy 2016–2025 evidence remains in archived workflows only.",
   "A two-year sample is faster to gather, but has less statistical power and may miss regulatory regimes and cycles.",
   "Historical FDA events are retrospective discovery leads: original date-of-announcement, Phase 3 and entire outcome denominator are not established by an archive row.",
   "Only accepted original issuer+FDA+SEC research can be compared, and daily market cap must be established independently at every entry.",
   "Unverifiable vendor prices, delisted tickers, and foreign venues are explicit coverage gaps, never zero or positive returns.",
   "The selection algorithm never approves any RAAS numerical metric or a trading optimum without the complete cohort and additional independent statistical/corporate-action review."]};
}
function main(){
 execute({key:process.env.APCA_API_KEY_ID||process.env.ALPACA_API_KEY_ID||process.env.ALPACA_API_KEY,
  secret:process.env.APCA_API_SECRET_KEY||process.env.ALPACA_SECRET_KEY}).then(r=>{
  const dest=process.env.RAAS_TWO_YEAR_RESULT_PATH||
   path.join(root,"raas-2024-2025-pdufa-research.json");
  fs.mkdirSync(path.dirname(dest),{recursive:true});
  fs.writeFileSync(dest,JSON.stringify(r,null,2)+"\n");
  const headline={status:r.status,period:r.studyStartDate+" to "+r.studyEndDate,
   discoveryCandidates:r.discoveryCandidates,reviewed:r.sourceReviewedIntakeCases,
   yearsAudited:r.fullYearCensusAudited,
   priceSessions:r.historicAdjustedPriceBarsCollected,
   provisionalGridRows:r.provisionalWindowArithmeticRows,
   validatedTrades:r.independentTradingCasesValidated,
   approvedRaasScores:r.approvedRaasMetricCalibrations,
   selection:r.selection.status};
  console.log(JSON.stringify(headline));
  if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,
   "### ACTIVE RAAS 2024–2025 two-year PDUFA historical study\n\n"+
   JSON.stringify(headline,null,2)+"\n\n2016–2025 is now legacy/archive only. No verified trades or scores.\n");
  if(r.status==="BLOCKED_MISSING_ALPACA_CREDENTIALS")process.exitCode=1;
 }).catch(e=>{
  console.error("RAAS_TWO_YEAR_FATAL_"+String(e.message).replace(/[^A-Z0-9_]/g,"_"));
  process.exitCode=1;
 });
}
if(require.main===module)main();
module.exports={verifyConfig,discoveryQueue,reviewIntake,selectResearchWindow,execute};
