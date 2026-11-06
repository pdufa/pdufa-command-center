import PhaseFirstTable from "./PhaseFirstTable";
export const metadata={title:"Phase-first Clinical Analysis | PDUFA Command Center"};
export default function PhaseFirstPage(){return <main className="shell" style={{maxWidth:1500}}>
 <div className="topline">CLINICAL RESEARCH · VERIFIED INDIVIDUAL-TRIAL PHASE</div>
 <h1>Phase-first clinical analysis</h1>
 <p>Assess each study against the evidence appropriate to its own phase. Clinical research ratings, evidence completeness and FDA predictions are separate. Compare ratings within the same phase and coverage.</p>
 <PhaseFirstTable/>
 </main>;}
