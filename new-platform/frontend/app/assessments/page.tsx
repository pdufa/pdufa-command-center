import FocusSavedAssessments from "../FocusSavedAssessments";
import PastSavedAssessments from "../PastSavedAssessments";
import {PredictionHeaders,PredictionCells,PredictionLegend} from '../PdufaPredictionColumns';
import AssessmentLauncher from '../AssessmentLauncher';
import Link from 'next/link';
import AssessmentWorkbench from '../AssessmentWorkbench';
import SixIndependentFocusSurveys from '../SixIndependentFocusSurveys';

export default async function AssessmentsPage({searchParams}:{searchParams:Promise<{nct?:string}>}){
 const query=await searchParams;const nct=query.nct&&/^NCT[0-9]{8}$/.test(query.nct)?query.nct:undefined;
 return <main className="shell">
  <div className="topline">PDUFA COMMAND CENTER · SCIENTIFIC ASSESSMENTS</div>
  <h1>ASSESSMENTS · Scientific Levels 1–6</h1>
  <p><a href="#focus-chart-quick-view" style={{display:"inline-block",padding:"9px 13px",background:"#e8f3ed",border:"1px solid #7baf99",borderRadius:7,fontWeight:700}}>View FOCUS four-line score chart</a></p>
  <p><Link href="/">← Command Center</Link></p>
  <p>Run source-backed assessments by exact NCT trial. Levels 1–3 evaluate trial identity, clinical design, efficacy and statistics. Scientific scores are withheld until validated; FDA predictions remain ABSTAIN. Historical runs require eligible pre-cutoff source snapshots.</p>
  <PredictionLegend/><section aria-label="PDUFA forecast status"><h2>PDUFA prediction and accuracy</h2><table><thead><tr><th>Trial</th><PredictionHeaders/></tr></thead><tbody><tr><td>Choose an exact NCT below</td><PredictionCells/></tr></tbody></table></section><SixIndependentFocusSurveys/><AssessmentLauncher source="FOCUS"/><FocusSavedAssessments/><PastSavedAssessments/><AssessmentWorkbench selectedNct={nct}/>
 </main>;
}
