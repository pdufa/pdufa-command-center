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
    <div className="topline">PDUFA COMMAND CENTER · OWNER-ONLY OUTCOME GOVERNANCE</div>
    <h1>FDA Outcome Predictions</h1>
    <p data-testid="predictions-owner-only" style={{padding:"12px 15px",background:"#eefaf5",border:"1px solid #a0cbb7",borderRadius:9}}>
      <strong>OWNER-ONLY LEVELS 1–20:</strong> You decide whether to accept,
      revise, or publish an AI-assisted assessment. No external clinical reviewer,
      independent challenger or third-party verification/signoff is required.
      Evidence gaps, historical leakage restrictions and account security still apply.
    </p>
    <p aria-label="Prediction analysis depth" style={{margin:"8px 0 18px",lineHeight:1.6,fontSize:17,color:"#195749"}}>
      <strong style={{color:"#075c4b",background:"linear-gradient(transparent 58%,#b6f2dd 58%)",fontWeight:850,fontSize:"clamp(17px,2.3vw,22px)",paddingBottom:3}}>
        Deep Clinical Subspecialty Intelligence
      </strong>
      <span style={{display:"block",fontSize:12,color:"#5a6f64",marginTop:4}}>
        Disease-specific owner-controlled scientific research · numerical outcome probabilities not yet prospectively calibrated
      </span>
    </p>
    <p style={{fontSize:15,lineHeight:1.6,maxWidth:960}}>
      Select a FOCUS stock ticker, then choose the exact trial to inspect separate
      <strong> FDA Approval</strong>, <strong>Complete Response Letter (CRL)</strong>, and
      <strong> FDA Review Delay / Extension</strong> readiness.
      <strong> No numerical forecast has been prospectively calibrated or released.</strong>
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
    <HistoricalMonthlyLevelTrend compact/>
    <FullRosterSourceScan/>
    <p style={{fontSize:13,margin:"12px 0"}}><Link href="/analyze-now?nct=NCT06081894" style={{color:"#075c4b",fontWeight:700}}>Open saved research pilot and exact-NCT revision history (PostgreSQL required)</Link> · The pilot fails closed until its secure backend is explicitly ready.</p>
    <FocusPredictionNavigator/>
    <section style={{...card,background:"#f5faf7",marginBottom:16}} aria-label="Owner-controlled prediction certainty">
      <h2 style={{margin:"0 0 9px",fontSize:19}}>How prediction certainty is determined</h2>
      <p style={{fontSize:14,color:"#415c50",lineHeight:1.6,margin:0}}>
        Certainty is separate from the predicted outcome. Source collection, completed checklists,
        and a passing website build do not establish predictive reliability. Numerical certainty and
        confidence intervals require documented historical performance and prospective calibration, which you can check yourself.
      </p>
    </section>
    <section style={{...card,marginBottom:16}} aria-label="Release and data requirements">
      <h2 style={{margin:"0 0 9px",fontSize:19}}>What must pass before a forecast is released?</h2>
      <p style={{lineHeight:1.65,marginBottom:0}}>
        Confirm each FOCUS trial's exact FDA application cycle; reconcile original clinical,
        statistical, safety, manufacturing and regulator evidence; save a traceable analysis;
        and complete historical out-of-time calibration and your own release checks.
        Missing evidence remains <strong>UNKNOWN</strong>, and earlier FDA decisions are not future predictions.
      </p>
    </section>
    <nav aria-label="Related prediction evidence" style={{display:"flex",gap:16,flexWrap:"wrap",fontSize:14}}>
      <Link href="/focus">Open FOCUS candidates</Link>
      <Link href="/precision-monitoring">Precision Monitoring Dashboard</Link>
      <Link href="/main">MAIN acceptance status</Link>
      <Link href="/preview/deep-medical-intelligence">Owner-only medical intelligence preview</Link>
    </nav>
  </main>;
}
