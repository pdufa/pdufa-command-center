/** Permanently retired compatibility endpoint. No scoring module is imported. */
export const dynamic="force-dynamic";
export function GET(){
 return Response.json({error:"RAAS_PERMANENTLY_RETIRED",status:"RETIRED",historicalArchive:"/api/archive/raas",message:"Historical records are read-only and cannot enter active analysis."},{status:410,headers:{"Cache-Control":"no-store"}});
}
