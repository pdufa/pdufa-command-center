import {NextResponse} from "next/server";
import {APPLICATION_CYCLES} from "../../../lib/medical-intelligence-applications";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 30;

const FEEDS = [
  "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml",
  "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/drugs/rss.xml"
] as const;
const headers = {"Cache-Control":"public, max-age=0, s-maxage=300", "X-Content-Type-Options":"nosniff"};
const noMarkup = (value:string) => value.replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g,"$1")
  .replace(/<[^>]+>/g," ").replace(/\s+/g," ").trim();
function decode(value:string) {
  return noMarkup(value).replace(/&#(x[0-9a-f]+|\d+);|&(amp|lt|gt|quot|apos|nbsp);/gi,(match,num,entity)=>{
    if (num) {
      const cp = num[0].toLowerCase()==="x"?parseInt(num.slice(1),16):parseInt(num,10);
      return cp>0 && cp<=0x10ffff && !(cp>=0xd800&&cp<=0xdfff)?String.fromCodePoint(cp):"";
    }
    return ({amp:"&",lt:"<",gt:">",quot:'"',apos:"'",nbsp:" "})[String(entity).toLowerCase() as "amp"]||match;
  });
}
function field(xml:string,name:string):string {
  return decode(xml.match(new RegExp("<"+name+"(?:\\s[^>]*)?>([\\s\\S]*?)<\\/"+name+">","i"))?.[1]||"");
}
function officialFdaLink(value:string) {
  try {
    const url=new URL(value);
    if(!["http:","https:"].includes(url.protocol) ||
       !["www.fda.gov","fda.gov"].includes(url.hostname) ||
       url.username || url.password || url.port) return null;
    // The official FDA RSS feed currently publishes http:// links. Upgrade
    // *only* exact FDA hosts to HTTPS; never follow offsite redirects.
    url.protocol="https:";
    url.hostname="www.fda.gov";
    url.hash="";
    return url.href;
  }catch{return null;}
}
function aliases(drug:string) {
  const cleaned=drug.replace(/\s*\(.*$/,"").replace(/\s*\+.*$/,"").trim().toLowerCase();
  return cleaned.length>=6 && !["not recorded","unknown"].includes(cleaned)?[cleaned]:[];
}
function literalMatch(haystack:string,term:string) {
  const normalized=haystack.toLowerCase().replace(/[^a-z0-9]+/g," ");
  const target=term.replace(/[^a-z0-9]+/g," ").trim();
  return target.length>=6 && (" "+normalized+" ").includes(" "+target+" ");
}
export type NewsEntry = {
  id:string; title:string; publishedAt:string|null; sourceUrl:string;
  sourceName:string; kind:"FDA_ARTICLE"|"APPLICATION_SOURCE_RECORD";
  ticker:string|null; cycleId:string|null; drug:string|null;
  ncts:string[]; verification:"OFFICIAL_FDA_PUBLICATION"|"SOURCE_LINK_RECORDED";
  matchStatus:"UNREVIEWED_EXACT_DRUG_MENTION"|"NOT_MAPPED"|"CYCLE_SOURCE_RECORD";
  impact:"NOT_ASSESSED"; description:string;
};

function sourceRecords():NewsEntry[] {
  return APPLICATION_CYCLES.map(c=>({
    id:"cycle-"+c.id,title:"Recorded application evidence: "+c.drug+" — "+c.indication,
    publishedAt:c.sourceDate+"T00:00:00.000Z", sourceUrl:c.sourceUrl,
    sourceName:c.sourceUrl.includes("sec.gov")?"SEC filing":"Sponsor / issuer source",
    kind:"APPLICATION_SOURCE_RECORD" as const,ticker:c.ticker,cycleId:c.id,
    drug:c.drug,ncts:[...c.ncts],verification:"SOURCE_LINK_RECORDED" as const,
    matchStatus:"CYCLE_SOURCE_RECORD" as const,impact:"NOT_ASSESSED" as const,
    description:"Dated source pointer recorded in the application cycle map. This is not a newly retrieved article, independent FDA verification, or a news-driven prediction."
  }));
}

async function fdaItems():Promise<NewsEntry[]> {
  const fetched=await Promise.allSettled(FEEDS.map(async (url)=>{
    const response=await fetch(url,{
      method:"GET",cache:"no-store",redirect:"manual",
      headers:{"Accept":"application/rss+xml, application/xml, text/xml","User-Agent":"PDUFACommandCenter-SourceNews/1.0 (research; no credentials)"},
      signal:AbortSignal.timeout(9000)
    });
    if(!response.ok || !String(response.headers.get("content-type")||"").match(/xml|rss|text\/plain/i))
      throw new Error("FDA feed not available");
    const raw=await response.text();
    if(raw.length>750000 || !/<rss\b/i.test(raw)) throw new Error("Invalid FDA XML feed");
    const entries:NewsEntry[]=[];
    for(const matched of raw.matchAll(/<item\b[^>]*>([\s\S]*?)<\/item>/gi)){
      const item=matched[1],sourceUrl=officialFdaLink(field(item,"link"));
      const title=field(item,"title"),pub=field(item,"pubDate");
      if(!sourceUrl||!title||title.length>300)continue;
      const published=new Date(pub);
      if(!Number.isFinite(published.getTime()))continue;
      const description=field(item,"description").slice(0,500);
      const sourceText=title+" "+description;
      const matchedCycles=APPLICATION_CYCLES.filter(c=>aliases(c.drug).some(alias=>literalMatch(sourceText,alias)));
      // Never guess the application if one drug could refer to multiple cycles.
      const exact=matchedCycles.length===1?matchedCycles[0]:null;
      entries.push({
        id:"fda-"+sourceUrl, title, publishedAt:published.toISOString(),sourceUrl,
        sourceName:"U.S. FDA",kind:"FDA_ARTICLE", ticker:exact?.ticker||null,
        cycleId:exact?.id||null,drug:exact?.drug||null,ncts:exact?[...exact.ncts]:[],
        verification:"OFFICIAL_FDA_PUBLICATION",
        matchStatus:exact?"UNREVIEWED_EXACT_DRUG_MENTION":"NOT_MAPPED",
        impact:"NOT_ASSESSED",description
      });
    }
    return entries;
  }));
  const available=fetched.filter((x):x is PromiseFulfilledResult<NewsEntry[]>=>x.status==="fulfilled");
  if(!available.length)throw new Error("No live FDA feeds");
  const byUrl=new Map<string,NewsEntry>();
  for(const result of available)for(const entry of result.value)byUrl.set(entry.sourceUrl,entry);
  return [...byUrl.values()].sort((a,b)=>(b.publishedAt||"").localeCompare(a.publishedAt||"")).slice(0,80);
}

export async function GET() {
  const documents=sourceRecords();
  try {
    const live=await fdaItems();
    return NextResponse.json({schemaVersion:1,feedStatus:"LIVE_FDA_RSS",fetchedAt:new Date().toISOString(),
      articles:live,records:documents,
      note:"FDA publication authenticity is not FDA application-cycle attribution. Exact drug matches are unreviewed and never change a prediction."},{headers});
  }catch {
    return NextResponse.json({schemaVersion:1,feedStatus:"FDA_RSS_UNAVAILABLE",fetchedAt:new Date().toISOString(),
      articles:[],records:documents,
      note:"Live FDA RSS unavailable; dated source-pointer records are displayed separately, not as new articles."},
      {headers:{"Cache-Control":"no-store","X-Content-Type-Options":"nosniff"}});
  }
}
