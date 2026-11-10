import {NextResponse} from "next/server";
export const runtime="nodejs";
export const dynamic="force-dynamic";
export async function GET(){
 const url="https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml";
 try {
  const r=await fetch(url,{cache:"no-store",redirect:"manual",headers:{Accept:"application/rss+xml, application/xml, text/xml","User-Agent":"PDUFACommandCenter-SourceNews/1.0 (research; no credentials)"},signal:AbortSignal.timeout(9000)});
  const s=await r.text();
  const m=s.match(/<item\b[^>]*>([\s\S]*?)<\/item>/i);
  return NextResponse.json({status:r.status,contentType:r.headers.get("content-type"),length:s.length,
    head:s.slice(0,650),itemCount:(s.match(/<item\b/gi)||[]).length,firstItem:m?.[1]?.slice(0,1600)||null});
 }catch(e){return NextResponse.json({error:e instanceof Error?e.message:"fetch failed"},{status:503})}
}
