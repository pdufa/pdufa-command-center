import coverage from "../../../public/phase3-source-coverage-20261105.json";

export const dynamic="force-dynamic";
const encode=(v:unknown)=>{
 let s=v===null||v===undefined?"":String(v).replace(/[\r\n]+/g," ");
 if(/^[=+@-]/.test(s))s="'"+s;
 return '"'+s.replace(/"/g,'""')+'"';
};
const csv=(cells:unknown[])=>cells.map(encode).join(",");
const HEADERS=[
 "NCT","Online registry status","Registered interventions",
 "Registered primary endpoint","Primary endpoint timeframe",
 "Enrollment","Allocation","Masking","Registered secondary outcome count",
 "Registry results posted","Posted result statistical analysis count","Registry public document count",
 "PubMed exact-NCT article PMID leads","SEC exact-NCT filing mention count","Source search errors",
 "Registry source URL","PubMed search URL","SEC search URL"
];
export async function GET(request:Request){
 if(coverage.trials!==762||coverage.rows.length!==762||
    new Set(coverage.rows.map(r=>r.nctId)).size!==762){
  return Response.json({error:"Online source snapshot failed NCT integrity check"},{status:503});
 }
 const u=new URL(request.url);
 const nct=u.searchParams.get("nctId")?.trim().toUpperCase();
 if(nct){
  if(!/^NCT\d{8}$/.test(nct))return Response.json({error:"Invalid exact NCT"},{status:400});
  const row=coverage.rows.find(r=>r.nctId===nct);
  if(!row)return Response.json({error:"NCT not in this 762-trial census"},{status:404});
  return Response.json({asOf:coverage.asOf,scope:coverage.notice,trial:row},{
   headers:{"Cache-Control":"no-store"}
  });
 }
 if(u.searchParams.get("format")==="csv"){
  const lines=[csv(HEADERS),...coverage.rows.map(r=>csv([
   r.nctId,r.registryStatus,r.interventions.join("; "),r.primaryEndpoint,r.primaryTimeFrame,
   r.enrollment,r.allocation,r.masking,r.secondaryEndpointCount,
   r.resultsPosted,r.resultsAnalysisCount,r.documentCount,r.pubmedPMIDs.join("; "),
   r.secFilingMentions,r.sourceErrors.join("; "),
   "https://clinicaltrials.gov/study/"+r.nctId,
   "https://pubmed.ncbi.nlm.nih.gov/?term="+r.nctId,
   "https://www.sec.gov/edgar/search/#/q="+r.nctId
  ]))];
  if(lines.length!==763||HEADERS.length!==18)
   return Response.json({error:"Source export row/column misalignment"},{status:503});
  return new Response("\uFEFF"+lines.join("\r\n")+"\r\n",{
   status:200,headers:{"Content-Type":"text/csv; charset=utf-8",
    "Content-Disposition":'attachment; filename="Phase3-762-Online-Source-Coverage-2026-11-05.csv"',
    "Cache-Control":"no-store"}
  });
 }
 const rows=coverage.rows;
 return Response.json({asOf:coverage.asOf,trials:rows.length,
  scope:coverage.notice,
  postedRegistryResults:rows.filter(r=>r.resultsPosted).length,
  primaryOutcomesAvailable:rows.filter(r=>r.primaryEndpoint).length,
  pubmedNctArticleLeads:rows.filter(r=>r.pubmedPMIDs.length).length,
  secFilingLeads:rows.filter(r=>(r.secFilingMentions||0)>0).length,
  usage:"Use ?format=csv for all 762 rows or ?nctId=NCT######## for one trial"
 },{headers:{"Cache-Control":"no-store"}});
}
