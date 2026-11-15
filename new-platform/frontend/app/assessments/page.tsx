import FocusSavedAssessments from "../FocusSavedAssessments";
import PastSavedAssessments from "../PastSavedAssessments";
import {PredictionHeaders,PredictionCells,PredictionLegend} from '../PdufaPredictionColumns';
import AssessmentLauncher from '../AssessmentLauncher';
import PastAssessmentYearLauncher from '../PastAssessmentYearLauncher';
import Link from 'next/link';
import AssessmentWorkbench from '../AssessmentWorkbench';

export default async function AssessmentsPage({searchParams}:{searchParams:Promise<{nct?:string}>}){
 const query=await searchParams;const nct=query.nct&&/^NCT[0-9]{8}$/.test(query.nct)?query.nct:undefined;
 return <main className="shell">
  <div className="topline">PDUFA COMMAND CENTER · SCIENTIFIC ASSESSMENTS</div>
  <h1>ASSESSMENTS · Scientific Levels 1–3</h1>
  <p><Link href="/">← Command Center</Link></p>
  <p>Saved FOCUS trial research appears below for all 32 exact-NCT trials, with separate Level 1, Level 2 and Level 3 findings and links to original evidence. These 96 completed research reports do not imply validated scientific scores or FDA approval probabilities: unvalidated scores are withheld and predictions remain ABSTAIN. Historical runs require eligible pre-cutoff source snapshots.</p>
  <PredictionLegend/><section aria-label="PDUFA forecast status"><h2>PDUFA prediction and accuracy</h2><table><thead><tr><th>Trial</th><PredictionHeaders/></tr></thead><tbody><tr><td>Choose an exact NCT below</td><PredictionCells/></tr></tbody></table></section><section aria-label="FOCUS cohort assessments" style={{margin:'16px 0',border:'1px solid #b9cebe',borderRadius:8,padding:12}}><h2>FOCUS · Upcoming PDUFA assessments</h2><p>Run single, selected or verified whole FOCUS trial roster.</p><AssessmentLauncher source="FOCUS" lockSource/></section><PastAssessmentYearLauncher/><FocusSavedAssessments selectedNct={nct}/><PastSavedAssessments/><AssessmentWorkbench selectedNct={nct}/>
 </main>;
}
