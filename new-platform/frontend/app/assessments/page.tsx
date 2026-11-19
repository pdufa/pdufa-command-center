import {ExactTrialIntakeSelector} from "../ExactTrialScientificIntake";
import focusSnapshot from "../../data/p3PostDataActive.json";
import FocusScientificCoverageChart from "../FocusScientificCoverageChart";
import HistoricalScientificBacktest from "../HistoricalScientificBacktest";
import historicalPilot from "../../data/historicalScientificPilot2026.json";
import FocusSavedAssessments from "../FocusSavedAssessments";
import PastSavedAssessments from "../PastSavedAssessments";
import {PredictionHeaders,PredictionCells,PredictionLegend} from '../PdufaPredictionColumns';
import AssessmentLauncher from '../AssessmentLauncher';
import Link from 'next/link';
import AssessmentWorkbench from '../AssessmentWorkbench';

export default async function AssessmentsPage({searchParams}:{searchParams:Promise<{nct?:string}>}){
 const query=await searchParams;const nct=typeof query.nct==="string"&&/^NCT[0-9]{8}$/.test(query.nct)?query.nct:undefined;
 const focusTrial=nct?focusSnapshot.records.find(trial=>trial.nct===nct):undefined;
 return <main className="shell">
  <div className="topline">PDUFA COMMAND CENTER · SCIENTIFIC ASSESSMENTS</div>
  <h1>ASSESSMENTS</h1>
  <section aria-label="FOCUS scientific evidence Levels 1–6">
   <h2>FOCUS evidence · Levels 1–6</h2>
   <FocusScientificCoverageChart/>
   <form method="get" action="/assessments">
    <label>FOCUS trial <select name="nct" defaultValue={focusTrial?.nct??""} required>
     <option value="">Select a trial</option>
     {focusSnapshot.records.map(trial=><option key={trial.nct} value={trial.nct}>{trial.ticker} · {trial.nct}</option>)}
    </select></label>{" "}<button type="submit">Open trial evidence</button>
   </form>
   {focusTrial&&<ExactTrialIntakeSelector key={focusTrial.nct} cohort="FOCUS" nctId={focusTrial.nct}/>}
  </section>
  <HistoricalScientificBacktest surface="ASSESSMENTS" evaluation={historicalPilot}/>
  <p><a href="#focus-chart-quick-view" style={{display:"inline-block",padding:"9px 13px",background:"#e8f3ed",border:"1px solid #7baf99",borderRadius:7,fontWeight:700}}>View FOCUS four-line score chart</a></p>
  <p><Link href="/">← Command Center</Link></p>
  <p>Run source-backed assessments by exact NCT trial. Levels 1–3 evaluate trial identity, clinical design, efficacy and statistics. Scientific scores are withheld until validated; FDA predictions remain ABSTAIN. Historical runs require eligible pre-cutoff source snapshots.</p>
  <PredictionLegend/><section aria-label="PDUFA forecast status"><h2>PDUFA prediction and accuracy</h2><table><thead><tr><th>Trial</th><PredictionHeaders/></tr></thead><tbody><tr><td>Choose an exact NCT below</td><PredictionCells/></tr></tbody></table></section><AssessmentLauncher source="FOCUS"/><FocusSavedAssessments/><PastSavedAssessments/><AssessmentWorkbench selectedNct={nct}/>
 </main>;
}
