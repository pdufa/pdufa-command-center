import Link from "next/link";
import type {Metadata} from "next";

export const metadata:Metadata={
  title:"FDA Outcome Predictions | PDUFA",
  description:"Independent FDA approval, complete response letter and review-delay prediction readiness. Unvalidated outcomes abstain."
};
const outcomes=[
  {name:"FDA Approval",description:"Approval outcome for the specific drug, indication and FDA application cycle."},
  {name:"Complete Response Letter (CRL)",description:"Risk of an FDA letter requiring deficiencies to be addressed before an application can be approved."},
  {name:"FDA Review Delay / Extension",description:"Risk that the FDA review timeline changes before a final action."}
];
const card={background:"#fff",border:"1px solid #c7d9d0",borderRadius:12,padding:20} as const;

export default function PredictionsPage(){
  return <main className="shell" style={{maxWidth:1120,margin:"0 auto",padding:"24px 14px 48px"}}>
    <div className="topline">PDUFA COMMAND CENTER · INDEPENDENT OUTCOME GOVERNANCE</div>
    <h1>FDA Outcome Predictions</h1>
    <p style={{fontSize:15,lineHeight:1.6,maxWidth:880}}>
      Three separate FDA outcomes are defined for research and future calibration.
      <strong> No numerical forecast has been independently validated or released.</strong>
      The current safe prediction is <strong>ABSTAIN</strong>, not an approval or rejection forecast.
    </p>
    <section style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(min(100%,240px),1fr))",gap:14,margin:"22px 0"}} aria-label="Independent FDA prediction outcomes">
      {outcomes.map(outcome=><article key={outcome.name} style={card}>
        <h2 style={{fontSize:18,margin:"0 0 9px",color:"#102f40"}}>{outcome.name}</h2>
        <p style={{fontSize:13,lineHeight:1.5,color:"#425964",minHeight:54}}>{outcome.description}</p>
        <p style={{border:"1px solid #d19b55",borderRadius:8,background:"#fff7e9",padding:11,marginBottom:0}}>
          <strong style={{color:"#7d4c0a"}}>ABSTAIN</strong>
          <span style={{display:"block",color:"#705f4c",fontSize:12,marginTop:3}}>Probability not released or validated</span>
        </p>
      </article>)}
    </section>
    <section style={{...card,background:"#f5faf7",marginBottom:16}} aria-label="Independent prediction certainty">
      <h2 style={{margin:"0 0 9px",fontSize:19}}>Prediction Certainty Rating</h2>
      <p style={{margin:"0 0 8px"}}><strong>NOT VALIDATED</strong></p>
      <p style={{fontSize:14,color:"#415c50",lineHeight:1.6,margin:0}}>
        Certainty is separate from the predicted outcome. Source collection, completed checklists,
        and a passing website build do not establish predictive reliability. Numerical certainty and
        confidence intervals require independently evaluated historical performance and calibration.
      </p>
    </section>
    <section style={{...card,marginBottom:16}} aria-label="Release and data requirements">
      <h2 style={{margin:"0 0 9px",fontSize:19}}>What must pass before a forecast is released?</h2>
      <p style={{lineHeight:1.65,marginBottom:0}}>
        Confirm each FOCUS trial's exact FDA application cycle; reconcile original clinical,
        statistical, safety, manufacturing and regulator evidence; save a traceable analysis;
        and complete historical out-of-time validation and independent release checks.
        Missing evidence remains <strong>UNKNOWN</strong>, and earlier FDA decisions are not future predictions.
      </p>
    </section>
    <nav aria-label="Related prediction evidence" style={{display:"flex",gap:16,flexWrap:"wrap",fontSize:14}}>
      <Link href="/focus">Open FOCUS candidates</Link>
      <Link href="/precision-monitoring">Precision Monitoring Dashboard</Link>
      <Link href="/main">MAIN acceptance status</Link>
      <Link href="/preview/deep-medical-intelligence">Independent medical intelligence preview</Link>
    </nav>
  </main>;
}
