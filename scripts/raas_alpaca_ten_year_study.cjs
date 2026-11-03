#!/usr/bin/env node
"use strict";
/**
 * 2016-2025 PDUFA price-window research. Historical FDA decision records are
 * discovery candidates, NEVER point-in-time investment opportunities.
 * Only separately reviewed, evidenced records can enter the eligible grid.
 * An empty verified intake must result in zero eligible trades / no winner.
 */
const fs = require("node:fs");
const path = require("node:path");
const prior = require("./raas_alpaca_historical_price_study.cjs");
const root = path.resolve(__dirname, "..");
const INTAKE = "new-platform/frontend/data/raas-ten-year-pdufa-intake.json";
const CANDIDATES = "data/historical_assessed_decisions.csv";
const START = "2016-01-01";
const END = "2025-12-31";
const years = Array.from({length:10},(_,i)=>2016+i);
const day = s => typeof s==="string" && /^\d{4}-\d{2}-\d{2}$/.test(s) &&
  !Number.isNaN(Date.parse(s+"T00:00:00Z")) &&
  new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
const urlOK = s => typeof s==="string" && /^https:\/\/[^\s/]+\.[^\s/]+/i.test(s);
const rnd = n => Math.round((n+Number.EPSILON)*100)/100;
const ymd = d => new Date(d).toISOString().slice(0,10);
const plusDays = (d,n) => ymd(Date.parse(d+"T00:00:00Z")+n*86400000);
const read = p => fs.readFileSync(path.join(root,p),"utf8");

/** Screen 10-year FDA-event archive without pretending these are tradable leads. */
function candidateQueue(csv) {
 const events=[], seen=new Set();
 for (const line of csv.split(/\r?\n/).slice(1)) {
  // First three CSV columns are unquoted event_key, ticker, target date.
  const m=/^([^,\r\n]+),([A-Z][A-Z0-9.-]{0,11}),(\d{4}-\d{2}-\d{2}),/.exec(line);
  if (!m || !day(m[3]) || m[3]<START || m[3]>END) continue;
  const key=m[1]+"|"+m[2]+"|"+m[3];
  if (seen.has(key)) continue;
  seen.add(key);
  events.push({eventKey:m[1],ticker:m[2],pdufaDate:m[3],
   evidenceStatus:"ARCHIVE_CANDIDATE_NOT_SOURCE_VERIFIED",
   missing:["PDUFA_FIRST_PUBLIC_DATE","PHASE3_PUBLIC_DATE",
    "HISTORICAL_MARKET_CAP_PER_ENTRY","EARLY_FDA_ACTION_CENSORING"]});
 }
 return events.sort((a,b)=>a.pdufaDate.localeCompare(b.pdufaDate)||
  a.ticker.localeCompare(b.ticker));
}
function validRecord(r) {
 if (!r || typeof r!=="object" || !r.caseId ||
  !/^[A-Z][A-Z0-9.-]{0,11}$/.test(r.ticker||"") ||
  !r.programId || !Array.isArray(r.nctIds) || r.nctIds.length===0 ||
  r.nctIds.some(x=>!/^NCT\d{8}$/.test(x)) ||
  !day(r.pdufaDate) || r.pdufaDate<START || r.pdufaDate>END ||
  !day(r.pdufaFirstPublicDate) || r.pdufaFirstPublicDate>=r.pdufaDate ||
  !day(r.phase3ReadoutDate) || r.phase3ReadoutDate>=r.pdufaDate ||
  !day(r.actualFDAActionDate) ||
  !urlOK(r.pdufaSourceUrl) || !urlOK(r.phase3SourceUrl) ||
  !urlOK(r.actualFDAActionSourceUrl) || !Array.isArray(r.historicalMarketCaps) ||
  r.reviewStatus!=="SOURCE_REVIEWED") return false;
 const seen=new Set();
 return r.historicalMarketCaps.every(c=>{
  if(!c || !day(c.session) || !day(c.sharesSourcePublishedAt) ||
   c.sharesSourcePublishedAt>c.session ||
   typeof c.usdMillions!=="number" || !Number.isFinite(c.usdMillions) ||
   c.usdMillions<=0 || !urlOK(c.sourceUrl) ||
   !urlOK(c.sharesSourceUrl) || seen.has(c.session)) return false;
  seen.add(c.session);
  return true;
 });
}
function intakeRecords(intake) {
 if (!intake || intake.scope!=="RAAS_2016_2025_PDUFA_POINT_IN_TIME_INTAKE" ||
  !Array.isArray(intake.records) || !Array.isArray(intake.yearAudits))
  throw Error("RAAS_TEN_YEAR_INTAKE_SCHEMA_INVALID");
 const seen=new Set(), accepted=[], rejected=[];
 for (const r of intake.records) {
  const k=r?.ticker+"|"+r?.programId+"|"+r?.pdufaDate;
  if (!validRecord(r) || seen.has(k)) {
   rejected.push({caseId:r?.caseId??null,reason:"MISSING_OR_DUPLICATE_POINT_IN_TIME_EVIDENCE"});
  } else {
   seen.add(k);accepted.push(r);
  }
 }
 const complete = years.every(y=>intake.yearAudits.some(x=>x.year===y &&
  x.status==="FULL_EVENT_CENSUS_AUDITED" && urlOK(x.sourceUrl)));
 return {accepted,rejected,complete};
}
function windowPrice(win,bars,e,x) {
 const start=prior.minusDays(win.pdufaDate,e), end=prior.minusDays(win.pdufaDate,x);
 const entry=bars.find(b=>b.date>=start && b.date<=plusDays(start,4));
 const exit=[...bars].reverse().find(b=>b.date<=end && b.date>=plusDays(end,-4));
 const base={caseId:win.caseId,ticker:win.ticker,programId:win.programId,
  year:+win.pdufaDate.slice(0,4),entryLeadDays:e,exitLeadDays:x,
  entryDate:entry?.date??null,exitDate:exit?.date??null,
  status:"BLOCKED",reason:null,grossReturnPct:null,netReturnPct:null};
 if (!entry || !exit) return {...base,reason:"MISSING_TRADING_SESSION"};
 if (entry.date>=exit.date) return {...base,reason:"ENTRY_NOT_BEFORE_EXIT"};
 if (entry.date<win.pdufaFirstPublicDate || entry.date<win.phase3ReadoutDate)
  return {...base,reason:"EVENT_NOT_PUBLIC_AT_ENTRY"};
 if (exit.date>=win.actualFDAActionDate)
  return {...base,reason:"FDA_ACTION_EARLIER_THAN_EXIT"};
 const cap=win.historicalMarketCaps.find(c=>c.session===entry.date);
 if (!cap) return {...base,reason:"MISSING_ENTRY_DAY_HISTORICAL_MARKET_CAP"};
 if (cap.usdMillions<300 || cap.usdMillions>10000)
  return {...base,reason:"HISTORICAL_CAP_OUT_OF_300M_10B_RANGE"};
 const gross=rnd((exit.close/entry.close-1)*100);
 return {...base,status:"POINT_IN_TIME_PRICE_RESEARCH",
  reason:"NEEDS_CORPORATE_ACTION_AND_EXECUTION_AUDIT",
  marketCapAtEntryMillions:cap.usdMillions,
  grossReturnPct:gross,netReturnPct:rnd(gross-1)};
}
function grid(win,bars) {
 const out=[];
 for(let e=90;e>=4;e--) for(let x=3;x<e;x++)
  out.push(windowPrice(win,bars,e,x));
 return out;
}
function summary(xs) {
 if (!xs.length) return {n:0,medianPct:null,meanPct:null,winRatePct:null};
 const vals=xs.map(x=>x.netReturnPct).sort((a,b)=>a-b),n=vals.length;
 return {n,medianPct:rnd(n%2?vals[(n-1)/2]:(vals[n/2-1]+vals[n/2])/2),
  meanPct:rnd(vals.reduce((a,b)=>a+b,0)/n),
  winRatePct:rnd(100*vals.filter(x=>x>0).length/n)};
}
/** One issuer contributes at most one event per candidate window/split. */
function independent(rows) {
 const m=new Map();
 for (const r of [...rows].sort((a,b)=>a.entryDate.localeCompare(b.entryDate) ||
   a.caseId.localeCompare(b.caseId))) if(!m.has(r.ticker))m.set(r.ticker,r);
 return [...m.values()];
}
/**
 * Select on 2016-2022 only; validate the selected rule in issuer-disjoint
 * 2023-2025. No completed annual census => no optimal-window declaration.
 */
function chooseWindow(rows,censusComplete) {
 const viable=rows.filter(x=>x.status==="POINT_IN_TIME_PRICE_RESEARCH");
 const holdoutIssuers=new Set(viable.filter(r=>r.year>=2023).map(r=>r.ticker));
 const groups=new Map();
 for(const r of viable) {
  const k=r.entryLeadDays+"|"+r.exitLeadDays;
  if(!groups.has(k))groups.set(k,{train:[],holdout:[]});
  if(r.year<=2022 && !holdoutIssuers.has(r.ticker))groups.get(k).train.push(r);
  if(r.year>=2023) groups.get(k).holdout.push(r);
 }
 const comparisons=[...groups].map(([key,g])=>{
  const [entryLeadDays,exitLeadDays]=key.split("|").map(Number);
  const train=summary(independent(g.train)),holdout=summary(independent(g.holdout));
  return {entryLeadDays,exitLeadDays,train,holdout,
   minSamplePassed:train.n>=30 && holdout.n>=30};
 }).sort((a,b)=>Number(b.minSamplePassed)-Number(a.minSamplePassed) ||
  (b.train.medianPct??-Infinity)-(a.train.medianPct??-Infinity) ||
  b.train.n-a.train.n || b.entryLeadDays-a.entryLeadDays || a.exitLeadDays-b.exitLeadDays);
 const valid=comparisons.filter(x=>x.minSamplePassed);
 return {status:!censusComplete?"BLOCKED_INCOMPLETE_2016_2025_EVENT_CENSUS":
  !valid.length?"BLOCKED_INSUFFICIENT_ISSUER_DISJOINT_SAMPLE":"TRAIN_SELECTED_HOLDOUT_EVALUATED",
  winner:censusComplete && valid.length?valid[0]:null,
  comparedGridCells:comparisons.length,
  sampleRule:"30 issuers in each of disjoint train 2016-2022 and holdout 2023-2025",
  costAssumption:"1 percentage point gross-return deduction per round trip",
  selectionMethod:"maximize training median net return; evaluate fixed rule on holdout"};
}
async function execute({key,secret,request=fetch,
 candidates=candidateQueue(read(CANDIDATES)),
 intake=JSON.parse(read(INTAKE)),fetchCandidates=true}={}) {
 const audit=intakeRecords(intake), work=new Map(), statuses=[];
 for(const x of [...candidates,...audit.accepted]) {
  const k=x.ticker+"|"+x.pdufaDate;
  if (!work.has(k))work.set(k,{ticker:x.ticker,pdufaDate:x.pdufaDate});
 }
 const prices=new Map();
 if(key && secret) {
  for(const [k,x] of work) {
   const win={ticker:x.ticker,scheduledEventDate:x.pdufaDate,
    firstBarDate:prior.minusDays(x.pdufaDate,100),
    lastBarDate:x.pdufaDate};
   if(!fetchCandidates && !audit.accepted.some(z=>z.ticker===x.ticker&&z.pdufaDate===x.pdufaDate))continue;
   try {
    const bars=await prior.downloadBars(win,key,secret,request);
    if(bars.length<20)throw Error("RAAS_TEN_YEAR_INSUFFICIENT_BARS");
    prices.set(k,bars);
    statuses.push({ticker:x.ticker,pdufaDate:x.pdufaDate,
     status:"ADJUSTED_SIP_PRICE_ROWS_COLLECTED",bars:bars.length});
   } catch(e) {
    statuses.push({ticker:x.ticker,pdufaDate:x.pdufaDate,
     status:"PRICE_SOURCE_UNAVAILABLE",
     reason:String(e.message).replace(/[^A-Z0-9_]/g,"_").slice(0,70)});
   }
  }
 }
 const windowRows=[];
 for(const v of audit.accepted) {
  const bars=prices.get(v.ticker+"|"+v.pdufaDate);
  if(bars)windowRows.push(...grid(v,bars));
 }
 const eligible=windowRows.filter(x=>x.status==="POINT_IN_TIME_PRICE_RESEARCH");
 const byYear=Object.fromEntries(years.map(y=>[y,{
  discoveryCandidates:candidates.filter(c=>c.pdufaDate.startsWith(String(y))).length,
  sourceReviewedEvents:audit.accepted.filter(r=>r.pdufaDate.startsWith(String(y))).length,
  eligiblePriceWindows:eligible.filter(r=>r.year===y).length
 }]));
 const rank=chooseWindow(windowRows,audit.complete);
 return {scope:"2016-2025 US PDUFA events; historical market cap $300M-$10B",
  status:!key||!secret?"BLOCKED_MISSING_ALPACA_CREDENTIALS":
   !audit.complete?"PARTIAL_CENSUS_RESEARCH_ONLY":rank.status,
  dataFeed:"ALPACA_SIP_1DAY_ADJUSTMENT_ALL",
  source:"data/historical_assessed_decisions.csv (discovery ONLY)",
  discoveryCandidates:candidates.length,reviewedEvents:audit.accepted.length,
  rejectedIntake:audit.rejected,tenYearCensusComplete:audit.complete,
  years:byYear,priceEventKeysCollected:prices.size,
  historicalDailyBarsCollected:[...prices.values()].reduce((s,x)=>s+x.length,0),
  eligibleWindowRows:eligible.length,
  blockedWindowRows:windowRows.length-eligible.length,
  priceSourceFailures:statuses.filter(x=>x.status==="PRICE_SOURCE_UNAVAILABLE").length,
  priceRetrievalStatuses:statuses,
  // Retain auditable vendor observations without pretending discovery-only
  // dates or unresolved market caps are validated trade-entry evidence.
  historicalPriceRows:[...prices.entries()].flatMap(([eventKey,bars])=>
   bars.map(b=>({eventKey,session:b.date,adjustedOpen:b.open,
    adjustedClose:b.close,adjustedHigh:b.high,adjustedLow:b.low,
    volume:b.volume,feed:"SIP",adjustment:"all",
    sourceUrl:"https://data.alpaca.markets/v2/stocks/"+
     encodeURIComponent(eventKey.split("|")[0])+"/bars"}))),
  selectedWindow:rank,
  windowResearch:windowRows,
  caveats:["Historical FDA event archive is NOT a verified pre-entry PDUFA announcement archive.",
   "No current market cap is substituted for entry-day market cap.",
   "The 2016-2025 event census is incomplete until all years are independently audited.",
   "Historical SIP adjusted prices and any source-provided share counts require independent audit.",
   "A realized event date cannot substitute for what was known when trading.",
   "Retrospective results are not prospective RAAS predictions or investment advice."]};
}
if(require.main===module) {
 const env=process.env;
 execute({key:env.APCA_API_KEY_ID||env.ALPACA_API_KEY_ID||env.ALPACA_API_KEY,
  secret:env.APCA_API_SECRET_KEY||env.ALPACA_SECRET_KEY}).then(r=>{
   const file=env.RAAS_TEN_YEAR_RESULT_PATH||path.join(root,"raas-ten-year-research.json");
   fs.mkdirSync(path.dirname(file),{recursive:true});
   fs.writeFileSync(file,JSON.stringify(r,null,2)+"\n");
   const headline={status:r.status,discoveryCandidates:r.discoveryCandidates,
    reviewedEvents:r.reviewedEvents,tenYearCensusComplete:r.tenYearCensusComplete,
    historicalDailyBarsCollected:r.historicalDailyBarsCollected,
    eligibleWindowRows:r.eligibleWindowRows,priceSourceFailures:r.priceSourceFailures,
    selectionStatus:r.selectedWindow.status};
   process.stdout.write(JSON.stringify(headline)+"\n");
   if(env.GITHUB_STEP_SUMMARY)fs.appendFileSync(env.GITHUB_STEP_SUMMARY,
    "### 2016-2025 Alpaca research — no unverified optimum\n\n"+
    JSON.stringify(headline,null,2)+"\n\nDownload the research artifact for case-level diagnostics.\n");
 }).catch(e=>{process.stderr.write("RAAS_TEN_YEAR_FATAL_"+String(e.message).replace(/[^A-Z0-9_]/g,"_")+"\n");process.exitCode=1;});
}
module.exports={candidateQueue,validRecord,intakeRecords,windowPrice,grid,summary,independent,chooseWindow,execute};
