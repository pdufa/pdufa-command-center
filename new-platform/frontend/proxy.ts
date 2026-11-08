import {NextResponse} from "next/server";
import type {NextRequest} from "next/server";

/** Legacy retired dashboard and API endpoints must never execute. The
 * underlying dated research and trial evidence remains in immutable archives.
 * This is a presentation/execution boundary, not a deletion of records.
 */
export function proxy(request:NextRequest){
 const path=request.nextUrl.pathname.toLowerCase();
 if(/^\/(?:api\/)?raas(?:-|\/|$)/.test(path)){
  return new NextResponse(
   path.startsWith("/api/")?
    JSON.stringify({error:"Retired historical research endpoint. No live operation."}):
    "Historical research interface retired. Live analysis is available through the independent medical system.",
   {status:410,headers:{
     "Content-Type":path.startsWith("/api/")?"application/json":"text/plain; charset=utf-8",
     "Cache-Control":"no-store","X-PDUFA-Research-Status":"retired"}
   });
 }
 return NextResponse.next();
}

export const config={matcher:"/:path*"};
