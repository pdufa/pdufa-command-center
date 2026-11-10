import Link from "next/link";
import type {Metadata} from "next";
import FocusPredictionNavigator from "./FocusPredictionNavigator";
import FullRosterSourceScan from "./FullRosterSourceScan";
import HistoricalMonthlyLevelTrend from "../HistoricalMonthlyLevelTrend";

export const metadata:Metadata={
  title:"FDA Outcome Predictions | PDUFA",
  description:"Navigate the FOCUS roster by ticker and exact NCT to inspect FDA approval, CRL and review-delay readiness. Unvalidated forecasts abstain."
};
const card={background:"#fff",border:"1px solid #c7d9d0",borderRadius:12,padding:20} as const;

export default function PredictionsPage(){
  return <main className="shell" style={{maxWidth:1200,margin:"0 auto",padding:"24px 14px 48px"}}>
    <div className="topline">PDUFA COMMAND CENTER · INDEPENDENT OUTCOME GOVERNANCE</div>
    <h1>FDA Outcome Predictions</h1>
    <p aria-label="Prediction analysis depth" style={{margin:"8px 0 18px",lineHeight:1.6,fontSize:17,color:"#195749"}}>
      <strong style={{color:"#075c4b",background:"linear-gradient(transparent 58%,#b6f2dd 58%)",fontWeight:850,fontSize:"clamp(17px,2.3vw,22px)",paddingBottom:3}}>
        Deep Clinical Subspecialty Intelligence
      </strong>
      <span style={{display:"block",fontSize:12,color:"#5a6f64",marginTop:4}}>
        Disease-specific scientific research framework · outcome probabilities and certainty not yet independently validated
      </span>
    </p>
    <p style={{fontSize:15,lineHeight:1.6,maxWidth:960}}>
      Select a FOCUS stock ticker, then choose the exact trial to inspect separate
      <strong> FDA Approval</strong>, <strong>Complete Response Letter (CRL)</strong>, and
      <strong> FDA Review Delay / Extension</strong> readiness.
      <strong> No numerical forecast has been independently validated or released.</strong>
      Until then, each outcome remains <strong>ABSTAIN</strong> and certainty remains <strong>NOT VALIDATED</strong>.
    </p>
    <p style={{margin:"12px 0 7px",fontSize:14,lineHeight:1.6}}>
      <Link href="/predictions/assessment" style={{fontWeight:800,color:"#087260",textDecoration:"underline"}}>
        Explore the 29-trial Deep Clinical Subspecialty research and evidence-readiness ledger
      </Link>
      <span style={{display:"block",fontSize:12,color:"#657c74"}}>
        Source-linked partial clinical dossiers and missing-evidence checkpoints. Not completed assessments or validated forecasts.
      </span>
    </p>
    <section style={{...card,background:"#fffaf0",borderColor:"#d8bc85",marginBottom:16}}
      aria-label="FOCUS 29 provisional Level 3 research">
      <div style={{fontSize:11,fontWeight:850,color:"#825913",letterSpacing:".07em"}}>
        NEW · LEVEL 3-STYLE DIRECTIONAL RESEARCH
      </div>
      <h2 style={{fontSize:20,margin:"6px 0"}}>29 FOCUS trials · 23 FDA application cycles</h2>
      <p style={{fontSize:13,lineHeight:1.6,margin:"6px 0"}}>
        Preliminary research: 12 approval leans, 5 CRL leans, 5 abstentions and 1
        already-approved application. These are not independent completed Level 3
        grades or calibrated engine forecasts.
      </p>
      <Link href="/predictions/assessment#focus-29-level3-research"
        style={{color:"#086d5a",fontWeight:800,textDecoration:"underline"}}>
        View every provisional Level 3 call, exact NCT, three evidence layers and sources
      </Link>
    </section>
    <HistoricalMonthlyLevelTrend compact/>
    <FullRosterSourceScan/>
    <p style={{fontSize:13,margin:"12px 0"}}><Link href="/analyze-now?nct=NCT06081894" style={{color:"#075c4b",fontWeight:700}}>Open saved research pilot and exact-NCT revision history (PostgreSQL required)</Link> · The pilot fails closed until its secure backend is explicitly ready.</p>
    <FocusPredictionNavigator/>
    <section style={{...card,background:"#f5faf7",marginBottom:16}} aria-label="Independent prediction certainty">
      <h2 style={{margin:"0 0 9px",fontSize:19}}>How prediction certainty is determined</h2>
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
