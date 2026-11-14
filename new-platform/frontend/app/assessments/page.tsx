import {PredictionHeaders,PredictionCells,PredictionLegend} from '../PdufaPredictionColumns';
import AssessmentLauncher from '../AssessmentLauncher';
import Link from 'next/link';
import AssessmentWorkbench from '../AssessmentWorkbench';

export default function AssessmentsPage(){
 return <main className="shell">
  <div className="topline">PDUFA COMMAND CENTER · SCIENTIFIC ASSESSMENTS</div>
  <h1>ASSESSMENTS · Levels 1–6</h1>
  <p><Link href="/">← Command Center</Link></p>
  <p>Run source-backed assessments by exact NCT trial. Levels 1–3 cover source provenance, phase verification and reported clinical results. Evidence coverage is not FDA approval probability. Historical runs require eligible pre-cutoff source snapshots.</p>
  <PredictionLegend/><section aria-label="PDUFA forecast status"><h2>PDUFA prediction and accuracy</h2><table><thead><tr><th>Trial</th><PredictionHeaders/></tr></thead><tbody><tr><td>Choose an exact NCT below</td><PredictionCells/></tr></tbody></table></section><AssessmentLauncher source="FOCUS"/><AssessmentWorkbench/>
 </main>;
}
